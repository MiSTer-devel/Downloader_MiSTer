from graphviz import Digraph

BACKUP_COLOR = '#888888'

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
dot.node('SKIP1', 'SKIP', shape='ellipse', fillcolor='#77DD77')
dot.node('SKIP2', 'SKIP', shape='ellipse', fillcolor='#77DD77')
dot.node('ABORT', 'ABORT', shape='ellipse', fillcolor='#ff8f8f')
dot.node('A', 'FetchDataJob [db]')
dot.node('B', 'LoadLocalStoreSigsJob', fillcolor='#ffefd5')
dot.node('C', 'LoadLocalStoreJob', fillcolor='#ffefd5')
dot.node('D', 'OpenDbJob', fillcolor='#B0E0E6')
dot.node('E', 'MixStoreAndDbJob', fillcolor='#B0E0E6')
dot.node('F', 'ProcessDbMainJob', fillcolor='#B0E0E6')
dot.node('G', 'ProcessDbIndexJob', fillcolor='#B0E0E6:#ffefd5')
dot.node('H', 'FetchFileJob [file]')

# Example "legend" nodes
dot.node('0', 'CPU', fillcolor='#B0E0E6')
dot.node('1', 'File System', fillcolor='#ffefd5')
dot.node('2', 'Network')

dot.edge('START', 'A', label='1:N')
dot.edge('START', 'B')

dot.edge('A', 'D', weight='10')
dot.edge('D', 'C', weight='5', constraint='false', label=' N:1, if any db sig != store sig')
dot.edge('D', 'E', weight='10', label=' db')
dot.edge('E', 'F', weight='10', label=' db + store')
dot.edge('F', 'G', weight='10', label=' if no zips')

dot.edge('G', 'H', label=' 1:N')

dot.edge('C', 'E', style='dotted', constraint='true', label='wait\nstore', dir='back')
dot.edge('B', 'D', style='dotted', constraint='true', label='wait\nstore sig', dir='back')

# Position SKIP1 at same rank as OpenDbJob (D)
with dot.subgraph() as s:
    s.attr(rank='same')
    s.node('SKIP1')
    s.node('D')
    s.node('C')

dot.edge('SKIP1', 'D', style='invis')
dot.edge('D', 'C', style='invis')

# Position E, SKIP2, and ABORT at same rank (left to right)
with dot.subgraph() as s:
    s.attr(rank='same')
    s.node('E')
    s.node('SKIP2')
    s.node('ABORT')

dot.edge('E', 'SKIP2', style='invis')
dot.edge('SKIP2', 'ABORT', style='invis')

dot.edge('C', 'C', label=' retry', style='dashed', constraint='false')
dot.edge('A', 'A', label=' retry', style='dashed', constraint='false')
dot.edge('D', 'A', label=' retry', style='dashed', constraint='true')
dot.edge('H', 'H', label=' retry', style='dashed', constraint='false')

dot.edge('H', 'END', weight='20', constraint='true')
dot.edge('C', 'ABORT', weight='20', constraint='true', label=' if always fails', style='dashed', color=BACKUP_COLOR, fontcolor=BACKUP_COLOR)
dot.edge('D', 'SKIP1', weight='1', constraint='false', label=' if db sig == store sig')
dot.edge('E', 'SKIP2', weight='1', constraint='false', label=' if db sig == store sig')

dot.render('jobs_diagram', format='png', cleanup=True)

# ZIP NODES in a subgraph cluster
with dot.subgraph(name='cluster_zip') as c:
    c.attr(style='filled', color='#f5f5ff', penwidth='1.0')
    c.node('3', 'Zip Feature', style='filled', fillcolor='#8f8fff', fontcolor='white', penwidth='0')

    c.node('I', 'WaitDbZipsJob', fillcolor='#B0E0E6')
    c.node('J', 'ProcessZipIndexJob', fillcolor='#B0E0E6:#ffefd5')
    c.node('K', 'FetchDataJob [zip summary]')
    c.node('L', 'OpenZipSummaryJob', fillcolor='#B0E0E6')
    c.node('DOT0', '', shape='circle', fixedsize='true', width='0.01', fillcolor='#ff8f8f')
    c.node('M', 'FetchDataJob [zip contents]')
    c.node('N', 'OpenZipContentsJob', fillcolor='#ffefd5')
    c.node('DOT1', '', shape='circle', fixedsize='true', width='0.01', fillcolor='#ff8f8f')
    c.node('DOT2', '', shape='circle', fixedsize='true', width='0.01', fillcolor='#ff8f8f')
#
# EDGES
#
dot.edge('F', 'I', weight='10', label='if zips')
dot.edge('I', 'G', weight='10', label='store w/ deselected\nzip indexes')
dot.edge('F', 'K', label='1:N (missing zips)')

dot.edge('J', 'M', label='if many file installs')
dot.edge('L', 'J')
dot.edge('K', 'L')
dot.edge('M', 'N')
dot.edge('N', 'H', label='1:N\n(invalid files)')
dot.edge('J', 'DOT1', dir='none')
dot.edge('DOT1', 'DOT2', label='if just few\n file installs', dir='none')
dot.edge('DOT2', 'H', label=' 1:N')
#dot.edge('N', 'H', label='1:N')

# "Wait" edges
dot.edge('J', 'I', style='dotted', constraint='true', label='wait\n zip indexes', dir='back')

# Labeled "1:N" edges
dot.edge('F', 'J', label='1:N (stored zips)', weight='5')

# Edges to END
dot.edge('N', 'END', weight='20', constraint='true')

# "Retry" edges
dot.edge('K', 'K', label=' retry', style='dashed', constraint='false')
dot.edge('L', 'K', label=' retry', style='dashed', constraint='false')
dot.edge('M', 'M', label=' retry', style='dashed', constraint='false')
dot.edge('N', 'M', label=' retry', style='dashed', constraint='false')

# "Backup" edges
dot.edge('K', 'DOT0', style='dashed', constraint='true', dir='none', color=BACKUP_COLOR)
dot.edge('L', 'DOT0', style='dashed', constraint='true', dir='none', color=BACKUP_COLOR)
dot.edge('DOT0', 'J', label='backup:\nstored summary', style='dashed', constraint='false', color=BACKUP_COLOR, fontcolor=BACKUP_COLOR)
#dot.edge('H', 'I', label='b', style='dashed', constraint='false', dir='none')
#dot.edge('I', 'F', label='b', style='dashed', constraint='false')
#dot.edge('J', 'E', label='b', style='dashed', constraint='false')
#dot.edge('K', 'L', label='b', style='dashed', constraint='false', dir='none')
#dot.edge('L', 'E', label='b', style='dashed', constraint='false')

dot.render('jobs_diagram_with_zip_feature', format='png', cleanup=True)
