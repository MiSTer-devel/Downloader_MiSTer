from graphviz import Digraph

# Initialize the Digraph
dot = Digraph(
    comment='Workflow Diagram',
    graph_attr={'rankdir': 'TB'},
    node_attr={
        'shape': 'box',
        'style': 'rounded,filled',
        'fillcolor': 'lightgrey',
        'fontname': 'Helvetica'
    },
    edge_attr={'color': 'black'}
)

# NON-ZIP NODES
dot.node('START', 'START', shape='ellipse', fillcolor='black', fontcolor='white')
dot.node('END', 'END', shape='ellipse', fillcolor='#77DD77')
dot.node('A', 'FetchFileJob [db]')
dot.node('C', 'OpenDbJob', fillcolor='#ffefd5')
dot.node('D', 'ProcessDbJob', fillcolor='#B0E0E6')
dot.node('E', 'ProcessIndexJob', fillcolor='#B0E0E6')
dot.node('M', 'FetchFileJob [file]')
dot.node('N', 'ValidateFileJob [file]', fillcolor='#ffefd5')

# Example "legend" nodes
dot.node('0', 'CPU', fillcolor='#B0E0E6')
dot.node('1', 'File System', fillcolor='#ffefd5')
dot.node('2', 'Network')

dot.edge('START', 'A', label='1:N')

dot.edge('A', 'C', weight='10')
dot.edge('C', 'D', weight='10')
dot.edge('D', 'E', weight='10')

dot.edge('E', 'M', label='1:N')
dot.edge('M', 'N')

dot.edge('C', 'A', label=' retry', style='dashed', constraint='true')
dot.edge('N', 'M', label=' retry', style='dashed', constraint='false')

dot.edge('N', 'END', weight='20', constraint='true')

dot.render('jobs_diagram', format='png', cleanup=True)

# ZIP NODES in a subgraph cluster
with dot.subgraph(name='cluster_zip') as c:
    c.attr(style='filled', color='#f5f5ff', penwidth='1.0')
    c.node('3', 'Zip Feature', style='filled', fillcolor='#8f8fff', fontcolor='white', penwidth='0')

    c.node('O', 'ProcessDbZipsWaiterJob', fillcolor='#B0E0E6')
    c.node('F', 'ProcessZipJob', fillcolor='#B0E0E6')
    c.node('G', 'FetchFileJob [zip index]')
    c.node('H', 'ValidateFileJob [zip index]', fillcolor='#ffefd5')
    c.node('I', 'OpenZipIndexJob', fillcolor='#ffefd5')
    c.node('J', 'FetchFileJob [zip contents]')
    c.node('K', 'ValidateFileJob [zip contents]', fillcolor='#ffefd5')
    c.node('L', 'OpenZipContentsJob', fillcolor='#ffefd5')

#
# EDGES
#
dot.edge('D', 'O', weight='10')
dot.edge('O', 'E', weight='10')
dot.edge('D', 'G', label='1:N')

dot.edge('F', 'J')
dot.edge('I', 'F')
dot.edge('G', 'H')
dot.edge('H', 'I')
dot.edge('J', 'K')
dot.edge('K', 'L')
dot.edge('L', 'E', label='inv[]', minlen='4', weight='2')

# “Wait” edges
dot.edge('F', 'O', style='dotted', constraint='true', label='wait')

# Labeled “1:N” edges
dot.edge('D', 'F', label='1:N', weight='5')

# Edges to END
dot.edge('L', 'END', weight='20', constraint='true')

# “Retry” edges
dot.edge('H', 'G', label=' r', style='dashed', constraint='false')
dot.edge('I', 'G', label=' r', style='dashed', constraint='false')
dot.edge('K', 'J', label=' r', style='dashed', constraint='false')
dot.edge('L', 'J', label=' r', style='dashed', constraint='false')

# "Backup" edges
dot.edge('G', 'F', label='backup if stored', style='dashed', constraint='false')
#dot.edge('H', 'I', label='b', style='dashed', constraint='false', dir='none')
#dot.edge('I', 'F', label='b', style='dashed', constraint='false')
dot.edge('J', 'E', label='b', style='dashed', constraint='false')
#dot.edge('K', 'L', label='b', style='dashed', constraint='false', dir='none')
#dot.edge('L', 'E', label='b', style='dashed', constraint='false')

dot.render('jobs_diagram_with_zip_feature', format='png', cleanup=True)
