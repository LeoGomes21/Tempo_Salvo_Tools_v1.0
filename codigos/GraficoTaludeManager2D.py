from qgis.PyQt.QtWidgets import QDialog, QCheckBox, QComboBox, QPushButton, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QTableWidget, QTableWidgetItem, QAbstractItemView, QFileDialog, QListWidgetItem, QProgressBar, QLabel
from qgis.core import QgsProject, QgsRasterLayer, QgsMapSettings, QgsMapRendererCustomPainterJob, Qgis, QgsMessageLog, QgsVectorLayer, QgsWkbTypes, QgsField, QgsFeature, QgsPointXY, QgsLayerTreeLayer, QgsGeometry, QgsRaster, QgsDistanceArea, edit, QgsVector, QgsCoordinateTransform, QgsPalLayerSettings, QgsProperty, QgsVectorLayerSimpleLabeling
from qgis.PyQt.QtGui import QImage, QPainter, QPixmap, QColor, QPainterPath, QFont
from qgis.PyQt.QtCore import Qt, QRectF, QPointF, QSize, QVariant, QTimer, QSettings
from PyQt5.QtWidgets import QGraphicsPathItem, QApplication
from pyqtgraph import InfiniteLine, TextItem
from PyQt5 import QtWidgets, QtGui, QtCore
from qgis.gui import QgsMapCanvas
from qgis.utils import iface
from qgis.PyQt import uic
import pyqtgraph as pg
import numpy as np
import ezdxf
import time
import math
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'GraficoPyQtGraphTalude.ui'))

class GraficoManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(GraficoManager, self).__init__(parent)
        # Configura a interface do usuário a partir do Designer.
        self.setupUi(self)
        # Altera o título da janela
        self.setWindowTitle("Gráfico com Talude 2D")

        # Salva as referências para a interface do QGIS e o diálogo fornecidos
        self.iface = iface

        # Cria uma cena gráfica para o QGraphicsView
        self.scene = QGraphicsScene()
        self.graphicsViewRaster.setScene(self.scene)

        # Inicializa o ComboBox de Raster e Camadas
        self.init_combo_box_raster()
        self.init_combo_box_camadas()

        # Conecta os sinais aos slots
        self.connect_signals()

        # Desativa o doubleSpinBoxDistancias inicialmente
        self.doubleSpinBoxDistancias.setEnabled(False)

        # Inicializa o timer para salvar edições após inatividade
        self.edit_timer = QTimer()
        self.edit_timer.setSingleShot(True)
        self.edit_timer.timeout.connect(self.save_layer_edits)

        # Configura a janela para permitir minimizar, maximizar e fechar
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)

    def init_combo_box_camadas(self):
        # Inicializa o combo box de camadas (linhas e polígonos)
        self.comboBoxCamadas.clear()
        self.update_combo_box_camadas()

    def init_combo_box_raster(self):
        # Armazena o ID da camada raster atualmente selecionada
        current_raster_id = self.comboBoxRaster.currentData()
        
        # Obtém todas as camadas do projeto atual
        layers = QgsProject.instance().mapLayers().values()
        
        # Filtra apenas camadas raster
        raster_layers = [layer for layer in layers if isinstance(layer, QgsRasterLayer)]
        
        # Limpa o ComboBox antes de adicionar itens
        self.comboBoxRaster.clear()
        
        # Adiciona as camadas raster ao ComboBox
        for raster_layer in raster_layers:
            self.comboBoxRaster.addItem(raster_layer.name(), raster_layer.id())
        
        # Restaura a seleção anterior, se possível
        if current_raster_id:
            index = self.comboBoxRaster.findData(current_raster_id)
            if index != -1:
                self.comboBoxRaster.setCurrentIndex(index)
            else:
                # Seleciona a última camada raster, se existir
                if raster_layers:
                    self.comboBoxRaster.setCurrentIndex(self.comboBoxRaster.count() - 1)
        else:
            # Seleciona a última camada raster, se existir
            if raster_layers:
                self.comboBoxRaster.setCurrentIndex(self.comboBoxRaster.count() - 1)
        
        # Atualiza a exibição do raster
        self.display_raster()

    def update_combo_box_raster(self, layers):
        """Atualiza o comboBoxRaster quando novas camadas são adicionadas ao projeto."""
        # Verifica se há novas camadas raster entre as adicionadas
        raster_layers_added = [layer for layer in layers if isinstance(layer, QgsRasterLayer)]
        if raster_layers_added:
            # Atualiza o comboBoxRaster
            self.init_combo_box_raster()
            # Seleciona a última camada raster adicionada
            self.comboBoxRaster.setCurrentIndex(self.comboBoxRaster.count() - 1)
            # Atualiza a exibição do raster
            self.display_raster()

    def connect_signals(self):

        # Conecta o sinal de adição de camada raster
        QgsProject.instance().layersAdded.connect(self.update_combo_box_raster)

        # Conecta os sinais aos slots
        self.comboBoxRaster.currentIndexChanged.connect(self.display_raster)

        # Conecta o sinal de remoção de camada
        QgsProject.instance().layersRemoved.connect(self.update_combo_box)

        # Desconectar todos os sinais para evitar múltiplas conexões
        try:
            QgsProject.instance().layersAdded.disconnect(self.handle_layers_added)
        except TypeError:
            pass  # O sinal não estava conectado anteriormente

        # Conecta os RadioButtons para selecionar linhas ou pontos
        self.radioButtonLinhas.clicked.connect(self.update_combo_box_camadas)
        self.radioButtonPontos.clicked.connect(self.update_combo_box_camadas)

        # Conecta os RadioButtons ao método que seleciona a aba no tabWidget
        self.radioButtonLinhas.toggled.connect(self.selecionar_aba_tab_widget)
        self.radioButtonPontos.toggled.connect(self.selecionar_aba_tab_widget)

        # Conecta o sinal de alteração do comboBoxCamadas para carregar atributos
        self.comboBoxCamadas.currentIndexChanged.connect(self.load_layer_attributes)

        # Conecta o sinal de alteração do nome da camada
        for layer in QgsProject.instance().mapLayers().values():
            layer.nameChanged.connect(self.update_combo_box)

        # Conecta o sinal de seleção no tableWidgetLista
        self.tableWidgetLista.itemSelectionChanged.connect(self.table_selection_changed)

        self.tableWidgetLista.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableWidgetLista.setSelectionMode(QAbstractItemView.MultiSelection)

        # Conecta os RadioButtons para selecionar linhas ou pontos
        self.radioButtonLinhas.toggled.connect(self.update_doubleSpinBoxDistancias_state)
        
        # Conecta o sinal de alteração do comboBoxCamadas para carregar atributos
        self.comboBoxCamadas.currentIndexChanged.connect(self.update_doubleSpinBoxDistancias_state)

        # Conecta o botão pushButtonCalcular ao cálculo dos pontos
        self.pushButtonCalcular.clicked.connect(self.calcular_pontos)

        # Conecta o sinal de mudança de valor do doubleSpinBoxDistancias
        self.doubleSpinBoxDistancias.valueChanged.connect(self.verificar_condicoes_calcular)

        # Conecta o sinal de mudança de seleção no tableWidgetLista
        self.tableWidgetLista.itemSelectionChanged.connect(self.verificar_condicoes_calcular)

        # Conecta o botão pushButtonGerar ao método gerar_pontos_com_z
        self.pushButtonGerar.clicked.connect(self.gerar_pontos_com_z)
        
        # Atualiza o comboBoxGrupoZ quando uma nova camada é adicionada
        QgsProject.instance().layersAdded.connect(self.update_combo_box_grupo_z)
        
        # Atualiza o comboBoxGrupoZ quando uma camada é removida
        QgsProject.instance().layersRemoved.connect(self.update_combo_box_grupo_z)
        
        # Atualiza o comboBoxGrupoZ quando o nome de uma camada é alterado
        for layer in QgsProject.instance().mapLayers().values():
            layer.nameChanged.connect(self.update_combo_box_grupo_z)

        # Conecta o comboBoxGrupoZ à função que carrega atributos no tableWidgetLista2
        self.comboBoxGrupoZ.currentIndexChanged.connect(self.load_layer_attributes_grupo_z)

        # Conecta a seleção do tableWidgetLista2 ao método que sincroniza com a camada
        self.tableWidgetLista2.itemSelectionChanged.connect(self.table_selection_changed_grupo_z)

        # Update the comboBoxGrupoZ when a layer is about to be removed
        QgsProject.instance().layersWillBeRemoved.connect(self.limpar_tableWidgetLista2)

        # Conecta o sinal de remoção de camada
        QgsProject.instance().layersRemoved.connect(self.update_combo_box_camadas)

        # Conecta o sinal de adição de camada
        QgsProject.instance().layersAdded.connect(self.update_combo_box_camadas)

        # Conecta o sinal de alteração do nome da camada
        for layer in QgsProject.instance().mapLayers().values():
            layer.nameChanged.connect(self.update_combo_box_camadas)

        # Conecta as alterações dos doubleSpinBoxHinicial e doubleSpinBoxHFinal
        self.doubleSpinBoxHinicial.valueChanged.connect(self.on_spinbox_value_changed)
        self.doubleSpinBoxHFinal.valueChanged.connect(self.on_spinbox_value_changed)

        # Conecta a mudança de aba no tabWidget
        self.tabWidget.currentChanged.connect(self.on_tab_changed)

        # Conecta o evento de alteração de seleção ao verificar as condições para o pushButtonGerar
        self.tableWidgetLista.itemSelectionChanged.connect(self.verificar_estado_pushButtonGerar)

        # #conectar este método ao sinal currentIndexChanged do comboBoxGrupoZ
        self.comboBoxGrupoZ.currentIndexChanged.connect(self.handle_support_points_layer)

        # Conecta as alterações do Corte/Aterro Inicial e Final
        self.tableWidgetLista2.cellChanged.connect(self.update_graph_from_table_widget)

        #Conecta a alteração da cor do fundo do Gráfico
        self.checkBoxFundo.stateChanged.connect(self.update_graph_background_color)

        #Conecta o pushButtonExportarDXF
        self.pushButtonExportarDXF.clicked.connect(self.exportar_dxf)

        # Conectar o botão pushButtonDel à função delete_selected_layer
        self.pushButtonDel.clicked.connect(self.delete_selected_layer)

        # Conecta o botão pushButtonFechar ao método de fechamento
        self.pushButtonFechar.clicked.connect(self.close_dialog)

    def display_raster(self):
        # Limpa a cena antes de adicionar um novo item
        self.scene.clear()

        # Garantir que a cena do graphicsViewRaster seja independente
        self.scene = QGraphicsScene()  # Esta é a cena do raster
        self.graphicsViewRaster.setScene(self.scene)

        # Obtém o ID da camada raster selecionada
        selected_raster_id = self.comboBoxRaster.currentData()

        # Busca a camada raster pelo ID
        selected_layer = QgsProject.instance().mapLayer(selected_raster_id)
        
        if isinstance(selected_layer, QgsRasterLayer):
            # Configurações do mapa
            map_settings = QgsMapSettings()
            map_settings.setLayers([selected_layer])  # Definimos a camada a ser renderizada
            map_settings.setBackgroundColor(QColor(255, 255, 255))
            
            # Define o tamanho da imagem a ser renderizada
            width = self.graphicsViewRaster.viewport().width()
            height = self.graphicsViewRaster.viewport().height()
            map_settings.setOutputSize(QSize(width, height))
            
            # Define a extensão do mapa (extensão do raster)
            map_settings.setExtent(selected_layer.extent())

            # Cria a imagem para renderizar
            image = QImage(width, height, QImage.Format_ARGB32)
            image.fill(Qt.transparent)

            # Configura o pintor e a tarefa de renderização
            painter = QPainter(image)
            render_job = QgsMapRendererCustomPainterJob(map_settings, painter)

            # Executa a renderização
            render_job.start()
            render_job.waitForFinished()
            painter.end()

            # Cria um pixmap a partir da imagem renderizada
            pixmap = QPixmap.fromImage(image)
            pixmap_item = QGraphicsPixmapItem(pixmap)

            # Adiciona o item à cena
            self.scene.addItem(pixmap_item)

            # Ajusta a cena ao QGraphicsView, garantindo que o modo de ajuste preserve a proporção
            self.graphicsViewRaster.setSceneRect(pixmap_item.boundingRect())
            self.graphicsViewRaster.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def _log_message(self, message, level=Qgis.Info):
        QgsMessageLog.logMessage(message, 'GRAFICO', level=level)

    def showEvent(self, event):
        """
        Sobrescreve o evento de exibição do diálogo para resetar os Widgets.
        """
        super(GraficoManager, self).showEvent(event)

        # Ajusta a visualização quando o diálogo é mostrado
        self.display_raster()

        # Reseta o gráfico no scrollAreaGrafico
        self.reset_scroll_area_grafico()

        # # Bloqueia sinais para evitar chamadas desnecessárias
        # self.comboBoxGrupoZ.blockSignals(True)

        # Reseta os controles e atualiza o comboBoxGrupoZ
        self.reset_controls()
        self.update_combo_box_grupo_z()

        # # Desbloqueia sinais após a atualização
        # self.comboBoxGrupoZ.blockSignals(False)

        # Chamar handle_support_points_layer() para carregar os dados
        self.handle_support_points_layer()

        # Resetar o listWidgetInfo ao reiniciar o diálogo
        self.listWidgetInfo.clear()

        # Verificar se o gráfico está presente e recarregar as informações, se necessário
        if hasattr(self, 'graphWidget') and self.graphWidget is not None:
            # Recarregar informações do gráfico no listWidgetInfo
            self.recarregar_informacoes_do_grafico()

    def reset_controls(self):
        """Função responsável por resetar os botões e widgets."""
        
        # Reseta os RadioButtons
        self.radioButtonLinhas.setChecked(False)
        self.radioButtonPontos.setChecked(False)

        # Reseta o doubleSpinBoxDistancias para o valor mínimo e desativa
        self.doubleSpinBoxDistancias.setValue(self.doubleSpinBoxDistancias.minimum())
        self.doubleSpinBoxDistancias.setEnabled(False)

        # Reseta o checkBoxFinal (desmarcado)
        self.checkBoxFinal.setChecked(False)

        # Define o fundo como branco por padrão
        self.checkBoxFundo.setChecked(True)

        # Define a exportação da Tabela para DXF por padrão
        self.checkBoxTabela.setChecked(True)

        # Desativa o botão pushButtonCalcular
        self.pushButtonCalcular.setEnabled(False)

        # Desativa o botão pushButtonGerar
        self.pushButtonGerar.setEnabled(False)

        # Desativa o botão pushButtonExportarDXF por padrão
        self.pushButtonExportarDXF.setEnabled(False)

        # Atualiza o comboBoxCamadas e o estado do doubleSpinBoxDistancias
        self.update_combo_box_camadas()
        self.update_doubleSpinBoxDistancias_state()

        # Define os spin boxes a partir do tableWidgetLista2
        self.set_spinboxes_from_tablewidget()

    def handle_layers_added(self, layers):
        # Chama a função de atualização quando novas camadas são adicionadas
        # self._log_message("Layers added: " + ", ".join([layer.name() for layer in layers]))
        self.update_combo_box()
        
        # Atualiza o comboBox de camadas de acordo com a seleção do RadioButton
        self.update_combo_box_camadas()

    def update_combo_box(self):
        """Atualiza o comboBox de camadas quando uma camada é removida ou renomeada"""
        # Armazena o índice atual do comboBox para restaurar depois
        current_index = self.comboBoxCamadas.currentIndex()
        current_layer_id = self.comboBoxCamadas.itemData(current_index)

        # Atualiza o comboBox de camadas (Linhas ou Pontos)
        self.update_combo_box_camadas()

        # Tenta restaurar a seleção anterior
        if current_layer_id:
            index = self.comboBoxCamadas.findData(current_layer_id)
            if index != -1:
                self.comboBoxCamadas.setCurrentIndex(index)
            else:
                # Se a camada não existe mais, seleciona a primeira disponível
                if self.comboBoxCamadas.count() > 0:
                    self.comboBoxCamadas.setCurrentIndex(0)

    def load_layer_attributes(self):
        # Limpa o tableWidgetLista antes de adicionar novos itens
        self.tableWidgetLista.clearContents()
        self.tableWidgetLista.setRowCount(0)

        # Obtém o ID da camada selecionada no comboBoxCamadas
        selected_layer_id = self.comboBoxCamadas.currentData()

        # Busca a camada pelo ID
        selected_layer = QgsProject.instance().mapLayer(selected_layer_id)

        if isinstance(selected_layer, QgsVectorLayer):
            # Salva a camada selecionada para uso posterior
            self.selected_layer = selected_layer

            # Desconecta o sinal selectionChanged da camada anterior, se existir
            try:
                self.selected_layer.selectionChanged.disconnect(self.layer_selection_changed)
            except TypeError:
                pass

            # Conecta o sinal selectionChanged da camada atual
            self.selected_layer.selectionChanged.connect(self.layer_selection_changed)

            # Obtém os campos (atributos) da camada
            fields = selected_layer.fields()

            # Define o número de colunas com base no número de campos
            self.tableWidgetLista.setColumnCount(len(fields))

            # Configura o cabeçalho da tabela com os nomes dos campos
            self.tableWidgetLista.setHorizontalHeaderLabels([field.name() for field in fields])

            # Inicializa uma lista para armazenar os IDs das feições correspondentes às linhas da tabela
            self.feature_ids = []

            # Itera sobre as feições da camada e adiciona os atributos à tabela
            for row_idx, feature in enumerate(selected_layer.getFeatures()):
                # Armazena o ID da feição
                self.feature_ids.append(feature.id())

                # Define o número de linhas dinamicamente
                self.tableWidgetLista.insertRow(row_idx)

                # Itera sobre cada campo da feição e adiciona o valor correspondente à célula da tabela
                for col_idx, field in enumerate(fields):
                    # Obtém o valor do campo da feição
                    field_value = str(feature[field.name()])
                    # Cria um item na célula da tabela
                    item = QTableWidgetItem(field_value)
                    # Desabilita a edição do item
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    # Armazena o ID da feição nos dados do item (apenas na primeira coluna)
                    if col_idx == 0:
                        item.setData(Qt.UserRole, feature.id())
                    # Adiciona o item à tabela na posição correta
                    self.tableWidgetLista.setItem(row_idx, col_idx, item)

            # Ajusta automaticamente o tamanho das colunas e das linhas
            self.tableWidgetLista.resizeRowsToContents()
            self.tableWidgetLista.resizeColumnsToContents()

            # Ajusta manualmente o espaçamento para deixar as colunas e linhas mais próximas
            for row in range(self.tableWidgetLista.rowCount()):
                self.tableWidgetLista.setRowHeight(row, 18)

            for col in range(self.tableWidgetLista.columnCount()):
                self.tableWidgetLista.setColumnWidth(col, 100)

            # Log para verificar se as feições foram carregadas corretamente
            # self._log_message(f"Camada {selected_layer.name()} carregada com {selected_layer.featureCount()} feições.")

            # Sincroniza a seleção inicial
            self.layer_selection_changed(self.selected_layer.selectedFeatureIds(), [], False)

            # A verificação do estado do pushButtonGerar**
            self.verificar_estado_pushButtonGerar()

            # Atualiza o estado do doubleSpinBoxDistancias
            self.update_doubleSpinBoxDistancias_state()

    def table_selection_changed(self):
        if not hasattr(self, 'selected_layer'):
            return

        # Desconecta o sinal selectionChanged da camada para evitar recursão
        self.selected_layer.selectionChanged.disconnect(self.layer_selection_changed)

        # Obtém as linhas selecionadas na tabela
        selected_rows = self.tableWidgetLista.selectionModel().selectedRows()

        # Obtém os IDs das feições correspondentes às linhas selecionadas
        selected_feature_ids = []
        for index in selected_rows:
            row = index.row()
            # Obtém o ID da feição armazenado nos dados do item da primeira coluna
            item = self.tableWidgetLista.item(row, 0)
            if item:
                feature_id = item.data(Qt.UserRole)
                if feature_id is not None:
                    selected_feature_ids.append(feature_id)

        # Seleciona as feições na camada
        self.selected_layer.selectByIds(selected_feature_ids)

        # Reconecta o sinal selectionChanged da camada
        self.selected_layer.selectionChanged.connect(self.layer_selection_changed)
  
    def set_label_for_layer(self, layer, field_name):
        """
        Configura o rótulo para uma camada no QGIS, com base em um campo específico e formatações adicionais.
        """
        label_settings = QgsPalLayerSettings()
        label_settings.drawBackground = True  # Ativa o fundo do rótulo
        label_settings.fieldName = field_name  # Define o campo a ser rotulado

        # Configura a formatação do texto
        text_format = label_settings.format()
        font = text_format.font()
        font.setItalic(True)
        font.setBold(True)
        text_format.setFont(font)

        # Configura a cor do rótulo com base em uma expressão condicional
        color_expression = """CASE
                                WHEN "Desnivel" < 0 THEN '255,0,0'  -- Vermelho
                                WHEN "Desnivel" > 0 THEN '0,0,255'  -- Azul
                                ELSE '0,0,0'  -- Preto
                              END"""

        properties = label_settings.dataDefinedProperties()
        properties.setProperty(QgsPalLayerSettings.Color, QgsProperty.fromExpression(color_expression))

        # Defina o tamanho da fonte usando propriedades definidas por dados
        properties.setProperty(QgsPalLayerSettings.Size, QgsProperty.fromValue(8))
        label_settings.setDataDefinedProperties(properties)

        # Configura o fundo branco para os rótulos
        background_color = text_format.background()
        background_color.setEnabled(True)
        background_color.setFillColor(QColor(255, 255, 255))
        text_format.setBackground(background_color)

        label_settings.setFormat(text_format)

        # Ativa o rótulo para a camada
        layer.setLabelsEnabled(True)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        layer.triggerRepaint()

    def layer_selection_changed(self, selected_feature_ids, deselected_feature_ids, clear_and_select):
        # Bloqueia os sinais do tableWidget para evitar recursão
        self.tableWidgetLista.blockSignals(True)

        # Limpa a seleção atual na tabela
        self.tableWidgetLista.clearSelection()

        # Seleciona as linhas correspondentes às feições selecionadas
        for feature_id in selected_feature_ids:
            if feature_id in self.feature_ids:
                row = self.feature_ids.index(feature_id)
                self.tableWidgetLista.selectRow(row)

        # Desbloqueia os sinais do tableWidget
        self.tableWidgetLista.blockSignals(False)

    def update_doubleSpinBoxDistancias_state(self):
        # Verifica se o radioButtonLinhas está selecionado
        if self.radioButtonLinhas.isChecked():
            # Verifica se há uma camada selecionada no comboBoxCamadas
            selected_layer_id = self.comboBoxCamadas.currentData()
            selected_layer = QgsProject.instance().mapLayer(selected_layer_id)

            if isinstance(selected_layer, QgsVectorLayer):
                # Verifica se a camada possui feições
                if selected_layer.featureCount() > 0:
                    # Ativa o doubleSpinBoxDistancias
                    self.doubleSpinBoxDistancias.setEnabled(True)
                    return  # Sai da função se todas as condições forem atendidas

        # Se qualquer condição não for atendida, desativa o doubleSpinBoxDistancias
        self.doubleSpinBoxDistancias.setEnabled(False)

    def calcular_pontos(self):
        """Calcula os pontos ao longo das feições de linha com base na distância e adiciona ao mapa."""
        
        # Verifica se há uma camada selecionada e se é uma camada de linhas
        if not hasattr(self, 'selected_layer') or not isinstance(self.selected_layer, QgsVectorLayer):
            # self._log_message("Nenhuma camada de linhas foi selecionada.", level=Qgis.Warning)
            return

        # Verifica se há feições selecionadas no tableWidgetLista
        selected_rows = self.tableWidgetLista.selectionModel().selectedRows()
        if not selected_rows:
            # self._log_message("Nenhuma feição de linha foi selecionada.", level=Qgis.Warning)
            return

        # Obtém o valor da distância a partir do doubleSpinBoxDistancias
        distancia = self.doubleSpinBoxDistancias.value()
        if distancia <= 0:
            # self._log_message("A distância deve ser maior que 0.", level=Qgis.Warning)
            return

        # Itera sobre as feições selecionadas para gerar uma camada de pontos por feição
        for index in selected_rows:
            row = index.row()
            # Obtém o ID da feição a partir do item do tableWidget
            item = self.tableWidgetLista.item(row, 0)
            if item:
                feature_id = item.data(Qt.UserRole)
                feature = self.selected_layer.getFeature(feature_id)

                # Verifica se a feição tem geometria de linha válida
                if feature.geometry().isMultipart():
                    geometria_linha = feature.geometry().asMultiPolyline()[0]  # Usando a primeira parte da linha multipart
                else:
                    geometria_linha = feature.geometry().asPolyline()

                if len(geometria_linha) < 2:
                    continue  # Pula linhas inválidas ou muito curtas

                # Gerar o nome da camada de pontos baseado no ID da feição
                nome_cam_pontos_base = f"{self.selected_layer.name()}_ID{feature_id}"
                nome_cam_pontos = self._gerar_nome_cam_pontos_unico(nome_cam_pontos_base)

                # Criar uma nova camada de pontos para essa feição
                crs = self.selected_layer.crs()  # Utiliza o CRS da camada de linhas
                pontos_layer = QgsVectorLayer("Point?crs={}".format(crs.authid()), nome_cam_pontos, "memory")
                pontos_layer_provider = pontos_layer.dataProvider()

                # Definir os campos na camada de pontos: ID1 (id_linha), ID2 (id_ponto), X, Y
                pontos_layer_provider.addAttributes([
                    QgsField("ID_Linha", QVariant.Int),  # ID1 = ID da feição de linha
                    QgsField("ID", QVariant.Int),  # ID2 = ID do ponto gerado
                    QgsField("coord_x", QVariant.Double),
                    QgsField("coord_y", QVariant.Double)
                ])
                pontos_layer.updateFields()

                comprimento_total = feature.geometry().length()
                pontos = []

                # Adiciona pontos ao longo da linha com base na distância
                distancia_acumulada = 0.0
                ponto_id = 1  # ID do ponto a ser incrementado
                while distancia_acumulada < comprimento_total:
                    ponto = feature.geometry().interpolate(distancia_acumulada)
                    pontos.append((ponto, distancia_acumulada))  # Armazena o ponto e a distância
                    distancia_acumulada += distancia

                # Se o checkboxFinal estiver marcado, adiciona um ponto no final da linha
                if self.checkBoxFinal.isChecked():
                    ponto_final = feature.geometry().interpolate(comprimento_total)
                    pontos.append((ponto_final, comprimento_total))

                # Adiciona os pontos à nova camada de pontos
                for ponto, dist in pontos:
                    if ponto.isNull():
                        continue  # Pula pontos inválidos

                    nova_feature = QgsFeature(pontos_layer.fields())
                    nova_feature.setGeometry(ponto)

                    # Extrai as coordenadas X e Y do ponto, arredondando para 3 casas decimais
                    coord_x = round(ponto.asPoint().x(), 3)
                    coord_y = round(ponto.asPoint().y(), 3)

                    # Define os atributos: ID1 (id_linha), ID2 (id_ponto), X, Y
                    nova_feature.setAttributes([feature.id(), ponto_id, coord_x, coord_y])
                    pontos_layer_provider.addFeature(nova_feature)

                    ponto_id += 1  # Incrementa o ID do ponto

                # Atualiza a camada de pontos
                pontos_layer.updateExtents()

                # Adiciona a camada de pontos ao projeto
                QgsProject.instance().addMapLayer(pontos_layer)
                self.mostrar_mensagem(f"Camada de pontos '{nome_cam_pontos}' gerada e adicionada ao mapa.", "Sucesso")

        # Verifica novamente as condições após o cálculo
        self.verificar_condicoes_calcular()

    def _gerar_nome_cam_pontos_unico(self, nome_base):
        """Gera um nome único para a camada de pontos, adicionando um sufixo numérico se necessário."""
        nome_unico = nome_base
        contador = 1

        # Verifica se já existe uma camada com o nome fornecido
        while QgsProject.instance().mapLayersByName(nome_unico):
            nome_unico = f"{nome_base}_{contador}"
            contador += 1

        return nome_unico

    def mostrar_mensagem(self, texto, tipo, duracao=3, caminho_pasta=None, caminho_arquivo=None):
        """
        Exibe uma mensagem na barra de mensagens do QGIS
        """
        # Obtém a barra de mensagens da interface do QGIS
        bar = iface.messageBar()  # Acessa a barra de mensagens da interface do QGIS

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

    def verificar_condicoes_calcular(self):
        """Verifica se o botão Calcular deve ser ativado ou desativado."""
        
        # Verifica se há uma camada selecionada no comboBoxCamadas
        selected_layer_id = self.comboBoxCamadas.currentData()
        selected_layer = QgsProject.instance().mapLayer(selected_layer_id)

        # Verifica se a camada selecionada é uma camada de pontos e desativa o botão se for
        if isinstance(selected_layer, QgsVectorLayer) and selected_layer.geometryType() == QgsWkbTypes.PointGeometry:
            self.pushButtonCalcular.setEnabled(False)
            return

        # Verifica se o valor do doubleSpinBoxDistancias é maior que 0
        distancia_valida = self.doubleSpinBoxDistancias.value() > 0
        
        # Verifica se há pelo menos uma linha selecionada no tableWidgetLista
        selected_rows = self.tableWidgetLista.selectionModel().selectedRows()
        linha_selecionada = len(selected_rows) > 0
        
        # Verifica se as feições selecionadas possuem ID válido
        for index in selected_rows:
            row = index.row()
            item = self.tableWidgetLista.item(row, 0)
            if item is None or item.data(Qt.UserRole) is None:
                # Exibe a mensagem de erro se a feição não contiver ID
                self.mostrar_mensagem("Feição selecionada não contém ID.", "Erro")
                self.pushButtonCalcular.setEnabled(False)  # Desativa o botão se o ID for inválido
                return
        
        # Se ambas as condições forem verdadeiras, ativa o botão Calcular
        if distancia_valida and linha_selecionada:
            self.pushButtonCalcular.setEnabled(True)
        else:
            self.pushButtonCalcular.setEnabled(False)

    def carregar_atributos_tableWidgetLista2(self, camada):
        """Carrega os atributos da camada no tableWidgetLista2."""
        
        # Limpa o tableWidgetLista2 antes de adicionar novos itens
        self.tableWidgetLista2.clearContents()
        self.tableWidgetLista2.setRowCount(0)

        if isinstance(camada, QgsVectorLayer):
            # Obtém os campos (atributos) da camada
            fields = camada.fields()

            # Define o número de colunas com base no número de campos
            self.tableWidgetLista2.setColumnCount(len(fields))

            # Configura o cabeçalho da tabela com os nomes dos campos
            self.tableWidgetLista2.setHorizontalHeaderLabels([field.name() for field in fields])

            # Itera sobre as feições da camada e adiciona os atributos à tabela
            for row_idx, feature in enumerate(camada.getFeatures()):
                # Define o número de linhas dinamicamente
                self.tableWidgetLista2.insertRow(row_idx)

                # Itera sobre cada campo da feição e adiciona o valor correspondente à célula da tabela
                for col_idx, field in enumerate(fields):
                    field_value = str(feature[field.name()])
                    item = QTableWidgetItem(field_value)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    self.tableWidgetLista2.setItem(row_idx, col_idx, item)

            # Ajusta automaticamente o tamanho das colunas e das linhas
            self.tableWidgetLista2.resizeRowsToContents()
            self.tableWidgetLista2.resizeColumnsToContents()

    def _get_z_value_from_raster(self, raster_layer, x, y, point_crs):
        """Obtém o valor Z do raster no ponto (x, y)."""
        # Converte a coordenada para o CRS do raster se necessário
        raster_crs = raster_layer.crs()
        if raster_crs != point_crs:
            transform = QgsCoordinateTransform(point_crs, raster_crs, QgsProject.instance())
            point = transform.transform(QgsPointXY(x, y))
        else:
            point = QgsPointXY(x, y)

        # Obtém o valor do raster no ponto
        ident = raster_layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue)
        if ident.isValid():
            results = ident.results()
            if results:
                # Se houver múltiplas bandas, pegar a primeira
                z_value = list(results.values())[0]
                return z_value
        return None

    def _add_layer_to_group(self, layer, group_name):
        """Adiciona a camada ao grupo especificado no projeto."""
        root = QgsProject.instance().layerTreeRoot()
        # self._log_message(f"Adicionando camada '{layer.name()}' ao grupo '{group_name}'.", Qgis.Info)

        # Procura o grupo com o nome especificado
        group = root.findGroup(group_name)
        if not group:
            # self._log_message(f"Grupo '{group_name}' não encontrado. Criando novo grupo.", Qgis.Info)
            group = root.insertGroup(0, group_name)

        # Verifica se a camada já está no grupo para evitar duplicação
        if any(layer.name() == existing_layer.name() for existing_layer in group.findLayers()):
            # self._log_message(f"Camada '{layer.name()}' já está presente no grupo '{group_name}'.", Qgis.Warning)
            return

        # Adiciona a camada ao grupo
        QgsProject.instance().addMapLayer(layer, False)
        group.insertLayer(0, layer)

    def load_layer_attributes_grupo_z(self):
        """Carrega os atributos da camada selecionada no comboBoxGrupoZ no tableWidgetLista2."""

        start_time = time.time()  # Inicia a medição de tempo

        # Obtém o ID da camada selecionada no comboBoxGrupoZ
        selected_layer_id = self.comboBoxGrupoZ.currentData()
        selected_layer = QgsProject.instance().mapLayer(selected_layer_id)

        if not isinstance(selected_layer, QgsVectorLayer):
            # self._log_message("Nenhuma camada válida selecionada no comboBoxGrupoZ.", Qgis.Warning)
            self.tableWidgetLista2.clearContents()  # Limpa o tableWidgetLista2 se a camada for inválida
            return

        # self._log_message("Iniciando a limpeza do tableWidgetLista2...", Qgis.Info)
        # Limpa o tableWidgetLista2 antes de adicionar novos itens
        self.tableWidgetLista2.clearContents()
        self.tableWidgetLista2.setRowCount(0)
        self._log_message(f"Limpeza do tableWidgetLista2 concluída em {time.time() - start_time:.2f} segundos.", Qgis.Info)

        # Obtém os campos (atributos) da camada
        fields = selected_layer.fields()
        # self._log_message(f"Número de campos obtidos: {len(fields)}", Qgis.Info)

        # Define o número de colunas com base no número de campos
        self.tableWidgetLista2.setColumnCount(len(fields))

        # Configura o cabeçalho da tabela com os nomes dos campos
        self.tableWidgetLista2.setHorizontalHeaderLabels([field.name() for field in fields])
        # self._log_message("Cabeçalhos do tableWidgetLista2 configurados.", Qgis.Info)

        # Bloqueia sinais e atualizações para acelerar o preenchimento
        self.tableWidgetLista2.blockSignals(True)
        self.tableWidgetLista2.setSortingEnabled(False)
        self.tableWidgetLista2.setUpdatesEnabled(False)

        # Inicia a medição de tempo para a iteração das feições
        feature_start_time = time.time()

        # Obter todas as feições como lista
        features = list(selected_layer.getFeatures())

        # Define o número de linhas antecipadamente
        total_features = len(features)
        self.tableWidgetLista2.setRowCount(total_features)

        for row_idx, feature in enumerate(features):
            if row_idx % 100 == 0 and row_idx > 0:  # Log a cada 100 feições processadas
                self._log_message(f"Processando feição {row_idx}...", Qgis.Info)

            # Itera sobre cada campo da feição e adiciona o valor correspondente à célula da tabela
            for col_idx, field in enumerate(fields):
                # Obtém o valor do campo da feição
                field_value = str(feature[field.name()])
                # Cria um item na célula da tabela
                item = QTableWidgetItem(field_value)
                # Desabilita a edição do item
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                # Adiciona o item à tabela na posição correta
                self.tableWidgetLista2.setItem(row_idx, col_idx, item)

        # self._log_message(f"Todas as feições processadas em {time.time() - feature_start_time:.2f} segundos.", Qgis.Info)

        # Reabilita atualizações e sinais
        self.tableWidgetLista2.setUpdatesEnabled(True)
        self.tableWidgetLista2.setSortingEnabled(True)
        self.tableWidgetLista2.blockSignals(False)

        # Ajusta automaticamente o tamanho das colunas e das linhas
        resize_start_time = time.time()
        self.tableWidgetLista2.resizeRowsToContents()
        self.tableWidgetLista2.resizeColumnsToContents()
        # self._log_message(f"Ajuste de tamanho das colunas e linhas concluído em {time.time() - resize_start_time:.2f} segundos.", Qgis.Info)

        # Após carregar os dados, definir os spin boxes
        spinbox_start_time = time.time()
        self.set_spinboxes_from_tablewidget()
        # self._log_message(f"Configuração dos spin boxes concluída em {time.time() - spinbox_start_time:.2f} segundos.", Qgis.Info)

        total_time = time.time() - start_time

    def table_selection_changed_grupo_z(self):
        """Sincroniza a seleção do tableWidgetLista2 com a camada selecionada no comboBoxGrupoZ."""
        
        # Obtém o ID da camada selecionada no comboBoxGrupoZ
        selected_layer_id = self.comboBoxGrupoZ.currentData()
        selected_layer = QgsProject.instance().mapLayer(selected_layer_id)

        if not isinstance(selected_layer, QgsVectorLayer):
            return

        # Desconecta o sinal selectionChanged da camada para evitar loops
        try:
            selected_layer.selectionChanged.disconnect(self.table_selection_changed_grupo_z)
        except TypeError:
            pass

        # Obtém as linhas selecionadas na tabela
        selected_rows = self.tableWidgetLista2.selectionModel().selectedRows()

        # Obtém os IDs das feições correspondentes às linhas selecionadas
        selected_feature_ids = []
        for index in selected_rows:
            row = index.row()
            item = self.tableWidgetLista2.item(row, 0)
            if item:
                feature_id = item.data(Qt.UserRole)
                if feature_id is not None:
                    selected_feature_ids.append(feature_id)

        # Seleciona as feições na camada
        selected_layer.selectByIds(selected_feature_ids)

        # Reconecta o sinal selectionChanged da camada
        selected_layer.selectionChanged.connect(self.table_selection_changed_grupo_z)

    def limpar_tableWidgetLista2(self, removed_layer_ids):
        """Limpa o tableWidgetLista2 se a camada selecionada no comboBoxGrupoZ for removida."""
        
        # Obtém o ID da camada atualmente selecionada no comboBoxGrupoZ
        selected_layer_id = self.comboBoxGrupoZ.currentData()

        # Verifica se a camada removida é a mesma que está selecionada no comboBoxGrupoZ
        if selected_layer_id in removed_layer_ids:
            # Limpa o tableWidgetLista2 se a camada foi removida
            self.tableWidgetLista2.clearContents()
            self.tableWidgetLista2.setRowCount(0)
            self.tableWidgetLista2.setColumnCount(0)

            # Limpa o gráfico no scrollAreaGrafico
            self.reset_scroll_area_grafico()

    def update_combo_box_grupo_z(self):
        """Atualiza o comboBoxGrupoZ para exibir apenas as camadas do grupo 'Pontos com Z'."""
        self.comboBoxGrupoZ.blockSignals(True)  # Bloqueia sinais durante a atualização
        
        # Limpa o comboBox antes de adicionar novos itens para evitar duplicação
        self.comboBoxGrupoZ.clear()
        
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup("Pontos com Z")
        
        if group:
            layers = [layer.layer() for layer in group.children() if isinstance(layer, QgsLayerTreeLayer)]
            
            for layer in layers:
                if self.comboBoxGrupoZ.findText(layer.name()) == -1:
                    self.comboBoxGrupoZ.addItem(layer.name(), layer.id())
        
        self.comboBoxGrupoZ.blockSignals(False)  # Desbloqueia sinais após a atualização
        
        # Chamar manualmente as funções necessárias para carregar os dados
        self.handle_support_points_layer()
        self.load_layer_attributes_grupo_z()  # Carrega os atributos no tableWidgetLista2

        # Se não houver camadas no comboBoxGrupoZ, limpa o tableWidgetLista2
        if self.comboBoxGrupoZ.count() == 0:
            self.tableWidgetLista2.clearContents()
            self.tableWidgetLista2.setRowCount(0)
            self.tableWidgetLista2.setColumnCount(0)

    def _get_z_value_from_raster(self, raster_layer, x, y, point_crs):
        """Obtém o valor Z do raster no ponto (x, y)."""
        raster_crs = raster_layer.crs()
        if raster_crs != point_crs:
            transform = QgsCoordinateTransform(point_crs, raster_crs, QgsProject.instance())
            point = transform.transform(QgsPointXY(x, y))
        else:
            point = QgsPointXY(x, y)

        # Obtém o valor do raster no ponto
        ident = raster_layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue)
        if ident.isValid():
            results = ident.results()
            if results:
                z_value = list(results.values())[0]
                return z_value
        return None

    def update_combo_box_camadas(self):
        """Atualiza o comboBoxCamadas quando há alterações no projeto."""
        # Armazena a seleção atual (índice e ID da camada)
        current_index = self.comboBoxCamadas.currentIndex()
        current_layer_id = self.comboBoxCamadas.itemData(current_index)

        # Limpa o combo box de camadas
        self.comboBoxCamadas.clear()

        # Obtém todas as camadas do projeto
        layers = QgsProject.instance().mapLayers().values()

        # Obter os IDs das camadas do grupo "Pontos com Z"
        root = QgsProject.instance().layerTreeRoot()
        grupo_z = root.findGroup("Pontos com Z")
        z_layers_ids = set()
        if grupo_z:
            z_layers_ids = {layer.layerId() for layer in grupo_z.findLayers()}

        # Obter os IDs das camadas do grupo "Pontos Apoio"
        grupo_apoio = root.findGroup("Pontos Apoio")
        apoio_layers_ids = set()
        if grupo_apoio:
            apoio_layers_ids = {layer.layerId() for layer in grupo_apoio.findLayers()}

        # Verifica qual RadioButton está selecionado (Linhas ou Pontos)
        if self.radioButtonLinhas.isChecked():
            # Filtra as camadas de linhas que não estão nos grupos "Pontos com Z" e "Pontos Apoio"
            line_layers = [
                layer for layer in layers
                if isinstance(layer, QgsVectorLayer)
                and layer.geometryType() == QgsWkbTypes.LineGeometry
                and layer.id() not in z_layers_ids
                and layer.id() not in apoio_layers_ids
            ]

            # Adiciona as camadas de linha ao comboBox
            for line_layer in line_layers:
                self.comboBoxCamadas.addItem(line_layer.name(), line_layer.id())

        elif self.radioButtonPontos.isChecked():
            # Filtra as camadas de pontos que não estão nos grupos "Pontos com Z" e "Pontos Apoio"
            point_layers = [
                layer for layer in layers
                if isinstance(layer, QgsVectorLayer)
                and layer.geometryType() == QgsWkbTypes.PointGeometry
                and layer.id() not in z_layers_ids
                and layer.id() not in apoio_layers_ids
            ]

            # Adiciona as camadas de pontos ao comboBox
            for point_layer in point_layers:
                self.comboBoxCamadas.addItem(point_layer.name(), point_layer.id())

        # Tenta restaurar a seleção que estava antes
        if current_layer_id is not None:
            index = self.comboBoxCamadas.findData(current_layer_id)
            if index != -1:
                # Se achou a camada anterior, restaura
                self.comboBoxCamadas.setCurrentIndex(index)
            else:
                # Se não achou a camada anterior (ela pode ter sido removida),
                # decide se seleciona nada ou a primeira camada disponível
                if self.comboBoxCamadas.count() > 0:
                    self.comboBoxCamadas.setCurrentIndex(0)
                else:
                    # Se não há camadas, desabilita o doubleSpinBoxDistancias
                    self.doubleSpinBoxDistancias.setEnabled(False)
        else:
            # Se não havia nada selecionado antes,
            # só seleciona a primeira se quiser manter o antigo comportamento
            if self.comboBoxCamadas.count() > 0:
                self.comboBoxCamadas.setCurrentIndex(0)
            else:
                self.doubleSpinBoxDistancias.setEnabled(False)

        # Atualiza o estado do doubleSpinBoxDistancias
        self.update_doubleSpinBoxDistancias_state()

    def on_spinbox_value_changed(self):
        # Verifica se a aba tab_2 está selecionada
        if self.tabWidget.currentWidget() != self.tab_2:
            return

        # Obtém o ID da camada selecionada no comboBoxGrupoZ
        selected_layer_id = self.comboBoxGrupoZ.currentData()
        selected_layer = QgsProject.instance().mapLayer(selected_layer_id)

        if not isinstance(selected_layer, QgsVectorLayer):
            return

        # Verifica se a camada pode entrar em modo de edição
        if not selected_layer.isEditable() and not selected_layer.startEditing():
            self.mostrar_mensagem("Não foi possível iniciar o modo de edição na camada.", "Erro")
            return

        # Recalcula os campos NovoZ e Desnivel
        self.recalculate_fields(selected_layer)

        # Reinicia o timer para salvar as edições após 5 segundos de inatividade
        self.edit_timer.start(5000)

        # Atualiza o gráfico no scrollAreaGrafico
        self.setup_graph_in_scroll_area()

    def recalculate_fields(self, layer):
        h_inicial = self.doubleSpinBoxHinicial.value()
        h_final = self.doubleSpinBoxHFinal.value()

        # Obter os índices dos campos necessários
        idx_z = layer.fields().indexFromName('Z')
        idx_novoz = layer.fields().indexFromName('NovoZ')
        idx_desnivel = layer.fields().indexFromName('Desnivel')
        idx_dist_acumulada = layer.fields().indexFromName('dist_acumulada')

        if idx_z == -1 or idx_novoz == -1 or idx_desnivel == -1 or idx_dist_acumulada == -1:
            self.mostrar_mensagem("Os campos necessários não estão presentes na camada.", "Erro")
            return

        # Coletar os valores de dist_acumulada
        dist_acumuladas = [feature['dist_acumulada'] for feature in layer.getFeatures()]
        total_length = max(dist_acumuladas)

        # Calcular Z inicial e Z final
        z_initial = None
        z_final = None
        for feature in layer.getFeatures():
            if feature['dist_acumulada'] == 0.0:
                z_initial = feature['Z'] + h_inicial
            if feature['dist_acumulada'] == total_length:
                z_final = feature['Z'] + h_final

        if z_initial is None or z_final is None:
            self.mostrar_mensagem("Não foi possível determinar Z inicial ou Z final.", "Erro")
            return

        # Recalcular NovoZ e Desnivel
        # Como já estamos em modo de edição, podemos atualizar diretamente
        for feature in layer.getFeatures():
            dist_acumulada = feature['dist_acumulada']
            novo_z = z_initial + (dist_acumulada / total_length) * (z_final - z_initial)
            # desnivel = round(feature['Z'] - novo_z, 3)
            desnivel = round(novo_z - feature['Z'], 3)

            # Atualizar atributos
            feature['NovoZ'] = round(novo_z, 3)
            feature['Desnivel'] = desnivel

            # Atualiza a feição na camada
            layer.updateFeature(feature)

        # Atualizar o tableWidgetLista2
        self.update_tableWidgetLista2(layer)

    def update_tableWidgetLista2(self, layer):
        # Limpa o tableWidgetLista2 antes de adicionar novos itens
        self.tableWidgetLista2.blockSignals(True)
        self.tableWidgetLista2.clearContents()
        self.tableWidgetLista2.setRowCount(0)

        # Obtém os campos (atributos) da camada
        fields = layer.fields()

        # Define o número de colunas com base no número de campos
        self.tableWidgetLista2.setColumnCount(len(fields))

        # Configura o cabeçalho da tabela com os nomes dos campos
        self.tableWidgetLista2.setHorizontalHeaderLabels([field.name() for field in fields])

        # Itera sobre as feições da camada e adiciona os atributos à tabela
        for row_idx, feature in enumerate(layer.getFeatures()):
            # Define o número de linhas dinamicamente
            self.tableWidgetLista2.insertRow(row_idx)

            # Itera sobre cada campo da feição e adiciona o valor correspondente à célula da tabela
            for col_idx, field in enumerate(fields):
                # Obtém o valor do campo da feição
                field_value = str(feature[field.name()])
                # Cria um item na célula da tabela
                item = QTableWidgetItem(field_value)
                # Desabilita a edição do item
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                # Adiciona o item à tabela na posição correta
                self.tableWidgetLista2.setItem(row_idx, col_idx, item)

        # Ajusta automaticamente o tamanho das colunas e das linhas
        self.tableWidgetLista2.resizeRowsToContents()
        self.tableWidgetLista2.resizeColumnsToContents()

        self.tableWidgetLista2.blockSignals(False)

    def save_layer_edits(self):
        # Obtém o ID da camada selecionada no comboBoxGrupoZ
        selected_layer_id = self.comboBoxGrupoZ.currentData()
        selected_layer = QgsProject.instance().mapLayer(selected_layer_id)

        if not isinstance(selected_layer, QgsVectorLayer):
            return

        if selected_layer.isEditable():
            selected_layer.commitChanges()
            self.mostrar_mensagem(f"Edições na camada '{selected_layer.name()}' foram salvas.", "Sucesso")

    def gerar_pontos_com_z(self):
        """Gera uma nova camada de pontos com os valores Z e calcula NovoZ, dist_acumulada e Desnivel."""
        self.pushButtonGerar.blockSignals(True)
        # Verifica se o radioButtonPontos está selecionado
        if not self.radioButtonPontos.isChecked():
            self.mostrar_mensagem("Selecione 'Pontos' para gerar pontos com Z.", "Erro")
            return

        # Obtém o ID da camada de pontos selecionada no comboBoxCamadas
        selected_layer_id = self.comboBoxCamadas.currentData()
        point_layer = QgsProject.instance().mapLayer(selected_layer_id)

        if not isinstance(point_layer, QgsVectorLayer) or point_layer.geometryType() != QgsWkbTypes.PointGeometry:
            self.mostrar_mensagem("Camada de pontos inválida selecionada.", "Erro")
            return

        # Verifica se há feições selecionadas no tableWidgetLista
        selected_rows = self.tableWidgetLista.selectionModel().selectedRows()
        if not selected_rows:
            self.mostrar_mensagem("Nenhuma feição de ponto foi selecionada.", "Erro")
            return

        # Obtém o raster selecionado no comboBoxRaster
        raster_layer_id = self.comboBoxRaster.currentData()
        raster_layer = QgsProject.instance().mapLayer(raster_layer_id)

        if not isinstance(raster_layer, QgsRasterLayer):
            self.mostrar_mensagem("Camada raster inválida selecionada.", "Erro")
            return

        # Obtém os valores de Hinicial e Hfinal
        h_inicial = self.doubleSpinBoxHinicial.value()
        h_final = self.doubleSpinBoxHFinal.value()

        # Obtém os valores de Hinicial e Hfinal
        h_inicial = self.doubleSpinBoxHinicial.value()
        h_final = self.doubleSpinBoxHFinal.value()

        # Cria uma nova camada de pontos em memória
        crs = point_layer.crs()
        new_layer_name_base = f"{point_layer.name()}_Z"
        new_layer_name = self._gerar_nome_cam_pontos_unico(new_layer_name_base)
        new_layer = QgsVectorLayer(f"Point?crs={crs.authid()}", new_layer_name, "memory")
        provider = new_layer.dataProvider()

        # Adiciona campos ID, X, Y, Z, NovoZ, dist_acumulada, Desnivel
        provider.addAttributes([
            QgsField("ID", QVariant.Int),
            QgsField("X", QVariant.Double),
            QgsField("Y", QVariant.Double),
            QgsField("Z", QVariant.Double),
            QgsField("NovoZ", QVariant.Double),
            QgsField("dist_acumulada", QVariant.Double),
            QgsField("Desnivel", QVariant.Double)  # Campo adicional para desnível
        ])
        new_layer.updateFields()

        # Itera sobre as feições selecionadas e extrai o Z do raster
        features = []
        points = []
        for index in selected_rows:
            row = index.row()
            item = self.tableWidgetLista.item(row, 0)
            if item:
                feature_id = item.data(Qt.UserRole)
                feature = point_layer.getFeature(feature_id)
                geom = feature.geometry()
                point = geom.asPoint()
                x = point.x()
                y = point.y()

                # Obtém o valor Z do raster no ponto (x, y)
                z_value = self._get_z_value_from_raster(raster_layer, x, y, crs)
                if z_value is None or z_value == raster_layer.dataProvider().sourceNoDataValue(1):
                    self.mostrar_mensagem(f"Não foi possível obter Z para o ponto ID {feature_id}.", "Erro")
                    continue

                # Armazena os pontos com as coordenadas e valores Z
                points.append((feature_id, x, y, z_value))

        if not points:
            self.mostrar_mensagem("Nenhum ponto válido foi processado.", "Erro")
            return

        # Calcular total_length e distâncias entre pontos
        total_length = 0.0
        distances = []
        for i in range(1, len(points)):
            x1, y1 = points[i-1][1], points[i-1][2]
            x2, y2 = points[i][1], points[i][2]
            point1 = QgsPointXY(x1, y1)
            point2 = QgsPointXY(x2, y2)
            distance = QgsDistanceArea().measureLine(point1, point2)
            distances.append(distance)
            total_length += distance

        # Calcular Z inicial e Z final
        z_initial = points[0][3] + h_inicial
        z_final = points[-1][3] + h_final

        # Itera sobre os pontos para calcular dist_acumulada e NovoZ
        dist_acumulada = 0.0
        previous_point = None
        for i, (feature_id, x, y, z_value) in enumerate(points):
            current_point = QgsPointXY(x, y)
            if i == 0:
                dist_acumulada = 0.0  # Primeiro ponto
                novo_z = z_initial  # Primeiro ponto com Hinicial
            else:
                # Soma a distância anterior à dist_acumulada
                dist_acumulada += distances[i - 1]
                # Calcula NovoZ com base na dist_acumulada e total_length corretos
                novo_z = z_initial + (dist_acumulada / total_length) * (z_final - z_initial)

            # Para garantir que o último ponto tenha dist_acumulada igual ao total_length
            if i == len(points) - 1:
                dist_acumulada = total_length
                novo_z = z_final  # Último ponto com Hfinal

            # Calcula o desnível entre Z e NovoZ
            desnivel = round(novo_z - z_value, 3)

            # Cria uma nova feição com os campos ID, X, Y, Z, NovoZ, dist_acumulada, Desnivel
            new_feature = QgsFeature(new_layer.fields())
            new_feature.setGeometry(QgsGeometry.fromPointXY(current_point))

            # Define os atributos com 3 casas decimais para os campos numéricos
            new_feature.setAttributes([
                feature_id,
                round(x, 3),
                round(y, 3),
                round(z_value, 3),
                round(novo_z, 3),
                round(dist_acumulada, 3),
                desnivel
            ])
            provider.addFeature(new_feature)

            previous_point = current_point

        new_layer.updateExtents()

        # Aplicar os rótulos à nova camada
        self.set_label_for_layer(new_layer, "Desnivel")

        # Adiciona a nova camada ao projeto dentro do grupo "Pontos com Z"
        self._add_layer_to_group(new_layer, "Pontos com Z")

        # Atualiza o comboBoxGrupoZ para exibir as camadas no grupo "Pontos com Z"
        self.update_combo_box_grupo_z()

        # Atualize o comboBox apenas uma vez após a camada ser gerada
        # self.update_combo_box_camadas()  # Certifique-se de que não há chamadas repetidas

        self.mostrar_mensagem(f"Camada '{new_layer.name()}' adicionada ao grupo 'Pontos com Z'.", "Sucesso")

        self.pushButtonGerar.blockSignals(False)

    def on_tab_changed(self):
        # Se a aba atual não for tab_2, salvar as edições se necessário
        if self.tabWidget.currentWidget() != self.tab_2:
            self.save_layer_edits()

    def selecionar_aba_tab_widget(self):
        """Seleciona a aba no tabWidget com base no RadioButton selecionado."""
        if self.radioButtonLinhas.isChecked():
            # Seleciona a aba de linhas chamada 'tab'
            self.tabWidget.setCurrentWidget(self.tab)
        elif self.radioButtonPontos.isChecked():
            # Seleciona a aba de pontos chamada 'tab'
            self.tabWidget.setCurrentWidget(self.tab)

    def verificar_estado_pushButtonGerar(self):
        """Verifica se o botão pushButtonGerar deve ser ativado ou desativado."""
        
        # Verifica se há feições no tableWidgetLista
        if self.tableWidgetLista.rowCount() == 0:
            self.pushButtonGerar.setEnabled(False)
            return

        # Verifica se pelo menos duas linhas estão selecionadas
        selected_rows = self.tableWidgetLista.selectionModel().selectedRows()
        if len(selected_rows) < 2:
            self.pushButtonGerar.setEnabled(False)
            return
        
        # Se as condições forem atendidas, ativa o botão
        self.pushButtonGerar.setEnabled(True)

    def on_pushButtonGerar_clicked(self):
        """Função chamada ao clicar no botão pushButtonGerar"""
        # Muda para a aba tab_2
        self.tabWidget.setCurrentWidget(self.tab_2)

        # Verifica se há uma camada válida no comboBoxGrupoZ
        selected_layer_id = self.comboBoxGrupoZ.currentData()
        estacas_layer = QgsProject.instance().mapLayer(selected_layer_id)
        
        if not isinstance(estacas_layer, QgsVectorLayer):
            # self.mostrar_mensagem("Nenhuma camada válida de 'Pontos com Z' foi selecionada.", "Erro")
            return

        # Verifica se há um raster selecionado
        raster_layer_id = self.comboBoxRaster.currentData()
        raster_layer = QgsProject.instance().mapLayer(raster_layer_id)

        if not isinstance(raster_layer, QgsRasterLayer):
            self.mostrar_mensagem("Nenhuma camada raster válida foi selecionada.", "Erro")
            return

        # Verifica se há pelo menos duas feições selecionadas no tableWidgetLista2
        selected_rows = self.tableWidgetLista2.selectionModel().selectedRows()
        if len(selected_rows) < 2:
            # self.mostrar_mensagem("Selecione pelo menos duas linhas no tableWidgetLista2.", "Erro")
            return

        # Gera a camada de suporte de pontos com base nas estacas e o raster selecionado
        try:
            support_layer = self.create_support_points_layer(estacas_layer, raster_layer)
        except Exception as e:
            self.mostrar_mensagem(f"Erro ao gerar a camada de suporte: {str(e)}", "Erro")
            return

    def handle_support_points_layer(self):
        start_time = time.time()
        self.comboBoxGrupoZ.blockSignals(True)

        try:
            selected_layer_id = self.comboBoxGrupoZ.currentData()
            pontos_z_layer = QgsProject.instance().mapLayer(selected_layer_id)
            
            if pontos_z_layer is None or not isinstance(pontos_z_layer, QgsVectorLayer):
                # self._log_message("Erro: Camada de pontos Z não encontrada ou inválida.", Qgis.Warning)
                return

            support_layer_name = f"{pontos_z_layer.name()}_PontosApoio"

            # Verificar se a camada de apoio já existe
            existing_layer = QgsProject.instance().mapLayersByName(support_layer_name)
            if existing_layer:
                # A camada de apoio já existe, não é necessário recriá-la
                pass
            else:
                # Criar a camada de apoio somente se não existir
                group = QgsProject.instance().layerTreeRoot().findGroup("Pontos Apoio")
                if not group:
                    group = QgsProject.instance().layerTreeRoot().insertGroup(0, "Pontos Apoio")

                raster_layer_id = self.comboBoxRaster.currentData()
                raster_layer = QgsProject.instance().mapLayer(raster_layer_id)
                
                if raster_layer is None or not isinstance(raster_layer, QgsRasterLayer):
                    # self._log_message("Erro: Camada raster não encontrada ou inválida.", Qgis.Warning)
                    return

                # Tente criar a camada de suporte
                support_layer = self.create_support_points_layer(pontos_z_layer, raster_layer)
                if support_layer is None:
                    raise AttributeError("Camada sem conformidades de atributos.")  # Lança um erro personalizado

                support_layer.setName(support_layer_name)

                QgsProject.instance().addMapLayer(support_layer, False)
                group_layer = group.insertLayer(0, support_layer)
                group_layer.setItemVisibilityChecked(False)

                # self.update_combo_box_camadas()

            # Chamar setup_graph_in_scroll_area() para atualizar o gráfico
            self.setup_graph_in_scroll_area()

        except AttributeError as e:
            self.mostrar_mensagem("Camada sem conformidades de atributos", "Erro")
            # self._log_message(f"Erro: {str(e)}", Qgis.Critical)

        finally:
            self.comboBoxGrupoZ.blockSignals(False)

    def sample_raster_value(self, point, raster_layer):
        """Amostra o valor Z do raster baseado nas coordenadas do ponto."""
        identify_result = raster_layer.dataProvider().identify(QgsPointXY(point.x(), point.y()), QgsRaster.IdentifyFormatValue)
        
        if identify_result.isValid():
            results = identify_result.results()
            if results:
                band_key = list(results.keys())[0]
                z_value = results.get(band_key)  # Use get para evitar KeyError
                if z_value is not None:  # Verifica se o valor é válido
                    return round(float(z_value), 3)
        return None  # Retorna None se não houver valor válido

    def iniciar_progress_bar(self, total_steps):
        """
        Inicia e exibe uma barra de progresso na interface do usuário para o processo de exportação.

        Parâmetros:
        - total_steps (int): O número total de etapas a serem concluídas no processo de exportação.

        Funcionalidades:
        - Cria uma mensagem personalizada na barra de mensagens para acompanhar o progresso.
        - Configura e estiliza uma barra de progresso.
        - Adiciona a barra de progresso à barra de mensagens e a exibe na interface do usuário.
        - Define o valor máximo da barra de progresso com base no número total de etapas.
        - Retorna os widgets de barra de progresso e de mensagem para que possam ser atualizados durante a exportação.
        """
        progressMessageBar = self.iface.messageBar().createMessage("Gerando Camadas de Pontos de Apoio...")
        progressBar = QProgressBar()  # Cria uma instância da QProgressBar
        progressBar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Alinha a barra de progresso à esquerda e verticalmente ao centro
        progressBar.setFormat("%p% - %v de %m etapas concluídas")  # Define o formato da barra de progresso
        progressBar.setMinimumWidth(300)  # Define a largura mínima da barra de progresso

        # Estiliza a barra de progresso
        progressBar.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 2px;
                background-color: #cddbde;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #55aaff;
                width: 5px;
                margin: 1px;
            }
            QProgressBar {
                min-height: 5px;}""")

        # Adiciona a progressBar ao layout da progressMessageBar e exibe na interface
        progressMessageBar.layout().addWidget(progressBar)
        self.iface.messageBar().pushWidget(progressMessageBar, Qgis.Info)

        # Define o valor máximo da barra de progresso com base no número total de etapas
        progressBar.setMaximum(total_steps)

        return progressBar, progressMessageBar

    def create_support_points_layer(self, estacas_layer, raster_layer):

        start_time = time.time()
        
        # Obter a resolução do pixel da camada raster
        raster_extent = raster_layer.extent()
        raster_width = raster_layer.width()
        raster_height = raster_layer.height()
        pixel_resolution_x = raster_extent.width() / raster_width
        pixel_resolution_y = raster_extent.height() / raster_height

        # Definir o espaçamento de suporte como a resolução do pixel
        support_spacing = min(pixel_resolution_x, pixel_resolution_y)

        # Obter o CRS da camada de estacas
        crs = estacas_layer.sourceCrs().authid()
        support_layer = QgsVectorLayer(f"Point?crs={crs}", "", "memory")  # Criar a camada sem nome

        prov = support_layer.dataProvider()

        # Adiciona os campos necessários, incluindo "Acumula_dist"
        fields = [
            QgsField("ID", QVariant.Int),              # Identificador do ponto de apoio
            QgsField("Original_ID", QVariant.Int),     # ID original do ponto de origem
            QgsField("X", QVariant.Double),            # Coordenada X
            QgsField("Y", QVariant.Double),            # Coordenada Y
            QgsField("Znovo", QVariant.Double),        # Altitude do MDT (Z interpolado)
            QgsField("Acumula_dist", QVariant.Double)  # Distância acumulada ao longo da linha
        ]
        prov.addAttributes(fields)
        support_layer.updateFields()

        estacas_features = [feat for feat in estacas_layer.getFeatures()]
        estacas_points = [feat.geometry().asPoint() for feat in estacas_features]
        all_points = []
        support_point_id = 0
        last_coord = None
        acumula_dist = 0

        # Obter o índice do campo "Desnivel"
        desnivel_index = estacas_layer.fields().indexFromName('Desnivel')

        if desnivel_index == -1:
            self.mostrar_mensagem("O campo 'Desnivel' não foi encontrado na camada.", "Erro")
            return

        # Acessar o valor do campo usando o índice
        first_desnivel = estacas_features[0][desnivel_index]
        last_desnivel = estacas_features[-1][desnivel_index]

        extend_by_start = min(abs(first_desnivel) + 10, 10)  # No máximo 10 metros
        extend_by_end = min(abs(last_desnivel) + 10, 10)  # No máximo 10 metros

        # Calcular o número total de pontos para a barra de progresso
        num_points_before_first_stake = int(extend_by_start // support_spacing)
        num_points_after_last_stake = int(extend_by_end // support_spacing) + 1
        num_points_along_segments = 0

        for i, start_point in enumerate(estacas_points[:-1]):
            end_point = estacas_points[i + 1]
            segment_length = start_point.distance(end_point)
            num_intermediate_points = int(segment_length / support_spacing)
            num_points_along_segments += num_intermediate_points + 1  # +1 para incluir o ponto final

        total_points = num_points_before_first_stake + num_points_along_segments + num_points_after_last_stake
        total_steps = total_points * 2  # Multiplica por 2 para incluir as etapas de atualização de Znovo

        # Iniciar a barra de progresso
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_steps)
        current_step = 0

        # Adicionar pontos extras antes do primeiro ponto de estacas
        first_segment_dir = estacas_points[1] - estacas_points[0]
        for i in range(num_points_before_first_stake, 0, -1):
            extra_point = QgsPointXY(estacas_points[0].x() - first_segment_dir.x() * (i * support_spacing) / first_segment_dir.length(),
                                     estacas_points[0].y() - first_segment_dir.y() * (i * support_spacing) / first_segment_dir.length())
            
            z_value = self.sample_raster_value(extra_point, raster_layer)
            if z_value is None:
                # Interrompe a extensão se o valor de Z for None
                break
            
            support_point_id += 1
            all_points.append((extra_point, -i, support_point_id))
            
            # Atualizar a barra de progresso
            current_step += 1
            progressBar.setValue(current_step)
            QApplication.processEvents()

        # Gerar os pontos de apoio ao longo dos segmentos
        for i, start_point in enumerate(estacas_points[:-1]):
            end_point = estacas_points[i + 1]
            segment_length = start_point.distance(end_point)
            num_intermediate_points = int(segment_length / support_spacing)

            for j in range(num_intermediate_points + 1):
                x = start_point.x() + (end_point.x() - start_point.x()) * (j * support_spacing) / segment_length
                y = start_point.y() + (end_point.y() - start_point.y()) * (j * support_spacing) / segment_length
                inter_point = QgsPointXY(x, y)
                support_point_id += 1
                all_points.append((inter_point, estacas_features[i]['ID'], support_point_id))
                
                # Atualizar a barra de progresso
                current_step += 1
                progressBar.setValue(current_step)
                QApplication.processEvents()

        # Adicionar pontos extras após o último ponto de estacas
        last_segment_dir = estacas_points[-1] - estacas_points[-2]
        for i in range(0, num_points_after_last_stake):
            extra_point = QgsPointXY(estacas_points[-1].x() + last_segment_dir.x() * (i * support_spacing) / last_segment_dir.length(),
                                     estacas_points[-1].y() + last_segment_dir.y() * (i * support_spacing) / last_segment_dir.length())
            
            z_value = self.sample_raster_value(extra_point, raster_layer)
            if z_value is None:
                # Interrompe a extensão se o valor de Z for None
                break

            support_point_id += 1
            all_points.append((extra_point, estacas_features[-1]['ID'], support_point_id))
            
            # Atualizar a barra de progresso
            current_step += 1
            progressBar.setValue(current_step)
            QApplication.processEvents()

        # Criar os recursos e adicionar à camada com a distância acumulada
        first_positive_id_encountered = False
        for point, original_id, support_point_id in all_points:
            current_coord = (point.x(), point.y())
            if not first_positive_id_encountered:
                if original_id >= 0:
                    acumula_dist = 0
                    first_positive_id_encountered = True
                else:
                    acumula_dist = -extend_by_start + (support_point_id - 1) * support_spacing
            else:
                if last_coord:
                    segment_distance = QgsPointXY(*last_coord).distance(QgsPointXY(*current_coord))
                    acumula_dist += segment_distance
            last_coord = current_coord

            # Atributos do recurso, incluindo acumulação de distância
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(*current_coord)))
            feat.setAttributes([support_point_id, original_id, round(point.x(), 3), round(point.y(), 3), None, round(acumula_dist, 3)])
            prov.addFeature(feat)
            
            # Atualizar a barra de progresso
            current_step += 1
            progressBar.setValue(current_step)
            QApplication.processEvents()

        # Amostra os valores do MDT para os pontos de apoio e atualiza o campo "Znovo"
        support_layer.startEditing()
        z_value_previous = None

        for feature in support_layer.getFeatures():
            point = feature.geometry().asPoint()
            z_value = self.sample_raster_value(point, raster_layer)
            if z_value is None and z_value_previous is not None:
                z_value = z_value_previous
            if z_value is not None:
                z_value_previous = z_value
            feature['Znovo'] = round(z_value, 3) if z_value is not None else None
            support_layer.updateFeature(feature)
            
            # Atualizar a barra de progresso
            current_step += 1
            progressBar.setValue(current_step)
            QApplication.processEvents()

        support_layer.commitChanges()
        
        # Remover a barra de progresso
        self.iface.messageBar().clearWidgets()

        end_time = time.time()
        elapsed_time = end_time - start_time

        self.mostrar_mensagem(f"Camada de suporte criada com sucesso em {elapsed_time:.2f} segundos.", "Sucesso")

        # Retorna a camada sem adicionar ao projeto
        return support_layer

    def atualizar_listWidgetInfo_com_inclinacao_e_area(self, estacas_distances, estacas_novoz, apoio_distances, apoio_elevations):
        """
        Calcula a inclinação média das linhas 'Corte' e 'Terreno Natural' e a área das regiões hachuradas
        (azul para a área acima e vermelha para a área abaixo) e atualiza o listWidgetInfo.
        A inclinação e as áreas são exibidas no listWidgetInfo com cores e tamanho de fonte aprimorados.
        """

        # Calcular inclinação da linha "Corte"
        delta_x_corte = estacas_distances[-1] - estacas_distances[0]
        delta_y_corte = estacas_novoz[-1] - estacas_novoz[0]
        if delta_x_corte != 0:
            inclinacao_corte = (delta_y_corte / delta_x_corte) * 100  # Convertido para porcentagem
        else:
            inclinacao_corte = 0

        # Calcular inclinação da linha "Terreno Natural"
        delta_x_terreno = apoio_distances[-1] - apoio_distances[0]
        delta_y_terreno = apoio_elevations[-1] - apoio_elevations[0]
        if delta_x_terreno != 0:
            inclinacao_terreno = (delta_y_terreno / delta_x_terreno) * 100  # Convertido para porcentagem
        else:
            inclinacao_terreno = 0

        # Calcular áreas das regiões hachuradas
        x_values = sorted(set(list(estacas_distances) + list(apoio_distances)))
        y_corte = [np.interp(x, estacas_distances, estacas_novoz) for x in x_values]
        y_terreno = [np.interp(x, apoio_distances, apoio_elevations) for x in x_values]
        diff = np.array(y_corte) - np.array(y_terreno)

        # Área azul (Corte acima de Terreno Natural)
        area_azul = np.trapz(diff[diff > 0], x_values[:len(diff[diff > 0])])

        # Área vermelha (Corte abaixo de Terreno Natural)
        area_vermelha = np.trapz(-diff[diff < 0], x_values[:len(diff[diff < 0])])

        # Atualizar listWidgetInfo
        self.listWidgetInfo.clear()  # Limpa o conteúdo anterior

        # Definir fonte e estilo para o texto
        font = QFont()
        font.setPointSize(9)  # Aumenta o tamanho da fonte

        # Função auxiliar para criar itens estilizados
        def criar_item(texto, cor):
            item = QListWidgetItem(texto)
            item.setFont(font)
            item.setForeground(QColor(cor))
            return item

        # Adicionar informações de inclinação ao listWidgetInfo
        self.listWidgetInfo.addItem(criar_item(f"Incl. Corte/Aterro: {inclinacao_corte:.2f}%", "blue"))
        self.listWidgetInfo.addItem(criar_item(f"Incl. Média Terreno: {inclinacao_terreno:.2f}%", "red"))

        # Adicionar informações de área ao listWidgetInfo
        self.listWidgetInfo.addItem(criar_item(f"Área de Aterro: {area_azul:.2f} m²", "blue"))
        self.listWidgetInfo.addItem(criar_item(f"Área de Corte: {area_vermelha:.2f} m²", "red"))

    def find_layer(self, layer_name, layer_type):
        """Função auxiliar para encontrar uma camada no projeto por nome."""
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == layer_name and isinstance(layer, layer_type):
                return layer
        return None

    def setup_table_widget_signals(self):
        """Configura os sinais do tableWidgetLista2."""
        self.tableWidgetLista2.cellChanged.connect(self.update_graph_from_table_widget)

    def update_graph_from_table_widget(self, row, column):
        """Atualiza o gráfico dinamicamente quando valores no tableWidgetLista2 são alterados."""
        selected_layer_id = self.comboBoxGrupoZ.currentData()
        estacas_layer = QgsProject.instance().mapLayer(selected_layer_id)

        if not isinstance(estacas_layer, QgsVectorLayer):
            self.mostrar_mensagem("Nenhuma camada válida de 'Pontos com Z' foi selecionada.", "Erro")
            return

        if self.tableWidgetLista2.rowCount() < 2:
            # self.mostrar_mensagem("É necessário pelo menos duas linhas no tableWidgetLista2.", "Erro")
            return

        # Aplica as mudanças do tableWidgetLista2 à camada
        self.apply_table_widget_changes_to_layer(estacas_layer)

        # Atualiza o gráfico
        self.setup_graph_in_scroll_area()

    def apply_table_widget_changes_to_layer(self, layer):
        """Aplica as alterações feitas no tableWidgetLista2 à camada associada."""
        for row_idx in range(self.tableWidgetLista2.rowCount()):
            feature_id_item = self.tableWidgetLista2.item(row_idx, 0)
            
            # Verifica se o item da linha e o ID da feição são válidos
            if feature_id_item is None or feature_id_item.data(Qt.UserRole) is None:
                continue

            try:
                # Tenta converter o ID da feição para inteiro
                feature_id = int(feature_id_item.data(Qt.UserRole))
            except (TypeError, ValueError):
                # Se não for possível converter, pula essa linha
                continue
            
            # Obtém a feição correspondente pelo ID
            feature = layer.getFeature(feature_id)

            # Itera sobre as colunas para obter os valores
            for col_idx in range(self.tableWidgetLista2.columnCount()):
                field_item = self.tableWidgetLista2.item(row_idx, col_idx)

                # Verifica se o item da célula é válido
                if field_item is None:
                    continue
                
                field_value = field_item.text()
                field_name = layer.fields().at(col_idx).name()

                # Define o valor do campo na feição
                feature.setAttribute(field_name, field_value)

            # Atualiza a feição com as mudanças feitas
            layer.updateFeature(feature)

        # Atualiza os campos da camada após as alterações
        layer.updateFields()

    def set_spinboxes_from_tablewidget(self):
        """Define os valores do doubleSpinBoxHinicial e doubleSpinBoxHFinal a partir dos valores no tableWidgetLista2."""
        row_count = self.tableWidgetLista2.rowCount()
        if row_count == 0:
            # Não há dados para definir os spin boxes
            self.doubleSpinBoxHinicial.setValue(0.0)
            self.doubleSpinBoxHFinal.setValue(0.0)
            return

        # Obter o índice da coluna 'Desnivel'
        desnivel_col_index = -1
        for col_idx in range(self.tableWidgetLista2.columnCount()):
            header_item = self.tableWidgetLista2.horizontalHeaderItem(col_idx)
            if header_item and header_item.text() == 'Desnivel':
                desnivel_col_index = col_idx
                break

        if desnivel_col_index == -1:
            # Coluna 'Desnivel' não encontrada
            self.mostrar_mensagem("Coluna 'Desnivel' não encontrada no tableWidgetLista2.", "Erro")
            return

        # Obter o valor de 'Desnivel' da primeira linha
        first_desnivel_item = self.tableWidgetLista2.item(0, desnivel_col_index)
        if first_desnivel_item and first_desnivel_item.text():
            try:
                first_desnivel_value = float(first_desnivel_item.text())
                self.doubleSpinBoxHinicial.setValue(first_desnivel_value)
            except ValueError:
                self.doubleSpinBoxHinicial.setValue(0.0)
        else:
            self.doubleSpinBoxHinicial.setValue(0.0)

        # Obter o valor de 'Desnivel' da última linha
        last_desnivel_item = self.tableWidgetLista2.item(row_count - 1, desnivel_col_index)
        if last_desnivel_item and last_desnivel_item.text():
            try:
                last_desnivel_value = float(last_desnivel_item.text())
                self.doubleSpinBoxHFinal.setValue(last_desnivel_value)
            except ValueError:
                self.doubleSpinBoxHFinal.setValue(0.0)
        else:
            self.doubleSpinBoxHFinal.setValue(0.0)

    def update_graph_background_color(self):
        """Atualiza a cor de fundo do gráfico dinamicamente ao alterar o checkBoxFundo."""
        # Verificar se o widget gráfico existe e não é None
        if hasattr(self, 'graphWidget') and self.graphWidget is not None:
            if self.checkBoxFundo.isChecked():
                self.graphWidget.setBackground('w')  # Fundo branco
            else:
                self.graphWidget.setBackground('k')  # Fundo preto
            
            # Atualizar as cores dos rótulos para se ajustarem à nova cor de fundo
            label_style = {'color': '#000', 'font-size': '9pt'} if self.checkBoxFundo.isChecked() else {'color': '#fff', 'font-size': '9pt'}
            self.graphWidget.setLabel('left', 'Elevação (m)', **label_style)
            self.graphWidget.setLabel('bottom', 'Distância Acumulada (m)', **label_style)

            # Atualizar o gráfico
            self.graphWidget.repaint()
        else:
            self._log_message("graphWidget não foi inicializado.", Qgis.Warning)

    def recarregar_informacoes_do_grafico(self):
        """
        Recalcula e atualiza o listWidgetInfo com a inclinação média e área das regiões hachuradas,
        com base no gráfico atualmente exibido.
        """
        # Certifique-se de que há dados no gráfico para atualizar as informações
        if hasattr(self, 'estacas_distances') and hasattr(self, 'apoio_distances'):
            # Calcular e atualizar a inclinação e áreas no listWidgetInfo
            self.atualizar_listWidgetInfo_com_inclinacao_e_area(
                self.estacas_distances, self.estacas_novoz,
                self.apoio_distances, self.apoio_elevations
            )

    def setup_graph_in_scroll_area(self):
        # Limpa o gráfico existente
        self.reset_scroll_area_grafico()

        # Obter o ID da camada selecionada no comboBoxGrupoZ
        selected_layer_id = self.comboBoxGrupoZ.currentData()
        estacas_layer = QgsProject.instance().mapLayer(selected_layer_id)

        if not isinstance(estacas_layer, QgsVectorLayer):
            # self.mostrar_mensagem("Nenhuma camada válida selecionada no comboBoxGrupoZ.", "Erro")
            return

        # Definir o nome da camada de pontos de apoio associada
        support_layer_name = f"{estacas_layer.name()}_PontosApoio"

        # Encontrar a camada de pontos de apoio
        pontos_apoio_layer = self.find_layer(support_layer_name, QgsVectorLayer)

        if not pontos_apoio_layer:
            # self.mostrar_mensagem(f"A camada de apoio '{support_layer_name}' não foi encontrada.", "Erro")
            return

        # Coletando dados das camadas para plotagem
        estacas_data = [
            (f['dist_acumulada'], f['NovoZ'], f['Z'], f['Desnivel'], f.geometry().asPoint().x(), f.geometry().asPoint().y())
            for f in estacas_layer.getFeatures()
        ]

        pontos_apoio_data = [
            (f['Acumula_dist'], f['Znovo']) for f in pontos_apoio_layer.getFeatures()
        ]

        # Verificar se há dados nas camadas
        if not estacas_data:
            self.mostrar_mensagem("Nenhum dado encontrado na camada de estacas.", "Erro")
            return

        if not pontos_apoio_data:
            self.mostrar_mensagem("Nenhum dado encontrado na camada de pontos de apoio.", "Erro")
            return

        # Ordenando dados baseados em 'dist_acumulada' e 'Acumula_dist'
        estacas_data.sort(key=lambda x: x[0])
        pontos_apoio_data.sort(key=lambda x: x[0])

        # Desempacotando os dados
        estacas_distances, estacas_novoz, estacas_z, estacas_desnivel, estacas_x, estacas_y = zip(*estacas_data)
        apoio_distances, apoio_elevations = zip(*pontos_apoio_data)

        # Criando o widget de gráfico PyQtGraph
        self.graphWidget = pg.PlotWidget()

        # Habilitar antialiasing para suavizar as linhas
        self.graphWidget.setAntialiasing(True)

        # Armazenar os dados para uso posterior
        self.estacas_distances = estacas_distances
        self.estacas_novoz = estacas_novoz
        self.apoio_distances = apoio_distances
        self.apoio_elevations = apoio_elevations

        # Criar linhas de referência para o cursor
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('g', style=QtCore.Qt.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('g', style=QtCore.Qt.DashLine))
        self.graphWidget.addItem(self.vLine, ignoreBounds=True)
        self.graphWidget.addItem(self.hLine, ignoreBounds=True)

        # Inicialmente, as linhas são invisíveis
        self.vLine.hide()
        self.hLine.hide()

        # Criar o TextItem para exibir as coordenadas
        self.coord_text = pg.TextItem(anchor=(0,1))
        self.graphWidget.addItem(self.coord_text)
        self.coord_text.hide()

        # Conectar o evento de movimento do mouse
        self.proxy = pg.SignalProxy(self.graphWidget.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved)

        # Verificar o estado do checkBoxFundo para definir a cor de fundo
        if self.checkBoxFundo.isChecked():
            self.graphWidget.setBackground('w')  # Fundo branco
        else:
            self.graphWidget.setBackground('k')  # Fundo preto

        # Criação do layout para o gráfico dentro do scrollAreaGrafico
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.graphWidget)

        # Criando um widget container para o layout e o gráfico
        container_widget = QtWidgets.QWidget()
        container_widget.setLayout(layout)

        # Definindo as dimensões do container para caber no scrollAreaGrafico
        container_widget.setMinimumSize(623, 250)

        # Configurando o widget para o scrollAreaGrafico
        self.scrollAreaGrafico.setWidget(container_widget)

        # Aumentar a resolução do gráfico, renderizando em uma área maior
        self.graphWidget.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)

        # Renderizar o gráfico com alta qualidade
        self.graphWidget.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        # Plotar a linha "Corte" (dados de estacas)
        self.graphWidget.plot(estacas_distances, estacas_novoz, pen=pg.mkPen('b', width=2), name='Corte')

        # Plotar a linha "Terreno Natural" (dados de pontos de apoio)
        self.graphWidget.plot(apoio_distances, apoio_elevations, pen=pg.mkPen('r', width=2), name='Terreno Natural')

        # Adicionar grades ao gráfico para facilitar a visualização
        self.graphWidget.showGrid(x=True, y=True, alpha=0.3)

        # **Ajuste do zoom para incluir margens**
        x_min = min(estacas_distances) - (0.05 * (max(estacas_distances) - min(estacas_distances)))  # Margem de 5%
        x_max = max(estacas_distances) + (0.05 * (max(estacas_distances) - min(estacas_distances)))  # Margem de 5%
        y_min = min(min(estacas_novoz), min(apoio_elevations)) - 2  # Inclui uma margem extra no Y
        y_max = max(max(estacas_novoz), max(apoio_elevations)) + 2  # Inclui uma margem extra no Y

        self.graphWidget.setXRange(x_min, x_max)
        self.graphWidget.setYRange(y_min, y_max)

        # Adicionar rótulos e melhorar o tamanho das fontes
        label_style = {'color': '#000', 'font-size': '8pt'} if self.checkBoxFundo.isChecked() else {'color': '#fff', 'font-size': '8pt'}

        self.graphWidget.setLabel('left', 'Elevação (m)', **label_style)
        self.graphWidget.setLabel('bottom', 'Distância Acumulada (m)', **label_style)

        # Adicionar legenda
        self.graphWidget.addLegend()

        # Exibir a inclinação no gráfico
        self.exibir_inclinacao_no_grafico(estacas_distances, estacas_novoz)

        # **Chama a função para adicionar as linhas inclinadas**
        self.adicionar_linhas_inclinadas(estacas_distances, estacas_novoz, apoio_distances, apoio_elevations)

        # Adicionar as linhas inclinadas e obter os pontos finais
        x_end0, y_end0, x_end1, y_end1 = self.adicionar_linhas_inclinadas(estacas_distances, estacas_novoz, apoio_distances, apoio_elevations)

        # Adicionar a hachura entre as linhas
        self.adicionar_hachura(estacas_distances, estacas_novoz, apoio_distances, apoio_elevations, x_end0, y_end0, x_end1, y_end1)

        # Após configurar o gráfico, recarregar o raster para garantir que ele seja exibido novamente
        self.display_raster()

        # Exibir a inclinação no gráfico
        self.exibir_inclinacao_no_grafico(estacas_distances, estacas_novoz)

        # Atualizar o listWidgetInfo com inclinação e áreas
        self.atualizar_listWidgetInfo_com_inclinacao_e_area(estacas_distances, estacas_novoz, apoio_distances, apoio_elevations)

        # Após configurar o gráfico com sucesso, habilita o pushButtonExportarDXF
        self.pushButtonExportarDXF.setEnabled(True)

    def delete_selected_layer(self):
        """
        Deleta a camada selecionada no comboBoxGrupoZ e sua respectiva camada de pontos de apoio.
        Limpa o tableWidgetLista2, listWidgetInfo e scrollAreaGrafico.
        Se os grupos ficarem vazios após a remoção, deleta os grupos também.
        """
        # Obter o ID da camada selecionada no comboBoxGrupoZ
        selected_layer_id = self.comboBoxGrupoZ.currentData()
        if not selected_layer_id:
            self.mostrar_mensagem("Nenhuma camada selecionada.", "Erro")
            return

        # Obter a camada a partir do ID
        layer = QgsProject.instance().mapLayer(selected_layer_id)
        if not layer:
            self.mostrar_mensagem("A camada selecionada não foi encontrada.", "Erro")
            return

        # Nome da camada de pontos de apoio associada
        support_layer_name = f"{layer.name()}_PontosApoio"

        # Encontrar a camada de pontos de apoio
        support_layer = self.find_layer(support_layer_name, QgsVectorLayer)

        # Remover a camada principal do projeto
        QgsProject.instance().removeMapLayer(layer.id())

        # Remover a camada de pontos de apoio, se existir
        if support_layer:
            QgsProject.instance().removeMapLayer(support_layer.id())

        # Remover a camada do comboBoxGrupoZ
        index = self.comboBoxGrupoZ.findData(selected_layer_id)
        if index >= 0:
            self.comboBoxGrupoZ.removeItem(index)

        # Verificar se o grupo "Pontos com Z" está vazio e remover se necessário
        root = QgsProject.instance().layerTreeRoot()
        group_z = root.findGroup("Pontos com Z")
        if group_z and not group_z.children():
            root.removeChildNode(group_z)
            self.mostrar_mensagem("Grupo 'Pontos com Z' removido por estar vazio.", "Sucesso")

        # Verificar se o grupo "Pontos Apoio" está vazio e remover se necessário
        group_apoio = root.findGroup("Pontos Apoio")
        if group_apoio and not group_apoio.children():
            root.removeChildNode(group_apoio)
            self.mostrar_mensagem("Grupo 'Pontos Apoio' removido por estar vazio.", "Sucesso")

        # Se houver outras camadas no comboBoxGrupoZ, selecionar a próxima camada disponível
        if self.comboBoxGrupoZ.count() > 0:
            # Selecionar a primeira camada disponível
            self.comboBoxGrupoZ.setCurrentIndex(0)

            # Carregar os dados da nova camada selecionada
            self.load_layer_attributes_grupo_z()
            self.setup_graph_in_scroll_area()  # Atualiza o gráfico com os dados da nova camada
        else:
            # Se não houver mais camadas, limpar o tableWidgetLista2, listWidgetInfo e o gráfico
            self.tableWidgetLista2.clearContents()
            self.tableWidgetLista2.setRowCount(0)
            self.listWidgetInfo.clear()
            self.reset_scroll_area_grafico()

        # Exibir uma mensagem de sucesso
        self.mostrar_mensagem("Camada e pontos de apoio excluídos com sucesso.", "Sucesso")

    def mouse_moved(self, evt):
        """
        Evento chamado quando o mouse é movido sobre o gráfico.
        Atualiza as linhas de referência (crosshairs) se o mouse estiver sobre as linhas "Corte" ou "Terreno Natural".
        O cursor "gruda" na linha mais próxima (Corte ou Terreno Natural) quando estiver dentro da tolerância.
        """
        pos = evt[0]  # Obter a posição do mouse do evento
        if self.graphWidget.plotItem.sceneBoundingRect().contains(pos):
            mousePoint = self.graphWidget.plotItem.vb.mapSceneToView(pos)
            x = mousePoint.x()
            y = mousePoint.y()

            # Verificar se o mouse está dentro do intervalo de distâncias
            if self.estacas_distances[0] <= x <= self.estacas_distances[-1]:
                # Interpolar para encontrar os valores de y nas linhas Corte e Terreno Natural
                y_corte = np.interp(x, self.estacas_distances, self.estacas_novoz)
                y_terreno = np.interp(x, self.apoio_distances, self.apoio_elevations)

                tolerance = (max(self.estacas_novoz) - min(self.estacas_novoz)) * 0.055  # Tolerância de 5%

                # Verificar se o mouse está próximo de uma das linhas
                if abs(y - y_corte) <= tolerance or abs(y - y_terreno) <= tolerance:
                    # "Grudar" na linha mais próxima
                    if abs(y - y_corte) < abs(y - y_terreno):
                        y = y_corte  # Grudar na linha "Corte"
                    else:
                        y = y_terreno  # Grudar na linha "Terreno Natural"

                    # Atualizar as linhas de referência
                    self.vLine.setPos(x)
                    self.hLine.setPos(y)
                    self.vLine.show()
                    self.hLine.show()

                    # Atualizar o texto das coordenadas
                    self.coord_text.setText(f"Elevação: {y:.2f} m\nDistância: {x:.2f} m")
                    self.coord_text.setFont(QtGui.QFont('Arial', 8, QtGui.QFont.Bold))
                    self.coord_text.setColor('green')
                    self.coord_text.setPos(x, y)
                    self.coord_text.show()
                else:
                    # Mouse não está próximo das linhas
                    self.vLine.hide()
                    self.hLine.hide()
                    self.coord_text.hide()
            else:
                # Fora do intervalo de x
                self.vLine.hide()
                self.hLine.hide()
                self.coord_text.hide()
        else:
            # Fora do gráfico
            self.vLine.hide()
            self.hLine.hide()
            self.coord_text.hide()

    def exibir_inclinacao_no_grafico(self, estacas_distances, estacas_novoz):
        """Exibe a inclinação entre o primeiro e o último ponto da linha 'Corte' no gráfico, centralizado e alinhado à linha."""

        # Calculando a diferença em distâncias e elevações
        delta_x = estacas_distances[-1] - estacas_distances[0]
        delta_y = estacas_novoz[-1] - estacas_novoz[0]

        # Calculando a inclinação em porcentagem
        if delta_x != 0:
            inclinacao = delta_y / delta_x
            inclinacao_percent = inclinacao * 100  # Convertendo para porcentagem
        else:
            inclinacao_percent = 0

        # Calculando a posição média
        distancia_media = (estacas_distances[-1] + estacas_distances[0]) / 2
        z_medio = (estacas_novoz[-1] + estacas_novoz[0]) / 2

        # Adicionar um deslocamento para colocar o texto acima da linha
        offset = (max(estacas_novoz) - min(estacas_novoz)) * 0.05  # 5% do intervalo de elevação
        z_medio_acima = z_medio + offset  # Eleva o texto acima da linha

        # Calculando o ângulo em graus
        angle = math.degrees(math.atan2(delta_y, delta_x))

        # Ajustar o ângulo para manter o texto legível e alinhado corretamente
        if angle < -90 or angle > 90:
            angle = angle + 180 if angle < 0 else angle - 180
        else:
            angle = -angle  # Inverte o ângulo para alinhar corretamente com a linha

        # Criando o TextItem
        color = 'k' if self.checkBoxFundo.isChecked() else 'w'
        self.inclinacao_text_item = pg.TextItem(f"{inclinacao_percent:.2f}%", 
                                                anchor=(0.5, 0.5),  # Centralizando o texto
                                                color='b', 
                                                border=None, 
                                                fill=None)
        self.inclinacao_text_item.setFont(QtGui.QFont('Arial', 12))  # Definindo o tamanho da fonte como 8pt
        self.inclinacao_text_item.setPos(distancia_media, z_medio_acima)  # Posiciona o texto acima da linha

        # Rotacionando o texto para alinhar com a linha "Corte"
        self.inclinacao_text_item.setRotation(angle)

        # Adicionando o TextItem ao gráfico
        self.graphWidget.addItem(self.inclinacao_text_item)

    def reset_scroll_area_grafico(self):
        """Limpa o conteúdo da scrollAreaGrafico ao iniciar o diálogo."""
        
        # Verifica se o widget gráfico existe e se ele não foi deletado
        if hasattr(self, 'graphWidget') and self.graphWidget is not None:
            try:
                # Verifica se o gráfico ainda está válido antes de tentar limpá-lo
                self.graphWidget.clear()
            except RuntimeError:
                self._log_message("O gráfico foi removido ou já está deletado.", Qgis.Warning)
            except Exception as e:
                self._log_message(f"Erro ao limpar o gráfico: {str(e)}", Qgis.Warning)

            # Remove o widget gráfico do scrollAreaGrafico
            if self.scrollAreaGrafico.widget():
                self.scrollAreaGrafico.takeWidget()

            # Remove a referência do graphWidget para garantir que ele seja recriado corretamente
            self.graphWidget = None

            # Desabilita o pushButtonExportarDXF já que não há gráfico
            self.pushButtonExportarDXF.setEnabled(False)

            # Limpa o listWidgetInfo, já que o gráfico foi removido
            self.listWidgetInfo.clear()

    def adicionar_hachura(self, estacas_distances, estacas_novoz, apoio_distances, apoio_elevations, x_end0, y_end0, x_end1, y_end1):
        """
        Adiciona hachuras limitadas pelas linhas inclinadas, a linha 'Terreno Natural' e a linha 'Corte'.
        A hachura fica vermelha se a linha 'Corte' estiver abaixo da linha 'Terreno Natural',
        e azul se a linha 'Corte' estiver acima da linha 'Terreno Natural'.
        """

        # Combinar os dados em uma lista de pontos x únicos e ordenados
        x_values = sorted(set(list(estacas_distances) + list(apoio_distances) + [x_end0, x_end1]))
        x_values = [x for x in x_values if estacas_distances[0] <= x <= estacas_distances[-1]]

        # Interpolar os valores de y para cada x
        y_corte = [np.interp(x, estacas_distances, estacas_novoz) for x in x_values]
        y_terreno = [np.interp(x, apoio_distances, apoio_elevations) for x in x_values]

        # Adicionar os pontos finais das linhas inclinadas (Taludes)
        x_values = [x_end0] + x_values + [x_end1]
        y_corte = [y_end0] + y_corte + [y_end1]
        y_terreno = [np.interp(x_end0, apoio_distances, apoio_elevations)] + y_terreno + [np.interp(x_end1, apoio_distances, apoio_elevations)]

        # Encontrar os pontos de interseção
        intersecoes = []
        for i in range(len(x_values) - 1):
            x1, x2 = x_values[i], x_values[i+1]
            y1_corte, y2_corte = y_corte[i], y_corte[i+1]
            y1_terreno, y2_terreno = y_terreno[i], y_terreno[i+1]

            # Verificar se há cruzamento entre os segmentos
            s1 = y1_corte - y1_terreno
            s2 = y2_corte - y2_terreno
            if s1 * s2 < 0:
                # Há interseção
                p_intersec = self.calcular_intersecao(
                    (x1, y1_corte), (x2, y2_corte),
                    (x1, y1_terreno), (x2, y2_terreno)
                )
                if p_intersec:
                    intersecoes.append((i, p_intersec))

        # Inserir os pontos de interseção nas listas
        for idx, (i, (x_int, y_int)) in enumerate(intersecoes):
            insert_pos = i + 1 + idx
            x_values.insert(insert_pos, x_int)
            y_corte.insert(insert_pos, y_int)
            y_terreno.insert(insert_pos, y_int)  # Ambos têm o mesmo y no ponto de interseção

        # Dividir os segmentos com base nos pontos de interseção
        segmentos = []
        start_idx = 0
        for idx in range(1, len(x_values)):
            x_seg = x_values[start_idx:idx+1]
            y_corte_seg = y_corte[start_idx:idx+1]
            y_terreno_seg = y_terreno[start_idx:idx+1]

            # Determinar se 'Corte' está acima ou abaixo neste segmento
            diff = np.array(y_corte_seg) - np.array(y_terreno_seg)
            media_diff = np.mean(diff)
            if media_diff >= 0:
                cor_hachura = (0, 0, 255, 100)  # Azul
            else:
                cor_hachura = (255, 0, 0, 100)  # Vermelho

            segmentos.append((x_seg, y_corte_seg, y_terreno_seg, cor_hachura))
            start_idx = idx

        # Desenhar hachuras para cada segmento
        for x_seg, y_corte_seg, y_terreno_seg, cor_hachura in segmentos:
            path = QPainterPath()
            # Começar no primeiro ponto do segmento na linha 'Corte'
            path.moveTo(x_seg[0], y_corte_seg[0])

            # Adicionar pontos da linha 'Corte'
            for x, y in zip(x_seg, y_corte_seg):
                path.lineTo(x, y)

            # Adicionar pontos da linha 'Terreno Natural' em ordem reversa
            for x, y in zip(reversed(x_seg), reversed(y_terreno_seg)):
                path.lineTo(x, y)

            # Fechar o caminho
            path.closeSubpath()

            # Criar o item gráfico para o preenchimento
            hachura_brush = pg.mkBrush(color=cor_hachura)
            hachura_item = QGraphicsPathItem(path)
            hachura_item.setBrush(hachura_brush)
            hachura_item.setPen(pg.mkPen(None))  # Sem bordas

            # Adicionar o item ao gráfico
            self.graphWidget.addItem(hachura_item)

    def adicionar_linhas_inclinadas(self, estacas_distances, estacas_novoz, apoio_distances, apoio_elevations):
        """
        Adiciona linhas inclinadas no início e no fim da linha 'Corte',
        que terminam exatamente ao tocar a linha 'Terreno Natural'.
        """
        # **Linha inicial**
        x0 = estacas_distances[0]
        y0 = estacas_novoz[0]

        # Determinar o ângulo da linha inclinada
        if y0 >= np.interp(x0, apoio_distances, apoio_elevations):
            angle = math.radians(45)
        else:
            angle = math.radians(135)

        m_talude = math.tan(angle)

        # Encontrar o ponto de interseção no início
        x_end0, y_end0 = self.encontrar_intersecao(x0, y0, m_talude, apoio_distances, apoio_elevations, lado='esquerda')

        # Plotar a linha inclinada no início
        self.graphWidget.plot([x0, x_end0], [y0, y_end0], pen=pg.mkPen('b', width=1.5, style=QtCore.Qt.DashLine))

        # **Linha final**
        x1 = estacas_distances[-1]
        y1 = estacas_novoz[-1]

        if y1 >= np.interp(x1, apoio_distances, apoio_elevations):
            angle = math.radians(135)
        else:
            angle = math.radians(45)

        m_talude = math.tan(angle)

        # Encontrar o ponto de interseção no final
        x_end1, y_end1 = self.encontrar_intersecao(x1, y1, m_talude, apoio_distances, apoio_elevations, lado='direita')

        # Plotar a linha inclinada no final
        self.graphWidget.plot([x1, x_end1], [y1, y_end1], pen=pg.mkPen('b', width=1.5, style=QtCore.Qt.DashLine))

        # Retorna os pontos finais das linhas inclinadas
        return x_end0, y_end0, x_end1, y_end1

    def encontrar_intersecao(self, x0, y0, m_talude, apoio_distances, apoio_elevations, lado):
        """
        Encontra o ponto de interseção entre a linha inclinada (talude) e a linha do Terreno Natural.
        """
        # Criar a equação da linha inclinada: y = m_talude * (x - x0) + y0

        # Dependendo do lado, percorremos os segmentos do Terreno Natural em ordem adequada
        if lado == 'esquerda':
            indices = range(len(apoio_distances) - 1)
        else:
            indices = range(len(apoio_distances) - 1, 0, -1)

        for i in indices:
            if lado == 'esquerda':
                x_tn1, y_tn1 = apoio_distances[i], apoio_elevations[i]
                x_tn2, y_tn2 = apoio_distances[i + 1], apoio_elevations[i + 1]
            else:
                x_tn1, y_tn1 = apoio_distances[i], apoio_elevations[i]
                x_tn2, y_tn2 = apoio_distances[i - 1], apoio_elevations[i - 1]

            # Calcular o coeficiente angular da linha do Terreno Natural
            if x_tn2 - x_tn1 != 0:
                m_tn = (y_tn2 - y_tn1) / (x_tn2 - x_tn1)
            else:
                m_tn = float('inf')  # Linha vertical

            # Se as linhas não forem paralelas, calcular o ponto de interseção
            if m_tn != m_talude:
                if m_tn != float('inf'):
                    x_intersect = ( (m_tn * x_tn1 - y_tn1) - (m_talude * x0 - y0) ) / (m_tn - m_talude)
                    y_intersect = m_talude * (x_intersect - x0) + y0
                else:
                    x_intersect = x_tn1
                    y_intersect = m_talude * (x_intersect - x0) + y0

                # Verificar se o ponto de interseção está dentro do segmento do Terreno Natural
                if (min(x_tn1, x_tn2) <= x_intersect <= max(x_tn1, x_tn2)) and (min(y_tn1, y_tn2) <= y_intersect <= max(y_tn1, y_tn2)):
                    # Encontramos o ponto de interseção
                    return x_intersect, y_intersect

        # Se não encontrar interseção, retornar o ponto final da linha do Terreno Natural
        if lado == 'esquerda':
            return apoio_distances[0], apoio_elevations[0]
        else:
            return apoio_distances[-1], apoio_elevations[-1]

    def escolher_local_para_salvar(self, nome_padrao, tipo_arquivo):
        # Acessa as configurações do QGIS para recuperar o último diretório utilizado
        settings = QSettings()
        lastDir = settings.value("lastDir", "")  # Usa uma string vazia como padrão se não houver último diretório

        # Configura as opções da caixa de diálogo para salvar arquivos
        options = QFileDialog.Options()
        
        # Gera o nome e a extensão do arquivo
        base_nome_padrao, extensao = os.path.splitext(nome_padrao)
        if not extensao:  # Caso o nome não inclua uma extensão, extrair do tipo_arquivo
            extensao = tipo_arquivo.split("*.")[-1].replace(")", "")
        numero = 1
        nome_proposto = base_nome_padrao

        # Incrementa o número no nome até encontrar um nome que não exista
        while os.path.exists(os.path.join(lastDir, nome_proposto + "." + extensao)):
            nome_proposto = f"{base_nome_padrao}_{numero}"
            numero += 1

        # Propõe o nome completo no último diretório utilizado
        nome_completo_proposto = os.path.join(lastDir, nome_proposto + "." + extensao)

        # Exibe a caixa de diálogo para salvar arquivos com o nome proposto
        fileName, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Camada",
            nome_completo_proposto,
            tipo_arquivo,
            options=options
        )

        # Verifica se um nome de arquivo foi escolhido
        if fileName:
            # Atualiza o último diretório usado nas configurações do QGIS
            settings.setValue("lastDir", os.path.dirname(fileName))

            # Assegura que o arquivo tenha a extensão correta
            if not fileName.endswith(f".{extensao}"):
                fileName += f".{extensao}"

        return fileName  # Retorna o caminho completo do arquivo escolhido ou None se cancelado

    def obter_dados_para_exportacao(self):
        # Obter o ID da camada selecionada no comboBoxGrupoZ
        selected_layer_id = self.comboBoxGrupoZ.currentData()
        estacas_layer = QgsProject.instance().mapLayer(selected_layer_id)

        if not isinstance(estacas_layer, QgsVectorLayer):
            self.mostrar_mensagem("Nenhuma camada válida de 'Pontos com Z' foi selecionada.", "Erro")
            return None, None

        # Definir o nome da camada de pontos de apoio associada
        support_layer_name = f"{estacas_layer.name()}_PontosApoio"

        # Encontrar a camada de pontos de apoio
        pontos_apoio_layer = self.find_layer(support_layer_name, QgsVectorLayer)

        if not pontos_apoio_layer:
            self.mostrar_mensagem(f"A camada de apoio '{support_layer_name}' não foi encontrada.", "Erro")
            return None, None

        # Coletando dados das camadas para exportação
        estacas_data = [
            (f.id(), f['dist_acumulada'], f['NovoZ'], f['Z'], f['Desnivel'], f.geometry().asPoint().x(), f.geometry().asPoint().y())
            for f in estacas_layer.getFeatures()
        ]

        pontos_apoio_data = [
            (f['Acumula_dist'], f['Znovo']) for f in pontos_apoio_layer.getFeatures()
        ]

        # Verificar se há dados nas camadas
        if not estacas_data:
            self.mostrar_mensagem("Nenhum dado encontrado na camada de estacas.", "Erro")
            return None, None

        if not pontos_apoio_data:
            self.mostrar_mensagem("Nenhum dado encontrado na camada de pontos de apoio.", "Erro")
            return None, None

        # Ordenando dados baseados em 'dist_acumulada' e 'Acumula_dist'
        estacas_data.sort(key=lambda x: x[1])
        pontos_apoio_data.sort(key=lambda x: x[0])

        return estacas_data, pontos_apoio_data

    def exportar_linhas_talude(self, msp, estacas_data, pontos_apoio_data):
        # Desempacotando os dados
        estacas_ids, estacas_distances, estacas_novoz, _, _, _, _ = zip(*estacas_data)
        apoio_distances, apoio_elevations = zip(*pontos_apoio_data)

        # **Linha de talude inicial**
        x0 = estacas_distances[0]
        y0 = estacas_novoz[0]

        if y0 >= np.interp(x0, apoio_distances, apoio_elevations):
            angle = math.radians(45)
        else:
            angle = math.radians(135)

        m_talude = math.tan(angle)

        # Encontrar o ponto de interseção no início
        x_end0, y_end0 = self.encontrar_intersecao_dxf(x0, y0, m_talude, apoio_distances, apoio_elevations, lado='esquerda')

        # Adicionar a linha de talude inicial ao DXF
        msp.add_lwpolyline([(x0, y0), (x_end0, y_end0)], dxfattribs={'layer': 'Talude'})

        # **Linha de talude final**
        x1 = estacas_distances[-1]
        y1 = estacas_novoz[-1]

        if y1 >= np.interp(x1, apoio_distances, apoio_elevations):
            angle = math.radians(135)
        else:
            angle = math.radians(45)

        m_talude = math.tan(angle)

        # Encontrar o ponto de interseção no final
        x_end1, y_end1 = self.encontrar_intersecao_dxf(x1, y1, m_talude, apoio_distances, apoio_elevations, lado='direita')

        # Adicionar a linha de talude final ao DXF
        msp.add_lwpolyline([(x1, y1), (x_end1, y_end1)], dxfattribs={'layer': 'Talude'})

    def encontrar_intersecao_dxf(self, x0, y0, m_talude, apoio_distances, apoio_elevations, lado):
        """
        Encontra o ponto de interseção entre a linha inclinada (talude) e a linha do Terreno Natural para o DXF.
        """
        # Mesma lógica da função anterior, adaptada se necessário para o contexto do DXF

        # Dependendo do lado, percorremos os segmentos do Terreno Natural em ordem adequada
        if lado == 'esquerda':
            indices = range(len(apoio_distances) - 1)
        else:
            indices = range(len(apoio_distances) - 1, 0, -1)

        for i in indices:
            if lado == 'esquerda':
                x_tn1, y_tn1 = apoio_distances[i], apoio_elevations[i]
                x_tn2, y_tn2 = apoio_distances[i + 1], apoio_elevations[i + 1]
            else:
                x_tn1, y_tn1 = apoio_distances[i], apoio_elevations[i]
                x_tn2, y_tn2 = apoio_distances[i - 1], apoio_elevations[i - 1]

            # Calcular o coeficiente angular da linha do Terreno Natural
            if x_tn2 - x_tn1 != 0:
                m_tn = (y_tn2 - y_tn1) / (x_tn2 - x_tn1)
            else:
                m_tn = float('inf')  # Linha vertical

            # Se as linhas não forem paralelas, calcular o ponto de interseção
            if m_tn != m_talude:
                if m_tn != float('inf'):
                    x_intersect = ( (m_tn * x_tn1 - y_tn1) - (m_talude * x0 - y0) ) / (m_tn - m_talude)
                    y_intersect = m_talude * (x_intersect - x0) + y0
                else:
                    x_intersect = x_tn1
                    y_intersect = m_talude * (x_intersect - x0) + y0

                # Verificar se o ponto de interseção está dentro do segmento do Terreno Natural
                if (min(x_tn1, x_tn2) <= x_intersect <= max(x_tn1, x_tn2)) and (min(y_tn1, y_tn2) <= y_intersect <= max(y_tn1, y_tn2)):
                    # Encontramos o ponto de interseção
                    return x_intersect, y_intersect

        # Se não encontrar interseção, retornar o ponto final da linha do Terreno Natural
        if lado == 'esquerda':
            return apoio_distances[0], apoio_elevations[0]
        else:
            return apoio_distances[-1], apoio_elevations[-1]

    def exportar_linhas_principais(self, msp, estacas_data, pontos_apoio_data):
        # Desempacotando os dados
        estacas_ids, estacas_distances, estacas_novoz, estacas_z, estacas_desnivel, estacas_x, estacas_y = zip(*estacas_data)
        apoio_distances, apoio_elevations = zip(*pontos_apoio_data)

        # Adicionar a linha 'Corte' como uma polilinha no DXF
        corte_points = list(zip(estacas_distances, estacas_novoz))
        msp.add_lwpolyline(corte_points, dxfattribs={'layer': 'Corte'})

        # Adicionar a linha 'Terreno Natural' como uma polilinha no DXF
        terreno_points = list(zip(apoio_distances, apoio_elevations))
        msp.add_lwpolyline(terreno_points, dxfattribs={'layer': 'Terreno_Natural'})

    def adicionar_informacoes_adicionais(self, msp, ponto_superior_esquerdo, x_margin, y_margin, estacas_data, pontos_apoio_data):
        """
        Adiciona informações de inclinação da linha de Corte, inclinação média do Terreno Natural,
        e áreas das hachuras (corte e aterro) no canto superior esquerdo do retângulo principal, organizadas em linha e coloridas.
        """
        # Cálculo das inclinações e áreas
        estacas_distances, estacas_novoz = zip(*[(e[1], e[2]) for e in estacas_data])
        apoio_distances, apoio_elevations = zip(*pontos_apoio_data)

        # Inclinação da linha de Corte
        inclinacao_corte = ((estacas_novoz[-1] - estacas_novoz[0]) / 
                            (estacas_distances[-1] - estacas_distances[0])) * 100

        # Inclinação média do Terreno Natural
        inclinacao_terreno = ((apoio_elevations[-1] - apoio_elevations[0]) / 
                              (apoio_distances[-1] - apoio_distances[0])) * 100

        # Cálculo das áreas (hachuras) - área de corte e área de aterro
        x_combined = sorted(set(estacas_distances + apoio_distances))
        y_corte_interpolated = np.interp(x_combined, estacas_distances, estacas_novoz)
        y_terreno_interpolated = np.interp(x_combined, apoio_distances, apoio_elevations)

        area_aterro = np.trapz(y_corte_interpolated[y_corte_interpolated > y_terreno_interpolated] - 
                               y_terreno_interpolated[y_corte_interpolated > y_terreno_interpolated], 
                               x=np.array(x_combined)[y_corte_interpolated > y_terreno_interpolated])
        area_corte = np.trapz(y_terreno_interpolated[y_terreno_interpolated > y_corte_interpolated] - 
                              y_corte_interpolated[y_terreno_interpolated > y_corte_interpolated], 
                              x=np.array(x_combined)[y_terreno_interpolated > y_corte_interpolated])

        # Posição inicial para o texto no canto superior esquerdo, dentro do retângulo
        pos_x = ponto_superior_esquerdo[0] + x_margin * 0.5 # Um pouco afastado da borda esquerda
        pos_y = ponto_superior_esquerdo[1] - y_margin * 1.2  # Um pouco afastado da borda superior

        # Espaçamento horizontal entre as informações em linha
        spacing = 15

        # Adicionar as informações em linha
        msp.add_text(f"Inclinação Corte: {inclinacao_corte:.2f}%", dxfattribs={
            'height': 0.5,
            'layer': 'Moldura',
            'color': 5,  # Azul
            'insert': (pos_x, pos_y)
        })
        pos_x += spacing

        msp.add_text(f"Inclinação Média Terreno: {inclinacao_terreno:.2f}%", dxfattribs={
            'height': 0.5,
            'layer': 'Moldura',
            'color': 6,  # Magenta
            'insert': (pos_x, pos_y)
        })
        pos_x += spacing

        msp.add_text(f"Área Aterro: {abs(area_aterro):.2f} m2", dxfattribs={
            'height': 0.5,
            'layer': 'Moldura',
            'color': 5,  # Azul
            'insert': (pos_x, pos_y)
        })
        pos_x += spacing

        msp.add_text(f"Área Corte: {abs(area_corte):.2f} m2", dxfattribs={
            'height': 0.5,
            'layer': 'Moldura',
            'color': 1,  # Vermelho
            'insert': (pos_x, pos_y)
        })

    def adicionar_retangulo_ao_redor(self, msp, estacas_data, pontos_apoio_data):
        # Desempacotando os dados
        estacas_ids, estacas_distances, estacas_novoz, _, _, _, _ = zip(*estacas_data)
        apoio_distances, apoio_elevations = zip(*pontos_apoio_data)

        # Definir os limites dos eixos usando os valores de apoio
        x_min = min(apoio_distances)
        x_max = max(apoio_distances)
        y_min = min(min(estacas_novoz), min(apoio_elevations))
        y_max = max(max(estacas_novoz), max(apoio_elevations))

        # Definir um intervalo mínimo para o eixo Y
        intervalo_minimo_y = 10  # Valor mínimo para o intervalo vertical
        intervalo_y = y_max - y_min

        if intervalo_y < intervalo_minimo_y:
            centro_y = (y_max + y_min) / 2
            y_min = centro_y - intervalo_minimo_y / 2
            y_max = centro_y + intervalo_minimo_y / 2

        # Adicionar margens
        x_margin = (x_max - x_min) * 0.05  # 5% de margem
        y_margin = (y_max - y_min) * 0.05  # 5% de margem

        # Definir uma margem mínima para garantir que o retângulo cubra adequadamente os eixos
        margem_minima = 0.75  # Ajuste este valor conforme necessário
        x_margin = max(x_margin, margem_minima)
        y_margin = max(y_margin, margem_minima)

        # Ajustar y_min e y_max com as margens
        x_min -= x_margin
        x_max += x_margin
        y_min -= y_margin
        y_max += y_margin

        # Adicionar margem extra ao retângulo para garantir espaço para os labels
        extra_margin = y_margin * 5  # Ajuste conforme necessário

        # Definir os quatro cantos do retângulo (com a margem extra)
        ponto_inferior_esquerdo = (x_min - extra_margin, y_min - extra_margin)
        ponto_inferior_direito = (x_max + extra_margin, y_min - extra_margin)
        ponto_superior_direito = (x_max + extra_margin, y_max + extra_margin)
        ponto_superior_esquerdo = (x_min - extra_margin, y_max + extra_margin)

        # Desenhar o retângulo como uma linha única (polilinha)
        msp.add_lwpolyline([
            ponto_inferior_esquerdo,
            ponto_inferior_direito,
            ponto_superior_direito,
            ponto_superior_esquerdo,
            ponto_inferior_esquerdo  # Fechar o loop para garantir que o retângulo se feche
        ], dxfattribs={'layer': 'Moldura'}, close=True)

        # Adicionar o texto no canto superior esquerdo do retângulo
        texto = "Perfil de Corte/Aterro sobre o Terreno Natural"
        msp.add_text(texto, dxfattribs={
            'height': 0.5,  # Ajustar tamanho do texto conforme necessário
            'layer': 'Moldura',  # Colocar na mesma camada do retângulo
            'insert': (ponto_superior_esquerdo[0] + x_margin * 0.5, ponto_superior_esquerdo[1] + y_margin * 0.5)  # Ajustar posição
        })

        # Chamar a função auxiliar para adicionar informações adicionais
        self.adicionar_informacoes_adicionais(msp, ponto_superior_esquerdo, x_margin, y_margin, estacas_data, pontos_apoio_data)

        # Retornar as coordenadas dos vértices inferiores e a altura do retângulo principal
        altura_retangulo_principal = y_max - y_min
        return ponto_inferior_esquerdo, ponto_inferior_direito, altura_retangulo_principal

    def adicionar_linhas_verticais(self, msp, estacas_data, x_min, y_min):
        """
        Adiciona linhas verticais sólidas na cor azul entre o eixo X e a linha 'Corte' para cada ponto de estaca.
        """
        # Desempacotar os dados de estacas
        estacas_ids, estacas_distances, estacas_novoz, _, _, _, _ = zip(*estacas_data)

        # Definir a camada 'Linhas_Verticais' para as linhas verticais
        if 'Linhas_Verticais' not in msp.doc.layers:
            msp.doc.layers.new(name='Linhas_Verticais', dxfattribs={'color': 5})  # Azul

        # Dicionário para verificar se a linha já foi adicionada
        linhas_ja_adicionadas = set()

        # Adicionar linhas verticais sólidas usando polilinhas
        for x, y in zip(estacas_distances, estacas_novoz):
            # Verificar se já existe uma linha neste ponto x para evitar duplicação
            if (x, y_min, y) not in linhas_ja_adicionadas:
                # Adicionar polilinha vertical com dois pontos
                msp.add_lwpolyline(
                    [(x, y_min), (x, y)],
                    dxfattribs={
                        'layer': 'Linhas_Verticais',
                        'linetype': 'BYLAYER'  # Usando o tipo de linha padrão sólido
                    }
                )
                # Marcar como linha já adicionada
                linhas_ja_adicionadas.add((x, y_min, y))

    def adicionar_retangulo_inferior(self, msp, ponto_inferior_esquerdo, ponto_inferior_direito, altura_retangulo_principal, estacas_data, x_min, y_min):
        """
        Adiciona um retângulo abaixo e encostado ao retângulo principal,
        utilizando os vértices inferiores do retângulo principal.
        E adiciona os IDs das estacas alinhados com as linhas tracejadas no retângulo inferior.
        """
        # Definir a altura do retângulo inferior (ajuste conforme necessário)
        altura_retangulo_inferior = altura_retangulo_principal * 0.2  # Por exemplo, 20% da altura do retângulo principal

        # Coordenadas do retângulo inferior (em relação ao retângulo principal)
        ponto_inferior_esquerdo_inferior = (ponto_inferior_esquerdo[0], ponto_inferior_esquerdo[1] - altura_retangulo_inferior)
        ponto_inferior_direito_inferior = (ponto_inferior_direito[0], ponto_inferior_direito[1] - altura_retangulo_inferior)
        ponto_superior_direito_inferior = (ponto_inferior_direito[0], ponto_inferior_direito[1])
        ponto_superior_esquerdo_inferior = (ponto_inferior_esquerdo[0], ponto_inferior_esquerdo[1])

        # Desenhar o retângulo inferior como uma polilinha fechada
        msp.add_lwpolyline([
            ponto_inferior_esquerdo_inferior,
            ponto_inferior_direito_inferior,
            ponto_superior_direito_inferior,
            ponto_superior_esquerdo_inferior,
            ponto_inferior_esquerdo_inferior  # Fechar o loop
        ], dxfattribs={'layer': 'Moldura'}, close=True)

        # Definir o estilo de texto Arial se ainda não existir
        if 'Arial' not in msp.doc.styles:
            msp.doc.styles.new('Arial', dxfattribs={'font': 'arial.ttf'})  # Define o estilo Arial usando a fonte arial.ttf

        # Adicionar o título "Estacas" alinhado com as IDs e na cor verde
        texto_estacas_x = ponto_inferior_esquerdo_inferior[0] + 0.1  # Definir a posição horizontal do texto "Estacas"
        msp.add_text("Estacas", dxfattribs={
            'height': 0.7,  # Ajuste o tamanho do texto conforme necessário
            'layer': 'Moldura',
            'color': 3,  # Cor verde
            'insert': (texto_estacas_x, ponto_inferior_esquerdo_inferior[1] + 1),  # Alinhamento com as IDs
            'style': 'Arial',
        })

        # Adicionar uma linha vertical de separação entre o texto "Estacas" e os IDs
        linha_vertical_x = texto_estacas_x + 4  # Ajuste a posição horizontal da linha vertical
        msp.add_line(
            (linha_vertical_x, ponto_inferior_esquerdo_inferior[1]),  # Ponto inicial (embaixo)
            (linha_vertical_x, ponto_inferior_esquerdo_inferior[1] + altura_retangulo_inferior),  # Ponto final (em cima)
            dxfattribs={'layer': 'Moldura', 'color': 256}  # Cor BYLAYER
        )

        # Adicionar os IDs das estacas alinhados com as linhas tracejadas no retângulo inferior
        for estaca in estacas_data:
            estaca_id = estaca[0]  # Pegar o ID da estaca
            estaca_distance = estaca[1]  # Pegar a distância acumulada

            # Inserir o texto do ID alinhado com a distância acumulada da estaca
            msp.add_text(f"{estaca_id}", dxfattribs={
                'height': 0.75,  # Ajuste o tamanho do texto conforme necessário
                'layer': 'Moldura',
                'color': 3,  # Cor verde
                'insert': (estaca_distance, ponto_inferior_esquerdo_inferior[1] + 1),  # Alinhamento horizontal com as estacas
                'rotation': 0,
                'style': 'Arial',
            })

        # Retornar as coordenadas dos vértices inferiores e a altura do retângulo inferior
        altura_retangulo_inferior = altura_retangulo_principal * 0.2  # Mesma altura definida anteriormente
        return ponto_inferior_esquerdo_inferior, ponto_inferior_direito_inferior, altura_retangulo_inferior

    def adicionar_terceiro_retangulo(self, msp, ponto_inferior_esquerdo_inferior, ponto_inferior_direito_inferior, altura_retangulo_inferior, estacas_data):
        """
        Adiciona um terceiro retângulo abaixo e encostado ao retângulo inferior,
        utilizando os vértices inferiores do retângulo inferior.
        Adiciona os textos "Cota" e "Terreno" e exibe apenas os valores de Z das estacas.
        """
        # Definir a altura do terceiro retângulo (mesma altura do retângulo inferior)
        altura_terceiro_retangulo = altura_retangulo_inferior  # Mesmo tamanho do retângulo inferior

        # Coordenadas do terceiro retângulo (em relação ao retângulo inferior)
        ponto_inferior_esquerdo_terceiro = (ponto_inferior_esquerdo_inferior[0], ponto_inferior_esquerdo_inferior[1] - altura_terceiro_retangulo)
        ponto_inferior_direito_terceiro = (ponto_inferior_direito_inferior[0], ponto_inferior_direito_inferior[1] - altura_terceiro_retangulo)
        ponto_superior_direito_terceiro = (ponto_inferior_direito_inferior[0], ponto_inferior_direito_inferior[1])
        ponto_superior_esquerdo_terceiro = (ponto_inferior_esquerdo_inferior[0], ponto_inferior_esquerdo_inferior[1])

        # Desenhar o terceiro retângulo como uma polilinha fechada
        msp.add_lwpolyline([
            ponto_inferior_esquerdo_terceiro,
            ponto_inferior_direito_terceiro,
            ponto_superior_direito_terceiro,
            ponto_superior_esquerdo_terceiro,
            ponto_inferior_esquerdo_terceiro  # Fechar o loop
        ], dxfattribs={'layer': 'Moldura'}, close=True)

        # Definir o estilo de texto Arial se ainda não existir
        if 'Arial' not in msp.doc.styles:
            msp.doc.styles.new('Arial', dxfattribs={'font': 'arial.ttf'})  # Define o estilo Arial usando a fonte arial.ttf

        # Adicionar os textos "Cota" e "Terreno" um abaixo do outro, alinhados à esquerda
        texto_cota_x = ponto_inferior_esquerdo_terceiro[0] + 0.1  # Posição horizontal para os textos
        texto_terreno_y = ponto_inferior_esquerdo_terceiro[1] + altura_terceiro_retangulo - 1.5  # Posição vertical para "Terreno"

        msp.add_text("Terreno", dxfattribs={
            'height': 0.6,
            'layer': 'Moldura',
            'color': 1,  # Cor Vermelho
            'insert': (texto_cota_x, texto_terreno_y),
            'style': 'Arial',
        })

        # Adicionar uma linha vertical de separação entre o texto e os valores
        linha_vertical_x = texto_cota_x + 4  # Ajuste a posição horizontal da linha vertical
        msp.add_line(
            (linha_vertical_x, ponto_inferior_esquerdo_terceiro[1]),  # Ponto inicial (embaixo)
            (linha_vertical_x, ponto_inferior_esquerdo_terceiro[1] + altura_terceiro_retangulo),  # Ponto final (em cima)
            dxfattribs={'layer': 'Moldura'}
        )

        # Adicionar os valores de Z (Terreno) das estacas alinhados com as linhas tracejadas
        for estaca in estacas_data:
            estaca_distance = estaca[1]  # Pegar a distância acumulada
            z_terreno = estaca[3]  # Z (Terreno)

            # Inserir o valor de "Terreno" (Z)
            msp.add_text(f"{z_terreno:.2f}", dxfattribs={
                'height': 0.55,
                'layer': 'Moldura',
                'color': 7,  # Cor Padrão
                'insert': (estaca_distance, texto_terreno_y),
                'rotation': 0,
                'style': 'Arial',
                'color': 1,  # Cor Vermelho
            })

        # Retornar as coordenadas dos vértices inferiores e a altura do terceiro retângulo
        return ponto_inferior_esquerdo_terceiro, ponto_inferior_direito_terceiro, altura_terceiro_retangulo

    def adicionar_quarto_retangulo(self, msp, ponto_inferior_esquerdo_terceiro, ponto_inferior_direito_terceiro, altura_terceiro_retangulo, estacas_data):
        """
        Adiciona um quarto retângulo abaixo e encostado ao terceiro retângulo,
        utilizando os vértices inferiores do terceiro retângulo.
        Adiciona o texto "Corte" e exibe os valores de NovoZ das estacas.
        """
        # Definir a altura do quarto retângulo (mesma altura dos retângulos anteriores)
        altura_quarto_retangulo = altura_terceiro_retangulo  # Mesmo tamanho do retângulo anterior

        # Coordenadas do quarto retângulo (em relação ao terceiro retângulo)
        ponto_inferior_esquerdo_quarto = (ponto_inferior_esquerdo_terceiro[0], ponto_inferior_esquerdo_terceiro[1] - altura_quarto_retangulo)
        ponto_inferior_direito_quarto = (ponto_inferior_direito_terceiro[0], ponto_inferior_direito_terceiro[1] - altura_quarto_retangulo)
        ponto_superior_direito_quarto = (ponto_inferior_direito_terceiro[0], ponto_inferior_direito_terceiro[1])
        ponto_superior_esquerdo_quarto = (ponto_inferior_esquerdo_terceiro[0], ponto_inferior_esquerdo_terceiro[1])

        # Desenhar o quarto retângulo como uma polilinha fechada
        msp.add_lwpolyline([
            ponto_inferior_esquerdo_quarto,
            ponto_inferior_direito_quarto,
            ponto_superior_direito_quarto,
            ponto_superior_esquerdo_quarto,
            ponto_inferior_esquerdo_quarto  # Fechar o loop
        ], dxfattribs={'layer': 'Moldura'}, close=True)

        # Definir o estilo de texto Arial se ainda não existir
        if 'Arial' not in msp.doc.styles:
            msp.doc.styles.new('Arial', dxfattribs={'font': 'arial.ttf'})  # Define o estilo Arial usando a fonte arial.ttf

        # Adicionar o texto "Corte" alinhado à esquerda
        texto_corte_x = ponto_inferior_esquerdo_quarto[0] + 0.1  # Posição horizontal para o texto
        texto_corte_y = ponto_inferior_esquerdo_quarto[1] + altura_quarto_retangulo - 1.5  # Posição vertical para "Corte"

        msp.add_text("Corte", dxfattribs={
            'height': 0.55,
            'color': 5,  # Cor Azul
            'layer': 'Moldura',
            'insert': (texto_corte_x, texto_corte_y),
            'style': 'Arial',
        })

        # Adicionar uma linha vertical de separação entre o texto e os valores
        linha_vertical_x = texto_corte_x + 4  # Ajuste a posição horizontal da linha vertical
        msp.add_line(
            (linha_vertical_x, ponto_inferior_esquerdo_quarto[1]),  # Ponto inicial (embaixo)
            (linha_vertical_x, ponto_inferior_esquerdo_quarto[1] + altura_quarto_retangulo),  # Ponto final (em cima)
            dxfattribs={'layer': 'Moldura'}
        )

        # Adicionar os valores de NovoZ (Corte) das estacas alinhados com as linhas tracejadas
        for estaca in estacas_data:
            estaca_distance = estaca[1]  # Pegar a distância acumulada
            novo_z = estaca[2]  # NovoZ (Corte)

            # Inserir o valor de "Corte" (NovoZ)
            msp.add_text(f"{novo_z:.2f}", dxfattribs={
                'height': 0.55,
                'layer': 'Moldura',
                'insert': (estaca_distance, texto_corte_y),
                'rotation': 0,
                'style': 'Arial',
                'color': 5,  # Cor Azul
            })

        return ponto_inferior_esquerdo_quarto, ponto_inferior_direito_quarto, altura_quarto_retangulo

    def adicionar_quinto_retangulo(self, msp, ponto_inferior_esquerdo_quarto, ponto_inferior_direito_quarto, altura_quarto_retangulo, estacas_data):
        """
        Adiciona um quinto retângulo abaixo e encostado ao quarto retângulo,
        utilizando os vértices inferiores do quarto retângulo.
        Adiciona o texto "Desnível" e exibe os valores de desnível das estacas.
        """
        # Definir a altura do quinto retângulo (mesma altura dos retângulos anteriores)
        altura_quinto_retangulo = altura_quarto_retangulo  # Mesmo tamanho do retângulo anterior

        # Coordenadas do quinto retângulo (em relação ao quarto retângulo)
        ponto_inferior_esquerdo_quinto = (ponto_inferior_esquerdo_quarto[0], ponto_inferior_esquerdo_quarto[1] - altura_quinto_retangulo)
        ponto_inferior_direito_quinto = (ponto_inferior_direito_quarto[0], ponto_inferior_direito_quarto[1] - altura_quinto_retangulo)
        ponto_superior_direito_quinto = (ponto_inferior_direito_quarto[0], ponto_inferior_direito_quarto[1])
        ponto_superior_esquerdo_quinto = (ponto_inferior_esquerdo_quarto[0], ponto_inferior_esquerdo_quarto[1])

        # Desenhar o quinto retângulo como uma polilinha fechada
        msp.add_lwpolyline([
            ponto_inferior_esquerdo_quinto,
            ponto_inferior_direito_quinto,
            ponto_superior_direito_quinto,
            ponto_superior_esquerdo_quinto,
            ponto_inferior_esquerdo_quinto  # Fechar o loop
        ], dxfattribs={'layer': 'Moldura'}, close=True)

        # Adicionar o texto "Desnível" alinhado à esquerda
        texto_desnivel_x = ponto_inferior_esquerdo_quinto[0] + 0.1  # Posição horizontal para o texto
        texto_desnivel_y = ponto_inferior_esquerdo_quinto[1] + altura_quinto_retangulo - 1.5  # Posição vertical para "Desnível"

        # Definir o estilo de texto Arial se ainda não existir
        if 'Arial' not in msp.doc.styles:
            msp.doc.styles.new('Arial', dxfattribs={'font': 'arial.ttf'})  # Define o estilo Arial usando a fonte arial.ttf

        msp.add_text("Desnível", dxfattribs={
            'height': 0.5,
            'color': 4,  # Cor Cian
            'layer': 'Moldura',
            'insert': (texto_desnivel_x, texto_desnivel_y),
            'style': 'Arial',
        })

        # Adicionar uma linha vertical de separação entre o texto e os valores
        linha_vertical_x = texto_desnivel_x + 4  # Ajuste a posição horizontal da linha vertical
        msp.add_line(
            (linha_vertical_x, ponto_inferior_esquerdo_quinto[1]),  # Ponto inicial (embaixo)
            (linha_vertical_x, ponto_inferior_esquerdo_quinto[1] + altura_quinto_retangulo),  # Ponto final (em cima)
            dxfattribs={'layer': 'Moldura'}
        )

        # Adicionar os valores de desnível das estacas alinhados com as linhas tracejadas
        for estaca in estacas_data:
            estaca_distance = estaca[1]  # Pegar a distância acumulada
            desnivel = estaca[4]  # Desnível

            # Inserir o valor de "Desnível"
            msp.add_text(f"{desnivel:.2f}", dxfattribs={
                'height': 0.5,
                'color': 4,  # Cor Cian
                'layer': 'Moldura',
                'insert': (estaca_distance, texto_desnivel_y),
                'rotation': 0,
                'style': 'Arial',
            })

        # Ao final da função, retorne os valores necessários
        return ponto_inferior_esquerdo_quinto, ponto_inferior_direito_quinto, altura_quinto_retangulo

    def adicionar_sexto_retangulo(self, msp, ponto_inferior_esquerdo_quinto, ponto_inferior_direito_quinto, altura_quinto_retangulo, estacas_data):
        """
        Adiciona um sexto retângulo abaixo e encostado ao quinto retângulo,
        utilizando os vértices inferiores do quinto retângulo.
        Adiciona o texto "Desnível (%)" e exibe os valores de desnível percentual das estacas com base no Terreno Natural.
        """
        # Definir a altura do sexto retângulo (mesma altura dos retângulos anteriores)
        altura_sexto_retangulo = altura_quinto_retangulo

        # Coordenadas do sexto retângulo (em relação ao quinto retângulo)
        ponto_inferior_esquerdo_sexto = (ponto_inferior_esquerdo_quinto[0], ponto_inferior_esquerdo_quinto[1] - altura_sexto_retangulo)
        ponto_inferior_direito_sexto = (ponto_inferior_direito_quinto[0], ponto_inferior_direito_quinto[1] - altura_sexto_retangulo)
        ponto_superior_direito_sexto = (ponto_inferior_direito_quinto[0], ponto_inferior_direito_quinto[1])
        ponto_superior_esquerdo_sexto = (ponto_inferior_esquerdo_quinto[0], ponto_inferior_esquerdo_quinto[1])

        # Desenhar o sexto retângulo como uma polilinha fechada
        msp.add_lwpolyline([
            ponto_inferior_esquerdo_sexto,
            ponto_inferior_direito_sexto,
            ponto_superior_direito_sexto,
            ponto_superior_esquerdo_sexto,
            ponto_inferior_esquerdo_sexto  # Fechar o loop
        ], dxfattribs={'layer': 'Moldura'}, close=True)

        # Adicionar o texto "Desnível (%)" alinhado à esquerda
        texto_desnivel_perc_x = ponto_inferior_esquerdo_sexto[0] + 0.1  # Posição horizontal para o texto
        texto_desnivel_perc_y = ponto_inferior_esquerdo_sexto[1] + altura_sexto_retangulo - 1.5  # Posição vertical para "Desnível (%)"

        # Definir o estilo de texto Arial se ainda não existir
        if 'Arial' not in msp.doc.styles:
            msp.doc.styles.new('Arial', dxfattribs={'font': 'arial.ttf'})  # Define o estilo Arial usando a fonte arial.ttf

        msp.add_text("Desnível(%)", dxfattribs={
            'height': 0.5,
            'color': 6,  # Cor Magenta
            'layer': 'Moldura',
            'insert': (texto_desnivel_perc_x, texto_desnivel_perc_y),
            'style': 'Arial',
        })

        # Adicionar uma linha vertical de separação entre o texto e os valores
        linha_vertical_x = texto_desnivel_perc_x + 4  # Ajuste a posição horizontal da linha vertical
        msp.add_line(
            (linha_vertical_x, ponto_inferior_esquerdo_sexto[1]),  # Ponto inicial (embaixo)
            (linha_vertical_x, ponto_inferior_esquerdo_sexto[1] + altura_sexto_retangulo),  # Ponto final (em cima)
            dxfattribs={'layer': 'Moldura'}
        )

        # Exibir o valor 0% para o primeiro ponto
        primeiro_ponto = estacas_data[0]
        msp.add_text("0.00", dxfattribs={
            'height': 0.5,
            'color': 6,  # Cor Magenta
            'layer': 'Moldura',
            'insert': (primeiro_ponto[1], texto_desnivel_perc_y),
            'rotation': 0,
            'style': 'Arial',
        })

        # Cálculo do desnível percentual para cada ponto em relação ao ponto anterior, a partir do segundo ponto
        for i in range(1, len(estacas_data)):
            estaca_atual = estacas_data[i]
            estaca_anterior = estacas_data[i - 1]
            
            distancia_entre_pontos = estaca_atual[1] - estaca_anterior[1]  # Diferença na distância acumulada
            if distancia_entre_pontos != 0:
                desnivel_percentual = ((estaca_atual[3] - estaca_anterior[3]) / distancia_entre_pontos) * 100  # Z do Terreno Natural
            else:
                desnivel_percentual = 0.0

            # Inserir o valor do "Desnível (%)" arredondado a duas casas decimais
            msp.add_text(f"{desnivel_percentual:.2f}", dxfattribs={
                'height': 0.5,
                'color': 6,  # Cor Magenta
                'layer': 'Moldura',
                'insert': (estaca_atual[1], texto_desnivel_perc_y),
                'rotation': 0,
                'style': 'Arial',
            })

        # Retornar as coordenadas dos vértices inferiores e a altura do sexto retângulo
        return ponto_inferior_esquerdo_sexto, ponto_inferior_direito_sexto, altura_sexto_retangulo

    def calcular_intersecao(self, p1, p2, p3, p4):
        """
        Calcula o ponto de interseção entre duas linhas definidas por p1->p2 e p3->p4.
        Retorna o ponto de interseção como (x, y) ou None se não houver interseção.
        """
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4

        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if denom == 0:
            return None  # Linhas são paralelas

        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        if 0 <= ua <= 1 and 0 <= ub <= 1:
            # Calcula o ponto de interseção
            x = x1 + ua * (x2 - x1)
            y = y1 + ua * (y2 - y1)
            return (x, y)
        return None

    def preencher_com_hachura(self, msp, estacas_data, pontos_apoio_data):
        _, estacas_distances, estacas_novoz, _, _, _, _ = zip(*estacas_data)
        apoio_distances, apoio_elevations = zip(*pontos_apoio_data)

        if 'Hachura' not in msp.doc.layers:
            msp.doc.layers.new(name='Hachura', dxfattribs={'color': 7})

        interseccoes = []
        for i in range(1, len(estacas_distances)):
            x1, y1 = estacas_distances[i - 1], estacas_novoz[i - 1]
            x2, y2 = estacas_distances[i], estacas_novoz[i]
            for j in range(1, len(apoio_distances)):
                xa, ya = apoio_distances[j - 1], apoio_elevations[j - 1]
                xb, yb = apoio_distances[j], apoio_elevations[j]
                ponto_intersec = self.calcular_intersecao((x1, y1), (x2, y2), (xa, ya), (xb, yb))
                if ponto_intersec:
                    interseccoes.append(ponto_intersec)

        # Definir os ângulos para os taludes e calcular os pontos precisos de início e fim para as hachuras dos taludes
        angle_135 = math.radians(135)
        angle_45 = math.radians(45)

        # Calcular pontos de interseção precisos para o talude inicial
        x0 = estacas_distances[0]
        y0 = estacas_novoz[0]
        y0_tn = np.interp(x0, apoio_distances, apoio_elevations)
        line_length_initial = abs(y0_tn - y0)
        if y0_tn > y0:
            dx0 = line_length_initial / math.tan(angle_135)
            x_end0 = x0 + dx0
        else:
            dx0 = line_length_initial / math.tan(angle_45)
            x_end0 = x0 - dx0
        y_end0 = y0_tn

        # Calcular pontos de interseção precisos para o talude final
        xn = estacas_distances[-1]
        yn = estacas_novoz[-1]
        yn_tn = np.interp(xn, apoio_distances, apoio_elevations)
        line_length_final = abs(yn_tn - yn)
        if yn_tn > yn:
            dxn = line_length_final / math.tan(angle_135)
            x_endn = xn - dxn
        else:
            dxn = line_length_final / math.tan(angle_45)
            x_endn = xn + dxn
        y_endn = yn_tn

        interseccoes.insert(0, (x_end0, y_end0))
        interseccoes.append((x_endn, y_endn))
        interseccoes.sort()

        for k in range(len(interseccoes) - 1):
            x_start, y_start = interseccoes[k]
            x_end, y_end = interseccoes[k + 1]

            # Filtrar as coordenadas da linha "Corte" entre x_start e x_end
            corte_coords = [(x, y) for x, y in zip(estacas_distances, estacas_novoz) if x_start <= x <= x_end]
            if not corte_coords:
                continue

            # Filtrar as coordenadas da linha "Terreno Natural" entre x_start e x_end
            tn_coords = [(x, y) for x, y in zip(apoio_distances, apoio_elevations) if x_start <= x <= x_end]
            if not tn_coords:
                continue

            # Construir o contorno do polígono para hachura usando pontos exatos de interseção
            poligono_hachura = [(x_start, y_start)] + corte_coords + [(x_end, y_end)] + tn_coords[::-1]

            # Calcular o ponto médio da seção
            x_mid = (x_start + x_end) / 2

            # Interpolar os valores de y para "Corte" e "Terreno Natural" no ponto médio
            y_corte_mid = np.interp(x_mid, estacas_distances, estacas_novoz)
            y_tn_mid = np.interp(x_mid, apoio_distances, apoio_elevations)

            # Calcular a diferença
            diferenca = y_corte_mid - y_tn_mid

            # Determinar a cor da hachura com base na diferença
            if diferenca > 0:
                hatch_color = 5  # Azul
                # self._log_message(f"Hachura azul aplicada na seção {k}", Qgis.Info)
            else:
                hatch_color = 1  # Vermelho
                # self._log_message(f"Hachura vermelha aplicada na seção {k}", Qgis.Info)

            # Adicionar a hachura para o contorno delimitado
            hatch = msp.add_hatch(color=hatch_color, dxfattribs={'layer': 'Hachura'})
            hatch.paths.add_polyline_path(poligono_hachura, is_closed=True)

    def adicionar_legendas_dxf(self, msp, x_min, x_max, y_max, escala, y_margin):
        """
        Adiciona legendas ao DXF, incluindo linhas e textos para "Perfil de Corte/Aterro," "Terreno,"
        "Talude," e retângulos para as áreas de "Corte" e "Aterro."
        """
        # Definir a altura inicial das legendas, acima do gráfico
        y_text_line = y_max + y_margin * 0.5

        # Posição horizontal inicial para a primeira legenda
        x_start_text = x_min + y_margin * 0.5

        # **Perfil de Corte/Aterro**
        msp.add_line((x_start_text, y_text_line), (x_start_text + 3 * escala, y_text_line), dxfattribs={'layer': 'Corte', 'color': 5})
        msp.add_text("Perfil de Corte/Aterro", dxfattribs={
            'height': 0.35 * escala,
            'layer': 'Corte',
            'insert': (x_start_text + 3.5 * escala, y_text_line),
            'style': 'Arial'
        })

        # **Terreno**
        x_start_text += 10 * escala
        msp.add_line((x_start_text, y_text_line), (x_start_text + 3 * escala, y_text_line), dxfattribs={'layer': 'Terreno_Natural', 'color': 1})
        msp.add_text("Terreno", dxfattribs={
            'height': 0.35 * escala,
            'layer': 'Terreno_Natural',
            'insert': (x_start_text + 3.5 * escala, y_text_line),
            'style': 'Arial'
        })

        # **Talude**
        x_start_text += 7 * escala
        msp.add_line((x_start_text, y_text_line), (x_start_text + 3 * escala, y_text_line), dxfattribs={'layer': 'Talude', 'color': 3})
        msp.add_text("Talude", dxfattribs={
            'height': 0.35 * escala,
            'layer': 'Talude',
            'insert': (x_start_text + 3.5 * escala, y_text_line),
            'style': 'Arial'
        })

        # **Área de Corte (vermelho)**
        x_start_text += 7 * escala
        corte_rect_x = x_start_text
        corte_rect_y = y_text_line - 0.1 * escala
        msp.add_lwpolyline([
            (corte_rect_x, corte_rect_y),
            (corte_rect_x + 1 * escala, corte_rect_y),
            (corte_rect_x + 1 * escala, corte_rect_y + 0.5 * escala),
            (corte_rect_x, corte_rect_y + 0.5 * escala),
            (corte_rect_x, corte_rect_y)
        ], dxfattribs={'layer': 'Hachura', 'color': 1})  # Vermelho
        msp.add_text("Área de Corte", dxfattribs={
            'height': 0.35 * escala,
            'layer': 'Hachura',
            'insert': (corte_rect_x + 2.5 * escala, corte_rect_y),
            'style': 'Arial'
        })

        # **Área de Aterro (azul)**
        x_start_text += 7 * escala
        aterro_rect_x = x_start_text
        aterro_rect_y = y_text_line - 0.1 * escala
        msp.add_lwpolyline([
            (aterro_rect_x, aterro_rect_y),
            (aterro_rect_x + 1 * escala, aterro_rect_y),
            (aterro_rect_x + 1 * escala, aterro_rect_y + 0.5 * escala),
            (aterro_rect_x, aterro_rect_y + 0.5 * escala),
            (aterro_rect_x, aterro_rect_y)
        ], dxfattribs={'layer': 'Hachura', 'color': 5})  # Azul
        msp.add_text("Área de Aterro", dxfattribs={
            'height': 0.35 * escala,
            'layer': 'Hachura',
            'insert': (aterro_rect_x + 2.5 * escala, aterro_rect_y),
            'style': 'Arial'
        })

    def exportar_eixos(self, msp, estacas_data, pontos_apoio_data):
        # Desempacotando os dados
        estacas_ids, estacas_distances, estacas_novoz, _, _, _, _ = zip(*estacas_data)
        apoio_distances, apoio_elevations = zip(*pontos_apoio_data)

        # Manter os limites originais do eixo X com base em apoio_distances
        x_min = min(apoio_distances)
        x_max = max(apoio_distances)
        y_min = min(min(estacas_novoz), min(apoio_elevations))
        y_max = max(max(estacas_novoz), max(apoio_elevations))

        # Definir um intervalo mínimo para o eixo Y
        intervalo_minimo_y = 10  # Valor mínimo para o intervalo vertical
        intervalo_y = y_max - y_min

        if intervalo_y < intervalo_minimo_y:
            centro_y = (y_max + y_min) / 2
            y_min = centro_y - intervalo_minimo_y / 2
            y_max = centro_y + intervalo_minimo_y / 2

        # Adicionar margens
        x_margin = (x_max - x_min) * 0.05  # 5% de margem
        y_margin = (y_max - y_min) * 0.05  # 5% de margem

        # Definir uma margem mínima para garantir que labels e ticks caibam dentro do retângulo
        margem_minima = 1  # Ajuste este valor conforme necessário
        x_margin = max(x_margin, margem_minima)
        y_margin = max(y_margin, margem_minima)

        # Ajustar x_min, x_max, y_min e y_max com as margens
        x_min -= x_margin
        x_max += x_margin
        y_min -= y_margin
        y_max += y_margin

        # Usar apenas os valores de dist_acumulada das estacas (estacas_distances) para os ticks no eixo X
        all_ticks = np.unique(estacas_distances)

        # Filtrar ticks que estão dentro dos limites x_min e x_max
        all_ticks = all_ticks[(all_ticks >= x_min) & (all_ticks <= x_max)]

        # Definir o estilo de texto Arial se ainda não existir
        if 'Arial' not in msp.doc.styles:
            msp.doc.styles.new('Arial', dxfattribs={'font': 'arial.ttf'})  # Define o estilo Arial usando a fonte arial.ttf

        # Desenhar os ticks e labels no eixo X
        for x in all_ticks:
            # Linha vertical pequena para o tick
            msp.add_line((x, y_min - y_margin * 0.3), (x, y_min + y_margin * 0.3), dxfattribs={'layer': 'Eixos'})
            # Label do tick
            msp.add_text(f"{x:.2f}", dxfattribs={
                'height': 0.5,
                'layer': 'Eixos',
                'insert': (x, y_min - y_margin * 1.5),
                'rotation': 0,
                'style': 'Arial'
            })

        # Adicionar ticks no eixo Y com valores próximos à linha horizontal do tick
        num_ticks_y = 9  # Agora serão 9 ticks no total
        y_ticks = np.linspace(y_min + y_margin, y_max - y_margin, num_ticks_y)

        # Margem fixa para posicionar os rótulos ao lado da linha horizontal
        margem_fixa_x = x_min - 2.5  # Valor fixo ao lado do eixo Y

        for y in y_ticks:
            # Linha horizontal pequena para o tick, agora na cor vermelha (color=1)
            msp.add_line(
                (x_min - x_margin * 0.1, y),
                (x_min + x_margin * 0.1, y),
                dxfattribs={'layer': 'Eixos', 'color': 1}
            )
            # Label do tick fixado na mesma posição horizontal ao lado da linha do tick
            msp.add_text(f"{y:.2f}", dxfattribs={
                'height': 0.45,
                'layer': 'Eixos',
                'insert': (margem_fixa_x, y),  # Posição fixa ao lado dos ticks
                'rotation': 0,
                'style': 'Arial'
            })
            
            # Linha horizontal paralela completa, cor cinza
            msp.add_line(
                (x_min, y),  # Início da linha no lado esquerdo
                (x_max, y),  # Final da linha no lado direito
                dxfattribs={'layer': 'Eixos', 'color': 254}  # Cinza
            )

        # Adicionar o contorno do retângulo ao redor dos eixos X e Y
        msp.add_lwpolyline([
            (x_min, y_min),  # Inferior esquerdo
            (x_max, y_min),  # Inferior direito
            (x_max, y_max),  # Superior direito
            (x_min, y_max),  # Superior esquerdo
            (x_min, y_min)   # Fechar o loop
        ], dxfattribs={'layer': 'Eixos'}, close=True)

        # Calcular a escala para as legendas
        escala = (x_max - x_min) / 100

        # Adicionar legendas usando a função auxiliar
        self.adicionar_legendas_dxf(msp, x_min, x_max, y_max, escala, y_margin)

        # No final da função, retornar x_min e y_min
        return x_min, y_min

    def exportar_tabela_dxf(self, msp, ponto_inferior_esquerdo_sexto, ponto_inferior_direito_sexto, altura_sexto_retangulo):
        """
        Exporta a tabela de atributos da camada selecionada no comboBoxGrupoZ para o DXF,
        posicionando-a logo abaixo do sexto retângulo.
        """
        # Obter o nome da camada selecionada no comboBox
        nome_camada = self.comboBoxGrupoZ.currentText()
        
        # Recuperar a camada pelo nome
        camada = QgsProject.instance().mapLayersByName(nome_camada)
        
        # Verificar se a camada foi encontrada e é válida
        if camada:
            camada = camada[0]  # Acessa a primeira camada que corresponde ao nome
            
            # Criar uma camada para a tabela
            msp.doc.layers.new(name='Tabela_Atributos', dxfattribs={'color': 7})  # Amarelo

            # Definir posição inicial para o texto da tabela no DXF
            pos_x = ponto_inferior_esquerdo_sexto[0] + 0.1  # Posição horizontal ajustada
            pos_y = ponto_inferior_esquerdo_sexto[1] - altura_sexto_retangulo - 1  # Logo abaixo do sexto retângulo
            cell_width = 7  # Largura de cada célula da tabela
            cell_height = 1  # Altura de cada célula da tabela

            # Adicionar cabeçalhos com células
            headers = [field.name() for field in camada.fields()]
            for col_index, header in enumerate(headers):
                # Definir a posição de inserção no lado esquerdo da célula
                header_x = pos_x + col_index * cell_width + 0.3  # Ajuste de margem para a esquerda
                header_y = pos_y - cell_height / 2 - 0.3
                # Adicionar o texto do cabeçalho
                msp.add_text(header, dxfattribs={
                    'layer': 'Tabela_Atributos',
                    'height': 0.5,
                    'insert': (header_x, header_y),
                })
                # Desenhar as células de cabeçalho (retângulos)
                msp.add_lwpolyline([
                    (pos_x + col_index * cell_width, pos_y),
                    (pos_x + (col_index + 1) * cell_width, pos_y),
                    (pos_x + (col_index + 1) * cell_width, pos_y - cell_height),
                    (pos_x + col_index * cell_width, pos_y - cell_height),
                    (pos_x + col_index * cell_width, pos_y)
                ], dxfattribs={'layer': 'Tabela_Atributos', 'color': 7})

            # Ajustar a posição vertical para os valores dos atributos
            pos_y -= cell_height

            # Adicionar os valores dos atributos com células
            for feature in camada.getFeatures():
                for col_index, field in enumerate(camada.fields()):
                    valor = str(feature[field.name()])
                    # Definir a posição de inserção no lado esquerdo da célula
                    valor_x = pos_x + col_index * cell_width + 0.3  # Ajuste de margem para a esquerda
                    valor_y = pos_y - cell_height / 2 - 0.3
                    # Adicionar o texto do valor
                    msp.add_text(valor, dxfattribs={
                        'layer': 'Tabela_Atributos',
                        'height': 0.5,
                        'insert': (valor_x, valor_y),
                    })
                    # Desenhar a célula (retângulo) ao redor do valor
                    msp.add_lwpolyline([
                        (pos_x + col_index * cell_width, pos_y),
                        (pos_x + (col_index + 1) * cell_width, pos_y),
                        (pos_x + (col_index + 1) * cell_width, pos_y - cell_height),
                        (pos_x + col_index * cell_width, pos_y - cell_height),
                        (pos_x + col_index * cell_width, pos_y)
                    ], dxfattribs={'layer': 'Tabela_Atributos', 'color': 7})

                # Ajustar a posição vertical para a próxima linha
                pos_y -= cell_height

            # Remover a linha extra na parte inferior da tabela
            pos_y += cell_height

    def exportar_dxf(self):
        # Obter o nome da camada selecionada no comboBoxGrupoZ
        nome_camada = self.comboBoxGrupoZ.currentText()

        # Usar a função escolher_local_para_salvar para obter o caminho do arquivo
        filename = self.escolher_local_para_salvar(nome_camada, "DXF Files (*.dxf)")
        if not filename:
            return  # Se o usuário cancelou, sair

        try:
            # Obter os dados necessários
            estacas_data, pontos_apoio_data = self.obter_dados_para_exportacao()
            if estacas_data is None or pontos_apoio_data is None:
                return  # Mensagem de erro já exibida

            # Iniciar o cronômetro
            tempo_inicio = time.time()

            # Criar um novo documento DXF
            doc = ezdxf.new(dxfversion='R2013')
            msp = doc.modelspace()

            # Definir camadas para o DXF
            doc.layers.new(name='Corte', dxfattribs={'color': 5})  # Azul
            doc.layers.new(name='Terreno_Natural', dxfattribs={'color': 1})  # Vermelho
            doc.layers.new(name='Talude', dxfattribs={'color': 3})  # Verde
            doc.layers.new(name='Eixos', dxfattribs={'color': 7})  # Branco
            doc.layers.new(name='Moldura', dxfattribs={'color': 256})  # Branco (para o retângulo)

            # Exportar os eixos X e Y e obter x_min e y_min
            x_min, y_min = self.exportar_eixos(msp, estacas_data, pontos_apoio_data)

            # Preencher com hachura
            self.preencher_com_hachura(msp, estacas_data, pontos_apoio_data)

            # Exportar as linhas principais
            self.exportar_linhas_principais(msp, estacas_data, pontos_apoio_data)

            # Exportar as linhas de talude
            self.exportar_linhas_talude(msp, estacas_data, pontos_apoio_data)

            # Adicionar linhas tracejadas do eixo X até a linha 'Corte'
            self.adicionar_linhas_verticais(msp, estacas_data, x_min, y_min)

            # Adicionar retângulo ao redor do gráfico e obter os vértices
            ponto_inferior_esquerdo, ponto_inferior_direito, altura_retangulo_principal = self.adicionar_retangulo_ao_redor(
                msp, estacas_data, pontos_apoio_data)

            # Adicionar retângulo inferior encostado ao retângulo principal com IDs das estacas alinhados com as linhas tracejadas
            ponto_inferior_esquerdo_inferior, ponto_inferior_direito_inferior, altura_retangulo_inferior = self.adicionar_retangulo_inferior(
                msp, ponto_inferior_esquerdo, ponto_inferior_direito, altura_retangulo_principal, estacas_data, x_min, y_min)

            # Adicionar o terceiro retângulo abaixo do retângulo inferior
            ponto_inferior_esquerdo_terceiro, ponto_inferior_direito_terceiro, altura_terceiro_retangulo = self.adicionar_terceiro_retangulo(
                msp, ponto_inferior_esquerdo_inferior, ponto_inferior_direito_inferior, altura_retangulo_inferior, estacas_data)

            # Adicionar o quarto retângulo abaixo do terceiro retângulo
            ponto_inferior_esquerdo_quarto, ponto_inferior_direito_quarto, altura_quarto_retangulo = self.adicionar_quarto_retangulo(
                msp, ponto_inferior_esquerdo_terceiro, ponto_inferior_direito_terceiro, altura_terceiro_retangulo, estacas_data)

            # Adicionar o quinto retângulo abaixo do quarto retângulo
            ponto_inferior_esquerdo_quinto, ponto_inferior_direito_quinto, altura_quinto_retangulo = self.adicionar_quinto_retangulo(
                msp, ponto_inferior_esquerdo_quarto, ponto_inferior_direito_quarto, altura_quarto_retangulo, estacas_data)

            # Adicionar o sexto retângulo abaixo do quinto retângulo
            ponto_inferior_esquerdo_sexto, ponto_inferior_direito_sexto, altura_sexto_retangulo = self.adicionar_sexto_retangulo(
                msp, ponto_inferior_esquerdo_quinto, ponto_inferior_direito_quinto, altura_quinto_retangulo, estacas_data)

            # Exportar tabela de atributos, se o checkbox estiver marcado
            if self.checkBoxTabela.isChecked():
                self.exportar_tabela_dxf(msp, ponto_inferior_esquerdo_sexto, ponto_inferior_direito_sexto, altura_sexto_retangulo)

            # Calcular o tempo de execução
            tempo_fim = time.time()
            tempo_execucao = tempo_fim - tempo_inicio

            # Salvar o arquivo DXF
            doc.saveas(filename)

            # Exibir mensagem de sucesso com botões "Abrir Pasta" e "Executar"
            caminho_pasta = os.path.dirname(filename)
            self.mostrar_mensagem(f"Arquivo DXF salvo com sucesso em: {tempo_execucao:.2f} segundos", "Sucesso", caminho_pasta=caminho_pasta, caminho_arquivo=filename)

        except Exception as e:
            self.mostrar_mensagem(f"Erro ao exportar DXF: {str(e)}", "Erro")

    def close_dialog(self):
        """Fecha o diálogo quando o botão Fechar é clicado."""
        self.close()


