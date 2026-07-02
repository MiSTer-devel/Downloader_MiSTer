from graphviz import Digraph

# Initialize the Digraph
dot = Digraph(
    comment='Online Checker Workflow Diagram',
    graph_attr={
        'rankdir': 'TB',
        'nodesep': '1.00',
        'ranksep': '1.20',
        'splines': 'spline',
    },
    node_attr={
        'shape': 'box',
        'style': 'rounded,filled',
        'fillcolor': 'lightgrey',
        'fontname': 'Helvetica'
    },
    edge_attr={'color': 'black', 'fontname': 'Helvetica-Narrow', 'fontsize': '9'}
)

# MAIN NODES
dot.node('START', 'START', shape='ellipse', fillcolor='black', fontcolor='white')
dot.node('A', 'FetchDataJob [db]')
dot.node('B', 'LoadLocalStoreFingerprintsJob', fillcolor='#ffefd5')
dot.node('C', 'LoadLocalStoreJob', fillcolor='#ffefd5')
dot.node('D', 'OpenDbJob', fillcolor='#B0E0E6')
dot.node('E', 'MixStoreAndDbJob', fillcolor='#B0E0E6:#ffefd5')

# RESULT NODES
dot.node('SKIP1', 'SKIP', shape='ellipse', fillcolor='#77DD77')
dot.node('SKIP2', 'SKIP', shape='ellipse', fillcolor='#77DD77')
dot.node('UPDATE', 'NEEDS\nUPDATE', shape='ellipse', fillcolor='#fff2a8')
dot.node('FAILED', 'FAILED', shape='ellipse', fillcolor='#ff8f8f')
dot.node('FINGERPRINT_FAILURE', 'FINGERPRINT\nFAILURE', shape='ellipse', fillcolor='#ff8f8f')

# Example "legend" nodes
dot.node('0', 'CPU', fillcolor='#B0E0E6')
dot.node('1', 'File System', fillcolor='#ffefd5')
dot.node('2', 'Network')

#
# MAIN FLOW
#
dot.edge('START', 'A', label='1:N')
dot.edge('START', 'B')
dot.edge('A', 'D', weight='10')
dot.edge('D', 'C', weight='5', constraint='false', label=' N:1, if any db figp\n!= store figp', tailport='e', headport='w')
dot.edge('D', 'E', weight='10', label=' db', tailport='s', headport='n')

# "Wait" edges
dot.edge('B', 'D', style='dotted', constraint='true', label='wait\nstore figp', dir='back', tailport='s', headport='n')
dot.edge('C', 'E', style='dotted', constraint='true', label='wait\nstore', dir='back', tailport='s', headport='n')

# "Retry" edges
dot.edge('A', 'A', label=' retry', style='dashed', constraint='false')
dot.edge('D', 'A', label=' retry', style='dashed', constraint='true')

#
# RESULTS
#
dot.edge('D', 'SKIP1', weight='1', constraint='false', label=' if db figp ==\nstore figp', tailport='w', headport='e')
dot.edge('E', 'SKIP2', weight='1', constraint='false', label=' if db figp ==\nstore figp')
dot.edge('E', 'UPDATE', weight='1', constraint='false', label=' if db figp !=\nstore figp')
dot.edge('A', 'FAILED', weight='1', constraint='false', label='fetch', style='dashed')
dot.edge('D', 'FAILED', weight='1', constraint='false', label='open', style='dashed')
dot.edge('B', 'FINGERPRINT_FAILURE', weight='1', constraint='false', label='figp load', style='dashed')
dot.edge('C', 'FINGERPRINT_FAILURE', weight='1', constraint='false', label='store load', style='dashed')

#
# LAYOUT HINTS
#
with dot.subgraph() as s:
    s.attr(rank='source')
    s.node('0')
    s.node('1')
    s.node('2')

dot.edge('0', '1', style='invis')
dot.edge('1', '2', style='invis')
dot.edge('1', 'START', style='invis', weight='20')

with dot.subgraph() as s:
    s.attr(rank='same')
    s.node('FAILED')
    s.node('A')
    s.node('B')

with dot.subgraph() as s:
    s.attr(rank='same')
    s.node('SKIP1')
    s.node('D')
    s.node('C')
    s.node('FINGERPRINT_FAILURE')

with dot.subgraph() as s:
    s.attr(rank='same')
    s.node('E')
    s.node('SKIP2')
    s.node('UPDATE')

# Invisible ordering edges keep branches away from the central path.
dot.edge('FAILED', 'A', style='invis')
dot.edge('A', 'B', style='invis')
dot.edge('SKIP1', 'D', style='invis')
dot.edge('D', 'C', style='invis')
dot.edge('C', 'FINGERPRINT_FAILURE', style='invis')
dot.edge('E', 'SKIP2', style='invis')
dot.edge('SKIP2', 'UPDATE', style='invis')

dot.render('jobs_online_checker_diagram', format='png', cleanup=True)
