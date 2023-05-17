from typing import List, Dict
from complement_base import ComplementBase, BDD, FlaggedState, InputState, Automaton, Transition, UnflaggedState

from buddy import bddtrue


class SaG(ComplementBase):
    def __init__(self, input_automaton: Automaton, optimization_flags: Dict[str, bool]):
        super().__init__(input_automaton, optimization_flags)

    def complement(self) -> Automaton:
        entry_cl_pair = tuple([(tuple([self.entry_state]), 0)])
        initial_state = tuple([entry_cl_pair, True])

        state_map = {initial_state: self.output_automaton.new_state()}

        self.output_automaton.set_init_state(state_map[initial_state])

        queue = [initial_state]

        while queue:

            current_state = queue.pop(0)

            for minterm in self.minterms(bddtrue):
                successors = self.successors(current_state, minterm)
                for successor, accepting in successors:
                    if self.flags['rightmost_terminal_skip'] is True and successor[0][-1][1] == - 2:
                        continue
                    if successor not in state_map:
                        state_map[successor] = self.output_automaton.new_state()
                        queue.append(successor)

                    if accepting:
                        self.output_automaton.new_edge(state_map[current_state], state_map[successor], minterm, [0])
                    else:
                        self.output_automaton.new_edge(state_map[current_state], state_map[successor], minterm)

        self.output_automaton.set_state_names(self.readable_names(state_map))
        self.output_automaton.merge_edges()

        return self.output_automaton

    def successors(self, state: FlaggedState, minterm: BDD) -> List[Transition]: # The transition function
        (state, upper_flag) = state

        upper_levels = []

        successor_components: UnflaggedState = []
        successor_transitions: List[Transition] = []

        origin_levels = set([component[1] for component in state])
        origin_terminals_alive = [True for component in state if component[1] == -2]

        t_index = len(origin_terminals_alive) - 1

        for i in range(len(state) - 1, - 1, - 1):
            leveled_up = [set() for _ in range(self.max_level)] # Required by the optimization to capture all possible level-ups
            not_leveled, tainted = set(), set()

            (component, level) = state[i]
            is_cl_pair_tainted = level < 0

            for component_state in component:
                for edge in self.input_automaton.out(component_state):
                    if minterm not in self.minterms(edge.cond):
                        continue

                    if is_cl_pair_tainted:
                        tainted |= {edge.dst}

                    if level in edge.acc.sets():
                        successor_level = (level + 1) % self.max_level
                        if self.flags['level_jumping'] is True:
                            while successor_level != level and successor_level in edge.acc.sets():
                                successor_level += 1
                                successor_level %= self.max_level
                        leveled_up[successor_level] |= {edge.dst}

                    else:
                        not_leveled |= {edge.dst}

            greedier = self.get_greedier(successor_components)
            (tainted, leveled_up, not_leveled) = self.remove_greedier(level, greedier, tainted, leveled_up, not_leveled)
            leveled_up = self.prepare_leveled_up_components(level, leveled_up)

            to_terminal_condition = level == - 2 or {-2}.isdisjoint(origin_levels) or not any(origin_terminals_alive)

            if level == - 2 and len(tainted) == 0: # Terminal component 'died'
                origin_terminals_alive[t_index] = False
                t_index -= 1

            if is_cl_pair_tainted and tainted: # Tainted branch
                new_level = - 2 if to_terminal_condition else - 3 # Placeholder color indicating a check at the end is required
                successor_components.append(list([tuple(tainted), new_level]))
                continue

            for lvled_up_pair in leveled_up[::-1]: # Level-up branch
                if upper_flag:
                    upper_levels.append(lvled_up_pair[1])

                no_reset_condition = self.max_level - 1 >= lvled_up_pair[1] > level # Checks for reset

                new_level = lvled_up_pair[1] if no_reset_condition else - 2 if to_terminal_condition else - 3
                successor_components.append([lvled_up_pair[0], new_level])

            if not_leveled: # No level-up branch
                if upper_flag:
                    upper_levels.append(level)

                successor_components.append([tuple(not_leveled), level])

        no_terminal_alive = not any(origin_terminals_alive)

        successor_components = self.resolve_levels(successor_components, no_terminal_alive)

        successor = tuple(successor_components)[::-1]
        upper_levels = upper_levels[::-1]

        if upper_flag:
            upper_state: FlaggedState = self.convert_to_upper(successor, upper_levels)
            successor_transitions.append((upper_state, False))
            no_terminal_alive &= False # No placement of acceptance on transition between parts

        successor_transitions.append(((successor, False), no_terminal_alive))

        return successor_transitions

    def readable_names(self, state_map: Dict[FlaggedState, InputState]) -> List[str]: # Pretty output of states
        state_names = []

        for state, _ in state_map.items():
            is_upper = state[1]
            name = "("
            for component in state[0]:
                name += f"{set(component[0])}:{int(component[1])} , "
            name = name[:-2]
            name += "↑)" if is_upper else "↓)"
            state_names.append(name)

        return state_names
