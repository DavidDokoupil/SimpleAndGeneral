from argparse import ArgumentParser

import spot

from SaG import SaG

spot.setup()

if __name__ == "__main__":
    arg_parser = ArgumentParser(description="Use the Simple and General construction on the input automaton")
    arg_parser.add_argument('file', type=str, nargs='*', help='automata to process', default='-')
    
    arg_parser.add_argument('--skip', action='store_true',
                            help='skip calculation for states which have the rightmost component of level = - 2')
    arg_parser.add_argument('--jump_levels', action='store_true',
                            help='enable jumping to the highest possible level at once')
    
    arguments = arg_parser.parse_args()
    
    optimization_flags = {'rightmost_terminal_skip': arguments.skip,
                          'level_jumping': arguments.jump_levels}

    for aut in spot.automata(*arguments.file):
        aut = spot.complete(aut)
        algo = SaG(aut, optimization_flags)
        res = algo.complement()

        print(res.to_str())

