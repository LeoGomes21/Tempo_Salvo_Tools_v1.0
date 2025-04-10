from qgis.PyQt.QtWidgets import QDockWidget, QTableWidgetItem, QTableWidget, QAbstractItemView, QInputDialog, QDialog, QVBoxLayout, QListWidgetItem, QProgressBar, QApplication, QWidget, QGroupBox, QVBoxLayout, QStyledItemDelegate, QStyle, QFileDialog, QPushButton
from qgis.core import QgsProject, QgsRasterLayer, QgsMessageLog, Qgis, QgsVectorLayer, QgsWkbTypes, QgsFeature, QgsGeometry, QgsPointXY, QgsField, QgsLayerTreeLayer, QgsFields, QgsLayerTreeGroup, QgsRaster, QgsPalLayerSettings, QgsProperty, QgsVectorLayerSimpleLabeling, QgsSymbolLayer, QgsTextFormat, QgsTextBufferSettings, QgsUnitTypes, QgsMapLayer
from qgis.PyQt.QtCore import Qt, QVariant, QRect, QPoint, QPointF, QEvent, QItemSelection, QItemSelectionModel, QSettings
from PyQt5.QtGui import QPainter, QStandardItemModel, QStandardItem, QBrush, QColor, QFont, QPen
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.patches as mpatches
from matplotlib.patches import Circle
from matplotlib.lines import Line2D
from pyqtgraph import PlotWidget
import matplotlib.pyplot as plt
from qgis.utils import iface
import matplotlib.patches
from qgis.PyQt import uic
import pyqtgraph as pg
import numpy as np
import ezdxf
import time
import math
import os
import re

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'GraficoEstruturaSolar.ui'))

class EstruturasManager(QDockWidget, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(EstruturasManager, self).__init__(parent)
        # Configura a interface do usuário a partir do Designer.
        self.setupUi(self)

        # Altera o título da janela
        self.setWindowTitle("Gráficos de Estruturas Solar")

        # Armazena a referência da interface QGIS
        self.iface = iface

        # Adiciona o dock widget à interface QGIS na parte inferior
        iface.addDockWidget(Qt.BottomDockWidgetArea, self)

        # Atributos de controle para seleção bidirecional
        self.selected_layer = None     # Armazena a camada atualmente exibida na tabela
        self.feature_ids = []          # Lista dos IDs das feições (para indexar as linhas da tabela)

        # Inicializa a variável para armazenar a camada atualmente selecionada
        self.current_estruturas_layer = None  

        # Configura o comportamento de seleção da tabela
        self.tableWidget_Dados1.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableWidget_Dados1.setSelectionMode(QAbstractItemView.MultiSelection)

        # Inicializa o ComboBox de Raster e Camadas
        self.init_combo_box_raster()
        self.init_combo_box_pontos()

        # Se já existe alguma camada de pontos, carrega a tabela de imediato
        if self.comboBoxPontos.count() > 0:
            self.load_table_widget_dados1()

        # Configura o gráfico ao iniciar
        self.setup_graph()

        # Configurações do listWidget_Lista
        self.listWidget_Lista.setItemDelegate(ListDeleteButtonDelegate(self.listWidget_Lista))
        self.listWidget_Lista.setMouseTracking(True)
        self.listWidget_Lista.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.listWidget_Lista.setSelectionMode(QAbstractItemView.SingleSelection)

        # current_dir é criar_vetor/codigos
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # plugin_dir agora será criar_vetor
        self.plugin_dir = os.path.dirname(current_dir)

        # Chama a função uma vez para garantir que o estado inicial seja atualizado corretamente
        self.atualizar_estado_botoes_calcular()

        # Chama a função uma vez para garantir que o estado inicial seja atualizado corretamente
        self.atualizar_estado_botao()

        self.support_layers = []  # ou como for definido
        # Certifique-se de criar o container e o dicionário de widgets, se necessário:
        self.dados_container = QWidget()
        self.dados_layout = QVBoxLayout(self.dados_container)
        self.scrollAreaDADOS.setWidget(self.dados_container)
        self.scrollAreaDADOS.setWidgetResizable(True)
        self.support_widgets = {}  # Chave: layer.id(), Valor: widget (group box)

        self.update_horizontalScrollBarSelec() #VERIFICAR A NECESSIDADE
        self.update_pushButtonSeq_state(self.spinBoxSelec.value())

        self.style_horizontal_scrollbar()  # Aplica o estilo

        # Conecta os sinais aos slots
        self.connect_signals()

    def connect_signals(self):
        
        # Quando camadas são adicionadas
        QgsProject.instance().layersAdded.connect(self.on_layers_added)
        # Quando camadas são removidas
        QgsProject.instance().layersRemoved.connect(self.on_layers_removed)

        # Conecta o sinal de alteração de nome
        for layer in QgsProject.instance().mapLayers().values():
            layer.nameChanged.connect(self.on_layer_name_changed)

        # Conecta o sinal de mudança de seleção no comboBoxPontos
        self.comboBoxPontos.currentIndexChanged.connect(self.load_table_widget_dados1)

        # Conecta a mudança de seleção na tabela
        self.tableWidget_Dados1.itemSelectionChanged.connect(self.table_selection_changed)

        self.pushButtonCalcular.clicked.connect(self.calcular)

        self.listWidget_Lista.itemSelectionChanged.connect(self.on_listwidget_selection_changed)
        self.doubleSpinBox_1.valueChanged.connect(self.recalc_current_layer)
        self.doubleSpinBox_2.valueChanged.connect(self.recalc_current_layer)

        self.listWidget_Lista.setItemDelegate(ListDeleteButtonDelegate(self.listWidget_Lista))

        self.pushButtonMat.clicked.connect(self.plot_layers)

        # Conectar o sinal selectionChanged da selectionModel do tableWidget_Dados1
        self.tableWidget_Dados1.selectionModel().selectionChanged.connect(
            lambda selected, deselected: self.atualizar_estado_botoes_calcular())

        # Sempre verificar o estado do botão quando houver mudanças
        self.listWidget_Lista.itemSelectionChanged.connect(self.atualizar_estado_botao)
        self.comboBoxRaster.currentIndexChanged.connect(self.atualizar_estado_botao)

        # Após conectar os demais sinais, adicione:
        self.tableWidget_Dados1.selectionModel().selectionChanged.connect(lambda sel, des: self.update_spinBoxSelec())

        self.spinBoxSelec.valueChanged.connect(self.on_spinBoxSelec_value_changed)

        # Conecta o botão comboBoxPontos a uma função:
        self.comboBoxPontos.currentIndexChanged.connect(self.load_table_widget_dados1)

        # Conecta o botão pushButtonSeq a uma função:
        self.pushButtonSeq.clicked.connect(self.on_pushButtonSeq_clicked)

        self.spinBoxSelec.valueChanged.connect(self.update_pushButtonSeq_state)

        self.horizontalScrollBarSelec.valueChanged.connect(self.on_horizontalScrollBarSelec_value_changed)

        # Botão Calcular Tudo
        self.pushButtonCalculaTudo.clicked.connect(self.calcular_tudo)

        # Conectar o botão pushButtonExportarDXF
        self.pushButtonExportarDXF.clicked.connect(self.pushButtonExportarDXF_clicked)

        # detecte a remoção e adição de Camadas do Grupo "Estruturas"
        QgsProject.instance().layersAdded.connect(lambda layers: self.atualizar_estado_pushButtonExportarDXF())
        QgsProject.instance().layersRemoved.connect(lambda layer_ids: self.atualizar_estado_pushButtonExportarDXF())

        # Fecha o diálogo
        self.pushButtonFecharD.clicked.connect(self.close)

    def showEvent(self, event):
        """
        Sobrescreve o evento de exibição do diálogo para resetar os Widgets.
        """
        super(EstruturasManager, self).showEvent(event)

        # Reseta o gráfico sempre que o diálogo for exibido
        self.reset_graph()

        # Reseta o tableView_2
        self.tableView_2.setModel(None)

        # Reseta o listWidget_inc
        self.listWidget_inc.clear()

        # Se houver pelo menos uma camada de pontos no comboBox, já carregar a tabela
        if self.comboBoxPontos.count() > 0:
            # Opcionalmente, forçar seleção do primeiro índice:
            # self.comboBoxPontos.setCurrentIndex(0)
            self.load_table_widget_dados1()
        else:
            # Se não há camadas, limpa a tabela
            self.tableWidget_Dados1.clear()
            self.tableWidget_Dados1.setRowCount(0)
            self.tableWidget_Dados1.setColumnCount(0)

        # Atualiza o listWidget com as camadas do grupo 'Estruturas'
        self.update_list_widget_estruturas()
        
        # Atualiza o botão pushButtonExportarDXF 
        self.atualizar_estado_pushButtonExportarDXF()

    def style_horizontal_scrollbar(self):
        """
        Aplica um estilo moderno e com efeito 3D ao horizontalScrollBarSelec.
        Agora um pouco mais fino e ajustado.
        """
        style = """
        QScrollBar:horizontal {
            border: 1px solid #999;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #f2f2f2, stop:1 #e6e6e6);
            height: 14px; /* 🔹 Altura reduzida para ficar mais fino */
            margin: 0px 18px 0px 18px; /* Ajuste para os botões laterais */
            border-radius: 3px;
        }

        /* 'Handle' (pegador) com efeito 3D e borda arredondada */
        QScrollBar::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #88b7f0, stop:1 #568dd6);
            border: 1px solid #666;
            min-width: 20px;
            border-radius: 4px;
            margin: 1px;
        }

        /* Hover no handle para efeito de realce */
        QScrollBar::handle:horizontal:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #aad7ff, stop:1 #6aa3ee);
        }

        /* Botão esquerdo (sub-line) */
        QScrollBar::sub-line:horizontal {
            border: 1px solid #666;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #cfcfcf, stop:1 #a9a9a9);
            width: 18px;
            subcontrol-position: left;
            subcontrol-origin: margin;
            border-radius: 3px;
        }

        /* Botão direito (add-line) */
        QScrollBar::add-line:horizontal {
            border: 1px solid #666;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #cfcfcf, stop:1 #a9a9a9);
            width: 18px;
            subcontrol-position: right;
            subcontrol-origin: margin;
            border-radius: 3px;
        }

        /* Remove as setas padrão */
        QScrollBar::up-arrow:horizontal, QScrollBar::down-arrow:horizontal {
            width: 0;
            height: 0;
        }

        /* Fundo entre o handle e os botões */
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
        """

        self.horizontalScrollBarSelec.setStyleSheet(style)

    def update_horizontalScrollBarSelec(self):
        """
        Atualiza o horizontalScrollBarSelec para que seu range corresponda
        ao número de feições da camada atualmente selecionada no comboBoxPontos.
        """
        # Aqui usamos a contagem de linhas do tableWidget, que reflete o número de feições
        row_count = self.tableWidget_Dados1.rowCount()
        self.horizontalScrollBarSelec.blockSignals(True)
        self.horizontalScrollBarSelec.setMinimum(0)
        self.horizontalScrollBarSelec.setMaximum(row_count)
        self.horizontalScrollBarSelec.setSingleStep(1)
        self.horizontalScrollBarSelec.setPageStep(1)
        self.horizontalScrollBarSelec.blockSignals(False)

    def on_pushButtonSeq_clicked(self):
        # Lê o valor atual do spinBoxSelec
        step_val = self.spinBoxSelec.value()
        # Define o singleStep do horizontalScrollBarSelec
        self.horizontalScrollBarSelec.setSingleStep(step_val)

    def update_pushButtonSeq_state(self, value):
        if value == 0:
            self.pushButtonSeq.setEnabled(False)
        else:
            self.pushButtonSeq.setEnabled(True)

    def on_horizontalScrollBarSelec_value_changed(self, new_val):
        """
        Ao mover o horizontalScrollBarSelec, selecionamos um bloco de linhas
        do tableWidget_Dados1 com tamanho = singleStep() do scroll.
        """
        # 1) Obter o tamanho do "bloco" a selecionar
        step = self.horizontalScrollBarSelec.singleStep()  # Definido quando clicou em pushButtonSeq

        # 2) Pegar o total de linhas do tableWidget
        row_count = self.tableWidget_Dados1.rowCount()
        if row_count == 0:
            return  # Nenhuma linha

        # 3) Cálculos para não sair do limite
        start_row = new_val
        end_row   = min(new_val + step - 1, row_count - 1)

        # 4) Bloqueia sinais para evitar loop
        self.tableWidget_Dados1.blockSignals(True)

        # 5) Limpa seleção atual
        self.tableWidget_Dados1.clearSelection()

        # 6) Seleciona as linhas [start_row .. end_row]
        for row in range(start_row, end_row + 1):
            self.tableWidget_Dados1.selectRow(row)

        self.tableWidget_Dados1.blockSignals(False)

        # 7) Sincroniza a seleção com a camada do QGIS
        self.table_selection_changed()

    def table_selection_changed(self):
        """
        Quando a seleção muda na tabela, selecionamos as feições correspondentes na camada.
        """
        if not self.selected_layer:
            return

        # Desconecta temporariamente o sinal para evitar loop recursivo
        try:
            self.selected_layer.selectionChanged.disconnect(self.layer_selection_changed)
        except (TypeError, AttributeError):
            pass

        # Obtém as linhas selecionadas na tabela
        selected_rows = self.tableWidget_Dados1.selectionModel().selectedRows()

        # Mapeia as linhas selecionadas para os IDs de feição
        selected_feature_ids = []
        for index in selected_rows:
            row = index.row()
            item = self.tableWidget_Dados1.item(row, 0)  # Pegamos o item da primeira coluna
            if item is not None:
                fid = item.data(Qt.UserRole)
                if fid is not None:
                    selected_feature_ids.append(fid)

        # Aplica a seleção na camada
        self.selected_layer.selectByIds(selected_feature_ids)
        
        # Atualiza o spinBoxSelec com a quantidade de feições selecionadas
        self.update_spinBoxSelec()

        # Atualiza o estado do pushButtonSeq
        self.update_pushButtonSeq_state(self.spinBoxSelec.value())

        # Reconecta
        self.selected_layer.selectionChanged.connect(self.layer_selection_changed)

    def update_spinBoxSelec(self):
        """Atualiza o spinBoxSelec com o número correto de linhas selecionadas."""
        if self.tableWidget_Dados1.selectionModel():
            selected_rows = self.tableWidget_Dados1.selectionModel().selectedRows()
            count = len(selected_rows)

            # Bloquear sinais para evitar loop
            self.spinBoxSelec.blockSignals(True)
            self.spinBoxSelec.setValue(count)
            self.spinBoxSelec.blockSignals(False)

            # Atualizar variável de controle
            self._prev_spin_box_selec = count
        else:
            self.spinBoxSelec.blockSignals(True)
            self.spinBoxSelec.setValue(0)
            self.spinBoxSelec.blockSignals(False)
            self._prev_spin_box_selec = 0

        # 🔹 Atualiza o estado do botão pushButtonSeq ao alterar o spinBox
        self.update_pushButtonSeq_state(self.spinBoxSelec.value())

    def on_spinBoxSelec_value_changed(self, new_val):
        """
        Quando o valor do spinBoxSelec é alterado,
        a seleção na tabela é ajustada para que o bloco contíguo
        de linhas selecionadas aumente ou diminua de acordo.
        Se não houver seleção, começa do 0.
        Após a alteração, a seleção é sincronizada com a camada do QGIS.
        """
        # Obter o número de linhas atualmente selecionadas
        sel_model = self.tableWidget_Dados1.selectionModel()
        if not sel_model:
            return
        current_selected = sorted([index.row() for index in sel_model.selectedRows()])
        current_count = len(current_selected)

        # Bloqueia sinais para evitar loop
        self.tableWidget_Dados1.blockSignals(True)
        
        # Se não há seleção, comece do 0
        if current_count == 0:
            start = 0
            last_selected = -1  # Nenhuma linha selecionada ainda
        else:
            # Assumindo que a seleção seja contígua; usamos o maior índice selecionado
            start = current_selected[0]
            last_selected = current_selected[-1]

        diff = new_val - current_count

        if diff > 0:
            # Queremos aumentar a seleção: adicionar 'diff' linhas após a última selecionada.
            for i in range(diff):
                next_row = last_selected + 1 if last_selected >= 0 else 0
                if next_row < self.tableWidget_Dados1.rowCount():
                    # Seleciona a linha 'next_row'
                    self.tableWidget_Dados1.selectRow(next_row)
                    last_selected = next_row
                else:
                    # Se não há mais linhas disponíveis, saia do loop.
                    break
        elif diff < 0:
            # Queremos diminuir a seleção: remover 'abs(diff)' linhas, removendo a última linha selecionada cada vez.
            for i in range(-diff):
                # Reobter a lista de linhas selecionadas (em ordem decrescente)
                sel_rows = sorted([index.row() for index in self.tableWidget_Dados1.selectionModel().selectedRows()], reverse=True)
                if sel_rows:
                    row_to_remove = sel_rows[0]
                    index = self.tableWidget_Dados1.model().index(row_to_remove, 0)
                    self.tableWidget_Dados1.selectionModel().select(index, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
                else:
                    break

        # Desbloqueia os sinais da tabela
        self.tableWidget_Dados1.blockSignals(False)

        # Atualiza o spinBoxSelec para refletir a nova contagem
        new_count = len(self.tableWidget_Dados1.selectionModel().selectedRows())
        self.spinBoxSelec.blockSignals(True)
        self.spinBoxSelec.setValue(new_count)
        self._prev_spin_box_selec = new_count
        self.spinBoxSelec.blockSignals(False)

        # Atualiza a seleção na camada do QGIS para sincronizar com a tabela
        self.table_selection_changed()

    def _select_more_features(self, count):
        """Seleciona mais `count` feições na tabela."""
        total_rows = self.tableWidget_Dados1.rowCount()
        
        # Obtém as linhas já selecionadas
        selected_rows = {index.row() for index in self.tableWidget_Dados1.selectionModel().selectedRows()}
        
        # Bloqueia sinais para evitar recursão infinita
        self.tableWidget_Dados1.blockSignals(True)

        # Seleciona mais linhas
        for row in range(total_rows):
            if len(selected_rows) >= count:
                break
            if row not in selected_rows:
                self.tableWidget_Dados1.selectRow(row)
                selected_rows.add(row)

        self.tableWidget_Dados1.blockSignals(False)

    def _deselect_some_features(self, count):
        """Deselects `count` rows from the selection."""
        selected_rows = sorted(index.row() for index in self.tableWidget_Dados1.selectionModel().selectedRows())

        # Bloqueia sinais para evitar recursão infinita
        self.tableWidget_Dados1.blockSignals(True)

        for _ in range(count):
            if selected_rows:
                row = selected_rows.pop()
                self.tableWidget_Dados1.selectionModel().select(
                    self.tableWidget_Dados1.model().index(row, 0),
                    QItemSelectionModel.Deselect
                )

        self.tableWidget_Dados1.blockSignals(False)

    def layer_selection_changed(self, selected_fids, deselected_fids, clear_and_select):
        """
        Dispara quando a seleção na camada muda.
        Vamos sincronizar a tabela.
        """
        self.tableWidget_Dados1.blockSignals(True)
        self.tableWidget_Dados1.clearSelection()

        for fid in selected_fids:
            if fid in self.feature_ids:
                row = self.feature_ids.index(fid)
                self.tableWidget_Dados1.selectRow(row)

        self.tableWidget_Dados1.blockSignals(False)
        # No final, chamamos update_spinBoxSelec ou definimos spinBoxSelec para len(selected_fids) se quiser
        self.spinBoxSelec.blockSignals(True)
        self.spinBoxSelec.setValue(len(self.selected_layer.selectedFeatureIds()))
        self.spinBoxSelec.blockSignals(False)

    def load_table_widget_dados1(self):
        """
        Carrega a tabela de atributos da camada de pontos selecionada
        no comboBoxPontos para o tableWidget_Dados1 e mantém a seleção de feições.
        """

        # Obtém o ID da camada atualmente selecionada
        layer_id = self.comboBoxPontos.currentData()
        layer = QgsProject.instance().mapLayer(layer_id)

        # Se a camada não for válida, limpa a tabela e retorna
        if not layer or not isinstance(layer, QgsVectorLayer) or layer.geometryType() != QgsWkbTypes.PointGeometry:
            self.tableWidget_Dados1.clear()
            self.tableWidget_Dados1.setRowCount(0)
            self.tableWidget_Dados1.setColumnCount(0)
            self.selected_layer = None
            return

        # Salva a seleção atual da camada antes de limpar a tabela
        saved_selection = layer.selectedFeatureIds()

        # Desconecta temporariamente o sinal de seleção para evitar loops
        if self.selected_layer:
            try:
                self.selected_layer.selectionChanged.disconnect(self.layer_selection_changed)
            except (RuntimeError, TypeError, AttributeError):
                pass

        # Atualiza a referência da camada selecionada
        self.selected_layer = layer

        # Obtém os campos e as feições da camada
        fields = layer.fields()
        features = list(layer.getFeatures())

        # Configura as colunas do tableWidget com base nos campos da camada
        self.tableWidget_Dados1.setColumnCount(len(fields))
        self.tableWidget_Dados1.setHorizontalHeaderLabels([field.name() for field in fields])

        # Limpa a lista de IDs e as linhas existentes na tabela
        self.feature_ids = []
        self.tableWidget_Dados1.setRowCount(0)

        # Adiciona os atributos ao tableWidget
        for row_idx, feature in enumerate(features):
            self.tableWidget_Dados1.insertRow(row_idx)
            self.feature_ids.append(feature.id())

            for col_idx, field in enumerate(fields):
                value = feature[field.name()]
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                # Armazena o ID da feição nos dados do item (apenas na primeira coluna)
                if col_idx == 0:
                    item.setData(Qt.UserRole, feature.id())

                self.tableWidget_Dados1.setItem(row_idx, col_idx, item)

        # Ajusta automaticamente o tamanho das colunas e linhas
        self.tableWidget_Dados1.resizeColumnsToContents()
        self.tableWidget_Dados1.verticalHeader().setDefaultSectionSize(20)

        # Reconecta o sinal de seleção da camada
        self.selected_layer.selectionChanged.connect(self.layer_selection_changed)

        # Reaplica a seleção das feições na TABELA
        if saved_selection:
            self.tableWidget_Dados1.blockSignals(True)
            for row in range(self.tableWidget_Dados1.rowCount()):
                item = self.tableWidget_Dados1.item(row, 0)
                if item is not None:
                    fid = item.data(Qt.UserRole)
                    if fid in saved_selection:
                        self.tableWidget_Dados1.selectRow(row)
            self.tableWidget_Dados1.blockSignals(False)

        # --- Reaplica a seleção na CAMADA ---
        if saved_selection:
            layer.selectByIds(saved_selection)  # Restaura a seleção original na camada

        # Ajustar o máximo do spinBox para não passar do total de feições
        row_count = self.tableWidget_Dados1.rowCount()
        self.spinBoxSelec.setMaximum(row_count)

        # Definir o valor do spinBox como o número de feições atualmente selecionadas
        selected_rows = self.tableWidget_Dados1.selectionModel().selectedRows()
        n_selected = len(selected_rows)
        self.spinBoxSelec.setValue(n_selected)
        self._prev_spin_box_selec = n_selected

        self.update_pushButtonSeq_state(self.spinBoxSelec.value())

    def _log_message(self, message, level=Qgis.Info):
        QgsMessageLog.logMessage(message, 'GRAFICO', level=level)

    def reset_graph(self):
        """
        Reseta os dados de todas as curvas do gráfico, inclusive reconfigurando o pen_new_line para a curve_CotaEstaca2,
        se estes atributos já existirem.
        """
        # Verifica se os atributos de curva foram criados
        for attr in ['curve_Z', 'curve_CotaEstaca', 'leftover_lines',
                     'vertical_lines_inrange', 'vertical_lines_outrange', 'curve_CotaEstaca2']:
            if hasattr(self, attr):
                getattr(self, attr).setData([], [])
        
        # Reinicializa o pen_new_line e o aplica à curve_CotaEstaca2 (se existir)
        self.pen_new_line = pg.mkPen(color='blue', width=5, style=Qt.SolidLine)
        self.pen_new_line.setCapStyle(Qt.FlatCap)  # Define extremidades retangulares
        if hasattr(self, 'curve_CotaEstaca2'):
            self.curve_CotaEstaca2.setPen(self.pen_new_line)

    def init_combo_box_raster(self):
        """
        Inicializa o comboBoxRaster com as camadas Raster do projeto.
        Adiciona uma mensagem inicial "Selecione um Raster".
        """
        # Armazena o ID da camada raster atualmente selecionada
        current_raster_id = self.comboBoxRaster.currentData()

        # Obtém todas as camadas do projeto atual
        layers = QgsProject.instance().mapLayers().values()

        # Filtra apenas camadas raster
        raster_layers = [layer for layer in layers if isinstance(layer, QgsRasterLayer)]

        # Limpa o ComboBox antes de adicionar itens
        self.comboBoxRaster.clear()

        # Adiciona a mensagem inicial ao ComboBox
        self.comboBoxRaster.addItem("Selecione Raster", None)

        # Adiciona as camadas raster ao ComboBox
        for raster_layer in raster_layers:
            self.comboBoxRaster.addItem(raster_layer.name(), raster_layer.id())

        # Tenta restaurar a seleção anterior, se possível
        if current_raster_id:
            index = self.comboBoxRaster.findData(current_raster_id)
            if index != -1:
                self.comboBoxRaster.setCurrentIndex(index)
            else:
                # Nenhuma seleção anterior ou inválida; exibe a mensagem inicial
                self.comboBoxRaster.setCurrentIndex(0)
        else:
            # Nenhuma seleção; exibe a mensagem inicial
            self.comboBoxRaster.setCurrentIndex(0)

    def update_combo_box_raster(self, layers):
        """Atualiza o comboBoxRaster quando novas camadas são adicionadas ao projeto."""
        # Verifica se há novas camadas raster entre as adicionadas
        raster_layers_added = [layer for layer in layers if isinstance(layer, QgsRasterLayer)]
        if raster_layers_added:
            # Atualiza o comboBoxRaster
            self.init_combo_box_raster()
            # Seleciona a última camada raster adicionada
            self.comboBoxRaster.setCurrentIndex(self.comboBoxRaster.count() - 1)

    def init_combo_box_pontos(self):
        """
        Inicializa o comboBoxPontos com as camadas vetoriais do tipo PONTO.
        Tenta restaurar a seleção anterior (via currentData).
        """
        current_point_layer_id = self.comboBoxPontos.currentData()

        layers = QgsProject.instance().mapLayers().values()
        point_layers = [
            lyr for lyr in layers
            if isinstance(lyr, QgsVectorLayer) and lyr.geometryType() == QgsWkbTypes.PointGeometry
        ]

        self.comboBoxPontos.clear()
        for p_lyr in point_layers:
            self.comboBoxPontos.addItem(p_lyr.name(), p_lyr.id())

        if current_point_layer_id:
            idx = self.comboBoxPontos.findData(current_point_layer_id)
            if idx != -1:
                self.comboBoxPontos.setCurrentIndex(idx)
            else:
                # Se não achou, seleciona a primeira, se existir
                if point_layers:
                    self.comboBoxPontos.setCurrentIndex(0)
        else:
            # Sem seleção anterior, seleciona a primeira se existir
            if point_layers:
                self.comboBoxPontos.setCurrentIndex(0)

    def on_layers_added(self, layers):
        """
        Quando qualquer camada é adicionada, checamos se há Raster ou Pontos
        e chamamos as funções de atualização correspondentes.
        """
        # Conecta o sinal nameChanged para cada camada nova
        for layer in layers:
            layer.nameChanged.connect(self.on_layer_name_changed)

        # Se quiser atualizar comboboxes aqui também, faça:
        self.update_combo_box_raster(layers)
        self.update_combo_box_pontos(layers)
        
        if self.comboBoxPontos.count() > 0:
            self.load_table_widget_dados1()

        # Atualiza listWidget
        self.update_list_widget_estruturas()

        # Se a camada removida era a selecionada, apaga o gráfico
        if self.current_estruturas_layer and self.current_estruturas_layer.id() in layer_ids:
            self.current_estruturas_layer = None
            self.update_graph()

        # Monitora a adição do botão pushButtonExportarDXF 
        self.atualizar_estado_pushButtonExportarDXF()

    def update_combo_box_pontos(self, layers):
        """
        Atualiza o comboBoxPontos quando camadas são adicionadas.
        Somente se nessas layers houver alguma do tipo PONTO.
        """
        point_layers_added = [
            lyr for lyr in layers
            if isinstance(lyr, QgsVectorLayer) and lyr.geometryType() == QgsWkbTypes.PointGeometry
        ]
        if point_layers_added:
            self.init_combo_box_pontos()
            # (Opcional) Selecionar a última camada ponto adicionada
            self.comboBoxPontos.setCurrentIndex(self.comboBoxPontos.count() - 1)

    def on_layer_name_changed(self):
        """
        Chamado quando o nome de qualquer camada no projeto é alterado.
        Atualizamos apenas o texto dos itens nos ComboBoxes, sem recriar tudo.
        """
        # Atualiza nomes no comboBoxRaster
        for i in range(self.comboBoxRaster.count()):
            layer_id = self.comboBoxRaster.itemData(i)
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer and isinstance(layer, QgsRasterLayer):
                self.comboBoxRaster.setItemText(i, layer.name())

        # Atualiza nomes no comboBoxPontos
        for i in range(self.comboBoxPontos.count()):
            layer_id = self.comboBoxPontos.itemData(i)
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer and isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PointGeometry:
                self.comboBoxPontos.setItemText(i, layer.name())

    def layer_selection_changed(self, selected_fids, deselected_fids, clear_and_select):
        """
        Quando a seleção muda na camada, atualizamos a seleção de linhas na tabela.
        """
        # Bloqueia temporariamente o sinal da tabela para evitar recursão
        self.tableWidget_Dados1.blockSignals(True)

        # Limpa a seleção atual da tabela
        self.tableWidget_Dados1.clearSelection()

        # Selecione as linhas correspondentes aos fids selecionados
        for fid in selected_fids:
            if fid in self.feature_ids:
                row = self.feature_ids.index(fid)
                self.tableWidget_Dados1.selectRow(row)

        # Desbloqueia os sinais
        self.tableWidget_Dados1.blockSignals(False)

    def mostrar_mensagem(self, texto, tipo, duracao=3, caminho_pasta=None, caminho_arquivo=None):
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

    def selecionar_coluna(self, numeric_fields):
        """
        Exibe um diálogo para selecionar uma coluna a partir de uma lista de colunas numéricas.
        """
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Selecionar Coluna")
        dialog.setLabelText("Escolha uma coluna numérica:")
        dialog.setComboBoxItems(numeric_fields)

        if dialog.exec_() == QDialog.Accepted:
            return dialog.textValue()
        return None

    def create_point_layer(self, layer_name, point_features):
        """
        Cria uma nova camada de pontos com atributos:
            X, Y, Z, CotaEstaca, AlturaEstaca

        point_features deve ser uma lista de tuplas:
           (x, y, z, cota_estaca, altura_estaca)
        """
        # Define os campos
        fields = QgsFields()
        fields.append(QgsField("X", QVariant.Double))
        fields.append(QgsField("Y", QVariant.Double))
        fields.append(QgsField("Z", QVariant.Double))
        # (Novo) Adicionamos as colunas solicitadas
        fields.append(QgsField("CotaEstaca", QVariant.Double))
        fields.append(QgsField("AlturaEstaca", QVariant.Double))

        # Cria a camada de memória
        crs = self.selected_layer.crs()
        new_layer = QgsVectorLayer("Point?crs=" + crs.authid(), layer_name, "memory")
        new_layer_data = new_layer.dataProvider()

        # Adiciona os campos à camada
        new_layer_data.addAttributes(fields)
        new_layer.updateFields()

        # Adiciona as feições
        for x, y, z_real, cota, altura in point_features:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
            feat.setAttributes([x, y, z_real, cota, altura])
            new_layer_data.addFeature(feat)

        new_layer.updateExtents()
        return new_layer

    def get_z_from_raster(self, raster_layer, x, y):
        """
        Obtém o valor de Z de um Raster para as coordenadas X, Y fornecidas.
        """
        raster_provider = raster_layer.dataProvider()
        raster_extent = raster_layer.extent()

        # Converte as coordenadas do ponto para o sistema de referência do raster
        raster_crs = raster_layer.crs()
        point_crs = self.selected_layer.crs()
        if point_crs != raster_crs:
            transform = QgsCoordinateTransform(point_crs, raster_crs, QgsProject.instance())
            point = transform.transform(QgsPointXY(x, y))
        else:
            point = QgsPointXY(x, y)

        # Verifica se o ponto está dentro da extensão do Raster
        if not raster_extent.contains(point):
            return 0  # Se o ponto está fora do Raster, retorna 0

        # Obtém o valor de Z no ponto
        ident = raster_provider.identify(point, QgsRaster.IdentifyFormatValue)
        if ident.isValid():
            band_values = ident.results()
            if band_values:
                return list(band_values.values())[0]  # Retorna o primeiro valor da banda

        return 0  # Caso não consiga obter o valor

    def generate_layer_name(self, raster_name=""):
        """
        Gera um nome sequencial para a nova camada com base em M1, M2, etc.
        Se houver um Raster, adiciona o nome dele no formato "M1_NomeDoRaster".
        """
        base_name = "M"
        idx = 1

        # Obtém os nomes das camadas já existentes no projeto
        existing_layer_names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]

        # Incrementa o índice até encontrar um nome não usado
        while True:
            new_name = f"{base_name}{idx}"
            if raster_name:
                new_name += f"_{raster_name}"
            if new_name not in existing_layer_names:
                break
            idx += 1

        return new_name

    def create_point_layer(self, layer_name, point_features):
        """
        Cria uma nova camada de pontos com os atributos:
            X, Y, Z, CotaEstaca, AlturaEstaca

        point_features deve ser uma lista de tuplas:
           (x, y, z, cota_estaca, altura_estaca)
        """
        # Define os campos
        fields = QgsFields()
        fields.append(QgsField("X", QVariant.Double))
        fields.append(QgsField("Y", QVariant.Double))
        fields.append(QgsField("Z", QVariant.Double))
        fields.append(QgsField("CotaEstaca", QVariant.Double))  # Novo campo
        fields.append(QgsField("AlturaEstaca", QVariant.Double))  # Novo campo

        # Cria a camada de memória
        crs = self.selected_layer.crs()  # Usa o mesmo sistema de coordenadas da camada original
        new_layer = QgsVectorLayer(f"Point?crs={crs.authid()}", layer_name, "memory")
        new_layer_data = new_layer.dataProvider()

        # Adiciona os campos à camada
        new_layer_data.addAttributes(fields)
        new_layer.updateFields()

        # Adiciona as feições
        for x, y, z, cota_estaca, altura_estaca in point_features:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
            feat.setAttributes([x, y, z, cota_estaca, altura_estaca])
            new_layer_data.addFeature(feat)

        # Atualiza a camada
        new_layer.updateExtents()
        return new_layer

    def on_layers_removed(self, layer_ids):
        """
        Atualiza os ComboBoxes e limpa a tabela se a camada atual for removida.
        Também remove automaticamente a camada de suporte associada.
        """
        self.init_combo_box_raster()
        self.init_combo_box_pontos()

        # Verifica se a camada selecionada foi removida
        current_layer_id = self.comboBoxPontos.currentData()
        if current_layer_id not in layer_ids:
            self.load_table_widget_dados1()
        else:
            # Limpa a tabela caso a camada selecionada tenha sido removida
            self.tableWidget_Dados1.clear()
            self.tableWidget_Dados1.setRowCount(0)
            self.tableWidget_Dados1.setColumnCount(0)

        # Atualiza listWidget
        self.update_list_widget_estruturas()

        # Atualiza o listWidget removendo os itens das camadas deletadas
        for i in reversed(range(self.listWidget_Lista.count())):  # Percorre de trás para frente
            item = self.listWidget_Lista.item(i)
            if item and item.data(Qt.UserRole) in layer_ids:
                self.listWidget_Lista.takeItem(i)  # Remove o item da lista

        # Se a camada removida era a selecionada...
        if self.current_estruturas_layer and self.current_estruturas_layer.id() in layer_ids:
            removed_main_layer_name = self.current_estruturas_layer.name()
            self.current_estruturas_layer = None
            self.graphWidget.clear()

            # Tenta remover do QGIS a camada "removed_main_layer_name + '_Suporte'"
            support_name = removed_main_layer_name + "_Suporte"
            for lyr in self.support_layers:
                if lyr.name() == support_name:
                    QgsProject.instance().removeMapLayer(lyr.id())
                    self.support_layers.remove(lyr)
                    break

        # Inicializa a lista antes de qualquer verificação
        support_layers_to_remove = []

        for layer in self.support_layers:
            # 1) Se o ID da camada de suporte está explicitamente em layer_ids, remova
            if layer.id() in layer_ids:
                QgsProject.instance().removeMapLayer(layer.id())
                support_layers_to_remove.append(layer)
                continue  # já tratou esse caso

            # 2) Verifica se a camada de suporte pertence a uma camada principal removida
            if layer.name().endswith("_Suporte"):
                main_name = layer.name().replace("_Suporte", "")

                # Verifica se essa camada principal ainda existe no projeto
                main_layer = next(
                    (ly for ly in QgsProject.instance().mapLayers().values() 
                     if ly.name() == main_name),
                    None)

                if main_layer is None:  # Se a camada principal foi removida, remova a de suporte
                    QgsProject.instance().removeMapLayer(layer.id())
                    support_layers_to_remove.append(layer)

        # Agora a variável está definida e pode ser usada na filtragem
        self.support_layers = [lyr for lyr in self.support_layers if lyr not in support_layers_to_remove]

        # Atualiza a exibição da tabela de dados
        self.update_scroll_area_dados()

        # Atualiza tableView_2 e listWidget_inc
        self.update_tableView_2()
        self.update_listWidget_inc()

        # 🔹 Garante que self.selected_layer seja resetado corretamente
        if self.selected_layer and self.selected_layer.id() in layer_ids:
            self.selected_layer = None

        # Monitora a remoção do botão pushButtonExportarDXF 
        self.atualizar_estado_pushButtonExportarDXF()

    def update_list_widget_estruturas(self):
        """
        Limpa o listWidget_Lista e adiciona o nome de todas as camadas
        presentes no grupo 'Estruturas'.
        """
        # Limpa o listWidget antes de adicionar os nomes das camadas
        self.listWidget_Lista.clear()
        
        root = QgsProject.instance().layerTreeRoot()
        
        # Localiza o grupo "Estruturas" (se existir)
        grupo_estruturas = None
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup) and child.name() == "Estruturas":
                grupo_estruturas = child
                break
        
        # Se o grupo não existir, não faz nada
        if not grupo_estruturas:
            return
        
        # Percorre as camadas do grupo e adiciona os itens ao listWidget_Lista
        for child in grupo_estruturas.children():
            if isinstance(child, QgsLayerTreeLayer):
                layer = child.layer()
                if layer is not None:
                    item = QListWidgetItem(layer.name())
                    item.setData(Qt.UserRole, layer.id())  # Armazena o ID da camada para remoção
                    self.listWidget_Lista.addItem(item)

    def recalc_current_layer(self):
        """
        Lê os valores de doubleSpinBox_1 e 2, localiza as feições na self.current_estruturas_layer,
        e atualiza CotaEstaca e AlturaEstaca por interpolação linear 
        entre o primeiro e o último, na ordem da coluna 'sequencia' (se existir) ou FID.
        """

        lyr = self.current_estruturas_layer
        if not lyr:
            return  # Nenhuma camada selecionada

        # Lê os valores do spinBox
        delta1 = self.doubleSpinBox_1.value()
        delta2 = self.doubleSpinBox_2.value()

        # Precisamos garantir que a camada tenha campos: X, Y, Z, CotaEstaca, AlturaEstaca
        # Se não tiver, não há como recalcular. (Você pode tratar esse caso, exibir mensagem, etc.)
        field_names = [f.name() for f in lyr.fields()]
        if not all(fname in field_names for fname in ["X","Y","Z","CotaEstaca","AlturaEstaca"]):
            self.mostrar_mensagem("A camada selecionada não possui os campos X, Y, Z, CotaEstaca, AlturaEstaca.", "Erro")
            return

        # Vamos determinar a ordem das feições.
        #   1) Se existe campo 'sequencia', ordenamos por ele.
        #      (Alternativamente, você poderia ordenar pela string M1E1, M1E2..., mas teria
        #       que extrair o número da estaca. Por simplicidade, basta ordenar pela FID,
        #       ou por X crescente, etc., depende da sua lógica.)
        #   2) Se não, podemos ordenar pela FID.
        sequencia_index = lyr.fields().indexFromName("sequencia")
        features_all = list(lyr.getFeatures())

        def get_seq_num(feat):
            # Exemplo simples: se 'sequencia' = 'M1E3', extrair o número 3
            # Mas isso depende do seu padrão. Aqui faço um parse simples:
            val = feat["sequencia"]
            # Espera algo tipo M1E3
            # Tentar extrair a parte numérica após 'E'
            try:
                idxE = val.index("E")
                return int(val[idxE+1:])
            except:
                return feat.id()  # fallback, se não conseguir parse

        if sequencia_index >= 0:
            # Ordenar usando a função get_seq_num
            features_all.sort(key=get_seq_num)
        else:
            # Se não existe 'sequencia', ordena por FID
            features_all.sort(key=lambda f: f.id())

        if len(features_all) < 2:
            # Precisamos de pelo menos 2 pontos para interpolar
            return

        # Montar lista com (feature, X, Y, Z)
        feats_info = []
        for f in features_all:
            x_ = f["X"]
            y_ = f["Y"]
            z_ = f["Z"]
            feats_info.append((f, x_, y_, z_))

        # Pega o primeiro e o último
        first_feat, x0, y0, z0 = feats_info[0]
        last_feat,  x1, y1, z1 = feats_info[-1]

        cota_first = z0 + delta1
        cota_last = z1 + delta2

        dx = x1 - x0
        dy = y1 - y0
        dist_total = math.sqrt(dx*dx + dy*dy)

        # Evitar zero
        if dist_total == 0:
            # Se for zero, significa que todos os pontos estão no mesmo lugar,
            # ou só existe 1 ponto.
            # Você pode decidir o que fazer, p. ex.:
            for (f, x_, y_, z_) in feats_info:
                # CotaEstaca = z0 + delta1 (ou delta2, pois first=last)
                # AlturaEstaca = cotaEstaca - z_
                cota_estaca = z0 + delta1
                altura_estaca = cota_estaca - z_
                f["CotaEstaca"] = cota_estaca
                f["AlturaEstaca"] = altura_estaca
            lyr.startEditing()
            for f,_,_,_ in feats_info:
                lyr.updateFeature(f)
            lyr.commitChanges()
            return

        # Caso normal: dist_total > 0
        dc = cota_last - cota_first

        lyr.startEditing()

        for (f, x_, y_, z_) in feats_info:
            # distância parcial do (x_, y_) até (x0, y0)
            dparc = math.sqrt((x_ - x0)**2 + (y_ - y0)**2)
            frac = dparc / dist_total
            cota_estaca = cota_first + dc * frac
            altura_estaca = cota_estaca - z_

            # Agora arredonda todos para 3 casas decimais
            f["X"] = round(x_, 3)
            f["Y"] = round(y_, 3)
            f["Z"] = round(z_, 3)
            f["CotaEstaca"] = round(cota_estaca, 3)
            f["AlturaEstaca"] = round(altura_estaca, 3)

            lyr.updateFeature(f)

        lyr.commitChanges()

        # Se houver uma camada raster selecionada, atualiza o gráfico de suporte;
        # caso contrário, atualiza o gráfico padrão.
        if self.comboBoxRaster.currentData():
            self.update_support_graph()
        else:
            self.update_graph()

        self.update_tableView_2()
        self.update_listWidget_inc()

    def setup_graph(self):
        """
        Configura o gráfico no scrollAreaGrafico.
        Melhora a suavização, ativa o anti-aliasing e configura as curvas de perfil.
        """
        self.graphWidget = PlotWidget()
        self.graphWidget.setAntialiasing(True)

        self.layout_grafico = QVBoxLayout(self.scrollAreaGrafico)
        self.layout_grafico.addWidget(self.graphWidget)

        # self.graphWidget.setTitle("Perfil de Elevação")
        self.graphWidget.setLabel("bottom", "Distância Acumulada (m)")
        self.graphWidget.setLabel("left", "Altitude (m)")
        # self.graphWidget.showGrid(x=True, y=True, alpha=0.3)

        self.legend = pg.LegendItem(colCount=10, offset=(0, 0))
        # Associa a legenda ao plot principal:
        self.legend.setParentItem(self.graphWidget.getPlotItem())

        # Defina a posição onde deseja que a legenda fique.
        # Por exemplo, (0, 0) é o topo-esquerda do gráfico.
        self.legend.setPos(1, 0)

        self.graphWidget.addLegend()
        self.graphWidget.setRenderHint(QPainter.Antialiasing)
        self.graphWidget.setRenderHint(QPainter.HighQualityAntialiasing)
        self.graphWidget.setRenderHint(QPainter.SmoothPixmapTransform)

    def update_tableView_2(self):
        """
        Atualiza o tableView_2 exibindo as colunas 'sequencia' e 'AlturaEstaca'
        da camada atualmente selecionada (self.current_estruturas_layer).
        Os dados são exibidos com alinhamento centralizado, são somente para leitura,
        e a cor de cada linha indica se AlturaEstaca está dentro do intervalo definido
        por doubleSpinBoxPadrao ± doubleSpinBoxVaria (azul se estiver dentro, vermelho se estiver fora).
        """
        # Se não houver camada selecionada, limpa o tableView_2.
        if not self.current_estruturas_layer:
            self.tableView_2.setModel(None)
            return

        # Verifica se os campos necessários existem
        field_names = [field.name() for field in self.current_estruturas_layer.fields()]
        if "sequencia" not in field_names or "AlturaEstaca" not in field_names:
            self.tableView_2.setModel(None)
            return

        # Pega os valores dos spinBoxes para definir o intervalo
        padraoValue = self.doubleSpinBoxPadrao.value()
        variaValue = self.doubleSpinBoxVaria.value()
        lower_lim = padraoValue - variaValue
        upper_lim = padraoValue + variaValue

        # Cria um modelo padrão com 2 colunas
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["LISTA", "AlturaEstaca"])

        # Fonte em negrito
        bold_font = QFont()
        bold_font.setBold(True)

        # Itera sobre as feições da camada e adiciona os dados ao modelo
        for feature in self.current_estruturas_layer.getFeatures():
            seq = feature["sequencia"]
            altura = feature["AlturaEstaca"]

            item_seq = QStandardItem(str(seq))
            item_altura = QStandardItem(str(altura))

            # Define os itens como não editáveis
            item_seq.setEditable(False)
            item_altura.setEditable(False)

            # Centraliza o texto
            item_seq.setTextAlignment(Qt.AlignCenter)
            item_altura.setTextAlignment(Qt.AlignCenter)

            # Aplica a fonte em negrito
            item_seq.setFont(bold_font)
            item_altura.setFont(bold_font)

            # Centraliza o texto
            item_seq.setTextAlignment(Qt.AlignCenter)
            item_altura.setTextAlignment(Qt.AlignCenter)

            # Tenta converter AlturaEstaca para número para fazer a comparação
            try:
                numeric_altura = float(altura)
            except Exception:
                numeric_altura = 0.0

            # Verifica se AlturaEstaca está dentro do intervalo definido
            if lower_lim <= numeric_altura <= upper_lim:
                color = Qt.blue
            else:
                color = Qt.red

            # Define a cor do texto
            item_seq.setForeground(color)
            item_altura.setForeground(color)

            model.appendRow([item_seq, item_altura])

        self.tableView_2.setModel(model)
        self.tableView_2.resizeColumnsToContents()
        # Reduz a altura das linhas (por exemplo, 20 pixels)
        self.tableView_2.verticalHeader().setDefaultSectionSize(20)
        # Impede a edição na view
        self.tableView_2.setEditTriggers(self.tableView_2.NoEditTriggers)

    def update_listWidget_inc(self):
        """
        Atualiza o listWidget_inc exibindo:
          - A inclinação média entre os valores de Z (calculada como a média dos incrementos de Z dividido
            pela distância acumulada entre pontos consecutivos), exibida em laranja.
          - A inclinação entre o primeiro e o último valor de CotaEstaca (calculada de forma global), exibida em azul.
        Os valores são convertidos para porcentagem e exibidos com o símbolo '%'.
        O listWidget_inc é resetado a cada atualização.
        """
        # Reseta o listWidget_inc
        self.listWidget_inc.clear()

        # Verifica se existe uma camada selecionada
        if not self.current_estruturas_layer:
            return

        # Verifica se os campos necessários existem
        field_names = [field.name() for field in self.current_estruturas_layer.fields()]
        if "Z" not in field_names or "CotaEstaca" not in field_names or "sequencia" not in field_names:
            return

        # Obtém as feições da camada ordenadas pela coluna 'sequencia' (ou FID, se não houver)
        seq_index = self.current_estruturas_layer.fields().indexFromName("sequencia")
        feats = list(self.current_estruturas_layer.getFeatures())
        
        def get_seq_num(feat):
            val = feat["sequencia"]
            try:
                idxE = val.index("E")
                return int(val[idxE + 1:])
            except:
                return feat.id()
        
        if seq_index >= 0:
            feats.sort(key=get_seq_num)
        else:
            feats.sort(key=lambda f: f.id())
        
        # Verifica se há pelo menos 2 pontos para calcular inclinação
        if len(feats) < 2:
            return

        # Construção dos arrays: x_vals (distância acumulada), z_vals e cota_vals
        x_vals = []
        z_vals = []
        cota_vals = []
        dist_acum = 0.0
        prev_x = None
        for f in feats:
            x_val = f["X"]
            z_val = f["Z"]
            cota_val = f["CotaEstaca"]
            if prev_x is not None:
                dx = abs(x_val - prev_x)
                dist_acum += dx
            else:
                dist_acum = 0.0
            x_vals.append(dist_acum)
            z_vals.append(z_val)
            cota_vals.append(cota_val)
            prev_x = x_val

        # Cálculo da inclinação média entre os valores de Z (média dos incrementos)
        slopes = []
        for i in range(len(x_vals)-1):
            dx = x_vals[i+1] - x_vals[i]
            if dx != 0:
                slope = (z_vals[i+1] - z_vals[i]) / dx
                slopes.append(slope)
        if slopes:
            avg_slope_z = sum(slopes) / len(slopes)
        else:
            avg_slope_z = 0.0

        # Cálculo da inclinação entre o primeiro e o último valor de CotaEstaca
        dx_total = x_vals[-1] - x_vals[0]
        if dx_total != 0:
            slope_cota = (cota_vals[-1] - cota_vals[0]) / dx_total
        else:
            slope_cota = 0.0

        # Converte as inclinações para porcentagem (m/m * 100) e formata com 2 casas decimais
        avg_slope_z_pct = avg_slope_z * 100
        slope_cota_pct = slope_cota * 100

        avg_slope_z_str = f"Inclinação média Z: {avg_slope_z_pct:.2f}%"
        slope_cota_str = f"Inclinação da Estrututa: {slope_cota_pct:.2f}%"

        # Cria itens de lista com as cores definidas:
        item_z = QListWidgetItem(avg_slope_z_str)
        item_z.setForeground(QBrush(QColor("orange")))  # Inclinação de Z em laranja
        # Aumenta o tamanho do texto:
        font_z = QFont()
        font_z.setPointSize(10)
        item_z.setFont(font_z)

        item_cota = QListWidgetItem(slope_cota_str)
        item_cota.setForeground(QBrush(QColor("blue")))   # Inclinação de CotaEstaca em azul
        font_cota = QFont()
        font_cota.setPointSize(10)
        item_cota.setFont(font_cota)

        # Adiciona os itens ao listWidget_inc
        self.listWidget_inc.addItem(item_z)
        self.listWidget_inc.addItem(item_cota)

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

        # Define o nome da camada de suporte com o nome da camada de estacas + "_Suporte"
        support_layer_name = f"{estacas_layer.name()}_Suporte"
        print("Nome que vou dar ao suporte:", support_layer_name)

        # Cria a camada de suporte (em memória) com o nome ajustado
        support_layer = QgsVectorLayer(f"Point?crs={crs}", support_layer_name, "memory")

        prov = support_layer.dataProvider()

        # Adiciona os campos necessários, incluindo "Acumula_dist"
        fields = [
            QgsField("ID", QVariant.Int),
            QgsField("Original_ID", QVariant.Int),
            QgsField("X", QVariant.Double),
            QgsField("Y", QVariant.Double),
            QgsField("Znovo", QVariant.Double),
            QgsField("Acumula_dist", QVariant.Double)
        ]
        prov.addAttributes(fields)
        support_layer.updateFields()

        # Obtém todas as feições e os pontos da camada de estacas
        estacas_features = [feat for feat in estacas_layer.getFeatures()]
        estacas_points = [feat.geometry().asPoint() for feat in estacas_features]
        all_points = []  # Lista para guardar os pontos de suporte gerados
        support_point_id = 0
        last_coord = None
        acumula_dist = 0

        # --- Alteração: usar o campo "AlturaEstaca" em vez de "Desnivel" ---
        altura_index = estacas_layer.fields().indexFromName('AlturaEstaca')
        if altura_index == -1:
            self.mostrar_mensagem("O campo 'AlturaEstaca' não foi encontrado na camada.", "Erro")
            return

        # Obter os valores de AlturaEstaca para o primeiro e o último ponto
        first_altura = estacas_features[0][altura_index]
        last_altura = estacas_features[-1][altura_index]

        # Definir extensão antes do primeiro ponto e após o último
        extend_by_start = min(abs(first_altura) + 2, 2)  # No máximo 2 metros
        extend_by_end = min(abs(last_altura) + 2, 2)       # No máximo 2 metros

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
            extra_point = QgsPointXY(
                estacas_points[0].x() - first_segment_dir.x() * (i * support_spacing) / first_segment_dir.length(),
                estacas_points[0].y() - first_segment_dir.y() * (i * support_spacing) / first_segment_dir.length()
            )
            z_value = self.sample_raster_value(extra_point, raster_layer)
            if z_value is None:
                break  # Interrompe se não há valor de Z
            support_point_id += 1
            # Como a coluna "ID" não está explícita, para Original_ID usamos um valor negativo indicando ponto extra
            all_points.append((extra_point, -i, support_point_id))
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
                # Se a camada de estacas não possui um campo "ID", usamos o índice (i+1) como Original_ID
                original_id = i + 1
                all_points.append((inter_point, original_id, support_point_id))
                current_step += 1
                progressBar.setValue(current_step)
                QApplication.processEvents()

        # Adicionar pontos extras após o último ponto de estacas
        last_segment_dir = estacas_points[-1] - estacas_points[-2]
        for i in range(0, num_points_after_last_stake):
            extra_point = QgsPointXY(
                estacas_points[-1].x() + last_segment_dir.x() * (i * support_spacing) / last_segment_dir.length(),
                estacas_points[-1].y() + last_segment_dir.y() * (i * support_spacing) / last_segment_dir.length()
            )
            z_value = self.sample_raster_value(extra_point, raster_layer)
            if z_value is None:
                break
            support_point_id += 1
            # Se a camada de estacas não possui um campo "ID", usamos o número total de estacas como Original_ID
            original_id = estacas_features[-1]['ID'] if 'ID' in estacas_features[-1].fields().names() else len(estacas_features)
            all_points.append((extra_point, original_id, support_point_id))
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

            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(*current_coord)))
            feat.setAttributes([support_point_id, original_id, round(point.x(), 3), round(point.y(), 3), None, round(acumula_dist, 3)])
            prov.addFeature(feat)
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
            current_step += 1
            progressBar.setValue(current_step)
            QApplication.processEvents()
        support_layer.commitChanges()
        
        self.iface.messageBar().clearWidgets()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.mostrar_mensagem(f"Camada de suporte criada com sucesso em {elapsed_time:.2f} segundos.", "Sucesso")
        
        # NÃO adicionamos a camada ao projeto. Em vez disso, armazenamos em uma lista interna.
        if not hasattr(self, "support_layers"):
            self.support_layers = []

        self.support_layers.append(support_layer)

        # Atualiza o scrollAreaDADOS para incluir a nova tabela
        self.update_scroll_area_dados()

        return support_layer

    def calcular(self):
        """
        Calcula uma nova camada de pontos a partir das feições selecionadas no tableWidget_Dados1.
        Se uma camada Raster estiver selecionada, o Z será obtido do Raster.
        A camada é adicionada ao grupo "Estruturas" com o nome correto.
        Agora, também cria duas colunas:
          - CotaEstaca
          - AlturaEstaca
        usando interpolação linear entre o primeiro e o último ponto.
        """
        # Verifica se existe uma camada associada
        if not self.selected_layer:
            self.mostrar_mensagem("Nenhuma camada associada ao tableWidget.", "Erro")
            return

        # Verifica se há feições selecionadas
        selected_feature_ids = self.selected_layer.selectedFeatureIds()
        if not selected_feature_ids:
            self.mostrar_mensagem("Nenhuma feição selecionada na tabela.", "Erro")
            return

        # Ordena as feições selecionadas na mesma ordem que aparece no tableWidget
        selected_features = [feat for feat in self.selected_layer.getFeatures() if feat.id() in selected_feature_ids]
        selected_features.sort(key=lambda f: self.feature_ids.index(f.id()))

        # Recupera valor do doubleSpinBox_1 e 2
        delta1 = self.doubleSpinBox_1.value()  # Ajuste no 1º ponto
        delta2 = self.doubleSpinBox_2.value()  # Ajuste no último ponto

        # Obtém a camada raster selecionada (se existir)
        raster_layer_id = self.comboBoxRaster.currentData()
        raster_layer = QgsProject.instance().mapLayer(raster_layer_id) if raster_layer_id else None

        # Gera nome para a nova camada
        raster_name = raster_layer.name() if raster_layer else ""
        layer_name = self.generate_layer_name(raster_name)

        # 1) Monta a lista dos pontos (x, y, z) na ordem das feições
        point_features = []
        for feature in selected_features:
            geom = feature.geometry()
            if geom.isEmpty():
                continue
            point = geom.asPoint()
            x, y = point.x(), point.y()

            # Se houver um Raster selecionado, extrai o Z do Raster
            if raster_layer:
                z_real = self.get_z_from_raster(raster_layer, x, y)
                # Se get_z_from_raster retorna None, significa que não há valor de raster p/ esse ponto
                if z_real is None:
                    self.mostrar_mensagem("Não existe raster sob algum dos pontos selecionados.", "Erro")
                    return
            else:
                # Tenta obter Z de um campo 'Z' da camada, caso exista
                z_field_index = self.selected_layer.fields().indexFromName('Z')
                if z_field_index >= 0:
                    z_real = feature[z_field_index]
                    if z_real is None:
                        z_real = 0
                else:
                    z_real = 0

            point_features.append((x, y, z_real))

        # Se não houve geometria válida
        if not point_features:
            self.mostrar_mensagem("Nenhuma geometria válida encontrada nas feições selecionadas.", "Erro")
            return

        # 2) Calcula a CotaEstaca e a AlturaEstaca usando interpolação linear entre 1º e último ponto
        x0, y0, z0 = point_features[0]
        x1, y1, z1 = point_features[-1]

        cota_first = z0 + delta1
        cota_last = z1 + delta2
        dc = cota_last - cota_first
        dist_total = math.sqrt((x1 - x0)**2 + (y1 - y0)**2)

        if dist_total == 0 and len(point_features) > 1:
            self.mostrar_mensagem("Primeiro e último pontos coincidem, não é possível interpolar.", "Erro")
            return

        final_features = []
        for (x, y, z_real) in point_features:
            frac = math.sqrt((x - x0)**2 + (y - y0)**2) / dist_total if dist_total > 0 else 0.0
            cota_estaca = cota_first + (dc * frac)
            altura_estaca = cota_estaca - z_real
            final_features.append((x, y, z_real, cota_estaca, altura_estaca))

        # Agora criamos uma lista com arredondamento de 3 casas decimais
        final_features_3 = []
        for (xx, yy, zz, cc, aa) in final_features:
            xx_r = round(xx, 3)
            yy_r = round(yy, 3)
            zz_r = round(zz, 3)
            cc_r = round(cc, 3)
            aa_r = round(aa, 3)
            final_features_3.append((xx_r, yy_r, zz_r, cc_r, aa_r))

        # Cria a nova camada usando os valores arredondados
        new_layer = self.create_point_layer(layer_name, final_features_3)

        # 4) Adiciona a camada ao grupo "Estruturas" e recebe a camada final (que pode ser nova ou a mesma)
        new_layer = self.add_layer_to_group(new_layer, "Estruturas")
        
        # 5) Agora que a camada existe e tem um nome, chamamos set_label_for_layer
        self.set_label_for_layer(new_layer)

        self.mostrar_mensagem(f"Nova camada '{layer_name}' criada e adicionada ao grupo 'Estruturas'.", "Sucesso")

        # Se houver uma camada raster selecionada, usa a camada recém-criada como referência
        if raster_layer:
            support_layer = self.create_support_points_layer(new_layer, raster_layer)
            if support_layer:
                self.mostrar_mensagem("Camada de suporte criada com sucesso.", "Sucesso")

        # Monitora o botão pushButtonExportarDXF 
        self.atualizar_estado_pushButtonExportarDXF()

    def add_layer_to_group(self, layer, group_name):
        """
        Adiciona a camada ao grupo especificado e retorna a camada que ficou efetivamente no projeto.
        """
        root = QgsProject.instance().layerTreeRoot()

        # Verifica se o grupo já existe
        group = next((g for g in root.children() if isinstance(g, QgsLayerTreeGroup) and g.name() == group_name), None)
        if not group:
            group = root.addGroup(group_name)

        # Adiciona a camada ao grupo
        QgsProject.instance().addMapLayer(layer, False)
        group.addLayer(layer)

        # Verifica se a camada tem um provedor de dados válido
        if not layer.dataProvider():
            self.mostrar_mensagem("Erro ao acessar a camada para atualização.", "Erro")
            return layer  # ou retorne None

        layer_name = layer.name()
        m_match = re.match(r"M(\d+)", layer_name)  # Extrai o número M do nome da camada
        m_value = m_match.group(1) if m_match else "1"

        existing_fields = [field.name() for field in layer.fields()]

        # Se o campo 'sequencia' não existe, cria uma nova camada e substitui a original
        if 'sequencia' not in existing_fields:
            new_fields = [QgsField('sequencia', QVariant.String)] + layer.fields().toList()
            new_layer = QgsVectorLayer(f"Point?crs={layer.crs().authid()}", layer_name, "memory")
            new_layer_data = new_layer.dataProvider()
            new_layer_data.addAttributes(new_fields)
            new_layer.updateFields()

            new_features = []
            for i, feature in enumerate(layer.getFeatures()):
                new_feature = QgsFeature()
                new_feature.setGeometry(feature.geometry())
                e_value = i + 1
                attributes = [f'M{m_value}E{e_value}'] + feature.attributes()

                # Ajusta X e Y para 3 casas decimais
                geom = feature.geometry()
                if geom and not geom.isEmpty():
                    point = geom.asPoint()
                    x_rounded = round(point.x(), 3)
                    y_rounded = round(point.y(), 3)
                    if 'X' in existing_fields:
                        x_index = existing_fields.index('X') + 1  # +1 pois 'sequencia' foi adicionada no início
                        attributes[x_index] = x_rounded
                    if 'Y' in existing_fields:
                        y_index = existing_fields.index('Y') + 1
                        attributes[y_index] = y_rounded

                new_feature.setAttributes(attributes)
                new_features.append(new_feature)

            new_layer_data.addFeatures(new_features)
            new_layer.updateExtents()

            # Remove a camada antiga e adiciona a nova
            QgsProject.instance().removeMapLayer(layer)
            QgsProject.instance().addMapLayer(new_layer, False)
            group.addLayer(new_layer)
            result_layer = new_layer
        else:
            # Se o campo já existe, apenas atualiza os valores e utiliza a própria camada
            layer.startEditing()
            for i, feature in enumerate(layer.getFeatures()):
                e_value = i + 1
                feature['sequencia'] = f'M{m_value}E{e_value}'
                geom = feature.geometry()
                if geom and not geom.isEmpty():
                    point = geom.asPoint()
                    feature['X'] = round(point.x(), 3)
                    feature['Y'] = round(point.y(), 3)
                layer.updateFeature(feature)
            layer.commitChanges()
            result_layer = layer

        self.mostrar_mensagem(f"Nova camada '{layer_name}' adicionada com coluna 'sequencia' como primeira coluna, sequência contínua e X/Y ajustados.", "Sucesso")
        self.update_list_widget_estruturas()

        return result_layer

    def mouse_moved(self, evt):
        """
        Exibe um crosshair apenas sobre a linha do suporte (Terreno Natural),
        garantindo que o cursor "grude" à linha quando dentro de uma tolerância.
        """
        # Converte o evento em coordenadas de cena
        if self.graphWidget.plotItem is None:
            return  # Segurança se o gráfico ainda não existe

        pos = evt  # evt já vem como QPointF
        if self.graphWidget.plotItem.sceneBoundingRect().contains(pos):
            mousePoint = self.graphWidget.plotItem.vb.mapSceneToView(pos)
            x = mousePoint.x()
            y = mousePoint.y()

            # Verifica se temos self.support_x / self.support_y
            if hasattr(self, 'support_x') and hasattr(self, 'support_y') and len(self.support_x) > 1:
                x_min = self.support_x[0]
                x_max = self.support_x[-1]
                if x_min <= x <= x_max:
                    # Interpola y_suporte (altura do Terreno Natural nesse x)
                    y_suporte = np.interp(x, self.support_x, self.support_y)

                    # Define tolerância (5% do range vertical, por exemplo)
                    y_range = max(self.support_y) - min(self.support_y)
                    tolerance = y_range * 0.05

                    if abs(y - y_suporte) <= tolerance:
                        # "Gruda" em (x, y_suporte)
                        self.vLine.setPos(x)
                        self.hLine.setPos(y_suporte)
                        self.vLine.show()
                        self.hLine.show()

                        self.coord_text.setFont(QFont('Arial', 9, QFont.Bold))
                        self.coord_text.setText(f"Elevação: {y_suporte:.2f} m\nDistância: {x:.2f} m")
                        self.coord_text.setPos(x, y_suporte)
                        self.coord_text.show()
                        return

            # Se chegou aqui, ou não há suporte_x/suporte_y, ou mouse está fora do range
            self.vLine.hide()
            self.hLine.hide()
            self.coord_text.hide()
        else:
            # Fora do gráfico
            self.vLine.hide()
            self.hLine.hide()
            self.coord_text.hide()

    def on_listwidget_selection_changed(self):
        """
        Quando a seleção no listWidget_Lista mudar,
        carregamos a camada correspondente no grupo 'Estruturas'
        e atualizamos o gráfico certo:
          - Se comboBoxRaster tiver camada, chamamos update_support_graph()
          - Senão, chamamos update_graph()
        """
        selected_items = self.listWidget_Lista.selectedItems()
        if not selected_items:
            self.current_estruturas_layer = None
            self.graphWidget.clear()  # ou self.reset_graph()
            return

        layer_name = selected_items[0].text()
        
        root = QgsProject.instance().layerTreeRoot()
        grupo_estruturas = None
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup) and child.name() == "Estruturas":
                grupo_estruturas = child
                break

        if not grupo_estruturas:
            self.current_estruturas_layer = None
            self.graphWidget.clear()
            return

        found_layer = None
        for child in grupo_estruturas.children():
            if isinstance(child, QgsLayerTreeLayer):
                lyr = child.layer()
                if lyr and lyr.name() == layer_name:
                    found_layer = lyr
                    break

        self.current_estruturas_layer = found_layer

        if self.current_estruturas_layer:
            raster_layer_id = self.comboBoxRaster.currentData()
            if raster_layer_id:
                # Se há raster selecionada, chamamos o gráfico de suporte
                self.update_support_graph()
            else:
                # Sem raster, chamamos o gráfico 'antigo'
                self.update_graph()

            # Se quiser, atualize as outras partes da interface
            self.update_tableView_2()
            self.update_listWidget_inc()
        else:
            self.current_estruturas_layer = None
            self.graphWidget.clear()

    def update_graph(self):
        """
        Atualiza o gráfico com os valores de Z, CotaEstaca, etc.,
        e desenha as linhas de diferença abaixo de CotaEstaca e Z,
        conforme doubleSpinBoxComp.

        Agora também inclui a linha "CotaEstaca + 10cm" em segmentos,
        dividida pelo spinBoxQ e com espaços (gaps) de 5 cm entre eles.
        """
        self.graphWidget.clear()

        lyr = self.current_estruturas_layer
        if not lyr:
            return

        field_names = [f.name() for f in lyr.fields()]
        # Verifica se há campos necessários
        if not all(fname in field_names for fname in ["X", "Y", "Z", "CotaEstaca", "AlturaEstaca"]):
            return

        feats = list(lyr.getFeatures())

        # Ordenação pela 'sequencia', se existir
        if "sequencia" in field_names:
            def get_seq_num(f):
                val = f["sequencia"]
                try:
                    idxE = val.index("E")
                    return int(val[idxE + 1:])
                except:
                    return f.id()
            feats.sort(key=get_seq_num)
        else:
            feats.sort(key=lambda f: f.id())

        # Variáveis de controle
        dist_acum = 0.0
        prev_x = None

        # Arrays para plotar Z, CotaEstaca
        x_vals_z = []
        y_vals_z = []
        x_vals_cota = []
        y_vals_cota = []

        # Arrays para as linhas verticais (dentro/fora do limite de AlturaEstaca)
        inrange_x = []
        inrange_y = []
        outrange_x = []
        outrange_y = []

        # Arrays para a linha vermelha (abaixo de CotaEstaca): (compValue - cota_)
        comp_x = []
        comp_y = []

        # Arrays para a linha magenta (abaixo de Z): (compValue - AlturaEstaca)
        magenta_x = []
        magenta_y = []

        # Parâmetros para saber se a AlturaEstaca está em intervalo
        padraoValue = self.doubleSpinBoxPadrao.value()
        variaValue = self.doubleSpinBoxVaria.value()
        lower_lim = padraoValue - variaValue
        upper_lim = padraoValue + variaValue

        # Valor que queremos comparar: doubleSpinBoxComp
        compValue = self.doubleSpinBoxComp.value()

        for f in feats:
            geom = f.geometry()
            if geom and not geom.isEmpty():
                pt = geom.asPoint()
                if prev_x is not None:
                    dist_acum += math.hypot(pt.x() - prev_x.x(), pt.y() - prev_x.y())
                else:
                    dist_acum = 0.0
                prev_x = pt

                z_ = f["Z"]
                cota_ = f["CotaEstaca"]
                alt_ = f["AlturaEstaca"]  # alt_ = cota_ - z_

                # Armazena para plotar Z e CotaEstaca
                x_vals_z.append(dist_acum)
                y_vals_z.append(z_)

                x_vals_cota.append(dist_acum)
                y_vals_cota.append(cota_)

                # Verifica se AlturaEstaca está dentro ou fora do intervalo
                if lower_lim <= alt_ <= upper_lim:
                    # Se estiver DENTRO do intervalo, plotamos em azul
                    inrange_x.extend([dist_acum, dist_acum, np.nan])
                    inrange_y.extend([z_, cota_, np.nan])
                else:
                    # Se estiver FORA do intervalo, plotamos em vermelho
                    outrange_x.extend([dist_acum, dist_acum, np.nan])
                    outrange_y.extend([z_, cota_, np.nan])

                # Calcula a diferença para CotaEstaca (linha vermelha abaixo de CotaEstaca)
                diff_cota = compValue - cota_
                if diff_cota > 0:
                    comp_x.extend([dist_acum, dist_acum, np.nan])
                    comp_y.extend([cota_, cota_ - diff_cota, np.nan])

                # Calcula a diferença para Z (linha magenta abaixo de Z) = compValue - AlturaEstaca
                diff_magenta = compValue - alt_
                if diff_magenta > 0:
                    magenta_x.extend([dist_acum, dist_acum, np.nan])
                    magenta_y.extend([z_, z_ - diff_magenta, np.nan])

        # === Plot das séries principais ===

        # Plot Z em laranja
        pen_z = pg.mkPen(color='orange', width=2)
        self.graphWidget.plot(x_vals_z, y_vals_z, pen=pen_z, symbol='o', symbolSize=6, name="Z")

        # Plot CotaEstaca em prata
        pen_cota = pg.mkPen(color='silver', width=3)
        self.graphWidget.plot(x_vals_cota, y_vals_cota, pen=pen_cota, symbol='x', symbolSize=6, name="CotaEstaca")

        # Plot das linhas verticais “in range” (azuis)
        pen_inrange = pg.mkPen(color='blue', width=3, style=Qt.DashLine)
        self.graphWidget.plot(inrange_x, inrange_y, pen=pen_inrange, name="AlturaEstaca (Dentro)")

        # Plot das linhas verticais “out range” (vermelhas)
        pen_outrange = pg.mkPen(color='red', width=3, style=Qt.DashLine)
        self.graphWidget.plot(outrange_x, outrange_y, pen=pen_outrange, name="AlturaEstaca (Fora)")

        # # Plot das linhas verticais da diferença (compValue - CotaEstaca)
        # if comp_x:
            # pen_comp = pg.mkPen(color='darkRed', width=2)
            # self.graphWidget.plot(comp_x, comp_y, pen=pen_comp, name="Diferença (Comp - Cota)")

        # Plot das linhas verticais magenta (compValue - AlturaEstaca), abaixo de Z
        if magenta_x:
            pen_magenta = pg.mkPen(color='magenta', width=6)
            self.graphWidget.plot(magenta_x, magenta_y, pen=pen_magenta, name="Estaca Aterrada")

        # === Criando a segunda linha paralela, 10 cm acima, com segmentos ===
        y_vals_cota2 = [valor + 0.10 for valor in y_vals_cota]

        # Lê o número de segmentos a partir do spinBoxQ
        Q = int(self.spinBoxQ.value())  
        if Q < 1:
            Q = 1

        # Define o 1º e o último X do array para a extensão horizontal
        x_start = x_vals_cota[0]
        x_end   = x_vals_cota[-1]
        total_length = x_end - x_start

        # Gap (espaço) de 5 cm -> 0.05 m
        gap = 0.05

        # Se houver mais de 1 segmento, reduz o comprimento desenhável
        if Q > 1:
            drawn_length = total_length - (Q - 1) * gap
            if drawn_length < 0:  # caso Q seja enorme
                drawn_length = 0
        else:
            drawn_length = total_length

        segment_length = drawn_length / Q if Q else 0

        seg_x = []
        seg_y = []

        # Vamos interpolar, pois x_seg_start / x_seg_end podem não estar exatamente em x_vals_cota
        for i in range(Q):
            x_seg_start = x_start + i * (segment_length + gap)
            x_seg_end   = x_seg_start + segment_length

            # Interpola valores de Y
            y_seg_start = np.interp(x_seg_start, x_vals_cota, y_vals_cota2)
            y_seg_end   = np.interp(x_seg_end,   x_vals_cota, y_vals_cota2)

            # Adiciona [início, fim, np.nan] para "quebrar" a linha
            seg_x.extend([x_seg_start, x_seg_end, np.nan])
            seg_y.extend([y_seg_start, y_seg_end, np.nan])

        # Pen grosso, cor azul, extremidades quadradas
        pen_cota2 = pg.mkPen(color='blue', width=5, style=Qt.SolidLine)
        pen_cota2.setCapStyle(Qt.SquareCap)

        # Plota a linha segmentada
        self.graphWidget.plot(seg_x, seg_y, pen=pen_cota2, name="Módulos")

        # Ajuste automático de eixo
        self.graphWidget.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

    @staticmethod
    def calcular_inclinacao_media(x_vals, y_vals):
        """
        Calcula a inclinação média (em m/m) com base nos valores de x e y.
        Retorna a média dos incrementos (slopes) entre os pontos.
        """

        slopes = []
        for i in range(1, len(x_vals)):
            dx = x_vals[i] - x_vals[i - 1]
            if dx == 0:
                continue
            slope = (y_vals[i] - y_vals[i - 1]) / dx
            slopes.append(slope)
        if slopes:
            return np.mean(slopes)
        else:
            return 0.0

    def get_estacas_data(self, estacas_layer):
        """
        Obtém os dados da camada de estruturas (estacas) calculando a distância acumulada entre os pontos.
        Retorna uma lista de tuplas:
           (dist_acumulada, CotaEstaca, Z, AlturaEstaca, x, y)
        """
        features = list(estacas_layer.getFeatures())
        field_names = [f.name() for f in estacas_layer.fields()]

        # Ordena as feições: se houver o campo 'sequencia', usa-o; caso contrário, usa FID.
        if "sequencia" in field_names:
            def seq_key(f):
                try:
                    # Exemplo: "M1E3" -> 3
                    return int(f["sequencia"].split("E")[1])
                except Exception:
                    return f.id()
            features.sort(key=seq_key)
        else:
            features.sort(key=lambda f: f.id())

        data = []
        dist_acum = 0.0
        prev_point = None
        import math
        for f in features:
            pt = f.geometry().asPoint()
            if prev_point is not None:
                # Calcula a distância Euclidiana entre o ponto atual e o anterior
                dist_acum += math.hypot(pt.x() - prev_point.x(), pt.y() - prev_point.y())
            else:
                dist_acum = 0.0
            # Obtém os valores dos campos necessários
            try:
                cota_estaca = f["CotaEstaca"]
                z_value = f["Z"]
                altura_estaca = f["AlturaEstaca"]
            except KeyError:
                self.mostrar_mensagem("A camada de estruturas não possui os campos 'CotaEstaca', 'Z' ou 'AlturaEstaca'.", "Erro")
                return []
            data.append((dist_acum, cota_estaca, z_value, altura_estaca, pt.x(), pt.y()))
            prev_point = pt

        return data

    def plot_layers(self):
        """
        Coleta os dados da camada de estruturas selecionada e da respectiva camada de apoio,
        calcula a distância acumulada entre os pontos da camada de estruturas e plota o gráfico
        utilizando o Matplotlib.
        
        Essa função só é executada se houver uma camada raster selecionada no comboBoxRaster.
        """
        # Verifica se há uma camada raster selecionada
        raster_layer_id = self.comboBoxRaster.currentData()
        if not raster_layer_id:
            self.mostrar_mensagem("Nenhuma camada raster selecionada.", "Erro")
            return

        # Verifica se há uma camada de estruturas selecionada (no listWidget_Lista)
        if not self.current_estruturas_layer:
            self.mostrar_mensagem("Nenhuma camada de estruturas selecionada.", "Erro")
            return
        estacas_layer = self.current_estruturas_layer

        # Procura a camada de apoio correspondente (com o nome "<nome_estacas>_Suporte")
        support_layer = None
        if hasattr(self, "support_layers"):
            for lyr in self.support_layers:
                if lyr.name() == f"{estacas_layer.name()}_Suporte":
                    support_layer = lyr
                    break
        if not support_layer:
            self.mostrar_mensagem("Camada de pontos de apoio não encontrada.", "Erro")
            return

        # Obtém os dados da camada de estruturas (calculando dist_acumulada)
        estacas_data = self.get_estacas_data(estacas_layer)
        if not estacas_data:
            self.mostrar_mensagem("Nenhum dado encontrado na camada de estruturas.", "Erro")
            return
        estacas_data.sort(key=lambda x: x[0])
        estacas_distances, estacas_cortes, z_values, desnivels, x_coords, y_coords = zip(*estacas_data)

        # Obtém os dados da camada de apoio
        pontos_apoio_data = []
        for f in support_layer.getFeatures():
            try:
                acumula_dist = f["Acumula_dist"]
                znovo = f["Znovo"]
            except KeyError:
                self.mostrar_mensagem("A camada de apoio não possui os campos 'Acumula_dist' e 'Znovo'.", "Erro")
                return
            pontos_apoio_data.append((acumula_dist, znovo))
        if not pontos_apoio_data:
            self.mostrar_mensagem("Nenhum dado encontrado na camada de apoio.", "Erro")
            return

        pontos_apoio_data.sort(key=lambda x: x[0])
        apoio_distances, apoio_elevations = zip(*pontos_apoio_data)

        fig, ax = plt.subplots(figsize=(10, 6))
        fig.set_size_inches(15, 9)
        fig.subplots_adjust(left=0.08, right=0.98, bottom=0.12, top=0.9)

        # Determina limites de Y
        y_min0 = min(apoio_elevations) - 2
        y_min1 = min(min(estacas_cortes), y_min0) - 2
        y_max = max(max(estacas_cortes), max(apoio_elevations)) + 4
        ax.set_ylim(y_min1, y_max)

        # Ticks de 1 em 1 no eixo Y
        ax.yaxis.set_major_locator(plt.MultipleLocator(1))

        # Preenchendo a área abaixo da linha do terreno natural (apoio_elevations)
        ax.fill_between(apoio_distances, apoio_elevations, y_min0, color='lightgreen', alpha=0.5, hatch='***')

        # Desenha linhas verticais (exemplo: do eixo X até a CotaEstaca)
        ax.vlines(
            x=estacas_distances,
            ymin=0,
            ymax=estacas_cortes,
            colors='grey',
            linestyles='dashed',
            linewidth=0.5)

        # --- Cálculo de inclinações ---
        inclinacao_media_corte = self.calcular_inclinacao_media(estacas_distances, estacas_cortes)
        inclinacao_media_znovo = self.calcular_inclinacao_media(apoio_distances, apoio_elevations)

        # Adiciona textos das inclinações
        bbox_props = dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=1)
        ax.text(
            0.005, 1.016,
            f'Inclinação do Perfil: {inclinacao_media_corte * 100:.3f}%',
            transform=ax.transAxes,
            color='blue',
            bbox=bbox_props)

        ax.text(
            0.005, 1.06,
            f'Inclinação média do Terreno: {inclinacao_media_znovo * 100:.3f}%',
            transform=ax.transAxes,
            color='orange',
            bbox=bbox_props)

        # Interpolação dos valores de elevação do terreno natural para os pontos das estacas
        interp_apoio_elevations = np.interp(estacas_distances, apoio_distances, apoio_elevations)

        # Borda das linhas
        for xi, yi1, yi2 in zip(estacas_distances, estacas_cortes, interp_apoio_elevations):
            ax.vlines(xi, yi1, yi2, color='black', linewidth=4, alpha=0.8)

        # Linha interna
        for xi, yi1, yi2 in zip(estacas_distances, estacas_cortes, interp_apoio_elevations):
            ax.vlines(xi, yi1, yi2, color='silver', linewidth=2.5, alpha=1)

        # Define um afastamento para a barra de conexão das setas
        afastamento_barra = -0.15
        deslocamento_x = 0.75

        for xi, yi_estaca, yi_terreno, desnivel in zip(estacas_distances, estacas_cortes, interp_apoio_elevations, desnivels):
            # Desenhe a linha de dimensão vertical com setas em ambas as extremidades
            ax.annotate("",
                        xy=(xi, yi_terreno), xycoords='data',
                        xytext=(xi, yi_estaca), textcoords='data',
                        arrowprops=dict(arrowstyle="<->", lw=1.0, 
                                        connectionstyle=f"bar,fraction={afastamento_barra}", color='orange'))
            
            # Adicione o valor do desnível
            ax.text(xi + deslocamento_x, (yi_terreno + yi_estaca) / 2, f"{desnivel:.2f} m",
                    verticalalignment='center', horizontalalignment='left',
                    fontsize=8.5, fontstyle='italic', rotation=90, fontweight='bold', color='blue',
                    bbox=dict(boxstyle='round,pad=0.1', edgecolor='orange', facecolor="white"))

        # Interpola de novo se necessário (mas se já estiver salvo em interp_apoio_elevations, pode reutilizar)
        interp_apoio_elevations = np.interp(estacas_distances, apoio_distances, apoio_elevations)
        Altura_Estaca = self.doubleSpinBoxComp.value()
        
        afastamento_barra_value_below = 0.18
        deslocamento_x_value_below = 0.8
        
        for xi, yi1, des in zip(estacas_distances, interp_apoio_elevations, desnivels):
            y_bottom = yi1 - (Altura_Estaca - des)
            # Preencher a área simulando concreto
            ax.fill_between([xi - 0.15, xi + 0.15], [y_bottom, y_bottom], [yi1, yi1], 
                            facecolor='Ivory', hatch='ooo', edgecolor='DarkSlateBlue', alpha=0.8)

            # Calcule value_below
            value_below = Altura_Estaca - des

            # Desenhe a linha de dimensão vertical
            ax.annotate("",
                        xy=(xi, y_bottom), xycoords='data',
                        xytext=(xi, yi1), textcoords='data',
                        arrowprops=dict(arrowstyle="<->", lw=1, 
                                        connectionstyle=f"bar,fraction={afastamento_barra_value_below}", color='green'))

            # Texto do value_below
            ax.text(xi - deslocamento_x_value_below, (y_bottom + yi1) / 2, f"{value_below:.2f} m",
                    verticalalignment='center', horizontalalignment='right',
                    fontsize=8.5, fontstyle='italic', fontweight='bold', color='red', rotation=90, 
                    bbox=dict(boxstyle='round,pad=0.1', edgecolor='darkGreen', facecolor='white'))

        # Anotação da altura da estaca
        ax.annotate(f'Altura da Estaca: {Altura_Estaca:.1f} metros',
                    xy=(0.005, 0.82), xycoords='axes fraction', 
                    fontsize=8, fontweight='bold', color='blue', fontstyle='italic', 
                    bbox=dict(boxstyle='round,pad=0.2', edgecolor='CadetBlue', facecolor='white'))

        # Crie o array Slopes (cálculo de inclinações em % entre cada par de pontos consecutivos)
        Slopes = []
        for i in range(1, len(estacas_distances)):
            dx = estacas_distances[i] - estacas_distances[i - 1]
            dy = interp_apoio_elevations[i] - interp_apoio_elevations[i - 1]
            slope_percent = 0.0 if dx == 0 else (100.0 * dy / dx)
            Slopes.append(slope_percent)

        # Ajuste estes valores conforme necessário
        deslocamento_x_slope = -1.75  # Deslocamento horizontal para a anotação
        deslocamento_y_slope = 0.20   # Deslocamento vertical para a anotação

        for i, (xi, yi, slope) in enumerate(zip(estacas_distances[1:], interp_apoio_elevations[1:], Slopes), start=1):
            # pular a primeira estaca se quiser (i == 1 corresponde à segunda estaca)
            slope_text = f"{slope:.2f}%"
            ax.text(xi + deslocamento_x_slope, yi + deslocamento_y_slope, slope_text,
                    verticalalignment='top', horizontalalignment='center',
                    fontsize=6.5, color='purple', rotation=0, fontweight='bold', fontstyle='italic',
                    bbox=dict(boxstyle='round,pad=0.2', edgecolor='darkGreen', facecolor='white'))

            # Linha horizontal de referência
            ax.hlines(yi, xi - 2, xi + 0.5, color='purple', linestyles='dashed', linewidth=1)

        # Calcule a inclinação da linha "Perfil"
        perfil_slope = (estacas_cortes[-1] - estacas_cortes[0]) / (estacas_distances[-1] - estacas_distances[0])

        # Estenda as distâncias para a linha "Perfil"
        estacas_distances_perfil_extended = np.array([estacas_distances[0] - 1] + list(estacas_distances) + [estacas_distances[-1] + 1])

        # Calcule as novas elevações baseadas na inclinação
        estacas_cortes_perfil_extended = np.array([estacas_cortes[0] - perfil_slope] + 
                                                  list(estacas_cortes) + 
                                                  [estacas_cortes[-1] + perfil_slope])

        # Calcule a inclinação da linha "Placas"
        placas_slope = perfil_slope  # assumindo a mesma inclinação do perfil

        # Distâncias para a linha "Placas"
        estacas_distances_placas_extended = np.array([estacas_distances[0] - 0.8] + 
                                                     list(estacas_distances) + 
                                                     [estacas_distances[-1] + 0.8])

        # Linha "Perfil" (contorno grosso em preto)
        ax.plot(estacas_distances_perfil_extended, estacas_cortes_perfil_extended, 
                color='black', linewidth=5)
                
        # Linha "Perfil" (prata, um pouco mais fina por cima do contorno)
        ax.plot(estacas_distances_perfil_extended, estacas_cortes_perfil_extended,
                color='silver', linewidth=3.5)
                
        # Linha "Perfil" com marcadores apenas entre as extremidades
        ax.plot(estacas_distances_perfil_extended[1:-1], estacas_cortes_perfil_extended[1:-1],
                color='silver', marker='P', markersize=10, markeredgewidth=0.9, 
                markeredgecolor='gray', markerfacecolor='silver', linewidth=3.5, label='Perfil')

        # Linha "Placas" 0.05 m acima
        estacas_cortes_placas_extended = np.array([estacas_cortes[0] - placas_slope * 0.8 + 0.13] + 
                                                  [c + 0.13 for c in estacas_cortes] + 
                                                  [estacas_cortes[-1] + placas_slope * 0.8 + 0.13])

        # Plotar a linha "Placas" estendida (tracejada customizada)
        ax.plot(estacas_distances_placas_extended, estacas_cortes_placas_extended, 
                color='blue', linewidth=4.5, linestyle=(0, (9, 0.2)), label='Módulos')

        # Plotar a linha "Terreno Natural" (outra cor)
        ax.plot(apoio_distances, apoio_elevations, color='DarkGoldenRod', linewidth=1.5, label='Terreno Natural')

        # Configuração adicional do gráfico
        xlabel_text = 'Distância Acumulada (m)'
        xlabel = ax.text(0.5, -0.07, xlabel_text, ha='center', va='center', transform=ax.transAxes, fontsize=10)
        # Aplicando boxstyle ao rótulo do eixo x
        xlabel.set_bbox(dict(facecolor='blue', alpha=0.8, edgecolor='blue', boxstyle='darrow,pad=0.08'))

        # Texto para o rótulo do eixo y
        ylabel_text = 'Elevação (m)'
        ylabel = ax.text(-0.05, 0.5, ylabel_text, ha='center', va='center', transform=ax.transAxes, fontsize=13, rotation=90, weight='bold', fontstyle='italic')
        # Aplicando boxstyle ao rótulo do eixo y
        ylabel.set_bbox(dict(facecolor='lightblue', alpha=0.5, edgecolor='black', boxstyle='Round4,pad=0.25'))
        
        title_text = 'Perfil de Estrutura Solar'
        title = ax.text(0.5, 1.05, title_text, ha='center', va='center', transform=ax.transAxes, fontsize=12, weight='bold')
        title.set_bbox(dict(facecolor='cyan', alpha=0.5, edgecolor='blue', boxstyle='round4,pad=0.5'))

        # Mostra a legenda no canto superior esquerdo do gráfico
        ax.grid(axis='y', color='gray', alpha=0.5, linestyle='-', linewidth=0.4)

        # Definindo o novo título da janela
        plt.get_current_fig_manager().set_window_title("Gráfico de Estrutura Solar")

        # Cria os patches para a legenda (concreto, estaca, etc.)
        concrete_patch = mpatches.Patch(facecolor='Ivory', hatch='/ooo/', edgecolor='DarkSlateBlue', alpha=0.8, label='Concretagem')
        stake_patch = mpatches.Patch(facecolor='silver', edgecolor='grey', linewidth=1, hatch='--', label='Estaca')

        # Obtém os handles e labels atuais da legenda
        handles, labels = ax.get_legend_handles_labels()

        # Acrescenta os patches aos handles existentes
        handles.extend([concrete_patch, stake_patch])

        # Atualiza a legenda com os novos handles
        ax.legend(handles=handles)

        # Exemplo de uso:
        fig = plt.gcf()
        self.adicionar_rosa_dos_ventos(fig, x_coords, y_coords)

        # Chama a função para adicionar o logotipo ao gráfico
        self.adicionar_logo(fig)

        # Exemplo fictício de interseções do talude:
        talude_start_intersection = (estacas_distances[0] - 2, 0)  # ou None se não existir
        talude_end_intersection   = (estacas_distances[-1] + 2, 0) # ou None se não existir

        # ... finalizou toda a plotagem? Então agora chamamos a função.
        self.configurar_ticks_eixo_x(
            ax=ax,
            estacas_distances=estacas_distances,
            talude_start_intersection=talude_start_intersection,
            talude_end_intersection=talude_end_intersection,
            step=5)

        # Exibe o gráfico
        plt.show()

    def configurar_ticks_eixo_x(self, ax, estacas_distances, talude_start_intersection=None, talude_end_intersection=None, step=5):
        """
        Configura os rótulos do eixo X com:
          - Múltiplos de 'step' (default=5).
          - Valores das estacas (estacas_distances).
          - Pontos de interseção do talude, caso existam.
          - Formatação especial (negrito + itálico) nos rótulos especiais (estacas + interseções).
        """

        # Se houver interseções do talude, use-as; caso contrário, use bordas default
        if talude_start_intersection:
            x_mag_left = talude_start_intersection[0]
        else:
            x_mag_left = estacas_distances[0]

        if talude_end_intersection:
            x_mag_right = talude_end_intersection[0]
        else:
            x_mag_right = estacas_distances[-1]

        # 1) Crie uma lista de ticks de 'step' em 'step' metros
        xticks = list(np.arange(min(estacas_distances), max(estacas_distances) + step, step))

        # 2) Adicione pontos especiais (magenta/interseções e distâncias das estacas)
        pontos_especiais = [x_mag_left, x_mag_right] + list(estacas_distances)
        for xi in pontos_especiais:
            if xi not in xticks:
                xticks.append(xi)

        # Ordene
        xticks.sort()

        # 3) Formate os rótulos
        formatted_labels = []
        for tick in xticks:
            if tick in [x_mag_left, x_mag_right]:
                label_str = f"{tick:.1f}"  # com 1 casa decimal
            elif tick in estacas_distances:
                label_str = f"{tick:.1f}"
            else:
                # para os múltiplos de step, formata como int se for inteiro
                label_str = f"{int(tick)}" if float(tick).is_integer() else f"{tick:.1f}"
            formatted_labels.append(label_str)

        # 4) Aplica no eixo
        ax.set_xticks(xticks)
        ax.set_xticklabels(formatted_labels, fontsize=7)

        # 5) Aplica estilos especiais aos rótulos 'especiais'
        for i, label in enumerate(ax.get_xticklabels()):
            tick_value = xticks[i]
            if tick_value in pontos_especiais:
                label.set_fontweight('bold')
                label.set_fontstyle('italic')

    def adicionar_rosa_dos_ventos(self, fig, x_coords, y_coords):
        """
        Adiciona uma rosa dos ventos ao gráfico.

        Parameters:
        - fig: a figura na qual a rosa dos ventos será desenhada.
        - x_coords: lista de coordenadas x do perfil.
        - y_coords: lista de coordenadas y do perfil.
        """
        # Defina o tamanho e a posição da Rosa dos Ventos
        radius = 0.035  # Raio do círculo (em unidades de figura)
        center = (0.50, 0.82)  # Posição do centro do círculo (em unidades de figura)

        # Desenha um círculo para a rosa dos ventos
        circle = Circle(center, radius, transform=fig.transFigure, edgecolor="black", facecolor="none", clip_on=False)
        fig.add_artist(circle)

        # Desenha linhas com setas para indicar as direções
        for angle in [0, 90, 180, 270]:
            x_start = center[0]
            y_start = center[1]
            x_end = center[0] + 1.0 * radius * np.cos(np.radians(angle))
            y_end = center[1] + 1.0 * radius * np.sin(np.radians(angle))

            # Adiciona uma seta ao final da linha
            arrowprops = dict(arrowstyle="->", lw=1.5, mutation_scale=10)
            fig.add_artist(mpatches.FancyArrowPatch((x_start, y_start), (x_end, y_end),
                                                   connectionstyle="arc3,rad=0.0",
                                                   transform=fig.transFigure, clip_on=False, **arrowprops))

        # Calcula o ângulo com base nas coordenadas fornecidas
        delta_x = x_coords[-1] - x_coords[0]
        delta_y = y_coords[-1] - y_coords[0]
        angle = math.atan2(delta_y, delta_x)

        # Converte o ângulo de radianos para graus para facilitar a interpretação
        angle_degrees = math.degrees(angle)

        # Determina a direção principal com base no ângulo
        if -45 < angle_degrees <= 45:
            directions = ["E", "N", "W", "S"]
        elif 45 < angle_degrees <= 135:
            directions = ["N", "W", "S", "E"]
        elif -135 < angle_degrees <= -45:
            directions = ["S", "E", "N", "W"]
        else:
            directions = ["W", "N", "E", "S"]

        # Adiciona rótulos para as direções
        label_distance = 1.4  # Ajuste essa variável para mudar a distância dos rótulos ao círculo
        for i, label in enumerate(directions):
            angle = 90 * i
            x = center[0] + label_distance * radius * np.cos(np.radians(angle))
            y = center[1] + label_distance * radius * np.sin(np.radians(angle))
            fig.text(x, y, label, ha="center", va="center")

    def adicionar_logo(self, fig):
        """
        Função para adicionar o logotipo ao gráfico do QGis, mantendo a transparência do fundo e adicionando contorno.
        
        Parameters:
        - fig: O objeto Figure do matplotlib onde o logotipo será adicionado.
        """
        try:
            icon_path_projetos = os.path.join(self.plugin_dir, 'icones', 'Qgis.png')
            logo = plt.imread(icon_path_projetos)  # 🔹 Carrega mantendo a transparência

            # Tamanho máximo para o logo
            max_width, max_height = 150, 75
            img_height, img_width = logo.shape[:2]
            scale_factor = min(max_width / img_width, max_height / img_height)

            # Criar a imagem com zoom proporcional
            imagebox = OffsetImage(logo, zoom=scale_factor)

            # 🔹 Define **fundo transparente** e **contorno preto**
            bboxprops = dict(boxstyle="round,pad=0.5", facecolor="none", edgecolor="blue", linewidth=1.0)

            # 🔹 Posicionamento dentro do gráfico no canto superior esquerdo
            ab = AnnotationBbox(
                imagebox,
                (0.085, 0.89),  # Ajuste fino da posição
                frameon=True,  # 🔹 Mantemos a moldura ativa
                xycoords='figure fraction',
                box_alignment=(0, 1),
                bboxprops=bboxprops  # 🔹 Aplicamos contorno preto ao redor do logo
            )

            ax = plt.gca()  # Obtém o eixo atual
            ax.add_artist(ab)  # Adiciona a imagem ao gráfico

        except Exception as e:
            print(f"Erro ao carregar o logotipo: {e}")

    def atualizar_estado_botao(self):
        """
        Habilita o botão pushButtonMat apenas se:
        - Uma camada estiver selecionada no listWidget_Lista
        - Uma camada raster estiver selecionada no comboBoxRaster
        """
        camada_selecionada = self.listWidget_Lista.selectedItems()  # Verifica se há uma camada selecionada
        camada_raster = self.comboBoxRaster.currentData()  # Verifica se há uma camada raster selecionada

        # Habilita o botão se ambos os critérios forem atendidos
        if camada_selecionada and camada_raster:
            self.pushButtonMat.setEnabled(True)
        else:
            self.pushButtonMat.setEnabled(False)

    def atualizar_estado_botoes_calcular(self):
        """
        Habilita ou desabilita ambos os botões (pushButtonCalcular e pushButtonCalculaTudo)
        de acordo com a quantidade de feições selecionadas na tabela.
        """
        # Usa selectedRows() para obter as linhas únicas selecionadas
        linhas_selecionadas = self.tableWidget_Dados1.selectionModel().selectedRows()
        
        # Se houver pelo menos 2 linhas selecionadas, ativa ambos os botões
        if len(linhas_selecionadas) >= 2:
            self.pushButtonCalcular.setEnabled(True)
            self.pushButtonCalculaTudo.setEnabled(True)
        else:
            self.pushButtonCalcular.setEnabled(False)
            self.pushButtonCalculaTudo.setEnabled(False)

    def update_scroll_area_dados(self):
        """
        Atualiza o scrollAreaDADOS exibindo a tabela de atributos de todas as camadas de suporte
        armazenadas em self.support_layers, de forma incremental.

        Cada widget (GroupBox com a tabela) permanece até que sua camada principal (conforme listWidget_Lista)
        seja removida.
        """
        # Certifica-se de que o container e o dicionário de widgets já foram criados.
        if not hasattr(self, 'dados_container'):
            self.dados_container = QWidget()
            self.dados_layout = QVBoxLayout(self.dados_container)
            self.scrollAreaDADOS.setWidget(self.dados_container)
            self.scrollAreaDADOS.setWidgetResizable(True)
        if not hasattr(self, 'support_widgets'):
            self.support_widgets = {}  # chave: layer.id(), valor: QGroupBox

        # Obtenha os nomes das camadas principais ativas no listWidget_Lista.
        active_main_names = {self.listWidget_Lista.item(i).text() for i in range(self.listWidget_Lista.count())}

        # --- Remoção dos widgets cujas camadas principais não estão mais ativas ---
        # Itera sobre os widgets já criados; se o nome da camada principal (extraído do título)
        # não estiver na lista ativa, remove o widget.
        for layer_id, widget in list(self.support_widgets.items()):
            # Supondo que o título do QGroupBox seja algo como "NomeDaCamada_Suporte"
            support_title = widget.title()  # Título do group box
            # Se o título terminar com "_Suporte", extraímos o nome principal:
            if support_title.endswith("_Suporte"):
                main_name = support_title.replace("_Suporte", "")
            else:
                main_name = support_title
            if main_name not in active_main_names:
                self.dados_layout.removeWidget(widget)
                widget.deleteLater()
                del self.support_widgets[layer_id]

        # --- Função auxiliar para criar a tabela de atributos de uma camada de suporte ---
        def create_support_table(layer):
            table = QTableWidget()
            fields = layer.fields()
            features = list(layer.getFeatures())
            table.setRowCount(len(fields))
            # A primeira coluna é para os nomes dos atributos, as demais para cada feição
            table.setColumnCount(len(features) + 1)
            headers = ["Atributo"] + [f"Feição {i+1}" for i in range(len(features))]
            table.setHorizontalHeaderLabels(headers)
            table.setVerticalHeaderLabels([""] * len(fields))
            # Preenche a primeira coluna com os nomes dos atributos
            for row, field in enumerate(fields):
                item = QTableWidgetItem(field.name())
                item.setFlags(Qt.ItemIsEnabled)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 0, item)
            # Preenche as demais colunas com os valores de cada feição
            for col, feat in enumerate(features):
                for row, field in enumerate(fields):
                    valor = feat[field.name()]
                    item = QTableWidgetItem(str(valor))
                    item.setFlags(Qt.ItemIsEnabled)
                    item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(row, col + 1, item)
            table.resizeColumnsToContents()
            table.resizeRowsToContents()
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            return table

        # --- Adiciona novos widgets para as camadas de suporte que ainda não possuem widget ---
        for layer in self.support_layers:
            layer_id = layer.id()
            # Considerando que o nome da camada de suporte tenha o padrão "NomeDaCamada_Suporte"
            if layer.name().endswith("_Suporte"):
                main_name = layer.name().replace("_Suporte", "")
            else:
                main_name = layer.name()
            # Só cria o widget se a camada principal estiver ativa
            if main_name in active_main_names:
                if layer_id not in self.support_widgets:
                    group_box = QGroupBox(layer.name())
                    layout = QVBoxLayout(group_box)
                    table = create_support_table(layer)
                    layout.addWidget(table)
                    self.dados_layout.addWidget(group_box)
                    self.support_widgets[layer_id] = group_box

    def update_support_graph(self):
        """
        Atualiza o gráfico para *apenas* a camada de suporte correspondente
        à camada de estruturas atualmente selecionada (self.current_estruturas_layer),
        ignorando as demais.
        """
        # 1) Verifica se há camada raster selecionada
        raster_layer_id = self.comboBoxRaster.currentData()
        if not raster_layer_id:
            self.update_graph()
            return

        # 2) Verifica se a camada de estruturas está definida
        if not self.current_estruturas_layer:
            self.mostrar_mensagem("Nenhuma camada de estruturas selecionada.", "Erro")
            return

        estacas_layer = self.current_estruturas_layer
        struct_layer_name = estacas_layer.name()

        # 3) Constrói o nome esperado da camada de suporte
        expected_support_name = struct_layer_name + "_Suporte"

        # 4) Localiza no self.support_layers a camada que tenha esse nome
        support_layer = None
        print("Camadas de suporte disponíveis:")
        for lyr in self.support_layers:
            print(f"- {lyr.name()}")
            if lyr.name() == expected_support_name:
                support_layer = lyr
                break

        if not support_layer:
            self.mostrar_mensagem(
                f"Nenhuma camada de suporte '{expected_support_name}' foi encontrada para a camada '{struct_layer_name}'.",
                "Erro")
            return

        # 5) Monta dados do Perfil (dist_e, cota_e) a partir da camada de estacas
        feats_estacas = list(estacas_layer.getFeatures())
        if not feats_estacas:
            self.mostrar_mensagem("A camada de estruturas não possui feições.", "Erro")
            return

        field_names = [f.name() for f in estacas_layer.fields()]
        if "sequencia" in field_names:
            def get_seq(f):
                try:
                    return int(f["sequencia"].split("E")[1])
                except:
                    return f.id()
            feats_estacas.sort(key=get_seq)
        else:
            feats_estacas.sort(key=lambda f: f.id())

        dist_e = []
        cota_e = []
        dist_acum = 0.0
        prev_pt = None

        for f in feats_estacas:
            geom = f.geometry()
            if geom and not geom.isEmpty():
                pt = geom.asPoint()
                if prev_pt is not None:
                    dist_acum += math.hypot(pt.x() - prev_pt.x(), pt.y() - prev_pt.y())
                prev_pt = pt
                cota = f["CotaEstaca"] if "CotaEstaca" in field_names else 0
                dist_e.append(dist_acum)
                cota_e.append(cota)

        if not dist_e:
            self.mostrar_mensagem("Não há dados de perfil para plotar.", "Erro")
            return

        # 6) Lê parâmetros dos spinBoxes
        padraoValue = self.doubleSpinBoxPadrao.value()
        variaValue = self.doubleSpinBoxVaria.value()
        lower_lim = padraoValue - variaValue
        upper_lim = padraoValue + variaValue
        compValue = self.doubleSpinBoxComp.value()

        # 7) Limpa o gráfico e plota o Perfil (CotaEstaca) em prata
        self.graphWidget.clear()
        self.graphWidget.plot(
            dist_e, cota_e,
            pen=pg.mkPen(color='silver', width=2),
            symbol='x', symbolSize=8, symbolBrush='blue',
            name="Perfil")

        # 8) Agora obtemos dist_s, z_s APENAS da camada de suporte desse layer
        feats_support = list(support_layer.getFeatures())
        if not feats_support:
            self.mostrar_mensagem(f"A camada de suporte '{expected_support_name}' não possui feições.", "Erro")
            return

        sup_field_names = [fld.name() for fld in support_layer.fields()]

        # Ordena pelas distâncias, se existir "Acumula_dist"
        if "Acumula_dist" in sup_field_names:
            feats_support.sort(key=lambda sf: sf["Acumula_dist"])
        else:
            feats_support.sort(key=lambda sf: sf.id())

        dist_s = []
        z_s = []
        import numpy as np

        for sf in feats_support:
            if "Acumula_dist" in sup_field_names and "Znovo" in sup_field_names:
                dist_s.append(sf["Acumula_dist"])
                z_s.append(sf["Znovo"])

        if not dist_s:
            self.mostrar_mensagem(
                f"Camada {support_layer.name()} não possui valores 'Acumula_dist' e 'Znovo' válidos.","Erro")
            return

        # 8a) Plota a linha do terreno (vermelho)
        self.graphWidget.plot(
            dist_s, z_s,
            pen=pg.mkPen(color='red', width=2),
            symbol=None,
            name=f"Terreno Natural")

        # 8b) Constrói as linhas verticais in range / out range específicas desse suporte
        inrange_x = []
        inrange_y = []
        outrange_x = []
        outrange_y = []
        comp_x = []
        comp_y = []
        magenta_x = []
        magenta_y = []

        for i in range(len(dist_e)):
            x_val = dist_e[i]
            cota_val = cota_e[i]
            
            # Interpola no dist_s para obter z_val
            z_val = np.interp(x_val, dist_s, z_s)
            alt_val = cota_val - z_val

            # in range vs out range (corrigido com tolerância)
            if lower_lim - 1e-6 <= alt_val <= upper_lim + 1e-6:
                inrange_x.extend([x_val, x_val, np.nan])
                inrange_y.extend([z_val, cota_val, np.nan])
            else:
                outrange_x.extend([x_val, x_val, np.nan])
                outrange_y.extend([z_val, cota_val, np.nan])

            # Diferença (compValue - CotaEstaca)
            diff_cota = compValue - cota_val
            if diff_cota > 0:
                comp_x.extend([x_val, x_val, np.nan])
                comp_y.extend([cota_val, cota_val - diff_cota, np.nan])

            # Diferença (compValue - AlturaEstaca) -> compValue - (cota - z)
            diff_alt = compValue - alt_val
            if diff_alt > 0:
                magenta_x.extend([x_val, x_val, np.nan])
                magenta_y.extend([z_val, z_val - diff_alt, np.nan])

        pen_inrange = pg.mkPen(color='blue', width=3, style=Qt.DashLine)
        self.graphWidget.plot(
            inrange_x, inrange_y,
            pen=pen_inrange,
            name=f"AlturaEstaca (Dentro)")

        pen_outrange = pg.mkPen(color='red', width=3, style=Qt.DashLine)
        self.graphWidget.plot(
            outrange_x, outrange_y,
            pen=pen_outrange,
            name=f"AlturaEstaca (Fora)")

        if comp_x:
            pen_comp = pg.mkPen(color='darkRed', width=2)
            self.graphWidget.plot(
                comp_x, comp_y,
                pen=pen_comp,
                name=f"Dif (Comp - Cota)")

        if magenta_x:
            pen_magenta = pg.mkPen(color='magenta', width=6)
            self.graphWidget.plot(
                magenta_x, magenta_y,
                pen=pen_magenta,
                name=f"Estaca Aterrada")

        # 8c) Definimos self.support_x e self.support_y para o crosshair:
        self.support_x = dist_s
        self.support_y = z_s

        # 9) Linha "Perfil + 10cm"
        perfil_plus10 = [valor + 0.10 for valor in cota_e]
        Q = int(self.spinBoxQ.value())
        if Q < 1:
            Q = 1

        x_start = dist_e[0]
        x_end = dist_e[-1]
        total_length = x_end - x_start
        gap = 0.05

        if Q > 1:
            drawn_length = total_length - (Q - 1) * gap
            if drawn_length < 0:
                drawn_length = 0
        else:
            drawn_length = total_length

        segment_length = drawn_length / Q if Q else 0
        seg_x = []
        seg_y = []

        for i in range(Q):
            seg_x_start = x_start + i * (segment_length + gap)
            seg_x_end = seg_x_start + segment_length
            y_seg_start = np.interp(seg_x_start, dist_e, perfil_plus10)
            y_seg_end = np.interp(seg_x_end, dist_e, perfil_plus10)
            seg_x.extend([seg_x_start, seg_x_end, np.nan])
            seg_y.extend([y_seg_start, y_seg_end, np.nan])

        pen_perfil_plus10 = pg.mkPen(color='blue', width=5, style=Qt.SolidLine)
        pen_perfil_plus10.setCapStyle(Qt.SquareCap)
        self.graphWidget.plot(
            seg_x, seg_y,
            pen=pen_perfil_plus10,
            name="Módulos" )

        # 10) Ajuste automático
        self.graphWidget.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

        # 11) Crosshair
        self.vLine = pg.InfiniteLine(angle=90, pen=pg.mkPen(color='green', width=1))
        self.hLine = pg.InfiniteLine(angle=0, pen=pg.mkPen(color='green', width=1))
        self.graphWidget.addItem(self.vLine, ignoreBounds=True)
        self.graphWidget.addItem(self.hLine, ignoreBounds=True)
        self.vLine.hide()
        self.hLine.hide()

        self.coord_text = pg.TextItem("", anchor=(0,1), color='white')
        self.graphWidget.addItem(self.coord_text)
        self.coord_text.hide()

        # Desconecta se já estava conectado, para evitar duplicações
        try:
            self.graphWidget.scene().sigMouseMoved.disconnect(self.mouse_moved)
        except Exception:
            pass

        self.graphWidget.scene().sigMouseMoved.connect(self.mouse_moved)

    def calcular_tudo(self):
        """
        Executa o mesmo procedimento do 'calcular()', porém para TODAS as feições
        da camada de pontos selecionada no comboBoxPontos, dividindo-as em blocos
        de tamanho = spinBoxSelec.value().

        Para cada bloco (chunk):
          - Interpola do primeiro ao último ponto do bloco,
          - Cria a camada resultante (M1, M2, M3, etc.),
          - Se houver raster selecionado, cria a camada de suporte.
        """

        # Verifica se existe alguma camada de pontos selecionada no comboBox
        layer_id = self.comboBoxPontos.currentData()
        point_layer = QgsProject.instance().mapLayer(layer_id)
        if not point_layer or not isinstance(point_layer, QgsVectorLayer):
            self.mostrar_mensagem("Nenhuma camada de pontos válida foi selecionada.", "Erro")
            return

        # Verifica se a camada é de pontos
        if point_layer.geometryType() != QgsWkbTypes.PointGeometry:
            self.mostrar_mensagem("A camada selecionada não é de pontos.", "Erro")
            return

        # Lê o tamanho do bloco no spinBoxSelec
        chunk_size = self.spinBoxSelec.value()
        if chunk_size < 2:
            self.mostrar_mensagem("Para criar camadas por bloco, selecione no mínimo 2 no spinBoxSelec.", "Erro")
            return

        # Obtém o doubleSpinBox_1 e doubleSpinBox_2 para os ajustes de cota
        delta1 = self.doubleSpinBox_1.value()  
        delta2 = self.doubleSpinBox_2.value()  

        # Verifica se há camada raster selecionada
        raster_layer_id = self.comboBoxRaster.currentData()
        raster_layer = QgsProject.instance().mapLayer(raster_layer_id) if raster_layer_id else None
        raster_name = raster_layer.name() if raster_layer else ""

        # 1) Obter **todas** as feições da camada, mantendo a mesma ordem que você usa na tabela.
        #    (se sua tabela ordena por FID ou por uma lógica de "feature_ids", faça igual aqui)
        all_features = list(point_layer.getFeatures())

        # Se quiser ordenar por FID, por exemplo:
        # all_features.sort(key=lambda f: f.id())

        # Se quiser ordenar por uma coluna "sequencia", faça algo como:
        # idx_seq = point_layer.fields().indexFromName("sequencia")
        # if idx_seq >= 0:
        #     def get_seq_num(feat):
        #         val = feat["sequencia"]
        #         # Tenta extrair o número após "E"
        #         try:
        #             idxE = val.index("E")
        #             return int(val[idxE+1:])
        #         except:
        #             return feat.id()
        #     all_features.sort(key=get_seq_num)
        # else:
        #     all_features.sort(key=lambda f: f.id())

        total_feats = len(all_features)
        if total_feats < 2:
            self.mostrar_mensagem("A camada de pontos não possui feições suficientes.", "Erro")
            return

        # Calcula quantos blocos teremos
        # Ex: se total_feats=37 e chunk_size=10, teremos 4 blocos (10,10,10,7)
        import math
        num_chunks = math.ceil(total_feats / chunk_size)

        # Exibe uma mensagem para informar quantas camadas serão criadas
        self.mostrar_mensagem(
            f"Serão criadas {num_chunks} novas camadas, cada bloco terá até {chunk_size} feições.",
            "Sucesso",
            duracao=2
        )

        # 2) Itera sobre cada bloco e cria a camada resultante
        start_index = 0
        block_number = 1
        while start_index < total_feats:
            end_index = start_index + chunk_size
            block_feats = all_features[start_index:end_index]  # Sublista com no máximo chunk_size feições

            # Monta os pontos (x, y, z)
            point_list = []
            for feat in block_feats:
                geom = feat.geometry()
                if geom.isEmpty():
                    continue
                pt = geom.asPoint()
                x, y = pt.x(), pt.y()

                # Se há raster, obtem Z do raster
                if raster_layer:
                    z_value = self.get_z_from_raster(raster_layer, x, y)
                    if z_value is None:
                        # Caso não tenha valor de raster, assuma 0 ou ignore a feição
                        z_value = 0
                else:
                    # Se não há raster, tenta usar um campo 'Z' (se existir na camada)
                    idx_z = point_layer.fields().indexFromName('Z')
                    if idx_z >= 0:
                        z_value = feat[idx_z]
                        if z_value is None:
                            z_value = 0
                    else:
                        z_value = 0

                point_list.append((x, y, z_value))

            if len(point_list) < 2:
                # Para interpolar, precisamos de pelo menos 2 pontos
                start_index = end_index
                block_number += 1
                continue

            # Interpolação linear da CotaEstaca/AlturaEstaca do primeiro ao último
            x0, y0, z0 = point_list[0]
            x1, y1, z1 = point_list[-1]

            cota_first = z0 + delta1
            cota_last  = z1 + delta2
            dist_total = math.sqrt((x1 - x0)**2 + (y1 - y0)**2)
            dc = cota_last - cota_first

            final_feats = []
            for (xx, yy, zz) in point_list:
                if dist_total > 0:
                    frac = math.sqrt((xx - x0)**2 + (yy - y0)**2) / dist_total
                else:
                    frac = 0.0
                cota_estaca = cota_first + dc * frac
                altura_estaca = cota_estaca - zz
                final_feats.append((
                    round(xx, 3),
                    round(yy, 3),
                    round(zz, 3),
                    round(cota_estaca, 3),
                    round(altura_estaca, 3)
                ))

            # Gera um nome para a camada, ex: M1_rasterName, M2_rasterName, etc.
            # Você pode usar a mesma lógica do generate_layer_name(), mas incrementando block_number.
            # Exemplo simples aqui:
            layer_name = f"M{block_number}"
            if raster_name:
                layer_name += f"_{raster_name}"

            # Cria a camada de memória com X,Y,Z,CotaEstaca,AlturaEstaca
            new_layer = self.create_point_layer(layer_name, final_feats)

            # Adiciona ao grupo 'Estruturas', garantindo criação do campo 'sequencia'
            final_layer = self.add_layer_to_group(new_layer, "Estruturas")

            # Aqui, configuramos os rótulos para a camada recém-criada:
            self.set_label_for_layer(final_layer)

            # Se houver raster, cria camada de suporte
            if raster_layer:
                self.create_support_points_layer(final_layer, raster_layer)

            # Incrementa para o próximo bloco
            start_index = end_index
            block_number += 1

        # No final, atualiza a listWidget_Lista, scroll e afins
        self.update_list_widget_estruturas()
        self.update_scroll_area_dados()

        # Mensagem final
        self.mostrar_mensagem("Processo concluído! Verifique as camadas criadas no grupo 'Estruturas'.", "Sucesso", 3)

    def set_label_for_layer(self, layer):
        """
        Configura rótulos e cores para a camada, exibindo:
          - 'sequencia' e 'AlturaEstaca' em duas linhas
          - Texto em negrito, maior
          - Posição à direita dos pontos, com deslocamento horizontal
          - Cor baseada na regra do update_tableView_2 (azul ou vermelho).
        """

        # 1) Obter limites da lógica de cor (update_tableView_2)
        padraoValue = self.doubleSpinBoxPadrao.value()
        variaValue  = self.doubleSpinBoxVaria.value()
        lower_lim = padraoValue - variaValue
        upper_lim = padraoValue + variaValue

        # 2) Expressão para cor: azul se dentro do intervalo; vermelho se fora

        color_expression = f"""
            CASE
                WHEN "AlturaEstaca" >= {lower_lim} AND "AlturaEstaca" <= {upper_lim}
                    THEN '0,0,255'
                ELSE
                    '255,0,0'
                END
        """

        # 3) Expressão de RÓTULO (duas linhas)

        label_expression = "\"sequencia\" || '\n' || \"AlturaEstaca\""

        # 4) Configurar estilo do texto (QFont + QgsTextFormat)

        text_format = QgsTextFormat()

        # # Negrito e tamanho maior
        # font = QFont("Arial", 15)    # 14 px pra ficar bem visível
        # font.setBold(True)           # Deixa em negrito
        # # Se quiser remover o itálico, comente a linha abaixo
        # font.setItalic(True)

        # text_format.setFont(font)
        # text_format.setSize(13)      # Também define tamanho via text_format

        # Buffer (fundo) branco ao redor das letras
        # buffer_settings = QgsTextBufferSettings()
        # buffer_settings.setEnabled(True)
        # buffer_settings.setColor(QColor(255, 255, 255))
        # buffer_settings.setSize(1)   # Espessura do "contorno" do texto
        # text_format.setBuffer(buffer_settings)

        # 5) Configurar PalLayerSettings
        pal_settings = QgsPalLayerSettings()
        pal_settings.enabled = True
        pal_settings.isExpression = True
        pal_settings.fieldName = label_expression  # expressão do rótulo
        pal_settings.format = text_format

        # Posição: usar OverPoint para rótulos de ponto
        pal_settings.placement = QgsPalLayerSettings.OverPoint

        # Quadrante: à direita
        # (Veja a documentação do enum LabelQuadrantPosition para outras opções)
        pal_settings.quadOffset = QgsPalLayerSettings.QuadrantRight

        # Em QGIS 3.30+, defina deslocamento via xOffset/yOffset:
        pal_settings.xOffset = 10  # Experimente valores maiores para notar claramente
        pal_settings.yOffset = 0
        pal_settings.offsetUnits = QgsUnitTypes.RenderPixels

        # Propriedades definidas por dados: cor do texto
        ddp = pal_settings.dataDefinedProperties()
        ddp.setProperty(QgsPalLayerSettings.Color, QgsProperty.fromExpression(color_expression))
        # Se quiser forçar um tamanho de fonte via expressão, pode usar:
        #   ddp.setProperty(QgsPalLayerSettings.Size, QgsProperty.fromValue(14))
        pal_settings.setDataDefinedProperties(ddp)

        # 6) Aplicar a rotulagem na camada
        layer.setLabelsEnabled(True)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(pal_settings))

        # 7) Ajustar cor das feições (pontos) via renderer
        renderer = layer.renderer()
        if renderer:
            symbol = renderer.symbol()
            if symbol and symbol.symbolLayerCount() > 0:
                sym_layer = symbol.symbolLayer(0)
                # Cor de preenchimento de cada ponto pela mesma expressão
                sym_layer.setDataDefinedProperty(
                    QgsSymbolLayer.PropertyFillColor,
                    QgsProperty.fromExpression(color_expression)
                )

        # 8) Forçar repaint e refrescar o mapa
        layer.triggerRepaint()
        try:
            iface.mapCanvas().refreshAllLayers()
        except Exception:
            pass

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

    def pushButtonExportarDXF_clicked(self):
        result = self.obter_camadas_e_caminho_dxf()
        if result:
            layers, caminho_arquivo = result
            self.exportar_camadas_para_dxf(layers, caminho_arquivo)

    def atualizar_estado_pushButtonExportarDXF(self):
        """
        Verifica se há alguma camada vetorial de pontos no grupo 'Estruturas'.
        Se existir ao menos uma, habilita o pushButtonExportarDXF; caso contrário, desabilita.
        """
        # Acessa o layer tree root
        root = QgsProject.instance().layerTreeRoot()

        grupo_estruturas = None
        # Localiza o grupo 'Estruturas'
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup) and child.name() == "Estruturas":
                grupo_estruturas = child
                break

        # Se não encontrou o grupo, desabilita o botão e retorna
        if not grupo_estruturas:
            self.pushButtonExportarDXF.setEnabled(False)
            return

        # Verifica se dentro do grupo existe alguma camada de pontos
        tem_camada_ponto = False
        for child in grupo_estruturas.children():
            if isinstance(child, QgsLayerTreeLayer):
                layer = child.layer()
                if (layer 
                    and layer.type() == QgsMapLayer.VectorLayer 
                    and layer.geometryType() == QgsWkbTypes.PointGeometry):
                    tem_camada_ponto = True
                    break

        # Habilita o botão se houver pelo menos 1 camada de pontos
        self.pushButtonExportarDXF.setEnabled(tem_camada_ponto)

    def obter_camadas_e_caminho_dxf(self):
        """
        Verifica se existe o grupo 'Estruturas' no projeto e obtém todas as camadas vetoriais (pontos) dentro dele.
        Em seguida, solicita ao usuário um caminho para salvar o arquivo DXF.
        Retorna uma tupla (layers, caminho_arquivo) ou None se ocorrer algum erro ou cancelamento.
        """
        # 1) Verificar se existe o grupo "Estruturas"
        root = QgsProject.instance().layerTreeRoot()
        grupo_estruturas = None
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup) and child.name() == "Estruturas":
                grupo_estruturas = child
                break
        if not grupo_estruturas:
            self.mostrar_mensagem("O grupo 'Estruturas' não foi encontrado no projeto.", "Erro")
            return None

        # 2) Obter todas as camadas (vetoriais) dentro do grupo "Estruturas"
        layers = []
        for child in grupo_estruturas.children():
            if isinstance(child, QgsLayerTreeLayer):
                layer = child.layer()
                # Consideramos apenas camadas de pontos
                if layer and layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PointGeometry:
                    layers.append(layer)
        if not layers:
            self.mostrar_mensagem("Nenhuma camada de pontos foi encontrada no grupo 'Estruturas'.", "Erro")
            return None

        # 3) Escolher local para salvar o DXF
        nome_padrao = "Estruturas"
        caminho_arquivo = self.escolher_local_para_salvar(nome_padrao, "DXF (*.dxf)")
        if not caminho_arquivo:
            return None  # Usuário cancelou

        return (layers, caminho_arquivo)

    def get_dxf_color(self, altura):
        """
        Determina a cor DXF com base no valor de AlturaEstaca, comparando-o com o intervalo definido
        por doubleSpinBoxPadrao e doubleSpinBoxVaria.
        Retorna:
          - 5 para azul (se AlturaEstaca estiver dentro do intervalo),
          - 1 para vermelho (caso contrário).
        """
        try:
            numeric_altura = float(altura)
        except Exception as e:
            self._log_message(f"Erro ao converter AlturaEstaca '{altura}' para float: {e}", level=Qgis.Warning)
            numeric_altura = 0.0
        padraoValue = self.doubleSpinBoxPadrao.value()
        variaValue = self.doubleSpinBoxVaria.value()
        lower_lim = padraoValue - variaValue
        upper_lim = padraoValue + variaValue
        self._log_message(
            f"Comparando AlturaEstaca: {numeric_altura} com intervalo [{lower_lim}, {upper_lim}]",
            level=Qgis.Info
        )
        if lower_lim <= numeric_altura <= upper_lim:
            return 5  # Azul
        else:
            return 1  # Vermelho

    def get_pen_for_feature(self, feature, espessura=2):
        """
        Retorna um QPen com a cor definida com base em "AlturaEstaca".
        Usa o mesmo critério: se AlturaEstaca estiver fora do intervalo definido,
        retorna vermelho; se estiver dentro, azul; caso contrário, preto.
        """
        # Obtém o valor e converte para float, se possível:
        try:
            valor = float(feature["AlturaEstaca"])
        except Exception:
            valor = 0.0

        padrao = self.doubleSpinBoxPadrao.value()
        varia = self.doubleSpinBoxVaria.value()
        lower_lim = padrao - varia
        upper_lim = padrao + varia

        # Se estiver dentro do intervalo, azul; senão, vermelho.
        if lower_lim <= valor <= upper_lim:
            cor = QColor("blue")
        else:
            cor = QColor("red")
        return QPen(cor, espessura)

    def criar_block_quadrado_traco(self, doc, block_name, cor):
        """
        Cria (ou obtém) um bloco com o nome 'block_name' no documento DXF 'doc', 
        onde todas as entidades (o quadrado e o traço) terão a cor definida por 'cor' (um inteiro DXF).
        
        O bloco contém:
          - Um quadrado centrado na origem (de -0.5 a 0.5 em X e Y)
          - Um traço vertical no centro, que se estende para cima (de (0,0) a (0,0.6))
        """
        try:
            block = doc.blocks.new(name=block_name)
        except ezdxf.DXFValueError:
            # Se o bloco já existe, apenas o obtém
            block = doc.blocks.get(block_name)

        # Limpar entidades do bloco se necessário:
        # block.reset()

        # Cria o quadrado com cor definida (não usamos BYBLOCK, definimos explicitamente)
        corners = [
            (-0.5, -0.5),
            (-0.5,  0.5),
            ( 0.5,  0.5),
            ( 0.5, -0.5),
            (-0.5, -0.5)
        ]
        block.add_lwpolyline(
            corners,
            dxfattribs={"color": cor}  # Cor definida
        )

        # Traço vertical no centro: agora estende para cima, de (0,0) a (0,0.6)
        block.add_line(
            (0, 0),
            (0, 0.6),
            dxfattribs={"color": cor}
        )

        return block_name

    def get_dxf_color_for_altura(self, altura):
        """
        Determina a cor DXF com base no valor de AlturaEstaca e nos valores dos spinBoxes.
        Retorna 5 (azul) se AlturaEstaca estiver dentro do intervalo definido,
        ou 1 (vermelho) se estiver fora.
        """
        try:
            a = float(altura)
        except Exception:
            a = 0.0

        padraoValue = self.doubleSpinBoxPadrao.value()
        variaValue  = self.doubleSpinBoxVaria.value()
        lower_lim = padraoValue - variaValue
        upper_lim = padraoValue + variaValue

        if lower_lim <= a <= upper_lim:
            return 5  # Azul
        else:
            return 1  # Vermelho

    def exportar_camadas_para_dxf(self, layers, caminho_arquivo):
        """
        Exporta as camadas de pontos do grupo 'Estruturas' para um arquivo DXF.
        Para cada feição, insere um bloco (INSERT) do "QuadradoTraço" apropriado:
          - Se AlturaEstaca estiver dentro do intervalo, usa o bloco azul.
          - Caso contrário, usa o bloco vermelho.
        Também, opcionalmente, adiciona um MTEXT com os rótulos (sequencia e AlturaEstaca).
        """

        # 1) Cria o documento DXF e define o estilo "Arial"
        doc = ezdxf.new()
        doc.styles.new("Arial", dxfattribs={"font": "arial.ttf"})
        msp = doc.modelspace()

        # 2) Cria os dois blocos (azul e vermelho)
        block_azul = self.criar_block_quadrado_traco(doc, "QuadradoTraço_azul", 5)
        block_vermelho = self.criar_block_quadrado_traco(doc, "QuadradoTraço_vermelho", 1)

        # 3) Itera sobre as camadas de pontos
        for layer in layers:
            layer_name = layer.name()
            # Cria uma layer DXF para organização
            doc.layers.add(name=layer_name)
            
            for feature in layer.getFeatures():
                geom = feature.geometry()
                if not geom or geom.isEmpty():
                    continue
                pt = geom.asPoint()
                x, y = pt.x(), pt.y()

                # Determina a cor com base em AlturaEstaca
                if "AlturaEstaca" in feature.fields().names():
                    dxf_color = self.get_dxf_color_for_altura(feature["AlturaEstaca"])
                else:
                    dxf_color = 7  # Preto (padrão) se não houver AlturaEstaca

                # Escolhe o nome do bloco de acordo com a cor
                if dxf_color == 5:
                    block_name = block_azul  # "QuadradoTraço_azul"
                elif dxf_color == 1:
                    block_name = block_vermelho  # "QuadradoTraço_vermelho"
                else:
                    # Caso não seja azul nem vermelho, usar o azul por padrão
                    block_name = block_azul

                # Define o fator de escala para o bloco
                scale_factor = 0.8  # ajuste conforme necessário

                # 3a) Insere o bloco (INSERT) na posição do ponto
                insert_entity = msp.add_blockref(
                    block_name,
                    (x, y),
                    dxfattribs={"layer": layer_name}
                )
                insert_entity.dxf.xscale = scale_factor
                insert_entity.dxf.yscale = scale_factor
                insert_entity.dxf.zscale = 1.0  # se necessário

                # 3b) (Opcional) Adiciona MTEXT com os rótulos
                if "sequencia" in feature.fields().names() and "AlturaEstaca" in feature.fields().names():
                    label_text = f"{feature['sequencia']}\n{feature['AlturaEstaca']}"
                    mtext_entity = msp.add_mtext(
                        label_text,
                        dxfattribs={"layer": layer_name, "style": "Arial"})

                    mtext_entity.dxf.char_height = 0.35
                    # mtext_entity.dxf.insert = (x + 1, y)
                    # mtext_entity.dxf.attachment_point = 1  # Top Left
                    # mtext_entity.dxf.color = dxf_color

                    # Controle do deslocamento do texto em relação ao ponto:
                    text_offset_x = 0.8  # ajuste esse valor conforme necessário
                    text_offset_y = 0.5  # ajuste esse valor se quiser deslocamento vertical

                    mtext_entity.dxf.insert = (x + text_offset_x, y + text_offset_y)
                    mtext_entity.dxf.attachment_point = 1  # Top Left
                    mtext_entity.dxf.color = dxf_color

        # 4) Salvar o arquivo DXF
        try:
            doc.saveas(caminho_arquivo)
            caminho_pasta = os.path.dirname(caminho_arquivo)
            self.mostrar_mensagem("Exportação DXF com Bloco QuadradoTraço concluída!", 
                                  "Sucesso", 
                                  caminho_pasta=caminho_pasta, 
                                  caminho_arquivo=caminho_arquivo)
        except Exception as e:
            self.mostrar_mensagem(f"Erro ao salvar o DXF: {str(e)}", "Erro")

class ListDeleteButtonDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(ListDeleteButtonDelegate, self).__init__(parent)
        self.parent = parent

    def paint(self, painter, option, index):
        if not index.isValid():
            return

        rect = option.rect
        icon_size = 10  # Tamanho do ícone
        icon_margin = 6  # Margem para o ícone

        # Ícone à esquerda
        icon_rect = QRect(
            rect.left() + icon_margin,
            rect.top() + (rect.height() - icon_size) // 2,
            icon_size,
            icon_size
        )
        # Texto deslocado para a direita do ícone
        text_rect = QRect(
            icon_rect.right() + icon_margin,
            rect.top(),
            rect.width() - icon_size - 2 * icon_margin,
            rect.height()
        )

        # Define o fundo do item:
        if option.state & QStyle.State_Selected:
            # Fundo de seleção: azul clarinho
            painter.fillRect(option.rect, QColor("#00aaff"))
        elif option.state & QStyle.State_MouseOver:
            # Quando o mouse passa sobre o item, fundo verde clarinho
            painter.fillRect(option.rect, QColor("#90EE90"))
        else:
            # Fundo padrão (base do palette)
            painter.fillRect(option.rect, option.palette.base())

        # Desenha o ícone de deletar (quadrado vermelho com contorno azul e "X" branco)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(0, 85, 255), 3))  # Contorno azul (1px)
        painter.setBrush(QBrush(QColor(255, 0, 0, 180)))  # Fundo vermelho
        painter.drawRoundedRect(icon_rect, 3, 3)

        # Desenha o "X" branco dentro do quadrado
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawLine(icon_rect.topLeft() + QPoint(3, 3), icon_rect.bottomRight() - QPoint(3, 3))
        painter.drawLine(icon_rect.topRight() + QPoint(-3, 3), icon_rect.bottomLeft() + QPoint(3, -3))
        painter.restore()

        # Desenha o texto da camada
        painter.save()
        painter.setPen(option.palette.text().color())
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        text = index.data(Qt.DisplayRole)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.TextSingleLine, text)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease:
            rect = option.rect
            icon_size = 11
            icon_margin = 6
            icon_rect = QRect(
                rect.left() + icon_margin,
                rect.top() + (rect.height() - icon_size) // 2,
                icon_size,
                icon_size
            )
            if icon_rect.contains(event.pos()):
                # Obtém o ID da camada armazenado no UserRole e remove a camada do QGIS
                layer_id = index.data(Qt.UserRole)
                QgsProject.instance().removeMapLayer(layer_id)
                # A atualização do listWidget ocorrerá no slot de layersRemoved
                return True
        return super(ListDeleteButtonDelegate, self).editorEvent(event, model, option, index)


