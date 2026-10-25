import unittest
from pathlib import Path
import tempfile
import numpy as np
from fashionlenet.reference import conv2d,pool2d,requantize,infer,float_infer
from fashionlenet.quant import demo_model,save,load,pot_scale,round_away
from fashionlenet.export import export_bundle
from fashionlenet.sim import simulate_bundle,Memory


class ReferenceTests(unittest.TestCase):
    def test_scalar_convolution_oracle(self):
        rng=np.random.default_rng(19)
        x=rng.integers(-128,128,(2,3,5,6),dtype=np.int16).astype(np.int8)
        w=rng.integers(-128,128,(4,3,2,3),dtype=np.int16).astype(np.int8)
        b=rng.integers(-500,500,4)
        z=conv2d(x,w,b)
        for n in range(2):
            for o in range(4):
                for y in range(4):
                    for xx in range(4):
                        expected=int(b[o])
                        for c in range(3):
                            for ky in range(2):
                                for kx in range(3):expected+=int(x[n,c,y+ky,xx+kx])*int(w[o,c,ky,kx])
                        self.assertEqual(int(z[n,o,y,xx]),expected)

    def test_rounding_signed_extremes(self):
        np.testing.assert_array_equal(requantize(np.array([-7,-5,-3,-1,1,3,5,7]),1,False),[-4,-3,-2,-1,1,2,3,4])
        np.testing.assert_array_equal(requantize(np.array([-2**31,2**31-1]),31,False),[-1,1])
        np.testing.assert_array_equal(requantize(np.array([-1000,-1,0,1000]),0,True),[0,0,0,127])
        with self.assertRaises(OverflowError):requantize(np.array([2**31]),0,False)
        with self.assertRaises(ValueError):requantize(np.array([0]),32,False)

    def test_pool_signed(self):
        x=np.array([[[[-7,-2,8,7],[-9,-4,1,2],[1,4,-2,-1],[2,3,-3,-4]]]],np.int8)
        np.testing.assert_array_equal(pool2d(x),np.array([[[[-2,8],[4,-1]]]]))

    def test_pot_scales(self):
        for value in [0,1e-6,0.1,1,4,100]:
            scale=pot_scale(value)
            self.assertEqual(np.log2(scale),int(np.log2(scale)))
            self.assertGreaterEqual(scale*127,value)
        np.testing.assert_array_equal(round_away([-1.5,-0.5,0.5,1.5]),[-2,-1,1,2])

    def test_portable_model_round_trip(self):
        m=demo_model(input_size=28,channels=(2,3,4,5))
        x=np.random.default_rng(9).integers(0,128,(1,1,28,28),dtype=np.int8)
        with tempfile.TemporaryDirectory() as d:
            save(m,Path(d)/"m.npz")
            loaded=load(Path(d)/"m.npz")
            np.testing.assert_array_equal(infer(m,x)[1],infer(loaded,x)[1])

    def test_export_layout_and_budget(self):
        m=demo_model(input_size=32,channels=(1,2,3,4))
        with tempfile.TemporaryDirectory() as d:
            manifest=export_bundle(m,np.zeros((1,1,32,32),np.int8),d)
            mem=np.array([int(t,16) for t in (Path(d)/"memory.hex").read_text().split()],np.uint8)
            weights=np.concatenate([l["weight"].ravel().view(np.uint8) for l in m["layers"]])
            np.testing.assert_array_equal(mem[:len(weights)],weights)
            bbytes=np.concatenate([l["bias"].astype("<i4").view(np.uint8) for l in m["layers"]])
            np.testing.assert_array_equal(mem[len(weights):len(weights)+len(bbytes)],bbytes)
            self.assertEqual(manifest["dense_macs"],24802)
            dense=simulate_bundle(d,2,3,False,1,False)
            sparse=simulate_bundle(d,2,3,False,1,True)
            self.assertEqual(dense["cycles"],sparse["cycles"])
            self.assertEqual(dense["mac_attempted"],manifest["dense_macs"])
            self.assertLessEqual(sparse["mac_executed"],dense["mac_executed"])

    def test_cache_conflict_and_coherence(self):
        m=Memory(np.arange(81920,dtype=np.uint32).astype(np.uint8),True,4)
        self.assertEqual(m.read(128),128);self.assertEqual(m.read(129),129)
        self.assertEqual((m.hits,m.misses),(1,1))
        self.assertEqual(m.cycles,100)
        m.read(1152);self.assertEqual(m.misses,2)
        m.write(128,7);self.assertEqual(m.read(128),7)

    def test_export_rejects_activation_bank_overflow(self):
        m=demo_model(channels=(100,1,1,1))
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"8 KiB"):
                export_bundle(m,np.zeros((1,1,32,32),np.int8),d)


if __name__=="__main__":unittest.main()
