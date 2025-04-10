from qgis.PyQt.QtWidgets import QDialog, QCheckBox, QRadioButton, QApplication, QProgressBar
from qgis.core import QgsProject, QgsMessageLog, Qgis, QgsVectorLayer, QgsWkbTypes, QgsPointXY, QgsFeature, QgsFields, QgsField, QgsGeometry, QgsPoint, QgsCoordinateTransform, QgsCoordinateReferenceSystem
from qgis.PyQt.QtCore import Qt, QVariant, QTimer
from qgis.utils import iface
from qgis.PyQt import uic
import time
import math
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'OpLinhas.ui'))

class LinhasManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(LinhasManager, self).__init__(parent)
        # Configura a interface do usuário a partir do Designer.
        self.setupUi(self)

        self.iface = iface # Armazena a referência da interface QGIS

        # Altera o título da janela
        self.setWindowTitle("Operações Sobre Linhas")

        # Conecta os sinais aos slots
        self.connect_signals()

    def connect_signals(self):

       # Conecta a mudança de seleção no comboBoxCamada para atualizar o checkBoxSeleciona
        self.comboBoxCamada.currentIndexChanged.connect(self.update_checkBoxSeleciona)

        # Conecta sinais do projeto para atualizar comboBox quando camadas forem adicionadas, removidas ou renomeadas
        QgsProject.instance().layersAdded.connect(self.populate_combo_box)
        QgsProject.instance().layersRemoved.connect(self.populate_combo_box)
        QgsProject.instance().layerWillBeRemoved.connect(self.populate_combo_box)

        # Conecta o botão de executar à função on_executar
        self.pushButtonExecutar.clicked.connect(self.on_executar)

        # Conecta o sinal toggled do checkBoxLinhas
        self.checkBoxLinhas.toggled.connect(self.update_lin_controls)

        # Conecte o sinal toggled do checkBoxSegmentar
        self.checkBoxSegmentar.toggled.connect(self.update_seg_controls)

        # Conecte o sinal toggled do checkBoxPoliLinhas
        self.checkBoxPoliLinhas.toggled.connect(self.update_poly_controls)

        # Conecte o sinal toggled do pushButtonExecutar
        self.checkBoxLinhas.toggled.connect(self.update_execute_button)
        self.checkBoxSegmentar.toggled.connect(self.update_execute_button)
        self.checkBoxPoliLinhas.toggled.connect(self.update_execute_button)
        
        # Fecha o Diálogo
        self.pushButtonFechar.clicked.connect(self.close)

        self.comboBoxCamada.currentIndexChanged.connect(self.update_execute_button)

    def showEvent(self, event):
        """
        Sobrescreve o evento de exibição do diálogo para resetar os Widgets.
        """
        super(LinhasManager, self).showEvent(event)

        self.populate_combo_box()  # Atualiza o comboBoxCamada com as camadas disponíveis

        self.update_checkBoxSeleciona()  # Atualiza o estado do checkBoxSeleciona com base nas feições selecionadas

        self.update_layer_connections()  # Conecta os sinais da camada atual

        self.update_lin_controls() # Atualiza o estado ao iniciar do checkBoxLinhas

        self.update_seg_controls() # Atualiza o estado ao iniciar do checkBoxSegmentar
        
        self.update_poly_controls() # Atualiza o estado ao iniciar do checkBoxPoliLinhas

        self.update_execute_button() # Atualiza o estado ao iniciar do pushButtonExecutar

        self.reset_controls()                # Reseta os controles para o estado padrão

    def _log_message(self, message, level=Qgis.Info):
        QgsMessageLog.logMessage(message, 'Malha', level=level)

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
        progressMessageBar = self.iface.messageBar().createMessage("Gerando Camada(as) solicitada(as)...")
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

    def update_checkBoxSeleciona(self):
        """
        Atualiza o estado do checkBoxSeleciona com base na seleção de feições da camada atualmente selecionada.

        Parâmetros:
        self : objeto
            Referência à instância atual da classe.

        A função realiza as seguintes ações:
        - Obtém o ID da camada atualmente selecionada no comboBoxCamada.
        - Se uma camada válida for encontrada, verifica a quantidade de feições selecionadas na camada.
        - Se houver feições selecionadas, o checkBoxSeleciona é ativado.
        - Se não houver feições selecionadas ou a camada não for válida, o checkBoxSeleciona é desativado e desmarcado.
        """
        layer_id = self.comboBoxCamada.currentData()  # Obtém o ID da camada selecionada no comboBoxCamada
        if layer_id:  # Verifica se há uma camada selecionada
            layer = QgsProject.instance().mapLayer(layer_id)  # Obtém a camada correspondente ao ID
            if layer:  # Verifica se a camada existe
                selected_features = layer.selectedFeatureCount()  # Conta o número de feições selecionadas na camada
                if selected_features > 0:  # Se houver feições selecionadas, ativa o checkBoxSeleciona
                    self.findChild(QCheckBox, 'checkBoxSeleciona').setEnabled(True)
                else:  # Se não houver feições selecionadas, desativa o checkBoxSeleciona e o desmarca
                    self.findChild(QCheckBox, 'checkBoxSeleciona').setEnabled(False)
                    self.findChild(QCheckBox, 'checkBoxSeleciona').setChecked(False)
            else:  # Se a camada não for válida, desativa o checkBoxSeleciona e o desmarca
                self.findChild(QCheckBox, 'checkBoxSeleciona').setEnabled(False)
                self.findChild(QCheckBox, 'checkBoxSeleciona').setChecked(False)
        else:  # Se não houver uma camada selecionada, desativa o checkBoxSeleciona e o desmarca
            self.findChild(QCheckBox, 'checkBoxSeleciona').setEnabled(False)
            self.findChild(QCheckBox, 'checkBoxSeleciona').setChecked(False)

    def update_layer_connections(self):
        """
        Conecta o sinal selectionChanged da camada selecionada no comboBoxCamada à função update_checkBoxSeleciona,
        e atualiza o estado do checkBoxSeleciona imediatamente.

        Parâmetros:
        self : objeto
            Referência à instância atual da classe.

        A função realiza as seguintes ações:
        - Obtém o ID da camada atualmente selecionada no comboBoxCamada.
        - Se uma camada válida for encontrada, conecta o sinal selectionChanged da camada à função update_checkBoxSeleciona.
        - Atualiza imediatamente o estado do checkBoxSeleciona com base na seleção de feições.
        - Se não houver uma camada selecionada, desativa o checkBoxSeleciona.
        """
        layer_id = self.comboBoxCamada.currentData()  # Obtém o ID da camada atualmente selecionada no comboBoxCamada
        if layer_id:  # Verifica se há uma camada selecionada
            layer = QgsProject.instance().mapLayer(layer_id)  # Obtém a camada correspondente ao ID
            if layer:  # Verifica se a camada existe
                layer.selectionChanged.connect(self.update_checkBoxSeleciona)  # Conecta o sinal selectionChanged à função update_checkBoxSeleciona
                self.update_checkBoxSeleciona()  # Atualiza o estado do checkBoxSeleciona imediatamente
        else:  # Se não houver uma camada selecionada, desativa o checkBoxSeleciona
            self.update_checkBoxSeleciona()  # Chama a função para desativar o checkBoxSeleciona

    def populate_combo_box(self):
        """
        Popula o comboBoxCamada com as camadas de polígonos disponíveis no projeto e realiza ações relacionadas.

        Parâmetros:
        self : objeto
            Referência à instância atual da classe.

        A função realiza as seguintes ações:
        - Salva a camada atualmente selecionada no comboBoxCamada.
        - Bloqueia temporariamente os sinais do comboBoxCamada para evitar atualizações desnecessárias.
        - Limpa o comboBoxCamada antes de preenchê-lo novamente.
        - Adiciona as camadas de polígonos disponíveis ao comboBoxCamada.
        - Restaura a seleção da camada anterior, se possível.
        - Desbloqueia os sinais do comboBoxCamada após preenchê-lo.
        - Preenche o comboBoxRotulagem com os campos da camada selecionada.
        - Ativa ou desativa o botão pushButtonConverter com base na presença de camadas no comboBoxCamada.
        """
        current_layer_id = self.comboBoxCamada.currentData()  # Salva a camada atualmente selecionada
        self.comboBoxCamada.blockSignals(True)  # Bloqueia os sinais para evitar chamadas desnecessárias a update_poligono_edit_nome
        self.comboBoxCamada.clear()  # Limpa o comboBox antes de preencher

        layer_list = QgsProject.instance().mapLayers().values()
        for layer in layer_list:
            if isinstance(layer, QgsVectorLayer) and QgsWkbTypes.geometryType(layer.wkbType()) == QgsWkbTypes.LineGeometry:
                self.comboBoxCamada.addItem(layer.name(), layer.id())
                layer.nameChanged.connect(self.update_combo_box_item)  # Conecta o sinal nameChanged à função update_combo_box_item

        # Restaura a seleção anterior, se possível
        if current_layer_id:
            index = self.comboBoxCamada.findData(current_layer_id) # Tenta encontrar a camada selecionada anteriormente
            if index != -1:
                self.comboBoxCamada.setCurrentIndex(index) # Restaura a seleção anterior

        self.comboBoxCamada.blockSignals(False)  # Desbloqueia os sinais

        # Atualiza o botão de execução, verificando se há camadas no comboBox
        self.update_execute_button()

    def update_combo_box_item(self):
        """
        Atualiza o texto dos itens no comboBoxCamada com base nos nomes atuais das camadas no projeto.

        Parâmetros:
        self : objeto
            Referência à instância atual da classe.

        A função realiza as seguintes ações:
        - Itera sobre os itens no comboBoxCamada.
        - Para cada item, obtém o ID da camada correspondente.
        - Atualiza o nome exibido no comboBoxCamada com o nome atual da camada, caso a camada ainda exista.
        - Atualiza o campo de nome do polígono (lineEditNome) após atualizar o comboBox.
        """
        
        for i in range(self.comboBoxCamada.count()):  # Itera sobre todos os itens no comboBoxCamada
            layer_id = self.comboBoxCamada.itemData(i)  # Obtém o ID da camada para o item atual
            layer = QgsProject.instance().mapLayer(layer_id)  # Obtém a camada correspondente ao ID
            if layer:  # Verifica se a camada existe
                self.comboBoxCamada.setItemText(i, layer.name())  # Atualiza o texto do item com o nome atual da camada

    def on_executar(self):
        """
        Método principal chamado ao clicar no botão "Executar".
        Verifica quais checkboxes/radiobuttons estão selecionados,
        checa se a camada está em CRS geográfico e, se necessário,
        prepara a reprojeção para UTM. Em seguida, chama as funções
        correspondentes.
        """
        # Obtém a camada selecionada do comboBox
        layer_id = self.comboBoxCamada.currentData()
        if not layer_id:
            self.mostrar_mensagem("Nenhuma camada selecionada.", "Erro")
            return

        line_layer = QgsProject.instance().mapLayer(layer_id)
        if not line_layer:
            self.mostrar_mensagem("Camada inválida.", "Erro")
            return

        # Verifica se a camada está em coordenadas geográficas (latitude/longitude)
        source_crs = line_layer.crs()
        needs_reprojection = source_crs.isGeographic()
        self.transform = None
        self.inverse_transform = None

        if needs_reprojection:
            # Obtém a extensão da camada
            extent = line_layer.extent()
            # Se a extensão não for válida, utiliza a extensão da primeira feição
            if extent.isEmpty() or math.isnan(extent.xMinimum()):
                # Como neste ponto ainda não processamos as feições, obtemos a lista completa
                features = list(line_layer.getFeatures())
                if features:
                    first_feat = features[0]
                    extent = first_feat.geometry().boundingBox()
                else:
                    self.mostrar_mensagem("Camada sem feições válidas.", "Erro")
                    return

            center = extent.center()
            # Calcula a zona UTM usando o centro da extensão
            zone = int((center.x() + 180) / 6) + 1
            # Define o EPSG conforme o hemisfério
            if center.y() >= 0:
                utm_epsg = 32600 + zone
            else:
                utm_epsg = 32700 + zone

            target_crs = QgsCoordinateReferenceSystem.fromEpsgId(utm_epsg)
            self.transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
            self.inverse_transform = QgsCoordinateTransform(target_crs, source_crs, QgsProject.instance())
            self.mostrar_mensagem(f"Reprojeção para UTM (EPSG:{utm_epsg}) aplicada.", "Info", duracao=3)

        # Chama as funções de operação conforme os checkboxes selecionados
        if self.checkBoxLinhas.isChecked():
            self.generate_points_along_lines()  # A função deve verificar self.transform se não for None

        if self.checkBoxSegmentar.isChecked():
            self.segment_lines()  # Idem, se a reprojeção for necessária

        if self.checkBoxPoliLinhas.isChecked():
            self.generate_polygons_along_lines()  # Também considerar a reprojeção se necessário

    def generate_points_along_lines(self):
        """
        Gera pontos ao longo de uma camada de linhas, considerando:
          - Espaçamento definido por doubleSpinBoxEspacamento;
          - Uso de feições selecionadas, se indicado;
          - Inclusão dos vértices, de modo que, na interpolação por segmento,
            cada vértice (exceto o último) tem um ponto associado, e o último
            vértice só receberá ponto se checkBoxPFinal estiver selecionado;
          - Se checkBoxIgnoraV estiver marcado, gera somente pontos interpolados.
        
        A camada de saída incluirá os campos:
          - ID: identificador sequencial
          - X: coordenada X do ponto
          - Y: coordenada Y do ponto

        Durante o processo, é exibida uma barra de progresso e, ao final, é exibida
        uma mensagem informando que a camada foi criada com sucesso, indicando também a
        duração total do processamento.
        
        Se a camada foi reprojetada (através de self.transform e self.inverse_transform), o processamento
        ocorre no CRS métrico e os resultados são revertidos para o CRS original.
        """
        start_time = time.time()  # Inicia a contagem do tempo

        # Obtém a camada selecionada
        layer_id = self.comboBoxCamada.currentData()
        if not layer_id:
            self.mostrar_mensagem("Nenhuma camada selecionada.", "Erro")
            return

        line_layer = QgsProject.instance().mapLayer(layer_id)
        if not line_layer:
            self.mostrar_mensagem("Camada inválida.", "Erro")
            return

        # Obtém o valor do espaçamento
        spacing = self.doubleSpinBoxEspacamento.value()
        if spacing <= 0:
            self.mostrar_mensagem("O espaçamento deve ser maior que zero.", "Erro")
            return

        # Determina se usa feições selecionadas ou todas
        if self.findChild(QCheckBox, 'checkBoxSeleciona').isChecked():
            features = list(line_layer.selectedFeatures())
            if not features:
                self.mostrar_mensagem("Nenhuma feição selecionada na camada.", "Erro")
                return
        else:
            features = list(line_layer.getFeatures())

        # Flags de opções
        ignora_vertices = self.findChild(QCheckBox, 'checkBoxIgnoraV').isChecked()
        adiciona_final = self.findChild(QCheckBox, 'checkBoxPFinal').isChecked()

        # Cria camada em memória para pontos
        crs = line_layer.crs().authid()
        point_layer = QgsVectorLayer(f"Point?crs={crs}", "Pontos", "memory")
        pr = point_layer.dataProvider()

        # Define os campos: ID (inteiro), X e Y (double)
        fields = QgsFields()
        fields.append(QgsField("ID", QVariant.Int))
        fields.append(QgsField("X", QVariant.Double))
        fields.append(QgsField("Y", QVariant.Double))
        pr.addAttributes(fields)
        point_layer.updateFields()

        new_features = []

        # Função auxiliar para obter os pontos de uma linha.
        # Se (ignora_vertices ou adiciona_final) é verdadeiro, utiliza interpolação contínua;
        # caso contrário, realiza interpolação por segmento, reiniciando o espaçamento a cada vértice,
        # e adiciona o vértice final do segmento somente se não for o último vértice da linha.
        def get_points_for_line(line):
            if ignora_vertices or adiciona_final:
                pts = []
                line_geom = QgsGeometry.fromPolylineXY(line)
                length = line_geom.length()
                if not ignora_vertices:
                    pts.append(line_geom.interpolate(0))
                d = spacing
                while d < length:
                    pts.append(line_geom.interpolate(d))
                    d += spacing
                if adiciona_final:
                    end_pt = line_geom.interpolate(length)
                    if not pts or (pts[-1].asPoint() != end_pt.asPoint()):
                        pts.append(end_pt)
                return pts
            else:
                # Interpolação por segmento: reinicia o espaçamento em cada vértice.
                pts = []
                for i in range(len(line) - 1):
                    # Adiciona o vértice inicial do segmento (somente para o primeiro segmento)
                    if i == 0:
                        pts.append(QgsGeometry.fromPointXY(line[i]))
                    seg_geom = QgsGeometry.fromPolylineXY([line[i], line[i + 1]])
                    seg_length = seg_geom.length()
                    d = spacing
                    while d < seg_length:
                        ratio = d / seg_length
                        new_x = line[i].x() + ratio * (line[i + 1].x() - line[i].x())
                        new_y = line[i].y() + ratio * (line[i + 1].y() - line[i].y())
                        pts.append(QgsGeometry.fromPointXY(QgsPointXY(new_x, new_y)))
                        d += spacing
                    # Adiciona o vértice final do segmento se não for o último vértice da linha.
                    if i < len(line) - 2:
                        pts.append(QgsGeometry.fromPointXY(line[i + 1]))
                return pts

        # Primeiro laço: contar o total de pontos (para configurar a barra de progresso)
        total_points = 0
        for feat in features:
            geom = feat.geometry()
            if geom.isEmpty():
                continue
            # Se necessário, transforma a geometria para o CRS métrico
            geom_proc = QgsGeometry(geom)
            if self.transform is not None:
                geom_proc.transform(self.transform)
            if geom_proc.isMultipart():
                parts = geom_proc.asMultiPolyline()
            else:
                parts = [geom_proc.asPolyline()]
            for line in parts:
                if len(line) < 2:
                    continue
                pts = get_points_for_line(line)
                total_points += len(pts)

        # Inicia a barra de progresso (usa a função iniciar_progress_bar)
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_points)
        current_step = 0
        point_id = 1  # contador para o campo ID

        # Segundo laço: gera os pontos e atualiza a barra de progresso
        for feat in features:
            geom = feat.geometry()
            if geom.isEmpty():
                continue
            geom_proc = QgsGeometry(geom)
            if self.transform is not None:
                geom_proc.transform(self.transform)
            if geom_proc.isMultipart():
                parts = geom_proc.asMultiPolyline()
            else:
                parts = [geom_proc.asPolyline()]
            for line in parts:
                if len(line) < 2:
                    continue
                pts = get_points_for_line(line)
                for pt in pts:
                    # Se a geometria foi processada em UTM, transforma o ponto de volta para o CRS original
                    pt_final = QgsGeometry(pt)  # cópia da geometria do ponto
                    if self.inverse_transform is not None:
                        pt_final.transform(self.inverse_transform)
                    new_feat = QgsFeature()
                    new_feat.setGeometry(pt_final)
                    pt_point = pt_final.asPoint()
                    new_feat.setAttributes([point_id, pt_point.x(), pt_point.y()])
                    point_id += 1
                    new_features.append(new_feat)
                    current_step += 1
                    progressBar.setValue(current_step)
                    QApplication.processEvents()  # Atualiza a interface

        # Adiciona as novas feições à camada e insere no projeto
        pr.addFeatures(new_features)
        point_layer.updateExtents()
        QgsProject.instance().addMapLayer(point_layer)

        # Fecha a barra de progresso (remove os widgets)
        self.iface.messageBar().clearWidgets()

        # Calcula a duração e exibe uma mensagem final com o tempo de execução
        duration = time.time() - start_time
        final_message = f"Camada de pontos gerada com sucesso. Duração: {duration:.2f} segundos."
        self.mostrar_mensagem(final_message, "Sucesso", duracao=2)

    def segment_lines(self):
        """
        Segmenta as linhas da camada selecionada conforme o modo escolhido:
          - Modo "Partes": divide cada feição em um número fixo de partes (valor de spinBoxPartes);
          - Modo "Comprimento": divide cada trecho entre vértices em segmentos de comprimento fixo
             (valor de doubleSpinBoxSegmentos), mas, se o trecho final entre dois vértices for menor,
             utiliza esse comprimento restante antes de reiniciar a contagem a partir do vértice.
        
        Durante o processamento, é exibida uma barra de progresso e, ao final, uma mensagem com a
        duração do processamento é mostrada.
        
        Se a camada estiver em CRS geográfico, o processamento será realizado reprojetando para um CRS
        métrico (UTM) e, ao final, os segmentos serão convertidos de volta para o CRS original.

        Cada feição criada recebe um ID sequencial.
        """
        start_time = time.time()
        
        # Obtém a camada de linhas
        layer_id = self.comboBoxCamada.currentData()
        if not layer_id:
            self.mostrar_mensagem("Nenhuma camada selecionada para segmentar.", "Erro")
            return

        line_layer = QgsProject.instance().mapLayer(layer_id)
        if not line_layer:
            self.mostrar_mensagem("Camada inválida.", "Erro")
            return

        # Usa feições selecionadas se o checkBoxSeleciona estiver marcado; senão, todas
        if self.findChild(QCheckBox, 'checkBoxSeleciona').isChecked():
            features = list(line_layer.selectedFeatures())
            if not features:
                self.mostrar_mensagem("Nenhuma feição selecionada na camada para segmentar.", "Erro")
                return
        else:
            features = list(line_layer.getFeatures())

        # Verifica qual modo de segmentação foi selecionado
        by_parts = self.findChild(QRadioButton, 'radioButtonPartes').isChecked()
        by_length = self.findChild(QRadioButton, 'radioButtonComprimento').isChecked()

        if not by_parts and not by_length:
            self.mostrar_mensagem("Selecione 'Partes' ou 'Comprimento' para segmentar.", "Erro")
            return

        new_features = []

        # Cria camada em memória para as linhas segmentadas
        crs = line_layer.crs().authid()
        segmented_layer = QgsVectorLayer(f"LineString?crs={crs}", "Linhas_Segmentadas", "memory")
        pr = segmented_layer.dataProvider()

        # Adiciona o campo ID
        pr.addAttributes([QgsField("ID", QVariant.Int)])
        segmented_layer.updateFields()

        # --- Verificação da projeção ---
        source_crs = line_layer.crs()
        needs_reprojection = source_crs.isGeographic()
        transform = None
        inverse_transform = None
        if needs_reprojection:
            extent = line_layer.extent()
            if extent.isEmpty() or math.isnan(extent.xMinimum()):
                features_all = list(line_layer.getFeatures())
                if features_all:
                    first_feat = features_all[0]
                    extent = first_feat.geometry().boundingBox()
                else:
                    self.mostrar_mensagem("Camada sem feições válidas.", "Erro")
                    return
            center = extent.center()
            zone = int((center.x() + 180) / 6) + 1
            if center.y() >= 0:
                utm_epsg = 32600 + zone
            else:
                utm_epsg = 32700 + zone
            target_crs = QgsCoordinateReferenceSystem.fromEpsgId(utm_epsg)
            transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
            inverse_transform = QgsCoordinateTransform(target_crs, source_crs, QgsProject.instance())
            # Opcional: informar ao usuário que a reprojeção está sendo aplicada
            self.mostrar_mensagem(f"Reprojeção para UTM (EPSG:{utm_epsg}) aplicada.", "Info", duracao=3)

        # Primeiro: contar o total de segmentos a serem gerados (para a barra de progresso)
        total_segments = 0
        if by_parts:
            n_parts = self.spinBoxPartes.value()
            for feat in features:
                geom = feat.geometry()
                if geom.isEmpty():
                    continue
                # Transformação para CRS métrico, se necessário
                geom_proc = QgsGeometry(geom)
                if transform is not None:
                    geom_proc.transform(transform)
                if geom_proc.isMultipart():
                    parts = geom_proc.asMultiPolyline()
                else:
                    parts = [geom_proc.asPolyline()]
                for line in parts:
                    if len(line) < 2:
                        continue
                    total_segments += n_parts
        else:
            seg_length = self.doubleSpinBoxSegmentos.value()
            for feat in features:
                geom = feat.geometry()
                if geom.isEmpty():
                    continue
                geom_proc = QgsGeometry(geom)
                if transform is not None:
                    geom_proc.transform(transform)
                if geom_proc.isMultipart():
                    parts = geom_proc.asMultiPolyline()
                else:
                    parts = [geom_proc.asPolyline()]
                for line in parts:
                    if len(line) < 2:
                        continue
                    for i in range(len(line) - 1):
                        p_start = QgsPointXY(line[i])
                        p_end = QgsPointXY(line[i+1])
                        d = p_start.distance(p_end)
                        if d < 1e-6:
                            continue
                        n_seg = int(d // seg_length)
                        if d - n_seg * seg_length > 1e-6:
                            n_seg += 1
                        total_segments += n_seg

        progressBar, progressMessageBar = self.iniciar_progress_bar(total_segments)
        current_step = 0

        # Contador de ID
        id_counter = 1

        # Processamento dos features conforme o modo selecionado
        if by_parts:
            # Modo por Partes: divide a linha em partes iguais
            n_parts = self.spinBoxPartes.value()
            for feat in features:
                geom = feat.geometry()
                if geom.isEmpty():
                    continue
                geom_proc = QgsGeometry(geom)
                if transform is not None:
                    geom_proc.transform(transform)
                if geom_proc.isMultipart():
                    parts = geom_proc.asMultiPolyline()
                else:
                    parts = [geom_proc.asPolyline()]
                for line in parts:
                    if len(line) < 2:
                        continue
                    line_geom = QgsGeometry.fromPolylineXY(line)
                    total_length = line_geom.length()
                    step = total_length / n_parts
                    start_dist = 0.0
                    for i in range(n_parts):
                        end_dist = total_length if i == n_parts - 1 else start_dist + step
                        # Obtém os pontos do segmento
                        start_point = line_geom.interpolate(start_dist).asPoint()
                        end_point = line_geom.interpolate(end_dist).asPoint()
                        # Cria o segmento como uma nova geometria de linha
                        segment_geom = QgsGeometry.fromPolylineXY([start_point, end_point])
                        # Reverte para o CRS original, se necessário
                        if inverse_transform is not None:
                            segment_geom.transform(inverse_transform)

                        # Cria a feição e define o ID
                        new_feat = QgsFeature(segmented_layer.fields())
                        new_feat.setGeometry(segment_geom)
                        new_feat.setAttribute("ID", id_counter)
                        id_counter += 1

                        new_features.append(new_feat)
                        start_dist = end_dist

                        current_step += 1
                        progressBar.setValue(current_step)
                        QApplication.processEvents()

        else:
            # Modo por Comprimento: segmenta cada trecho entre vértices
            seg_length = self.doubleSpinBoxSegmentos.value()
            for feat in features:
                geom = feat.geometry()
                if geom.isEmpty():
                    continue
                geom_proc = QgsGeometry(geom)
                if transform is not None:
                    geom_proc.transform(transform)
                if geom_proc.isMultipart():
                    parts = geom_proc.asMultiPolyline()
                else:
                    parts = [geom_proc.asPolyline()]
                for line in parts:
                    if len(line) < 2:
                        continue
                    # Processa trecho a trecho (entre vértices consecutivos)
                    for i in range(len(line) - 1):
                        p_start = QgsPointXY(line[i])
                        p_end = QgsPointXY(line[i+1])
                        d_total = p_start.distance(p_end)
                        if d_total < 1e-6:
                            continue
                        dx = p_end.x() - p_start.x()
                        dy = p_end.y() - p_start.y()
                        current_point = p_start
                        distance_left = d_total

                        while distance_left > 1e-6:
                            if distance_left < seg_length:
                                next_point = p_end
                            else:
                                frac = seg_length / distance_left
                                next_point = QgsPointXY(
                                    current_point.x() + dx * frac,
                                    current_point.y() + dy * frac
                                )
                            segment_geom = QgsGeometry.fromPolylineXY([current_point, next_point])
                            # Reverte para o CRS original, se necessário
                            if inverse_transform is not None:
                                segment_geom.transform(inverse_transform)

                            # Cria a feição e define o ID
                            new_feat = QgsFeature(segmented_layer.fields())
                            new_feat.setGeometry(segment_geom)
                            new_feat.setAttribute("ID", id_counter)
                            id_counter += 1

                            new_features.append(new_feat)
                            current_step += 1
                            progressBar.setValue(current_step)
                            QApplication.processEvents()

                            if next_point == p_end:
                                break
                            current_point = next_point
                            distance_left = current_point.distance(p_end)
                            dx = p_end.x() - current_point.x()
                            dy = p_end.y() - current_point.y()

        pr.addFeatures(new_features)
        segmented_layer.updateExtents()
        QgsProject.instance().addMapLayer(segmented_layer)
        
        # Fecha a barra de progresso
        self.iface.messageBar().clearWidgets()
        duration = time.time() - start_time
        final_message = f"Linhas segmentadas com sucesso. Duração: {duration:.2f} segundos."
        self.mostrar_mensagem(final_message, "Sucesso", duracao=2)

    def generate_polygons_along_lines(self):
        """
        Cria polígonos (quadrados, círculos ou hexágonos) ao longo das linhas,
        com espaçamento definido por doubleSpinBoxEspacamento2 e tamanho definido
        por doubleSpinBoxTamanho. Garante também que cada vértice da linha receba um polígono.
        O processamento é feito em unidades métricas se a camada estiver em CRS geográfico,
        utilizando a reprojeção para UTM e, ao final, os polígonos são convertidos de volta para o CRS original.

        Além disso, cria um campo 'ID' para cada polígono gerado.
        """

        # --- 1) Verifica camada de linha selecionada ---
        layer_id = self.comboBoxCamada.currentData()
        if not layer_id:
            self.mostrar_mensagem("Nenhuma camada de linha selecionada.", "Erro")
            return

        line_layer = QgsProject.instance().mapLayer(layer_id)
        if not line_layer:
            self.mostrar_mensagem("Camada inválida.", "Erro")
            return

        # --- 2) Lê parâmetros da GUI ---
        spacing = self.doubleSpinBoxEspacamento2.value()
        if spacing <= 0:
            self.mostrar_mensagem("O espaçamento deve ser maior que zero.", "Erro")
            return

        poly_size = self.doubleSpinBoxTamanho.value()
        if poly_size <= 0:
            self.mostrar_mensagem("O tamanho do polígono deve ser maior que zero.", "Erro")
            return

        # Verifica qual radiobutton está selecionado
        if self.radioButtonQuadrados.isChecked():
            shape_type = "Quadrado"
        elif self.radioButtonCirculos.isChecked():
            shape_type = "Circulo"
        elif self.radioButtonHexagonos.isChecked():
            shape_type = "Hexagono"
        else:
            self.mostrar_mensagem("Selecione Quadrado, Círculo ou Hexágono.", "Erro")
            return

        # --- 3) Se checkBoxSeleciona estiver marcado, pega feições selecionadas ---
        if self.checkBoxSeleciona.isChecked():
            features = list(line_layer.selectedFeatures())
            if not features:
                self.mostrar_mensagem("Não há feições selecionadas na camada.", "Erro")
                return
        else:
            features = list(line_layer.getFeatures())

        # --- 3.1) Verifica se a camada está em CRS geográfico e prepara a reprojeção ---
        source_crs = line_layer.crs()
        needs_reprojection = source_crs.isGeographic()
        transform = None
        inverse_transform = None
        if needs_reprojection:
            extent = line_layer.extent()
            if extent.isEmpty() or math.isnan(extent.xMinimum()):
                if features:
                    extent = features[0].geometry().boundingBox()
                else:
                    self.mostrar_mensagem("Camada sem feições válidas.", "Erro")
                    return
            center = extent.center()
            zone = int((center.x() + 180) / 6) + 1
            if center.y() >= 0:
                utm_epsg = 32600 + zone
            else:
                utm_epsg = 32700 + zone
            target_crs = QgsCoordinateReferenceSystem.fromEpsgId(utm_epsg)
            transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
            inverse_transform = QgsCoordinateTransform(target_crs, source_crs, QgsProject.instance())
            self.mostrar_mensagem(f"Reprojeção para UTM (EPSG:{utm_epsg}) aplicada.", "Info", duracao=3)

        # --- 4) Cria camada em memória para receber os polígonos ---
        crs = line_layer.crs().authid()
        polygon_layer = QgsVectorLayer(f"Polygon?crs={crs}", "Poligonos_Linhas", "memory")
        pr = polygon_layer.dataProvider()

        # Adiciona o campo ID ao provedor de dados
        pr.addAttributes([QgsField("ID", QVariant.Int)])
        polygon_layer.updateFields()

        new_features = []
        id_counter = 1  # Contador para o atributo ID

        # --- 5) Função auxiliar para construir cada polígono ---
        def create_polygon_geometry(center: QgsPointXY, shape: str, size: float) -> QgsGeometry:
            """
            Retorna uma QgsGeometry do tipo Polígono em torno de 'center',
            baseado no 'shape' (Quadrado, Circulo ou Hexagono) e no 'size'.
            Obs: os polígonos são criados alinhados aos eixos X/Y.
            """
            if shape == "Quadrado":
                half = size / 2.0
                ring = [
                    QgsPointXY(center.x() - half, center.y() - half),
                    QgsPointXY(center.x() + half, center.y() - half),
                    QgsPointXY(center.x() + half, center.y() + half),
                    QgsPointXY(center.x() - half, center.y() + half),
                    QgsPointXY(center.x() - half, center.y() - half)  # fecha polígono
                ]
                return QgsGeometry.fromPolygonXY([ring])

            elif shape == "Circulo":
                pt = QgsGeometry.fromPointXY(center)
                radius = size / 2.0
                return pt.buffer(radius, 36)  # 36 segmentos para uma boa aproximação

            elif shape == "Hexagono":
                ring = []
                for i in range(6):
                    angle_rad = math.radians(60 * i)
                    x = center.x() + size * math.cos(angle_rad)
                    y = center.y() + size * math.sin(angle_rad)
                    ring.append(QgsPointXY(x, y))
                ring.append(ring[0])  # fecha o hexágono
                return QgsGeometry.fromPolygonXY([ring])
            else:
                return None

        # --- 6) Percorre cada feição (cada linha) e gera polígonos ao longo dela ---
        for feat in features:
            geom = feat.geometry()
            if geom.isEmpty():
                continue

            # Se necessário, transforma a geometria para o CRS métrico
            geom_proc = QgsGeometry(geom)
            if transform is not None:
                geom_proc.transform(transform)

            # Trata geometria multipart ou single
            if geom_proc.isMultipart():
                parts = geom_proc.asMultiPolyline()
            else:
                parts = [geom_proc.asPolyline()]

            for line in parts:
                if len(line) < 2:
                    continue

                line_geom = QgsGeometry.fromPolylineXY(line)
                length = line_geom.length()

                # Lista para armazenar os pontos onde já foi criado um polígono
                polygon_centers = []

                # Gera polígonos ao longo da linha com base no espaçamento
                d = 0.0
                while d <= length:
                    center_pt = line_geom.interpolate(d).asPoint()
                    polygon_centers.append(center_pt)
                    poly_geom = create_polygon_geometry(QgsPointXY(center_pt), shape_type, poly_size)
                    # Se houve reprojeção, retorna o polígono para o CRS original
                    if inverse_transform is not None and poly_geom is not None:
                        poly_geom.transform(inverse_transform)

                    if poly_geom:
                        f = QgsFeature(polygon_layer.fields())  # Usa o schema de campos da camada
                        f.setGeometry(poly_geom)
                        # Define o ID e incrementa
                        f.setAttribute("ID", id_counter)
                        id_counter += 1
                        new_features.append(f)
                    d += spacing

                # Garante que cada vértice da linha receba um polígono (caso ainda não exista um próximo)
                tol = 1e-6  # tolerância para comparação de coordenadas
                for vertex in line:
                    vertex_point = QgsPointXY(vertex)
                    if not any(vertex_point.distance(p) < tol for p in polygon_centers):
                        polygon_centers.append(vertex_point)
                        poly_geom = create_polygon_geometry(vertex_point, shape_type, poly_size)
                        if inverse_transform is not None and poly_geom is not None:
                            poly_geom.transform(inverse_transform)
                        if poly_geom:
                            f = QgsFeature(polygon_layer.fields())
                            f.setGeometry(poly_geom)
                            f.setAttribute("ID", id_counter)
                            id_counter += 1
                            new_features.append(f)

        # --- 7) Adiciona as novas feições à camada de polígonos e insere no projeto ---
        pr.addFeatures(new_features)
        polygon_layer.updateExtents()
        QgsProject.instance().addMapLayer(polygon_layer)

        self.mostrar_mensagem("Polígonos gerados com sucesso.", "Sucesso")

    def update_lin_controls(self):
        # Ativa os controles apenas se checkBoxLinhas estiver marcado
        active = self.checkBoxLinhas.isChecked()
        self.doubleSpinBoxEspacamento.setEnabled(active)
        self.checkBoxPFinal.setEnabled(active)
        self.checkBoxIgnoraV.setEnabled(active)

    def update_seg_controls(self):
        # Ativa os controles apenas se checkBoxSegmentar estiver marcado
        active = self.checkBoxSegmentar.isChecked()
        self.radioButtonPartes.setEnabled(active)
        self.spinBoxPartes.setEnabled(active)
        self.radioButtonComprimento.setEnabled(active)
        self.doubleSpinBoxSegmentos.setEnabled(active)
        
        # Se estiver ativo, define o radioButtonComprimento como selecionado imediatamente
        if active:
            self.radioButtonComprimento.setChecked(True)

    def update_poly_controls(self):
        # Ativa os controles se checkBoxPoliLinhas estiver marcado
        active = self.checkBoxPoliLinhas.isChecked()
        self.radioButtonQuadrados.setEnabled(active)
        self.radioButtonCirculos.setEnabled(active)
        self.radioButtonHexagonos.setEnabled(active)
        self.doubleSpinBoxEspacamento2.setEnabled(active)
        self.doubleSpinBoxTamanho.setEnabled(active)
        # Se estiver ativo, marca o radioButtonQuadrados
        if active:
            self.radioButtonQuadrados.setChecked(True)

    def update_execute_button(self):
        # Se o comboBox estiver vazio, desativa o botão de executar
        if self.comboBoxCamada.count() == 0:
            self.pushButtonExecutar.setEnabled(False)
            return

        # Caso haja camadas, verifica se pelo menos um dos checkboxes está marcado
        enable = (self.checkBoxLinhas.isChecked() or 
                  self.checkBoxSegmentar.isChecked() or 
                  self.checkBoxPoliLinhas.isChecked())
        self.pushButtonExecutar.setEnabled(enable)

    def reset_controls(self):
        # Reseta os controles relacionados às linhas
        self.checkBoxLinhas.setChecked(False)
        # Aqui você pode definir um valor padrão para o doubleSpinBoxEspacamento, se desejar (por exemplo, 10)
        self.doubleSpinBoxEspacamento.setValue(self.doubleSpinBoxEspacamento.minimum())
        self.checkBoxPFinal.setChecked(False)
        self.checkBoxIgnoraV.setChecked(False)

        # Reseta os controles de segmentação
        self.checkBoxSegmentar.setChecked(False)
        self.radioButtonPartes.setChecked(False)
        self.spinBoxPartes.setValue(self.spinBoxPartes.minimum())
        self.radioButtonComprimento.setChecked(False)
        self.doubleSpinBoxSegmentos.setValue(self.doubleSpinBoxSegmentos.minimum())

        # Reseta os controles para os polígonos (ou "Pontos de Linhas")
        self.checkBoxPoliLinhas.setChecked(False)  # ou se o nome for checkBoxPoliLinhas, use esse
        # Inicia os radioButtons de polígonos: inicia com o radioButtonQuadrados marcado
        self.radioButtonQuadrados.setChecked(False)
        self.radioButtonCirculos.setChecked(False)
        self.radioButtonHexagonos.setChecked(False)
        self.doubleSpinBoxEspacamento2.setValue(self.doubleSpinBoxEspacamento2.minimum())
        self.doubleSpinBoxTamanho.setValue(self.doubleSpinBoxTamanho.minimum())

        # Atualiza os estados (ativar/desativar) de cada grupo de controles, conforme suas lógicas
        self.update_lin_controls()
        self.update_seg_controls()
        self.update_poly_controls()

        # Atualiza também o botão de executar, se necessário
        self.update_execute_button()
