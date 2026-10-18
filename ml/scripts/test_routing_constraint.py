import unittest
from routing_codes import label_prefix_constraint

class RoutingTokenTests(unittest.TestCase):
    def test_only_classes_can_start(self):
        allowed=label_prefix_constraint([11,12,13],[99],2,2)
        self.assertEqual(allowed(0,[6,7]),[11,12,13])
        self.assertEqual(allowed(0,[6,7,12]),[11,13,99])
        self.assertEqual(allowed(0,[6,7,12,13]),[99])

    def test_single_label_and_bad_constraints(self):
        allowed=label_prefix_constraint([11,12],[99],1,1)
        self.assertEqual(allowed(0,[6,12]),[99])
        with self.assertRaises(ValueError):label_prefix_constraint([11],[11],1,2)

if __name__=='__main__':unittest.main()
