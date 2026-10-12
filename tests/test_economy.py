import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch

from phenomenal_engine.cli import main
from phenomenal_engine.economy import EconomyError, station_snapshot, prepare_command, settle_economy, load_profile
from phenomenal_engine.engine import Engine
from phenomenal_engine.memory import new_memory, save_memory, verify_ledger
from phenomenal_engine.mod_loader import load_mod
from phenomenal_engine.turn_exchange import propose_turn, git_blob_sha, TurnExchangeError
from phenomenal_engine.consent import covenant_digest


class EconomyTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_mod('mods/mirror_delivery.json')
        self.memory = new_memory(self.mod, 'market-test')
        self.memory['world_state']['location'] = 'earth_escape_gate'

    def step(self, command, action='I visit the local station businesses'):
        return Engine(self.mod,self.memory).step(action,economy_command=command,idempotency_key='fixture-'+str(self.memory['turn']))

    def offer(self,vendor='gate_outfitter',item='ration_pack'):
        market=station_snapshot(self.mod,self.memory)
        v=next(v for v in market['vendors'] if v['vendor_id']==vendor)
        return next(o for o in v['offers'] if o['item_id']==item)

    def buy(self,qty=3,item='ration_pack',vendor='gate_outfitter'):
        return {'kind':'buy','vendor_id':vendor,'item_id':item,'quantity':qty,'expected_unit_price':self.offer(vendor,item)['buy_price']}

    def job(self,code='manifests'):
        return next(j for j in station_snapshot(self.mod,self.memory)['job_board'] if ':'+code+':' in j['job_id'])

    def test_hubs_have_distinct_people_markets_and_exploration(self):
        gate=station_snapshot(self.mod,self.memory)
        self.assertEqual(len(gate['vendors']),5)
        self.assertEqual(len(gate['job_board']),8)
        self.assertEqual(len(gate['sectors']),6)
        self.memory['world_state']['location']='nacre_station'
        nacre=station_snapshot(self.mod,self.memory)
        self.assertEqual(len(nacre['vendors']),6)
        self.assertEqual(len(nacre['job_board']),10)
        self.assertNotEqual(gate['vendors'][0]['npc']['name'],nacre['vendors'][0]['npc']['name'])

    def test_browsing_and_quotes_never_mutate_or_consume_rng(self):
        before=copy.deepcopy(self.memory)
        command=self.buy()
        q=prepare_command(self.mod,self.memory,command)
        self.assertEqual(q['quote']['total_credits'],3*command['expected_unit_price'])
        self.assertEqual(before,self.memory)
        self.assertTrue(station_snapshot(self.mod,self.memory)['read_only'])

    def test_buy_and_sell_conserve_credits_and_items(self):
        e=self.memory['economy'];v=e['stations']['earth_escape_gate']['vendors']['gate_outfitter']
        initial_money=e['credits']+v['credits'];initial_items=e['inventory']['ration_pack']+v['stock']['ration_pack']
        self.step(self.buy(3))
        e=self.memory['economy'];v=e['stations']['earth_escape_gate']['vendors']['gate_outfitter']
        self.assertEqual(initial_money,e['credits']+v['credits'])
        self.assertEqual(initial_items,e['inventory']['ration_pack']+v['stock']['ration_pack'])
        sell={'kind':'sell','vendor_id':'gate_outfitter','item_id':'ration_pack','quantity':3,'expected_unit_price':self.offer()['sell_price']}
        self.step(sell)
        e=self.memory['economy'];v=e['stations']['earth_escape_gate']['vendors']['gate_outfitter']
        self.assertEqual(initial_money,e['credits']+v['credits'])
        self.assertEqual(initial_items,e['inventory']['ration_pack']+v['stock']['ration_pack'])
        self.assertTrue(verify_ledger(self.memory))

    def test_invalid_transactions_are_atomic(self):
        cases=[dict(self.buy(),quantity=-1),dict(self.buy(),quantity=True),dict(self.buy(),quantity=9999),
               dict(self.buy(),expected_unit_price=9999),dict(self.buy(),vendor_id='nacre_growers'),
               {'kind':'buy','vendor_id':'gate_outfitter','item_id':'ration_pack','quantity':1},
               {'kind':'service','service_id':'unknown','expected_price':100}]
        for command in cases:
            before=copy.deepcopy(self.memory)
            with self.subTest(command=command):
                with self.assertRaises(EconomyError):self.step(command)
                self.assertEqual(before,self.memory)
        self.memory['economy']['cargo_capacity_g']=1
        before=copy.deepcopy(self.memory)
        with self.assertRaises(EconomyError):self.step(self.buy())
        self.assertEqual(before,self.memory)

    def test_services_apply_resources_time_and_readiness_without_touching_mir(self):
        before=copy.deepcopy(self.memory)
        packet=self.step({'kind':'service','service_id':'full_service','expected_price':1100})
        after=self.memory
        self.assertEqual(after['economy']['credits'],before['economy']['credits']-1100)
        self.assertEqual(after['world_state']['world_time_minutes'],240)
        self.assertAlmostEqual(after['world_state']['morrowglass_propellant_margin'],.97)
        self.assertAlmostEqual(after['world_state']['morrowglass_thermal_margin'],.90)
        self.assertEqual(after['world_state']['mirror_payload_status'],'sealed_pristine')
        self.assertEqual(after['world_state']['mirror_activation_count'],0)
        self.assertTrue(packet['simulation_outcome']['deterministic'])
        self.assertEqual(packet['story_update']['action_mode'],'craft')

    def test_service_fails_if_provider_has_no_parts(self):
        self.memory['economy']['stations']['earth_escape_gate']['vendors']['gate_yard']['stock']['propellant_canister']=0
        before=copy.deepcopy(self.memory)
        with self.assertRaises(EconomyError):self.step({'kind':'service','service_id':'full_service','expected_price':1100})
        self.assertEqual(before,self.memory)

    def test_paid_work_tracks_progress_and_pays_only_once(self):
        offer=self.job();command={'kind':'accept_job','job_id':offer['job_id']}
        starting=self.memory['economy']['credits']
        self.step(command)
        self.assertEqual(self.memory['economy']['credits'],starting)
        with patch.object(Engine,'_resolve_check',return_value={'success_probability':.8,'uniform_draw':.2,'success':True,'degree':'success','margin':1,'confidence':.6,'consequence_severity':0}):
            self.step({'kind':'work_job','job_id':offer['job_id']})
        self.assertEqual(self.memory['economy']['jobs'][offer['job_id']]['status'],'ready_for_payment')
        self.step({'kind':'claim_reward','job_id':offer['job_id']})
        self.assertEqual(self.memory['economy']['credits'],starting+offer['reward_credits'])
        self.assertEqual(self.memory['quests']['economy:'+offer['job_id']]['status'],'completed')
        before=copy.deepcopy(self.memory)
        with self.assertRaises(EconomyError):self.step({'kind':'claim_reward','job_id':offer['job_id']})
        self.assertEqual(before,self.memory)
        with self.assertRaises(EconomyError):self.step(command)
        self.assertTrue(verify_ledger(self.memory))

    def test_partial_work_is_useful_but_unfinished_work_cannot_be_claimed(self):
        offer=self.job('tug_schedule');self.step({'kind':'accept_job','job_id':offer['job_id']})
        with self.assertRaises(EconomyError):self.step({'kind':'claim_reward','job_id':offer['job_id']})
        with patch.object(Engine,'_resolve_check',return_value={'success_probability':.66,'uniform_draw':.68,'success':False,'degree':'partial_success','margin':-.1,'confidence':.3,'consequence_severity':.1}):
            self.step({'kind':'work_job','job_id':offer['job_id']})
        self.assertEqual(self.memory['economy']['jobs'][offer['job_id']]['progress'],1)

    def test_delivery_requires_actual_destination_and_carried_capacity(self):
        offer=self.job('nacre_crate')
        self.step({'kind':'accept_job','job_id':offer['job_id']})
        before=copy.deepcopy(self.memory)
        with self.assertRaises(EconomyError):self.step({'kind':'deliver_job','job_id':offer['job_id']})
        self.assertEqual(before,self.memory)
        self.memory['world_state']['location']='nacre_station'
        self.step({'kind':'deliver_job','job_id':offer['job_id']})
        self.step({'kind':'claim_reward','job_id':offer['job_id']})
        self.assertEqual(self.memory['economy']['jobs'][offer['job_id']]['status'],'completed')

    def test_time_advances_stock_activity_consumption_and_expiring_jobs(self):
        offer=self.job();self.step({'kind':'accept_job','job_id':offer['job_id']})
        inventory_before=self.memory['economy']['inventory']['ration_pack']
        v=self.memory['economy']['stations']['earth_escape_gate']['vendors']['gate_outfitter'];v['stock']['ration_pack']=0
        self.step({'kind':'wait','minutes':4320})
        e=self.memory['economy']
        self.assertEqual(e['inventory']['ration_pack'],inventory_before-9)
        self.assertGreater(e['stations']['earth_escape_gate']['vendors']['gate_outfitter']['stock']['ration_pack'],0)
        self.assertEqual(e['jobs'][offer['job_id']]['status'],'expired')
        self.assertEqual(e['jobs'][offer['job_id']]['escrow'],0)
        self.assertTrue(any(x['kind']=='station_activity' for x in e['activity_log']))
        self.assertTrue(verify_ledger(self.memory))

    def test_shortages_never_create_negative_inventory_or_automatic_deaths(self):
        self.memory['economy']['inventory']['ration_pack']=1
        self.step({'kind':'wait','minutes':2880})
        e=self.memory['economy'];self.assertEqual(e['inventory']['ration_pack'],0)
        self.assertEqual(e['shortages']['ration_pack'],5)
        self.assertEqual(self.memory['world_state']['morrowglass_hull'],1)

    def test_legacy_save_initialization_does_not_rewrite_or_back_consume(self):
        del self.memory['economy'];self.memory['world_state']['world_time_minutes']=480
        before=copy.deepcopy(self.memory)
        snap=station_snapshot(self.mod,self.memory)
        self.assertTrue(snap['initialization_pending']);self.assertEqual(before,self.memory)
        self.step({'kind':'visit_sector','sector_id':'market_ring'})
        self.assertEqual(self.memory['economy']['initialization']['at_world_minute'],480)
        self.assertEqual(self.memory['economy']['inventory']['ration_pack'],135)
        self.assertEqual(self.memory['event_ledger'][:-1],before['event_ledger'])

    def test_local_sector_visit_does_not_launch_ship(self):
        self.step({'kind':'visit_sector','sector_id':'dispatch_hall'},'I visit a desk before our journey to Mercury')
        self.assertEqual(self.memory['world_state']['location'],'earth_escape_gate')
        self.assertEqual(self.memory['economy']['local_sector']['sector_id'],'dispatch_hall')
        self.assertEqual(self.memory['world_state']['world_time_minutes'],15)

    def test_world_activity_is_bounded_even_after_long_elapsed_time(self):
        self.memory['world_state']['world_time_minutes']=1440*100000
        developments=settle_economy(self.mod,self.memory)
        self.assertLess(len(developments),30)
        self.assertLessEqual(len(self.memory['economy']['activity_log']),40)
        profile=load_profile(self.mod)
        for sid,state in self.memory['economy']['stations'].items():
            for vid,v in state['vendors'].items():
                definition=profile['stations'][sid]['vendors'][vid]
                for item,qty in v['stock'].items():self.assertLessEqual(qty,definition['stock'][item]['capacity'])

    def test_stock_flow_is_independent_of_time_partition(self):
        single=copy.deepcopy(self.memory);split=copy.deepcopy(self.memory)
        single['world_state']['world_time_minutes']=1440*37
        settle_economy(self.mod,single)
        for day in range(1,38):
            split['world_state']['world_time_minutes']=day*1440
            settle_economy(self.mod,split)
        self.assertEqual(single['economy']['stations'],split['economy']['stations'])
        self.assertEqual(single['economy']['inventory'],split['economy']['inventory'])

    def test_hidden_station_activity_does_not_leak_into_observer_packet(self):
        packet=self.step({'kind':'wait','minutes':2880})
        self.assertNotIn('redoubt_asteroid',{x.get('station_id') for x in packet['story_update']['economy_developments']})

    def test_legacy_initialization_precedes_first_new_travel(self):
        del self.memory['economy']
        before=copy.deepcopy(self.memory['event_ledger'])
        packet=Engine(self.mod,self.memory).step('I travel to Nacre Station',adjudication={
            'mode':'automatic','task':'routine_movement','reason':'An available authored route'})
        self.assertEqual(self.memory['economy']['initialization']['at_world_minute'],0)
        self.assertLess(self.memory['economy']['inventory']['ration_pack'],135)
        self.assertEqual(before,self.memory['event_ledger'][:-1])
        self.assertIn('economy_initialization',packet['simulation_outcome'])

    def test_owned_supplies_can_be_used_for_ship_readiness(self):
        before=self.memory['economy']['inventory']['coolant_pack']
        self.step({'kind':'use_item','item_id':'coolant_pack','quantity':1})
        self.assertEqual(self.memory['economy']['inventory']['coolant_pack'],before-1)
        self.assertAlmostEqual(self.memory['world_state']['morrowglass_thermal_margin'],.82)
        self.assertEqual(self.memory['world_state']['mirror_payload_status'],'sealed_pristine')

    def test_cli_market_view_never_writes_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            save=Path(tmp)/'save.json';save_memory(save,self.memory);before=save.read_bytes()
            out=io.StringIO()
            with redirect_stdout(out):main(['economy','mods/mirror_delivery.json',str(save)])
            result=json.loads(out.getvalue());self.assertTrue(result['no_state_mutated'])
            self.assertEqual(save.read_bytes(),before)

    def test_connected_quote_purchase_and_retry_are_idempotent(self):
        self.memory['github_publication']={'repository':'Aggredicus/Phenomenal-Engine','branch':'campaign-saves',
            'path':'campaigns/economy_fixture.json','public':True,'agreement_sha256':covenant_digest()}
        raw=json.dumps(self.memory)
        req={'campaign_id':'economy_fixture','mod_id':'mirror_delivery','expected_state_version':0,
             'expected_blob_sha':git_blob_sha(raw.encode()),'save_json':raw,'action':'I buy rations',
             'idempotency_key':'purchase-1','economy_command':self.buy()}
        preview=propose_turn(dict(req,operation='preview'))
        proposal=propose_turn(dict(req,expected_adjudication_sha256=preview['adjudication_sha256'],
                                  expected_economy_sha256=preview['economy_quote']['quote_sha256']))
        self.assertFalse(proposal['persisted'])
        saved=json.loads(proposal['proposed_save_json'])
        retry=dict(req,expected_state_version=1,expected_blob_sha=proposal['proposed_blob_sha'],save_json=proposal['proposed_save_json'])
        self.assertEqual(propose_turn(retry)['status'],'duplicate')
        with self.assertRaisesRegex(TurnExchangeError,'different economy'):
            propose_turn(dict(retry,economy_command=dict(self.buy(),quantity=4)))
        self.assertEqual(saved['economy']['inventory']['ration_pack'],138)
        self.assertTrue(verify_ledger(saved))


if __name__=='__main__':unittest.main()
