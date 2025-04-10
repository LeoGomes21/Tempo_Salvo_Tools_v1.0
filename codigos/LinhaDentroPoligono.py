from qgis.core import QgsProject, QgsMessageLog, Qgis, QgsVectorLayer, QgsWkbTypes, QgsMapSettings, QgsMapRendererCustomPainterJob, QgsGeometry, QgsPointXY, QgsFeature, QgsLineSymbol, QgsCoordinateReferenceSystem, QgsCoordinateTransform
from qgis.PyQt.QtWidgets import QDialog, QCheckBox, QGraphicsScene, QGraphicsPixmapItem, QToolTip, QGraphicsLineItem, QColorDialog, QProgressBar, QApplication
from PyQt5.QtGui import QImage, QPainter, QPixmap, QColor, QPen, QIntValidator, QCursor
from qgis.PyQt.QtCore import Qt, QSize
from qgis.utils import iface
from qgis.PyQt import uic
import math
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'LinhasdentroPoligono.ui'))

class DentroManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(DentroManager, self).__init__(parent)
        # Configura a interface do usuário a partir do Designer.
        self.setupUi(self)

        self.iface = iface

        # Inicializa o atributo de cor (nenhuma cor definida inicialmente)
        self.linha_cor = None

        # Configuração do lineEditAngulo: cor cinza e texto centralizado
        self.lineEditAngulo.setValidator(QIntValidator(0, 360, self))
        self.lineEditAngulo.setStyleSheet("background-color: lightgray;")
        self.lineEditAngulo.setAlignment(Qt.AlignCenter)
        
        # Define um tooltip inicial e duração para o horizontalSlider.
        self.horizontalSlider.setToolTip(f"Ângulo: {self.horizontalSlider.value()}°")
        self.horizontalSlider.setToolTipDuration(3000)

        self.scenePoligono = QGraphicsScene()
        self.graphicsView.setScene(self.scenePoligono)

        # Altera o título da janela
        self.setWindowTitle("Linhas Dentro de Polígonos")

        # Preenche o comboBox com camadas de linha
        self.populate_combo_box()

        # Conecta os sinais aos slots
        self.connect_signals()

    def connect_signals(self):

       # Conecta a mudança de seleção no comboBoxCamada para atualizar o checkBoxSeleciona
        self.comboBoxCamada.currentIndexChanged.connect(self.update_checkBoxSeleciona)
        self.comboBoxCamada.currentIndexChanged.connect(self.display_polygon)  # Conexão para atualizar o graphicsView

        # Conecta também para atualizar os sinais da camada (selectionChanged)
        self.comboBoxCamada.currentIndexChanged.connect(self.update_layer_connections)

        # Conecta o horizontalSlider para atualizar o tooltip e o lineEditAngulo
        self.horizontalSlider.valueChanged.connect(self.atualizar_angulo)

        # Conecta o lineEditAngulo para atualizar o horizontalSlider imediatamente
        self.lineEditAngulo.textChanged.connect(self.atualizar_slider_pelo_lineEdit)
        self.lineEditAngulo.editingFinished.connect(self.atualizar_slider_pelo_lineEdit)

        # Conecta o clique do botão pushButtonExecutar para executar
        self.pushButtonExecutar.clicked.connect(self.executar)

        # Conecta sinais do projeto para atualizar comboBox quando camadas forem adicionadas, removidas ou renomeadas
        QgsProject.instance().layersAdded.connect(self.populate_combo_box)
        QgsProject.instance().layersRemoved.connect(self.populate_combo_box)
        QgsProject.instance().layerWillBeRemoved.connect(self.populate_combo_box)

        # Conecta a alteração do lineEditAngulo para atualizar o horizontalSlider
        self.lineEditAngulo.editingFinished.connect(self.atualizar_slider_pelo_lineEdit)

        # Conecta o pushButtonCor ao método para selecionar a cor
        self.pushButtonCor.clicked.connect(self.selecionar_cor)

        # Atualiza o estado do pushButtonExecutar quando a camada muda
        self.comboBoxCamada.currentIndexChanged.connect(self.update_pushButtonExecutar)
        
        # Conecta o doubleSpinBoxEspassamento para atualizar o estado do botão
        self.doubleSpinBoxEspassamento.valueChanged.connect(self.update_pushButtonExecutar)

        # Conecta o botão pushButtonFechar
        self.pushButtonFechar.clicked.connect(self.close)

    def showEvent(self, event):
        """
        Sobrescreve o evento de exibição do diálogo para resetar os Widgets.
        """
        super(DentroManager, self).showEvent(event)

        # Reset do checkBoxSeleciona
        checkBox = self.findChild(QCheckBox, 'checkBoxSeleciona')
        if checkBox:
            checkBox.setChecked(False)
            checkBox.setEnabled(False)
        
        # Reset do horizontalSlider para 0 (ou valor padrão desejado)
        self.horizontalSlider.setValue(0)
        
        # Reset do lineEditAngulo para "0"
        self.lineEditAngulo.setText("0")
        
        # Reset do doubleSpinBoxEspassamento para 1 (ou outro valor padrão)
        self.doubleSpinBoxEspassamento.setValue(1)
        
        # Reset do pushButtonCor para o estilo padrão e variável interna
        self.pushButtonCor.setStyleSheet("")
        self.linha_cor = None

        self.populate_combo_box()  # Atualiza o comboBoxCamada com as camadas disponíveis

        self.update_checkBoxSeleciona()  # Atualiza o estado do checkBoxSeleciona com base nas feições selecionadas

        self.display_polygon() # Ajusta a visualização quando o diálogo é mostrado

        self.update_pushButtonExecutar()  # Atualiza o estado do botão executar

        self.update_layer_connections()  # Conecta os sinais da camada atual

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
                layer.selectionChanged.connect(self.display_polygon)
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
        self.comboBoxCamada.blockSignals(True)  # Evita disparar eventos desnecessários
        self.comboBoxCamada.clear()

        layer_list = QgsProject.instance().mapLayers().values()
        polygon_layers = [
            layer for layer in layer_list 
            if isinstance(layer, QgsVectorLayer) and QgsWkbTypes.geometryType(layer.wkbType()) == QgsWkbTypes.PolygonGeometry
        ]

        for layer in polygon_layers:
            self.comboBoxCamada.addItem(layer.name(), layer.id())
            layer.nameChanged.connect(self.update_combo_box_item)  # Mantém a conexão para atualizar nomes

        # Restaura a camada anteriormente selecionada, se ainda existir
        if current_layer_id:
            index = self.comboBoxCamada.findData(current_layer_id)
            if index != -1:
                self.comboBoxCamada.setCurrentIndex(index)

        self.comboBoxCamada.blockSignals(False)  # Libera os sinais

        # Atualiza o estado do checkbox e a visualização
        self.update_checkBoxSeleciona()
        self.display_polygon()
        
        # Reconecta os sinais da camada atual, garantindo que o selectionChanged esteja conectado
        self.update_layer_connections()
        self.update_pushButtonExecutar()  # Atualiza o estado do botão

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

    def display_polygon(self):
        """Atualiza a exibição do polígono no QGraphicsView com base na seleção de feições ou no extent da camada."""
        self.scenePoligono.clear()
        selected_polygon_id = self.comboBoxCamada.currentData()
        selected_layer = QgsProject.instance().mapLayer(selected_polygon_id)
        
        if selected_layer and isinstance(selected_layer, QgsVectorLayer):
            # Filtra somente as feições de polígono
            features = [f for f in selected_layer.getFeatures() if f.geometry().type() == QgsWkbTypes.PolygonGeometry]

            if len(features) == 0:
                if self.isVisible():
                    self.mostrar_mensagem("A camada de polígono não contém feições.", "Erro")
                return
            
            # Verifica se há feições selecionadas
            selected_features = selected_layer.selectedFeatures()
            if len(selected_features) > 0:
                # Cria uma geometria unificada que é a união de todas as feições selecionadas
                geom = selected_features[0].geometry()
                for feat in selected_features[1:]:
                    geom = geom.combine(feat.geometry())
            else:
                geom = QgsGeometry.fromRect(selected_layer.extent())

            if geom is None or geom.isEmpty():
                if self.isVisible():
                    self.mostrar_mensagem("A geometria não contém dados válidos.", "Erro")
                return

            # Configurações do renderizador
            map_settings = QgsMapSettings()
            map_settings.setLayers([selected_layer])
            map_settings.setBackgroundColor(QColor(255, 255, 255))
            width = self.graphicsView.viewport().width()
            height = self.graphicsView.viewport().height()
            map_settings.setOutputSize(QSize(width, height))
            
            # Define o extent com base na geometria (seja a feição selecionada ou o extent da camada)
            bounding_box = geom.boundingBox()
            if not bounding_box.isNull():
                map_settings.setExtent(bounding_box)
            else:
                if self.isVisible():
                    self.mostrar_mensagem("A geometria não tem um bounding box válido.", "Erro")
                return

            # Renderiza a imagem
            image = QImage(width, height, QImage.Format_ARGB32)
            image.fill(Qt.transparent)
            painter = QPainter(image)
            render_job = QgsMapRendererCustomPainterJob(map_settings, painter)
            render_job.start()
            render_job.waitForFinished()
            painter.end()

            # Exibe a imagem no QGraphicsView
            pixmap = QPixmap.fromImage(image)
            pixmap_item = QGraphicsPixmapItem(pixmap)
            self.scenePoligono.addItem(pixmap_item)
            self.graphicsView.setSceneRect(pixmap_item.boundingRect())
            self.graphicsView.fitInView(self.scenePoligono.sceneRect(), Qt.KeepAspectRatio)

        else:
            # Opcional: mostrar mensagem de que nenhuma camada válida foi encontrada
            pass

    def atualizar_angulo(self, value):
        """
        Atualiza o tooltip do horizontalSlider, o texto do lineEditAngulo e exibe o tooltip
        próximo à posição atual do cursor enquanto o slider é movido.
        """
        tooltip = f"Ângulo: {value}°"
        self.horizontalSlider.setToolTip(tooltip)
        if self.lineEditAngulo.text() != str(value):
            self.lineEditAngulo.setText(str(value))
        # Exibe o tooltip próximo ao cursor enquanto o slider é movido
        QToolTip.showText(QCursor.pos(), tooltip, self.horizontalSlider)

    def atualizar_slider_pelo_lineEdit(self, text=None):
        """
        Atualiza o horizontalSlider com base no valor inserido no lineEditAngulo.
        Essa função é chamada sempre que o texto mudar ou quando a edição for finalizada.
        """
        if text is None:
            text = self.lineEditAngulo.text()
        if text == '':
            return
        try:
            value = int(text)
        except ValueError:
            return
        # Garante que o valor esteja dentro do intervalo (0 a 360)
        value = max(min(value, self.horizontalSlider.maximum()), self.horizontalSlider.minimum())
        if self.horizontalSlider.value() != value:
            self.horizontalSlider.setValue(value)

    def executar(self):
        """
        Gera uma camada de linhas dentro dos polígonos da camada selecionada.
        
        Se o checkBoxSeleciona estiver marcado, usa apenas as feições selecionadas;
        caso contrário, utiliza todas as feições da camada.
        
        As linhas são geradas com a direção definida pelo horizontalSlider (ângulo em graus)
        e com espaçamento definido pelo doubleSpinBoxEspassamento, utilizando uma abordagem
        que funciona mesmo se a camada de polígonos estiver em coordenadas geográficas.
        
        Se o CRS for geográfico, as geometrias serão reprojetadas para um CRS projetado (zona UTM),
        os cálculos ocorrerão em unidades lineares e, ao final, as linhas serão transformadas de volta.
        
        Uma barra de progresso é exibida durante o processamento.
        A camada resultante é adicionada ao projeto.
        """
        # Obtém a camada de polígonos selecionada
        polygon_layer_id = self.comboBoxCamada.currentData()
        if not polygon_layer_id:
            self.mostrar_mensagem("Nenhuma camada de polígono selecionada.", "Erro")
            return

        polygon_layer = QgsProject.instance().mapLayer(polygon_layer_id)
        if not polygon_layer:
            self.mostrar_mensagem("A camada selecionada não é válida.", "Erro")
            return

        # Determina se usará as feições selecionadas ou todas as feições da camada
        checkBoxSeleciona = self.findChild(QCheckBox, 'checkBoxSeleciona')
        if checkBoxSeleciona and checkBoxSeleciona.isChecked():
            polygon_features = polygon_layer.selectedFeatures()
            if not polygon_features:
                self.mostrar_mensagem("Nenhuma feição selecionada na camada.", "Erro")
                return
        else:
            polygon_features = list(polygon_layer.getFeatures())
            if not polygon_features:
                self.mostrar_mensagem("A camada não contém feições.", "Erro")
                return

        spacing = self.doubleSpinBoxEspassamento.value()
        angle_deg = self.horizontalSlider.value()  # Ângulo em graus (0 a 360)
        angle_rad = math.radians(angle_deg)
        d_x = math.cos(angle_rad)
        d_y = math.sin(angle_rad)
        p_x = -math.sin(angle_rad)
        p_y = math.cos(angle_rad)

        # Se o CRS da camada de polígonos for geográfico, converte para um CRS projetado.
        source_crs = polygon_layer.crs()
        if source_crs.isGeographic():
            # Usa o centro do primeiro polígono para determinar a zona UTM
            first_geom = polygon_features[0].geometry()
            center = first_geom.centroid().asPoint()
            lon = center.x()
            lat = center.y()
            utm_zone = int((lon + 180) / 6) + 1
            if lat >= 0:
                epsg_code = 32600 + utm_zone
            else:
                epsg_code = 32700 + utm_zone
            proj_crs = QgsCoordinateReferenceSystem(epsg_code)
            transform_to_proj = QgsCoordinateTransform(source_crs, proj_crs, QgsProject.instance())
            transform_to_source = QgsCoordinateTransform(proj_crs, source_crs, QgsProject.instance())
        else:
            transform_to_proj = None
            transform_to_source = None

        # Inicia a barra de progresso: cada polígono é uma etapa
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_steps=len(polygon_features))
        features_list = []
        processed = 0

        for polygon_feature in polygon_features:
            processed += 1
            progressBar.setValue(processed)
            QApplication.processEvents()

            polygon_geom = polygon_feature.geometry()
            if polygon_geom.isEmpty():
                continue

            # Trabalha com uma cópia da geometria
            polygon_geom_work = QgsGeometry.fromWkt(polygon_geom.asWkt())
            if transform_to_proj:
                polygon_geom_work.transform(transform_to_proj)

            bbox = polygon_geom_work.boundingBox()
            # Para gerar as linhas inclinadas, usamos os cantos do bounding box
            corners = [
                QgsPointXY(bbox.xMinimum(), bbox.yMinimum()),
                QgsPointXY(bbox.xMinimum(), bbox.yMaximum()),
                QgsPointXY(bbox.xMaximum(), bbox.yMinimum()),
                QgsPointXY(bbox.xMaximum(), bbox.yMaximum())
            ]
            offsets = [pt.x() * p_x + pt.y() * p_y for pt in corners]
            offset_min = min(offsets)
            offset_max = max(offsets)

            # Define o centro do bbox para servir de referência
            center = QgsPointXY((bbox.xMinimum() + bbox.xMaximum()) / 2,
                                (bbox.yMinimum() + bbox.yMaximum()) / 2)
            center_proj = center.x() * p_x + center.y() * p_y

            current_offset = offset_max
            while current_offset >= offset_min:
                delta = current_offset - center_proj
                base = QgsPointXY(center.x() + delta * p_x, center.y() + delta * p_y)
                L = math.sqrt(bbox.width()**2 + bbox.height()**2) * 2
                start = QgsPointXY(base.x() - d_x * L, base.y() - d_y * L)
                end = QgsPointXY(base.x() + d_x * L, base.y() + d_y * L)
                linha = QgsGeometry.fromPolylineXY([start, end])
                intersec = polygon_geom_work.intersection(linha)
                if not intersec.isEmpty():
                    if intersec.type() == QgsWkbTypes.LineGeometry:
                        if intersec.isMultipart():
                            for parte in intersec.asMultiPolyline():
                                if parte:
                                    parte_ordenada = sorted(parte, key=lambda pt: pt.x() * d_x + pt.y() * d_y)
                                    feat = QgsFeature()
                                    geom_line = QgsGeometry.fromPolylineXY(parte_ordenada)
                                    # Transforma de volta para o CRS original, se necessário
                                    if transform_to_source:
                                        geom_line.transform(transform_to_source)
                                    feat.setGeometry(geom_line)
                                    features_list.append(feat)
                        else:
                            pts = intersec.asPolyline()
                            if pts:
                                pts_ordenados = sorted(pts, key=lambda pt: pt.x() * d_x + pt.y() * d_y)
                                feat = QgsFeature()
                                geom_line = QgsGeometry.fromPolylineXY(pts_ordenados)
                                if transform_to_source:
                                    geom_line.transform(transform_to_source)
                                feat.setGeometry(geom_line)
                                features_list.append(feat)
                current_offset -= spacing

        self.iface.messageBar().popWidget(progressMessageBar)

        if not features_list:
            self.mostrar_mensagem("Não foi possível gerar linhas dentro dos polígonos.", "Erro")
            return

        # Cria a nova camada de memória para as linhas no CRS original da camada de polígonos
        crs = polygon_layer.crs()
        layer_name = "Linhas Dentro dos Polígonos"
        uri = "LineString?crs={}".format(crs.authid())
        new_layer = QgsVectorLayer(uri, layer_name, "memory")
        pr = new_layer.dataProvider()
        pr.addFeatures(features_list)
        new_layer.updateExtents()

        if self.linha_cor is not None:
            symbol = QgsLineSymbol.createSimple({'color': self.linha_cor.name()})
            new_layer.renderer().setSymbol(symbol)

        QgsProject.instance().addMapLayer(new_layer)
        self.mostrar_mensagem("Camada de linhas criada com sucesso.", "Sucesso")

    def selecionar_cor(self):
        """
        Abre um diálogo para escolher a cor. Se uma cor for escolhida,
        armazena em self.linha_cor e atualiza o botão para mostrar essa cor.
        Se o usuário cancelar, mantém o botão com o estilo padrão.
        """
        color = QColorDialog.getColor()
        if color.isValid():
            # Se uma cor válida for escolhida, salva e atualiza o botão
            self.linha_cor = color
            self.pushButtonCor.setStyleSheet(f"background-color: {color.name()};")
        else:
            # Se não escolher (cancelar), mantém o botão com o estilo padrão
            self.linha_cor = None
            self.pushButtonCor.setStyleSheet("")

    def update_pushButtonExecutar(self):
        """
        Habilita o pushButtonExecutar somente se:
          - O comboBoxCamada tiver pelo menos uma camada;
          - O valor do doubleSpinBoxEspassamento for diferente de 0.
        Caso contrário, o botão é desabilitado.
        """
        tem_camadas = self.comboBoxCamada.count() > 0
        espassamento_valido = self.doubleSpinBoxEspassamento.value() != 0
        self.pushButtonExecutar.setEnabled(tem_camadas and espassamento_valido)