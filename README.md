# BEAGLE_HOLO
code for implementing the BEAGLE model by Mewhort and Jones (2007), in addition to alternative binding approach, using Random Permutaitons (Sahlgren, Holst, & Kanerva, 2008).


More specifically, the code was used to construct vectors for the following paper...

Global semantic similarity effects in recognition memory: Insights from BEAGLE representations and the diffusion decision model
Adam F Osth Andrew Heathcote Douglas Mewhort Kevin Shabahang 


...

Note that parts of the code may be redundant due to change of approach.  For instance, instead of shifting vectors on-the-fly when binding via random permutations, I later changed the code so that we pre-compute the permutation vectors and use Numpy's vector indexing approach to speed up the process.  I have tested the code against typical examples to ensure correctness, but perhaps you'll notice something that I missed.
