import unittest
import importlib.util
import numpy as np

TORCH_AVAILABLE=importlib.util.find_spec("torch") is not None


@unittest.skipUnless(TORCH_AVAILABLE,"Install the optional training dependencies")
class TrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        torch.set_num_threads(2)

    def test_numpy_float_matches_torch_both_geometries(self):
        import torch
        from fashionlenet.model import LeNet
        from fashionlenet.reference import float_infer
        for size in [28,32]:
            torch.manual_seed(23)
            net=LeNet(size,(3,4,5,6)).eval()
            x=np.random.default_rng(4).random((2,1,size,size)).astype(np.float32)
            model={"layers":[{"weight":l.weight.detach().numpy(),"bias":l.bias.detach().numpy()} for l in net.weighted_layers()]}
            with torch.inference_mode():z=net(torch.from_numpy(x)).numpy()
            np.testing.assert_allclose(float_infer(model,x),z,rtol=1e-5,atol=1e-6)

    def test_unstructured_exact_count_and_bias_preservation(self):
        import torch
        from fashionlenet.model import LeNet
        from fashionlenet.pruning import unstructured,statistics
        torch.manual_seed(1);net=LeNet()
        result,masks=unstructured(net,0.7)
        s=statistics(result)
        self.assertEqual(s["nonzero_weights"],s["weight_parameters"]-int(0.7*s["weight_parameters"]))
        for a,b,mask in zip(net.weighted_layers(),result.weighted_layers(),masks):
            torch.testing.assert_close(a.bias,b.bias)
            torch.testing.assert_close(b.weight,a.weight*mask)
        self.assertEqual(statistics(net)["weight_sparsity"],0)

    def test_structural_surgery_all_requested_rates(self):
        import torch
        from fashionlenet.model import LeNet
        from fashionlenet.pruning import structured,statistics
        net=LeNet(28)
        old=statistics(net)["stored_parameters"]
        for f in [0.25,0.5,0.7,0.9,0.95,0.97,0.99]:
            result=structured(net,f)
            expected=tuple(max(1,int(np.ceil(round(c*(1-f),12)))) for c in net.channels)
            self.assertEqual(result.channels,expected)
            self.assertEqual(result(torch.zeros(2,1,28,28)).shape,(2,10))
            self.assertLess(statistics(result)["stored_parameters"],old)
        self.assertEqual(structured(net,0.95).channels,(1,1,6,5))

    def test_calibration_uses_integer_datapath(self):
        import torch
        from fashionlenet.model import LeNet
        from fashionlenet.quant import calibrate
        from fashionlenet.reference import infer
        torch.manual_seed(3);net=LeNet(32,(2,3,4,5))
        x=np.random.default_rng(5).random((3,1,32,32)).astype(np.float32)
        q=calibrate(net,x)
        p,z,traces=infer(q,x,True)
        self.assertEqual(p.shape,(3,))
        self.assertEqual(z.dtype,np.int8)
        for layer in q["layers"]:
            self.assertEqual(layer["weight"].dtype,np.int8)
            self.assertEqual(layer["bias"].dtype,np.int32)
            self.assertTrue(0<=layer["shift"]<=31)
        self.assertTrue(np.issubdtype(traces["conv1_acc"].dtype,np.integer))


if __name__=="__main__":unittest.main()
