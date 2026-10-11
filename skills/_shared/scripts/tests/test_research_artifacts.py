import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('research_artifacts_test', Path(__file__).parents[1]/'research_context.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ArtifactChecks(unittest.TestCase):
    def setUp(self):
        self.record = {'schema_version':1,'feature_key':'OSAC-1','stage':'prd','run_id':'run-1',
            'research_mode':'replay','status':'available',
            'sources':[{'id':'S','url':'https://example.org/source','date':None,'revision':'r1','verification':'verified'}],
            'requirements':[{'id':'R1','statement':'Required behavior','scope':'in','source_ids':['S']}],
            'claims':[{'id':'C1','statement':'Prior decision','source_ids':['S'],'decision_state':'accepted'}],
            'conflicts':[],'questions':[]}
        self.coverage = {'schema_version':1,'feature_key':'OSAC-1','stage':'prd','run_id':'run-1',
            'requirements':[{'id':'R1','status':'covered','evidence':'Required behavior'}]}
        self.document = '# Example\n\n' + '\n\n'.join('## '+h+'\nRequired behavior' for h in [
            'Problem Statement','In Scope','Out of Scope','User Stories','Assumptions','Dependencies'])

    def check(self, **changes):
        args = {'record':self.record,'brief':'Evidence for run-1','document':self.document,'coverage':self.coverage,'forge_prd':True}
        args.update(changes)
        return module.check_artifacts(**args)

    def test_complete_artifacts_pass_mechanical_checks_only(self):
        result = self.check()
        self.assertTrue(result['valid'])
        self.assertTrue(result['ready_for_semantic_review'])
        self.assertTrue(result['semantic_review_required'])
        scaffold = module.coverage_template(self.record)
        self.assertEqual([], module.validate_coverage(scaffold, self.record))
        self.assertEqual('unresolved', scaffold['requirements'][0]['status'])
        self.assertFalse(self.check(coverage=scaffold)['ready_for_semantic_review'])

    def test_commentary_is_rejected_without_stripping(self):
        result = self.check(document='Now I will draft.\n\n'+self.document)
        self.assertFalse(result['valid'])
        self.assertIn('without commentary', ' '.join(result['errors']))

    def test_stale_coverage_and_missing_requirement_rejected(self):
        self.coverage['run_id']='previous-run'
        self.coverage['requirements']=[]
        self.assertFalse(self.check()['valid'])

    def test_missing_section_rejected(self):
        self.assertFalse(self.check(document=self.document.replace('## Dependencies','## Risks'))['valid'])

    def test_missing_and_unverified_citations_rejected(self):
        self.assertFalse(self.check(document=self.document+'\n[Chai:C1]')['valid'])
        self.record['sources'][0]['verification']='unverified'
        self.assertFalse(self.check(document=self.document+'\n[Chai:C1](https://example.org/source)')['valid'])

    def test_unresolved_requirement_blocks_promotion(self):
        self.coverage['requirements'][0]['status']='unresolved'
        result = self.check()
        self.assertTrue(result['valid'])
        self.assertFalse(result['ready_for_semantic_review'])

    def test_malformed_coverage_reports_error(self):
        for value in (None, [], {'requirements':None}):
            with self.subTest(value=value):
                self.assertFalse(self.check(coverage=value)['valid'])


if __name__ == '__main__':
    unittest.main()
