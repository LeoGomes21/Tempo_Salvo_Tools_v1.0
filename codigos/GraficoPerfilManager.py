from qgis.core import QgsProject, QgsRasterLayer, QgsPointXY, QgsWkbTypes, QgsFeature, QgsRaster, Qgis, QgsGeometry, QgsLayerTreeLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsDistanceArea, QgsCoordinateTransformContext, QgsMapLayerType, QgsVectorLayer, QgsTextAnnotation, QgsTextFormat, QgsProperty, QgsMapRendererParallelJob, QgsMapRendererCustomPainterJob, QgsMapSettings, QgsMessageLog, QgsField
from qgis.PyQt.QtWidgets import QDockWidget, QWidget, QListWidgetItem, QColorDialog, QStyledItemDelegate, QStyleOptionViewItem, QApplication, QStyle, QLabel, QVBoxLayout, QTableWidgetItem, QToolTip, QLabel, QListView, QFileDialog, QPushButton
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand, QgsVertexMarker, QgsMapToolIdentifyFeature, QgsMapCanvasAnnotationItem
from qgis.PyQt.QtCore import Qt, QRect, QPoint, QSize, QEvent, QVariant, QSettings
from PyQt5.QtGui import QTextDocument, QImage, QPixmap, QPainter, QFont
from PyQt5.QtCore import QThread, pyqtSignal, QByteArray, QBuffer
from matplotlib.backends.backend_pdf import PdfPages
from qgis.PyQt.QtGui import QIcon, QPixmap, QColor
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph import SignalProxy
import matplotlib.pyplot as plt
from qgis.utils import iface
import pyqtgraph.exporters
from qgis.PyQt import uic
from PyQt5 import QtCore
import pyqtgraph as pg
import numpy as np
import random
import base64
import ezdxf
import math
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Grafico_perfil.ui'))

class PerfilManager(QDockWidget, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(PerfilManager, self).__init__(parent)
        self.setupUi(self)

        self.setWindowTitle("Gráficos de Perfis de MDT's")

        # Armazena a referência da interface QGIS
        self.iface = iface

        # Adiciona o dock widget à interface QGIS na parte inferior
        iface.addDockWidget(Qt.BottomDockWidgetArea, self)

        # Ativa o antialiasing globalmente
        pg.setConfigOptions(antialias=True)

        # Inicializa o dicionário de mapeamento camada-item
        self.layer_item_map = {}

        # Preenche o listWidgetRaster com camadas Raster
        self.populate_raster_list()

        # Cria o widget do pyqtgraph e adiciona ao scrollAreaGrafico
        self.plot_widget = pg.PlotWidget()
        self.scrollAreaGrafico.setWidget(self.plot_widget)

        # Ativa o uso do OpenGL para melhorar a renderização
        self.plot_widget.useOpenGL(True)

        # Inicializa o fundo como preto e ajusta a cor dos textos
        self.plot_widget.setBackground('k')
        self.update_axis_labels(color='white')  # Define o texto dos rótulos como branco

        # Variáveis auxiliares
        self.selected_raster_layers = []  # Lista de camadas raster selecionadas
        self.selected_raster_layer = None  # Mantém uma única camada selecionada para compatibilidade
        self.line_tool = None
        self.rubber_band = None
        # Marcador para indicar a posição na linha temporária
        self.map_marker = None

        self.selected_raster_item = None

        # Inicializa as variáveis do gráfico
        self.current_x_values = []  # Lista vazia para os valores x
        self.current_y_values = []  # Lista vazia para os valores y

        # Inicializa o checkBoxLinha como selecionado
        self.checkBoxLinha.setChecked(True)

        # Inicializa a variável z_value_annotation como None
        self.z_value_annotation = None

        # Conecta os sinais aos slots
        self.connect_signals()

        self.update_checkboxes_state()

        self.setup_raster_tooltips()

        self.setup_second_graph() #Inicializa o segundo gráfico

        # Conecta os sinais de mudança de nome das camadas
        self.connect_name_changed_signals()

        # Variável para armazenar a rubber band do segmento destacado no mapa
        self.highlighted_map_segment = None

        self.inclination_tooltip = None  # Adicionado para o tooltip de inclinação

        # Armazenar os valores padrão do doubleSpinBox_espaco
        self.default_doubleSpinBox_espaco_value = self.doubleSpinBox_espaco.value()
        self.default_doubleSpinBox_espaco_max = self.doubleSpinBox_espaco.maximum()

    def connect_signals(self):
        # Conecta a seleção de camada raster
        self.listWidgetRaster.itemChanged.connect(self.on_raster_layer_selected)
        self.listWidgetRaster.itemChanged.connect(self.update_checkboxes_state)  # Atualiza checkboxes

        # Monitorar mudança no sistema de coordenadas
        iface.mapCanvas().destinationCrsChanged.connect(self.update_checkboxes_state)

        # Conecta o checkbox para selecionar a linha
        self.checkBoxLinha.stateChanged.connect(self.on_select_line_state_changed)

        # Conecta o checkbox para selecionar uma linha de uma camada vetorial
        self.checkBoxLinha2.stateChanged.connect(self.on_select_line_layer_state_changed)

        # Conecta sinais do projeto para monitorar alterações de camadas
        QgsProject.instance().layerWasAdded.connect(self.on_layer_added)
        QgsProject.instance().layerWillBeRemoved.connect(self.on_layer_removed)

        # Conecta o sinal do checkBox_PB para alternar o fundo do gráfico
        self.checkBox_PB.stateChanged.connect(self.toggle_background_color)

        # Conecta o sinal do checkBox_Cotas para exibir o valor da cota do MDT
        self.checkBox_Cotas.stateChanged.connect(self.on_checkBox_Cotas_state_changed)

        # Conecta o sinal currentIndexChanged do comboBoxListaRaster ao novo método
        self.comboBoxListaRaster.currentIndexChanged.connect(self.on_combobox_layer_changed)

        #Conecte o sinal valueChanged do doubleSpinBox_espaco para que ele acione a atualização do tableWidget_Dados ao ser alterado
        self.doubleSpinBox_espaco.valueChanged.connect(self.update_table_on_spacing_change)

        # Sincronização ao Alterar o comboBoxListaRaster
        self.comboBoxListaRaster.currentIndexChanged.connect(self.update_second_graph)

        # Conectar o estado do checkBox_Inclina a um slot para mostrar ou ocultar o tooltip
        self.checkBox_Inclina.stateChanged.connect(self.on_checkBox_Inclina_state_changed)

        # Conecta a criação da camada de pontos
        self.pushButtonCriar.clicked.connect(self.create_points_layer_from_table)

        # Conecte os sinais para verificar o estado do botão exportar
        self.comboBoxTipo.currentIndexChanged.connect(self.update_export_button_state)
        self.comboBoxTipo_2.currentIndexChanged.connect(self.update_export_button_state)

        # Conectar o botão pushButtonExportar à função export_plot
        self.pushButtonExportar.clicked.connect(self.export_plot)

        # Conectar o botão pushButtonExportar_2 ao método de exportação
        self.pushButtonExportar_2.clicked.connect(self.export_second_graph)

    def connect_name_changed_signals(self):
        """Conecta o sinal de mudança de nome de todas as camadas raster existentes no projeto QGIS."""
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsRasterLayer):
                layer.nameChanged.connect(self.on_layer_name_changed)

    def on_layer_name_changed(self):
        """Atualiza o listWidgetRaster quando o nome de uma camada raster é alterado."""
        # Atualiza a lista de camadas raster no listWidgetRaster
        self.populate_raster_list()

    def on_layer_added(self, layer):
        """Atualiza o listWidgetRaster ao adicionar uma nova camada raster."""
        if isinstance(layer, QgsRasterLayer):  # Verifica se é uma camada raster
            # Conecta o sinal de mudança de nome para a camada recém-adicionada
            layer.nameChanged.connect(self.on_layer_name_changed)
            # Adiciona a nova camada ao listWidgetRaster
            self.add_raster_layer_to_list(layer)

            self.update_checkboxes_state() #Atualiza o checkboxes 

    def add_raster_layer_to_list(self, layer):
        """Adiciona uma camada raster ao listWidgetRaster."""
        # Definindo cores iniciais ou aleatórias conforme a necessidade
        initial_colors = [
            QColor(0, 0, 255), QColor(255, 0, 0), QColor(0, 255, 0),
            QColor(255, 0, 255), QColor(0, 255, 255), QColor(255, 255, 0)
        ]

        # Determina o índice atual das camadas, ignorando o cabeçalho
        index = self.listWidgetRaster.count() - 1  # Subtrai 1 para ignorar o cabeçalho
        color = initial_colors[index] if index < len(initial_colors) else QColor(
            random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
        )

        # Cria o QPixmap para o quadradinho colorido e configura o item
        pixmap = QPixmap(5, 5)
        pixmap.fill(color)
        icon = QIcon(pixmap)
        list_item = QListWidgetItem(layer.name())
        list_item.setIcon(icon)
        list_item.setFlags(list_item.flags() | Qt.ItemIsUserCheckable)
        list_item.setCheckState(Qt.Unchecked)
        list_item.setData(Qt.UserRole, color)

        # Adiciona o item ao listWidgetRaster
        self.listWidgetRaster.addItem(list_item)

    def on_layer_removed(self, layer_id):
        """Atualiza o listWidgetRaster e o gráfico ao remover uma camada raster."""
        layer_to_remove = None

        # Encontra o item correspondente no listWidgetRaster e o remove
        for i in range(self.listWidgetRaster.count()):
            item = self.listWidgetRaster.item(i)
            layer_name = item.text()
            layers = QgsProject.instance().mapLayersByName(layer_name)
            if layers and layers[0].id() == layer_id:
                layer_to_remove = layers[0]
                self.listWidgetRaster.takeItem(i)
                break

        # Se a camada removida estiver na lista de camadas selecionadas, remova-a e atualize o gráfico
        if layer_to_remove and layer_to_remove in self.selected_raster_layers:
            self.selected_raster_layers.remove(layer_to_remove)
            # Atualiza o gráfico com as camadas restantes
            self.extract_profile(self.line_tool.points if self.line_tool else [])

        self.update_checkboxes_state()

    def showEvent(self, event):
        """Ativado quando o diálogo é exibido."""
        super(PerfilManager, self).showEvent(event)

        # Certifique-se de que plot_widget está inicializado
        if not hasattr(self, 'plot_widget') or not self.plot_widget:
            self.plot_widget = pg.PlotWidget()
            self.scrollAreaGrafico.setWidget(self.plot_widget)
            self.plot_widget.setBackground('k')
            self.update_axis_labels(color='white')

        # Reseta as variáveis de dados do gráfico
        self.current_x_values = []
        self.current_y_values = []
        self.all_profiles = []  # Remove todos os perfis armazenados
        self.selected_raster_layers = []  # Reseta as camadas selecionadas
        self.line_points = []  # Adicione esta linha
        self.line_distances = []  # Adicione esta linha

        # Ativa a ferramenta de linha se o checkBoxLinha estiver selecionado
        if self.checkBoxLinha.isChecked():
            self.activate_line_tool()

        # Reseta o listWidgetRaster
        self.populate_raster_list()  # Recria a lista de camadas Raster

        # Verifica se há camadas raster selecionadas
        if not self.selected_raster_layers:
            # Desmarca e desativa os checkboxes se não houver camadas selecionadas
            self.checkBoxLinha.setChecked(False)
            self.checkBoxLinha.setEnabled(False)
            self.checkBoxLinha2.setChecked(False)
            self.checkBoxLinha2.setEnabled(False)
        else:
            # Ativa os checkboxes
            self.checkBoxLinha.setEnabled(True)
            self.checkBoxLinha2.setEnabled(True)

            # Ativa a ferramenta de linha se o checkBoxLinha estiver selecionado
            if self.checkBoxLinha.isChecked():
                self.activate_line_tool()
            elif self.checkBoxLinha2.isChecked():
                self.activate_line_layer_tool()

        self.setup_raster_tooltips()

        # Configura os comboBoxes
        self.setup_comboboxes()

        # Reset the pushButtonExportar state
        self.pushButtonExportar.setEnabled(False)

    def closeEvent(self, event):
        """Ativado quando o diálogo é fechado."""
        super(PerfilManager, self).closeEvent(event)

        # Remove o marcador do mapa
        self.remove_map_marker()

        # Remove a linha temporária ao fechar o diálogo
        if self.rubber_band:
            self.rubber_band.reset(QgsWkbTypes.LineGeometry)
            self.rubber_band = None

        # Reseta o checkBox_PB para desmarcado
        self.checkBox_PB.setChecked(False)

        # Reseta o checkBoxLinha para desmarcado
        self.checkBoxLinha.setChecked(False)

        # Reseta o checkBoxLinha2 para desmarcado
        self.checkBoxLinha2.setChecked(False)
        
         # Reseta o checkBox_Cotas para desmarcado
        self.checkBox_Cotas.setChecked(False)

        # Reseta o conteúdo do scrollAreaGrafico
        if hasattr(self, 'plot_widget') and self.plot_widget is not None:
            self.plot_widget.clear()  # Limpa o gráfico se estiver presente
            self.scrollAreaGrafico.takeWidget()  # Remove o widget do scroll area
            self.plot_widget = None  # Redefine para None

        # Restaura o estado inicial do scrollAreaGrafico
        self.plot_widget = pg.PlotWidget()
        self.scrollAreaGrafico.setWidget(self.plot_widget)
        self.plot_widget.setBackground('k')  # Fundo preto como padrão
        self.update_axis_labels(color='white')  # Texto branco como padrão

        # Reseta as variáveis de perfil
        self.line_points = []
        self.line_distances = []
        self.current_x_values = []
        self.current_y_values = []
        self.all_profiles = []
        self.selected_raster_layers = []

        # Esconde e redefine o tooltip_widget
        if hasattr(self, 'tooltip_widget') and self.tooltip_widget:
            self.tooltip_widget.hide()
            self.tooltip_widget = None

        # Reseta o comboBoxListaRaster
        self.comboBoxListaRaster.clear()
        self.comboBoxListaRaster.addItem("Nenhuma camada exibida")

        # Reseta o tableWidget_Dados e o gráfico no scrollAreaGrafico2
        self.reset_table_and_graph()

        # Remover o destaque do segmento no mapa
        if self.highlighted_map_segment:
            iface.mapCanvas().scene().removeItem(self.highlighted_map_segment)
            self.highlighted_map_segment = None

        # Esconde e redefine o inclination_tooltip
        if hasattr(self, 'inclination_tooltip') and self.inclination_tooltip:
            self.inclination_tooltip.hide()
            self.inclination_tooltip = None

        # Reseta os comboBoxes para o estado inicial
        self.reset_comboboxes()
 
    def activate_line_tool(self):
        """Ativa a ferramenta de desenho de linha e mantém a linha visível."""
        if not self.line_tool:
            self.line_tool = LineTool(iface.mapCanvas(), self)
        iface.mapCanvas().setMapTool(self.line_tool)

    def clear_rubber_band(self):
        """Limpa a linha temporária do mapa."""
        if self.rubber_band:
            self.rubber_band.reset(QgsWkbTypes.LineGeometry)
            self.rubber_band = None

    def deactivate_line_tool(self):
        """Desativa a ferramenta de desenho de linha sem remover a linha temporária."""
        if self.line_tool:
            iface.mapCanvas().unsetMapTool(self.line_tool)
            # Não chama self.line_tool.clear_rubber_band()
            self.line_tool = None

    def remove_map_marker(self):
        """Remove o marcador do mapa."""
        if self.map_marker:
            iface.mapCanvas().scene().removeItem(self.map_marker)
            self.map_marker = None

    def populate_raster_list(self):
        """Lista todas as camadas Raster no listWidgetRaster com um checkbox, um quadradinho colorido, e o nome."""

        self.listWidgetRaster.clear()  # Limpa o widget antes de adicionar novas camadas

        # Adiciona o cabeçalho
        header_item = QListWidgetItem()
        header_item.setText("Camadas Rasters")
        header_item.setTextAlignment(Qt.AlignCenter)
        header_item.setFlags(Qt.NoItemFlags)  # Faz o cabeçalho não ser selecionável
        header_item.setBackground(QColor(200, 200, 200))  # Fundo cinza claro
        self.listWidgetRaster.addItem(header_item)

        # Definindo cores iniciais
        initial_colors = [
            QColor(0, 0, 255),    # Azul
            QColor(255, 0, 0),    # Vermelho
            QColor(0, 255, 0),    # Verde
            QColor(255, 0, 255),  # Magenta
            QColor(0, 255, 255),  # Ciano
            QColor(255, 255, 0)   # Amarelo
        ]

        # Itera sobre todas as camadas carregadas no QGIS
        layers = list(QgsProject.instance().mapLayers().values())
        for index, layer in enumerate(layers):
            if isinstance(layer, QgsRasterLayer):
                # Escolhe uma cor inicial ou uma cor aleatória se exceder o conjunto inicial
                if index < len(initial_colors):
                    color = initial_colors[index]
                else:
                    color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

                # Cria um QPixmap para o quadradinho colorido
                pixmap = QPixmap(5, 5)
                pixmap.fill(color)
                icon = QIcon(pixmap)

                # Cria um item para o QListWidget
                list_item = QListWidgetItem(layer.name())
                # Define o ícone (quadradinho colorido)
                list_item.setIcon(icon)
                # Define o item como checkable
                list_item.setFlags(list_item.flags() | Qt.ItemIsUserCheckable)
                # Define o estado inicial do checkbox como não marcado
                list_item.setCheckState(Qt.Unchecked)
                # Armazena a cor no item (para uso posterior se necessário)
                list_item.setData(Qt.UserRole, color)

                # Adiciona o item ao listWidgetRaster
                self.listWidgetRaster.addItem(list_item)

        # Adiciona um item delegate personalizado ao listWidgetRaster
        self.listWidgetRaster.setItemDelegate(ColorItemDelegate(self.listWidgetRaster))
        # Criar o item delegate passando o self (PerfilManager)
        self.color_delegate = ColorItemDelegate(self.listWidgetRaster, self)
        self.listWidgetRaster.setItemDelegate(self.color_delegate)

    def update_graph_color(self, new_color, index):
        """Atualiza a cor da linha do gráfico."""
        # Atualiza a cor armazenada no item
        item = self.listWidgetRaster.item(index.row())
        if item:
            item.setData(Qt.UserRole, new_color)
            # Verifica se este item é o que está atualmente plotado
            if item == self.selected_raster_item:
                self.plot_profile(self.current_x_values, self.current_y_values)

    def extract_profile(self, points):
        """Extrai os perfis das camadas raster selecionadas ao longo da linha."""

        if not self.selected_raster_layers:
            iface.messageBar().pushMessage("Erro", "Nenhuma camada raster selecionada.", level=Qgis.Warning)
            return

        self.all_profiles = []  # Lista para armazenar todos os perfis

        # Calcula os pontos e distâncias apenas uma vez
        distances, line_points = self.calculate_distances_and_points(points)
        self.line_points = line_points
        self.line_distances = distances

        # Ajusta o valor máximo do doubleSpinBox_espaco
        if distances:
            total_length = distances[-1]
            self.doubleSpinBox_espaco.setMaximum(total_length)
            # Opcional: ajustar o valor atual se for maior que o máximo
            if self.doubleSpinBox_espaco.value() > total_length:
                self.doubleSpinBox_espaco.setValue(total_length)

        # Para cada camada selecionada, extrai os valores de elevação
        for layer in self.selected_raster_layers:
            profiles = []  # Lista para armazenar segmentos de dados válidos
            current_distances = []
            current_values = []

            # Obtém o CRS da camada raster e configura a transformação de coordenadas
            raster_crs = layer.crs()
            map_crs = iface.mapCanvas().mapSettings().destinationCrs()
            if raster_crs != map_crs:
                transform = QgsCoordinateTransform(map_crs, raster_crs, QgsProject.instance())
                transformed_points = [transform.transform(point) for point in line_points]
            else:
                transformed_points = line_points

            for i, point in enumerate(transformed_points):
                ident = layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue)
                if ident.isValid():
                    results = ident.results()
                    value = list(results.values())[0]
                    if value is not None and not np.isnan(value):
                        current_distances.append(distances[i])
                        current_values.append(value)
                    else:
                        if current_distances and current_values:
                            profiles.append({
                                'distances': current_distances,
                                'values': current_values
                            })
                            current_distances = []
                            current_values = []
                else:
                    if current_distances and current_values:
                        profiles.append({
                            'distances': current_distances,
                            'values': current_values
                        })
                        current_distances = []
                        current_values = []

            if current_distances and current_values:
                profiles.append({
                    'distances': current_distances,
                    'values': current_values
                })

            # Armazena os perfis segmentados junto com a camada
            self.all_profiles.append({
                'layer': layer,
                'profiles': profiles
            })

        # Plota todos os perfis
        self.plot_profiles()

    def sample_raster_along_line(self, start_point, end_point, num_samples=100):
        """Amostra o raster ao longo de um segmento de linha, desconsiderando pontos fora da extensão do raster."""
        if not self.selected_raster_layer:
            return [], [], []

        extent = self.selected_raster_layer.extent()
        x_values = [start_point.x() + (end_point.x() - start_point.x()) * i / (num_samples - 1) for i in range(num_samples)]
        y_values = [start_point.y() + (end_point.y() - start_point.y()) * i / (num_samples - 1) for i in range(num_samples)]
        values = []
        distances = []
        points = []
        last_distance = 0

        for i, (x, y) in enumerate(zip(x_values, y_values)):
            point = QgsPointXY(x, y)
            if not extent.contains(point):
                continue

            ident = self.selected_raster_layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue)
            if ident.isValid():
                results = ident.results()
                value = list(results.values())[0] if results else None
            else:
                value = None

            if value is not None:
                values.append(value)
                points.append(point)
                if i == 0:
                    distances.append(0)
                else:
                    dx = x - x_values[i - 1]
                    dy = y - y_values[i - 1]
                    last_distance += (dx**2 + dy**2)**0.5
                    distances.append(last_distance)

        return values, distances, points

    def calculate_distances_and_points(self, points):
        """Calcula as distâncias cumulativas e pontos ao longo da linha."""
        distances = []
        total_distance = 0
        all_points = []

        for i in range(len(points) - 1):
            start = points[i]
            end = points[i+1]
            segment_distances, segment_points = self.sample_points_along_line(start, end)
            distances.extend([d + total_distance for d in segment_distances])
            total_distance += segment_distances[-1]
            all_points.extend(segment_points)

        return distances, all_points

    def sample_points_along_line(self, start_point, end_point, num_samples=100):
        """Gera pontos ao longo de um segmento de linha."""
        x_values = [start_point.x() + (end_point.x() - start_point.x()) * i / (num_samples - 1) for i in range(num_samples)]
        y_values = [start_point.y() + (end_point.y() - start_point.y()) * i / (num_samples - 1) for i in range(num_samples)]
        distances = []
        points = []
        last_distance = 0

        for i, (x, y) in enumerate(zip(x_values, y_values)):
            point = QgsPointXY(x, y)
            points.append(point)
            if i == 0:
                distances.append(0)
            else:
                dx = x - x_values[i - 1]
                dy = y - y_values[i - 1]
                last_distance += (dx**2 + dy**2)**0.5
                distances.append(last_distance)

        return distances, points

    def toggle_background_color(self, state):
        """Alterna a cor de fundo do gráfico e a cor dos textos dos rótulos dos eixos."""
        if state == Qt.Checked:
            self.plot_widget.setBackground('w')  # Define o fundo como branco
            self.update_axis_labels(color='black')   # Define o texto dos rótulos como preto
        else:
            self.plot_widget.setBackground('k')  # Define o fundo como preto
            self.update_axis_labels(color='white')   # Define o texto dos rótulos como branco

    def update_axis_labels(self, color):
        """Atualiza a cor dos rótulos dos eixos."""
        self.plot_widget.setLabel('left', 'Elevação (m)', color=color, size='10pt')
        self.plot_widget.setLabel('bottom', 'Distância (m)', color=color, size='10pt')

    def plot_profiles(self):
        """Plota todos os perfis no gráfico."""
        self.plot_widget.clear()

        if not self.all_profiles:
            return

        # Ativa o antialiasing globalmente
        pg.setConfigOptions(antialias=True)

        # Ativa o uso do OpenGL (opcional)
        self.plot_widget.useOpenGL(True)

        # Inicializa listas para armazenar todos os valores de x e y para definir o alcance dos eixos
        all_x_values = []
        all_y_values = []

        # Plota cada perfil com a cor correspondente
        for profile_data in self.all_profiles:
            layer = profile_data['layer']
            profiles = profile_data['profiles']

            # Obtém a cor do item correspondente no listWidgetRaster
            layer_name = layer.name()
            item = self.get_list_item_by_layer_name(layer_name)
            if item:
                color = item.data(Qt.UserRole)
                pen = pg.mkPen(color=color, width=1.3)
            else:
                pen = pg.mkPen(color='b', width=1.3)

            for segment in profiles:
                distances = segment['distances']
                values = segment['values']
                # Coleta todos os valores de x e y
                all_x_values.extend(distances)
                all_y_values.extend(values)
                # Plota o segmento
                self.plot_widget.plot(distances, values, pen=pen, name=layer_name)

        # Armazena os valores de x (distâncias) e y (valores) do primeiro segmento do primeiro perfil para interação
        first_profile = self.all_profiles[0]['profiles'][0] if self.all_profiles[0]['profiles'] else None
        if first_profile:
            self.current_x_values = first_profile['distances']
            self.current_y_values = first_profile['values']
        else:
            self.current_x_values = []
            self.current_y_values = []

        if not all_x_values or not all_y_values:
            return  # Não há dados para plotar

        # Adiciona rótulos nos eixos
        self.plot_widget.setLabel('left', 'Elevação (m)')
        self.plot_widget.setLabel('bottom', 'Distância (m)')

        # Adiciona uma grade ao gráfico
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Desativa o auto-range e fixa os limites dos eixos
        self.plot_widget.enableAutoRange(axis='y', enable=False)
        self.plot_widget.enableAutoRange(axis='x', enable=False)
        self.plot_widget.setXRange(min(all_x_values), max(all_x_values), padding=0)
        self.plot_widget.setYRange(min(all_y_values), max(all_y_values), padding=0)

        # Ativa o antialiasing
        # self.plot_widget.getPlotItem().setMouseEnabled(True, True)

        # Criar linhas de referência para o cursor com estilo tracejado
        self.vLine = pg.InfiniteLine(angle=90, pen=pg.mkPen(color='g', style=QtCore.Qt.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, pen=pg.mkPen(color='g', style=QtCore.Qt.DashLine))
        self.plot_widget.addItem(self.vLine)
        self.plot_widget.addItem(self.hLine)

        # Inicialmente, as linhas são invisíveis
        self.vLine.hide()
        self.hLine.hide()

        # Criar o TextItem para exibir as coordenadas
        self.coord_text = pg.TextItem(anchor=(0, 1))
        self.plot_widget.addItem(self.coord_text)
        self.coord_text.hide()

        # Criar o ponto sincronizado (um ScatterPlotItem com um único ponto)
        self.sync_point = pg.ScatterPlotItem(pen=pg.mkPen(None), brush=pg.mkBrush('r'), size=6)
        self.plot_widget.addItem(self.sync_point)
        self.sync_point.hide()

        # Conectar o evento de movimento do mouse
        self.proxy = SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved)

        # Atualizar o comboBox com as camadas exibidas
        self.update_combobox_raster_list()

        self.update_export_button_state() # Conecta update_export_button_state

    def get_list_item_by_layer_name(self, layer_name):
        """Retorna o QListWidgetItem correspondente ao nome da camada."""
        for index in range(self.listWidgetRaster.count()):
            item = self.listWidgetRaster.item(index)
            if item.text() == layer_name:
                return item
        return None

    def on_raster_layer_selected(self, item):
        """Callback quando um item do listWidgetRaster é alterado."""
        layer_name = item.text()
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            layer = layers[0]
            if item.checkState() == Qt.Checked:
                if layer not in self.selected_raster_layers:
                    self.selected_raster_layers.append(layer)
            else:
                if layer in self.selected_raster_layers:
                    self.selected_raster_layers.remove(layer)

        # if not self.selected_raster_layers:
            # self.plot_widget.clear()  # Limpa o gráfico
            # return

        if not self.selected_raster_layers:
            # Limpa o gráfico e variáveis associadas se nenhuma camada estiver selecionada
            self.plot_widget.clear()
            self.current_x_values = []
            self.current_y_values = []
            self.all_profiles = []
            return

        # Determina os pontos da linha
        if self.line_tool and self.line_tool.points:
            line_points = self.line_tool.points
        elif hasattr(self, 'line_points') and self.line_points:
            line_points = self.line_points
        else:
            self.plot_widget.clear()
            iface.messageBar().pushMessage("Aviso", "Desenhe ou selecione uma linha para gerar o perfil.", level=Qgis.Info)
            return

        # Processa o perfil em uma thread
        self.thread = ProfileExtractionThread(self, line_points, self.selected_raster_layers)
        self.thread.profile_ready.connect(self.on_profile_ready)
        self.thread.start()

    def on_profile_ready(self, all_profiles):
        """Callback chamado quando o perfil está pronto."""
        self.all_profiles = all_profiles
        self.plot_profiles()

    def on_select_line_state_changed(self, state):
        """Ativa ou desativa a ferramenta de desenho de linha."""
        if state == Qt.Checked:
            # Desativa o checkBoxLinha2 (seleção de linha de camada) se estiver ativo
            self.checkBoxLinha2.setChecked(False)
            self.deactivate_line_layer_tool()
            # Ativa a ferramenta de desenho de linha se o diálogo estiver visível
            if self.isVisible():
                self.activate_line_tool()

        else:
            # Desativa a ferramenta de desenho de linha
            self.deactivate_line_tool()

    def on_select_line_layer_state_changed(self, state):
        """Ativa ou desativa a ferramenta de seleção de linha de camada."""
        if state == Qt.Checked:
            # Desativa o checkBoxLinha (linha temporária) se estiver ativo
            self.checkBoxLinha.setChecked(False)
            self.deactivate_line_tool()
            # Ativa a ferramenta de seleção de linha de camada
            self.activate_line_layer_tool()

        else:
            # Desativa a ferramenta de seleção de linha de camada
            self.deactivate_line_layer_tool()

    def activate_line_layer_tool(self):
        """Ativa a ferramenta de seleção de linha de qualquer camada."""
        if not hasattr(self, 'line_layer_tool') or not self.line_layer_tool:
            self.line_layer_tool = SelectLineTool(iface.mapCanvas(), self)
        iface.mapCanvas().setMapTool(self.line_layer_tool)

    def deactivate_line_layer_tool(self):
        """Desativa a ferramenta de seleção de linha."""
        if hasattr(self, 'line_layer_tool') and self.line_layer_tool:
            iface.mapCanvas().unsetMapTool(self.line_layer_tool)
            self.line_layer_tool = None

    def draw_rubber_band(self, points, color=None):
        """
        Desenha a linha no mapa com uma cor fixa baseada na ação (checkBoxLinha ou checkBoxLinha2).
        :param points: Lista de pontos para formar a linha.
        :param color: Cor fixa opcional para a linha. Se None, usa a cor padrão do checkbox ativo.
        """
        if not self.rubber_band:
            self.rubber_band = QgsRubberBand(iface.mapCanvas(), QgsWkbTypes.LineGeometry)
            self.rubber_band.setWidth(2)

        # Define a cor da linha: usa o parâmetro 'color' ou a cor padrão do checkbox ativo
        if color:
            self.rubber_band.setColor(color)
        elif self.checkBoxLinha.isChecked():
            self.rubber_band.setColor(Qt.red)  # Vermelho para linha temporária
        elif self.checkBoxLinha2.isChecked():
            self.rubber_band.setColor(Qt.magenta)  # Magenta para linha fixa

        # Redefine a geometria da linha
        if points:
            line_geometry = QgsGeometry.fromPolylineXY([QgsPointXY(point.x(), point.y()) for point in points])
            self.rubber_band.setToGeometry(line_geometry, None)

    def calculate_cumulative_distances(self, points):
        """Calcula as distâncias cumulativas ao longo dos pontos."""
        distances = []
        total_distance = 0

        for i in range(len(points)):
            if i == 0:
                distances.append(0)
            else:
                dx = points[i].x() - points[i - 1].x()
                dy = points[i].y() - points[i - 1].y()
                segment_distance = math.hypot(dx, dy)
                total_distance += segment_distance
                distances.append(total_distance)

        return distances

    def interpolate_line_points(self, points, num_samples=100):
        """Interpola pontos ao longo da linha para aumentar a densidade."""
        if len(points) < 2:
            return points  # Sem interpolação necessária

        interpolated_points = []
        total_length = 0
        segment_lengths = []

        # Calcula o comprimento total da linha e o comprimento de cada segmento
        for i in range(len(points) - 1):
            dx = points[i + 1].x() - points[i].x()
            dy = points[i + 1].y() - points[i].y()
            segment_length = math.hypot(dx, dy)
            segment_lengths.append(segment_length)
            total_length += segment_length

        # Número total de pontos interpolados
        total_samples = num_samples * (len(points) - 1)

        for i in range(len(points) - 1):
            start = points[i]
            end = points[i + 1]
            num_segment_samples = max(int((segment_lengths[i] / total_length) * total_samples), 1)
            for j in range(num_segment_samples):
                t = j / num_segment_samples
                x = start.x() + t * (end.x() - start.x())
                y = start.y() + t * (end.y() - start.y())
                interpolated_points.append(QgsPointXY(x, y))
        interpolated_points.append(points[-1])  # Adiciona o último ponto
        return interpolated_points

    def extract_profiles_from_rasters(self, raster_layers):
        """Extrai os perfis das camadas raster selecionadas."""
        # Verifica se self.line_points e self.line_distances estão disponíveis
        if not hasattr(self, 'line_points') or not hasattr(self, 'line_distances'):
            iface.messageBar().pushMessage("Erro", "Nenhuma linha disponível para extrair o perfil.", level=Qgis.Warning)
            return []

        # Utiliza os pontos interpolados existentes
        line_points = self.line_points
        distances = self.line_distances

        all_profiles = []
        for layer in raster_layers:
            profiles = []  # Lista para armazenar segmentos contínuos
            current_distances = []
            current_values = []

            # Verifica se a camada está em coordenadas geográficas e realiza a transformação se necessário
            raster_crs = layer.crs()
            map_crs = iface.mapCanvas().mapSettings().destinationCrs()
            if raster_crs != map_crs:
                transform = QgsCoordinateTransform(map_crs, raster_crs, QgsProject.instance())
                transformed_points = [transform.transform(point) for point in line_points]
            else:
                transformed_points = line_points

            for i, point in enumerate(transformed_points):
                ident = layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue)
                if ident.isValid():
                    results = ident.results()
                    value = list(results.values())[0]
                    if value is not None and not np.isnan(value):
                        current_distances.append(distances[i])
                        current_values.append(value)
                    else:
                        if current_distances and current_values:
                            profiles.append({
                                'distances': current_distances,
                                'values': current_values
                            })
                            current_distances = []
                            current_values = []
                else:
                    if current_distances and current_values:
                        profiles.append({
                            'distances': current_distances,
                            'values': current_values
                        })
                        current_distances = []
                        current_values = []

            if current_distances and current_values:
                profiles.append({
                    'distances': current_distances,
                    'values': current_values
                })

            all_profiles.append({
                'layer': layer,
                'profiles': profiles
            })

        return all_profiles

    def update_checkboxes_state(self):
        """Atualiza o estado dos checkboxes com base nas condições."""
        # Verifica se o sistema de coordenadas do projeto é geográfico
        map_crs = iface.mapCanvas().mapSettings().destinationCrs()
        is_geographic = map_crs.isGeographic()

        # Verifica se há camadas selecionadas no listWidgetRaster
        has_selected_rasters = any(
            self.listWidgetRaster.item(i).checkState() == Qt.Checked
            for i in range(self.listWidgetRaster.count())
            if self.listWidgetRaster.item(i).flags() & Qt.ItemIsUserCheckable)

        # Verifica se há camadas de linha com feições
        has_line_features = any(
            isinstance(layer, QgsVectorLayer) and 
            layer.geometryType() == QgsWkbTypes.LineGeometry and 
            layer.featureCount() > 0
            for layer in QgsProject.instance().mapLayers().values())

        # Atualiza o estado do checkBoxLinha
        self.checkBoxLinha.setEnabled(has_selected_rasters)
        if not has_selected_rasters:
            self.checkBoxLinha.setChecked(False)  # Desmarca se não houver camadas raster selecionadas

        # Atualiza o estado do checkBoxLinha2
        self.checkBoxLinha2.setEnabled(
            has_selected_rasters and has_line_features and not is_geographic)
        if not has_selected_rasters or is_geographic or not has_line_features:
            self.checkBoxLinha2.setChecked(False)  # Desmarca se as condições não forem atendidas

    def update_map_marker(self, distance):
        """Atualiza a posição do marcador no mapa com base na distância percorrida."""
        if not hasattr(self, 'line_distances') or not hasattr(self, 'line_points') or not self.line_distances or not self.line_points:
            self.remove_map_marker()
            return

        # Verifica se a distância está dentro do intervalo permitido
        if distance < self.line_distances[0] or distance > self.line_distances[-1]:
            self.remove_map_marker()
            return

        # Encontra os índices dos pontos entre os quais a distância atual se encontra
        point = None
        for i in range(len(self.line_distances) - 1):
            if self.line_distances[i] <= distance <= self.line_distances[i + 1]:
                # Interpola entre os pontos line_points[i] e line_points[i + 1]
                ratio = (distance - self.line_distances[i]) / (self.line_distances[i + 1] - self.line_distances[i])
                x = self.line_points[i].x() + ratio * (self.line_points[i + 1].x() - self.line_points[i].x())
                y = self.line_points[i].y() + ratio * (self.line_points[i + 1].y() - self.line_points[i].y())
                point = QgsPointXY(x, y)
                break

        if not point:
            self.remove_map_marker()
            return

        # Se o marcador não existir, cria um novo
        if not self.map_marker:
            self.map_marker = QgsVertexMarker(iface.mapCanvas())
            self.map_marker.setIconSize(10)
            self.map_marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
            self.map_marker.setPenWidth(2)

        # Atualiza a cor do marcador com base no estado dos checkboxes
        if self.checkBoxLinha.isChecked():
            self.map_marker.setColor(Qt.red)  # Vermelho para checkBoxLinha
        elif self.checkBoxLinha2.isChecked():
            self.map_marker.setColor(Qt.magenta)  # Magenta para checkBoxLinha2

        # Atualiza a posição do marcador
        self.map_marker.setCenter(point)

        # Armazena o ponto e a distância atuais para uso no tooltip
        self.current_point = point
        self.current_distance = distance

    def hide_tooltip(self):
        """Esconde o tooltip flutuante."""
        if hasattr(self, 'tooltip_widget') and self.tooltip_widget and self.tooltip_widget.isVisible():
            self.tooltip_widget.hide()

    def on_checkBox_Cotas_state_changed(self, state):
        if state == Qt.Checked:
            # Atualiza o marcador do mapa para mostrar o valor de Z
            if hasattr(self, 'current_distance') and self.current_distance is not None:
                self.update_map_marker(self.current_distance)
        else:
            # Esconde o tooltip se desmarcado
            self.hide_tooltip()

    def mouse_moved(self, evt):
        """Evento chamado quando o mouse é movido sobre o gráfico."""
        if not self.all_profiles or not self.current_x_values:
            return

        pos = evt[0]  # Obter a posição do mouse do evento
        if self.plot_widget.plotItem.sceneBoundingRect().contains(pos):
            mousePoint = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            x = mousePoint.x()
            y = mousePoint.y()

            # Verificar se x está dentro do intervalo de todos os x_values
            all_x_values = [x for profile_data in self.all_profiles for segment in profile_data['profiles'] for x in segment['distances']]
            if min(all_x_values) <= x <= max(all_x_values):
                # Encontrar o perfil mais próximo do cursor em y
                min_diff = float('inf')
                closest_y_interp = None
                closest_profile_data = None

                # Percorrer todos os perfis e segmentos para encontrar o valor de y mais próximo
                for profile_data in self.all_profiles:
                    for segment in profile_data['profiles']:
                        distances = segment['distances']
                        values = segment['values']
                        if distances[0] <= x <= distances[-1]:
                            y_interp = np.interp(x, distances, values)
                            diff = abs(y - y_interp)
                            if diff < min_diff:
                                min_diff = diff
                                closest_y_interp = y_interp
                                closest_profile_data = profile_data  # Armazena o perfil correspondente

                if closest_y_interp is not None:
                    # Atualizar as linhas de referência
                    self.vLine.setPos(x)
                    self.hLine.setPos(closest_y_interp)
                    self.vLine.show()
                    self.hLine.show()

                    # Determina a cor do texto com base no estado do checkBox_PB
                    text_color = 'black' if self.checkBox_PB.isChecked() else 'white'

                    # Atualizar o texto das coordenadas com a cor apropriada
                    self.coord_text.setHtml(f'<div style="color:{text_color};">'
                                            f'<b>Elevação:</b> {closest_y_interp:.2f} m<br>'
                                            f'<b>Distância:</b> {x:.2f} m</div>')
                    self.coord_text.setPos(x, closest_y_interp)
                    self.coord_text.show()


                    # Atualizar a posição do ponto sincronizado
                    self.sync_point.setData([x], [closest_y_interp])
                    self.sync_point.show()

                    # Atualizar a posição do marcador no mapa
                    self.update_map_marker(x)

                    # Obter a cor da linha correspondente
                    if closest_profile_data:
                        layer = closest_profile_data['layer']
                        color = self.get_color_for_layer(layer)
                    else:
                        color = QColor('white')  # Cor padrão se não encontrado

                    # Mostrar o tooltip se o checkBox_Cotas estiver marcado
                    if self.checkBox_Cotas.isChecked():
                        z_value = closest_y_interp
                        self.show_tooltip_on_map(z_value, color)
                    else:
                        self.hide_tooltip()
                else:
                    # Esconder as linhas, o texto, o ponto e o marcador
                    self.vLine.hide()
                    self.hLine.hide()
                    self.coord_text.hide()
                    self.sync_point.hide()
                    self.remove_map_marker()
                    self.hide_tooltip()
            else:
                # Esconder as linhas, o texto, o ponto e o marcador
                self.vLine.hide()
                self.hLine.hide()
                self.coord_text.hide()
                self.sync_point.hide()
                self.remove_map_marker()
                self.hide_tooltip()
        else:
            # Esconder as linhas, o texto, o ponto e o marcador
            if hasattr(self, 'vLine'):
                self.vLine.hide()
            if hasattr(self, 'hLine'):
                self.hLine.hide()
            if hasattr(self, 'coord_text'):
                self.coord_text.hide()
            if hasattr(self, 'sync_point'):
                self.sync_point.hide()
            self.remove_map_marker()
            self.hide_tooltip()

    def get_color_for_layer(self, layer):
        """Retorna a cor associada a uma camada raster."""
        layer_name = layer.name()
        item = self.get_list_item_by_layer_name(layer_name)
        if item:
            color = item.data(Qt.UserRole)
            return color
        else:
            return QColor('white')  # Cor padrão se não encontrado

    def show_tooltip_on_map(self, z_value, color):
        """Mostra um tooltip flutuante no mapa com o valor de Z e a cor especificada."""
        # Inicializar o tooltip_widget se ainda não existir
        if not hasattr(self, 'tooltip_widget') or self.tooltip_widget is None:
            self.tooltip_widget = FloatingTooltip(iface.mainWindow())

        if self.current_point:
            canvas = iface.mapCanvas()

            # Converter as coordenadas do ponto para posição na tela
            screen_pos = canvas.mapSettings().mapToPixel().transform(self.current_point)
            global_pos = canvas.mapToGlobal(QPoint(int(screen_pos.x()), int(screen_pos.y())))

            # Mostrar o tooltip com o valor de Z e a cor
            self.tooltip_widget.show_tooltip(f"{z_value:.2f} m", global_pos, color)

    def get_raster_thumbnail(self, layer, max_size=100):
        """Gera uma miniatura de uma camada raster, ajustando ao formato da imagem."""
        if not isinstance(layer, QgsRasterLayer):
            return None

        # Obtém a extensão do raster
        extent = layer.extent()
        width_extent = extent.width()
        height_extent = extent.height()

        # Calcula a proporção da imagem
        if width_extent > height_extent:
            width = max_size
            height = int((height_extent / width_extent) * max_size)
        else:
            height = max_size
            width = int((width_extent / height_extent) * max_size)

        # Configura as definições do mapa
        map_settings = QgsMapSettings()
        map_settings.setLayers([layer])
        map_settings.setBackgroundColor(QColor(255, 255, 255))  # Fundo branco
        map_settings.setOutputSize(QSize(width, height))
        map_settings.setExtent(extent)

        # Cria uma imagem para renderizar o raster
        image = QImage(width, height, QImage.Format_ARGB32)
        image.fill(Qt.transparent)

        # Configura o pintor e o trabalho de renderização
        painter = QPainter(image)
        render_job = QgsMapRendererCustomPainterJob(map_settings, painter)

        # Executa o trabalho de renderização
        render_job.start()
        render_job.waitForFinished()
        painter.end()

        # Converte a imagem para PNG em memória
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        image.save(buffer, "PNG")
        buffer.close()

        # Codifica os dados da imagem em Base64
        img_base64 = base64.b64encode(buffer.data()).decode('utf-8')

        return img_base64

    def setup_raster_tooltips(self):
        """Conecta o sinal de movimento do mouse ao listWidgetRaster."""
        self.listWidgetRaster.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        """Intercepta eventos de mouse no listWidgetRaster."""
        if obj == self.listWidgetRaster.viewport() and event.type() == QEvent.ToolTip:
            # Obtém a posição do mouse
            item = self.listWidgetRaster.itemAt(event.pos())
            if item:
                # Obtém a camada correspondente ao item
                layer_name = item.text()
                layers = QgsProject.instance().mapLayersByName(layer_name)
                if layers:
                    layer = layers[0]
                    img_base64 = self.get_raster_thumbnail(layer)
                    if img_base64:
                        # Cria o HTML do tooltip com a imagem embutida
                        tooltip_html = f"<img src='data:image/png;base64,{img_base64}'>"
                        QToolTip.showText(event.globalPos(), tooltip_html, self.listWidgetRaster)
                        return True
            else:
                QToolTip.hideText()
        return super().eventFilter(obj, event)

    def _log_message(self, message, level=Qgis.Info):
        QgsMessageLog.logMessage(message, 'GRÁFICO', level=level)

    def start_profile_extraction(self):
        """Inicia a extração do perfil se uma linha e camadas raster estiverem selecionadas."""
        if not self.selected_raster_layers:
            self.plot_widget.clear()
            iface.messageBar().pushMessage("Aviso", "Nenhuma camada raster selecionada.", level=Qgis.Info)
            return

        if not hasattr(self, 'line_points') or not self.line_points:
            self.plot_widget.clear()
            iface.messageBar().pushMessage("Aviso", "Desenhe ou selecione uma linha para gerar o perfil.", level=Qgis.Info)
            return

        # Processa o perfil em uma thread
        self.thread = ProfileExtractionThread(self, self.selected_raster_layers)
        self.thread.profile_ready.connect(self.on_profile_ready)
        self.thread.start()

    def on_raster_layer_selected(self, item):
        """Callback quando um item do listWidgetRaster é alterado."""
        layer_name = item.text()
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            layer = layers[0]
            if item.checkState() == Qt.Checked:
                if layer not in self.selected_raster_layers:
                    self.selected_raster_layers.append(layer)
            else:
                if layer in self.selected_raster_layers:
                    self.selected_raster_layers.remove(layer)

        # Inicia a extração do perfil
        self.start_profile_extraction()

    def calculate_cumulative_distances(self, points):
        """
        Calcula as distâncias cumulativas ao longo da linha.
        """
        distances = []
        total_distance = 0

        for i in range(len(points)):
            if i == 0:
                distances.append(0)
            else:
                dx = points[i].x() - points[i - 1].x()
                dy = points[i].y() - points[i - 1].y()
                segment_distance = math.hypot(dx, dy)
                total_distance += segment_distance
                distances.append(total_distance)

        return distances

    def get_point_at_distance(self, distance):
        """Retorna o ponto ao longo da linha na distância cumulativa especificada."""
        if not self.line_points or not self.line_distances:
            return None

        if distance < self.line_distances[0] or distance > self.line_distances[-1]:
            return None

        for i in range(len(self.line_distances) - 1):
            d0 = self.line_distances[i]
            d1 = self.line_distances[i + 1]
            if d0 <= distance <= d1:
                # Evita divisão por zero
                if d1 - d0 == 0:
                    ratio = 0
                else:
                    ratio = (distance - d0) / (d1 - d0)
                x = self.line_points[i].x() + ratio * (self.line_points[i + 1].x() - self.line_points[i].x())
                y = self.line_points[i].y() + ratio * (self.line_points[i + 1].y() - self.line_points[i].y())
                return QgsPointXY(x, y)
        # Se a distância for exatamente a última, retorna o último ponto
        if np.isclose(distance, self.line_distances[-1]):
            return self.line_points[-1]
        return None

    def get_z_values_at_point(self, point):
        """Retorna um dicionário de valores Z das camadas raster selecionadas no ponto dado."""
        z_values = {}
        for layer in self.selected_raster_layers:
            # Transforma o ponto para o CRS da camada raster, se necessário
            raster_crs = layer.crs()
            map_crs = iface.mapCanvas().mapSettings().destinationCrs()
            if raster_crs != map_crs:
                transform = QgsCoordinateTransform(map_crs, raster_crs, QgsProject.instance())
                point_in_raster_crs = transform.transform(point)
            else:
                point_in_raster_crs = point

            ident = layer.dataProvider().identify(point_in_raster_crs, QgsRaster.IdentifyFormatValue)
            if ident.isValid():
                results = ident.results()
                value = list(results.values())[0]
                if value is not None and not np.isnan(value):
                    z_values[layer.name()] = value
                else:
                    z_values[layer.name()] = float('nan')
            else:
                z_values[layer.name()] = float('nan')
        return z_values

    def on_profile_ready(self, all_profiles):
        """Callback chamado quando o perfil está pronto."""
        self.all_profiles = all_profiles
        self.plot_profiles()
        # Chama o método para registrar os valores
        self.log_xyz_every_100m()

    def update_combobox_raster_list(self):
        """Atualiza o comboBoxListaRaster com os nomes das camadas raster cujos gráficos estão sendo exibidos."""
        self.comboBoxListaRaster.clear()  # Limpa o comboBox antes de adicionar os itens

        # Adiciona os nomes das camadas raster cujos gráficos estão no perfil
        if self.all_profiles:
            layer_names = [profile_data['layer'].name() for profile_data in self.all_profiles]
            self.comboBoxListaRaster.addItems(layer_names)

        # Caso nenhum gráfico esteja sendo exibido
        if not self.all_profiles:
            self.comboBoxListaRaster.addItem("Nenhuma camada exibida")

    def on_combobox_layer_changed(self, index):
        """
        Atualiza a tabela de dados com base na camada raster selecionada no comboBoxListaRaster.
        """
        selected_layer_name = self.comboBoxListaRaster.currentText()

        # Se nenhuma camada válida estiver selecionada, limpa a tabela
        if selected_layer_name == "Nenhuma camada exibida":
            self.tableWidget_Dados.clearContents()
            self.tableWidget_Dados.setRowCount(0)
            return

        # Gera os dados a partir do log_xyz_every_100m
        self.log_xyz_every_100m()

    def populate_table(self, data):
        """
        Preenche o tableWidget_Dados com os dados fornecidos e calcula a Inclinação.
        :param data: Lista de tuplas contendo (distância, x, y, z).
        """
        self.tableWidget_Dados.clearContents()
        self.tableWidget_Dados.setRowCount(len(data))
        self.tableWidget_Dados.setColumnCount(6)  # Agora temos 6 colunas
        self.tableWidget_Dados.setHorizontalHeaderLabels(["ID", "X", "Y", "Z", "Inclinação (%)", "Distância (m)"])

        # Inicializa variáveis para calcular a inclinação
        prev_z = None
        prev_distance = None

        for row_index, (distance, x, y, z) in enumerate(data):
            # Adiciona o ID (sequência)
            self.tableWidget_Dados.setItem(row_index, 0, QTableWidgetItem(str(row_index + 1)))

            # Adiciona X, Y, Z, e Distância
            self.tableWidget_Dados.setItem(row_index, 1, QTableWidgetItem(f"{x:.2f}"))
            self.tableWidget_Dados.setItem(row_index, 2, QTableWidgetItem(f"{y:.2f}"))
            self.tableWidget_Dados.setItem(row_index, 3, QTableWidgetItem(f"{z:.2f}" if not np.isnan(z) else "N/A"))
            self.tableWidget_Dados.setItem(row_index, 5, QTableWidgetItem(f"{distance:.2f}"))

            # Calcula a inclinação
            if row_index == 0:
                # Para o primeiro ponto, inclinação é sempre 0, exceto se Z for inválido
                inclination = 0 if not np.isnan(z) else None
            elif prev_z is None or prev_distance is None or np.isnan(z):
                # Reinicia a inclinação se Z for inválido
                inclination = None
            else:
                try:
                    # Inclinação em %: (ΔZ / ΔDistância) * 100
                    inclination = ((z - prev_z) / (distance - prev_distance)) * 100
                except ZeroDivisionError:
                    inclination = 0  # Previne divisão por zero

            # Formata inclinação como N/A se for inválida
            inclination_str = f"{inclination:.3f} %" if inclination is not None else "N/A"
            self.tableWidget_Dados.setItem(row_index, 4, QTableWidgetItem(inclination_str))

            # Atualiza valores anteriores se Z for válido
            if not np.isnan(z):
                prev_z = z
                prev_distance = distance

        # Ajusta automaticamente o tamanho das colunas
        self.tableWidget_Dados.resizeColumnsToContents()

        #  Para chamar update_second_graph após preencher a tabela
        self.update_second_graph()

    def log_xyz_every_100m(self):
        """Registra X, Y e Z a cada N metros, onde N é definido no doubleSpinBox_espaco."""
        if not hasattr(self, 'line_points') or not self.line_points:
            self._log_message("Nenhuma linha disponível para extrair os pontos.", level=Qgis.Warning)
            return

        self.tableWidget_Dados.clearContents()
        self.tableWidget_Dados.setRowCount(0)

        selected_layer_name = self.comboBoxListaRaster.currentText()
        if selected_layer_name == "Nenhuma camada exibida":
            return

        selected_layer = next(
            (layer for layer in self.selected_raster_layers if layer.name() == selected_layer_name), None
        )

        if not selected_layer:
            self._log_message(f"Camada '{selected_layer_name}' não encontrada.", level=Qgis.Warning)
            return

        total_distance = self.line_distances[-1] if self.line_distances else 0
        spacing = self.doubleSpinBox_espaco.value()

        if total_distance == 0:
            iface.messageBar().pushMessage(
                "Aviso", 
                "A linha desenhada tem comprimento zero.", 
                level=Qgis.Warning
            )
            return
        if spacing <= 0:
            iface.messageBar().pushMessage(
                "Erro", 
                "O espaçamento é zero ou negativo, não é possível amostrar.", 
                level=Qgis.Warning
            )
            return

        # Agora podemos chamar np.arange sem risco
        distances_to_sample = list(np.arange(0, total_distance, spacing)) + [total_distance]

        table_data = []
        self.graph_line_points = []  # Adicione esta linha para armazenar os pontos
        for distance in distances_to_sample:
            point = self.get_point_at_distance(distance)
            if point:
                x, y = point.x(), point.y()
                z_values = self.get_z_values_at_point(point)
                z_value = z_values.get(selected_layer_name, float('nan'))
                table_data.append((distance, x, y, z_value))
                self.graph_line_points.append(point)  # Armazena o ponto correspondente

        self.populate_table(table_data)

    def update_table_on_spacing_change(self):
        """
        Atualiza a tabela de dados ao alterar o valor do espaçamento no doubleSpinBox_espaco.
        """
        spacing = self.doubleSpinBox_espaco.value()
        if spacing <= 0:
            iface.messageBar().pushMessage(
                "Aviso", 
                "O espaçamento não pode ser zero ou negativo. Ajuste o valor.", 
                level=Qgis.Warning
            )
            return
        # Se estiver tudo ok:
        self.log_xyz_every_100m()

    def mouse_moved_second_graph(self, evt):
        """
        Evento chamado quando o mouse é movido sobre o segundo gráfico.
        Destaque o segmento entre duas IDs, exiba a inclinação rotacionada, e destaque o segmento no mapa,
        ignorando segmentos onde a inclinação é "N/A".
        """
        pos = evt[0]  # Obter a posição do mouse do evento
        if self.plot_widget2.plotItem.sceneBoundingRect().contains(pos):
            mousePoint = self.plot_widget2.plotItem.vb.mapSceneToView(pos)
            x = mousePoint.x()
            y = mousePoint.y()

            # Obter os dados do gráfico
            x_data = self.graph_x_data  # Distâncias
            y_data = self.graph_y_data  # Z (Elevação)

            if not x_data or not y_data:
                return

            # Encontrar o segmento entre duas IDs onde x está entre x_data[i] e x_data[i+1]
            for i in range(len(x_data) - 1):
                x0, x1 = x_data[i], x_data[i+1]
                y0, y1 = y_data[i], y_data[i+1]

                # Verificar se os valores de Z são válidos
                if y0 is None or y1 is None or np.isnan(y0) or np.isnan(y1):
                    continue  # Ignora este segmento

                delta_x = x1 - x0
                delta_y = y1 - y0

                # Verificar se a inclinação pode ser calculada
                if delta_x == 0 or delta_x is None or np.isnan(delta_x):
                    continue  # Ignora este segmento

                # Verifica se a posição do mouse está dentro do segmento (x0->x1)
                if x0 <= x <= x1 or x1 <= x <= x0:

                    rowcount = self.tableWidget_Dados.rowCount()
                    if (i+1) < rowcount:
                        table_inclination_item = self.tableWidget_Dados.item(i+1, 4)  # Supondo coluna 4 seja Inclinação
                    else:
                        table_inclination_item = None

                    if table_inclination_item:
                        # Lê a string exata, ex: "10.943 %"
                        inclination_str = table_inclination_item.text()
                    else:
                        # Se não houver item (ou fora de range), faz um fallback local
                        inclination_value = (delta_y / delta_x) * 100
                        # Aqui você pode escolher quantas casas exibir, ou não arredondar:
                        # inclination_str = f"{inclination_value:.3f} %"
                        inclination_str = f"{inclination_value} %"

                    # Mouse está sobre o segmento entre os pontos i e i+1
                    if hasattr(self, 'highlighted_segment_index') and self.highlighted_segment_index == i:
                        # Já está destacado, não precisa fazer nada
                        return
                    else:
                        # Remover destaque anterior (linhas, textos, etc.)
                        if self.highlighted_segment:
                            self.plot_widget2.removeItem(self.highlighted_segment)
                            self.highlighted_segment = None
                        if hasattr(self, 'inclination_text'):
                            self.plot_widget2.removeItem(self.inclination_text)
                            self.inclination_text = None
                        if self.highlighted_map_segment:
                            iface.mapCanvas().scene().removeItem(self.highlighted_map_segment)
                            self.highlighted_map_segment = None

                        # Criar uma nova linha com traço mais grosso para destacar o segmento
                        pen = pg.mkPen(color='yellow', width=4)
                        x_segment = [x0, x1]
                        y_segment = [y0, y1]
                        self.highlighted_segment = pg.PlotCurveItem(x_segment, y_segment, pen=pen)
                        self.plot_widget2.addItem(self.highlighted_segment)

                        # Armazenar o índice do segmento destacado
                        self.highlighted_segment_index = i

                        # Calcular o ângulo em graus para rotacionar o texto
                        angle_rad = math.atan2(delta_y, delta_x)
                        angle_deg = math.degrees(angle_rad)

                        # Ajustar o ângulo para manter o texto legível
                        if angle_deg < -90 or angle_deg > 90:
                            angle_deg += 180

                        # Adicionar um deslocamento para posicionar o texto acima da linha
                        offset = 0.4  # Ajuste conforme necessário para o deslocamento acima da linha
                        midpoint_x = (x0 + x1) / 2
                        midpoint_y = (y0 + y1) / 2
                        offset_x = -offset * math.sin(angle_rad)
                        offset_y = offset * math.cos(angle_rad)

                        # Adicionar o texto da inclinação ao gráfico
                        self.inclination_text = pg.TextItem(
                            text=inclination_str,  # Usa a string recuperada da tabela
                            color='white',
                            anchor=(0.5, 0.5),
                            angle=angle_deg  # Rotaciona o texto
                        )
                        self.inclination_text.setFont(QFont("Arial", 11, QFont.Bold))  # Muda o estilo do texto
                        self.plot_widget2.addItem(self.inclination_text)
                        self.inclination_text.setPos(midpoint_x + offset_x, midpoint_y + offset_y)

                        # Destacar o segmento correspondente no mapa
                        self.highlight_segment_on_map(i)

                        # Mostrar o tooltip de inclinação no mapa se o checkbox estiver marcado
                        if self.checkBox_Inclina.isChecked():
                            if hasattr(self, 'current_segment_points'):
                                point1, point2 = self.current_segment_points
                                # Calcular o ponto médio
                                midpoint_x = (point1.x() + point2.x()) / 2
                                midpoint_y = (point1.y() + point2.y()) / 2
                                midpoint = QgsPointXY(midpoint_x, midpoint_y)

                                # Converter as coordenadas do ponto para posição na tela
                                canvas = iface.mapCanvas()
                                screen_pos = canvas.mapSettings().mapToPixel().transform(midpoint)
                                global_pos = canvas.mapToGlobal(QPoint(int(screen_pos.x()), int(screen_pos.y())))

                                # Inicializar o tooltip se ainda não existir
                                if not hasattr(self, 'inclination_tooltip') or self.inclination_tooltip is None:
                                    self.inclination_tooltip = FloatingTooltip(iface.mainWindow())

                                # Mostrar o tooltip com o valor da inclinação
                                self.inclination_tooltip.show_tooltip(inclination_str, global_pos, QColor(Qt.yellow))
                        else:
                            # Esconde o tooltip se o checkbox não estiver marcado
                            if hasattr(self, 'inclination_tooltip') and self.inclination_tooltip:
                                self.inclination_tooltip.hide()

                        break  # Segmento encontrado e processado
            else:
                # Mouse está fora da área do gráfico
                if self.highlighted_segment:
                    self.plot_widget2.removeItem(self.highlighted_segment)
                    self.highlighted_segment = None
                    self.highlighted_segment_index = None
                if hasattr(self, 'inclination_text'):
                    self.plot_widget2.removeItem(self.inclination_text)
                    self.inclination_text = None
                if self.highlighted_map_segment:
                    iface.mapCanvas().scene().removeItem(self.highlighted_map_segment)
                    self.highlighted_map_segment = None

                # Esconder o tooltip de inclinação
                if hasattr(self, 'inclination_tooltip') and self.inclination_tooltip:
                    self.inclination_tooltip.hide()

    def setup_second_graph(self):
        """
        Configura o segundo gráfico no scrollAreaGrafico2.
        """
        self.plot_widget2 = pg.PlotWidget()
        self.scrollAreaGrafico2.setWidget(self.plot_widget2)

        # Configurações do gráfico
        self.plot_widget2.setBackground('k')  # Fundo preto
        self.plot_widget2.setLabel('left', 'Z (Elevação)', color='white', size='10pt')
        self.plot_widget2.setLabel('bottom', 'Distância (m)', color='white', size='10pt')
        self.plot_widget2.showGrid(x=True, y=True, alpha=0.3)  # Exibe a grade no gráfico

        # Inicializa as variáveis para dados do gráfico
        self.graph_x_data = []
        self.graph_y_data = []

        # Cria um SignalProxy para capturar o movimento do mouse
        self.proxy2 = pg.SignalProxy(self.plot_widget2.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved_second_graph)

        # Variáveis para manter o controle do segmento destacado
        self.highlighted_segment = None
        self.highlighted_segment_index = None

    def reset_table_and_graph(self):
        """
        Reseta o tableWidget_Dados e o gráfico no scrollAreaGrafico2.
        """
        # Reseta o tableWidget_Dados
        self.tableWidget_Dados.clearContents()
        self.tableWidget_Dados.setRowCount(0)
        self.tableWidget_Dados.setColumnCount(0)

        # Limpa o gráfico no scrollAreaGrafico2
        if hasattr(self, 'plot_widget2') and self.plot_widget2 is not None:
            self.plot_widget2.clear()

        # Limpa o destaque do segmento
        if self.highlighted_segment:
            self.plot_widget2.removeItem(self.highlighted_segment)
            self.highlighted_segment = None
            self.highlighted_segment_index = None

    def update_second_graph(self):
        """
        Atualiza o gráfico com os dados do tableWidget_Dados, usando a cor definida no listWidgetRaster para o raster selecionado.
        """
        if not hasattr(self, 'plot_widget2'):
            self.setup_second_graph()

        # Limpa o gráfico existente
        self.plot_widget2.clear()

        # Limpa o destaque anterior
        if self.highlighted_segment:
            self.plot_widget2.removeItem(self.highlighted_segment)
            self.highlighted_segment = None
            self.highlighted_segment_index = None

        # Recupera o nome do raster selecionado no comboBoxListaRaster
        selected_raster_name = self.comboBoxListaRaster.currentText()

        # Determina a cor associada ao raster selecionado no listWidgetRaster
        color = 'r'  # Cor padrão (vermelha)
        for index in range(self.listWidgetRaster.count()):
            item = self.listWidgetRaster.item(index)
            if item.text() == selected_raster_name:
                color = item.data(Qt.UserRole)  # Recupera a cor associada
                break

        # Recupera os dados do tableWidget_Dados
        x_data = []
        y_data = []
        valid_graph_line_points = []  # Lista para armazenar pontos válidos

        for row in range(self.tableWidget_Dados.rowCount()):
            distance_item = self.tableWidget_Dados.item(row, 5)  # Coluna de distância
            z_item = self.tableWidget_Dados.item(row, 3)  # Coluna de Z

            if distance_item and z_item:
                try:
                    distance = float(distance_item.text())
                    z_value = float(z_item.text()) if z_item.text() != "N/A" else None
                    if z_value is not None:
                        x_data.append(distance)
                        y_data.append(z_value)
                        valid_graph_line_points.append(self.graph_line_points[row])  # Adiciona o ponto correspondente
                except (ValueError, IndexError):
                    continue

        # Remova quaisquer valores None de valid_graph_line_points
        valid_graph_line_points = [p for p in valid_graph_line_points if p is not None]

        # Atualiza os dados no gráfico
        self.graph_x_data = x_data
        self.graph_y_data = y_data
        self.graph_line_points_filtered = valid_graph_line_points  # Usa apenas pontos válidos

        # Adiciona os dados ao gráfico com a cor correspondente
        if x_data and y_data:
            pen = pg.mkPen(color=color, width=2)  # Define a cor com base no raster selecionado
            self.plot_widget2.plot(x_data, y_data, pen=pen)

    def on_checkBox_Inclina_state_changed(self, state):
        """Esconde o tooltip de inclinação se o checkbox for desmarcado."""
        if state != Qt.Checked:
            if hasattr(self, 'inclination_tooltip') and self.inclination_tooltip:
                self.inclination_tooltip.hide()

    def highlight_segment_on_map(self, segment_index):
        """
        Destaca o segmento correspondente na linha do mapa.
        :param segment_index: Índice do segmento na lista de pontos da linha.
        """
        # Remover o destaque anterior se existir
        if self.highlighted_map_segment:
            iface.mapCanvas().scene().removeItem(self.highlighted_map_segment)
            self.highlighted_map_segment = None

        # Verificar se os pontos do gráfico estão disponíveis
        if not hasattr(self, 'graph_line_points_filtered') or not self.graph_line_points_filtered:
            return

        # Verificar se o índice do segmento é válido
        if segment_index < len(self.graph_line_points_filtered) - 1:
            point1 = self.graph_line_points_filtered[segment_index]
            point2 = self.graph_line_points_filtered[segment_index + 1]

            # Garantir que ambos os pontos são válidos
            if not point1 or not point2:
                return

            # Criar uma rubber band para o segmento destacado
            self.highlighted_map_segment = QgsRubberBand(iface.mapCanvas(), QgsWkbTypes.LineGeometry)
            self.highlighted_map_segment.setColor(Qt.yellow)
            self.highlighted_map_segment.setWidth(4)
            self.highlighted_map_segment.setToGeometry(QgsGeometry.fromPolylineXY([point1, point2]), None)

            # Armazenar os pontos do segmento atual
            self.current_segment_points = (point1, point2)

    def update_spinBox_maximum(self):
        """Atualiza o valor máximo do doubleSpinBox_espaco para o comprimento da linha temporária."""
        if hasattr(self, 'line_distances') and self.line_distances:
            total_length = self.line_distances[-1]  # Comprimento total da linha
            self.doubleSpinBox_espaco.setMaximum(total_length)
        else:
            self.doubleSpinBox_espaco.setMaximum(0)  # Valor padrão quando não há linha

    def create_points_layer_from_table(self):
        """
        Cria uma camada de pontos a partir dos dados no tableWidget_Dados e adiciona ao projeto.
        """
        # Verifica se há dados no tableWidget_Dados
        row_count = self.tableWidget_Dados.rowCount()
        if row_count == 0:
            iface.messageBar().pushMessage("Erro", "Tabela de dados está vazia.", level=Qgis.Warning)
            return

        # Obtém o nome base da camada a partir do comboBoxListaRaster
        selected_raster_name = self.comboBoxListaRaster.currentText()
        if selected_raster_name == "Nenhuma camada exibida":
            iface.messageBar().pushMessage("Erro", "Nenhuma camada raster selecionada.", level=Qgis.Warning)
            return
        base_layer_name = f"{selected_raster_name}_Pontos"

        # Garante que o nome da camada seja único
        existing_layer_names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
        layer_name = base_layer_name
        counter = 1
        while layer_name in existing_layer_names:
            layer_name = f"{base_layer_name}_{counter}"
            counter += 1

        # Obtém o CRS atual do projeto
        crs = iface.mapCanvas().mapSettings().destinationCrs()

        # Cria uma camada vetorial de pontos com o CRS do projeto
        layer = QgsVectorLayer(f"Point?crs={crs.authid()}", layer_name, "memory")
        if not layer.isValid():
            iface.messageBar().pushMessage("Erro", "Falha ao criar a camada de pontos.", level=Qgis.Critical)
            return

        # Configura o provedor de dados para editar a camada
        provider = layer.dataProvider()

        # Adiciona os campos baseados nas colunas do tableWidget_Dados
        field_names = [self.tableWidget_Dados.horizontalHeaderItem(col).text() for col in range(self.tableWidget_Dados.columnCount())]
        fields = [
            QgsField(name, QVariant.Double if name not in ["ID"] else QVariant.String)
            for name in field_names
        ]
        provider.addAttributes(fields)
        layer.updateFields()

        # Adiciona os pontos com atributos à camada
        features = []
        for row in range(row_count):
            try:
                # Obtem os valores das colunas diretamente do tableWidget_Dados
                attributes = []
                x = None
                y = None

                for col in range(self.tableWidget_Dados.columnCount()):
                    item = self.tableWidget_Dados.item(row, col)
                    if not item:
                        attributes.append(None)
                        continue

                    # Extrai os valores conforme o tipo da coluna
                    field_type = fields[col].type()
                    value = item.text()
                    if field_type == QVariant.Double:
                        try:
                            attributes.append(float(value.replace(" %", "")) if "%" in value else float(value))
                        except ValueError:
                            attributes.append(None)
                    elif field_type == QVariant.String:
                        attributes.append(value)
                    else:
                        attributes.append(None)

                    # Armazena X e Y separadamente para criar a geometria do ponto
                    if field_names[col] == "X":
                        x = float(value)
                    elif field_names[col] == "Y":
                        y = float(value)

                if x is None or y is None:
                    iface.messageBar().pushMessage(
                        "Erro", f"Coordenadas inválidas na linha {row + 1}.", level=Qgis.Warning
                    )
                    continue

                # Cria a feição de ponto
                point = QgsPointXY(x, y)
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPointXY(point))
                feature.setAttributes(attributes)

                features.append(feature)

            except Exception as e:
                iface.messageBar().pushMessage(
                    "Erro", f"Erro ao processar a linha {row + 1}: {str(e)}", level=Qgis.Critical
                )
                continue

        # Adiciona as feições à camada
        provider.addFeatures(features)

        # Atualiza a extensão e adiciona a camada ao projeto
        layer.updateExtents()
        QgsProject.instance().addMapLayer(layer)

        iface.messageBar().pushMessage("Sucesso", f"Camada '{layer_name}' criada com sucesso!", level=Qgis.Success)

    def setup_comboboxes(self):
        """
        Configura os comboBoxTipo e comboBoxTipo_2 com os formatos de exportação,
        texto maior e barra de rolagem com 3 itens visíveis.
        """
        # Define os formatos disponíveis para exportação
        formats = [
            "Selecione:",  # Primeira mensagem
            "*.png",       # Imagem raster
            "*.svg",       # Imagem vetorial
            "*.dxf",       # Formato CAD
            "*.pdf",       # Documento PDF
            "*.tiff",      # Imagem raster de alta qualidade
            "*.jpeg",      # Imagem raster compactada
        ]

        # Configura o comboBoxTipo
        self.comboBoxTipo.clear()
        self.comboBoxTipo.addItems(formats)
        self.comboBoxTipo.setStyleSheet("""
            QComboBox {
                font-size: 12px;  /* Tamanho do texto no ComboBox */
                padding: 4px;     /* Espaçamento interno */
            }
            QComboBox QAbstractItemView {
                font-size: 12px;  /* Tamanho do texto na lista */
                background-color: white;  /* Fundo branco */
                selection-background-color: blue;  /* Fundo ao selecionar */
                border: 1px solid lightgray;  /* Borda */
                padding: 4px;     /* Espaçamento interno */
            }
        """)
        self.comboBoxTipo.setMaxVisibleItems(3)  # Limita a exibição a 3 itens visíveis
        self.comboBoxTipo.setView(QListView())  # Habilita barra de rolagem personalizada

        # Configura o comboBoxTipo_2
        self.comboBoxTipo_2.clear()
        self.comboBoxTipo_2.addItems(formats)
        self.comboBoxTipo_2.setStyleSheet("""
            QComboBox {
                font-size: 12px;  /* Tamanho do texto no ComboBox */
                padding: 4px;     /* Espaçamento interno */
            }
            QComboBox QAbstractItemView {
                font-size: 12px;  /* Tamanho do texto na lista */
                background-color: white;  /* Fundo branco */
                selection-background-color: blue;  /* Fundo ao selecionar */
                border: 1px solid lightgray;  /* Borda */
                padding: 4px;     /* Espaçamento interno */
            }
        """)
        self.comboBoxTipo_2.setMaxVisibleItems(3)  # Limita a exibição a 3 itens visíveis
        self.comboBoxTipo_2.setView(QListView())  # Habilita barra de rolagem personalizada

    def reset_comboboxes(self):
        """
        Reseta os comboBoxTipo e comboBoxTipo_2 ao estado inicial.
        """
        self.comboBoxTipo.setCurrentIndex(0)  # Reseta para "Selecione:"
        self.comboBoxTipo_2.setCurrentIndex(0)  # Reseta para "Selecione:"
        self.update_export_button_state()

    def escolher_local_para_salvar(self, nome_padrao, tipo_arquivo):

        # Acessa as configurações do QGIS para recuperar o último diretório utilizado
        settings = QSettings()
        lastDir = settings.value("lastDir", "")  # Usa uma string vazia como padrão se não houver último diretório

        # Configura as opções da caixa de diálogo para salvar arquivos
        options = QFileDialog.Options()
        
        # Gera um nome de arquivo com um sufixo numérico caso o arquivo já exista
        base_nome_padrao, extensao = os.path.splitext(nome_padrao)
        numero = 1
        nome_proposto = base_nome_padrao
        
        # Incrementa o número no nome até encontrar um nome que não exista
        while os.path.exists(os.path.join(lastDir, nome_proposto + extensao)):
            nome_proposto = f"{base_nome_padrao}_{numero}"
            numero += 1

        # Propõe o nome completo no último diretório utilizado
        nome_completo_proposto = os.path.join(lastDir, nome_proposto + extensao)

        # Exibe a caixa de diálogo para salvar arquivos com o nome proposto
        fileName, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Camada",
            nome_completo_proposto,
            tipo_arquivo,
            options=options)

        # Verifica se um nome de arquivo foi escolhido
        if fileName:
            # Atualiza o último diretório usado nas configurações do QGIS
            settings.setValue("lastDir", os.path.dirname(fileName))

            # Assegura que o arquivo tenha a extensão correta
            if not fileName.endswith(extensao):
                fileName += extensao

        return fileName  # Retorna o caminho completo do arquivo escolhido ou None se cancelado

    def mostrar_mensagem(self, texto, tipo, duracao=3, caminho_pasta=None, caminho_arquivo=None):

        # Obtém a barra de mensagens da interface do QGIS
        bar = self.iface.messageBar()  # Acessa a barra de mensagens da interface do QGIS

        # Exibe a mensagem com o nível apropriado baseado no tipo
        if tipo == "Erro":
            # Mostra uma mensagem de erro na barra de mensagens com um ícone crítico e a duração especificada
            bar.pushMessage("Erro", texto, level=Qgis.Critical, duration=duracao)
        elif tipo == "Sucesso":
            # Cria o item da mensagem
            msg = bar.createMessage("Sucesso", texto)
            
            # Se o caminho da pasta for fornecido, adiciona um botão para abrir a pasta
            if caminho_pasta:
                botao_abrir_pasta = QPushButton("Abrir Pasta")
                botao_abrir_pasta.clicked.connect(lambda: os.startfile(caminho_pasta))
                msg.layout().insertWidget(1, botao_abrir_pasta)  # Adiciona o botão à esquerda do texto
            
            # Se o caminho do arquivo for fornecido, adiciona um botão para executar o arquivo
            if caminho_arquivo:
                botao_executar = QPushButton("Executar")
                botao_executar.clicked.connect(lambda: os.startfile(caminho_arquivo))
                msg.layout().insertWidget(2, botao_executar)  # Adiciona o botão à esquerda do texto
            
            # Adiciona a mensagem à barra com o nível informativo e a duração especificada
            bar.pushWidget(msg, level=Qgis.Info, duration=duracao)

    def export_plot(self):
        """
        Exporta o gráfico gerado pelo plot_profiles no formato selecionado no comboBoxTipo.
        """
        # Verifica se há um gráfico para exportar
        if not hasattr(self, 'plot_widget') or self.plot_widget is None:
            self.mostrar_mensagem("Nenhum gráfico para exportar.", "Erro")
            return

        # Obtém o formato selecionado no comboBoxTipo
        selected_format = self.comboBoxTipo.currentText()

        # Verifica se um formato válido foi selecionado
        if selected_format == "Selecione:":
            self.mostrar_mensagem("Por favor, selecione um formato para exportação.", "Erro")
            return

        # Define o filtro de arquivo e a extensão com base no formato selecionado
        format_mapping = {
            "*.png": ("PNG Image (*.png)", ".png"),
            "*.svg": ("SVG Image (*.svg)", ".svg"),
            "*.dxf": ("DXF Drawing (*.dxf)", ".dxf"),
            "*.tiff": ("TIFF Image (*.tiff)", ".tiff"),
            "*.jpeg": ("JPEG Image (*.jpeg *.jpg)", ".jpeg"),
            "*.pdf": ("PDF Document (*.pdf)", ".pdf")
        }

        file_filter, file_extension = format_mapping.get(selected_format, ("All Files (*)", ""))

        # Gera um nome padrão para o arquivo
        nome_padrao = "grafico_perfil" + file_extension

        # Abre a caixa de diálogo para escolher onde salvar
        file_path = self.escolher_local_para_salvar(nome_padrao, file_filter)

        # Se o usuário cancelar a ação, `file_path` será None
        if not file_path:
            return

        # Garante que o arquivo seja salvo com a extensão correta
        if not file_path.endswith(file_extension):
            file_path += file_extension

        # Exporta o gráfico no formato selecionado
        try:
            if selected_format == "*.png":
                self.export_plot_as_image(file_path, 'png')
            elif selected_format == "*.svg":
                self.export_plot_as_svg(file_path)
            elif selected_format == "*.tiff":
                self.export_plot_as_image(file_path, 'tiff')
            elif selected_format == "*.jpeg":
                self.export_plot_as_image(file_path, 'jpeg')
            elif selected_format == "*.pdf":
                self.export_plot_as_pdf(file_path)
            elif selected_format == "*.dxf":  # Certifique-se de que essa condição está incluída
                self.export_plot_as_dxf(file_path)
            else:
                self.mostrar_mensagem("Formato de exportação não suportado.", "Erro")
                return

            # Mostra uma mensagem de sucesso com o botão para abrir o arquivo ou a pasta
            self.mostrar_mensagem("Gráfico exportado com sucesso!", "Sucesso", caminho_pasta=os.path.dirname(file_path), caminho_arquivo=file_path)
        except Exception as e:
            self.mostrar_mensagem(f"Falha ao exportar o gráfico: {str(e)}", "Erro")

    def export_plot_as_dxf(self, file_path):
        if not self.all_profiles:
            raise ValueError("Nenhum perfil disponível para exportar em DXF.")

        doc = ezdxf.new(dxfversion='R2010')
        msp = doc.modelspace()

        def get_layer_color(layer_name):
            for i in range(self.listWidgetRaster.count()):
                item = self.listWidgetRaster.item(i)
                if item.text() == layer_name:
                    return item.data(Qt.UserRole)
            return QColor(255, 255, 255)

        all_distances = []
        all_values = []
        layers_info = []  # Para armazenar (nome_da_camada, true_color)

        # Exportar perfis
        for profile_data in self.all_profiles:
            layer = profile_data['layer']
            profiles = profile_data['profiles']

            color = get_layer_color(layer.name())
            true_color = (color.red() << 16) | (color.green() << 8) | color.blue()

            # Armazena info da camada para legenda, se não já armazenado
            if not any(l[0] == layer.name() for l in layers_info):
                layers_info.append((layer.name(), true_color))

            if layer.name() not in doc.layers:
                doc.layers.new(name=layer.name(), dxfattribs={'color': 7})

            for segment in profiles:
                distances = segment['distances']
                values = segment['values']

                for d, v in zip(distances, values):
                    if not np.isnan(v):
                        all_distances.append(d)
                        all_values.append(v)

                points = [(float(d), float(v)) for d, v in zip(distances, values) if not np.isnan(v)]
                if len(points) > 1:
                    msp.add_lwpolyline(
                        points,
                        dxfattribs={
                            'true_color': true_color,
                            'layer': layer.name()
                        }
                    )

        # Agora exporta os eixos, passando layers_info para a legenda
        if all_distances and all_values:
            self.exportar_eixos(msp, all_distances, all_values, layers_info)

        doc.saveas(file_path)

    def exportar_eixos(self, msp, all_distances, all_values, layers_info):

        x_min, x_max = min(all_distances), max(all_distances)
        y_min, y_max = min(all_values), max(all_values)

        intervalo_minimo_y = 10
        intervalo_y = y_max - y_min
        if intervalo_y < intervalo_minimo_y:
            centro_y = (y_max + y_min) / 2
            y_min = centro_y - intervalo_minimo_y / 2
            y_max = centro_y + intervalo_minimo_y / 2

        x_margin = (x_max - x_min) * 0.05
        y_margin = (y_max - y_min) * 0.05
        margem_minima = 1
        x_margin = max(x_margin, margem_minima)
        y_margin = max(y_margin, margem_minima)

        x_min = max(0, x_min - x_margin)
        x_max += x_margin
        y_min -= y_margin
        y_max += y_margin

        # Arredondar para inteiros
        x_min, x_max = int(x_min), int(x_max) + 1
        y_min, y_max = int(y_min), int(y_max) + 1

        if 'Eixos' not in msp.doc.layers:
            msp.doc.layers.new(name='Eixos', dxfattribs={'color': 7})

        if 'Arial' not in msp.doc.styles:
            msp.doc.styles.new('Arial', dxfattribs={'font': 'arial.ttf'})

        # Calcula a altura base do texto conforme o tamanho do menor eixo
        base_text_height = min((x_max - x_min), (y_max - y_min)) * 0.025
        if base_text_height < 0.1:
            base_text_height = 0.1

        # Ticks do eixo X
        intervalo_x = max(1, (x_max - x_min) // 10)
        x_ticks = list(range(x_min, x_max, intervalo_x))

        for x in x_ticks:
            msp.add_line((x, y_min - y_margin * 0.3), (x, y_min + y_margin * 0.3), dxfattribs={'layer': 'Eixos'})
            msp.add_text(f"{x}", dxfattribs={
                'height': base_text_height,
                'layer': 'Eixos',
                'insert': (x, y_min - y_margin * 1.5),
                'rotation': 0,
                'style': 'Arial'
            })

        # Ticks do eixo Y
        intervalo_y_axis = max(1, (y_max - y_min) // 10)
        y_ticks = list(range(y_min, y_max, intervalo_y_axis))

        # Ajuste da posição do texto do eixo Y para a esquerda da linha vermelha
        # A linha vermelha vai de x_min - x_margin*0.1 a x_min + x_margin*0.1
        # Para garantir que o texto fique sempre à esquerda, vamos colocá-lo antes de x_min - x_margin*0.1
        margem_fixa_x = x_min - x_margin * 0.25  # Posição do texto ainda mais à esquerda

        for y in y_ticks:
            msp.add_line(
                (x_min - x_margin * 0.075, y),
                (x_min + x_margin * 0.075, y),
                dxfattribs={'layer': 'Eixos', 'color': 1}
            )
            msp.add_text(f"{y}", dxfattribs={
                'height': base_text_height,
                'layer': 'Eixos',
                'insert': (margem_fixa_x, y),
                'rotation': 0,
                'style': 'Arial'
            })

        # Contorno do gráfico
        msp.add_lwpolyline([
            (x_min, y_min),
            (x_max, y_min),
            (x_max, y_max),
            (x_min, y_max),
            (x_min, y_min)
        ], dxfattribs={'layer': 'Eixos'}, close=True)

        self.adicionar_legendas_camadas(msp, layers_info, x_min, x_max, y_max, y_margin, base_text_height)

        return x_min, y_min

    def adicionar_legendas_camadas(self, msp, layers_info, x_min, x_max, y_max, y_margin, base_text_height):
        # Posição da legenda acima do retângulo
        legend_y = y_max + y_margin
        # Começar a legenda próximo de x_min
        x_pos = x_min
        # Espaço entre legendas
        spacing = (x_max - x_min)*0.1 if (x_max - x_min)*0.1 > 5 else 5
        # Tamanho da linha representativa
        line_length = (x_max - x_min)*0.05 if (x_max - x_min)*0.05 > 2 else 2

        for layer_name, true_color in layers_info:
            # Desenhar um pequeno traço para representar a linha
            msp.add_line(
                (x_pos, legend_y), 
                (x_pos+line_length, legend_y), 
                dxfattribs={'true_color': true_color, 'layer': 'Eixos'}
            )
            # Escrever o nome da camada ao lado do traço
            msp.add_text(layer_name, dxfattribs={
                'height': base_text_height,
                'layer': 'Eixos',
                'insert': (x_pos+line_length+1, legend_y),
                'rotation': 0,
                'style': 'Arial'
            })
            # Avança a posição x para a próxima legenda
            x_pos += line_length + len(layer_name)*2 + spacing

    def export_plot_as_pdf(self, file_path):
        """
        Exporta o gráfico como um arquivo PDF com uma margem fixa de 2 metros nos eixos X e Y.
        :param file_path: Caminho completo do arquivo para salvar.
        """
        if not hasattr(self, 'plot_widget') or not self.plot_widget:
            raise ValueError("Nenhum gráfico disponível para exportar.")

        # Obtém todos os itens do gráfico para extrair os dados
        x_data_all = []
        y_data_all = []
        plot_items = []

        for item in self.plot_widget.plotItem.items:
            if isinstance(item, pg.PlotDataItem):
                x_data, y_data = item.xData, item.yData
                x_data_all.extend(x_data)
                y_data_all.extend(y_data)
                plot_items.append((x_data, y_data, item.name()))

        if not x_data_all or not y_data_all:
            raise ValueError("Nenhum dado encontrado no gráfico para exportar.")

        # Configura os limites dos eixos com margem fixa de 2 metros
        margin_fixed = 2  # Margem fixa em metros
        x_min, x_max = min(x_data_all) - margin_fixed, max(x_data_all) + margin_fixed
        y_min, y_max = min(y_data_all) - margin_fixed, max(y_data_all) + margin_fixed

        # Calcula a escala em metros
        x_range = x_max - x_min
        y_range = y_max - y_min
        scale_ratio = x_range / y_range if y_range != 0 else None
        scale_text = (
            f"Escala:\n1 unidade no eixo Y (Elevação) equivale a {scale_ratio:.2f} unidades no eixo X (Distância)"
            if scale_ratio is not None else "Escala: não aplicável"
        )

        # Cria o PDF
        with PdfPages(file_path) as pdf:
            # Cria uma nova figura do matplotlib com layout horizontal maior
            fig, ax = plt.subplots(figsize=(12, 6))  # Largura maior para layout estendido

            # Adiciona os dados ao gráfico
            for x_data, y_data, label in plot_items:
                ax.plot(x_data, y_data, label=label, linewidth=1.5)

            # Configurações dos eixos com as margens fixas
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
            ax.set_title("Gráfico de Perfil", fontsize=16, fontweight='bold')
            ax.set_xlabel("Distância (m)", fontsize=12)
            ax.set_ylabel("Elevação (m)", fontsize=12)

            # Grade e legenda
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.legend(fontsize=10, loc="upper right")

            # Adiciona a escala no gráfico
            ax.text(
                0.98, 0.02, scale_text,
                fontsize=10, color='gray', ha='right', va='bottom', transform=ax.transAxes
            )

            # Adiciona o gráfico ao PDF
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

    def export_plot_as_image(self, file_path, image_format):
        """
        Exporta o gráfico como uma imagem nos formatos PNG, TIFF ou JPEG.
        :param file_path: Caminho completo do arquivo para salvar.
        :param image_format: Formato da imagem ('png', 'tiff', 'jpeg').
        """
        exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
        exporter.parameters()['width'] = 1920  # Ajusta a largura em pixels
        exporter.export(file_path)

    def export_plot_as_svg(self, file_path):
        """
        Exporta o gráfico como um arquivo SVG.
        :param file_path: Caminho completo do arquivo para salvar.
        """
        exporter = pg.exporters.SVGExporter(self.plot_widget.plotItem)
        exporter.export(file_path)

    def update_export_button_state(self):
        """
        Atualiza o estado (ativado/desativado) dos botões de exportação pushButtonExportar e pushButtonExportar_2.
        """
        selected_format = self.comboBoxTipo.currentText()
        selected_format_2 = self.comboBoxTipo_2.currentText()

        # Verifica se há gráficos plotados corretamente
        has_graph = bool(self.all_profiles and len(self.all_profiles) > 0)

        # Verifica se o formato foi selecionado
        enable_export = has_graph and selected_format != "Selecione:"
        enable_export_2 = has_graph and selected_format_2 != "Selecione:"

        # Garante que o resultado seja booleano
        self.pushButtonExportar.setEnabled(bool(enable_export))
        self.pushButtonExportar_2.setEnabled(bool(enable_export_2))

    def on_export_button_clicked(self):
        """
        Executa a lógica de exportação ao clicar no botão Exportar.
        """
        try:
            self.exportar_grafico()
        except Exception as e:
            self.mostrar_mensagem(f"Erro ao exportar gráfico: {str(e)}", "Erro")

    def export_second_graph(self):
        """
        Exporta o segundo gráfico no formato selecionado no comboBoxTipo_2.
        """
        # Verifica se o segundo gráfico existe
        if not hasattr(self, 'plot_widget2') or self.plot_widget2 is None:
            self.mostrar_mensagem("Nenhum gráfico para exportar.", "Erro")
            return

        # Obtém o formato selecionado no comboBoxTipo_2
        selected_format = self.comboBoxTipo_2.currentText()

        # Verifica se um formato válido foi selecionado
        if selected_format == "Selecione:":
            self.mostrar_mensagem("Por favor, selecione um formato para exportação.", "Erro")
            return

        # Define o filtro de arquivo e a extensão com base no formato selecionado
        format_mapping = {
            "*.png": ("PNG Image (*.png)", ".png"),
            "*.svg": ("SVG Image (*.svg)", ".svg"),
            "*.tiff": ("TIFF Image (*.tiff)", ".tiff"),
            "*.jpeg": ("JPEG Image (*.jpeg *.jpg)", ".jpeg"),
            "*.pdf": ("PDF Document (*.pdf)", ".pdf"),
            "*.dxf": ("DXF Drawing (*.dxf)", ".dxf"),  # Adicionando o DXF
        }
        file_filter, file_extension = format_mapping.get(selected_format, ("All Files (*)", ""))

        # Gera um nome padrão para o arquivo
        nome_padrao = "grafico_perfil_2" + file_extension

        # Abre a caixa de diálogo para escolher onde salvar
        file_path = self.escolher_local_para_salvar(nome_padrao, file_filter)

        # Se o usuário cancelar a ação, `file_path` será None
        if not file_path:
            return

        # Garante que o arquivo seja salvo com a extensão correta
        if not file_path.endswith(file_extension):
            file_path += file_extension

        # Exporta o gráfico no formato selecionado
        try:
            if selected_format == "*.png":
                self.export_second_graph_as_image(file_path, 'png')
            elif selected_format == "*.svg":
                self.export_second_graph_as_svg(file_path)
            elif selected_format == "*.tiff":
                self.export_second_graph_as_image(file_path, 'tiff')
            elif selected_format == "*.jpeg":
                self.export_second_graph_as_image(file_path, 'jpeg')
            elif selected_format == "*.pdf":
                self.export_second_graph_as_pdf(file_path)
            elif selected_format == "*.dxf":
                self.export_second_graph_as_dxf(file_path)
            else:
                self.mostrar_mensagem("Formato de exportação não suportado.", "Erro")
                return

            # Mostra uma mensagem de sucesso com o botão para abrir o arquivo ou a pasta
            self.mostrar_mensagem("Gráfico exportado com sucesso!", "Sucesso", caminho_pasta=os.path.dirname(file_path), caminho_arquivo=file_path)
        except Exception as e:
            self.mostrar_mensagem(f"Falha ao exportar o gráfico: {str(e)}", "Erro")

    def export_second_graph_as_image(self, file_path, image_format):
        """
        Exporta o segundo gráfico como uma imagem nos formatos PNG, TIFF ou JPEG.
        :param file_path: Caminho completo do arquivo para salvar.
        :param image_format: Formato da imagem ('png', 'tiff', 'jpeg').
        """
        exporter = pg.exporters.ImageExporter(self.plot_widget2.plotItem)
        exporter.parameters()['width'] = 1920  # Ajusta a largura em pixels
        exporter.export(file_path)

    def export_second_graph_as_svg(self, file_path):
        """
        Exporta o segundo gráfico como um arquivo SVG.
        :param file_path: Caminho completo do arquivo para salvar.
        """
        exporter = pg.exporters.SVGExporter(self.plot_widget2.plotItem)
        exporter.export(file_path)

    def export_second_graph_as_pdf(self, file_path):
        """
        Exporta o segundo gráfico como um arquivo PDF.
        :param file_path: Caminho completo do arquivo para salvar.
        """
        if not hasattr(self, 'plot_widget2') or not self.plot_widget2:
            raise ValueError("Nenhum gráfico disponível para exportar.")

        # Obtém todos os itens do gráfico para extrair os dados
        x_data_all = []
        y_data_all = []
        plot_items = []

        for item in self.plot_widget2.plotItem.items:
            if isinstance(item, pg.PlotDataItem):
                x_data, y_data = item.xData, item.yData
                x_data_all.extend(x_data)
                y_data_all.extend(y_data)
                plot_items.append((x_data, y_data, item.name()))

        if not x_data_all or not y_data_all:
            raise ValueError("Nenhum dado encontrado no gráfico para exportar.")

        # Configura os limites dos eixos com margem fixa de 2 metros
        margin_fixed = 2  # Margem fixa em metros
        x_min, x_max = min(x_data_all) - margin_fixed, max(x_data_all) + margin_fixed
        y_min, y_max = min(y_data_all) - margin_fixed, max(y_data_all) + margin_fixed

        # Calcula a escala em metros
        x_range = x_max - x_min
        y_range = y_max - y_min
        scale_ratio = x_range / y_range if y_range != 0 else None
        scale_text = (
            f"Escala:\n1 unidade no eixo Y (Elevação) equivale a {scale_ratio:.2f} unidades no eixo X (Distância)"
            if scale_ratio is not None else "Escala: não aplicável"
        )

        # Cria o PDF
        with PdfPages(file_path) as pdf:
            # Cria uma nova figura do matplotlib com layout horizontal maior
            fig, ax = plt.subplots(figsize=(12, 6))  # Largura maior para layout estendido

            # Adiciona os dados ao gráfico
            for x_data, y_data, label in plot_items:
                ax.plot(x_data, y_data, label=label, linewidth=1.5)

            # Configurações dos eixos com as margens fixas
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
            ax.set_title("Gráfico de Perfil (Gráfico Secundário)", fontsize=16, fontweight='bold')
            ax.set_xlabel("Distância (m)", fontsize=12)
            ax.set_ylabel("Elevação (m)", fontsize=12)

            # Grade e legenda
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.legend(fontsize=10, loc="upper right")

            # Adiciona a escala no gráfico
            ax.text(
                0.98, 0.02, scale_text,
                fontsize=10, color='gray', ha='right', va='bottom', transform=ax.transAxes
            )

            # Adiciona o gráfico ao PDF
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

    def export_second_graph_as_dxf(self, file_path):
        """
        Exporta o segundo gráfico como um arquivo DXF.
        :param file_path: Caminho completo do arquivo para salvar.
        """
        if not self.graph_x_data or not self.graph_y_data:
            raise ValueError("Nenhum dado disponível para exportar em DXF.")

        doc = ezdxf.new(dxfversion='R2010')
        msp = doc.modelspace()

        # Configurações de estilo e escala
        x_data = self.graph_x_data
        y_data = self.graph_y_data
        x_min, x_max = min(x_data), max(x_data)
        y_min, y_max = min(y_data), max(y_data)

        # Cor do gráfico
        color = QColor(Qt.red)  # Cor padrão
        selected_raster_name = self.comboBoxListaRaster.currentText()
        if selected_raster_name != "Nenhuma camada exibida":
            for i in range(self.listWidgetRaster.count()):
                item = self.listWidgetRaster.item(i)
                if item.text() == selected_raster_name:
                    color = item.data(Qt.UserRole)
                    break

        true_color = (color.red() << 16) | (color.green() << 8) | color.blue()

        # Criar camada no DXF para o gráfico
        layer_name = "Perfil_Gráfico_Secundário"
        if layer_name not in doc.layers:
            doc.layers.new(name=layer_name, dxfattribs={'color': 7})

        # Adicionar os pontos do gráfico como uma linha poligonal
        points = [(float(x), float(y)) for x, y in zip(x_data, y_data)]
        msp.add_lwpolyline(
            points,
            dxfattribs={'true_color': true_color, 'layer': layer_name}
        )

        # Exportar eixos e informações no gráfico
        layers_info = [(selected_raster_name, true_color)]
        self.exportar_eixos_segundo(msp, x_data, y_data, layers_info)

        # Salvar o arquivo DXF
        doc.saveas(file_path)

    def desenhar_retangulo_eixo_x(self, msp, x_min, x_max, y_min, y_margin, base_text_height):
        """
        Desenha um retângulo ao redor dos valores do eixo X com a mesma extensão do contorno do eixo
        e posiciona o texto "Distâncias" mais à esquerda do retângulo.
        :param msp: ModelSpace do DXF.
        :param x_min: Limite mínimo do eixo X.
        :param x_max: Limite máximo do eixo X.
        :param y_min: Valor mínimo do eixo Y (já com margens aplicadas).
        :param y_margin: Margem vertical calculada.
        :param base_text_height: Altura base do texto para escalonamento.
        """
        # Define a altura do retângulo ao redor dos valores do eixo X
        rect_bottom = y_min - y_margin * 2  # Margem extra abaixo do eixo
        rect_top = y_min - y_margin * 0.5  # Margem acima do texto do eixo X

        # Desenha o retângulo com a mesma extensão do contorno do eixo
        msp.add_lwpolyline([
            (x_min, rect_bottom),
            (x_max, rect_bottom),
            (x_max, rect_top),
            (x_min, rect_top),
            (x_min, rect_bottom)
        ], dxfattribs={'layer': 'Eixos_Segundo'}, close=True)

        # Adiciona o texto "Distâncias" à esquerda do retângulo
        # Posicionamos o texto um pouco antes do limite esquerdo (x_min)
        text_x = x_min - (x_max - x_min) * 0.05  # Ajuste para deixar o texto mais à esquerda
        text_y = (rect_bottom + rect_top) / 2.0  # Centralizado verticalmente no retângulo

        msp.add_text("Distâncias", dxfattribs={
            'height': base_text_height,
            'layer': 'Eixos_Segundo',
            'insert': (text_x, text_y),
            'rotation': 0,
            'style': 'Arial'
        })

    def exportar_eixos_segundo(self, msp, x_data, y_data, layers_info):
        """
        Adiciona os eixos X e Y ao gráfico secundário exportado para DXF, garantindo que a extensão do eixo X
        cubra toda a linha do gráfico com base em x_data, adicionando uma margem antes do 0, e ao final desenha
        um retângulo com o texto "Distâncias".
        """
        x_min_real, x_max_real = min(x_data), max(x_data)
        y_min, y_max = min(y_data), max(y_data)

        intervalo_minimo_y = 10
        intervalo_y = y_max - y_min
        if intervalo_y < intervalo_minimo_y:
            centro_y = (y_max + y_min) / 2
            y_min = centro_y - intervalo_minimo_y / 2
            y_max = centro_y + intervalo_minimo_y / 2

        x_margin = (x_max_real - x_min_real) * 0.05
        y_margin = (y_max - y_min) * 0.05
        margem_minima = 1
        x_margin = max(x_margin, margem_minima)
        y_margin = max(y_margin, margem_minima)

        extra_margin_x = 5
        x_min = max(-extra_margin_x, x_min_real - x_margin)
        x_max = x_max_real + x_margin
        y_min -= y_margin
        y_max += y_margin

        x_min, x_max = int(x_min), int(x_max) + 1
        y_min, y_max = int(y_min), int(y_max) + 1

        if 'Eixos_Segundo' not in msp.doc.layers:
            msp.doc.layers.new(name='Eixos_Segundo', dxfattribs={'color': 7})

        if 'Arial' not in msp.doc.styles:
            msp.doc.styles.new('Arial', dxfattribs={'font': 'arial.ttf'})

        base_text_height = min((x_max - x_min), (y_max - y_min)) * 0.025
        if base_text_height < 0.1:
            base_text_height = 0.1

        x_spacing = int(self.doubleSpinBox_espaco.value())
        if x_spacing <= 0:
            x_spacing = max(1, (x_max_real - x_min_real) // 10)

        x_ticks = list(range(int(x_min_real), int(x_max_real), x_spacing))
        if x_max_real not in x_ticks:
            x_ticks.append(x_max_real)

        # Desenho dos ticks do eixo X e linhas verticais
        for x in x_ticks:
            # Linha vertical até a linha do gráfico (se existir ponto exato)
            if x in x_data:
                y_value = y_data[x_data.index(x)]
                msp.add_line((x, y_min), (x, y_value), dxfattribs={'color': 3, 'layer': 'Eixos_Segundo'}) # amarelo

            msp.add_line((x, y_min - y_margin * 0.3), (x, y_min + y_margin * 0.3), dxfattribs={'layer': 'Eixos_Segundo'})
            msp.add_text(f"{x}", dxfattribs={
                'height': base_text_height,
                'layer': 'Eixos_Segundo',
                'insert': (x, y_min - y_margin * 1.5),
                'rotation': 0,
                'style': 'Arial'
            })

        intervalo_y_axis = max(1, (y_max - y_min) // 10)
        y_ticks = list(range(y_min, y_max, intervalo_y_axis))

        margem_fixa_x = x_min - x_margin * 0.25
        for y in y_ticks:
            msp.add_line(
                (x_min - x_margin * 0.075, y),
                (x_min + x_margin * 0.075, y),
                dxfattribs={'layer': 'Eixos_Segundo', 'color': 1}
            )
            msp.add_text(f"{y}", dxfattribs={
                'height': base_text_height,
                'layer': 'Eixos_Segundo',
                'insert': (margem_fixa_x, y),
                'rotation': 0,
                'style': 'Arial'
            })

        msp.add_lwpolyline([
            (x_min, y_min),
            (x_max, y_min),
            (x_max, y_max),
            (x_min, y_max),
            (x_min, y_min)
        ], dxfattribs={'layer': 'Eixos_Segundo'}, close=True)

        self.adicionar_legendas_camadas(msp, layers_info, x_min, x_max, y_max, y_margin, base_text_height)

        # Chama a função para desenhar o retângulo envolvendo os valores do eixo X
        self.desenhar_retangulo_eixo_x(msp, x_min, x_max, y_min, y_margin, base_text_height)

        # Desenha o retângulo de Elevação
        self.desenhar_retangulo_elevacao(msp, x_min, x_max, y_min, y_margin, base_text_height)

        # Desenha o retângulo de Inclinação
        self.desenhar_retangulo_inclinacao(msp, x_min, x_max, y_min, y_margin, base_text_height)

        # Desenha o retângulo de Desnível
        self.desenhar_retangulo_desnivel(msp, x_min, x_max, y_min, y_margin, base_text_height)

    def desenhar_retangulo_elevacao(self, msp, x_min, x_max, y_min, y_margin, base_text_height):
        """
        Desenha um segundo retângulo abaixo do retângulo de 'Distâncias' para exibir valores de Z
        presentes no tableWidget_Dados, e adiciona o texto 'Elevação' mais próximo do retângulo.
        """
        # Define a posição vertical do retângulo de Elevação logo abaixo do retângulo de Distâncias
        rect_top_elev = y_min - y_margin * 2.0  # Ajusta o topo próximo ao retângulo anterior
        rect_bottom_elev = y_min - y_margin * 3.5  # Base logo abaixo

        # Desenha o retângulo com a mesma largura do eixo X
        msp.add_lwpolyline([
            (x_min, rect_bottom_elev),
            (x_max, rect_bottom_elev),
            (x_max, rect_top_elev),
            (x_min, rect_top_elev),
            (x_min, rect_bottom_elev)
        ], dxfattribs={'layer': 'Eixos_Segundo'}, close=True)

        # Adiciona o texto "Elevação" alinhado verticalmente ao centro do retângulo
        ele_text_x = x_min - (x_max - x_min) * 0.05  # Mais próximo do retângulo
        ele_text_y = (rect_bottom_elev + rect_top_elev) / 2.0

        msp.add_text("Elevação", dxfattribs={
            'height': base_text_height,
            'layer': 'Eixos_Segundo',
            'insert': (ele_text_x, ele_text_y),
            'rotation': 0,
            'style': 'Arial'
        })

        # Agora obtém os valores de Z e suas distâncias do tableWidget_Dados
        row_count = self.tableWidget_Dados.rowCount()
        col_dist = 5  # Coluna "Distância (m)"
        col_z = 3     # Coluna "Z"

        # Posição vertical centralizada para os valores de Z dentro do retângulo
        z_text_y = (rect_bottom_elev + rect_top_elev) / 2.0

        for row in range(row_count):
            distance_item = self.tableWidget_Dados.item(row, col_dist)
            z_item = self.tableWidget_Dados.item(row, col_z)

            if distance_item and z_item:
                try:
                    dist_value = float(distance_item.text())
                    z_value = z_item.text()
                    if z_value.upper() == "N/A":
                        continue
                    z_value_float = float(z_value)

                    z_formatted = f"{z_value_float:.2f}"
                    msp.add_text(z_formatted, dxfattribs={
                        'height': base_text_height,
                        'layer': 'Eixos_Segundo',
                        'insert': (dist_value, z_text_y),
                        'rotation': 0,
                        'style': 'Arial'
                    })
                except ValueError:
                    continue

    def desenhar_retangulo_desnivel(self, msp, x_min, x_max, y_min, y_margin, base_text_height):
        """
        Desenha um retângulo para exibir valores de Desnível abaixo do retângulo de Inclinação,
        e adiciona o texto 'Desnível' à esquerda do retângulo de forma proporcional ao seu comprimento.
        """
        rect_top_desnivel = y_min - y_margin * 5.0
        rect_bottom_desnivel = y_min - y_margin * 6.5

        msp.add_lwpolyline([
            (x_min, rect_bottom_desnivel),
            (x_max, rect_bottom_desnivel),
            (x_max, rect_top_desnivel),
            (x_min, rect_top_desnivel),
            (x_min, rect_bottom_desnivel)
        ], dxfattribs={'layer': 'Eixos_Segundo'}, close=True)

        # Ajuste do texto "Desnível" proporcional ao comprimento do retângulo
        desnivel_text_x = x_min - (x_max - x_min) * 0.05  # Agora mais perto do retângulo
        desnivel_text_y = (rect_bottom_desnivel + rect_top_desnivel) / 2.0

        msp.add_text("Desnível", dxfattribs={
            'height': base_text_height,
            'layer': 'Eixos_Segundo',
            'insert': (desnivel_text_x, desnivel_text_y),
            'rotation': 0,
            'style': 'Arial'
        })

        desnivel_text_y = (rect_bottom_desnivel + rect_top_desnivel) / 2.0

        # Cálculo do Desnível
        row_count = self.tableWidget_Dados.rowCount()
        col_dist = 5  # Coluna "Distância (m)"
        col_z = 3     # Coluna "Z"

        previous_z = None
        for row in range(row_count):
            distance_item = self.tableWidget_Dados.item(row, col_dist)
            z_item = self.tableWidget_Dados.item(row, col_z)

            if distance_item and z_item:
                try:
                    dist_value = float(distance_item.text())
                    z_value = z_item.text()

                    if z_value.upper() == "N/A":
                        desnivel_value = "N/A"
                        previous_z = None
                    else:
                        z_value_float = float(z_value)
                        if previous_z is None:
                            desnivel_value = 0.0
                        else:
                            desnivel_value = z_value_float - previous_z
                        previous_z = z_value_float

                    desnivel_formatted = f"{desnivel_value:.2f}" if desnivel_value != "N/A" else "N/A"

                    msp.add_text(desnivel_formatted, dxfattribs={
                        'height': base_text_height,
                        'layer': 'Eixos_Segundo',
                        'insert': (dist_value, desnivel_text_y),
                        'rotation': 0,
                        'style': 'Arial'
                    })
                except ValueError:
                    continue

    def desenhar_retangulo_inclinacao(self, msp, x_min, x_max, y_min, y_margin, base_text_height):
        """
        Desenha um terceiro retângulo encostado abaixo do retângulo de 'Elevação' para exibir valores de Inclinação (%)
        presentes no tableWidget_Dados, com posicionamento dinâmico do texto 'Inclinação' mais próximo do retângulo.
        """
        # Coordenadas do retângulo da Inclinação encostado ao retângulo de Elevação
        rect_top_incl = y_min - y_margin * 3.5  # Topo encostado ao retângulo de Elevação
        rect_bottom_incl = y_min - y_margin * 5.0  # Base logo abaixo

        # Desenha o retângulo com a mesma largura do eixo X
        msp.add_lwpolyline([
            (x_min, rect_bottom_incl),
            (x_max, rect_bottom_incl),
            (x_max, rect_top_incl),
            (x_min, rect_top_incl),
            (x_min, rect_bottom_incl)
        ], dxfattribs={'layer': 'Eixos_Segundo'}, close=True)

        # Ajuste dinâmico da posição do texto "Inclinação"
        # Usamos, por exemplo, 1% do comprimento do retângulo para a distância à esquerda.
        incl_text_x = x_min - (x_max - x_min) * 0.05  # Ajuste conforme necessário
        incl_text_y = (rect_bottom_incl + rect_top_incl) / 2.0

        msp.add_text("Inclinação", dxfattribs={
            'height': base_text_height,
            'layer': 'Eixos_Segundo',
            'insert': (incl_text_x, incl_text_y),
            'rotation': 0,
            'style': 'Arial'
        })

        # Posição vertical para os valores de Inclinação dentro do retângulo (centralizado verticalmente)
        incl_text_y = (rect_bottom_incl + rect_top_incl) / 2.0

        # Obtém os valores de Inclinação e suas distâncias do tableWidget_Dados
        row_count = self.tableWidget_Dados.rowCount()
        col_dist = 5  # Coluna "Distância (m)"
        col_incl = 4  # Coluna "Inclinação (%)"

        for row in range(row_count):
            distance_item = self.tableWidget_Dados.item(row, col_dist)
            incl_item = self.tableWidget_Dados.item(row, col_incl)

            if distance_item and incl_item:
                try:
                    dist_value = float(distance_item.text())
                    incl_value = incl_item.text()

                    if incl_value.upper() == "N/A":
                        continue
                    incl_value_float = float(incl_value.replace("%", ""))

                    incl_formatted = f"{incl_value_float:.2f} %"
                    msp.add_text(incl_formatted, dxfattribs={
                        'height': base_text_height,
                        'layer': 'Eixos_Segundo',
                        'insert': (dist_value, incl_text_y),
                        'rotation': 0,
                        'style': 'Arial'
                    })
                except ValueError:
                    continue

class ProfileExtractionThread(QThread):
    profile_ready = pyqtSignal(list)  # Sinal para enviar o resultado do perfil

    def __init__(self, parent, raster_layers):
        super().__init__()
        self.parent = parent
        self.raster_layers = raster_layers

    def run(self):
        # Processa o perfil em background usando os pontos interpolados
        all_profiles = self.parent.extract_profiles_from_rasters(self.raster_layers)
        self.profile_ready.emit(all_profiles)

class SelectLineTool(QgsMapToolIdentifyFeature):
    def __init__(self, canvas, parent):
        super().__init__(canvas)
        self.canvas = canvas
        self.parent = parent

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Identifica todas as camadas vetoriais de linha no projeto
            layers = [
                layer for layer in QgsProject.instance().mapLayers().values()
                if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.LineGeometry
            ]

            if not layers:
                iface.messageBar().pushMessage("Erro", "Nenhuma camada de linha encontrada no projeto.", level=Qgis.Warning)
                return

            # Identifica a feição clicada em qualquer camada de linha
            results = self.identify(event.x(), event.y(), layers, self.TopDownStopAtFirst)
            if results:
                feature = results[0].mFeature
                geometry = feature.geometry()
                if geometry and geometry.type() == QgsWkbTypes.LineGeometry:
                    # Extrair os vértices da geometria da linha
                    line_points = [QgsPointXY(pt) for pt in geometry.vertices()]
                    # Armazena os pontos da linha selecionada
                    self.parent.line_points = line_points
                    # Atualizar o perfil
                    self.parent.extract_profile(line_points)

                    # Desenha a linha selecionada no mapa
                    self.parent.draw_rubber_band(line_points)

                    # Desenha a linha selecionada no mapa
                    self.parent.draw_rubber_band(line_points, color=Qt.magenta)  # Sempre magenta

                    # Inicia a extração do perfil
                    self.parent.start_profile_extraction()
                else:
                    iface.messageBar().pushMessage("Erro", "A feição selecionada não é uma linha.", level=Qgis.Warning)
            else:
                iface.messageBar().pushMessage("Erro", "Nenhuma feição encontrada no local clicado.", level=Qgis.Warning)

class ColorItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, perfil_manager=None):
        super().__init__(parent)
        self.perfil_manager = perfil_manager

    def paint(self, painter, option, index):
        """Personaliza a renderização do item com um quadradinho de cor entre o checkbox e o nome."""
        # Desenha o item padrão (inclui o checkbox)
        super().paint(painter, option, index)

        # Recupera a cor armazenada no item
        color = index.data(Qt.UserRole)
        if color:
            # Configura o retângulo para o quadradinho de cor
            rect = option.rect
            size = 12  # Tamanho do quadradinho
            color_rect = QRect(rect.left() + 20, rect.top() + (rect.height() - size) // 2, size, size)

            # Desenha o quadradinho de cor com a cor atualizada
            painter.fillRect(color_rect, color)

    def editorEvent(self, event, model, option, index):
        # Código existente
        if event.type() == QtCore.QEvent.MouseButtonPress:
            # Verificar se o clique foi no quadradinho de cor
            rect = option.rect
            size = 12
            color_rect = QtCore.QRect(rect.left() + 20, rect.top() + (rect.height() - size) // 2, size, size)
            if color_rect.contains(event.pos()):
                # Abrir o QColorDialog
                current_color = index.data(Qt.UserRole)
                new_color = QColorDialog.getColor(initial=current_color, parent=None, title="Selecione uma cor")
                if new_color.isValid():
                    # Atualizar a cor no modelo
                    model.setData(index, new_color, Qt.UserRole)
                    # Chamar update_graph_color no PerfilManager
                    if self.perfil_manager:
                        self.perfil_manager.update_graph_color(new_color, index)
                return True
        return super().editorEvent(event, model, option, index)

class LineTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, parent):
        super().__init__(canvas)
        self.canvas = canvas
        self.parent = parent
        self.points = []
        self.rubber_band = QgsRubberBand(canvas, QgsWkbTypes.LineGeometry)
        self.rubber_band.setColor(Qt.red)
        self.rubber_band.setWidth(2)
        self.is_drawing = False

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Adiciona ponto à linha
            if not self.parent.checkBoxLinha.isChecked():
                iface.messageBar().pushMessage("Aviso", "Ative o checkbox 'Desenhar Linha' para usar esta ferramenta.", level=Qgis.Info)
                return

            if not self.is_drawing:
                # Inicia um novo desenho
                self.points = []
                if self.parent.rubber_band:
                    self.parent.rubber_band.reset(QgsWkbTypes.LineGeometry)

            # Adiciona o ponto atual
            point = self.toMapCoordinates(event.pos())
            self.points.append(point)

            self.parent.draw_rubber_band(self.points, color=Qt.red)  # Sempre vermelho

            self.update_rubber_band()
            self.is_drawing = True

        elif event.button() == Qt.RightButton and self.is_drawing:
            # Conclui o desenho ao clicar com o botão direito
            self.is_drawing = False
            self.parent.extract_profile(self.points)  # Extrai o perfil
            self.parent.log_xyz_every_100m()  # Registra os pontos a cada 100 metros

    def on_profile_ready(self, all_profiles):
        """Callback chamado quando o perfil está pronto."""
        self.all_profiles = all_profiles
        self.plot_profiles()
        self.log_xyz_every_100m()  # Registra os pontos a cada 100 metros

    def canvasMoveEvent(self, event):
        # Verifica se o checkBoxLinha está marcado antes de permitir desenhar
        if not self.parent.checkBoxLinha.isChecked():
            return

        if self.is_drawing:
            # Atualiza a linha temporária conforme o mouse se move
            point = self.toMapCoordinates(event.pos())
            if len(self.points) > 0:
                self.update_rubber_band(self.points + [point])
    
    def update_rubber_band(self, points=None):
        """Atualiza a linha temporária no mapa."""
        if points is None:
            points = self.points
        if self.parent.rubber_band is None:
            self.parent.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
            self.parent.rubber_band.setColor(Qt.red)
            self.parent.rubber_band.setWidth(2)
        else:
            self.parent.rubber_band.reset(QgsWkbTypes.LineGeometry)
        if points:
            line_geometry = QgsGeometry.fromPolylineXY([QgsPointXY(p.x(), p.y()) for p in points])
            self.parent.rubber_band.setToGeometry(line_geometry, None)

    def clear_rubber_band(self):
        """Limpa a linha temporária do mapa."""
        if self.rubber_band:
            self.rubber_band.reset(QgsWkbTypes.LineGeometry)

    def deactivate(self):
        """Mantém a linha visível ao desativar a ferramenta."""
        pass  # Não faz nada para manter a linha visível

class FloatingTooltip(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLabel {
                border: none;
                background-color: rgba(0, 0, 0, 0);  /* Fundo transparente */
                font: bold 12px;
            }
        """)
        # Alteramos aqui para usar Qt.Tool em vez de Qt.ToolTip
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAlignment(Qt.AlignCenter)

    def show_tooltip(self, text, global_pos, color):
        # Define o texto com HTML para aplicar a cor
        color_name = color.name()  # Obtém a cor em formato hexadecimal
        self.setText(f'<span style="color:{color_name}">{text}</span>')
        self.setTextFormat(Qt.RichText)
        self.adjustSize()
        x = global_pos.x() - self.width() // 2 - 2
        y = global_pos.y() - self.height() - 5  # Ajuste conforme necessário
        self.move(x, y)
        self.show()

    def hide_tooltip(self):
        self.hide()
