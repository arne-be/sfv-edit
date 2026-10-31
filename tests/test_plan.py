import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from plan import PlanError, check, parse  # noqa: E402

PLAN = '''# T
style: default
## Hook!
c1 6.30-10.70 | Five years ago, my hometown had the biggest flood
- zoom 1.3 cx=0.5
- caption-lead "five *years* ago" @five ..ago
- photo-stack a.jpg@biggest b.jpg @hometown ..sec from=2
~~c1 11.52-13.12 | and we were hit.~~ (repeat)
> note
'''


class Plan(unittest.TestCase):
    def test_parse(self):
        p = parse(PLAN)
        sec = p['sections'][0]
        self.assertEqual(sec['name'], 'hook')
        kept, cut = sec['segs']
        self.assertEqual((kept['id'], kept['in'], kept['out'], kept['cut']), ('hook_0', 6.3, 10.7, False))
        self.assertEqual((cut['id'], cut['cut'], cut['text'], cut['reason']), ('hook_1', True, 'and we were hit.', 'repeat'))
        z, cap, ps = kept['fx']
        self.assertEqual(z['params'], {'zoom': 1.3, 'cx': '0.5'})
        self.assertEqual((cap['text'], cap['at'], cap['until']), ('five *years* ago', 'five', 'ago'))
        self.assertEqual(ps['media'], [{'file': 'a.jpg', 'at': 'biggest'}, {'file': 'b.jpg', 'at': None}])
        self.assertEqual((ps['at'], ps['until'], ps['params']), ('hometown', 'sec', {'from': '2'}))

    def test_errors(self):
        with self.assertRaises(PlanError):
            parse('## a\nc1 1-2 | hi\n- wobble')
        with self.assertRaises(PlanError):
            parse('## a\nc1 1-2 | hi\n- pip')
        errs = check(parse('## a\nc1 1-2 | hello there\n- blur-pop "x" @nope'), '/nonexistent')
        self.assertTrue(any("anchor 'nope'" in e for e in errs))


if __name__ == '__main__':
    unittest.main()
