# This script generates a jobs flow diagram for the documentation

from graphviz import Digraph

# Initialize the Digraph object with some graph attributes
dot = Digraph(comment='Workflow Diagram',
                            graph_attr={'rankdir': 'TB'},  # TB for top to bottom diagram
                            node_attr={'shape': 'box', 'style': 'rounded,filled', 'fillcolor': 'lightgrey', 'fontname': 'Helvetica'},
                            edge_attr={'color': 'black'})  # Use a neutral color for edges

# Adding nodes (steps) with specific pastel colors for START and END
dot.node('A', 'FetchFileJob [db]')
dot.node('B', 'ValidateFileJob [db]', fillcolor='#ffefd5')
dot.node('0', 'CPU', fillcolor='#B0E0E6')
dot.node('1', 'File System', fillcolor='#ffefd5')
dot.node('2', 'Network')
dot.node('C', 'OpenDbJob', fillcolor='#ffefd5')
dot.node('D', 'ProcessDbJob', fillcolor='#B0E0E6')
dot.node('E', 'ProcessIndexJob', fillcolor='#B0E0E6')
dot.node('F', 'ProcessZipJob', fillcolor='#B0E0E6')
dot.node('G', 'FetchFileJob [zip index]')
dot.node('H', 'ValidateFileJob [zip index]', fillcolor='#ffefd5')
dot.node('I', 'OpenZipIndexJob', fillcolor='#ffefd5')
dot.node('J', 'FetchFileJob [zip contents]')
dot.node('K', 'ValidateFileJob [zip contents]', fillcolor='#ffefd5')
dot.node('L', 'OpenZipContentsJob', fillcolor='#ffefd5')
dot.node('M', 'FetchFileJob [file]')
dot.node('N', 'ValidateFileJob [file]', fillcolor='#ffefd5')
dot.node('START', 'START', shape='ellipse', fillcolor='black', fontcolor='white')  # Pastel blue for START
dot.node('END', 'END', shape='ellipse', fillcolor='#77DD77')  # Pastel green for END

# Adding edges (transitions)
# The normal workflow without labeled edges
dot.edges(['AB', 'BC', 'CD', 'GH', 'HI', 'JK', 'KL', 'MN'])

# The workflow with labeled edges "1 to N"
dot.edge('START', 'A', label='1 to N')
dot.edge('D', 'G', label='1 to N')
dot.edge('D', 'F', label='1 to N')
dot.edge('E', 'M', label='1 to N')

# Additional edges as per the diagram requirements
dot.edge('D', 'E')
dot.edge('F', 'J')
dot.edge('I', 'F')
dot.edge('L', 'END')
dot.edge('N', 'END')
dot.edge('F', 'E')

# Backward "retry" edges
dot.edge('B', 'A', label=' retry', constraint='false', minlen='10')
dot.edge('C', 'A', label=' retry', constraint='false', minlen='10')
dot.edge('H', 'G', label=' retry', constraint='false', minlen='10')
dot.edge('I', 'G', label=' retry', constraint='false', minlen='10')
dot.edge('K', 'J', label=' retry', constraint='false', minlen='10')
dot.edge('L', 'J', label=' retry', constraint='false', minlen='10')
dot.edge('N', 'M', label=' retry', constraint='false', minlen='10')

dot.render('jobs_diagram', format='png', cleanup=True)
