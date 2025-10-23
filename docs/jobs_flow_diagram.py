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
    edge_attr={'color': 'black', 'fontname': 'Helvetica-Narrow', 'fontsize': '10'}
)

# NON-ZIP NODES
dot.node('START', 'START', shape='ellipse', fillcolor='black', fontcolor='white')
dot.node('END', 'END', shape='ellipse', fillcolor='#77DD77')
dot.node('SKIP', 'SKIP', shape='ellipse', fillcolor='#77DD77')
dot.node('ABORT', 'ABORT', shape='ellipse', fillcolor='#ff8f8f')
dot.node('A', 'FetchDataJob [db]')
dot.node('B1', 'LoadLocalStoreSigsJob', fillcolor='#ffefd5')
dot.node('B2', 'LoadLocalStoreJob', fillcolor='#ffefd5')
dot.node('C', 'OpenDbJob', fillcolor='#B0E0E6')
dot.node('D', 'ProcessDbMainJob', fillcolor='#B0E0E6')
dot.node('E', 'ProcessDbIndexJob', fillcolor='#B0E0E6:#ffefd5')
dot.node('M', 'FetchFileJob [file]')

# Example "legend" nodes
dot.node('0', 'CPU', fillcolor='#B0E0E6')
dot.node('1', 'File System', fillcolor='#ffefd5')
dot.node('2', 'Network')

dot.edge('START', 'A', label='1:N')
dot.edge('START', 'B1')
dot.edge('START', 'B2')

dot.edge('A', 'C', weight='10')
dot.edge('C', 'D', weight='10', label=' db + store')
dot.edge('D', 'E', weight='10', label=' if no zips')

dot.edge('E', 'M', label=' 1:N')

dot.edge('B2', 'C', style='dotted', constraint='true', label='wait\nstore', dir='back')
dot.edge('B1', 'C', style='dotted', constraint='true', label='wait\nstore sig', dir='back')

# Keep B1 and B2 on same rank, with B1 to the left of B2
dot.edge('B1', 'B2', style='invis')
with dot.subgraph() as s:
    s.attr(rank='same')
    s.node('B1')
    s.node('B2')

with dot.subgraph() as s:
    s.attr(rank='same')
    s.node('SKIP')
    s.node('ABORT')

dot.edge('SKIP', 'ABORT', style='invis')

dot.edge('B2', 'B2', label=' retry', style='dashed', constraint='false')
dot.edge('A', 'A', label=' retry', style='dashed', constraint='false')
dot.edge('C', 'A', label=' retry', style='dashed', constraint='true')
dot.edge('M', 'M', label=' retry', style='dashed', constraint='false')

dot.edge('M', 'END', weight='20', constraint='true')
dot.edge('B2', 'ABORT', weight='20', constraint='true', label=' if always fails', style='dashed')
dot.edge('C', 'SKIP', weight='1', constraint='false', label=' if db sig == store sig')

dot.render('jobs_diagram', format='png', cleanup=True)

# ZIP NODES in a subgraph cluster
with dot.subgraph(name='cluster_zip') as c:
    c.attr(style='filled', color='#f5f5ff', penwidth='1.0')
    c.node('3', 'Zip Feature', style='filled', fillcolor='#8f8fff', fontcolor='white', penwidth='0')

    c.node('O', 'WaitDbZipsJob', fillcolor='#B0E0E6')
    c.node('F', 'ProcessZipIndexJob', fillcolor='#B0E0E6:#ffefd5')
    c.node('G', 'FetchDataJob [zip summary]')
    c.node('I', 'OpenZipSummaryJob', fillcolor='#B0E0E6')
    c.node('DOT0', '', shape='circle', fixedsize='true', width='0.01', fillcolor='#ff8f8f')
    c.node('J', 'FetchDataJob [zip contents]')
    c.node('L', 'OpenZipContentsJob', fillcolor='#ffefd5')
    c.node('DOT1', '', shape='circle', fixedsize='true', width='0.01', fillcolor='#ff8f8f')
    c.node('DOT2', '', shape='circle', fixedsize='true', width='0.01', fillcolor='#ff8f8f')
#
# EDGES
#
dot.edge('D', 'O', weight='10', label='if zips')
dot.edge('O', 'E', weight='10', label='store w/ deselected\nzip indexes')
dot.edge('D', 'G', label='1:N (missing zips)')

dot.edge('F', 'J', label='if many file installs')
dot.edge('I', 'F')
dot.edge('G', 'I')
dot.edge('J', 'L')
dot.edge('L', 'M', label='1:N\n(invalid files)')
dot.edge('F', 'DOT1', dir='none')
dot.edge('DOT1', 'DOT2', label='if just few\n file installs', dir='none')
dot.edge('DOT2', 'M', label=' 1:N')
#dot.edge('L', 'M', label='1:N')

# “Wait” edges
dot.edge('F', 'O', style='dotted', constraint='true', label='wait\n zip indexes', dir='back')

# Labeled “1:N” edges
dot.edge('D', 'F', label='1:N (stored zips)', weight='5')

# Edges to END
dot.edge('L', 'END', weight='20', constraint='true')

# “Retry” edges
dot.edge('G', 'G', label=' retry', style='dashed', constraint='false')
dot.edge('I', 'G', label=' retry', style='dashed', constraint='false')
dot.edge('J', 'J', label=' retry', style='dashed', constraint='false')
dot.edge('L', 'J', label=' retry', style='dashed', constraint='false')

# "Backup" edges
dot.edge('G', 'DOT0', style='dashed', constraint='true', dir='none')
dot.edge('I', 'DOT0', style='dashed', constraint='true', dir='none')
dot.edge('DOT0', 'F', label='backup:\nstored summary', style='dashed', constraint='false')
#dot.edge('H', 'I', label='b', style='dashed', constraint='false', dir='none')
#dot.edge('I', 'F', label='b', style='dashed', constraint='false')
#dot.edge('J', 'E', label='b', style='dashed', constraint='false')
#dot.edge('K', 'L', label='b', style='dashed', constraint='false', dir='none')
#dot.edge('L', 'E', label='b', style='dashed', constraint='false')

dot.render('jobs_diagram_with_zip_feature', format='png', cleanup=True)
