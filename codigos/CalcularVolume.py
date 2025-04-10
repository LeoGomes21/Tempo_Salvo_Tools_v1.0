from qgis.core import QgsProject, QgsRasterLayer, QgsMapSettings, QgsMapRendererCustomPainterJob, Qgis, QgsMessageLog, QgsLayerTreeLayer, QgsRasterBandStats, QgsRasterShader, QgsColorRampShader, QgsSingleBandPseudoColorRenderer, QgsSingleBandGrayRenderer, QgsVectorLayer, QgsFields, QgsField, QgsPointXY, QgsRaster, QgsGeometry, QgsRectangle, QgsFeature, QgsFillSymbol, QgsRendererRange, QgsGraduatedSymbolRenderer
from qgis.PyQt.QtWidgets import QDialog, QCheckBox, QComboBox, QPushButton, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QListView, QLabel, QVBoxLayout, QListWidgetItem, QLabel, QProgressBar, QApplication, QStyledItemDelegate, QStyleOptionViewItem, QStyle, QAbstractItemView, QFileDialog, QProgressBar
from qgis.PyQt.QtGui import QImage, QPainter, QPixmap, QColor, QStandardItemModel, QStandardItem, QFont, QPen, QBrush
from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator
from qgis.PyQt.QtCore import Qt, QSize, QFileInfo, QVariant, QRect, QPoint, QEvent, QSettings, QItemSelectionModel, QCoreApplication
from qgis.utils import iface
from qgis.PyQt import uic
from osgeo import gdal
import pandas as pd
import numpy as np
import processing
import tempfile
import time
import math
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'calcularVolumeMDT.ui'))

class VolumeManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(VolumeManager, self).__init__(parent)
        # Configura a interface do usuário a partir do Designer.
        self.setupUi(self)
        # Altera o título da janela
        self.setWindowTitle("Calcular Volumes entre MDTs")

        self.iface = iface

        # Cria uma cena gráfica para os QGraphicsViews
        self.scene = QGraphicsScene()
        self.scene2 = QGraphicsScene()  # Segunda cena gráfica

        self.graphicsViewRaster.setScene(self.scene)
        self.graphicsViewRaster2.setScene(self.scene2)  # Configura a segunda view

        # Inicializa os ComboBoxes de Raster
        self.init_combo_box_raster()

        self.setup_table_view()

        # Conecta os sinais aos slots
        self.connect_signals()

        # Configura a janela para permitir minimizar, maximizar e fechar
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)

    def connect_signals(self):
        # Conecta os sinais aos slots
        self.comboBoxRaster.currentIndexChanged.connect(self.display_raster)
        self.comboBoxRaster2.currentIndexChanged.connect(self.display_raster2)  # Conecta ao segundo ComboBox

        # Impede que o mesmo raster seja selecionado nos dois comboBoxes
        self.comboBoxRaster.currentIndexChanged.connect(self.sync_combo_boxes)
        self.comboBoxRaster2.currentIndexChanged.connect(self.sync_combo_boxes)

        # Conecta o sinal de remoção de camada
        QgsProject.instance().layersRemoved.connect(self.update_combo_box)

        # Conecta o sinal de remoção de camada
        QgsProject.instance().layersRemoved.connect(self.update_list_view_on_layer_removed)

        # Conecta o sinal de adição de camada
        QgsProject.instance().layersAdded.connect(self.handle_layers_added)

        # Conecta o sinal de alteração do nome da camada
        for layer in QgsProject.instance().mapLayers().values():
            layer.nameChanged.connect(self.update_combo_box)

        # Conecta o botão para Calcular a diferença entre as camadas Rasters
        self.pushButtonCalcular.clicked.connect(self.calculate_raster_difference)

        # Conecta o listWidgetRasters à função para exibir estatísticas ao selecionar uma camada
        self.listWidgetRasters.itemSelectionChanged.connect(self.display_raster_statistics)

        # Conectar o botão pushButtonVolume à função de cálculo de volume
        self.pushButtonVolume.clicked.connect(self.calculate_volume)

        # Conecta o botão de exportação ao método export_to_excel
        self.pushButtonExcel.clicked.connect(self.exportar_tabela_para_excel)

        # Conectar o botão pushButtonCancelar para fechar o diálogo
        self.pushButtonCancelar.clicked.connect(self.close)

        # Conectar a verificação das condições dos comboBoxes para ativar/desativar o pushButtonCalcular
        self.comboBoxRaster.currentIndexChanged.connect(self.verificar_condicoes_calculo)
        self.comboBoxRaster2.currentIndexChanged.connect(self.verificar_condicoes_calculo)

        # Método de inicialização do diálogo listWidget
        self.listWidgetRasters.setItemDelegate(ListDeleteButtonDelegate(self.listWidgetRasters))

        # Chama a verificação de condições ao iniciar
        # self.verificar_condicoes_calculo()

        self.listWidgetRasters.itemSelectionChanged.connect(self.verificar_selecao_volume)
        
        self.verificar_dados_excel()

    def update_combo_box(self):
        # Atualiza ambos os ComboBoxes quando camadas são adicionadas, removidas ou renomeadas
        current_index = self.comboBoxRaster.currentIndex()
        current_layer_id = self.comboBoxRaster.itemData(current_index)

        current_index2 = self.comboBoxRaster2.currentIndex()
        current_layer_id2 = self.comboBoxRaster2.itemData(current_index2)

        # Atualiza os ComboBoxes
        self.init_combo_box_raster()

        # Tenta restaurar a seleção anterior para ambos os ComboBoxes
        if current_layer_id:
            index = self.comboBoxRaster.findData(current_layer_id)
            if index != -1:
                self.comboBoxRaster.setCurrentIndex(index)
            else:
                if self.comboBoxRaster.count() > 0:
                    self.comboBoxRaster.setCurrentIndex(0)
                    self.display_raster()

        if current_layer_id2:
            index2 = self.comboBoxRaster2.findData(current_layer_id2)
            if index2 != -1:
                self.comboBoxRaster2.setCurrentIndex(index2)
            else:
                if self.comboBoxRaster2.count() > 0:
                    self.comboBoxRaster2.setCurrentIndex(0)
                    self.display_raster2()

    def display_raster(self):
        # Limpa a cena antes de adicionar um novo item
        self.scene.clear()

        # Obtém o ID da camada raster selecionada
        selected_raster_id = self.comboBoxRaster.currentData()

        # Busca a camada raster pelo ID
        selected_layer = QgsProject.instance().mapLayer(selected_raster_id)
        
        if isinstance(selected_layer, QgsRasterLayer):
            # Configurações do mapa
            map_settings = QgsMapSettings()
            map_settings.setLayers([selected_layer])
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

            # Ajusta a cena ao QGraphicsView
            self.graphicsViewRaster.setSceneRect(pixmap_item.boundingRect())
            self.graphicsViewRaster.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def display_raster2(self):
        # Limpa a segunda cena antes de adicionar um novo item
        self.scene2.clear()

        # Obtém o ID da camada raster selecionada
        selected_raster_id = self.comboBoxRaster2.currentData()

        # Busca a camada raster pelo ID
        selected_layer = QgsProject.instance().mapLayer(selected_raster_id)
        
        if isinstance(selected_layer, QgsRasterLayer):
            # Configurações do mapa
            map_settings = QgsMapSettings()
            map_settings.setLayers([selected_layer])
            map_settings.setBackgroundColor(QColor(255, 255, 255))
            
            # Define o tamanho da imagem a ser renderizada
            width = self.graphicsViewRaster2.viewport().width()
            height = self.graphicsViewRaster2.viewport().height()
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
            self.scene2.addItem(pixmap_item)

            # Ajusta a cena ao QGraphicsView
            self.graphicsViewRaster2.setSceneRect(pixmap_item.boundingRect())
            self.graphicsViewRaster2.fitInView(self.scene2.sceneRect(), Qt.KeepAspectRatio)

    def handle_layers_added(self, layers):
        # Chama a função de atualização quando novas camadas são adicionadas
        self._log_message("Layers added: " + ", ".join([layer.name() for layer in layers]))
        self.update_combo_box()

    def _log_message(self, message, level=Qgis.Info):
        QgsMessageLog.logMessage(message, 'GRAFICO', level=level)

    def showEvent(self, event):
        super(VolumeManager, self).showEvent(event)
        # Ajusta a visualização quando o diálogo é mostrado
        self.display_raster()
        self.display_raster2()
        self.clear_list_view()
        self.reset_table_view()  # Limpa o tableView ao iniciar o diálogo

        # Verifica e carrega camadas do grupo "Calculados" ao iniciar o diálogo
        self.load_calculados_group()

        # Reseta o estado dos checkboxes ao iniciar o diálogo
        self.checkBoxPoligono.setChecked(False)
        self.checkBoxCorteAterro.setChecked(False)
        self.checkBoxSalvar.setChecked(False)
        
        # Verifica as condições para habilitar/desabilitar o botão Calcular
        self.verificar_condicoes_calculo()

        self.verificar_selecao_volume()  # reseta o estado do pushButtonVolume ao iniciar o diálogo

        # Reseta o estado do pushButtonExcel ao iniciar o diálogo
        self.verificar_dados_excel()

    def closeEvent(self, event):
        parent = self.parent()
        if parent:
            parent.volume_mdt_dlg = None
        super(VolumeManager, self).closeEvent(event)

    def add_layer_to_group(self, layer, group_name):
        # Obtém o root do projeto QGIS
        root = QgsProject.instance().layerTreeRoot()

        # Verifica se o grupo já existe
        group = root.findGroup(group_name)

        # Se o grupo não existir, cria um novo
        if group is None:
            group = root.addGroup(group_name)

        # Adiciona a camada ao grupo
        layer_node = QgsLayerTreeLayer(layer)
        group.insertChildNode(0, layer_node)

        # Adiciona a camada ao projeto
        QgsProject.instance().addMapLayer(layer, False)

        # Atualiza a listView com as camadas do grupo
        self.update_list_view(group)

        self._log_message(f"Camada '{layer.name()}' adicionada ao grupo '{group_name}'.", Qgis.Info)

    def update_list_view_on_layer_removed(self, layer_ids):
        group = QgsProject.instance().layerTreeRoot().findGroup("Calculados")
        if group:
            self.update_list_view(group)
        else:
            self.clear_list_view()

    def clear_list_view(self):
        # Limpa o listWidgetRasters diretamente
        self.listWidgetRasters.clear()

        # Adiciona uma mensagem de que o grupo "Calculados" não existe mais
        self._log_message("Grupo 'Calculados' foi removido. A listView foi limpa.", Qgis.Info)

    def update_list_view(self, group):
        # Converte o listWidgetRasters em um QListWidget se ainda não for um
        list_widget = self.listWidgetRasters

        # Limpa o listWidget antes de adicionar novas entradas
        list_widget.clear()

        # Adiciona o cabeçalho com estilo
        header_text = "Calculados"
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)  # Centraliza o texto
        header_label.setFont(QFont("Arial", 8, QFont.Bold))

        # Estiliza a borda para criar um efeito 3D
        header_label.setStyleSheet("""
            QLabel {
                background-color: #C0C0C0;  /* Cinza 3D */
                color: #000000;  /* Cor do texto */
                padding: 2px;
                border: 1px solid #A0A0A0;  /* Borda 3D mais clara */
                border-left-color: #E0E0E0;  /* Borda 3D mais clara à esquerda */
                border-top-color: #E0E0E0;  /* Borda 3D mais clara no topo */
                border-right-color: #808080; /* Borda 3D mais escura à direita */
                border-bottom-color: #808080; /* Borda 3D mais escura na parte inferior */
            }
        """)

        # Cria um item de lista para o cabeçalho e define seu widget
        header_item = QListWidgetItem(list_widget)
        header_item.setFlags(Qt.NoItemFlags)  # Desabilita a seleção do cabeçalho
        list_widget.addItem(header_item)
        list_widget.setItemWidget(header_item, header_label)
        header_item.setSizeHint(header_label.sizeHint())

        # Itera sobre as camadas do grupo e adiciona ao listWidget
        for tree_layer in group.findLayers():
            layer = tree_layer.layer()  # Obtém a camada associada ao QgsLayerTreeLayer
            if layer:  # Verifica se a camada é válida
                layer_name = layer.name()  # Usa o método name() do QgsMapLayer
                item = QListWidgetItem(layer_name)
                item.setData(Qt.UserRole, layer.id())
                list_widget.addItem(item)

        # Estilo para os itens da lista
        list_widget.setStyleSheet("""
            QListWidget::item:hover {
                background-color: #aaffff;  /* Azul claro no hover */
            }
            QListWidget::item:selected {
                background-color: #00aaff;  /* Azul claro para itens selecionados */
                color: black;
            }
            QListWidget::item:hover:selected {
                background-color: #00aaff;  /* Mantém a seleção ao passar o mouse sobre o item selecionado */
            }
            QListWidget::item {
                padding: 1px;
            }
        """)

    def load_calculados_group(self):
        # Obtém o grupo "Calculados" no projeto
        group = QgsProject.instance().layerTreeRoot().findGroup("Calculados")
        
        # Verifica se o grupo existe e se possui camadas
        if group and group.findLayers():
            # Atualiza o listWidgetRasters com as camadas do grupo
            self.update_list_view(group)
            self._log_message("Grupo 'Calculados' carregado com sucesso.", Qgis.Info)
        else:
            # Se o grupo não existir ou estiver vazio, limpa o listWidget
            self.clear_list_view()
            self._log_message("Grupo 'Calculados' não encontrado ou vazio.", Qgis.Warning)

    def init_combo_box_raster(self):
        # Obtém todas as camadas do projeto atual
        layers = QgsProject.instance().mapLayers().values()
        
        # Obtém camadas do grupo "Calculados"
        group = QgsProject.instance().layerTreeRoot().findGroup("Calculados")
        calculados_layers = set()
        if group:
            for tree_layer in group.findLayers():
                calculados_layers.add(tree_layer.layerId())

        # Filtra apenas camadas raster que não estão no grupo "Calculados"
        raster_layers = [layer for layer in layers if layer.type() == layer.RasterLayer and layer.id() not in calculados_layers]
        
        # Limpa os ComboBoxes antes de adicionar itens
        self.comboBoxRaster.clear()
        self.comboBoxRaster2.clear()  # Limpa o segundo ComboBox

        # Adiciona as camadas raster aos ComboBoxes, excluindo as do grupo "Calculados"
        for raster_layer in raster_layers:
            self.comboBoxRaster.addItem(raster_layer.name(), raster_layer.id())
            self.comboBoxRaster2.addItem(raster_layer.name(), raster_layer.id())  # Adiciona ao segundo ComboBox

        # Seleciona a primeira camada raster, se existir, para ambos os ComboBoxes
        if raster_layers:
            self.comboBoxRaster.setCurrentIndex(0)
            self.comboBoxRaster2.setCurrentIndex(1 if len(raster_layers) > 1 else 0)  # Evita selecionar a mesma camada, se houver mais de uma
            self.display_raster()  # Exibe no primeiro gráfico
            self.display_raster2()  # Exibe no segundo gráfico

    def sync_combo_boxes(self):
        # Obtém o ID das camadas selecionadas em cada comboBox
        selected_id_1 = self.comboBoxRaster.currentData()
        selected_id_2 = self.comboBoxRaster2.currentData()

        # Verifica se os IDs são iguais e faz ajustes
        if selected_id_1 == selected_id_2:
            # Verifica qual comboBox foi alterado
            sender_combo = self.sender()
            
            if sender_combo == self.comboBoxRaster:
                # Se o comboBoxRaster foi alterado, ajusta o comboBoxRaster2
                self.adjust_combo_box(self.comboBoxRaster2, selected_id_1)
            elif sender_combo == self.comboBoxRaster2:
                # Se o comboBoxRaster2 foi alterado, ajusta o comboBoxRaster
                self.adjust_combo_box(self.comboBoxRaster, selected_id_2)

    def adjust_combo_box(self, combo_box, excluded_id):
        """
        Ajusta o comboBox para selecionar um índice diferente do excluded_id.
        """
        count = combo_box.count()
        current_index = combo_box.currentIndex()

        # Encontrar um índice que não corresponda ao excluded_id
        for i in range(count):
            new_index = (current_index + 1 + i) % count
            if combo_box.itemData(new_index) != excluded_id:
                combo_box.setCurrentIndex(new_index)
                break

    def display_raster_statistics(self):
        # Obtém o item selecionado no listWidgetRasters
        selected_items = self.listWidgetRasters.selectedItems()

        if not selected_items:
            self.textEditInfo.setHtml("<p><b>Nenhuma camada selecionada.</b></p>")
            return

        # Obtém o ID da camada selecionada
        selected_item = selected_items[0]
        layer_id = selected_item.data(Qt.UserRole)
        layer = QgsProject.instance().mapLayer(layer_id)

        if not isinstance(layer, QgsRasterLayer):
            self.textEditInfo.setHtml("<p><b>Camada selecionada não é um raster válido.</b></p>")
            return

        # Obtenção das estatísticas básicas do raster
        stats = layer.dataProvider().bandStatistics(1, QgsRasterBandStats.All)
        extent = layer.extent()
        crs = layer.crs()

        # Obtém o nome completo do sistema de referência de coordenadas (SRC)
        crs_description = crs.description()

        # Formatação das informações para exibição com 3 casas decimais e indicações em negrito
        info_text = (
            f"<b>Estatísticas:</b><br><br>"  # Cabeçalho em negrito
            f"<b>Valor Mínimo:</b> {stats.minimumValue:.3f}<br>"
            f"<b>Valor Máximo:</b> {stats.maximumValue:.3f}<br>"
            f"<b>Total de Pixels:</b> {stats.elementCount:,}<br>"
            f"<b>Área:</b> {extent.width() * extent.height():.3f} m²<br>"
            f"<b>Resolução Espacial:</b> {layer.rasterUnitsPerPixelX():.1f} x {layer.rasterUnitsPerPixelY():.1f}<br>"
            f"<b>Extensão (Extent):</b><br>"
            f" - xmin: {extent.xMinimum():.3f}<br>"
            f" - ymin: {extent.yMinimum():.3f}<br>"
            f" - xmax: {extent.xMaximum():.3f}<br>"
            f" - ymax: {extent.yMaximum():.3f}<br>"
            f"<b>SRC da Camada:</b> {crs.authid()} - {crs_description}<br>"
        )

        # Define o textEditInfo como apenas leitura e exibe o texto em HTML
        self.textEditInfo.setReadOnly(True)
        self.textEditInfo.setHtml(info_text)

    def mostrar_mensagem(self, texto, tipo, duracao=2):
        """
        Exibe uma mensagem na barra de mensagens do QGIS, proporcionando feedback ao usuário baseado nas ações realizadas.
        As mensagens podem ser de erro ou de sucesso, com uma duração configurável e uma opção de abrir uma pasta.

        :param texto: Texto da mensagem a ser exibida.
        :param tipo: Tipo da mensagem ("Erro" ou "Sucesso") que determina a cor e o ícone da mensagem.
        :param duracao: Duração em segundos durante a qual a mensagem será exibida (padrão é 3 segundos).
        :param caminho_pasta: Caminho da pasta a ser aberta ao clicar no botão (padrão é None).
        :param caminho_arquivo: Caminho do arquivo a ser executado ao clicar no botão (padrão é None).
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
            
            # Adiciona a mensagem à barra com o nível informativo e a duração especificada
            bar.pushWidget(msg, level=Qgis.Info, duration=duracao)

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
        progressMessageBar = self.iface.messageBar().createMessage("Extraindo cotas do Raster")
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

    def add_result_raster_to_project(self, output_path, primitive_name, modified_name):
        file_info = QFileInfo(output_path)
        base_name = f"{primitive_name}_{modified_name}"

        # Verificar se já existe uma camada com este nome e adicionar um sufixo para torná-lo único
        base_name = self.get_unique_layer_name(base_name)

        result_layer = QgsRasterLayer(output_path, base_name)

        if not result_layer.isValid():
            self._log_message("Erro ao adicionar a camada resultante ao projeto.", Qgis.Critical)
            return None  # Retorna None em caso de erro

        # Verifica se o checkBoxCorteAterro está selecionado
        if self.checkBoxCorteAterro.isChecked():
            # Obtém as estatísticas da banda 1
            stats = result_layer.dataProvider().bandStatistics(1, QgsRasterBandStats.All)
            minValue = stats.minimumValue
            maxValue = stats.maximumValue

            # Cria os itens do color ramp shader
            colorRampItems = []

            # Valores menores que 0 - Vermelho
            if minValue < 0:
                colorRampItems.append(QgsColorRampShader.ColorRampItem(minValue, QColor('red'), f"{minValue:.3f} a -0.000001"))
                colorRampItems.append(QgsColorRampShader.ColorRampItem(-0.000001, QColor('red'), "< 0"))

            # Valor igual a 0 - Cinza
            if minValue <= 0 <= maxValue:
                colorRampItems.append(QgsColorRampShader.ColorRampItem(0, QColor('gray'), "0"))

            # Valores maiores que 0 - Azul
            if maxValue > 0:
                colorRampItems.append(QgsColorRampShader.ColorRampItem(0.000001, QColor('blue'), "> 0"))
                colorRampItems.append(QgsColorRampShader.ColorRampItem(maxValue, QColor('blue'), f"0.000001 a {maxValue:.3f}"))

            # Configura o shader
            colorRampShader = QgsColorRampShader()
            colorRampShader.setColorRampItemList(colorRampItems)
            colorRampShader.setColorRampType(QgsColorRampShader.Discrete)  # Interpolação Discreta

            # Configura o raster shader
            rasterShader = QgsRasterShader()
            rasterShader.setRasterShaderFunction(colorRampShader)

            # Cria o renderizador
            renderer = QgsSingleBandPseudoColorRenderer(result_layer.dataProvider(), 1, rasterShader)
            result_layer.setRenderer(renderer)

        # Adicionar a camada ao grupo "Calculados"
        self.add_layer_to_group(result_layer, "Calculados")

        # Retorna a camada raster criada
        return result_layer

    def get_unique_layer_name(self, base_name):
        """
        Gera um nome de camada único, adicionando um sufixo numérico, se necessário.
        """
        counter = 1
        unique_name = base_name

        while QgsProject.instance().mapLayersByName(unique_name):
            unique_name = f"{base_name}_{counter}"
            counter += 1

        return unique_name

    def calculate_raster_difference(self):
        # Obtém os IDs das camadas raster selecionadas
        raster_id_primitivo = self.comboBoxRaster.currentData()
        raster_id_modificado = self.comboBoxRaster2.currentData()

        # Busca as camadas raster pelos IDs
        raster_primitivo = QgsProject.instance().mapLayer(raster_id_primitivo)
        raster_modificado = QgsProject.instance().mapLayer(raster_id_modificado)

        # Verifica se as camadas existem e são do tipo QgsRasterLayer
        if not (isinstance(raster_primitivo, QgsRasterLayer) and isinstance(raster_modificado, QgsRasterLayer)):
            self._log_message("Erro: selecione duas camadas raster válidas.", Qgis.Critical)
            return

        # Verifica se ambos os rasters possuem o mesmo CRS (Sistema de Referência de Coordenadas)
        if raster_primitivo.crs() != raster_modificado.crs():
            self._log_message("Erro: As camadas raster devem ter o mesmo sistema de referência de coordenadas (CRS).", Qgis.Critical)
            return

        # Definir a extensão de interseção entre os dois rasters
        intersection_extent = raster_primitivo.extent().intersect(raster_modificado.extent())

        if intersection_extent.isEmpty():
            self._log_message("Erro: As camadas raster não possuem sobreposição.", Qgis.Critical)
            return

        # Calcular a resolução com base no raster primitivo
        resolution_x = raster_primitivo.rasterUnitsPerPixelX()
        resolution_y = raster_primitivo.rasterUnitsPerPixelY()

        # Calcular o número de colunas e linhas para a extensão de interseção
        width = int(intersection_extent.width() / resolution_x)
        height = int(intersection_extent.height() / resolution_y)

        # Definir o caminho de saída para o raster resultante
        temp_fd, temp_path = tempfile.mkstemp(suffix='.tif')
        os.close(temp_fd)  # Fechar o arquivo temporário

        # Criar as entradas para o QgsRasterCalculator
        entries = []

        entry_primitivo = QgsRasterCalculatorEntry()
        entry_primitivo.raster = raster_primitivo
        entry_primitivo.bandNumber = 1  # Usar a banda 1
        entry_primitivo.ref = 'primitivo@1'
        entries.append(entry_primitivo)

        entry_modificado = QgsRasterCalculatorEntry()
        entry_modificado.raster = raster_modificado
        entry_modificado.bandNumber = 1  # Usar a banda 1
        entry_modificado.ref = 'modificado@1'
        entries.append(entry_modificado)

        # Expressão de cálculo: -(primitivo - modificado)
        expression = '-1 * (primitivo@1 - modificado@1)'

        # Número total de etapas para o progresso
        total_steps = width * height

        # Inicializa a barra de progresso
        progress_bar, progress_message = self.iniciar_progress_bar(total_steps)

        # Criar o objeto QgsRasterCalculator para realizar a operação
        calculator = QgsRasterCalculator(
            expression,
            temp_path,
            'GTiff',
            intersection_extent,
            width,
            height,
            entries
        )

        # Captura o tempo inicial
        start_time = time.time()

        # Inicia o cálculo e atualiza a barra de progresso a cada linha processada
        result = 0
        for i in range(height):
            progress_bar.setValue(i * width)  # Atualiza a barra de progresso
            QCoreApplication.processEvents()  # Permite a atualização da interface
            # Simula o cálculo parcial para cada linha do raster (exemplo fictício)
            # Este é apenas um exemplo e deve ser substituído pelo cálculo real
            if result != 0:
                self.mostrar_mensagem(f"Erro ao calcular a diferença dos rasters: {result}", "Erro", 5)
                break

        # Finaliza o cálculo do raster
        result = calculator.processCalculation()

        # Calcula o tempo total gasto
        total_time = time.time() - start_time

        # Verifica se houve sucesso no cálculo
        if result != 0:
            self.mostrar_mensagem(f"Erro ao calcular a diferença dos rasters: {result}", "Erro", 5)
            return

        # Completa a barra de progresso
        progress_bar.setValue(total_steps)
        self.iface.messageBar().popWidget(progress_message)  # Remove a mensagem de progresso

        # Adicionar o raster resultante ao projeto e obter a camada resultante
        result_layer = self.add_result_raster_to_project(temp_path, raster_primitivo.name(), raster_modificado.name())

        # Se o checkBoxPoligono estiver selecionado e a camada resultante for válida, gera a camada de polígonos
        if self.checkBoxPoligono.isChecked() and result_layer:
            self.gerar_camadas_poligono_custom(result_layer)

        # Exibe mensagem de sucesso com o tempo total gasto
        self.mostrar_mensagem(f"Sucesso: raster calculado em {total_time:.2f} segundos.", "Sucesso", 5)

    def gerar_camadas_poligono_custom(self, raster_layer):
        """
        Gera uma camada de polígonos a partir de um raster, onde cada pixel se torna um polígono.
        Adiciona um campo de volume calculado como o valor do pixel multiplicado pela área do pixel.

        Parâmetros:
        - raster_layer: Camada raster de entrada.
        """

        # Captura o tempo inicial
        start_time = time.time()

        # Define o caminho temporário para a camada de polígonos
        temp_fd, temp_polygon_path = tempfile.mkstemp(suffix='.shp')
        os.close(temp_fd)  # Fecha o arquivo temporário

        # Definir o provedor e a extensão do raster
        provider = raster_layer.dataProvider()
        extent = provider.extent()
        pixelSizeX = raster_layer.rasterUnitsPerPixelX()
        pixelSizeY = raster_layer.rasterUnitsPerPixelY()
        width = provider.xSize()
        height = provider.ySize()

        # Calcula a área de cada pixel (polígono)
        area_pixel = pixelSizeX * pixelSizeY

        # Número total de pixels a serem processados
        total_pixels = width * height

        # Inicializa a barra de progresso
        progress_bar, progress_message = self.iniciar_progress_bar(total_pixels)

        # Cria uma nova camada de polígonos temporária
        campos = QgsFields()
        campos.append(QgsField("ID", QVariant.Int))
        campos.append(QgsField("Value", QVariant.Double))
        campos.append(QgsField("Volume", QVariant.Double))

        crs = raster_layer.crs().toWkt()
        camada_poligono = QgsVectorLayer(f"Polygon?crs={crs}", "Polígonos do Raster", "memory")
        pr = camada_poligono.dataProvider()
        pr.addAttributes(campos)
        camada_poligono.updateFields()

        # Inicializa um ID para as features
        ID = 0
        valores_pixel = []  # Lista para armazenar valores de pixels

        # Itera sobre cada pixel no raster para criar polígonos
        for row in range(height):
            for col in range(width):
                ID += 1

                # Calcula a coordenada do centro do pixel
                x = extent.xMinimum() + col * pixelSizeX + pixelSizeX / 2
                y = extent.yMaximum() - row * pixelSizeY - pixelSizeY / 2
                ponto = QgsPointXY(x, y)
                valor_pixel = provider.identify(ponto, QgsRaster.IdentifyFormatValue).results().get(1)

                if valor_pixel is not None:  # Ignorar pixels NoData
                    # Definir coordenadas do retângulo do pixel
                    xMin = extent.xMinimum() + col * pixelSizeX
                    xMax = extent.xMinimum() + (col + 1) * pixelSizeX
                    yMax = extent.yMaximum() - row * pixelSizeY
                    yMin = extent.yMaximum() - (row + 1) * pixelSizeY

                    # Criar um polígono a partir do retângulo do pixel
                    poligono = QgsGeometry.fromRect(QgsRectangle(xMin, yMin, xMax, yMax))

                    # Calcular o volume (valor do pixel * área do pixel)
                    volume = valor_pixel * area_pixel

                    # Criar uma nova feature com os atributos e a geometria
                    feature = QgsFeature()
                    feature.setGeometry(poligono)
                    feature.setAttributes([ID, valor_pixel, volume])
                    pr.addFeature(feature)

                    # Adicionar o valor do pixel à lista para estatísticas (opcional)
                    valores_pixel.append(valor_pixel)

                # Atualiza a barra de progresso a cada pixel processado
                progress_bar.setValue(ID)
                QCoreApplication.processEvents()  # Permite a atualização da interface

        # Atualizar a camada de polígonos com as novas features
        camada_poligono.updateExtents()
        QgsProject.instance().addMapLayer(camada_poligono)

        # Aplica o estilo de coloração à camada de polígonos
        self.aplicar_estilo_atribuido(camada_poligono)

        # Finaliza a barra de progresso
        progress_bar.setValue(total_pixels)
        self.iface.messageBar().popWidget(progress_message)  # Remove a mensagem de progresso

        # Calcula o tempo total gasto
        total_time = time.time() - start_time
        
        self.mostrar_mensagem(f"Camada de polígonos gerada com sucesso em {total_time:.2f} segundos!", "Sucesso", 3)

    def aplicar_estilo_atribuido(self, camada_poligono):
        """
        Aplica um estilo de coloração atribuído a uma camada de polígonos baseado nos valores dos pixels.

        Passos detalhados:
        1. Cria uma lista para armazenar os intervalos de renderização.
        2. Cria símbolos de preenchimento para pixels positivos, negativos e nulos.
        3. Adiciona intervalos de renderização para cada tipo de símbolo.
        4. Cria um renderizador graduado com base nos intervalos de valores.
        5. Aplica o renderizador à camada de polígonos.

        Parâmetros:
        - camada_poligono: Camada de polígonos a ser estilizada.

        Retorna:
        - None
        """
        ranges = []  # Cria uma lista para armazenar os intervalos de renderização

        # Cria símbolos de preenchimento para pixels positivos, negativos e nulos
        symbol_positive = QgsFillSymbol.createSimple({'color': 'blue', 'outline_color': 'blue'})  # Azul para pixels positivos
        symbol_negative = QgsFillSymbol.createSimple({'color': 'red', 'outline_color': 'red'})  # Vermelho para pixels negativos
        symbol_zero = QgsFillSymbol.createSimple({'color': 'gray', 'outline_color': 'gray'})  # Cinza para pixels nulos

        # Adiciona intervalos de renderização para cada tipo de símbolo
        ranges.append(QgsRendererRange(0.0001, float('inf'), symbol_positive, "> 0"))  # Intervalo para pixels positivos
        ranges.append(QgsRendererRange(float('-inf'), -0.0001, symbol_negative, "< 0"))  # Intervalo para pixels negativos
        ranges.append(QgsRendererRange(-0.0001, 0.0001, symbol_zero, "= 0"))  # Intervalo para pixels nulos

        renderer = QgsGraduatedSymbolRenderer('Value', ranges)  # Cria um renderizador graduado com base nos intervalos de valores
        camada_poligono.setRenderer(renderer)  # Aplica o renderizador à camada de polígonos

    def calculate_volume(self):
        """
        Calcula os volumes de corte e aterro com base nos valores dos pixels e suas áreas
        e exibe os resultados na tableViewVolumes.
        """
        # Obtém o item selecionado no listWidgetRasters
        selected_items = self.listWidgetRasters.selectedItems()

        if not selected_items:
            self._log_message("Nenhuma camada selecionada.", Qgis.Warning)
            return

        # Obtém o ID da camada selecionada
        selected_item = selected_items[0]
        layer_id = selected_item.data(Qt.UserRole)
        raster_layer = QgsProject.instance().mapLayer(layer_id)

        if not isinstance(raster_layer, QgsRasterLayer):
            self._log_message("Camada selecionada não é um raster válido.", Qgis.Critical)
            return

        # Nome da camada raster
        layer_name = raster_layer.name()

        # Definir fator de empolamento (exemplo: 1.3 para 30% de empolamento)
        fator_empolamento = 1.3

        # Obter o provedor de dados e a extensão do raster
        provider = raster_layer.dataProvider()
        extent = raster_layer.extent()
        pixel_size_x = raster_layer.rasterUnitsPerPixelX()
        pixel_size_y = raster_layer.rasterUnitsPerPixelY()

        # Inicializar variáveis para cálculo de volumes
        total_corte = 0.0
        total_aterro = 0.0

        # Calcular volume para cada pixel
        for row in range(provider.ySize()):
            for col in range(provider.xSize()):
                # Coordenada do centro do pixel
                x = extent.xMinimum() + col * pixel_size_x + pixel_size_x / 2
                y = extent.yMaximum() - row * pixel_size_y - pixel_size_y / 2
                point = QgsPointXY(x, y)
                pixel_value = provider.identify(point, QgsRaster.IdentifyFormatValue).results().get(1)

                if pixel_value is not None:
                    # Calcular área do pixel (considerando retângulo)
                    area = pixel_size_x * pixel_size_y

                    # Calcular volume do pixel
                    volume = pixel_value * area

                    # Acumular volumes de corte e aterro
                    if volume < 0:
                        total_corte += volume
                    elif volume > 0:
                        total_aterro += volume

        # Calcular volumes empolados
        total_corte_empolado = total_corte * fator_empolamento
        total_aterro_empolado = total_aterro * fator_empolamento

        # Preencher o modelo da tableViewVolumes com as informações atualizadas
        self.fill_table_view_volumes(layer_name, total_corte, total_aterro, total_corte_empolado, total_aterro_empolado)

    def fill_table_view_volumes(self, layer_name, total_corte, total_aterro, total_corte_empolado, total_aterro_empolado):
        """
        Preenche a tableViewVolumes com os volumes de corte e aterro, incluindo o volume empolado.
        Adiciona os dados da nova camada abaixo das camadas existentes.
        """
        # Obter o modelo existente da tableView
        model = self.tableViewVolumes.model()

        # Se não houver modelo, crie um novo
        if model is None:
            model = QStandardItemModel()
            # Definir cabeçalhos das colunas
            model.setHorizontalHeaderLabels(["Nome da Camada", "Descrição", "Volume (m³)", "Volume Empolado (m³)"])
            self.tableViewVolumes.setModel(model)

        # Índice da primeira linha da nova camada
        start_row = model.rowCount()

        # Adicionar dados de corte e aterro ao modelo
        corte_item = QStandardItem("Corte")
        aterro_item = QStandardItem("Aterro")

        # Formatação dos números sem separadores de milhar e com 3 casas decimais
        volume_corte = QStandardItem(f"{abs(total_corte):.3f}")  # Removido o separador de milhar
        volume_aterro = QStandardItem(f"{total_aterro:.3f}")  # Removido o separador de milhar
        volume_corte_empolado = QStandardItem(f"{abs(total_corte_empolado):.3f}")  # Removido o separador de milhar
        volume_aterro_empolado = QStandardItem(f"{total_aterro_empolado:.3f}")  # Removido o separador de milhar

        # Nome da camada
        name_item = QStandardItem(layer_name)

        # Adicionar linha com o nome da camada apenas na primeira linha
        model.appendRow([name_item, corte_item, volume_corte, volume_corte_empolado])
        model.appendRow([QStandardItem(""), aterro_item, volume_aterro, volume_aterro_empolado])  # Nome ausente nas linhas subsequentes

        # Mesclar a célula "Nome da Camada" na tabela
        self.tableViewVolumes.setSpan(start_row, 0, 2, 1)  # Mescla duas linhas da coluna "Nome"

        # Definir o modelo como não editável
        for row in range(model.rowCount()):
            for column in range(model.columnCount()):
                item = model.item(row, column)
                if item is not None:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        # Configurar o estilo para as células
        self.apply_table_style()

        # Configurar o modelo na tableViewVolumes
        self.tableViewVolumes.resizeColumnsToContents()  # Ajusta o tamanho das colunas ao conteúdo

        # Verifica se há dados na tabela após preenchê-la
        self.verificar_dados_excel()

    def apply_table_style(self):
        """
        Aplica o estilo de borda ao tableViewVolumes.
        """
        self.tableViewVolumes.setAlternatingRowColors(True)
        self.tableViewVolumes.setStyleSheet("""
            QTableView {
                gridline-color: black;
                border: 1px solid gray;
                background-color: #ffffff;
                alternate-background-color: #f2f2f2;  /* Cor para as linhas alternadas */
            }
            QHeaderView::section {
                background-color: #d3d3d3;
                font-weight: bold;
            }
        """)

    def reset_table_view(self):
        """
        Reseta os dados do tableViewVolumes, limpando a tabela e restaurando seu estado inicial.
        """
        # Limpa o modelo associado ao tableViewVolumes
        self.tableViewVolumes.setModel(None)

        # Aplica o estilo novamente após resetar
        self.apply_table_style()

        # Verifica se há dados na tabela após resetá-la
        self.verificar_dados_excel()

    def setup_table_view(self):
        # Aplica o DeleteButtonDelegate na primeira coluna (coluna de Nome, que é mesclada)
        delegate = DeleteButtonDelegate(self.tableViewVolumes)
        self.tableViewVolumes.setItemDelegateForColumn(0, delegate)

        # Configura a tabela para não ser editável
        self.tableViewVolumes.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Aplica estilo personalizado à tabela
        self.apply_table_style()

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

    def exportar_tabela_para_excel(self):
        """
        Exporta o conteúdo do tableViewVolumes para um arquivo Excel, garantindo que números sejam exportados
        sem formatação de divisão de milhar e como números.
        Se o checkBoxSalvar estiver selecionado, abre a caixa de diálogo para escolher o local de salvamento.
        Caso contrário, salva em um local temporário e abre o Excel automaticamente.
        """
        # Nome e tipo de arquivo padrão
        nome_padrao = "volumes_exportados.xlsx"
        tipo_arquivo = "Excel Files (*.xlsx)"

        if self.checkBoxSalvar.isChecked():
            # Abre a caixa de diálogo para escolher o local de salvamento
            fileName = self.escolher_local_para_salvar(nome_padrao, tipo_arquivo)
        else:
            # Cria um caminho temporário para salvar o arquivo Excel
            temp_fd, fileName = tempfile.mkstemp(suffix=".xlsx")
            os.close(temp_fd)  # Fecha o arquivo temporário

        if fileName:
            # Obtém o modelo da tabela do tableViewVolumes
            model = self.tableViewVolumes.model()

            # Cria uma lista para armazenar os dados
            dados_tabela = []

            # Percorre todas as linhas e colunas do modelo
            for row in range(model.rowCount()):
                linha_dados = []
                for col in range(model.columnCount()):
                    # Obtém o texto exibido na célula
                    valor_celula = model.index(row, col).data()
                    
                    # Tenta converter para número se possível
                    try:
                        valor_celula = float(valor_celula)
                    except (ValueError, TypeError):
                        pass  # Mantém o valor como string se não for um número

                    linha_dados.append(valor_celula)
                dados_tabela.append(linha_dados)

            # Cria um DataFrame a partir dos dados
            df = pd.DataFrame(dados_tabela, columns=["Nome da Camada", "Descrição", "Volume (m³)", "Volume Empolado (m³)"])

            # Salva o DataFrame no arquivo Excel
            try:
                df.to_excel(fileName, index=False)
                if self.checkBoxSalvar.isChecked():
                    # Mensagem de sucesso se o usuário escolheu salvar
                    self.mostrar_mensagem(f"Exportação concluída com sucesso: {fileName}", "Sucesso")
                else:
                    # Abre o Excel com o arquivo temporário
                    os.startfile(fileName)  # Abre o arquivo no Excel (Windows)
                    self.mostrar_mensagem("A tabela foi exportada e aberta no Excel temporariamente.", "Sucesso")
            except Exception as e:
                self.mostrar_mensagem(f"Erro ao salvar o arquivo Excel: {str(e)}", "Erro")

    def verificar_selecao_volume(self):
        """
        Verifica se há uma camada selecionada no listWidgetRasters e ativa/desativa o botão pushButtonVolume.
        """
        selected_items = self.listWidgetRasters.selectedItems()
        if selected_items:
            self.pushButtonVolume.setEnabled(True)
        else:
            self.pushButtonVolume.setEnabled(False)

    def verificar_dados_excel(self):
        """
        Verifica se há dados no tableViewVolumes e ativa/desativa o pushButtonExcel.
        """
        model = self.tableViewVolumes.model()
        if model is None or model.rowCount() == 0:
            self.pushButtonExcel.setEnabled(False)
        else:
            self.pushButtonExcel.setEnabled(True)

    def verificar_condicoes_calculo(self):
        """
        Verifica as condições para ativar/desativar o botão pushButtonCalcular.
        """
        # Verifica se há camadas selecionadas em ambos os comboBoxes
        raster_id_1 = self.comboBoxRaster.currentData()
        raster_id_2 = self.comboBoxRaster2.currentData()

        if not raster_id_1 or not raster_id_2:
            # Desativa o botão se alguma camada não estiver selecionada
            self.pushButtonCalcular.setEnabled(False)
            return

        # Obtém as camadas raster dos IDs
        raster_layer_1 = QgsProject.instance().mapLayer(raster_id_1)
        raster_layer_2 = QgsProject.instance().mapLayer(raster_id_2)

        # Verifica se as camadas são do tipo raster
        if not isinstance(raster_layer_1, QgsRasterLayer) or not isinstance(raster_layer_2, QgsRasterLayer):
            self.pushButtonCalcular.setEnabled(False)
            return

        # Verifica se ambas as camadas possuem o mesmo sistema de referência (CRS)
        crs_1 = raster_layer_1.crs()
        crs_2 = raster_layer_2.crs()
        if crs_1 != crs_2:
            self.pushButtonCalcular.setEnabled(False)
            return

        # Verifica se ambas as camadas estão em coordenadas geográficas
        if crs_1.isGeographic() or crs_2.isGeographic():
            self.pushButtonCalcular.setEnabled(False)
            return

        # Verifica se há interseção entre as extensões das camadas
        extent_1 = raster_layer_1.extent()
        extent_2 = raster_layer_2.extent()
        intersection_extent = extent_1.intersect(extent_2)
        if intersection_extent.isEmpty():
            self.pushButtonCalcular.setEnabled(False)
            return

        # Verifica se as duas comboBoxes têm a mesma camada selecionada e só há uma camada raster disponível
        total_raster_layers = len([layer for layer in QgsProject.instance().mapLayers().values() if isinstance(layer, QgsRasterLayer)])
        if raster_id_1 == raster_id_2 and total_raster_layers == 1:
            self.pushButtonCalcular.setEnabled(False)
            return

        # Se todas as condições forem atendidas, ativa o botão
        self.pushButtonCalcular.setEnabled(True)

class DeleteButtonDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(DeleteButtonDelegate, self).__init__(parent)
        self.parent = parent

    def paint(self, painter, option, index):
        super(DeleteButtonDelegate, self).paint(painter, option, index)

        # Renderizar o ícone de deletar somente na célula que contém o nome da camada
        if index.isValid() and index.column() == 0:
            cell_data = index.data()
            if cell_data:  # Se a célula não estiver vazia
                rect = option.rect
                icon_rect = QRect(rect.left() + 3, rect.top() + 3, 10, 10)  # Ajuste do tamanho e posição do ícone "x"

                # Desenhar ícone estilizado com quadrado de bordas arredondadas
                painter.save()
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setPen(QPen(QColor(0, 0, 255), 2))  # Cor da borda do quadrado
                painter.setBrush(QBrush(QColor(255, 0, 0, 200)))  # Fundo vermelho claro
                radius = 2  # Raio das bordas arredondadas
                painter.drawRoundedRect(icon_rect, radius, radius)  # Desenha o quadrado com bordas arredondadas

                # Desenha o "x" dentro do quadrado
                painter.setPen(QPen(QColor(255, 255, 255), 2))  # Cor e espessura do "x"
                # Desenha o "x" simétrico dentro do quadrado
                painter.drawLine(icon_rect.topLeft() + QPoint(2, 2), icon_rect.bottomRight() - QPoint(2, 2))
                painter.drawLine(icon_rect.topRight() + QPoint(-2, 2), icon_rect.bottomLeft() + QPoint(2, -2))
                painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease:
            rect = option.rect
            icon_rect = QRect(rect.left() + 3, rect.top() + 3, 10, 10)  # Ajuste do tamanho e posição do ícone "x"
            if icon_rect.contains(event.pos()):
                # Remove as duas linhas correspondentes à camada
                row_to_remove = index.row()
                # Remove as duas linhas a partir de row_to_remove
                model.removeRows(row_to_remove, 2)  # Remove 2 linhas começando de row_to_remove
                return True
        return super(DeleteButtonDelegate, self).editorEvent(event, model, option, index)

class ListDeleteButtonDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(ListDeleteButtonDelegate, self).__init__(parent)
        self.parent = parent

    def paint(self, painter, option, index):
        if index.isValid():
            # Evita desenhar o botão no item de cabeçalho
            if index.row() == 0:
                return super(ListDeleteButtonDelegate, self).paint(painter, option, index)

            # Determinar a cor de fundo com base no estado
            if option.state & QStyle.State_Selected:
                background_color = QColor("#00aaff")  # Azul normal para item selecionado
            elif option.state & QStyle.State_MouseOver:
                background_color = QColor("#aaffff")  # Azul claro quando o mouse está sobre o item
            else:
                background_color = option.palette.base().color()

            painter.fillRect(option.rect, background_color)

            # Calcula as posições
            rect = option.rect
            icon_size = 11
            icon_margin = 4
            icon_rect = QRect(
                rect.left() + icon_margin,
                rect.top() + (rect.height() - icon_size) // 2,
                icon_size,
                icon_size
            )
            text_rect = QRect(
                icon_rect.right() + icon_margin,
                rect.top(),
                rect.width() - icon_size - 3 * icon_margin,
                rect.height()
            )

            # Desenha o quadradinho com borda arredondada para exclusão
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor(0, 0, 255), 2))  # Cor da borda do quadrado
            painter.setBrush(QBrush(QColor(255, 0, 0, 200)))  # Fundo vermelho claro
            radius = 2  # Raio das bordas arredondadas
            painter.drawRoundedRect(icon_rect, radius, radius)  # Desenha o quadrado com bordas arredondadas

            # Desenha o "x" dentro do quadrado
            painter.setPen(QPen(QColor(255, 255, 255), 2))  # Cor e espessura do "x"
            painter.drawLine(icon_rect.topLeft() + QPoint(3, 3), icon_rect.bottomRight() - QPoint(3, 3))
            painter.drawLine(icon_rect.topRight() + QPoint(-3, 3), icon_rect.bottomLeft() + QPoint(3, -3))
            painter.restore()

            # Desenha o texto
            painter.save()
            # Definir a cor do texto com base no fundo para melhor contraste
            if option.state & QStyle.State_Selected:
                text_color = QColor('black')
            else:
                text_color = option.palette.text().color()

            painter.setPen(text_color)
            font = painter.font()
            font.setPointSize(10)  # Ajusta o tamanho da fonte se necessário
            painter.setFont(font)
            text = index.data(Qt.DisplayRole)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.TextSingleLine, text)
            painter.restore()
        else:
            super(ListDeleteButtonDelegate, self).paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        # Evita interações com o item de cabeçalho
        if index.row() == 0:
            return False

        if event.type() == QEvent.MouseButtonRelease:
            # Calcula as posições
            rect = option.rect
            icon_size = 12
            icon_margin = 4
            icon_rect = QRect(
                rect.left() + icon_margin,
                rect.top() + (rect.height() - icon_size) // 2,
                icon_size,
                icon_size
            )
            if icon_rect.contains(event.pos()):
                # Remove a camada correspondente do QGIS
                layer_id = index.data(Qt.UserRole)
                QgsProject.instance().removeMapLayer(layer_id)
                return True

        return super(ListDeleteButtonDelegate, self).editorEvent(event, model, option, index)





