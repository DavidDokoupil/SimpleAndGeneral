from abc import ABC, abstractmethod

from typing import List, Any, Tuple, Set, Dict, Union

import spot
from buddy import bddtrue, bddfalse, bdd_support, bdd_satoneset

BDD = Any
Automaton = spot.twa_graph
Level = int
InputState = int
UpperFlag = bool
IsAccepting = bool
Component = Union[Tuple[InputState, ...], List[InputState]]
Cl_Pair = Union[Tuple[Component, Level], List[Union[Component, Level]]]
UnflaggedState = Union[Tuple[Cl_Pair, ...], List[Cl_Pair]]
FlaggedState = Tuple[UnflaggedState, UpperFlag]
Transition = Tuple[FlaggedState, IsAccepting]


class ComplementBase(ABC):
    @abstractmethod
    def __init__(self, input_automaton: Automaton, optimization_flags: Dict[str, bool]):
        if not input_automaton.acc().is_generalized_buchi():
            raise ValueError('Input automaton is not Generalized Buchi')

        self.flags = optimization_flags

        self.input_automaton = input_automaton
        
        self.max_level = self.input_automaton.acc().get_acceptance().used_sets().count()
        self.entry_state = self.input_automaton.get_init_state_number()

        bdd_dict = spot.make_bdd_dict()

        self.output_automaton: Automaton
        self.output_automaton = spot.make_twa_graph(bdd_dict)
        self.output_automaton.copy_ap_of(self.input_automaton)
        self.output_automaton.set_acceptance(1, "Inf(0)")

        self.atomic_props = bddtrue

        conditions = {edge.cond for edge in self.input_automaton.edges()}

        for cond in conditions:
            self.atomic_props &= bdd_support(cond)
            
        self.cache = {}

    @abstractmethod
    def complement(self):
        pass
    
    @abstractmethod
    def successors(self, state: FlaggedState, minterm: BDD) -> List[Transition]:
        pass

    @abstractmethod
    def readable_names(self, state_map: Dict[FlaggedState, int]):
        pass

    def minterms(self, label: BDD) -> List[BDD]:
        
        cached = self.cache.setdefault('minterms', dict())
        
        if label in cached:
            return cached[label]
        
        minterms = []

        all_ = label

        while all_ != bddfalse:
            one = bdd_satoneset(all_, self.atomic_props, bddfalse)
            all_ -= one
            minterms.append(one)
            
        cached[label] = minterms

        return minterms

    def get_greedier(self, state: List[Cl_Pair]) -> Set[InputState]: # Obtains the successor components of greedier component-level pairs 
        greedier_states = set()

        for component in state:
            greedier_states |= set(component[0])

        return greedier_states
    
    def remove_greedier(self, current_level: Level,
                        greedier_components: Set[InputState],
                        tainted_components: Set[InputState],
                        lvled_up_components: List[Set[InputState]],
                        notlvled_up_components: Set[InputState]) -> Tuple[Set[InputState], List[Set[InputState]], Set[InputState]]: # Hierarchichal subtraction based on the greediness
        
        tainted_components -= greedier_components
        greedier_components |= tainted_components

        for i in range(self.max_level):
            lvled_up_components[(current_level - i) % self.max_level] -= greedier_components
            greedier_components |= lvled_up_components[(current_level - i) % self.max_level]
        
        notlvled_up_components -= greedier_components
        
        return tainted_components, lvled_up_components, notlvled_up_components
    
    def prepare_leveled_up_components(self, current_level: Level,
                                      lvled_up_components: List[Set[InputState]]) -> List[Cl_Pair]: # Sorts the leveled-up component pairs according to greedyness
        prepared = []
        for i in range(self.max_level):
            if lvled_up_components[i]:
                prepared.append((tuple(lvled_up_components[i]), i))
        return prepared[current_level + 1:] + prepared[:current_level + 1]
    
    def resolve_levels(self, cl_pairs: List[Cl_Pair], no_terminal_follow: bool) -> UnflaggedState: # Resolves levels for component-level pairs based on if all terminal component-level pairs 'died'
        resolved = []
        for cl_pair in cl_pairs:
            if cl_pair[1] == - 3:
                cl_pair[1] = - 2 if no_terminal_follow else -1
            resolved.append(tuple(cl_pair))
        return resolved

    def convert_to_upper(self, state: UnflaggedState, levels: List[Level]) -> FlaggedState: # Adjusts the unflagged state based on provided levels and sets the correct flag
        converted = []
        for component, level in zip(state, levels):
            converted.append((component[0], level))
        return tuple(converted), True
