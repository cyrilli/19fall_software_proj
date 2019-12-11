import random
import pickle  # serializes an object by producing a byte array from all the information in the object
import hashlib # produces a 128-bit hash value from a byte array
from fuzzingbook.Fuzzer import PrintRunner
from fuzzingbook.GreyboxFuzzer import AFLFastSchedule
import numpy as np
import pickle  # serializes an object by producing a byte array from all the information in the object
import hashlib # produces a 128-bit hash value from a byte array


class UCB1Schedule(object):
    def __init__(self, explorationConstant_seed = 1.0):
        self.path_frequency = {}
        self.explorationConstant_seed = explorationConstant_seed

    def choose(self, population):
        """Choose weighted by normalized energy."""
        import numpy as np

        totalHits = 0
        for seed in population:
            pathID = getPathID(seed.coverage)
            if pathID not in self.path_frequency:
                self.path_frequency[pathID] = [0, 0]
            totalHits += self.path_frequency[pathID][1]

        maximumUCBValue = -np.inf
        selected_seed_idx = -1
        # to break ties by random
        seed_idx_list = list(range(len(population)))
        random.shuffle(seed_idx_list)
        # print("======================================")
        for seed_idx in seed_idx_list:
            pathID = getPathID(population[seed_idx].coverage)
            # print(pathID)
            [cum_reward, pathHits] = self.path_frequency[pathID]
            # print(self.path_frequency[pathID])
            if pathHits == 0:
                selected_seed_idx = seed_idx
                break
            else:
                averagedReward = cum_reward/pathHits
                UCBValue = averagedReward + self.explorationConstant_seed * np.sqrt(np.log(totalHits)/pathHits)
                if UCBValue >= maximumUCBValue:
                    maximumUCBValue = UCBValue
                    selected_seed_idx = seed_idx
        assert selected_seed_idx != -1

        seed = population[selected_seed_idx]
        # print("selected")
        # print(getPathID(seed.coverage))
        return seed

def getPathID(coverage):
    """Returns a unique hash for the covered statements"""
    pickled = pickle.dumps(coverage)
    return hashlib.md5(pickled).hexdigest()

class UCB1Mutator(object):
    def __init__(self):
        self.mutators = [
            self.delete_random_character,
            self.insert_random_character,
            self.flip_random_character
        ]

    def insert_random_character(self,s):
        """Returns s with a random character inserted"""
        pos = random.randint(0, len(s))
        random_character = chr(random.randrange(32, 127))
        return s[:pos] + random_character + s[pos:]

    def delete_random_character(self,s):
        """Returns s with a random character deleted"""
        if s == "":
            return self.insert_random_character(s)

        pos = random.randint(0, len(s) - 1)
        return s[:pos] + s[pos + 1:]

    def flip_random_character(self,s):
        """Returns s with a random bit flipped in a random position"""
        if s == "":
            return self.insert_random_character(s)

        pos = random.randint(0, len(s) - 1)
        c = s[pos]
        bit = 1 << random.randint(0, 6)
        new_c = chr(ord(c) ^ bit)
        return s[:pos] + new_c + s[pos + 1:]

    def mutate(self, inp, mutator_id=None):
        """Return s with a mutation specified by mutator_id applied"""
        if mutator_id is None:
            mutator = random.choice(self.mutators)
        else:
            mutator = self.mutators[mutator_id]
        return mutator(inp)

class AdaptiveMutationAndSeedSelectionGreyboxFuzzer():
    def __init__(self, seeds, mutator=UCB1Mutator(), schedule=UCB1Schedule()):
        self.seeds = seeds
        self.mutator = mutator
        self.schedule = schedule
        self.inputs = []
        self.explorationConstant = 1
        self.reset()
        self.decay = 0.9

    def reset(self):
        """Reset path frequency"""
        self.population = list(map(lambda x: Seed(x), self.seeds))
        self.seed_index = 0
        self.coverages_seen = set()
        self.population = [] # population is filled during greybox fuzzing
        self.schedule.path_frequency = {}
        self.path_mutation_frequency = {}

    # select seed: input that activates less frequent path is more likely to be selected
    # select mutation on seed
    def create_candidate(self):
        """Returns an input generated by fuzzing a seed in the population"""
        seed = self.schedule.choose(self.population)

        # Stacking: Apply multiple mutations to generate the candidate
        candidate = seed.data
        # by the time we run create_candidate,
        # all seeds have been ran at least once, so seed.coverage is defined
        pathID = getPathID(seed.coverage)
        # retrieve mutation history for pathID
        # {mutationID: [sum of rewards, number of hits]}
        if pathID not in self.path_mutation_frequency:
            # never hit this path before
            self.path_mutation_frequency[pathID] = {}
            for mut_index in range(len(self.mutator.mutators)):
                self.path_mutation_frequency[pathID][mut_index] = [0, 0]
        mutationHistoryDict = self.path_mutation_frequency[pathID]
        # print(pathID)
        # print(mutationHistoryDict)
        pathIDTotalHits = 0
        for mut_list in mutationHistoryDict.values():
            pathIDTotalHits += mut_list[1]
        # print(pathIDTotalHits)
        # select mutation id using UCB
        maximumUCBValue = -np.inf
        selected_mutation_id = -1
        # to break ties by random
        mutator_id_list = list(range(len(self.mutator.mutators)))
        random.shuffle(mutator_id_list)
        for mut_index in mutator_id_list:
            if mutationHistoryDict[mut_index][1] == 0:
                selected_mutation_id = mut_index
                break
            else:
                averagedReward = mutationHistoryDict[mut_index][0]/mutationHistoryDict[mut_index][1]
                UCBValue = averagedReward + self.explorationConstant * np.sqrt(np.log(pathIDTotalHits)/mutationHistoryDict[mut_index][1])
                if UCBValue >= maximumUCBValue:
                    maximumUCBValue = UCBValue
                    selected_mutation_id = mut_index
        assert selected_mutation_id != -1
        # print(selected_mutation_id)
        trials = min(len(candidate), 1 << random.randint(1, 5))
        for i in range(trials):
            candidate = self.mutator.mutate(candidate, selected_mutation_id)
            # candidate = self.mutator.mutate(candidate)
        return pathID, candidate, selected_mutation_id

    def fuzz(self):
        """Returns first each seed once and then generates new inputs"""
        if self.seed_index < len(self.seeds):
            # Still seeding
            inp = self.seeds[self.seed_index]
            self.seed_index += 1
            self.inputs.append(inp)
            mutation_id = -1
            return None, inp, mutation_id
        else:
            # Mutating
            seed_PathID, inp, mutation_id = self.create_candidate()
            self.inputs.append(inp)

            return seed_PathID, inp, mutation_id

    def run(self, runner):
        """Inform scheduler about path frequency"""
        seed_PathID, inp, mutation_id = self.fuzz()
        result, outcome = runner.run(inp)
        new_coverage = frozenset(runner.coverage())
        reward = 0
        if new_coverage not in self.coverages_seen:
            reward = 1
            # We have new coverage
            seed = Seed(inp)
            seed.coverage = runner.coverage()
            self.coverages_seen.add(new_coverage)
            self.population.append(seed)
        path_id = getPathID(runner.coverage())
        if seed_PathID is None:
            seed_PathID = path_id

        if seed_PathID not in self.schedule.path_frequency:
            self.schedule.path_frequency[seed_PathID] = [reward, 1]
        else:
            self.schedule.path_frequency[seed_PathID][0] = self.decay * self.schedule.path_frequency[seed_PathID][0] + reward
            self.schedule.path_frequency[seed_PathID][1] = self.decay * self.schedule.path_frequency[seed_PathID][1] + 1

        if seed_PathID not in self.path_mutation_frequency:
            # print("??????")
            # never hit this path before
            self.path_mutation_frequency[seed_PathID] = {}
            for mut_index in range(len(self.mutator.mutators)):
                if mut_index == mutation_id:
                    self.path_mutation_frequency[seed_PathID][mut_index] = [reward, 1]
                else:
                    self.path_mutation_frequency[seed_PathID][mut_index] = [0, 0]
        else:
            # has hit this path before, not sure whether has used this mutation before
            if mutation_id != -1:
                # print("!!!!!")
                # increment number of times path_id, mutation_id pair appears
                self.path_mutation_frequency[seed_PathID][mutation_id][1] = self.decay * self.path_mutation_frequency[seed_PathID][mutation_id][1] + 1
                if reward == 1:
                    # increment number of times path_id, mutation_id pair gives reward 1
                    self.path_mutation_frequency[seed_PathID][mutation_id][0] = self.decay * self.path_mutation_frequency[seed_PathID][mutation_id][0] + 1
                else:
                    self.path_mutation_frequency[seed_PathID][mutation_id][0] = self.decay * \
                                                                                self.path_mutation_frequency[
                                                                                    seed_PathID][mutation_id][0] + 0

        return (result, outcome)

    def runs(self, runner=PrintRunner(), trials=10):
        """Run `runner` with fuzz input, `trials` times"""
        # Note: the list comprehension below does not invoke self.run() for subclasses
        # return [self.run(runner) for i in range(trials)]
        outcomes = []
        for i in range(trials):
            outcomes.append(self.run(runner))
        return outcomes

def getPathID(coverage):
    """Returns a unique hash for the covered statements"""
    pickled = pickle.dumps(coverage)
    return hashlib.md5(pickled).hexdigest()

class Seed(object):
    def __init__(self, data):
        """Set seed data"""
        self.data = data

    def __str__(self):
        """Returns data as string representation of the seed"""
        return self.data

    __repr__ = __str__