"""Headless, unclipped diagnostic figures for the evaluated flight examples."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

COLORS = {'nominal':'#11875d','step_attack':'#d54a45','ramp_attack':'#d18a12','stealth_attack':'#7254af'}

def save(fig,output,name):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    for extension in ('png','pdf','svg'):
        fig.savefig(output/f'{name}.{extension}',dpi=180,bbox_inches='tight')
    plt.close(fig)

def plot_diagnostics(examples,config,output,protocol):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.titleweight':'bold','pdf.fonttype':42,'svg.fonttype':'none'})
    onset = config['attack_onset_sec']
    fig,axes = plt.subplots(2,1,figsize=(11,8),sharex=True,layout='constrained')
    for category,item in examples.items():
        frame = item['frame']
        label = f'{category.replace("_"," ")} / {item["flight"]}'
        axes[0].plot(frame.time_sec,item['cusum'],color=COLORS[category],label=label,lw=1.4)
        axes[1].plot(frame.time_sec,np.abs(frame.ekf_y-frame.gt_y_true),color=COLORS[category],lw=1.4)
    axes[0].axhline(config['cusum_threshold'],color='#172b4d',ls='--',label='CUSUM threshold')
    axes[0].set(title='Detector memory',ylabel='Leaky CUSUM score')
    axes[1].set(title='East position estimation error',ylabel='|EKF east − ground-truth east| (m)',xlabel='Time from preserved flight origin (s)')
    for ax in axes:
        ax.axvline(onset,color='#64748b',ls=':',label=f'Attack onset: {onset:g} s')
        ax.grid(alpha=0.18)
    axes[0].legend(fontsize=8,loc='best')
    fig.suptitle(f'GNSS simulation · example traces · {protocol} protocol',fontsize=15,fontweight='bold')
    save(fig,output,'detector_overview')
    if 'stealth_attack' in examples:
        item = examples['stealth_attack']; frame=item['frame']
        fig,axes=plt.subplots(3,1,figsize=(10,9),sharex=True,layout='constrained')
        axes[0].plot(frame.time_sec,item['raw'],color='#b6bdc9',label='Raw residual',lw=1)
        axes[0].plot(frame.time_sec,item['rolling'],color='#167d9a',label='Rolling residual',lw=1.5)
        axes[0].set_ylabel('Mismatch (m/s²)');axes[0].legend()
        axes[1].plot(frame.time_sec,item['z'],color='#d18a12')
        axes[1].axhline(config['z_threshold'],color='#172b4d',ls='--')
        axes[1].set_ylabel('Standardized residual')
        axes[2].plot(frame.time_sec,item['cusum'],color=COLORS['stealth_attack'])
        axes[2].axhline(config['cusum_threshold'],color='#172b4d',ls='--')
        axes[2].set(ylabel='CUSUM score',xlabel='Time from preserved flight origin (s)')
        for ax in axes:
            ax.axvline(onset,color='#64748b',ls=':');ax.grid(alpha=0.18)
        fig.suptitle(f'Stealth scenario · {item["flight"]} · offline detector states',fontsize=15,fontweight='bold')
        save(fig,output,'stealth_internals')
