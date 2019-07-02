from GeneralVSAModel import Model
import numpy as np
#import torch
from copy import deepcopy
from progressbar import ProgressBar
import sys
import pickle

def cconv(a, b):
    '''
    Computes the circular convolution of the (real-valued) vectors a and b.
    '''
    return np.fft.ifft(np.fft.fft(a) * np.fft.fft(b)).real

def ccorr(a, b):
    '''
    Computes the circular correlation (inverse convolution) of the real-valued
    vector a with b.
    '''
    return cconv(np.roll(a[::-1], 1), b)


class BEAGLE_HOLO(Model):
    def __init__(self, params, hparams, QaAs=None, E=None, vocab = None):
        super(BEAGLE_HOLO, self).__init__(hparams, QaAs)

        self.params = params

        ###initialize environment vectors
        if type(E) == list:
            self.E = E
            self.C = np.zeros((len(E), hparams["NFEATs"]))
            self.O = np.zeros((len(E), hparams["NFEATs"]))
        else:
            self.E = []
            self.C = []
            self.O = []
        if type(vocab) == list:
            for i in xrange(len(vocab)):
                self.vocab.append(vocab[i])
                self.I[vocab[i]] = i
        else:
            self.vocab = []
        ###initialize context vectors
        ###initialize order vectors
        self.N      = hparams["NFEATs"]
        self.SD     = 1.0/np.sqrt(self.N)

        f = open("../rsc/STOPLIST.txt", "r")
        STOPLIST = f.readlines()
        f.close()
        self.STOPLIST = [STOPLIST[i].strip() for i in xrange(len(STOPLIST))]

        self.PHI = np.random.normal(0.0, self.SD, self.N)
        perm    = np.array([i for i in xrange(self.N)])
        np.random.shuffle(perm)
        self.p1 = deepcopy(perm)
        np.random.shuffle(perm)
        self.p2 = deepcopy(perm)

#        self.E1_map = dict(zip([i for i in xrange(self.N)], np.random.permutation(self.N)))
#        self.E2_map = dict(zip([i for i in xrange(self.N)], np.random.permutation(self.N)))
#        self.D1_map = {self.E1_map[i]:i for i in xrange(self.N)} 
#        self.D2_map = {self.E2_map[i]:i for i in xrange(self.N)}
#    
#        self.E1 = lambda a : np.array([a[self.E1_map[i]] for i in xrange(self.N)])
#        self.E2 = lambda a : np.array([a[self.E2_map[i]] for i in xrange(self.N)])
#        self.D1 = lambda a : np.array([a[self.D1_map[i]] for i in xrange(self.N)])
#        self.D2 = lambda a : np.array([a[self.D2_map[i]] for i in xrange(self.N)])


    def bind(self, a, b):
        return cconv(a[self.p1], b[self.p2])

    def update_vocab(self, corpus_process):
        N  = self.N
        SD = self.SD
        corpus_process = corpus_process.split()

        for i in xrange(len(corpus_process)):
            if corpus_process[i] in self.I:
                self.wf[corpus_process[i]] += 1
            elif corpus_process[i] != '_':
                self.I[corpus_process[i]] = len(self.vocab)
                self.vocab.append(corpus_process[i])
                self.wf[corpus_process[i]] = 1
                ###construct environment vector
                self.E.append(np.random.normal(0.0, SD, N))
                self.C.append(np.zeros(N))
                self.O.append(np.zeros(N))
        self.V = len(self.vocab)

    def learn_context(self, window):
        '''we assume window is string of tokens, each already in the vocabulary'''
        window = window.split()
        N = self.N
        I = self.I
        WINDOW_LIM = self.hparams["CONTEXT_WINDOW"] + 1
        for i in xrange(len(window)):
            if window[i] not in self.STOPLIST:
                wi = window[i]
                for j in xrange(len(window)):
                    if j != i and window[j] not in self.STOPLIST and np.abs(i - j) < WINDOW_LIM:
                        wj = window[j]
                        self.C[I[wi]] += self.E[I[wj]]

    def learn_order(self, window):
        '''we assume window is a string of tokens, each already in the vocabulary'''
        window = window.split()
        I = self.I
        for i in xrange(len(window)):
            wi = window[i]
            self.O[I[wi]] += self.RP_bind(window, i)

    def RP_bind(self, window, i):
        o = np.zeros(self.N)
        I = self.I
        WINDOW_LIM = self.hparams["ORDER_WINDOW"] + 1
        for j in xrange(len(window)):
            if WINDOW_LIM > j - i > 0:
                o += self.perm_n(self.E[I[window[j]]], j-i ) #forward associations
            elif -WINDOW_LIM < j - i < 0:
                o += self.invperm_n(self.E[I[window[j]]], i - j)
        return o



    def normalize_context(self):
        for i in xrange(len(self.C)):
            vlen = np.linalg.norm(self.C[i])
            if vlen > 0:
                self.C[i] = self.C[i]/vlen  



    def normalize_order(self):
        for i in xrange(len(self.O)):
            vlen = np.linalg.norm(self.O[i])
            if vlen > 0:
                self.O[i] = self.O[i]/vlen  



    def compute_lexicon(self):
        '''combines context and order information
           assumes context and order vectors have been normalized'''
        I = self.I
        M = []
        for i in xrange(self.V):
            v = self.C[i] + self.O[i]
            vlen = np.linalg.norm(v)
            if vlen > 0:
                v = v/vlen
            M.append(v)
        self.M = M

    def sim_context(self, w):
        I = self.I
        if type(w) == str and w in self.vocab:
            v = self.C[I[w]]
        elif type(w) == np.ndarray:
            v = w
        else:
            print "ERROR: the token, {}, is not known".format(w)
            return -1

        strengths = sorted(zip(map(lambda u : np.dot(u, v), self.C), self.vocab))[::-1]
        for i in xrange(10):
            print round(strengths[i][0], 7), strengths[i][1]
        return strengths

    def perm_n(self, x, n):
        y = np.zeros(self.N)
        for i in xrange(self.N):
            y[(i+n)%self.N] = x[i]
        return y

    def invperm_n(self, y, n):
        x = np.zeros(self.N)
        for i in xrange(self.N):
            x[(i-n)] = y[i]
        return x

    def sim_order(self, w, n=0):
        I = self.I
        if type(w) == str and w in self.vocab:
            v = self.O[I[w]]
        elif type(w) == np.ndarray:
            v = w
        else:
            print "ERROR: the token, {}, is not known".format(w)
            return -1

        if n < 0:
            v = self.perm_n(v, -n)
        if n > 0:
            v = self.invperm_n(v, n)

        strengths =  sorted(zip(map(lambda u : np.dot(u, v), self.O), self.vocab))[::-1]
        for i in xrange(10):
            print round(strengths[i][0], 7), strengths[i][1]

        return strengths

    def sim(self, w):
        I = self.I
        if type(w) == str and w in self.vocab:
            v = self.M[I[w]]
        elif type(w) == np.ndarray:
            v = w
        else:
            print "ERROR: the token, {}, is not known".format(w)
            return -1

        strengths = sorted(zip(map(lambda u : np.dot(u, v), self.M), self.vocab))[::-1]
        for i in xrange(10):
            print round(strengths[i][0], 7), strengths[i][1]

        return strengths

def open_npz(npzfile):
    return list(np.load(npzfile).items()[0][1])


if __name__ == "__main__":
    params = []
    hparams = {"NFEATs":1024,  "ORDER_WINDOW":5, "CONTEXT_WINDOW":50}

    toTest = False
    getOrder = True
    getContext= True
    ##load corpus
  



    idx = int(sys.argv[1]) #current chunk
    CHU = int(sys.argv[2]) #number of chunks
    MODE = sys.argv[3]
    if MODE == "run" or MODE == "compile":
        source = sys.argv[4] #source of vectors to compile
        


    if MODE == "init" or MODE == "train":
        corpus_path = sys.argv[4]

        f = open("{}".format(corpus_path), "r")
        corpus = f.readlines()
        f.close()
        L = len(corpus)/CHU

    if MODE == "init":
        corpus = [corpus[i].strip() for i in xrange(len(corpus))]
        vocab = list(set(" ".join(corpus).split()))
        E = []
        N = hparams["NFEATs"]
        SD = 1/np.sqrt(N)
        f = open("vocab.txt", "w")
        print "Generating environmental vectors..."
        pbar = ProgressBar(maxval=len(vocab)).start()
        for i in xrange(len(vocab)):
            E.append(np.random.normal(0, SD, N))
            f.write(vocab[i]+"\n")
            pbar.update(i+1)
        print "Dumping to disk..."
        np.savez_compressed("env.npz", np.array(E))


    elif MODE == "train":
        corpus = [corpus[i].strip() for i in xrange(len(corpus))][idx*L:(idx+1)*L]
        E = open_npz("../rsc/env.npz")

        f = open("../rsc/vocab.txt", "r")
        vocab = f.readlines()
        f.close()
        vocab = [vocab[i].strip() for i in xrange(len(vocab))]

        beagle = BEAGLE_HOLO(params, hparams, E = E, vocab = vocab)

        
        pbar = ProgressBar(maxval = len(corpus)).start()
        for i in xrange(len(corpus)):
            #beagle.update_vocab(corpus[i])
            if getContext:
                beagle.learn_context(corpus[i])
            if getOrder:
                beagle.learn_order(corpus[i])
            pbar.update(i+1)
        if getContext:
            beagle.normalize_context()
        if getOrder:
            beagle.normalize_order()
        if getContext and getOrder:
            beagle.compute_lexicon()

        if getContext:
            np.savez_copmressed("context_CHU{}.npz".format(idx), beagle.C)

        if getOrder:
            np.savez_compressed("order_ORD{}.npz".format(idx), beagle.O)


    elif MODE == "compile":        
        E = open_npz("../rsc/env.npz")

        f = open("../rsc/vocab.txt", "r")
        vocab = f.readlines()
        f.close()
        vocab = [vocab[i].strip() for i in xrange(len(vocab))]

        beagle = BEAGLE_HOLO(params, hparams, E = E, vocab = vocab)
        if getOrder:
            O = open_npz("../rsc/{}/order_ORD0.npz".format(source))

        if getContext:
            C = open_npz("../rsc/{}/context_CHU0.npz".format(source))
        
        if getOrder:
            print "Compiling order "
            pbar = ProgressBar(maxval = CHU).start()
            for i in xrange(1, CHU):
                Oi = open_npz("../rsc/{}/order_ORD{}.npz".format(source, i))
                for j in xrange(len(Oi)):
                    O[j] += Oi[j]
                pbar.update(i+1)

            np.savez_compressed("../rsc/{}/order.npz".format(source))



        if getContext:
            print "Compiling context "
            pbar = ProgressBar(maxval = CHU).start()
            Ci = open_npz("../rsc/{}/context_ORD{}.npz".format(source, i))
            for j in xrange(len(Oi)): 
                C[j] += Ci[j]
                pbar.update(i+1)

            np.savez_compressed("../rsc/{}/context.npz".format(source))
 
    elif MODE == "run":
         E = open_npz("../rsc/env.npz")



         f = open("../rsc/vocab.txt", "r")
         vocab = f.readlines()
         f.close()
         vocab = [vocab[i].strip() for i in xrange(len(vocab))]
 
         beagle = BEAGLE_HOLO(params, hparams, E = E, vocab = vocab)

         beagle.O = open_npz("../rsc/{}/order.npz".format(source))

         beagle.C = open_npz("../rsc/{}/context.pkl".format(source))

         beagle.normalize_order()
         beagle.normalize_context()


























