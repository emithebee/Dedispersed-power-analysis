import matplotlib.pyplot as plt, os, numpy as np
from mpl_toolkits.mplot3d import axes3d
import datetime as dt
import matplotlib.dates as mdt
import pickle as pkl
import seaborn as sns
from scipy.signal import find_peaks


def prep():
    """
    Function to have a list of the files in the directory and the keys to the .npz files
    Output :
    listdir: list, names of the .npz files
    dmkeys: list, keys to access the arrays where the data is stored in the .npz files
    """
    #se crea lista con archivoc npz
    listdir = os.listdir()
    listdir.sort()
    #todos los archivos tienen las mismas llaves
    file = np.load(listdir[0])
    keys = list(file.keys())
    keys.sort()
    dmkeys = keys[2:13]
    #se intercambian los elementos dm11 y dm2
    cindex, nindex = 2, 10
    element = dmkeys.pop(cindex)
    dmkeys.insert(nindex, element)
    return listdir, dmkeys


def moving_average(data, N = 256):
    """
    Function to calculate the moving average of an array
    Input :
    data: 1d-array, data from which to calculate moving average
    N: int, window size for the mv. avg
    Output :
    np.array(mvavg): array, the calculated moving average. the first N indices are replaced with NaN
    """
    cumsum = np.cumsum(np.insert(data, 0, 0))
    mvavg = list((cumsum[N:]-cumsum[:-N])/float(N))
    for i in range(N-1):
         mvavg.insert(0, np.nan)
    return np.array(mvavg)




def dm(data):
    """
    Function to extract all the DM data of an .npz file
    Input :
    data: str, name of the file to extract the DM data
    Output :
    dms: 2d-array, consisting of the 11 DMs in the file. the length of each DM is diferent, longer in smaller DMs
    """
    dms = []
    for n in range(len(dmkeys)):
        file = np.load(data)
        dm = file[dmkeys[n]]
        #el índice 2: es para quitar las primeras dos iteraciones de los archivos npz pues estos tienen pulsos de calibración
        dm = dm[int(2*len(dm[n])/(5*60)):].flatten()
        dms.append(dm)
    return dms

#para encontrar detecciones buscamos las intersecciones de los moving average + sigma con los datos
#La función devuelve los índices donde sucede esta intersección, por lo que el número de detecciones es len(i)/2
#slice = win_size-1, se usa para no contar detecciones las partes nan que vienen de la función moving_average(data, win_size)



def hl_envelopes_idx(s, dmin=1, dmax=1, split=False):
    """
    Function to create masks in order to obtain the envelope of an array in a time series
    Input :
    s: 1d-array, data signal from which to extract high and low envelopes
    dmin, dmax: int, optional, size of chunks, use this if the size of the input signal is too big
    split: bool, optional, if True, split the signal in half along its mean, might help to generate the envelope in some cases
    Output :
    lmin,lmax : high/low envelope idx of input signal s
    """

    # locals min      
    lmin = (np.diff(np.sign(np.diff(s))) > 0).nonzero()[0] + 1
    # locals max
    lmax = (np.diff(np.sign(np.diff(s))) < 0).nonzero()[0] + 1

    if split:
        # s_mid is zero if s centered around x-axis or more generally mean of signal
        s_mid = np.mean(s)
        # pre-sorting of locals min based on relative position with respect to s_mid 
        lmin = lmin[s[lmin]<s_mid]
        # pre-sorting of local max based on relative position with respect to s_mid 
        lmax = lmax[s[lmax]>s_mid]

    # global min of dmin-chunks of locals min 
    lmin = lmin[[i+np.argmin(s[lmin[i:i+dmin]]) for i in range(0,len(lmin),dmin)]]
    # global max of dmax-chunks of locals max 
    lmax = lmax[[i+np.argmax(s[lmax[i:i+dmax]]) for i in range(0,len(lmax),dmax)]]
    return lmin,lmax


#se obtiene la envolvente de la potencia para dilusidar mejor los eventos los unos de los otros

def detecciones_eventos(data, std=8, slice = 255):
    """
    Function to count the events that surpass a threshold
    Input :
    data: 1d-array, raw DM data
    std: int, sigma threshold value
    slice: int, equal in number of the used window size in the moving average
    Output :
    round(len(i)/2): int, number of events detected from the data
    """
    lmin, lmax = hl_envelopes_idx(data, dmin=256, dmax=256)
     
    envolvente = data[lmax]
     
    t = np.median(moving_average(data)[slice:]+ std*np.std(data))*np.ones(len(envolvente))
     
    i = np.argwhere(np.diff(np.sign(envolvente-t))).flatten()
    return round(len(i)/2)
       
def peaks_over_thresh(data, std = 8, slice = 255):
    """
    Function to count the peaks of the signal over a threshold
    Input :
    data: 1d-array, raw DM data
    std: int, sigma threshold value
    Output :
    len(filtered_peaks_indices): int, number of peaks
    filtered_peaks_indices: 1d-array, indices of the peaks 
    filtered_peaks_values: 1d-array, value of the peaks
    """
    peaks_indices = find_peaks(data)[0]
    peaks = np.array(list(zip(peaks_indices, data[peaks_indices])))
    threshold = np.median(moving_average(data)[slice:]+ std*np.std(data))
    
    #filtered_peaks = [(index, value) for index, value in peaks if value > threshold]
    
    # If you just want the indices:
    
    filtered_peaks_indices = [index for index, value in peaks if value > threshold]
    
    # Or just want the values
    
    filtered_peaks_values = [value for index, value in peaks if value > threshold]
    
    return len(filtered_peaks_indices), filtered_peaks_indices, filtered_peaks_values

#-----------------------------------------------------------------------------plots---------------------------------------------------------------------------------

#estos valores de sigma pueden ser modificados a gusto

np.arange(10, 19, 1)

nombres = [45, 90, 135, 180, 225, 270, 315, 360, 405, 450, 495]

#visualizar dms de un solo archivo
def plot_dm(data, quantity = 11):
    """
    Plot the DM data as a timeseries, you can choose to plot all 11 DMs or only a limited amount (matplotlib takes memory...)
    Input :
    data: 1d-array, raw DM data
    quantity: int, number of DMs to plot
    Output :
    a plot of the dedispersed power versus time for different DMs.
    """
    dms = dm(data)
    for i in range(quantity):
        fig, ax = plt.subplots()
        ax.plot(np.linspace(0, 5, len(dms[i])), 10*np.log10(dms[i]))
        #ax.plot(np.linspace(0, 5, len(dms[i])), 10*np.log10(moving_average(dms[i])+4*np.std(dms[i])))
        ax.set(title = 'DM'+ str(45*(i+1)) + ' ' + str(data), xlabel = 'Tiempo (min)', ylabel = 'Potencia de-dispersada (dBs)', ylim = (min(10*np.log10(dms[i]))-0.1, max(10*np.log10(dms[i]))+0.1), xlim = (0, 5))
        #ax.legend(['DM signal', 'Moving Average + 4$\sigma$'])
        plt.grid()



#matriz de cantidad de detecciones
#cada npz toma ~50 segundos, a tener en cuenta si se quiere medir en varios datos
#se recomienda guardar la matriz como un binario usando pickle para poder ser usada en cualquier momento

def conteo_detecciones(lista_archivos):
    """
    Function to count the peaks of the data over several thresholds and the events detected over the same thresholds.
    Input :
    lista_archivos: 1d-array with the names of the files
    Output :
    cantidad_peaks: 2d-array, number of peaks over certain threshold per DM
    eventos: 2d-array, number of events over certain threshold per DM
    """
    cantidad_peaks = np.zeros((11, len(sigmas)))
    eventos = np.zeros((11, len(sigmas)))
    for npz in lista_archivos:
        dms = dm(npz)
        peaks_in_npz = []
        eventos_in_npz = []
        
        for i in range(len(dms)):
            peaks_in_dm = np.zeros(len(sigmas))
            eventos_in_dm = np.zeros(len(sigmas))
            for n in range(len(sigmas)):
                p = peaks_over_thresh(dms[i], std = n+int(sigmas[0]))[0]
                e = detecciones_eventos(dms[i], std = n+int(sigmas[0]))
                
                fila_p = np.zeros(len(sigmas))
                fila_p[n] = p
                
                fila_e = np.zeros(len(sigmas))
                fila_e[n] = e
                
                peaks_in_dm = peaks_in_dm + fila_p
                eventos_in_dm = eventos_in_dm + fila_e
            peaks_in_npz.append(peaks_in_dm)
            eventos_in_npz.append(eventos_in_dm)
        cantidad_peaks = cantidad_peaks + np.array(peaks_in_npz)
        eventos = eventos + np.array(eventos_in_npz)
    return cantidad_peaks, eventos


def desacumular(cantidad_detecciones):
    """
    Function to deacumulate the detections from one threshold to a higher one in order to count a detections that surpasses only highest threhsold
    Input : 
    cantidad_detecciones: 2d-array containing peaks/events
    Output :
    new_matrix: 2d-array with deacumulated peaks/events on each threhshold
    """
    new_matrix = cantidad_detecciones.copy()
    for fila in new_matrix:
        for i in range(len(fila)):
            if i+1 < max(range(len(fila)))+1:
                e = fila[i]-fila[i+1]
                fila[i] = e
    return new_matrix

#crear figura con histogramas adheridos
#se crea una función para poder usar cualquier matriz de detecciones guardada

def heatmap_hist(files, cantidad_detecciones, title = 'Detecciones'):
    """
    2d plot of the detections for each DM over different thresholds
    Input :
    files: 1d-array with the names of the files
    cantidad_detecciones: 2d-array containing peaks/events
    title: str, title for the plot
    Output :
    Heatmap of the DMs and thresholds with cumulative histograms. Title specifies the time frame from which the files are being analyzed.
    """
    fig = plt.figure()
    ax1 = fig.add_axes([0.1, 0.1, 0.65, 0.65])
    ax2 = fig.add_axes([0.1, 0.75, 0.65, 0.15])
    ax3 = fig.add_axes([0.75, 0.1, 0.15, 0.65])
    #heatmap
    sns.heatmap(cantidad_detecciones, cmap = 'viridis', linewidth = 0.5, annot = True, xticklabels = sigmas, yticklabels= nombres, ax = ax1, cbar = False, fmt = 'g')
    ax1.set(xlabel = '$\sigma$-Threshold', ylabel = 'DM')
    #histograma cumulativo para DM
    ax2.bar(sigmas, sum(cantidad_detecciones)), ax2.set_xticklabels([])
    ax2.set(ylabel='Detecciones/$\sigma$'), ax2.grid()
    #histograma cumulativo para sigma
    sum_horizontal = []
    for fila in cantidad_detecciones:
        sum_horizontal.append(sum(fila))
    sum_horizontal.reverse()

    ax3.barh(nombres, sum_horizontal), ax3.set_yticklabels([])
    ax3.set(xlabel='Detecciones/DM'), ax3.grid()
    fig.suptitle(title + ' desde ' + files[0][:19] + ' hasta ' + files[-1][:19])

def hist3d(cantidad_detecciones):
    """
    3d histogram of the detections for each DM over different thresholds
    Input :
    cantidad_detecciones: 2d-array containing peaks/events
    Output :
    3d histogram that shows graphically the quantity of detections over thresholds for each DM
    """
    fig = plt.figure()
    ax = fig.add_subplot(111, projection = '3d')

    x_data, y_data = np.meshgrid( np.arange(cantidad_detecciones.shape[1]), np.arange(cantidad_detecciones.shape[0]) )
    x_data = x_data.flatten()
    y_data = y_data.flatten()
    z = cantidad_detecciones.flatten()

    dx = np.ones_like(np.zeros(len(z)))
    dy = dx.copy()
    cmap = plt.cm.viridis(plt.Normalize(0, np.amax(cantidad_detecciones))(z))
    ax.bar3d(x_data, y_data, np.zeros(len(z)), dx-0.3, dy-0.5, z, color = cmap)
    #los ticks deben ajustarse a la cantidad de datos, si cantidad de datos = n -> ticks = n+1
    ax.set_xlabel('Threshold'), ax.set_ylabel('DM'), ax.set_zlabel('Cantidad de detecciones'), ax.set_xticks(np.arange(1, len(sigmas)+1, 1), sigmas), ax.set_yticks(np.arange(1, 12, 1), nombres)#, plt.title('Detecciones para un periodo de ' +str(len(dms[0])/294912) + ' días')



#queremos una forma de visualizar las detecciones en el tiempo para un día
#para esto, usamos una función donde tomamos una lista de archivos y escogemos un threshold y contar las detecciones
#esto noes entrega un array de cantidad de detecciones en el tiempo

def detecciones_por_npz(files, threshold = 8):
    """
    Function to count all the detections from a single .npz file
    Input :
    files: 1d-array with the names of the files
    threshold: int, sigma threshold used
    Output :
    det_per_npz: 2d-array, detections for a single .npz file with a set threshold
    """
    det_per_npz = []
    for npz in files:
        dms = dm(npz)
        det = np.zeros(len(dms))
        for i in range(len(dms)):
           c = peaks_over_thresh(dms[i], std = threshold)[0]
           fila = np.zeros(len(dms))
           fila[i] = c
           det = det + fila
        det_per_npz.append(sum(det))
    return det_per_npz

#plot en el tiempo
#el eje x muestra la hora en formato Y-M-D h:m:s

def detecciones_diarias(files, detecciones_por_dia):
    """
    plot of the detections for each DM over a set threshold in a day or a given period of time
    Input :
    files: 1d-array with the names of the files
    detecciones_por_dia: 2d-array containing peaks in a period of time
    Output :
    plot of how many detections per day are obtained, x-axis shows dates and y-axis is the quantity of detections
    """
    new = []
    for i in range(len(files)):
        e = dt.datetime.strptime(files[i][:19], '%Y-%m-%d %H_%M_%S')#, '%Y-%m-%d %H:%M:%S')
        new.append(e)
    fig, ax = plt.subplots()
    ax.bar(new, detecciones_por_dia, width = 0.001, edgecolor = 'white')
    ax.xaxis_date()
    ax.set(title = 'Detecciones desde ' + files[0][:19] + ' hasta ' + files[-1][:19], xlabel = 'Fecha y hora', ylabel = 'Cantidad de detecciones')
    plt.xticks(rotation = 'vertical', fontsize = 'small')

#Idealmente se usan estos códigos para un solo día de observación pero pueden usare para más o menos tiempo

#borrador filtro
'''
def filtering(data, std=5, slice = 255):
     index = np.argwhere(np.diff(np.sign(data-moving_average(data)-std*np.std(data)))).flatten()[slice:]
     pairs = np.split(index, len(index)/2)
     mask = [True for i in range(len(pairs))]
     for j in range(len(pairs)):
         if j == 0:
             j+=1
         elif pairs[j][0] - pairs[j-1][1] <= len(data)/len(dms[10]):
             mask[j] = False
             mask[j-1] = False
     return np.array(pairs)[mask]
'''



if __name__ == '__main__':
    lista_archivos, dmkeys = prep()
    init_point = float(input('Primer sigma: '))
    end_point = float(input('Último sigma: '))
    
    #normalizar por tiempo
    time1 = lista_archivos[0][0:19]
    time2 = lista_archivos[-1][0:19]
    formato = '%Y-%m-%d %H:%M:%S'
    resta = dt.datetime.strptime(time2, formato) - dt.datetime.strptime(time1, formato)
    (h, m, s) = str(resta).split(':')
    time_in_hours = int(h) + int(m)/60 + int(s)/3600
    #fin
    
    plt.ion()
    sigmas = np.arange(init_point, end_point+1, 1)
    peaks, eventos = conteo_detecciones(lista_archivos)
    perday = detecciones_por_npz(lista_archivos)
    heatmap_hist(lista_archivos, np.round(desacumular(peaks)/time_in_hours), title = 'Detecciones sobre threshold')
    heatmap_hist(lista_archivos, np.round(desacumular(eventos/time_in_hours)), title = 'Número de eventos')
    detecciones_diarias(lista_archivos, perday)
    plt.show()
    


#guardar imágenes interactivas
#pkl.dump(fig, open('nombredetuimagen.pickle', 'wb'))
#pkl.load(open('nombredetuimagen.pickle', 'rb'))


#este código tiene normalización por hora
