import copy
import json
import unittest
from unittest.mock import patch

from phenomenal_engine.campaign import CampaignError, campaign_view, prepare_command, sync_campaign, load_profile, validate_profile
from phenomenal_engine.engine import Engine
from phenomenal_engine.memory import new_memory, verify_ledger
from phenomenal_engine.mod_loader import load_mod
from phenomenal_engine.github_saves import encode_state, decode_state
from phenomenal_engine.turn_exchange import propose_turn, git_blob_sha, TurnExchangeError
from phenomenal_engine.consent import covenant_digest


SUCCESS={'success_probability':.8,'uniform_draw':.2,'success':True,'degree':'success','margin':1,'confidence':.6,'consequence_severity':0}


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.mod=load_mod('mods/mirror_delivery.json')
        self.memory=new_memory(self.mod,'campaign-test')

    def act(self,command):
        return Engine(self.mod,self.memory).step('I take the selected campaign action',campaign_command=command,
                                                idempotency_key='fixture-'+str(self.memory['turn']))

    def choose(self,scene,choice):return self.act({'kind':'choose','scene_id':scene,'choice_id':choice})
    def talk(self,npc,topic):return self.act({'kind':'talk','npc_id':npc,'topic_id':topic})

    def stage(self,location,days=0):
        self.memory['world_state']['location']=location
        self.memory['world_state']['world_time_minutes']=days*1440
        sync_campaign(self.mod,self.memory)

    def test_scene_and_topic_views_do_not_reveal_hidden_evidence(self):
        before=copy.deepcopy(self.memory)
        view=campaign_view(self.mod,self.memory)
        self.assertEqual(before,self.memory)
        self.assertEqual(view['evidence'],[])
        self.assertNotIn('mirror_instance',view['conversation_topics'])
        self.assertNotIn('accountability',[t['topic_id'] for t in view['conversation_topics']['heliograph']])
        self.assertNotIn('Three Shares',json.dumps(view))

    def test_cairn_conversation_has_a_recorded_reply_not_a_coin_flip(self):
        packet=self.talk('sister_cairn','ships')
        outcome=packet['simulation_outcome']
        self.assertTrue(outcome['deterministic'])
        self.assertIn('Morrowglass',outcome['campaign_result']['text'])
        self.assertEqual(self.memory['campaign']['contacts']['sister_cairn']['trust'],1)
        self.talk('sister_cairn','ships')
        self.assertEqual(self.memory['campaign']['contacts']['sister_cairn']['trust'],1)
        self.assertTrue(verify_ledger(self.memory))

    def test_mir_speech_requires_existing_deliberate_activation(self):
        before=copy.deepcopy(self.memory)
        with self.assertRaises(CampaignError):self.talk('mirror_instance','first_contact')
        self.assertEqual(before,self.memory)
        Engine(self.mod,self.memory).step('I activate Mir')
        self.assertEqual(self.memory['world_state']['mirror_payload_status'],'sealed_pristine')
        with self.assertRaises(CampaignError):self.talk('mirror_instance','first_contact')
        Engine(self.mod,self.memory).step('I confirm Mir activation')
        self.talk('mirror_instance','first_contact')
        self.assertTrue(self.memory['campaign']['flags']['mir_consulted'])

    def test_distinct_courier_responses_are_persistent_and_do_not_move_ships(self):
        before_time=self.memory['world_state']['world_time_minutes']
        def resolve(engine,assessment):
            r=dict(SUCCESS,target_id=assessment.get('target_id'))
            if r['target_id']=='sister_cairn':r.update(success=False,degree='partial_success',uniform_draw=.9)
            return r
        with patch.object(Engine,'_resolve_check',resolve):
            packet=self.act({'kind':'propose_cooperation','policy':'emergency_comms','npc_ids':['ren_ivo','sister_cairn','mara_ves']})
        responses=packet['simulation_outcome']['campaign_result']['responses']
        self.assertEqual([r['status'] for r in responses],['agreed','conditional','agreed'])
        self.assertTrue(self.memory['campaign']['contacts']['ren_ivo']['emergency_comms'])
        self.assertFalse(self.memory['campaign']['contacts']['sister_cairn']['emergency_comms'])
        self.assertEqual(self.memory['world_state']['location'],'cislunar_exchange')
        self.assertEqual(self.memory['world_state']['world_time_minutes'],before_time+15)
        self.assertEqual(self.memory['world_state']['mirror_activation_count'],0)

    def test_scene_rewards_cannot_repeat_with_a_new_key(self):
        self.stage('earth_escape_gate')
        starting=self.memory['economy']['credits']
        with patch.object(Engine,'_resolve_check',return_value=SUCCESS):self.choose('gate_burn','reconcile')
        self.assertEqual(self.memory['economy']['credits'],starting+180)
        before=copy.deepcopy(self.memory)
        with self.assertRaises(CampaignError):self.choose('gate_burn','reconcile')
        self.assertEqual(before,self.memory)

    def test_evidence_requires_playing_the_available_scene(self):
        self.stage('perihelic_shelter',40)
        self.assertNotIn('quorum_record',self.memory['campaign']['evidence'])
        self.choose('shelter_archive','verify')
        self.assertIn('quorum_record',self.memory['campaign']['evidence'])
        self.assertEqual(self.memory['quests']['main_fourth_reason']['status'],'completed')

    def test_optional_redoubt_unlocks_real_existing_travel_routes(self):
        self.stage('perihelic_shelter',40)
        self.assertNotIn('redoubt_asteroid',self.memory['travel_state']['known_nodes'])
        self.choose('shelter_invoice','verify')
        self.assertIn('redoubt_asteroid',self.memory['travel_state']['known_nodes'])
        self.assertIn('shelter_redoubt',self.memory['travel_state']['known_routes'])

    def test_resource_shortfall_and_wrong_location_are_atomic(self):
        self.stage('nacre_station',12)
        self.memory['economy']['inventory']['coolant_pack']=0
        before=copy.deepcopy(self.memory)
        with self.assertRaises(CampaignError):self.choose('courier_rescue','assist')
        self.assertEqual(before,self.memory)
        with self.assertRaises(CampaignError):self.choose('wrong_inspectors','deny')
        self.assertEqual(before,self.memory)

    def test_deadline_expiry_has_an_authored_nonfatal_consequence(self):
        self.stage('venus_tangent',20)
        record=self.memory['campaign']['scene_records']['medical_crisis']
        self.memory['world_state']['world_time_minutes']=record['deadline']+1
        changes=sync_campaign(self.mod,self.memory)
        self.assertEqual(record['status'],'expired')
        self.assertTrue(any(c['kind']=='missed_window' for c in changes))
        with self.assertRaises(CampaignError):self.choose('medical_crisis','kit')

    def test_all_six_ending_paths_and_payload_custody(self):
        for choice_id,ending,awake,mara in [('baseline','pristine_seed',False,False),('divergent','mir_of_morrowglass',True,False),
                ('commons','open_sun',False,False),('plural','plural_mirrors',False,True),
                ('pause','sealed_away',False,False),('continue','unfinished_delivery',False,False)]:
            with self.subTest(ending=ending):
                self.memory=new_memory(self.mod,'ending-'+ending)
                if awake:
                    Engine(self.mod,self.memory).step('I activate Mir')
                    Engine(self.mod,self.memory).step('I confirm Mir activation')
                self.stage('caloris_terminus',56)
                self.choose('caloris_reception','register')
                if mara:self.talk('mara_ves','provenance')
                before_money=self.memory['economy']['credits']
                with patch.object(Engine,'_resolve_check',return_value=SUCCESS):self.choose('acceptance_hearing',choice_id)
                state=self.memory['campaign']
                self.assertEqual(state['ending'],ending)
                self.assertTrue(verify_ledger(self.memory))
                if ending!='unfinished_delivery':
                    self.assertEqual(self.memory['economy']['credits'],before_money+8000)
                    self.assertEqual(self.memory['quests']['main_delivery']['status'],'completed')
                    self.assertEqual(self.memory['world_state']['mirror_custody'],'caloris_receiving_authority')
                    if not awake:
                        with self.assertRaises(CampaignError):Engine(self.mod,self.memory).step('I activate Mir')
                else:
                    self.assertIsNone(state['payload_receipt'])
                    self.assertEqual(state['status'],'ongoing')

    def test_reported_arrival_is_not_itself_a_verified_share(self):
        self.stage('caloris_terminus',56)
        self.assertTrue(all(not v['share_verified'] for v in self.memory['campaign']['arrivals'].values()))
        with self.assertRaises(CampaignError):self.choose('acceptance_hearing','commons')
        self.choose('caloris_reception','register')
        self.assertTrue(all(v['share_verified'] for v in self.memory['campaign']['arrivals'].values()))

    def test_live_schema_bridge_preview_execution_and_retry(self):
        self.memory['github_publication']={'repository':'Aggredicus/Phenomenal-Engine','branch':'campaign-saves',
            'path':'campaigns/campaign_fixture.json','public':True,'agreement_sha256':covenant_digest()}
        raw=json.dumps(self.memory)
        req={'campaign_id':'campaign_fixture','mod_id':'mirror_delivery','expected_state_version':0,
             'expected_blob_sha':git_blob_sha(raw.encode()),'save_json':raw,'action':'I ask Cairn about the ships',
             'idempotency_key':'talk-1','campaign_command':{'kind':'talk','npc_id':'sister_cairn','topic_id':'ships'}}
        preview=propose_turn(dict(req,operation='preview'))
        proposal=propose_turn(dict(req,expected_campaign_sha256=preview['campaign_quote']['quote_sha256'],expected_adjudication_sha256=preview['adjudication_sha256']))
        retry=dict(req,expected_state_version=1,expected_blob_sha=proposal['proposed_blob_sha'],save_json=proposal['proposed_save_json'])
        self.assertEqual(propose_turn(retry)['status'],'duplicate')
        with self.assertRaisesRegex(TurnExchangeError,'different campaign'):
            propose_turn(dict(retry,campaign_command={'kind':'talk','npc_id':'ren_ivo','topic_id':'history'}))

    def test_full_route_to_a_governed_ending_has_persistable_history(self):
        def travel(destination):
            Engine(self.mod,self.memory).step('I travel to '+destination,adjudication={
                'mode':'automatic','task':'routine_movement','reason':'Confirmed available authored route'})
        self.choose('custody_brief','review')
        self.talk('juno_arel','home')
        travel('Earth Escape Gate')
        self.choose('gate_burn','request_log');self.choose('gate_insurer','clarify')
        Engine(self.mod,self.memory).step('Service the ship',economy_command={'kind':'service','service_id':'full_service','expected_price':1100})
        travel('Nacre Station')
        self.choose('nacre_union','listen');self.choose('nacre_open_sun','defer');self.choose('pax_colleague','respect')
        self.choose('nav_corruption','pax');self.choose('courier_rescue','relay')
        travel('Perihelic Shelter Nine')
        self.choose('shelter_archive','verify');self.choose('shelter_invoice','archive');self.choose('wrong_inspectors','deny')
        travel('Mercury High Orbit')
        self.choose('mercury_audit','outer_audit');self.choose('mercury_disclosure','testimony')
        travel('Caloris Terminus');self.choose('caloris_reception','register')
        with patch.object(Engine,'_resolve_check',return_value=SUCCESS):self.choose('acceptance_hearing','commons')
        self.assertEqual(self.memory['campaign']['ending'],'open_sun')
        self.assertTrue(verify_ledger(self.memory))
        raw=encode_state(self.memory)
        loaded=decode_state(raw)
        self.assertEqual(loaded['event_ledger'],self.memory['event_ledger'])
        self.assertEqual(loaded['campaign']['ending'],'open_sun')

    def test_typed_prose_cannot_trigger_or_arm_mir(self):
        for prose in ['I activate Mir while asking Cairn', 'I confirm Mir activation while asking Cairn']:
            Engine(self.mod,self.memory).step(prose,campaign_command={
                'kind':'talk','npc_id':'sister_cairn','topic_id':'ships'})
            self.assertEqual(self.memory['world_state']['mirror_payload_status'],'sealed_pristine')
            self.assertEqual(self.memory['world_state']['mirror_activation_count'],0)
            self.assertEqual(self.memory['world_state']['mirror_activation_stage'],'unarmed')

    def test_legacy_inspection_and_first_turn_preserve_history(self):
        self.memory.pop('campaign')
        old_ledger=copy.deepcopy(self.memory['event_ledger'])
        before=copy.deepcopy(self.memory)
        view=campaign_view(self.mod,self.memory)
        self.assertTrue(view['initialization_pending'])
        self.assertEqual(self.memory,before)
        self.talk('sister_cairn','ships')
        self.assertEqual(self.memory['event_ledger'][:-1],old_ledger)
        self.assertEqual(self.memory['world_state']['world_time_minutes'],10)
        self.assertTrue(verify_ledger(self.memory))

    def test_commands_cannot_inject_effects_or_mix_transactions(self):
        before=copy.deepcopy(self.memory)
        for command in [{'kind':[]}, {'kind':'talk','npc_id':'sister_cairn','topic_id':'ships','effects':{'credits_gain':9999}}]:
            with self.assertRaises(CampaignError):self.act(command)
        with self.assertRaises(ValueError):
            Engine(self.mod,self.memory).step('Two commands',campaign_command={'kind':'talk','npc_id':'sister_cairn','topic_id':'ships'},economy_command={})
        self.assertEqual(self.memory,before)

    def test_profiles_validate_dialogue_effects_and_requirements(self):
        for effects in [{'ship':{'mirror_activation_count':1}}, {'credits_gain':-1}, {'ship':{'crew_trust':float('nan')}}]:
            profile=load_profile(self.mod)
            profile['dialogues']['sister_cairn']['ships']['effects']=effects
            with self.assertRaises(CampaignError):validate_profile(profile)
        profile=load_profile(self.mod)
        profile['scenes']['custody_brief']['requires']={'unknown_condition':True}
        with self.assertRaises(CampaignError):validate_profile(profile)

    def test_hearing_failure_preserves_provenance_and_awards_once(self):
        self.stage('caloris_terminus',56)
        self.choose('caloris_reception','register')
        fail=dict(SUCCESS,success=False,degree='failure',uniform_draw=.99)
        with patch.object(Engine,'_resolve_check',return_value=fail):self.choose('acceptance_hearing','commons')
        self.assertEqual(self.memory['campaign']['ending'],'sealed_away')
        self.assertEqual(self.memory['campaign']['payload_receipt']['payload_state'],'sealed_pristine')
        self.assertEqual(self.memory['quests']['main_mercury_hearing']['status'],'completed')
        before=copy.deepcopy(self.memory)
        with self.assertRaises(CampaignError):self.choose('acceptance_hearing','pause')
        self.assertEqual(self.memory,before)

    def test_all_authored_choices_execute_at_valid_prerequisites(self):
        profile=load_profile(self.mod)
        for scene_id,scene in profile['scenes'].items():
            for choice_id,choice in scene['choices'].items():
                for degree,success in [('success',True),('partial_success',False),('failure',False)]:
                    with self.subTest(scene=scene_id,choice=choice_id,degree=degree):
                        self.memory=new_memory(self.mod,'branch-fixture')
                        requires={**scene.get('requires',{}),**choice.get('requires',{})}
                        if requires.get('awake'):
                            Engine(self.mod,self.memory).step('I activate Mir')
                            Engine(self.mod,self.memory).step('I confirm Mir activation')
                        state=self.memory['campaign']
                        state['flags'].update({k:True for k in requires.get('flags',[])})
                        if requires.get('divergent_copy'):state['flags']['mara_divergent']=True
                        for key in requires.get('evidence',[]):state['evidence'][key]={'id':key,**profile['evidence'][key]}
                        self.stage(scene['locations'][0],56 if scene['act']==5 else 20)
                        if requires.get('quorum'):
                            for arrival in state['arrivals'].values():arrival['share_verified']=True
                        result=dict(SUCCESS,success=success,degree=degree)
                        with patch.object(Engine,'_resolve_check',return_value=result):
                            packet=self.choose(scene_id,choice_id)
                        self.assertEqual(packet['simulation_outcome']['campaign_result']['choice_id'],choice_id)
                        self.assertTrue(verify_ledger(self.memory))


if __name__=='__main__':unittest.main()
