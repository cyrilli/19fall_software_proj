from fuzzingbook.myFuzzers.BoostedGreyboxFuzzer import BoostedGreyboxFuzzer
from fuzzingbook.myFuzzers.AdaptiveMutationBoostedGreyboxFuzzer import AdaptiveMutationBoostedGreyboxFuzzer
from fuzzingbook.myFuzzers.AdaptiveMutationAndSeedSelectionGreyboxFuzzer import AdaptiveMutationAndSeedSelectionGreyboxFuzzer

from fuzzingbook.MutationFuzzer import FunctionCoverageRunner
from fuzzingbook.Coverage import population_coverage
from html.parser import HTMLParser
import time
import matplotlib.pyplot as plt
import numpy as np
import codecs

# create wrapper function
def my_parser(inp):
    parser = HTMLParser()  # resets the HTMLParser object for every fuzz input
    parser.feed(inp)

if __name__ == "__main__":
    cov_b = []
    cov_a = []
    cov_aa = []
    f = codecs.open("./fuzzingbook/seeds/example_html.html",'r')
    seed_input = f.read()
    f.close()
    for i in range(1):
        n = 3000
        boostedGreyboxFuzzer = BoostedGreyboxFuzzer([seed_input])
        adaptiveMutationBoostedGreyboxFuzzer = AdaptiveMutationBoostedGreyboxFuzzer([seed_input])
        adaptiveMutationAndSeedSelectionGreyboxFuzzer = AdaptiveMutationAndSeedSelectionGreyboxFuzzer([seed_input])

        start = time.time()
        boostedGreyboxFuzzer.runs(FunctionCoverageRunner(my_parser), trials=n)
        end = time.time()
        print("It took the BoostedGreyboxFuzzer w/ exponential schedule %0.2f seconds to generate and execute %d inputs." % (end - start, n))

        start = time.time()
        adaptiveMutationBoostedGreyboxFuzzer.runs(FunctionCoverageRunner(my_parser), trials=n)
        end = time.time()
        print("It took the AdaptiveMutationBoostedGreyboxFuzzer w/ exponential schedule %0.2f seconds to generate and execute %d inputs." % (end - start, n))

        start = time.time()
        adaptiveMutationAndSeedSelectionGreyboxFuzzer.runs(FunctionCoverageRunner(my_parser), trials=n)
        end = time.time()
        print("It took the AdaptiveMutationAndSeedSelectionGreyboxFuzzer w/ exponential schedule %0.2f seconds to generate and execute %d inputs." % (end - start, n))

        #
        _, b_coverage = population_coverage(boostedGreyboxFuzzer.inputs, my_parser)
        # print(b_coverage)
        _, a_coverage = population_coverage(adaptiveMutationBoostedGreyboxFuzzer.inputs, my_parser)
        # print(a_coverage)
        _, a2_coverage = population_coverage(adaptiveMutationAndSeedSelectionGreyboxFuzzer.inputs, my_parser)
        # print(a2_coverage)
        cov_b.append(b_coverage)
        cov_a.append(a_coverage)
        cov_aa.append(a2_coverage)

    cov_b = np.array(cov_b)
    cov_a = np.array(cov_a)
    cov_aa = np.array(cov_aa)
    line_b, = plt.plot(np.mean(cov_b, axis = 0).tolist(), label="Boosted greybox fuzzer")
    line_a, = plt.plot(np.mean(cov_a, axis = 0).tolist(), label="UCB1 mutation selection + boosted greybox fuzzer")
    line_a2, = plt.plot(np.mean(cov_aa, axis = 0).tolist(), label="UCB1 mutation selection + UCB1 seed scheduling greybox fuzzer")

    plt.legend(handles=[line_b, line_a, line_a2], loc='lower right')
    # plt.legend(handles=[line_a2])
    plt.title('Coverage over time')
    plt.xlabel('# of inputs')
    plt.ylabel('lines covered')
    plt.show()