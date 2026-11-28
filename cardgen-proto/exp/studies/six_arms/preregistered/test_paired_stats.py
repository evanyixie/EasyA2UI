"""仅用合成摘要及二元结局，验证 §4 的家族配对统计。"""

import itertools
import unittest

from paired_stats import analyze_pairs, holm_adjust


def cases(entries):
    return [{"family": f, "input_sha256": f"{i:064x}", "left": l, "right": r}
            for i, (f, l, r) in enumerate(entries, 1)]


def run(entries, **kwargs):
    return analyze_pairs(cases(entries), boot_reps=400, perm_reps=4000, **kwargs)


class PairedStatistics(unittest.TestCase):
    def test_all_nine_possible_pairs_and_sharp_bounds(self):
        choices = [False, True, None]
        for left, right in itertools.product(choices, repeat=2):
            with self.subTest(left=left, right=right):
                result = run([("a", left, right)])
                possible = [r - l for l, r in itertools.product((False, True), repeat=2)
                            if left in (None, l) and right in (None, r)]
                self.assertEqual(result["effect_bounds"], [min(possible), max(possible)])
                if left is None or right is None:
                    for key in ("effect", "cluster_bootstrap", "family_permutation", "representative_mcnemar"):
                        self.assertIsNone(result[key])

    def test_joint_and_separate_missing_keep_original_denominator(self):
        result = run([("a", None, True), ("a", False, None), ("b", None, None), ("c", True, False)])
        self.assertEqual((result["n_total"], result["n_known"], result["n_unknown"]), (4, 1, 3))
        self.assertEqual(result["coverage"], .25)
        self.assertEqual(result["missing_pattern"], {"both": 1, "left_only": 1, "right_only": 1})
        self.assertEqual(result["paired_table"], {"both_fail": 0, "right_only": 0, "left_only": 1, "both_pass": 0})
        self.assertEqual(result["effect_bounds"], [-.5, .5])
        self.assertEqual(result["inference_status"], "incomplete_endpoints")

    def test_group_resampling_family_weighting_and_representative_hash(self):
        raw = cases([("a", False, True)] * 3 + [("b", True, False)])
        r = analyze_pairs(raw, boot_reps=600, perm_reps=1000, seed=4)
        self.assertEqual(r["effect"], .5)
        self.assertEqual(r["representative_mcnemar"]["effect"], 0)
        self.assertEqual(r["cluster_bootstrap"]["ci95"], [-1, 1])
        self.assertEqual(r["family_permutation"]["p_two_sided"], 1)
        # 同一家族大小不等，重采样一次抽整个家族；家族交换只能产生 ±2 或 ±4。
        self.assertEqual(r["family_permutation"]["extreme"], 1000)
        r2 = run([("a", False, True), ("a", True, False), ("b", False, True), ("c", False, True)])
        self.assertEqual(r2["representative_mcnemar"]["p_exact_two_sided"], .25)
        raw = cases([("a", True, False), ("a", False, True)])
        raw[1]["input_sha256"] = "0"*64
        r3 = analyze_pairs(raw, boot_reps=10, perm_reps=20)
        self.assertEqual(r3["representative_mcnemar"]["paired_table"]["right_only"], 1)

    def test_reversal_order_invariance_fixed_seed_and_plus_one(self):
        raw = cases([("d", False, True), ("a", False, True), ("d", False, True),
                     ("z", True, False), ("y", True, True)])
        opts = {"boot_reps": 201, "perm_reps": 513, "seed": 101}
        result = analyze_pairs(raw, **opts)
        self.assertEqual(result, analyze_pairs(reversed(raw), **opts))
        swapped = analyze_pairs([{**r, "left": r["right"], "right": r["left"]} for r in raw], **opts)
        self.assertEqual(swapped["effect"], -result["effect"])
        self.assertEqual(swapped["family_permutation"], result["family_permutation"])
        for a,b in zip(swapped["cluster_bootstrap"]["ci95"], reversed(result["cluster_bootstrap"]["ci95"])):
            self.assertAlmostEqual(a, -b)
        perm = result["family_permutation"]
        self.assertEqual(perm["p_two_sided"], (perm["extreme"]+1)/514)
        self.assertGreater(perm["p_two_sided"], 0)
        self.assertLess(perm["p_two_sided"], 1)

    def test_zero_difference_with_no_evidence_of_precision(self):
        result = run([("a", False, False), ("b", True, True), ("b", False, False)])
        self.assertEqual(result["effect"], 0)
        self.assertEqual(result["representative_mcnemar"]["p_exact_two_sided"], 1)
        self.assertEqual(result["family_permutation"]["p_two_sided"], 1)
        self.assertEqual(result["cluster_bootstrap"]["empirical_percentiles"], [0, 0])
        self.assertIsNone(result["cluster_bootstrap"]["ci95"])
        self.assertEqual(result["cluster_bootstrap"]["precision_status"], "constant_observed_family_effect")
        single = run([("only", False, True), ("only", True, False)])
        self.assertEqual(single["cluster_bootstrap"]["precision_status"], "single_observed_family")

    def test_invalid_or_duplicate_input_even_across_families(self):
        a = cases([("a", False, True)])[0]
        a["input_sha256"] = "ab"*32
        with self.assertRaisesRegex(ValueError, "重复"):
            analyze_pairs([a, {**a, "family": "other", "input_sha256": a["input_sha256"].upper()}])
        for bad in ([], [{**a, "left": 0}], [{**a, "family": ""}], [{**a, "input_sha256": "abc"}]):
            with self.assertRaises(ValueError):
                analyze_pairs(bad)
        with self.assertRaises(ValueError):
            analyze_pairs([a], perm_reps=0)

    def test_four_prespecified_secondary_tests_and_missing(self):
        self.assertEqual(holm_adjust([.03, .01, .04, .2]), [.09, .04, .09, .2])
        result = holm_adjust([None, .01, .03, .8])
        self.assertEqual(result, [None, .04, .09, 1])
        self.assertEqual(holm_adjust([None, None, None, None]), [None]*4)
        self.assertEqual(holm_adjust([None, 0, 1, None]), [None, 0, 1, None])
        for bad in ([.1, .2, .3], [True, .1, .4, None], [float("nan"), None, None, None]):
            with self.assertRaises(ValueError):
                holm_adjust(bad)


if __name__ == "__main__":
    unittest.main()
