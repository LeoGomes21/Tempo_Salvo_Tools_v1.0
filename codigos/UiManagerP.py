from PyQt5.QtWidgets import QInputDialog, QInputDialog, QTreeView, QStyledItemDelegate, QColorDialog, QMenu, QLineEdit, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog, QComboBox, QFrame, QCheckBox, QDoubleSpinBox, QRadioButton, QButtonGroup, QProgressBar, QDialogButtonBox, QGraphicsView, QListWidget, QScrollBar, QDesktopWidget, QGraphicsEllipseItem, QGraphicsScene, QToolTip, QGraphicsPathItem, QGraphicsRectItem, QGraphicsPolygonItem, QGraphicsLineItem, QGraphicsItemGroup
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon, QPixmap, QPainter, QColor, QPen, QFont, QBrush, QGuiApplication, QTransform, QCursor, QPainterPath, QPolygonF, QMouseEvent, QWheelEvent#, QSizePolicy
from PyQt5.QtCore import Qt, QPoint, QRect, QEvent, QCoreApplication, QSettings, QItemSelectionModel, QPointF, QObject
from qgis.core import QgsProject, QgsMapLayer, QgsWkbTypes, QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer, QgsSymbol, Qgis, QgsVectorLayerSimpleLabeling, QgsSimpleLineSymbolLayer, QgsRenderContext, QgsSymbolLayerUtils, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMessageLog, QgsLayerTreeLayer, QgsSymbolLayer, QgsGeometry
from qgis.gui import QgsProjectionSelectionDialog
from PIL import Image, UnidentifiedImageError
import xml.etree.ElementTree as ET
from qgis.utils import iface
from ezdxf import colors
from io import BytesIO
import processing
import requests
import random
import ezdxf
import time
import math
import os
import re

# Importe a função criar_camada_poligonos
from .criar_poligonos import criar_camada_poligonos

class UiManagerP:
    """
    Gerencia a interface do usuário, interagindo com um QTreeView para listar e gerenciar camadas de polígonos no QGIS.
    """
    def __init__(self, iface, dialog):
        """
        Inicializa a instância da classe UiManagerO, responsável por gerenciar a interface do usuário
        que interage com um QTreeView para listar e gerenciar camadas de polígonos no QGIS.

        :param iface: Interface do QGIS para interagir com o ambiente.
        :param dialog: Diálogo ou janela que esta classe gerenciará.

        Funções e Ações Desenvolvidas:
        - Configuração inicial das variáveis de instância.
        - Associação do modelo de dados com o QTreeView.
        - Inicialização da configuração do QTreeView.
        - Seleção automática da última camada no QTreeView.
        - Conexão dos sinais do QGIS e da interface do usuário com os métodos correspondentes.
        """
        # Salva as referências para a interface do QGIS e o diálogo fornecidos
        self.iface = iface
        self.dlg = dialog

        # Cria e configura o modelo de dados para o QTreeView
        self.treeViewModel = QStandardItemModel()
        self.dlg.treeViewListaPoligono.setModel(self.treeViewModel)

        # Inicializa o QTreeView com as configurações necessárias
        self.init_treeView()

        # Seleciona a última camada adicionada para facilitar a interação do usuário
        self.selecionar_ultima_camada()  # Chama a função após a inicialização da árvore

        # Conecta os sinais do QGIS e da interface do usuário para sincronizar ações e eventos
        self.connect_signals()

        # Adiciona o filtro de eventos ao treeView
        self.tree_view_event_filter = TreeViewEventFilter(self)
        self.dlg.treeViewListaPoligono.viewport().installEventFilter(self.tree_view_event_filter)

    def init_treeView(self):
        """
        Configura o QTreeView para listar e gerenciar camadas de polígonos. 
        Este método inicializa a visualização da árvore com os itens e configurações necessárias,
        conecta os eventos de interface do usuário e estiliza os componentes visuais.
        
        Funções e Ações Desenvolvidas:
        - Atualização inicial da lista de camadas no QTreeView.
        - Conexão do evento de duplo clique em itens para tratamento.
        - Conexão do evento de alteração em itens para tratamento.
        - Configuração de delegado para customização da apresentação de itens.
        - Configuração do menu de contexto para interações adicionais.
        - Aplicação de estilos CSS para melhor visualização dos itens.
        - Conexão do botão de exportação para ação de exportar dados.
        """
        # Atualiza a visualização da lista de camadas no QTreeView
        self.atualizar_treeView_lista_poligono()

        # Conecta o evento de duplo clique em um item para manipulação de cores da camada
        self.dlg.treeViewListaPoligono.doubleClicked.connect(self.on_item_double_clicked)

        # Conecta o evento de mudança em um item para atualizar a visibilidade da camada
        self.treeViewModel.itemChanged.connect(self.on_item_changed)

        # Define e aplica um delegado personalizado para customização da exibição de itens no QTreeView
        self.treeViewDelegate = PolygonDelegate(self.dlg.treeViewListaPoligono)
        self.dlg.treeViewListaPoligono.setItemDelegate(self.treeViewDelegate)

        # Configura a política de menu de contexto para permitir menus personalizados em cliques com o botão direito
        self.dlg.treeViewListaPoligono.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dlg.treeViewListaPoligono.customContextMenuRequested.connect(self.open_context_menu)

        # Aplica estilos CSS para aprimorar a interação visual com os itens do QTreeView
        self.dlg.treeViewListaPoligono.setStyleSheet("""
            QTreeView::item:hover:!selected {
                background-color: #def2fc;
            }
            QTreeView::item:selected {
            }""")

        # Conecta o botão para criar uma camada de polígonos ao método que adiciona a camada e atualiza o treeView
        self.dlg.ButtonCriarPoligono.clicked.connect(self.adicionar_camada_e_atualizar)

        # Conecta o botão ao novo método do botão cria uma camada com o nome
        self.dlg.ButtonCriarPoligonoNome.clicked.connect(self.abrir_caixa_nome_camada)

        # Conecta o botão de exportação DXF a uma função que maneja a exportação de camadas
        self.dlg.pushButtonExportaDXF_P.clicked.connect(self.exportar_para_dxf)

        # Conecta o botão para exportar a camada para KML
        self.dlg.pushButtonExportaKml_2.clicked.connect(self.exportar_para_kml)

    def configurar_tooltip(self, index):
        """
        Configura um tooltip para exibir informações sobre a camada de ponto selecionada no treeView.

        A função extrai informações sobre a camada de ponto, como o tipo de geometria (ex: Point, MultiPoint) 
        e o sistema de referência de coordenadas (SRC) atual da camada. Essas informações são exibidas em 
        um tooltip que aparece quando o usuário passa o mouse sobre o item correspondente no treeView.

        Parâmetros:
        - index: QModelIndex do item atualmente sob o cursor no treeView.
        """
        item = index.model().itemFromIndex(index)  # Obtém o item do modelo de dados com base no índice fornecido
        layer_id = item.data(Qt.UserRole)  # Obtém o ID da camada associada ao item
        layer = QgsProject.instance().mapLayer(layer_id)  # Recupera a camada correspondente ao ID no projeto QGIS
        if layer:  # Verifica se a camada existe
            tipo_poligono = self.obter_tipo_de_poligono(layer)  # Obtém o tipo de geometria da camada (ex: Point, MultiPoint)
            crs = layer.crs().description() if layer.crs().isValid() else "Sem Georreferenciamento"  # Obtém a descrição do SRC da camada ou "Sem Georreferenciamento" se inválido
            tooltip_text = f"Tipo: {tipo_poligono}\nSRC: {crs}"  # Formata o texto do tooltip com as informações da camada
            QToolTip.showText(QCursor.pos(), tooltip_text)  # Exibe o tooltip na posição atual do cursor

    def obter_tipo_de_poligono(self, layer):
        """
        Retorna uma string que descreve o tipo de geometria da camada fornecida.

        A função obtém o tipo de geometria WKB (Well-Known Binary) da camada e converte esse tipo
        em uma string legível, como 'Point', 'MultiPoint', etc.

        Parâmetros:
        - layer: Objeto QgsVectorLayer representando a camada de onde o tipo de ponto será extraído.

        Retorno:
        - tipo_poligono (str): Uma string que descreve o tipo de geometria da camada.
        """
        geometry_type = layer.wkbType()  # Obtém o tipo de geometria WKB (Well-Known Binary) da camada
        tipo_poligono = QgsWkbTypes.displayString(geometry_type)  # Converte o tipo de geometria em uma string legível
        return tipo_poligono  # Retorna a string que descreve o tipo de geometria

    def adicionar_camada_e_atualizar(self):
        """
        Método chamado ao clicar no botão para criar uma camada de polígono.
        Cria a camada de polígono e atualiza o treeView.
        """
        # Chamada para a função que cria uma nova camada de polígonos
        criar_camada_poligonos(self.iface)

        # Após adicionar a camada, atualize o treeView
        self.atualizar_treeView_lista_poligono()

    def abrir_caixa_nome_camada(self):
        """
        Esta função cria uma caixa de diálogo que permite ao usuário inserir o nome de uma nova camada.
        A caixa de diálogo contém um campo de texto e dois botões: 'BLZ' e 'Cancelar'.
        O botão 'BLZ' é ativado somente quando o campo de texto não está vazio.
        Se o usuário clicar em 'BLZ', a função 'criar_camada_poligonos' é chamada e a árvore de visualização é atualizada.
        """
        dialog = QDialog(self.dlg) # Cria uma nova caixa de diálogo
        dialog.setWindowTitle("Nome da Camada") # Define o título da caixa de diálogo
        layout = QVBoxLayout(dialog) # Define o layout da caixa de diálogo
        layout.addWidget(QLabel("Digite o nome da camada:")) # Adiciona um rótulo ao layout

        lineEdit = QLineEdit() # Cria um novo campo de texto
        lineEdit.setPlaceholderText("Camada Temporária") # Define o texto do espaço reservado para o campo de texto
        layout.addWidget(lineEdit) # Adiciona o campo de texto ao layout

        okButton = QPushButton("BLZ") # Cria botões OK e Cancelar
        cancelButton = QPushButton("Cancelar") # Cria um novo botão 'Cancelar'

        okButton.clicked.connect(dialog.accept) # Conecta o clique do botão 'BLZ' à função 'accept' da caixa de diálogo
        cancelButton.clicked.connect(dialog.reject) # Conecta o clique do botão 'Cancelar' à função 'reject' da caixa de diálogo

        okButton.setEnabled(False) # Desativa o botão 'BLZ' por padrão

        # Ativa o botão 'BLZ' quando o campo de texto não está vazio
        lineEdit.textChanged.connect(lambda: okButton.setEnabled(bool(lineEdit.text().strip())))

        buttonLayout = QHBoxLayout()  # Cria um novo layout horizontal para os botões
        buttonLayout.addWidget(okButton)  # Adiciona o botão 'BLZ' ao layout do botão
        buttonLayout.addWidget(cancelButton)  # Adiciona o botão 'Cancelar' ao layout do botão
        layout.addLayout(buttonLayout)  # Adiciona o layout do botão ao layout principal

        # Se a caixa de diálogo for aceita e o campo de texto não estiver vazio, cria uma nova camada e atualiza a árvore de visualização
        if dialog.exec_() == QDialog.Accepted and lineEdit.text().strip():
            nome_camada = lineEdit.text().strip()  # Obtém o nome da camada do campo de texto
            criar_camada_poligonos(self.iface, nome_camada)  # Cria uma nova camada de polígonos
            self.atualizar_treeView_lista_poligono()  # Atualiza a árvore de visualização

    def connect_signals(self):
        """
        Conecta os sinais do QGIS e do QTreeView para sincronizar a interface com o estado atual do projeto.
        Este método garante que mudanças no ambiente do QGIS se reflitam na interface do usuário e que ações na
        interface desencadeiem reações apropriadas no QGIS.

        Funções e Ações Desenvolvidas:
        - Conexão com sinais de adição e remoção de camadas para atualizar a visualização da árvore.
        - Sincronização do modelo do QTreeView com mudanças de seleção e propriedades das camadas no QGIS.
        - Tratamento da mudança de nome das camadas para manter consistência entre a interface e o estado interno.
        """
        # Conecta sinais do QGIS para lidar com a adição e remoção de camadas no projeto
        QgsProject.instance().layersAdded.connect(self.layers_added)
        QgsProject.instance().layersRemoved.connect(self.atualizar_treeView_lista_poligono)

        # Conecta o evento de mudança em um item do QTreeView para atualizar a visibilidade da camada no QGIS
        self.treeViewModel.itemChanged.connect(self.on_item_changed)

        # Sincroniza o estado das camadas no QGIS com o checkbox do QTreeView sempre que as camadas do mapa mudam
        self.iface.mapCanvas().layersChanged.connect(self.sync_from_qgis_to_treeview)

        # Conecta mudanças na seleção do QTreeView para atualizar a camada ativa no QGIS
        self.dlg.treeViewListaPoligono.selectionModel().selectionChanged.connect(self.on_treeview_selection_changed)

        # Sincroniza a seleção no QGIS com a seleção no QTreeView quando a camada ativa no QGIS muda
        self.iface.currentLayerChanged.connect(self.on_current_layer_changed)

        # Inicia a conexão de sinais para tratar a mudança de nome das camadas no projeto
        self.connect_name_changed_signals()

        # Conecta o botão para reprojetar a camada
        self.dlg.pushButtonReprojetarP.clicked.connect(self.abrir_dialogo_crs)

        # Conectando o botão pushButtonFecharP à função que fecha o diálogo
        self.dlg.pushButtonFecharP.clicked.connect(self.close_dialog)

    def close_dialog(self):
        """
        Fecha o diálogo associado a este UiManagerP:
        """
        self.dlg.close()

    def abrir_dialogo_crs(self):
        """
        Abre um diálogo de seleção de CRS e reprojeta a camada de pontos selecionada no treeViewListaPolígono.

        A função permite ao usuário escolher um novo sistema de referência de coordenadas (SRC) para a camada 
        selecionada no treeViewListaPoligono. Após a seleção, a camada é reprojetada usando o novo SRC, e a nova camada é 
        adicionada ao projeto QGIS com a mesma cor de ícone e rótulo da camada original.

        Parâmetros:
        - self: Referência à instância atual do objeto. (UiManagerP)

        A função não retorna valores, mas adiciona uma nova camada reprojetada ao projeto QGIS.
        """
        index = self.dlg.treeViewListaPoligono.currentIndex()  # Obtém o índice atualmente selecionado no treeViewListaPolígono
        if not index.isValid():  # Verifica se o índice é válido (se há uma seleção)
            return  # Sai da função se o índice não for válido
        
        layer_id = index.model().itemFromIndex(index).data(Qt.UserRole)  # Obtém o ID da camada associada ao item selecionado
        layer = QgsProject.instance().mapLayer(layer_id)  # Recupera a camada correspondente ao ID no projeto QGIS
        if not layer or layer.geometryType() != QgsWkbTypes.PolygonGeometry:  # Verifica se a camada existe e é de pontos
            self.mostrar_mensagem("Por favor, selecione uma camada de pontos válida.", "Aviso")  # Exibe uma mensagem de aviso
            return  # Sai da função se a camada não for de pontos
        
        # Abre o diálogo de seleção de CRS para que o usuário possa escolher um novo SRC
        dialog = QgsProjectionSelectionDialog(self.dlg)  # Cria uma instância do diálogo de seleção de CRS
        dialog.setCrs(layer.crs())  # Configura o CRS atual da camada como o CRS padrão no diálogo
        if dialog.exec_():  # Exibe o diálogo e verifica se o usuário confirmou a seleção
            novo_crs = dialog.crs()  # Obtém o novo CRS selecionado pelo usuário

            # Usa o processamento do QGIS para reprojetar a camada
            params = {
                'INPUT': layer,  # Define a camada original como entrada
                'TARGET_CRS': novo_crs,  # Define o novo CRS como o CRS alvo
                'OUTPUT': 'memory:'  # Salva o resultado na memória
            }
            resultado = processing.run('qgis:reprojectlayer', params)  # Executa o processo de reprojeção
            nova_camada = resultado['OUTPUT']  # Obtém a nova camada reprojetada a partir dos resultados

            # Verifique se a nova camada tem feições válidas
            if nova_camada and nova_camada.isValid():  # Verifica se a nova camada foi criada corretamente
                # Gerar nome único para a nova camada reprojetada
                novo_nome = self.gerar_nome_unico_rep(layer.name())  # Gera um nome único para evitar duplicidades
                nova_camada.setName(novo_nome)  # Define o nome da nova camada

                # # Aplicar as cores do ícone e do rótulo da camada original
                # cor_icone = self.obter_cor_icone(layer)  # Obtém a cor do ícone da camada original
                # cor_rotulo = self.obter_cor_rotulo(layer)  # Obtém a cor do rótulo da camada original

                # self.aplicar_simbologia_com_cores_qgis(nova_camada, cor_icone, cor_rotulo)  # Aplica a simbologia

                QgsProject.instance().addMapLayer(nova_camada)  # Adiciona a nova camada reprojetada ao projeto

                # Atualiza a camada na tela
                layer.triggerRepaint()  # Recarrega a camada original (caso necessário)
                self.iface.mapCanvas().refresh()  # Atualiza a tela do mapa para refletir a nova camada

                # Exibe uma mensagem informando que a camada foi reprojetada
                texto_mensagem = f"A camada '{layer.name()}' foi reprojetada para {novo_crs.authid()} ({novo_crs.description()}) com o nome '{novo_nome}'."  # Cria a mensagem de sucesso
                self.mostrar_mensagem(texto_mensagem, "Sucesso")  # Exibe a mensagem na barra de mensagens do QGIS
            else:
                self.mostrar_mensagem(f"Erro na reprojeção da camada '{layer.name()}'.", "Erro")  # Exibe uma mensagem de erro se a reprojeção falhar

    def gerar_nome_unico_rep(self, base_nome):
        """
        Gera um nome único para uma nova camada baseada no nome da camada original.

        A função cria um novo nome para a camada reprojetada, adicionando um sufixo incremental 
        (_rep1, _rep2, etc.) ao nome base, garantindo que o novo nome seja único dentro do projeto QGIS.

        Parâmetros:
        - self: Referência à instância atual do objeto. (UiManager)
        - base_nome (str): O nome original da camada, usado como base para gerar o novo nome.

        Retorno:
        - novo_nome (str): Um nome único gerado para a nova camada reprojetada.
        """
        # Cria um conjunto contendo todos os nomes de camadas existentes no projeto QGIS
        existing_names = {layer.name() for layer in QgsProject.instance().mapLayers().values()}

        # Se o nome base ainda não existir no projeto, retorna com o sufixo _rep1
        if base_nome not in existing_names:
            return f"{base_nome}_rep1"
        # Inicia o contador de sufixos em 1
        i = 1
        # Gera o primeiro nome com o sufixo _rep1
        novo_nome = f"{base_nome}_rep{i}"

        # Incrementa o sufixo até encontrar um nome que não exista no projeto
        while novo_nome in existing_names:
            i += 1
            novo_nome = f"{base_nome}_rep{i}"
        # Retorna o nome único gerado
        return novo_nome

    def on_treeview_selection_changed(self, selected, deselected):
        """
        Reage às mudanças de seleção no QTreeView, atualizando a camada ativa no QGIS.
        Este método é chamado sempre que o usuário seleciona ou desseleciona uma camada na lista do QTreeView.
        
        Funções e Ações Desenvolvidas:
        - Obtenção do nome da camada selecionada no QTreeView.
        - Busca da camada correspondente no projeto do QGIS.
        - Atualização da camada ativa no QGIS para corresponder à seleção do usuário.

        :param selected: Índices dos itens que foram selecionados (não utilizado diretamente neste método).
        :param deselected: Índices dos itens que foram desselecionados (não utilizado diretamente neste método).
        """
        # Obtém os índices dos itens selecionados no QTreeView
        indexes = self.dlg.treeViewListaPoligono.selectionModel().selectedIndexes()
        if indexes:
            # Extrai o nome da camada do item selecionado no QTreeView
            selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
            # Busca a camada por nome no projeto do QGIS
            layers = QgsProject.instance().mapLayersByName(selected_layer_name)
            # Se a camada existir, define-a como a camada ativa
            if layers:
                self.iface.setActiveLayer(layers[0])

    def connect_name_changed_signals(self):
        """
        Conecta o sinal de mudança de nome de todas as camadas de polígono existentes no projeto QGIS.
        Este método percorre todas as camadas listadas no QgsLayerTreeRoot e, para cada camada,
        conecta o evento de mudança de nome à função de callback on_layer_name_changed.

        Funções e Ações Desenvolvidas:
        - Busca e iteração por todas as camadas no projeto QGIS.
        - Conexão do sinal de mudança de nome da camada ao método correspondente para tratamento.
        """
        # Acessa a raiz da árvore de camadas do projeto QGIS
        root = QgsProject.instance().layerTreeRoot()
        # Itera por todos os nós de camadas na árvore de camadas
        for layerNode in root.findLayers():
            # Verifica se o nó é uma instância de QgsLayerTreeLayer
            if isinstance(layerNode, QgsLayerTreeLayer):
                # Conecta o sinal de mudança de nome da camada ao método de tratamento on_layer_name_changed
                layerNode.layer().nameChanged.connect(self.on_layer_name_changed)

    def layers_added(self, layers):
        """
        Responde ao evento de adição de camadas no projeto QGIS, atualizando a lista de camadas no QTreeView
        e conectando sinais de mudança de nome para camadas de polígonos recém-adicionadas.

        Este método verifica cada camada adicionada para determinar se é uma camada de vetor de polígonos.
        Se for, ele atualiza a lista de camadas no QTreeView e conecta o sinal de mudança de nome à função
        de callback apropriada.

        :param layers: Lista de camadas recém-adicionadas ao projeto.

        Funções e Ações Desenvolvidas:
        - Verificação do tipo e da geometria das camadas adicionadas.
        - Atualização da visualização da lista de camadas no QTreeView para incluir novas camadas de polígonos.
        - Conexão do sinal de mudança de nome da camada ao método de tratamento correspondente.
        """
        # Itera por todas as camadas adicionadas
        for layer in layers:
            # Verifica se a camada é do tipo vetor e se sua geometria é de polígono
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                # Atualiza a lista de camadas no QTreeView
                self.atualizar_treeView_lista_poligono()
                # Conecta o sinal de mudança de nome da nova camada ao método on_layer_name_changed
                layer.nameChanged.connect(self.on_layer_name_changed)
                # Interrompe o loop após adicionar o sinal à primeira camada de polígono encontrada
                break

    def on_layer_name_changed(self):
        """
        Responde ao evento de mudança de nome de qualquer camada no projeto QGIS. 
        Este método é chamado automaticamente quando o nome de uma camada é alterado,
        e sua função é garantir que a lista de camadas no QTreeView seja atualizada para refletir
        essa mudança.

        Funções e Ações Desenvolvidas:
        - Atualização da lista de camadas no QTreeView para assegurar que os nomes das camadas estejam corretos.
        """
        # Atualiza a lista de camadas no QTreeView para refletir a mudança de nome
        self.atualizar_treeView_lista_poligono()

    def update_treeview_selection_from_qgis(self, layer):
        """
        Sincroniza a seleção no QTreeView com a camada ativa no QGIS. Quando uma camada é selecionada
        diretamente no QGIS, este método atualiza a seleção no QTreeView para refletir essa escolha.

        Este método verifica todas as entradas no QTreeView e seleciona aquela que corresponde ao nome
        da camada ativa no QGIS.

        :param layer: A camada atualmente ativa no QGIS que deve ser refletida na interface do usuário.

        Funções e Ações Desenvolvidas:
        - Limpeza da seleção atual no QTreeView para evitar seleções múltiplas ou desatualizadas.
        - Busca e seleção da camada correspondente no modelo do QTreeView.
        - Scrolling automático para o item selecionado, garantindo sua visibilidade.
        """
        # Limpa a seleção atual no modelo do QTreeView para garantir que não haja itens duplicadamente selecionados
        self.dlg.treeViewListaPoligono.selectionModel().clearSelection()

        # Verifica se uma camada foi fornecida
        if layer:
            # Itera por todos os itens no modelo do QTreeView
            for i in range(self.treeViewModel.rowCount()):
                item = self.treeViewModel.item(i)
                # Encontra o item que corresponde ao nome da camada ativa no QGIS
                if item and item.text() == layer.name():
                    # Obtém o índice do item correspondente no modelo
                    index = self.treeViewModel.indexFromItem(item)
                    # Seleciona o item no QTreeView e garante que ele esteja visível para o usuário
                    self.dlg.treeViewListaPoligono.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                    self.dlg.treeViewListaPoligono.scrollTo(index)
                    break  # Encerra o loop após a seleção ser feita para evitar processamento desnecessário

    def adjust_item_font(self, item, layer):
        """
        Ajusta a fonte do item no QTreeView com base no tipo de fonte de dados da camada associada.
        Este método modifica a fonte para itálico se a camada for temporária (em memória) e para negrito se for permanente.

        A visualização visual das camadas como itálicas ou negritas ajuda o usuário a identificar rapidamente
        o tipo de camada (temporária vs. permanente) diretamente pela interface do usuário.

        :param item: O item no QTreeView que representa uma camada no QGIS.
        :param layer: A camada do QGIS associada ao item no QTreeView.

        :return: Retorna o item com a fonte ajustada.

        Funções e Ações Desenvolvidas:
        - Configuração da fonte para itálico se a fonte de dados da camada for 'memory' (temporária).
        - Configuração da fonte para negrito se a fonte de dados da camada for permanente.
        """
        # Cria um objeto QFont para ajustar a fonte do item
        fonte_item = QFont()

        # Verifica se a camada é temporária (dados em memória) e ajusta a fonte para itálico
        if layer.dataProvider().name() == 'memory':
            fonte_item.setItalic(True)
        # Se não for temporária, ajusta a fonte para negrito, indicando uma camada permanente
        else:
            fonte_item.setBold(True)

        # Aplica a fonte ajustada ao item no QTreeView
        item.setFont(fonte_item)

        # Retorna o item com a fonte ajustada para uso posterior se necessário
        return item

    def atualizar_treeView_lista_poligono(self):
        """
        Esta função atualiza a lista de camadas de polígonos no QTreeView. 
        Ela limpa o modelo existente, adiciona um cabeçalho, 
        itera sobre todas as camadas no projeto do QGIS, filtra as camadas de polígonos,
        cria itens para essas camadas e ajusta a fonte dos itens conforme necessário.
        Por fim, garante que a última camada esteja selecionada no QTreeView.

        Detalhes:
        - Limpa o modelo do QTreeView.
        - Adiciona um item de cabeçalho ao modelo.
        - Obtém a raiz da árvore de camadas do QGIS e todas as camadas do projeto.
        - Itera sobre todas as camadas do projeto.
            - Filtra para incluir apenas camadas de polígonos.
            - Cria um item para cada camada de polígonos com nome, verificável e não editável diretamente.
            - Define o estado de visibilidade do item com base no estado do nó da camada.
            - Ajusta a fonte do item com base no tipo de camada (temporária ou permanente).
            - Adiciona o item ao modelo do QTreeView.
        - Seleciona a última camada no QTreeView.
        """
        # Limpa o modelo existente para assegurar que não haja itens desatualizados
        self.treeViewModel.clear()
        
        # Cria e configura um item de cabeçalho para a lista
        headerItem = QStandardItem('Lista de Camadas de Polígonos')
        headerItem.setTextAlignment(Qt.AlignCenter)
        self.treeViewModel.setHorizontalHeaderItem(0, headerItem)

        # Acessa a raiz da árvore de camadas do QGIS para obter todas as camadas
        root = QgsProject.instance().layerTreeRoot()
        layers = QgsProject.instance().mapLayers().values()

        # Itera sobre todas as camadas do projeto
        for layer in layers:
            # Filtra para incluir apenas camadas de polígonos
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                # Cria um item para a camada com nome, verificável e não editável diretamente
                item = QStandardItem(layer.name())
                item.setCheckable(True)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(layer.id(), Qt.UserRole)

                # Encontra o nó correspondente na árvore de camadas para definir o estado de visibilidade
                layerNode = root.findLayer(layer.id())
                item.setCheckState(Qt.Checked if layerNode and layerNode.isVisible() else Qt.Unchecked)

                # Ajusta a fonte do item com base no tipo de camada (temporária ou permanente)
                self.adjust_item_font(item, layer)

                # Adiciona o item ao modelo do QTreeView
                self.treeViewModel.appendRow(item)
        
        # Seleciona a última camada no QTreeView para garantir que uma camada esteja sempre selecionada
        self.selecionar_ultima_camada()

    def selecionar_ultima_camada(self):
        """
        Esta função garante que uma camada de polígonos esteja sempre selecionada no QTreeView.
        Se houver camadas no modelo, seleciona a última camada.
        Se não houver camadas, tenta selecionar a primeira camada disponível.

        Detalhes:
        - Obtém o modelo associado ao QTreeView.
        - Conta o número de linhas (camadas) no modelo.
        - Se houver camadas:
            - Obtém o índice da última camada no modelo.
            - Define a seleção atual para o índice da última camada e garante que esteja visível.
        - Se não houver camadas:
            - Obtém o índice da primeira camada.
            - Se válido, define a seleção atual para o índice da primeira camada e garante que esteja visível.
        """
        # Obtém o modelo associado ao QTreeView
        model = self.dlg.treeViewListaPoligono.model()
        
        # Conta o número de linhas (camadas) no modelo
        row_count = model.rowCount()

        # Verifica se há camadas no modelo
        if row_count > 0:
            # Obtém o índice da última camada no modelo
            last_index = model.index(row_count - 1, 0)
            
            # Define a seleção atual para o índice da última camada
            self.dlg.treeViewListaPoligono.setCurrentIndex(last_index)
            
            # Garante que a última camada esteja visível no QTreeView
            self.dlg.treeViewListaPoligono.scrollTo(last_index)
        else:
            # Obtém o índice da primeira camada no modelo
            first_index = model.index(0, 0)
            
            # Verifica se o índice da primeira camada é válido
            if first_index.isValid():
                # Define a seleção atual para o índice da primeira camada
                self.dlg.treeViewListaPoligono.setCurrentIndex(first_index)
                
                # Garante que a primeira camada esteja visível no QTreeView
                self.dlg.treeViewListaPoligono.scrollTo(first_index)

    def on_current_layer_changed(self, layer):
        """
        Esta função é chamada quando a camada ativa no QGIS muda.
        Ela verifica se a camada ativa é uma camada de polígonos e, se for, 
        atualiza a seleção no QTreeView para corresponder à camada ativa.
        Se a camada ativa não for uma camada de polígonos, reverte a seleção 
        para a última camada de polígonos selecionada no QTreeView.

        Detalhes:
        - Verifica se a camada ativa existe e se é uma camada de polígonos.
        - Se for uma camada de polígonos:
            - Obtém o modelo associado ao QTreeView.
            - Itera sobre todas as linhas no modelo para encontrar a camada correspondente.
            - Quando encontrada, seleciona e garante que a camada esteja visível no QTreeView.
        - Se a camada ativa não for uma camada de polígonos, seleciona a última camada de polígonos no QTreeView.
        """
        # Verifica se a camada ativa existe e se é uma camada de polígonos
        if layer and layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            # Obtém o modelo associado ao QTreeView
            model = self.dlg.treeViewListaPoligono.model()
            
            # Itera sobre todas as linhas no modelo
            for row in range(model.rowCount()):
                # Obtém o item da linha atual
                item = model.item(row, 0)
                
                # Verifica se o nome do item corresponde ao nome da camada ativa
                if item.text() == layer.name():
                    # Obtém o índice do item correspondente
                    index = model.indexFromItem(item)
                    
                    # Define a seleção atual para o índice do item correspondente
                    self.dlg.treeViewListaPoligono.setCurrentIndex(index)
                    
                    # Garante que o item correspondente esteja visível no QTreeView
                    self.dlg.treeViewListaPoligono.scrollTo(index)
                    
                    # Interrompe a iteração, pois a camada correspondente foi encontrada
                    break
        else:
            # Se a camada ativa não for uma camada de polígonos, seleciona a última camada de polígonos no QTreeView
            self.selecionar_ultima_camada()

    def on_layer_was_renamed(self, layerId, newName):
        """
        Responde ao evento de renomeação de uma camada no QGIS, atualizando o nome da camada no QTreeView.
        Este método garante que as mudanças de nome no projeto sejam refletidas na interface do usuário.

        :param layerId: ID da camada que foi renomeada.
        :param newName: Novo nome atribuído à camada.

        Funções e Ações Desenvolvidas:
        - Pesquisa no modelo do QTreeView pelo item que corresponde à camada renomeada.
        - Atualização do texto do item no QTreeView para refletir o novo nome.
        """
        # Itera sobre todos os itens no modelo do QTreeView para encontrar o item correspondente
        for i in range(self.treeViewModel.rowCount()):
            item = self.treeViewModel.item(i)
            layer = QgsProject.instance().mapLayer(layerId)
            # Verifica se o item corresponde à camada que foi renomeada
            if layer and item.text() == layer.name():
                item.setText(newName)  # Atualiza o nome do item no QTreeView
                break  # Sai do loop após atualizar o nome

    def on_item_changed(self, item):
        """
        Responde a mudanças nos itens do QTreeView, especificamente ao estado do checkbox, sincronizando a visibilidade
        da camada correspondente no QGIS. Este método assegura que ações na interface do usuário sejam refletidas no
        estado visual das camadas no mapa.

        :param item: Item do QTreeView que foi alterado (geralmente, uma mudança no estado do checkbox).

        Funções e Ações Desenvolvidas:
        - Busca da camada correspondente no projeto QGIS usando o nome do item.
        - Ajuste da visibilidade da camada na árvore de camadas do QGIS com base no estado do checkbox do item.
        """
        # Encontra a camada correspondente no projeto QGIS pelo nome do item
        layer = QgsProject.instance().mapLayersByName(item.text())
        if not layer:
            return  # Se a camada não for encontrada, interrompe o método

        layer = layer[0]  # Assume a primeira camada encontrada (nomes deveriam ser únicos)

        # Encontra o QgsLayerTreeLayer correspondente na árvore de camadas
        root = QgsProject.instance().layerTreeRoot()
        node = root.findLayer(layer.id())

        if node:
            # Ajusta a visibilidade da camada com base no estado do checkbox do item
            node.setItemVisibilityChecked(item.checkState() == Qt.Checked)

    def sync_from_qgis_to_treeview(self):
        """
        Sincroniza o estado do checkbox no QTreeView com a visibilidade das camadas no QGIS.
        Este método garante que as alterações na visibilidade das camadas, feitas através do QGIS,
        sejam refletidas nos checkboxes correspondentes no QTreeView.

        Funções e Ações Desenvolvidas:
        - Obtenção da lista atual de camadas visíveis no canvas do QGIS.
        - Iteração pelos itens do QTreeView para ajustar o estado do checkbox com base na visibilidade de cada camada.

        Observação: Este método assume que os nomes das camadas são únicos, o que permite a correspondência direta entre
        o item no QTreeView e a camada no QGIS.
        """
        # Acessa a raiz da árvore de camadas do projeto QGIS
        root = QgsProject.instance().layerTreeRoot()
        # Obtém as camadas atualmente visíveis no canvas do QGIS
        layers = self.iface.mapCanvas().layers()
        layer_names = [layer.name() for layer in layers]  # Lista de nomes das camadas visíveis

        # Itera por cada item no modelo do QTreeView
        for i in range(self.treeViewModel.rowCount()):
            item = self.treeViewModel.item(i)
            if item:
                # Busca a camada correspondente no QGIS pelo nome do item
                layerNode = root.findLayer(QgsProject.instance().mapLayersByName(item.text())[0].id())
                if layerNode:
                    # Ajusta o estado do checkbox com base na visibilidade da camada correspondente
                    item.setCheckState(Qt.Checked if layerNode.isVisible() else Qt.Unchecked)

    def on_item_double_clicked(self, index):
        """
        Manipula o evento de duplo clique em um item do QTreeView. Este método é acionado quando um usuário
        efetua um duplo clique em uma camada listada, permitindo que altere as cores de preenchimento e borda da camada.

        Funções e Ações Desenvolvidas:
        - Recuperação da camada associada ao item clicado.
        - Obtenção das cores atuais de preenchimento e borda da camada.
        - Exibição de um diálogo para que o usuário selecione novas cores.
        - Aplicação das cores selecionadas à camada, se novas cores foram escolhidas.

        :param index: QModelIndex que representa o item no modelo que foi duplo clicado.
        """
        # Obtém o ID da camada do item clicado usando o UserRole
        layer_id = index.model().itemFromIndex(index).data(Qt.UserRole)
        # Busca a camada correspondente no projeto QGIS usando o ID
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:
            # Obtém as cores atuais de preenchimento e borda da camada
            current_fill_color, current_border_color = self.get_polygon_colors(layer)
            # Solicita ao usuário que selecione novas cores para preenchimento e borda
            new_fill_color, new_border_color = self.prompt_for_new_colors(current_fill_color, current_border_color)
            # Se novas cores forem selecionadas, aplica estas cores à camada
            if new_fill_color and new_border_color:
                self.apply_new_colors(layer, new_fill_color, new_border_color)

    def get_polygon_colors(self, layer):
        """
        Obtém as cores de preenchimento e borda de um polígono a partir da camada especificada.
        Este método acessa o renderizador da camada para extrair as configurações de cor atuais do símbolo do polígono.
        
        Funções e Ações Desenvolvidas:
        - Acesso ao renderizador da camada para obter os símbolos usados na renderização.
        - Extração da cor de preenchimento e da cor da borda do primeiro símbolo de polígono.
        - Retorno das cores obtidas ou (None, None) se as cores não puderem ser determinadas.
        
        :param layer: Camada do QGIS de onde as cores serão obtidas (deve ser uma camada de vetor de polígono).
        
        :return: Uma tupla contendo a cor de preenchimento e a cor da borda do polígono, respectivamente.
                 Retorna (None, None) se não conseguir extrair as cores.
        """
        # Acessa o renderizador da camada para obter a lista de símbolos usados na renderização
        symbols = layer.renderer().symbols(QgsRenderContext())
        if symbols:
            # Extrai a cor de preenchimento do primeiro símbolo (geralmente usado para o preenchimento de polígonos)
            fill_color = symbols[0].color()
            # Define uma cor padrão para a borda caso não seja especificada
            border_color = Qt.black  # Cor padrão se não houver contorno definido
            # Verifica se há camadas de símbolo no símbolo do polígono
            if symbols[0].symbolLayerCount() > 0:
                border_layer = symbols[0].symbolLayer(0)
                # Se o símbolo da borda tiver uma propriedade de cor de borda, extrai essa cor
                if hasattr(border_layer, 'strokeColor'):
                    border_color = border_layer.strokeColor()
            # Retorna as cores de preenchimento e borda
            return fill_color, border_color
        # Retorna None para ambos se não houver símbolos ou se as cores não puderem ser determinadas
        return None, None

    def apply_new_colors(self, layer, fill_color, border_color):
        """
        Aplica novas cores de preenchimento e borda à camada especificada. Este método atualiza o renderizador
        da camada com um novo símbolo criado a partir das cores selecionadas, garantindo que as alterações de cor
        sejam visualmente refletidas no mapa do QGIS.

        Funções e Ações Desenvolvidas:
        - Criação de um novo símbolo com as cores de preenchimento e borda especificadas.
        - Configuração de um novo renderizador para a camada usando o símbolo criado.
        - Atualização da camada no QGIS para refletir as novas cores.

        :param layer: Camada do QGIS que terá suas cores alteradas.
        :param fill_color: Nova cor de preenchimento para a camada.
        :param border_color: Nova cor de borda para a camada.
        """
        # Cria um novo símbolo com as cores selecionadas baseado no tipo de geometria da camada
        new_symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        new_symbol.setColor(fill_color)  # Define a cor de preenchimento do novo símbolo
        new_symbol.symbolLayer(0).setStrokeColor(border_color)  # Define a cor da borda no primeiro símbolo da camada

        # Cria um novo renderizador usando o novo símbolo e aplica à camada
        new_renderer = QgsSingleSymbolRenderer(new_symbol)
        layer.setRenderer(new_renderer)  # Atualiza o renderizador da camada

        # Dispara o processo de repintura para atualizar a visualização da camada no mapa
        layer.triggerRepaint()
        # Emite um sinal para notificar que a camada foi adicionada (usado para atualizar interfaces de usuário dependentes)
        QgsProject.instance().layerWasAdded.emit(layer)
        # Refresca a simbologia da camada na árvore de camadas do QGIS para garantir que as mudanças sejam visíveis
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    def prompt_for_new_colors(self, current_fill_color, current_border_color):
        """
        Exibe diálogos de seleção de cor para que o usuário escolha novas cores de preenchimento e borda para uma camada.
        Este método usa o QColorDialog para permitir a seleção visual das cores, proporcionando uma interface amigável
        e intuitiva.

        Funções e Ações Desenvolvidas:
        - Exibição de diálogos para seleção de cores para a borda e o preenchimento da camada.
        - Verificação da validade das cores selecionadas.
        - Retorno das novas cores selecionadas, ou cores transparentes se nenhuma cor válida for escolhida.

        :param current_fill_color: Cor atual de preenchimento da camada, usada como valor inicial no diálogo.
        :param current_border_color: Cor atual da borda da camada, usada como valor inicial no diálogo.

        :return: Uma tupla contendo as novas cores de preenchimento e borda. Retorna cores transparentes se o usuário
                 cancelar a seleção ou selecionar uma cor inválida.
        """
        # Inicializa as variáveis de cor como None para verificar se houve seleção
        new_fill_color = None
        new_border_color = None

        # Solicita ao usuário que selecione uma nova cor da borda
        border_color_dialog = QColorDialog.getColor(current_border_color, self.dlg, "Escolha a Cor da Borda")
        if border_color_dialog.isValid():
            new_border_color = border_color_dialog
        else:
            new_border_color = QColor(0, 0, 0, 0)  # Define cor transparente se nenhuma cor válida for selecionada

        # Solicita ao usuário que selecione uma nova cor de preenchimento
        fill_color_dialog = QColorDialog.getColor(current_fill_color, self.dlg, "Escolha a Cor de Preenchimento")
        if fill_color_dialog.isValid():
            new_fill_color = fill_color_dialog
        else:
            new_fill_color = QColor(0, 0, 0, 0)  # Define cor transparente se nenhuma cor válida for selecionada

        # Retorna as novas cores selecionadas
        return new_fill_color, new_border_color

    def abrir_layer_properties(self, index):
        """
        Abre a janela de propriedades da camada selecionada no QTreeView. Este método é chamado quando o usuário deseja
        ver ou editar as propriedades de uma camada específica, como símbolos, campos e outras configurações.

        Funções e Ações Desenvolvidas:
        - Obtenção do ID da camada a partir do item selecionado no QTreeView.
        - Recuperação da camada correspondente no projeto QGIS.
        - Exibição da janela de propriedades da camada se ela for encontrada.

        :param index: O índice do modelo que representa o item selecionado no QTreeView.
        """
        # Obtém o ID da camada do item selecionado no treeView
        layer_id = index.model().itemFromIndex(index).data(Qt.UserRole)
        # Busca a camada correspondente no projeto QGIS usando o ID
        layer = QgsProject.instance().mapLayer(layer_id)
        # Se a camada for encontrada, exibe a janela de propriedades da camada
        if layer:
            self.iface.showLayerProperties(layer)

    def open_context_menu(self, position):
        """
        Cria e exibe um menu de contexto para ações específicas em um item selecionado no QTreeView.
        Este método é acionado com um clique do botão direito do mouse sobre um item da lista,
        apresentando opções como abrir propriedades da camada e alterar a espessura da borda da camada.

        Funções e Ações Desenvolvidas:
        - Verificação da seleção atual no QTreeView para determinar o item sobre o qual o menu será aberto.
        - Criação das opções do menu para manipulação das propriedades da camada e ajuste de sua espessura.
        - Execução do menu no local do clique e execução da ação selecionada.

        :param position: A posição do cursor no momento do clique, usada para posicionar o menu de contexto.
        """
        # Obtém os índices selecionados no QTreeView
        indexes = self.dlg.treeViewListaPoligono.selectedIndexes()
        if indexes:
            # Obter o índice da primeira coluna, que deve conter o ID da camada
            index = indexes[0].sibling(indexes[0].row(), 0)
            # Cria o menu de contexto
            menu = QMenu()
            # Adiciona opção para abrir propriedades da camada
            layer_properties_action = menu.addAction("Abrir Propriedades da Camada")
            # Adiciona opção para alterar a espessura da borda
            change_border_thickness_action = menu.addAction("Alterar Espessura da Borda")
            # Exibe o menu no local do clique e aguarda ação do usuário
            action = menu.exec_(self.dlg.treeViewListaPoligono.viewport().mapToGlobal(position))

            # Executa a ação correspondente à escolha do usuário
            if action == layer_properties_action:
                self.abrir_layer_properties(index)
            elif action == change_border_thickness_action:
                self.prompt_for_new_border_thickness(index)

    def prompt_for_new_border_thickness(self, index):
        """
        Exibe um diálogo que permite ao usuário ajustar a espessura da borda de uma camada de polígono.
        O método recupera a espessura atual da borda, apresenta um QDoubleSpinBox para seleção do novo valor,
        e aplica a alteração se o usuário confirmar.

        Funções e Ações Desenvolvidas:
        - Recuperação da camada associada ao item selecionado no QTreeView.
        - Obtenção da espessura atual da borda da camada.
        - Criação de um diálogo com um QDoubleSpinBox para o usuário escolher a nova espessura.
        - Aplicação da nova espessura à camada se o usuário confirmar a mudança.

        :param index: Índice do item no modelo de onde o ID da camada é extraído.
        """
        # Recupera o ID da camada do item selecionado no QTreeView
        layer_id = index.model().itemFromIndex(index).data(Qt.UserRole)
        # Busca a camada correspondente no projeto QGIS usando o ID
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:
            # Obtém a espessura atual da borda da camada
            current_thickness = self.get_current_border_thickness(layer)

            # Cria um diálogo personalizado para ajuste de espessura
            dlg = QDialog(self.dlg)
            dlg.setWindowTitle("Espessura da Borda")
            layout = QVBoxLayout(dlg)

            # Configura um QDoubleSpinBox para escolha da nova espessura
            spinBox = QDoubleSpinBox(dlg)
            spinBox.setRange(0, 100)  # Define o intervalo de valores
            spinBox.setSingleStep(0.2)  # Define o incremento de ajuste
            spinBox.setValue(current_thickness)  # Define o valor inicial com a espessura atual
            spinBox.setDecimals(2)  # Define a precisão decimal
            layout.addWidget(spinBox)

            # Cria botões de OK e Cancelar
            buttonLayout = QHBoxLayout()
            okButton = QPushButton("OK", dlg)
            okButton.clicked.connect(dlg.accept)  # Conecta o botão OK à ação de aceitar o diálogo
            buttonLayout.addWidget(okButton)
            layout.addLayout(buttonLayout)

            # Exibe o diálogo e espera pela ação do usuário
            if dlg.exec_():
                new_thickness = spinBox.value()  # Obtém o novo valor da espessura
                # Aplica a nova espessura à camada se o usuário confirmar
                self.apply_new_border_thickness(layer, new_thickness)

    def get_current_border_thickness(self, layer):
        """
        Recupera a espessura atual da borda de uma camada específica no QGIS. Este método acessa o renderizador da camada,
        e extrai a espessura da borda do primeiro símbolo de polígono encontrado, que é geralmente utilizado para a renderização
        das bordas dos polígonos.

        Funções e Ações Desenvolvidas:
        - Acesso ao renderizador da camada para obter os símbolos usados na renderização.
        - Extração da espessura da borda do primeiro símbolo de polígono se disponível.
        - Retorno da espessura atual da borda ou 0 se não for possível determinar.

        :param layer: Camada do QGIS cuja espessura da borda precisa ser obtida.
        :return: Espessura da borda da camada ou 0 se não for possível determinar a espessura.
        """
        # Acessa o renderizador da camada para obter a lista de símbolos utilizados
        symbols = layer.renderer().symbols(QgsRenderContext())
        if symbols and symbols[0].symbolLayerCount() > 0:
            # Extrai o primeiro símbolo de polígono, que é comumente usado para renderizar bordas
            border_layer = symbols[0].symbolLayer(0)
            # Verifica se o símbolo da borda possui um atributo para espessura da linha
            if hasattr(border_layer, 'strokeWidth'):
                # Retorna a espessura da borda se disponível
                return border_layer.strokeWidth()
        # Retorna 0 como valor padrão caso a espessura da borda não seja acessível ou não esteja definida
        return 0

    def apply_new_border_thickness(self, layer, thickness):
        """
        Aplica uma nova espessura de borda para a camada especificada no QGIS. Este método modifica diretamente
        o símbolo de polígono usado para renderizar a camada, garantindo que as alterações sejam visíveis imediatamente
        no mapa.

        Funções e Ações Desenvolvidas:
        - Acesso ao renderizador da camada para modificar a espessura da borda de cada símbolo de polígono.
        - Aplicação da nova espessura da borda.
        - Disparo de eventos para atualizar a visualização e a interface do usuário no QGIS.

        :param layer: Camada do QGIS que terá a espessura da borda ajustada.
        :param thickness: Nova espessura da borda a ser aplicada.
        """
        # Acessa o renderizador da camada para obter os símbolos usados na renderização
        symbols = layer.renderer().symbols(QgsRenderContext())
        if symbols:
            # Itera sobre cada símbolo na lista de símbolos da camada
            for symbol in symbols:
                # Verifica se há camadas de símbolo disponíveis no símbolo atual
                if symbol.symbolLayerCount() > 0:
                    border_layer = symbol.symbolLayer(0)
                    # Verifica se o símbolo da borda possui um método para definir a espessura da borda
                    if hasattr(border_layer, 'setStrokeWidth'):
                        # Aplica a nova espessura da borda
                        border_layer.setStrokeWidth(thickness)
            # Dispara o repintura da camada para atualizar a visualização no mapa
            layer.triggerRepaint()
            # Emite um sinal indicando que a camada foi adicionada para atualizar interfaces de usuário dependentes
            QgsProject.instance().layerWasAdded.emit(layer)
            # Refresca a simbologia da camada na árvore de camadas do QGIS
            self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    def escolher_local_para_salvar(self, nome_padrao, tipo_arquivo):
        """
        Permite ao usuário escolher um local e um nome de arquivo para salvar uma camada, usando uma caixa de diálogo.
        O método também gerencia nomes de arquivos para evitar sobreposição e lembra o último diretório utilizado.

        Funções e Ações Desenvolvidas:
        - Recuperação do último diretório utilizado através das configurações do QGIS.
        - Geração de um nome de arquivo único para evitar sobreposição.
        - Exibição de uma caixa de diálogo para escolha do local de salvamento.
        - Atualização do último diretório utilizado nas configurações do QGIS.

        :param nome_padrao: Nome padrão proposto para o arquivo a ser salvo.
        :param tipo_arquivo: Descrição do tipo de arquivo para a caixa de diálogo (ex. "Arquivos DXF (*.dxf)").

        :return: O caminho completo do arquivo escolhido para salvar ou None se nenhum arquivo foi escolhido.
        """
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
            self.dlg,
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

    def mostrar_mensagem(self, texto, tipo, duracao=3, caminho_pasta=None, caminho_arquivos=None):
        """
        Exibe uma mensagem na barra de mensagens do QGIS, proporcionando feedback ao usuário baseado nas ações realizadas.
        As mensagens podem ser de erro ou de sucesso, com uma duração configurável e uma opção de abrir uma pasta.

        :param texto: Texto da mensagem a ser exibida.
        :param tipo: Tipo da mensagem ("Erro" ou "Sucesso") que determina a cor e o ícone da mensagem.
        :param duracao: Duração em segundos durante a qual a mensagem será exibida (padrão é 3 segundos).
        :param caminho_pasta: Caminho da pasta a ser aberta ao clicar no botão (padrão é None).
        :param caminho_arquivos: Caminho do arquivo a ser executado ao clicar no botão (padrão é None).
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
            if caminho_arquivos:
                botao_executar = QPushButton("Executar")
                botao_executar.clicked.connect(lambda: os.startfile(caminho_arquivos))
                msg.layout().insertWidget(2, botao_executar)  # Adiciona o botão à esquerda do texto
            
            # Adiciona a mensagem à barra com o nível informativo e a duração especificada
            bar.pushWidget(msg, level=Qgis.Info, duration=duracao)

    def exportar_para_dxf(self):
        """
        Gerencia a exportação de uma camada selecionada para um arquivo DXF. Este método inclui várias etapas:
        seleção da camada, configuração das opções de exportação e salvamento do arquivo.

        Funções e Ações Desenvolvidas:
        - Seleção de uma camada para exportação.
        - Exibição de um diálogo para definir opções de exportação.
        - Escolha de local para salvar o arquivo.
        - Exportação da camada para o formato DXF.
        - Feedback sobre o sucesso ou falha da exportação.
        """
        # Obtém a seleção atual no QTreeView
        indexes = self.dlg.treeViewListaPoligono.selectionModel().selectedIndexes()
        if not indexes:
            self.mostrar_mensagem("Selecione uma camada para exportar.", "Erro")
            return

        # Obtém o nome da camada selecionada
        selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
        layer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
        if not layer:
            self.mostrar_mensagem("Camada não encontrada.", "Erro")
            return

        # Inicializando e exibindo o diálogo de exportação
        dialogo_exportacao = ExportacaoDialogoDXF(layer, self)
        resultado = dialogo_exportacao.exec_()  # Exibe o diálogo e aguarda o usuário fechar

        if resultado == QDialog.Accepted:
            campo_camada, campo_rotulo, ezdxf_pattern, escala, rotacao = dialogo_exportacao.Obter_Valores()

            nome_padrao = f"{selected_layer_name}.dxf"
            tipo_arquivo = "Arquivos DXF (*.dxf)"
            fileName = self.escolher_local_para_salvar(nome_padrao, tipo_arquivo)

            if fileName:
                start_time = time.time()  # Marca o início do processo
                # Chama a função para salvar a camada como DXF
                self.salvar_camada_como_dxf(layer, fileName, campo_camada, campo_rotulo, ezdxf_pattern, escala, rotacao)
                
                # Verifica se o checkbox está marcado antes de exportar rótulos
                if dialogo_exportacao.checkBoxCampoRotulo.isChecked():
                    # Exporta rótulos para DXF, se selecionado
                    self.exportar_rotulos_para_dxf(msp, layer, campo_rotulo, escala, rotacao)
                
                end_time = time.time()  # Marca o fim do processo
                duration = end_time - start_time  # Calcula a duração do processo

                # Exibir mensagem de sucesso com o tempo de execução e caminhos dos arquivos
                self.mostrar_mensagem(
                    f"Arquivo DXF salvo com sucesso em {duration:.2f} segundos", 
                    "Sucesso", 
                    caminho_pasta=os.path.dirname(fileName), 
                    caminho_arquivos=fileName)

    def salvar_camada_como_dxf(self, layer, fileName, nome_atributo, nome_campo_rotulo, ezdxf_pattern, escala, rotacao):
        """
        Exporta uma camada do QGIS para um arquivo DXF, aplicando configurações específicas como padrão de hachura,
        escala, rotação, e tratando rótulos e atributos.

        Funções e Ações Desenvolvidas:
        - Criação de um novo documento DXF e configuração da área de modelo.
        - Extração e aplicação de cores de preenchimento e borda.
        - Iteração sobre todas as feições da camada e exportação de cada uma para o DXF.
        - Atualização da barra de progresso com cada feição processada.
        - Adição de rótulos ao DXF se necessário.
        - Salvamento do arquivo DXF no local especificado.

        :param layer: Camada do QGIS a ser exportada.
        :param fileName: Caminho completo do arquivo DXF a ser criado.
        :param nome_atributo: Nome do atributo a ser usado para nomear a camada no DXF.
        :param nome_campo_rotulo: Nome do campo usado para rótulos no DXF.
        :param ezdxf_pattern: Padrão de hachura a ser aplicado.
        :param escala: Escala de hachura.
        :param rotacao: Rotação de hachura.
        """

        # Inicia a barra de progresso
        progressBar, progressMessageBar = self.iniciar_progress_bar(layer)

        # Criação do documento DXF
        doc = ezdxf.new(dxfversion='R2010')
        msp = doc.modelspace()

        # Obter cores de preenchimento e borda
        fill_color, border_color = self.obter_cores_da_camada(layer)

        # O nome da camada DXF
        nome_camada_dxf = nome_atributo

        # Contador de feições processadas para atualizar a barra de progresso
        processed_features = 0

        for feature in layer.getFeatures():
            geometry = feature.geometry()
            if geometry.isMultipart():
                for polygon in geometry.asMultiPolygon():
                    for ring in polygon:
                        hatch = msp.add_hatch()
                        # Define o padrão de hachura e a cor
                        hatch.set_pattern_fill(ezdxf_pattern, scale=escala, angle=rotacao)
                        hatch.dxf.true_color = fill_color  # Aplicando a cor de preenchimento
                        hatch.dxf.layer = nome_camada_dxf
                        hatch.paths.add_polyline_path(ring, is_closed=True)
                        # Adicionando borda ao polígono
                        msp.add_lwpolyline(ring, close=True, dxfattribs={'true_color': border_color, 'layer': nome_camada_dxf})
            else:
                for ring in geometry.asPolygon():
                    hatch = msp.add_hatch()
                    # Define o padrão de hachura e a cor
                    hatch.set_pattern_fill(ezdxf_pattern, scale=escala, angle=rotacao)
                    hatch.dxf.true_color = fill_color  # Aplicando a cor de preenchimento
                    hatch.dxf.layer = nome_camada_dxf
                    hatch.paths.add_polyline_path(ring, is_closed=True)
                    # Adicionando borda ao polígono
                    msp.add_lwpolyline(ring, close=True, dxfattribs={'true_color': border_color, 'layer': nome_camada_dxf})

            # Atualiza a barra de progresso
            processed_features += 1
            progressBar.setValue(processed_features)

        # Após adicionar todas as geometrias, chama a função para adicionar os rótulos
        self.exportar_rotulos_para_dxf(msp, layer, nome_campo_rotulo)

        # Salva o documento DXF
        doc.saveas(fileName)

        # Remove a mensagem de progresso após a conclusão
        self.iface.messageBar().clearWidgets()

    def iniciar_progress_bar(self, layer):
        """
        Inicia e exibe uma barra de progresso na interface do usuário para o processo de exportação de uma camada para DXF.

        Parâmetros:
        - layer (QgsVectorLayer): A camada para a qual a barra de progresso será exibida, indicando o progresso da exportação.

        Funcionalidades:
        - Cria uma mensagem personalizada na barra de mensagens para acompanhar o progresso.
        - Configura e estiliza uma barra de progresso.
        - Adiciona a barra de progresso à barra de mensagens e a exibe na interface do usuário.
        - Define o valor máximo da barra de progresso com base no número de feições na camada.
        - Retorna os widgets de barra de progresso e de mensagem para que possam ser atualizados durante a exportação.
        """
        # Cria uma mensagem personalizada na barra de progresso
        progressMessageBar = self.iface.messageBar().createMessage("Exportando camada para DXF: " + layer.name())
        progressBar = QProgressBar()  # Cria uma instância da QProgressBar
        progressBar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Alinha a barra de progresso à esquerda e verticalmente ao centro
        progressBar.setFormat("%p% - %v de %m Feições processadas")  # Define o formato da barra de progresso
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

        # Define o valor máximo da barra de progresso com base no número de feições da camada
        feature_count = layer.featureCount()
        progressBar.setMaximum(feature_count)

        # Retorna o progressBar e o progressMessageBar para que possam ser atualizados durante o processo de exportação
        return progressBar, progressMessageBar

    def obter_cores_da_camada(self, layer):
        """
        Obtém as cores de preenchimento e borda de uma camada específica no QGIS. Este método considera diferentes tipos
        de renderizadores e extrai as cores do primeiro símbolo disponível ou de uma categoria específica.

        Funções e Ações Desenvolvidas:
        - Determinação do tipo de renderizador usado pela camada.
        - Extração do símbolo usado para o desenho da camada.
        - Obtenção da cor de preenchimento e, se disponível, da cor da borda.
        - Conversão das cores RGB para o formato de inteiro usado em arquivos DXF.

        :param layer: Camada do QGIS da qual as cores serão obtidas.
        :return: Uma tupla contendo as cores de preenchimento e borda no formato inteiro para uso em DXF.
        """
        # Define cores padrão em caso de não conseguir extrair do renderizador
        fill_color = (0, 0, 0)  # Preto como cor padrão de preenchimento
        border_color = (0, 0, 0)  # Preto como cor padrão da borda
        symbol = None
        fill_color_tuple = (0, 0, 0)  # Inicializa com preto padrão
        border_color_tuple = (0, 0, 0)  # Inicializa com preto padrão

        # Obtém o renderizador da camada e determina o tipo
        renderer = layer.renderer()
        if isinstance(renderer, QgsCategorizedSymbolRenderer):
            # Se for um renderizador categorizado, extrai o símbolo da primeira categoria
            for category in renderer.categories():
                symbol = category.symbol()
                break  # Pegar o símbolo da primeira categoria apenas para exemplo
        elif isinstance(renderer, QgsSingleSymbolRenderer):
            # Se for um renderizador de símbolo único, usa esse símbolo diretamente
            symbol = renderer.symbol()

        # Se um símbolo foi obtido, extrai as cores
        if symbol:
            fill_color = symbol.color()
            fill_color_tuple = (fill_color.red(), fill_color.green(), fill_color.blue())

            # Tenta obter a camada de símbolo de linha para a cor da borda
            border_symbol_layer = symbol.symbolLayers()[0] if symbol.symbolLayerCount() > 0 else None
            if border_symbol_layer and hasattr(border_symbol_layer, 'strokeColor'):
                border_color = border_symbol_layer.strokeColor()
                border_color_tuple = (border_color.red(), border_color.green(), border_color.blue())
            else:
                border_color_tuple = fill_color_tuple  # Usa a cor de preenchimento se não houver cor de borda específica

        # Converte as cores RGB para o formato de inteiro usado em arquivos DXF
        fill_color_int = ezdxf.colors.rgb2int(fill_color_tuple)
        border_color_int = ezdxf.colors.rgb2int(border_color_tuple)

        return fill_color_int, border_color_int

    def exportar_rotulos_para_dxf(self, msp, layer, nome_campo_rotulo):
        """
        Adiciona rótulos aos elementos em um arquivo DXF com base no campo especificado de uma camada do QGIS.
        Este método posiciona os rótulos no centro geométrico de cada feição da camada.

        Funções e Ações Desenvolvidas:
        - Verificação da existência de um campo de rótulo selecionado.
        - Criação ou verificação de um estilo de texto no documento DXF.
        - Iteração sobre todas as feições da camada para adicionar rótulos ao DXF.

        :param msp: Espaço do modelo no documento DXF onde os elementos são adicionados.
        :param layer: Camada do QGIS de onde os dados são extraídos.
        :param nome_campo_rotulo: Nome do campo da camada usado para extrair o texto dos rótulos.
        """
        # Se nenhum campo de rótulo foi selecionado, não faça nada
        if not nome_campo_rotulo:
            return

        doc = msp.doc  # Acesso ao documento DXF associado ao espaço do modelo
        # Cria um novo estilo de texto se ainda não existir no documento DXF
        if "BoldStyle" not in doc.styles:
            doc.styles.new("BoldStyle", dxfattribs={'font': 'Calibri Light'})  # Substitua 'Calibri Light' pelo nome da sua fonte em negrito

        # Itera sobre cada feição da camada
        for feature in layer.getFeatures():
            geometry = feature.geometry()

            # Determina o ponto central da geometria para posicionar o rótulo
            if geometry.isMultipart():
                pontos = geometry.asMultiPolygon()[0][0]  # Obtém o primeiro polígono e o primeiro anel
                ponto_central = QgsGeometry.fromPolygonXY([pontos]).centroid().asPoint()
            else:
                pontos = geometry.asPolygon()[0]  # Obtém o primeiro anel do polígono
                ponto_central = QgsGeometry.fromPolygonXY([pontos]).centroid().asPoint()

            # Obtém o texto do rótulo do campo especificado
            rotulo = str(feature[nome_campo_rotulo])
            # Adiciona o texto ao espaço do modelo no DXF
            msp.add_text(
                rotulo,
                dxfattribs={
                    'insert': (ponto_central.x(), ponto_central.y()), # Posição de inserção do texto
                    'height': 1, # Altura do texto
                    'style': 'BoldStyle', # Estilo do texto
                    'width': 1.5, # Largura do texto (fator de escala)
                    'oblique': 15, # Ângulo oblíquo do texto
                })

    def obter_cores(self, layer):
        """
        Obtém as cores de borda e preenchimento de uma camada de polígonos.

        Esta função verifica se a camada é uma camada de polígonos, e se sim, extrai as cores de borda e preenchimento
        do símbolo da camada. Se as cores não puderem ser obtidas, a função retorna cores padrão (branco opaco).

        Args:
        - layer: A camada de mapa cujas cores serão obtidas.

        Returns:
        - Uma tupla contendo as cores de borda e preenchimento no formato KML (ARGB).
        """
        # Define a cor branca opaca como padrão
        cor_linha_kml = "ffffffff"  # Branco opaco para borda
        cor_preenchimento_kml = "ffffffff"  # Branco opaco para preenchimento

        if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            renderer = layer.renderer()
            simbologia = None

            # Checa se o renderer suporta o método symbol()
            if hasattr(renderer, 'symbol'):
                try:
                    simbologia = renderer.symbol()
                except Exception:
                    pass

            if simbologia and simbologia.symbolLayerCount() > 0:
                # Pega a primeira camada de símbolo para borda
                symbolLayer = simbologia.symbolLayer(0)
                if hasattr(symbolLayer, 'strokeColor'):  # Verifica se a camada do símbolo tem cor de borda
                    cor_linha = symbolLayer.strokeColor()
                    if cor_linha.isValid():
                        cor_linha_kml = self.cor_qgis_para_kml(cor_linha)

                # Cor de preenchimento
                if hasattr(simbologia, 'color'):
                    cor_preenchimento = simbologia.color()
                    if cor_preenchimento.isValid():
                        cor_preenchimento_kml = self.cor_qgis_para_kml(cor_preenchimento)

        return cor_linha_kml, cor_preenchimento_kml

    def cor_qgis_para_kml(self, cor_qgis):
        """
        Converte uma cor do QGIS para o formato de cor KML (aabbggrr).
        """
        # Converte os componentes RGB e alfa para hexadecimal
        a = format(cor_qgis.alpha(), '02x')
        b = format(cor_qgis.blue(), '02x')
        g = format(cor_qgis.green(), '02x')
        r = format(cor_qgis.red(), '02x')
        # Retorna a cor no formato KML
        return a + b + g + r

    def gerar_cor_suave(self):
        """
        Gera uma cor suave em formato hexadecimal.

        Esta função cria uma cor suave, selecionando valores aleatórios para os componentes
        vermelho (R), verde (G) e azul (B) dentro de um intervalo alto (180 a 255), garantindo
        que a cor gerada seja relativamente clara. Isso é útil para fundos de texto ou elementos
        gráficos que precisam ser suavemente coloridos sem dominar o conteúdo sobreposto.

        Retorna:
        - Uma string representando a cor no formato hexadecimal (ex: '#ffeedd').
        """
        # Gera valores aleatórios para os componentes RGB dentro do intervalo de cores suaves
        r = random.randint(180, 255) # Componente vermelho
        g = random.randint(180, 255) # Componente verde
        b = random.randint(180, 255) # Componente azul
        return f'#{r:02x}{g:02x}{b:02x}' # Retorna a cor formatada como uma string hexadecimal

    def exportar_para_kml(self):
        """
        Exporta uma camada selecionada para um arquivo KML.

        Esta função realiza as seguintes etapas:
        1. Verifica se alguma camada está selecionada na treeView.
        2. Obtém a camada selecionada.
        3. Abre o diálogo para configuração da exportação.
        4. Se o diálogo for aceito, obtém os valores fornecidos pelo usuário.
        5. Define o nome padrão e o tipo de arquivo para salvar.
        6. Solicita ao usuário o local para salvar o arquivo.
        7. Cria uma barra de progresso para acompanhar o processo de exportação.
        8. Inicia a exportação da camada para KML em memória.
        9. Escreve o conteúdo KML no arquivo especificado.
        10. Limpa a barra de progresso após a conclusão.
        11. Exibe uma mensagem de sucesso após a exportação.

        Returns:
        - None
        """
        # Obtém a seleção atual no QTreeView
        indexes = self.dlg.treeViewListaPoligono.selectionModel().selectedIndexes()
        if not indexes:
            self.mostrar_mensagem("Selecione uma camada para exportar.", "Erro")
            return

        # Obtém o nome da camada selecionada
        selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
        layer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
        if not layer:
            self.mostrar_mensagem("Camada não encontrada.", "Erro")
            return

        dialog = ExportarKMLDialog(layer, self.dlg)
        if dialog.exec_() == QDialog.Accepted:
            values = dialog.getValues()  # Obter valores usando a função getValues
            selected_field, include_table, line_width, line_opacity, area_opacity, height, use_3d, is_elevated, is_solido, is_edges, image_url, overlay_url = values
            
        else:
            self.mostrar_mensagem("Exportação cancelada.", "Info")
            return # Usuário cancelou a operação

        nome_padrao = f"{layer.name()}.kml"
        tipo_arquivo = "KML Files (*.kml)"
        caminho_arquivo = self.escolher_local_para_salvar(nome_padrao, tipo_arquivo)
        if not caminho_arquivo:
            self.mostrar_mensagem("Exportação cancelada.", "Info")
            return  # Usuário cancelou a seleção do arquivo para salvar

        # Inicia a barra de progresso
        progressBar, progressMessageBar = self.iniciar_progress_bar(layer)

        feature_count = layer.featureCount()
        progressBar.setMaximum(feature_count)

        # Medir o tempo de execução da criação do KML e da escrita no arquivo
        start_time = time.time()

        # Iniciando a exportação
        kml_element = self.criar_kml_em_memoria(layer, selected_field, include_table, line_width, line_opacity, area_opacity, height, use_3d, is_elevated, is_solido, is_edges, image_url, overlay_url, progressBar)

        tree = ET.ElementTree(kml_element)
        tree.write(caminho_arquivo, xml_declaration=True, encoding='utf-8', method="xml")

        end_time = time.time()

        # Calcula o tempo de execução
        execution_time = end_time - start_time

        self.iface.messageBar().clearWidgets()  # Remove a barra de progresso após a conclusão

        # Exibir mensagem de sucesso com o tempo de execução e caminhos dos arquivos
        self.mostrar_mensagem(
            f"Camada exportada para KMZ em {execution_time:.2f} segundos", 
            "Sucesso", 
            caminho_pasta=os.path.dirname(caminho_arquivo), 
            caminho_arquivos=caminho_arquivo)

    def redimensionar_imagem_proporcional_url(self, url_imagem, largura_max, altura_max):
        """
        Baixa a imagem de um URL e redimensiona proporcionalmente para caber dentro de uma caixa de largura e altura máximas.

        Parâmetros:
        - url_imagem (str): URL da imagem a ser redimensionada.
        - largura_max (int): Largura máxima da caixa.
        - altura_max (int): Altura máxima da caixa.

        Retorna:
        - Uma instância de `PIL.Image.Image` redimensionada proporcionalmente.
        - As novas dimensões da imagem (largura, altura).
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }  # Define o cabeçalho de User-Agent para a solicitação HTTP

        try:
            response = requests.get(url_imagem, headers=headers)  # Faz o download da imagem do URL com o cabeçalho definido
            response.raise_for_status()  # Verifica se o download foi bem-sucedido

            imagem = Image.open(BytesIO(response.content))  # Abre a imagem a partir do conteúdo baixado
            largura_original, altura_original = imagem.size  # Obtém as dimensões originais da imagem

            proporcao_largura = largura_max / largura_original  # Calcula a proporção para a largura
            proporcao_altura = altura_max / altura_original  # Calcula a proporção para a altura
            proporcao_final = min(proporcao_largura, proporcao_altura)  # Usa a menor proporção para manter a imagem dentro da caixa

            nova_largura = int(largura_original * proporcao_final)  # Calcula a nova largura proporcional
            nova_altura = int(altura_original * proporcao_final)  # Calcula a nova altura proporcional

            imagem_redimensionada = imagem.resize((nova_largura, nova_altura), Image.LANCZOS)  # Redimensiona a imagem

            return imagem_redimensionada, nova_largura, nova_altura  # Retorna a imagem redimensionada e as novas dimensões

        except UnidentifiedImageError:
            # Captura o erro se a imagem não puder ser identificada e exibe uma mensagem de erro
            self.mostrar_mensagem("Erro ao abrir a imagem. O arquivo não é uma imagem válida ou está corrompido.", "Erro")
            return None, None, None  # Retorna None se ocorrer um erro

        except Exception as e:
            # Captura qualquer outro erro, exibe uma mensagem de erro e continua
            self.mostrar_mensagem(f"Erro ao processar a imagem: {e}", "Erro")
            return None, None, None  # Retorna None se ocorrer um erro

    def criar_kml_em_memoria(self, layer, campo_id, include_table, line_width, line_opacity, area_opacity, height, use_3d, is_elevated, is_solido, is_edges, image_url, overlay_url, progressBar=None):
        """
        Cria um documento KML em memória com base nos parâmetros fornecidos.

        Esta função realiza as seguintes etapas:
        1. Inicializa um elemento KML e um elemento Document.
        2. Obtém as cores da linha e do preenchimento para a camada.
        3. Verifica se é necessário transformar as coordenadas da camada para EPSG:4326.
        4. Itera sobre as feições da camada, criando placemarks KML para cada uma delas.
        5. Atualiza a barra de progresso, se fornecida.
        6. Adiciona um ScreenOverlay ao documento KML, se uma URL válida for fornecida para a imagem do overlay.

        Args:
        - layer: A camada QgsVectorLayer a ser exportada para KML.
        - campo_id: O nome do campo a ser usado como identificador de cada placemark.
        - include_table: Booleano que indica se os atributos da feição devem ser incluídos na descrição do placemark.
        - line_width: Largura da linha do placemark.
        - line_opacity: Opacidade da linha do placemark.
        - area_opacity: Opacidade da área do placemark.
        - height: Altura do placemark em metros.
        - use_3d: Booleano que indica se o placemark deve ser renderizado em 3D.
        - is_elevated: Booleano que indica se a elevação deve ser ajustada automaticamente.
        - is_solido: Booleano que indica se o placemark deve ter uma aparência sólida.
        - is_edges: Booleano que indica se as bordas do placemark devem ser exibidas.
        - image_url: A URL da imagem a ser usada como ícone do placemark.
        - overlay_url: A URL da imagem a ser usada como overlay.

        Returns:
        - O elemento KML contendo o documento.
        """
        kml = ET.Element('kml', xmlns="http://www.opengis.net/kml/2.2")
        document = ET.SubElement(kml, 'Document')

        # Obtém as cores da linha e do preenchimento para a camada
        cor_linha_kml, cor_preenchimento_kml = self.obter_cores(layer)

        transform = None
        if layer.crs().authid() != 'EPSG:4326':
            crsDestino = QgsCoordinateReferenceSystem(4326)
            transform = QgsCoordinateTransform(layer.crs(), crsDestino, QgsProject.instance())
            transformar = True
        else:
            transformar = False

        # Atualização da barra de progresso durante a iteração
        for count, feature in enumerate(layer.getFeatures()):
            if progressBar:
                progressBar.setValue(count)
            self.criar_placemark_kml(document, feature, campo_id, transformar, transform, cor_linha_kml, cor_preenchimento_kml, include_table, line_width, line_opacity, area_opacity, height, use_3d, is_elevated, is_solido, is_edges, image_url, overlay_url)

        # Finaliza a barra de progresso
        if progressBar:
            progressBar.setValue(layer.featureCount())

        # Adiciona ScreenOverlay apenas se overlay_url for fornecida e não for vazia
        if overlay_url:
            # Redimensiona a imagem obtida a partir do URL
            imagem_redimensionada, nova_largura, nova_altura = self.redimensionar_imagem_proporcional_url(overlay_url, 300, 150)

            if imagem_redimensionada is not None:
                # Adiciona o ScreenOverlay ao KML usando a imagem redimensionada
                screen_overlay = ET.SubElement(document, 'ScreenOverlay') # Cria o elemento ScreenOverlay no documento KML
                name = ET.SubElement(screen_overlay, 'name')  # Define o nome do ScreenOverlay
                name.text = 'logo'

                # Define o ícone do ScreenOverlay, utilizando a URL da imagem fornecida
                icon = ET.SubElement(screen_overlay, 'Icon')
                href = ET.SubElement(icon, 'href')
                href.text = overlay_url

                # Configura a posição e o tamanho do overlay na tela
                overlay_xy = ET.SubElement(screen_overlay, 'overlayXY', x="1", y="1", xunits="fraction", yunits="fraction")
                screen_xy = ET.SubElement(screen_overlay, 'screenXY', x=f"{nova_largura}", y=f"{nova_altura}", xunits="pixels", yunits="pixels")
                rotation_xy = ET.SubElement(screen_overlay, 'rotationXY', x="0", y="0", xunits="fraction", yunits="fraction")
                # Define o tamanho do ScreenOverlay
                size = ET.SubElement(screen_overlay, 'size', x=f"{nova_largura}", y=f"{nova_altura}", xunits="pixels", yunits="pixels")

        return kml

    def criar_placemark_kml(self, document, feature, campo_id, transformar, transform, cor_linha_kml, cor_preenchimento_kml, include_table, line_width, line_opacity, area_opacity, height, use_3d, is_elevated, is_solido, is_edges, image_url, overlay_url):
        """
        Cria um elemento Placemark KML com base nos parâmetros fornecidos e adiciona ao documento.

        Esta função realiza as seguintes etapas:
        1. Cria um elemento Placemark no documento KML.
        2. Verifica se a geometria é um multipolígono e itera sobre seus anéis, criando elementos Polygon para cada um deles.
        3. Define estilos para a linha e preenchimento do Placemark com base nas cores fornecidas.
        4. Processa as configurações de elevação, 3D e bordas do Placemark.
        5. Inclui atributos da feição e uma tabela HTML na descrição do Placemark, se necessário.
        6. Adiciona um BalloonStyle ao estilo do Placemark, se uma URL de imagem for fornecida.

        Args:
        - document: O elemento Documento KML ao qual o Placemark será adicionado.
        - feature: A feição QgsFeature a ser representada pelo Placemark.
        - campo_id: O nome do campo a ser usado como identificador do Placemark.
        - transformar: Booleano que indica se as coordenadas devem ser transformadas para EPSG:4326.
        - transform: O objeto QgsCoordinateTransform usado para transformar as coordenadas, se necessário.
        - cor_linha_kml: A cor da linha do Placemark em formato KML.
        - cor_preenchimento_kml: A cor de preenchimento do Placemark em formato KML.
        - include_table: Booleano que indica se os atributos da feição devem ser incluídos na descrição do Placemark.
        - line_width: Largura da linha do Placemark.
        - line_opacity: Opacidade da linha do Placemark.
        - area_opacity: Opacidade da área do Placemark.
        - height: Altura do Placemark em metros.
        - use_3d: Booleano que indica se o Placemark deve ser renderizado em 3D.
        - is_elevated: Booleano que indica se a elevação deve ser ajustada automaticamente.
        - is_solido: Booleano que indica se o Placemark deve ter uma aparência sólida.
        - is_edges: Booleano que indica se as bordas do Placemark devem ser exibidas.
        - image_url: A URL da imagem a ser usada como ícone do Placemark.
        - overlay_url: A URL da imagem a ser usada como overlay.

        Returns:
        - None
        """
        placemark = ET.SubElement(document, 'Placemark')

        # Verifica se a geometria é um multipolígono
        if feature.geometry().type() == QgsWkbTypes.PolygonGeometry and feature.geometry().isMultipart():
            geometria = feature.geometry().asMultiPolygon()  # Para multipolígonos
            multi_geometry = ET.SubElement(placemark, 'MultiGeometry')
            
            for poligono in geometria:
                for anel in poligono:
                    polygon = ET.SubElement(multi_geometry, 'Polygon')
                    self.processar_poligono(polygon, anel, height, transformar, transform, use_3d)
        else:
            # Para polígonos simples
            geometria = feature.geometry().asPolygon()
            polygon = ET.SubElement(placemark, 'Polygon')
            self.processar_poligono(polygon, geometria[0], height, transformar, transform, use_3d)  # Assume o anel exterior

        # Converter opacidade de preenchimento percentual para hexadecimal
        opacidade_preenchimento_hex = format(int(area_opacity * 255 / 100), '02x')
        # Aplicar a opacidade ao estilo de preenchimento
        cor_preenchimento_completa = opacidade_preenchimento_hex + cor_preenchimento_kml[2:]

        # Converter opacidade percentual para hexadecimal
        opacidade_hex = format(int(line_opacity * 255 / 100), '02x')
        # Supondo que cor_linha_kml já esteja no formato "bbggrr" e precisa do prefixo de opacidade "aa"
        cor_linha_completa = opacidade_hex + cor_linha_kml[2:]

        style = ET.SubElement(placemark, 'Style')
        poly_style = ET.SubElement(style, 'PolyStyle')
        color = ET.SubElement(poly_style, 'color')
        color.text = cor_preenchimento_completa  # Usa a cor de preenchimento com opacidade aplicada
        line_style = ET.SubElement(style, 'LineStyle')
        color = ET.SubElement(line_style, 'color')
        color.text = cor_linha_completa  # Usa a cor da linha com opacidade aplicada
        width = ET.SubElement(line_style, 'width')
        width.text = str(line_width)  

        # Certifique-se de passar 'poly_style' para a função
        self.processar_poligono_elevado(polygon, geometria[0], height, transformar, transform, use_3d, poly_style, is_elevated, is_solido, is_edges, image_url, overlay_url)

        if include_table:
            # Adicionar o nome e os dados extendidos ao Placemark
            name = ET.SubElement(placemark, 'name')
            name.text = str(feature[campo_id])
            extended_data = ET.SubElement(placemark, 'ExtendedData')

            # Adicionar dados como elementos Data para ExtendedData
            for field in feature.fields():
                data = ET.SubElement(extended_data, 'Data', name=field.name())
                value = ET.SubElement(data, 'value')
                value.text = str(feature[field.name()])

            # Construir a tabela HTML
            tabela_geral_html = '<table border="1" style="border-collapse: collapse; border: 2px solid black; width: 100%;">'
            for field in feature.fields():
                cor_fundo = self.gerar_cor_suave()  # Gera uma cor suave
                tabela_geral_html += f'<tr><td><table border="0" style="background-color: {cor_fundo}; width: 100%;">'
                tabela_geral_html += f'<tr><td style="text-align: left;"><b>{field.name()}</b></td>'
                tabela_geral_html += f'<td style="text-align: right;">{str(feature[field.name()])}</td></tr></table></td></tr>'
            tabela_geral_html += '</table>'

            # Inserindo a imagem, se a URL for fornecida
            imagem_html = ""
            # if image_url:  # Verifica se a URL da imagem foi fornecida
                # imagem_html = f'<div style="text-align: center;"><img src="{image_url}" alt="Ícone" width="72" height="36" style="margin-top: 1px; margin-bottom: -15px; margin-left: 0px; margin-right: 0px;"></div>'

            if image_url:  # Se image_url não estiver vazia
                # Redimensiona a imagem para caber dentro de width="72" e height="36"
                imagem_redimensionada, nova_largura, nova_altura = self.redimensionar_imagem_proporcional_url(image_url, 150, 75)
                
                # Se a imagem foi redimensionada com sucesso, aplica as novas dimensões ao HTML
                if imagem_redimensionada is not None:
                    imagem_html = f'<div style="text-align: center;"><img src="{image_url}" alt="Ícone" width="{nova_largura}" height="{nova_altura}" style="margin-top: 1px; margin-bottom: -15px; margin-left: 0px; margin-right: 0px;"></div>'

            # BalloonStyle com a imagem e a tabela de atributos diretamente
            balloon_style = ET.SubElement(style, 'BalloonStyle')
            text = ET.SubElement(balloon_style, 'text')
            balloon_html = f"""
            {imagem_html}
            <h3 style="margin-bottom:1px;">{campo_id}: {str(feature[campo_id])}</h3>
            <p>Tabela de Informações:</p>
            {tabela_geral_html}
            """
            text.text = balloon_html

    def processar_poligono_elevado(self, polygon_element, anel, height, transformar, transform, use_3d, poly_style, is_elevated, is_solido, is_edges, image_url, overlay_url):
        """
        Processa as configurações de elevação, 3D e bordas para um elemento de polígono KML.

        Esta função realiza as seguintes etapas:
        1. Verifica se o modo 3D está ativado e aplica a configuração de altitudeMode se necessário.
        2. Aplica configurações adicionais com base nos modos específicos (elevado, sólido, bordas).

        Args:
        - polygon_element: O elemento Polygon ao qual as configurações serão aplicadas.
        - anel: O anel de coordenadas do polígono.
        - height: A altura do polígono em metros.
        - transformar: Booleano que indica se as coordenadas devem ser transformadas para EPSG:4326.
        - transform: O objeto QgsCoordinateTransform usado para transformar as coordenadas, se necessário.
        - use_3d: Booleano que indica se o modo 3D está ativado.
        - poly_style: O elemento Style associado ao polígono.
        - is_elevated: Booleano que indica se o modo 'Elevado' está ativado.
        - is_solido: Booleano que indica se o modo 'Sólido' está ativado.
        - is_edges: Booleano que indica se o modo 'Bordas' está ativado.
        - image_url: A URL da imagem a ser usada como ícone do Placemark.
        - overlay_url: A URL da imagem a ser usada como overlay.

        Returns:
        - None
        """
        # Se o checkBox3D estiver ativado, mas nenhum modo específico foi selecionado, então não faz nada
        if use_3d and not (is_elevated or is_solido or is_edges):
            return

        if use_3d:
            altitudeMode = ET.SubElement(polygon_element, 'altitudeMode')
            altitudeMode.text = 'relativeToGround'
            extrude = ET.SubElement(polygon_element, 'extrude')
            extrude.text = '1'  # As laterais se estendem até o solo

        # Se algum modo específico estiver ativo, aplica as configurações
        if is_elevated or is_solido or is_edges:
            outline = ET.SubElement(poly_style, 'outline')
            outline.text = '1'  # Mostra as bordas
            fill = ET.SubElement(poly_style, 'fill')
            fill.text = '0' if is_edges else '1'  # Sem preenchimento se for 'Edges', preenchido para outros

        # Especificamente para o modo 'Sólido', não mostrar as bordas
        if is_solido:
            outline.text = '0'

    def processar_poligono(self, polygon_element, anel, height, transformar, transform, use_3d):
        """
        Processa as coordenadas de um polígono e adiciona-as a um elemento Polygon KML.

        Esta função realiza as seguintes etapas:
        1. Cria um LinearRing e adiciona as coordenadas do polígono.
        2. Aplica tessellate se o modo 3D não estiver ativado e a altura for zero.
        3. Define o altitudeMode com base na configuração do modo 3D.

        Args:
        - polygon_element: O elemento Polygon ao qual as coordenadas serão adicionadas.
        - anel: O anel de coordenadas do polígono.
        - height: A altura do polígono em metros.
        - transformar: Booleano que indica se as coordenadas devem ser transformadas para EPSG:4326.
        - transform: O objeto QgsCoordinateTransform usado para transformar as coordenadas, se necessário.
        - use_3d: Booleano que indica se o modo 3D está ativado.

        Returns:
        - None
        """
        outer_boundary = ET.SubElement(polygon_element, 'outerBoundaryIs')
        linear_ring = ET.SubElement(outer_boundary, 'LinearRing')
        coordinates = ET.SubElement(linear_ring, 'coordinates')
        
        coords = []
        for point in anel:
            if transformar:
                point = transform.transform(point.x(), point.y())
            coords.append(f"{point[0]},{point[1]},{height}")

        coordinates.text = ' '.join(coords)
        
        # Se o checkBox3D estiver desmarcado e a altura for zero, aplica tessellate
        if not use_3d and height == 0:
            tessellate = ET.SubElement(polygon_element, 'tessellate')
            tessellate.text = '1'
        else:
            altitudeMode = ET.SubElement(polygon_element, 'altitudeMode')
            altitudeMode.text = 'relativeToGround' if use_3d else 'clampToGround'

class TreeViewEventFilter(QObject):
    """
    Filtro de eventos personalizado para detectar movimentos do mouse sobre itens em um treeView.

    Esta classe herda de QObject e implementa um filtro de eventos que detecta quando o mouse se move
    sobre itens específicos em um treeView. Quando o mouse se move sobre um item, a classe chama um 
    método no UiManager para exibir um tooltip com informações sobre o item.

    Parâmetros:
    - ui_manager: Referência à instância do objeto UiManager, que gerencia a interface do usuário.
    """

    def __init__(self, ui_manager):
        """
        Inicializa o filtro de eventos com uma referência ao UiManager.

        Parâmetros:
        - ui_manager: Instância do UiManager que será usada para acessar e manipular a interface do usuário.
        """
        super().__init__()  # Inicializa a classe base QObject
        self.ui_manager = ui_manager  # Armazena a referência ao UiManagerT para uso posterior

    def eventFilter(self, obj, event):
        """
        Filtra os eventos de movimentação do mouse sobre o treeView e exibe tooltips quando aplicável.

        Esta função intercepta eventos que ocorrem no treeView especificado. Se o evento for de movimento
        do mouse (QEvent.MouseMove) e o mouse estiver sobre um item válido no treeView, a função chama
        o método 'configurar_tooltip' do UiManager para exibir um tooltip com informações sobre o item.

        Parâmetros:
        - obj: O objeto que está sendo monitorado (neste caso, o viewport do treeView).
        - event: O evento que está sendo filtrado (como QEvent.MouseMove).

        Retorno:
        - bool: O resultado da chamada à função 'eventFilter' da classe base, indicando se o evento foi processado.
        """
        # Verifica se o objeto é o viewport do treeView e se o evento é de movimento do mouse
        if obj == self.ui_manager.dlg.treeViewListaPoligono.viewport() and event.type() == QEvent.MouseMove:
            # Obtém o índice do item no treeView sob o cursor do mouse
            index = self.ui_manager.dlg.treeViewListaPoligono.indexAt(event.pos())
            if index.isValid():  # Verifica se o índice é válido (se o mouse está sobre um item)
                self.ui_manager.configurar_tooltip(index)  # Chama o método para configurar e exibir o tooltip
        # Retorna o resultado padrão do filtro de eventos
        return super().eventFilter(obj, event)  # Chama a implementação da classe base para continuar o processamento normal

class ExportarKMLDialog(QDialog):

    # Atributos de classe para armazenar os URLs
    ultimoTextoUrl = ""
    ultimoTextoUrl2 = ""

    def __init__(self, layer, parent=None):
        super().__init__(parent)
        
        self.layer = layer
        self.setWindowTitle("Configurações de Exportação para KML")

        mainLayout = QVBoxLayout(self)

        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Raised)
        frameLayout = QVBoxLayout(frame)

        # ComboBox para campo de identificação
        identificationLayout = QHBoxLayout()
        self.comboBox = QComboBox()
        self.populate_fields()
        identificationLayout.addWidget(QLabel("Campo de Identificação:"))
        identificationLayout.addWidget(self.comboBox)

        # CheckBox para opção Tabela
        self.tableCheckBox = QCheckBox("Tabela")
        self.tableCheckBox.setChecked(True)
        identificationLayout.addWidget(self.tableCheckBox)
        frameLayout.addLayout(identificationLayout)

        # DoubleSpinBox para largura da linha
        lineLayout = QHBoxLayout()
        self.lineWidthSpinBox = QDoubleSpinBox()
        self.lineWidthSpinBox.setValue(1.0)  # Valor padrão
        self.lineWidthSpinBox.setSingleStep(0.1)
        self.lineWidthSpinBox.setDecimals(1)
        lineLayout.addWidget(QLabel("Largura da Linha:"))
        lineLayout.addWidget(self.lineWidthSpinBox)

        # DoubleSpinBox para opacidade da linha
        self.lineOpacitySpinBox = QDoubleSpinBox()
        self.lineOpacitySpinBox.setRange(0, 100)
        self.lineOpacitySpinBox.setValue(100)  # Valor padrão
        self.lineOpacitySpinBox.setSingleStep(5)
        self.lineOpacitySpinBox.setDecimals(0)
        self.lineOpacitySpinBox.setSuffix(" %")
        lineLayout.addWidget(QLabel("Opacidade:"))
        lineLayout.addWidget(self.lineOpacitySpinBox)
        frameLayout.addLayout(lineLayout)

        # DoubleSpinBox para altura
        heightLayout = QHBoxLayout()
        self.heightSpinBox = QDoubleSpinBox()
        self.heightSpinBox.setSuffix(" m")
        self.heightSpinBox.setSingleStep(0.5)
        self.heightSpinBox.setValue(0.00)  # Valor padrão
        self.heightSpinBox.setRange(0, 1000)
        self.heightSpinBox.setDecimals(2)  # Define a precisão decimal para dois dígitos
        heightLayout.addWidget(QLabel("Altura:"))
        heightLayout.addWidget(self.heightSpinBox)

        # DoubleSpinBox para opacidade da área
        self.areaOpacitySpinBox = QDoubleSpinBox()
        self.areaOpacitySpinBox.setRange(0, 100)
        self.areaOpacitySpinBox.setValue(100)  # Valor padrão
        self.areaOpacitySpinBox.setSingleStep(5)
        self.areaOpacitySpinBox.setDecimals(0)
        self.areaOpacitySpinBox.setSuffix(" %")
        heightLayout.addWidget(QLabel("Opacidade da Área:"))
        heightLayout.addWidget(self.areaOpacitySpinBox)
        frameLayout.addLayout(heightLayout)

        # Layout para opções 3D
        options3DLayout = QHBoxLayout()

        # CheckBox para opção 3D
        self.checkBox3D = QCheckBox("3D")
        options3DLayout.addWidget(self.checkBox3D)

        # Conecta o sinal toggled do checkBox3D ao slot que atualiza o estado do DoubleSpinBox da altura
        self.checkBox3D.toggled.connect(self.updateHeightSpinBoxState)

        # Atualiza o estado inicial do DoubleSpinBox da altura com base no estado inicial do checkBox3D
        self.updateHeightSpinBoxState(self.checkBox3D.isChecked())

        # RadioButtons para opções de visualização 3D
        self.radioElevated = QRadioButton("Elevado")
        self.radioSolid = QRadioButton("Sólido")
        self.radioEdges = QRadioButton("Arestas")

        # Adicionar os RadioButtons a um grupo (opcional)
        self.visualization3DGroup = QButtonGroup(self)
        self.visualization3DGroup.addButton(self.radioElevated)
        self.visualization3DGroup.addButton(self.radioSolid)
        self.visualization3DGroup.addButton(self.radioEdges)

        # Adicionar RadioButtons ao layout
        options3DLayout.addWidget(self.radioElevated)
        options3DLayout.addWidget(self.radioSolid)
        options3DLayout.addWidget(self.radioEdges)

        # Adicionar o layout das opções 3D ao layout principal do frame
        frameLayout.addLayout(options3DLayout)

        # Primeiro QLineEdit e QPushButton para o URL da imagem
        self.labelImageUrl = QLabel("URL da Imagem para a Tabela:")
        frameLayout.addWidget(self.labelImageUrl)
        
        urlLayout1 = QHBoxLayout()
        self.lineEditImageUrl = QLineEdit()
        self.lineEditImageUrl.setPlaceholderText("Colar o URL da IMG para a Tabela: Opcional")
        self.lineEditImageUrl.setClearButtonEnabled(True)  # Habilita o botão de limpeza
        self.btnAbrirImagem = QPushButton("Colar")
        self.btnAbrirImagem.setMaximumWidth(40)
        urlLayout1.addWidget(self.lineEditImageUrl)
        urlLayout1.addWidget(self.btnAbrirImagem)
        frameLayout.addLayout(urlLayout1)

        self.btnAbrirImagem.clicked.connect(self.colarTextop)

        # Segundo QLineEdit e QPushButton para o URL da imagem
        self.labelImageUrl2 = QLabel("URL para ScreenOverlay:")
        frameLayout.addWidget(self.labelImageUrl2)
        
        urlLayout2 = QHBoxLayout()
        self.lineEditImageUrl2 = QLineEdit()
        self.lineEditImageUrl2.setPlaceholderText("Colar o URL para o ScreenOverlay: Opcional")
        self.lineEditImageUrl2.setClearButtonEnabled(True)  # Habilita o botão de limpeza
        self.btnColarImagem2 = QPushButton("Colar")
        self.btnColarImagem2.setMaximumWidth(40)
        urlLayout2.addWidget(self.lineEditImageUrl2)
        urlLayout2.addWidget(self.btnColarImagem2)
        frameLayout.addLayout(urlLayout2)

        self.btnColarImagem2.clicked.connect(self.colarTexto2p)

        # Setar o texto dos QLineEdit com os últimos valores usados
        self.lineEditImageUrl.setText(self.ultimoTextoUrl)
        self.lineEditImageUrl2.setText(self.ultimoTextoUrl2)

        # Conecta o sinal textChanged a um novo método para lidar com a atualização do texto
        self.lineEditImageUrl.textChanged.connect(self.verificarTexto)
        self.lineEditImageUrl2.textChanged.connect(self.verificarTexto2)

        # Botões Exportar e Cancelar
        buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("Exportar")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancelar")
        self.cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(self.okButton)
        buttonLayout.addWidget(self.cancelButton)
        frameLayout.addLayout(buttonLayout)

        mainLayout.addWidget(frame)

        # Conectar sinais aos slots
        self.tableCheckBox.toggled.connect(self.updateUIElements)
        self.radioSolid.toggled.connect(self.updateUIElements)
        self.radioEdges.toggled.connect(self.updateUIElements)
        self.checkBox3D.toggled.connect(self.updateUIElements)

        # Atualizar a UI inicialmente
        self.updateUIElements()

    def updateHeightSpinBoxState(self, checked):
        """
        Atualiza o estado do QSpinBox associado à altura com base no valor de checked.

        Args:
        - checked (bool): Indica se a caixa de seleção relacionada está marcada (True) ou desmarcada (False).
        """

        # Define se o QSpinBox associado à altura deve ser ativado ou desativado com base no valor de checked
        self.heightSpinBox.setEnabled(checked)

    def updateUIElements(self):
        """
        Atualiza os elementos da interface do usuário (UI) com base no estado atual dos widgets.

        Esta função realiza as seguintes etapas:
        1. Verifica se há feições na camada e se há campos na camada.
        2. Atualiza a ativação dos widgets com base nas condições de presença de feições e estado dos checkboxes.
        3. Habilita ou desabilita os widgets conforme necessário, dependendo das opções 3D e dos radio buttons selecionados.

        Args:
        - None

        Returns:
        - None
        """
        # Atualiza os elementos da UI com base no estado atual dos widgets
        hasFeatures = self.layer.featureCount() > 0 and len(self.layer.fields()) > 0
        # Habilita ou desabilita os widgets conforme necessário
        self.comboBox.setEnabled(hasFeatures and self.tableCheckBox.isChecked())
        self.okButton.setEnabled(hasFeatures)
        self.lineEditImageUrl.setEnabled(self.tableCheckBox.isChecked())
        self.btnAbrirImagem.setEnabled(self.tableCheckBox.isChecked())

        # Opções 3D e radio buttons
        isElevatedChecked = self.radioSolid.isChecked() and self.checkBox3D.isChecked()
        isEdgesChecked = self.radioEdges.isChecked() and self.checkBox3D.isChecked()
        # Desabilita a configuração da opacidade da linha se 'isElevatedChecked' estiver verdadeiro
        self.lineOpacitySpinBox.setEnabled(not isElevatedChecked)
        # Desabilita a configuração da largura da linha se 'isElevatedChecked' estiver verdadeiro
        self.lineWidthSpinBox.setEnabled(not isElevatedChecked)
        # Desabilita a configuração da opacidade da área se 'isEdgesChecked' estiver verdadeiro
        self.areaOpacitySpinBox.setEnabled(not isEdgesChecked)

        # Atualizar a ativação dos radio buttons com base no checkBox 3D
        self.radioElevated.setEnabled(self.checkBox3D.isChecked())
        self.radioSolid.setEnabled(self.checkBox3D.isChecked())
        self.radioEdges.setEnabled(self.checkBox3D.isChecked())

    def verificarValidadeURL(self, url):
        """
        Verifica a validade de uma URL de acordo com um padrão regex.

        Args:
        - url (str): A URL a ser verificada.

        Returns:
        - bool: True se a URL for válida, False caso contrário.
        """

        # Define o padrão regex para verificar a validade da URL
        padrao_url = re.compile(
            r'^(https?:\/\/)?'  # http:// ou https://
            r'((([a-z\d]([a-z\d-]*[a-z\d])*)\.)+[a-z]{2,}|'  # domínio
            r'((\d{1,3}\.){3}\d{1,3}))'  # ou ip
            r'(\:\d+)?(\/[-a-z\d%_.~+=]*)*'  # porta e caminho, incluído '=' no caminho
            r'(\?[;&a-z\d%_.~+=-]*)?'  # query string
            r'(\#[-a-z\d_]*)?$', re.IGNORECASE)  # fragmento
        return re.match(padrao_url, url) is not None

    def colarTextop(self):
        """
        Cola o texto da área de transferência na caixa de texto QLineEdit.

        Esta função verifica se o texto colado da área de transferência é uma URL válida.
        Se for uma URL válida, o texto é definido como o texto da caixa de texto QLineEdit.

        Nota: A validação da URL é realizada utilizando a função verificarValidadeURL.

        """
        # Obtém o objeto de área de transferência da aplicação
        clipboard = QGuiApplication.clipboard()
        texto = clipboard.text() # Obtém o texto da área de transferência
        
        # Verifica se o texto da área de transferência é uma URL válida
        if self.verificarValidadeURL(texto):
            self.lineEditImageUrl.setText(texto) # Define o texto colado como o texto da caixa de texto QLineEdit

    def colarTexto2p(self):
        """
        Cola o texto da área de transferência na caixa de texto QLineEdit.

        Esta função verifica se o texto colado da área de transferência é uma URL válida.
        Se for uma URL válida, o texto é definido como o texto da caixa de texto QLineEdit.

        Nota: A validação da URL é realizada utilizando a função verificarValidadeURL.

        """
        # Obtém o objeto de área de transferência da aplicação
        clipboard = QGuiApplication.clipboard()
        texto = clipboard.text() # Obtém o texto da área de transferência
        # Verifica se o texto da área de transferência é uma URL válida
        if self.verificarValidadeURL(texto):
            # Define o texto colado como o texto da caixa de texto QLineEdit
            self.lineEditImageUrl2.setText(texto)

    def verificarValidadeURLImagem(self, url):
        """
        Verifica se a URL fornecida leva a uma imagem válida.

        Esta função verifica se a URL termina com uma das extensões de arquivo de imagem
        aceitáveis. Se a URL terminar com uma dessas extensões, ela é considerada uma URL
        válida para uma imagem.

        Args:
            url (str): A URL a ser verificada.

        Returns:
            bool: True se a URL levar a uma imagem válida, False caso contrário.
        """
        # Define as extensões de arquivo de imagem que são aceitáveis
        extensoes_validas = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.webp']
        # Verifica se a URL termina com uma das extensões de arquivo de imagem válidas
        return any(url.lower().endswith(ext) for ext in extensoes_validas)

    def verificarTexto(self):
        """
        Verifica o texto inserido no lineEdit da URL.

        Esta função verifica se o texto inserido na caixa de texto da URL é uma URL válida e se leva a uma imagem válida.
        Se a URL for válida e levar a uma imagem válida, a cor do texto na caixa de texto da URL será alterada para azul.
        Se a URL não for válida ou não levar a uma imagem válida, a cor do texto na caixa de texto da URL será alterada para vermelho.

        """
        # Obtém o texto da caixa de texto da URL
        texto = self.lineEditImageUrl.text()
        # Verifica se o texto é uma URL válida e se leva a uma imagem válida
        if self.verificarValidadeURL(texto) and self.verificarValidadeURLImagem(texto):
            # Se a URL for válida e levar a uma imagem válida, define a cor do texto como azul
            ExportarKMLDialog.ultimoTextoUrl = texto 
            self.lineEditImageUrl.setStyleSheet("QLineEdit { color: blue; }")
        else:
            # Se a URL não for válida ou não levar a uma imagem válida, limpa a última URL válida e
            # define a cor do texto como vermelho, se o texto não estiver vazio
            ExportarKMLDialog.ultimoTextoUrl = ""
            if texto.strip() != "":
                self.lineEditImageUrl.setStyleSheet("QLineEdit { color: red; }")
            else:
                # Se o texto estiver vazio, remove qualquer estilo de cor
                self.lineEditImageUrl.setStyleSheet("")

    def verificarTexto2(self):
        """
        Verifica o texto inserido no lineEdit da segunda URL.

        Esta função verifica se o texto inserido na caixa de texto da segunda URL é uma URL válida e se leva a uma imagem válida.
        Se a URL for válida e levar a uma imagem válida, a cor do texto na caixa de texto da segunda URL será alterada para azul.
        Se a URL não for válida ou não levar a uma imagem válida, a cor do texto na caixa de texto da segunda URL será alterada para vermelho.

        """
        # Obtém o texto da caixa de texto da segunda URL
        texto = self.lineEditImageUrl2.text()
        if self.verificarValidadeURL(texto) and self.verificarValidadeURLImagem(texto):
            ExportarKMLDialog.ultimoTextoUrl2 = texto
            self.lineEditImageUrl2.setStyleSheet("QLineEdit { color: blue; }")
        else:
            ExportarKMLDialog.ultimoTextoUrl2 = ""
            if texto.strip() != "":
                self.lineEditImageUrl2.setStyleSheet("QLineEdit { color: red; }")
            else:
                self.lineEditImageUrl2.setStyleSheet("")

    def populate_fields(self):
        """
        Preenche o comboBox com os nomes dos campos da camada.

        Esta função obtém os campos da camada atual e adiciona os nomes dos campos ao comboBox na interface do usuário.
        """
        # Obtém os campos da camada
        fields = self.layer.fields()
        # Adiciona os nomes dos campos ao comboBox
        for field in fields:
            self.comboBox.addItem(field.name())

    def getValues(self):
        """
        Obtém os valores dos elementos da interface do usuário.

        Retorna uma tupla contendo os valores dos elementos da interface do usuário, que serão usados para exportação.
        """
        return (
            self.comboBox.currentText(), # Valor selecionado no comboBox
            self.tableCheckBox.isChecked(), # Estado de seleção do checkBox
            self.lineWidthSpinBox.value(),  # Valor do spinBox de largura da linha
            self.lineOpacitySpinBox.value(), # Valor do spinBox de opacidade da linha
            self.areaOpacitySpinBox.value(), # Valor do spinBox de opacidade da área
            self.heightSpinBox.value(),  # Valor do spinBox de altura
            self.checkBox3D.isChecked(), # Estado de seleção do checkBox 3D
            self.radioElevated.isChecked(), # Estado de seleção do radioButton 'Elevated'
            self.radioSolid.isChecked(), # Estado de seleção do radioButton 'Solid'
            self.radioEdges.isChecked(),  # Estado de seleção do radioButton 'Edges'
            self.lineEditImageUrl.text(),  # Texto inserido no lineEdit para URL de imagem
            self.lineEditImageUrl2.text(), # Texto inserido no segundo lineEdit para URL de imagem (se houver)
            #... [adicione mais valores conforme necessário]
        )

class ExportacaoDialogoDXF(QDialog):
    def __init__(self, layer, ui_manager, parent=None):
        """
        Inicializa uma instância do diálogo de exportação DXF, configurando variáveis iniciais e preparando a interface do usuário.
        
        :param layer: A camada do QGIS de onde os dados serão exportados.
        :param ui_manager: Instância do gerenciador de interface do usuário para acessar métodos e dados adicionais.
        :param parent: O widget pai deste diálogo, se houver.
        """
        super(ExportacaoDialogoDXF, self).__init__(parent)
        self.layer = layer  # Armazena a camada QGIS para uso posterior
        self.ui_manager = ui_manager  # Armazena a instância de UiManagerO para acessar métodos específicos

        # Dicionário para armazenar estilos de hachura personalizados
        self.hatchStyles = {}

        # Mapeamento das hachuras do Qt para os padrões correspondentes em EZDXF
        self.qt_to_ezdxf_hatch_map = {
            Qt.CrossPattern: "NET",
            Qt.FDiagPattern: "ANS131",
            Qt.HorPattern: "LINE",
            Qt.SolidPattern: "SOLID",
        }

        # Inicializa a interface do usuário configurando controles e layouts
        self.initUI()

        # Utiliza o método do UiManagerO para obter a cor de preenchimento da camada em formato inteiro
        fill_color_int, _ = self.ui_manager.obter_cores_da_camada(self.layer)
        # Converte o inteiro para um QColor para uso em estilos de hachura
        fill_color_qcolor = QColor.fromRgb(fill_color_int)

        # Cria estilos de hachura com base na cor obtida
        self.create_hatch_styles(fill_color_qcolor)

        # Conecta a mudança de item no listWidget para ativar ou desativar opções de exportação
        self.listWidget.currentItemChanged.connect(self.toggleExportOptions)

    def initUI(self):
        """
        Configura a interface do usuário para o diálogo de exportação, organizando todos os controles necessários,
        incluindo seletores de campos, opções de visualização gráfica e botões de ação.

        Funções e Ações Desenvolvidas:
        - Estruturação de layouts e adição de widgets para configuração de campos, rótulos e visualização gráfica.
        - Configuração de conexões de sinais e slots para interatividade.
        - Inicialização e configuração de elementos gráficos e de controle.
        """
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Raised)
        frameLayout = QVBoxLayout(frame)

        # ComboBox para seleção do campo da camada
        campoCamadaLayout = QHBoxLayout()
        labelCampoCamada = QLabel("Selecione o Campo da Camada:")
        campoCamadaLayout.addWidget(labelCampoCamada)

        self.comboBoxCampoCamada = QComboBox()
        self.comboBoxCampoCamada.addItems([field.name() for field in self.layer.fields()])
        self.comboBoxCampoCamada.setMaxVisibleItems(5)
        campoCamadaLayout.addWidget(self.comboBoxCampoCamada)

        frameLayout.addLayout(campoCamadaLayout)

        # ComboBox e CheckBox para seleção do campo do rótulo
        campoRotuloLayout = QHBoxLayout()
        labelCampoRotulo = QLabel("Selecione o Campo do Rótulo:")
        campoRotuloLayout.addWidget(labelCampoRotulo)

        self.checkBoxCampoRotulo = QCheckBox("Ativar")
        self.checkBoxCampoRotulo.setChecked(False)  # Inicia desmarcado
        campoRotuloLayout.addWidget(self.checkBoxCampoRotulo)

        self.comboBoxCampoRotulo = QComboBox()
        self.comboBoxCampoRotulo.addItems([field.name() for field in self.layer.fields()])
        self.comboBoxCampoRotulo.setMaxVisibleItems(5)
        self.comboBoxCampoRotulo.setEnabled(False)  # Inicia inativo
        campoRotuloLayout.addWidget(self.comboBoxCampoRotulo)

        frameLayout.addLayout(campoRotuloLayout)

        # Conectando o sinal do QCheckBox ao slot que irá ativar/desativar o QComboBox
        self.checkBoxCampoRotulo.stateChanged.connect(self.toggleComboBoxCampoRotulo)

        # Layout principal horizontal para todos os controles
        mainControlLayout = QHBoxLayout()

        # Configurando o QListWidget
        self.listWidget = QListWidget()
        self.listWidget.setFixedSize(120, 169)
        mainControlLayout.addWidget(self.listWidget)

        # Layout vertical para scaleSpinBox, angleScrollBar e graphicsView
        rightSideLayout = QVBoxLayout()

        # Label e QDoubleSpinBox para a escala
        scaleLayout = QHBoxLayout()
        scaleLabel = QLabel("Escala:")
        scaleLayout.addWidget(scaleLabel)

        self.scaleSpinBox = QDoubleSpinBox()
        self.scaleSpinBox.setRange(0.1, 10.0)  # Define a faixa de valores
        self.scaleSpinBox.setSingleStep(0.5)  # Define o incremento dos passos
        self.scaleSpinBox.setValue(1.0)  # Define o valor inicial
        scaleLayout.addWidget(self.scaleSpinBox)

        rightSideLayout.addLayout(scaleLayout)

        # Label e QScrollBar para a rotação
        angleLayout = QHBoxLayout()
        angleLabel = QLabel("Rotação:")
        angleLayout.addWidget(angleLabel)

        self.angleScrollBar = QScrollBar(Qt.Horizontal)
        self.angleScrollBar.setRange(0, 360)  # Ângulo de 0 a 360 graus
        self.angleScrollBar.setSingleStep(1)  # Passo de 1 grau
        self.angleScrollBar.setFixedHeight(10)  # Controla a espessura do QScrollBar
        self.angleScrollBar.setMinimumWidth(100)  # Controla o comprimento mínimo do QScrollBar
        angleLayout.addWidget(self.angleScrollBar)

        rightSideLayout.addLayout(angleLayout)

        # # Configurando o QGraphicsView
        self.graphicsView = QGraphicsView()
        self.graphicsView.setFixedSize(150, 120)
        # Definir políticas de barra de rolagem para nunca mostrar barras de rolagem
        self.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Adicionando dicas de renderização para suavização
        self.graphicsView.setRenderHint(QPainter.Antialiasing, True)
        self.graphicsView.setRenderHint(QPainter.HighQualityAntialiasing, True)
        # self.graphicsView.viewport().setAttribute(Qt.WA_TransparentForMouseEvents, True)  # Bloquear interação do mouse

        rightSideLayout.addWidget(self.graphicsView)

        # Adicionando o layout vertical à direita ao layout principal horizontal
        mainControlLayout.addLayout(rightSideLayout)

        # Adicionando o layout principal horizontal ao layout do frame
        frameLayout.addLayout(mainControlLayout)

        # QDialogButtonBox personalizado
        self.buttonBox = QDialogButtonBox()

        # Botões centralizados
        hbox = QHBoxLayout()
        hbox.addStretch(1)  # Espaço em branco antes dos botões para empurrá-los para o centro
        self.exportButton = QPushButton("Exportar")
        self.exportButton.clicked.connect(self.accept)
        hbox.addWidget(self.exportButton, 0, Qt.AlignCenter)  # Adiciona o botão Exportar centralizado
        self.cancelButton = self.buttonBox.addButton(QDialogButtonBox.Cancel)
        hbox.addWidget(self.cancelButton, 0, Qt.AlignCenter)  # Adiciona o botão Cancelar centralizado
        hbox.addStretch(1)  # Espaço em branco depois dos botões para mantê-los no centro

        # Adiciona o layout com os botões centralizados ao layout principal do frame
        frameLayout.addLayout(hbox)

        # Configuração do layout principal do diálogo
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(frame)
        self.setLayout(mainLayout)

        # Definições do título e geometria do diálogo
        self.setWindowTitle("Configurações de Exportação")
        self.resize(300, 150)
        self.adjustSize()  # Ajusta o tamanho com base nos widgets
        self.centerDialog()

        # Configuração da cena do QGraphicsView
        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)

        # Conectando o sinal de mudança do QListWidget ao slot de atualização da cena
        self.listWidget.currentRowChanged.connect(self.update_hatch_style)

        # Conecta o sinal valueChanged do scaleSpinBox ao slot de atualização
        self.scaleSpinBox.valueChanged.connect(self.update_graphics_view_transform)

        # Conecta o sinal valueChanged do angleScrollBar ao slot de atualização
        self.angleScrollBar.valueChanged.connect(self.update_graphics_view_transform)

        # Conecta o sinal valueChanged do angleScrollBar ao slot de atualização
        self.angleScrollBar.valueChanged.connect(self.show_angle_tooltip)

        self.toggleExportOptions(self.listWidget.currentItem(), None)

        # Checagem de feições e campos
        self.checkLayerFeaturesAndFields()

    def checkLayerFeaturesAndFields(self):
        """
        Verifica se a camada selecionada possui feições e campos, e atualiza os componentes da interface do usuário
        baseados nessas verificações. Este método ajusta a ativação de controles da UI e atualiza as listas de opções
        com base na presença de dados válidos na camada.

        Funções e Ações Desenvolvidas:
        - Verificação da contagem de feições e da existência de campos na camada.
        - Habilitação ou desabilitação de componentes da interface com base na disponibilidade de dados.
        - Atualização dos itens no comboBox e no botão de exportação baseados nas condições da camada.

        :return: None
        """
        # Atualiza o estado dos atributos da classe para refletir a presença de feições e campos
        self.has_features = self.layer.featureCount() > 0
        self.has_fields = len(self.layer.fields()) > 0

        # Habilita o comboBox para seleção de campos somente se houver feições e campos disponíveis
        self.comboBoxCampoCamada.setEnabled(self.has_features and self.has_fields)

        # Habilita o botão de exportação se houver um item selecionado no listWidget e a camada tiver feições e campos
        self.exportButton.setEnabled(self.has_features and self.has_fields and self.listWidget.currentItem() is not None)

        # Se a camada possui feições e campos, popula o comboBox com os nomes dos campos
        if self.has_features and self.has_fields:
            # Limpa itens existentes e adiciona os novos com base nos campos disponíveis
            self.comboBoxCampoCamada.clear()
            self.comboBoxCampoCamada.addItems([field.name() for field in self.layer.fields()])
        else:
            # Caso não haja campos disponíveis, limpa o comboBox e adiciona um item indicativo
            self.comboBoxCampoCamada.clear()
            self.comboBoxCampoCamada.addItem("Nenhum campo disponível")

    def toggleExportOptions(self, current, previous):
        """
        Atualiza a disponibilidade (habilitado/desabilitado) de várias opções e controles de exportação com base na
        seleção atual de um item e na disponibilidade de feições e campos na camada. Este método é crucial para garantir
        que o usuário só possa interagir com controles relevantes quando um item válido está selecionado.

        Funções e Ações Desenvolvidas:
        - Ativação ou desativação do botão de exportação dependendo da seleção e da presença de feições e campos.
        - Ativação ou desativação de controles como spinboxes e barras de rolagem com base na seleção de um item.

        :param current: O item atualmente selecionado (pode ser None se nenhum item estiver selecionado).
        :param previous: O item anteriormente selecionado (não utilizado diretamente, mas disponível para referência).
        """
        # Habilita o botão de exportar se um item está selecionado e a camada tem feições e campos válidos
        self.exportButton.setEnabled(current is not None and self.has_features and self.has_fields)
        
        # Habilita o spinbox de escala se um item está selecionado
        self.scaleSpinBox.setEnabled(current is not None)
        
        # Habilita a barra de rolagem de ângulo se um item está selecionado
        self.angleScrollBar.setEnabled(current is not None)
        
        # Habilita a visualização gráfica se um item está selecionado
        self.graphicsView.setEnabled(current is not None)

    def toggleComboBoxCampoRotulo(self):
        """
        Ativa ou desativa o comboBox de seleção de campos de rótulo com base no estado de um checkBox.
        Esta função é usada para garantir que o usuário só possa escolher um campo de rótulo quando a opção
        correspondente estiver ativa, evitando confusão e erros de configuração.

        Funções e Ações Desenvolvidas:
        - Leitura do estado do checkBox e atualização do estado de habilitação do comboBox.

        :return: None
        """
        # Ajusta a disponibilidade do comboBox de campos de rótulo de acordo com o estado do checkBox
        self.comboBoxCampoRotulo.setEnabled(self.checkBoxCampoRotulo.isChecked())

    def show_angle_tooltip(self, value):
        """
        Exibe um tooltip com o valor atual do ângulo e atualiza a transformação de um QGraphicsView
        com base nesse valor de ângulo. Este método é útil para fornecer feedback visual imediato ao usuário
        quando um ângulo é ajustado usando um controle de interface, como um slider ou scroll bar.

        Funções e Ações Desenvolvidas:
        - Exibição de um tooltip com o valor do ângulo na posição atual do cursor.
        - Atualização opcional da transformação em um QGraphicsView para refletir o novo ângulo.

        :param value: O valor do ângulo a ser exibido e possivelmente aplicado em transformações.
        """
        # Formata o texto do tooltip para mostrar o valor do ângulo
        tooltip_text = f"Ângulo: {value}°"
        # Mostra o tooltip na posição atual do cursor, associado à barra de rolagem do ângulo
        QToolTip.showText(QCursor.pos(), tooltip_text, self.angleScrollBar)

        # Chama o método para atualizar a transformação do QGraphicsView, se necessário
        self.update_graphics_view_transform()

    def create_hatch_styles(self, fill_color):
        """
        Cria e adiciona estilos de hachura para serem usados na renderização gráfica ou em exportações.
        Define uma variedade de padrões visuais que podem representar diferentes materiais ou características,
        como linhas cruzadas para grades, sólidos para áreas preenchidas, ou padrões simulados para texturas específicas.

        Funções e Ações Desenvolvidas:
        - Adiciona estilos de hachura com padrões básicos e simulados.
        - Associa cada estilo de hachura a uma representação gráfica específica e a uma chave de mapeamento para exportação.

        :param fill_color: Cor de preenchimento a ser usada para todos os estilos de hachura.
        """
        # Adiciona estilos de hachura usando padrões do Qt e mapeamento para padrões do EZDXF
        self.add_hatch_style("Linhas Cruzadas", Qt.CrossPattern, fill_color, self.qt_to_ezdxf_hatch_map[Qt.CrossPattern])
        self.add_hatch_style("Linhas Diagonais", Qt.FDiagPattern, fill_color, self.qt_to_ezdxf_hatch_map[Qt.FDiagPattern])
        self.add_hatch_style("Linhas Horizontais", Qt.HorPattern, fill_color, self.qt_to_ezdxf_hatch_map[Qt.HorPattern])
        self.add_hatch_style("Sólido", Qt.SolidPattern, fill_color, self.qt_to_ezdxf_hatch_map[Qt.SolidPattern])

        # Adiciona estilos de hachura com nomes e padrões simulados para representar diferentes texturas ou elementos
        self.add_hatch_style("Cascalho (Simulado)", Qt.Dense7Pattern, fill_color, "GRAVEL")
        self.add_hatch_style("Tijolo (Simulado)", Qt.BDiagPattern, fill_color, "BRICK")
        self.add_hatch_style("Favo de Mel (Simulado)", Qt.Dense7Pattern, fill_color, "HONEY")
        self.add_hatch_style("Triângulo (Simulado)", Qt.Dense7Pattern, fill_color, "TRIANG")
        self.add_hatch_style("Flex (Simulado)", Qt.Dense7Pattern, fill_color, "FLEX")
        self.add_hatch_style("Plantas (Simulado)", Qt.Dense7Pattern, fill_color, "SWAMP")

    def draw_approximate_swamp_pattern(self, fill_color):
        """
        Desenha um padrão de hachura simulando um pântano na cena gráfica. O padrão consiste em uma combinação de
        linhas horizontais, verticais e inclinadas que criam uma representação visual de vegetação densa típica de pântanos.

        :param fill_color: A cor usada para desenhar o padrão.

        Funções e Ações Desenvolvidas:
        - Calcula a quantidade de padrões que cabem na área visível com base no tamanho da janela.
        - Desenha cada padrão repetidamente de acordo com a quantidade calculada.
        """
        # Parâmetros para o desenho do padrão SWAMP
        horizontal_length = 50
        vertical_length = 15  # Metade do comprimento pois estamos desenhando apenas a parte superior
        incline_length = 20
        space_between_patterns = 20  # Espaçamento adicional entre os padrões

        # Ajustando o espaçamento total incluindo o espaço entre os padrões
        pattern_spacing = horizontal_length + space_between_patterns
        width = self.graphicsView.width()
        height = self.graphicsView.height()

        # Obter escala e rotação dos controles da interface
        scale_factor = self.scaleSpinBox.value()
        rotation_angle = self.angleScrollBar.value()

        # Calcula quantos padrões cabem na altura e largura, adicionando extra para cobrir área rotacionada
        cols = int(width // pattern_spacing) + 2
        rows = int(height // (vertical_length + space_between_patterns)) + 2

        # Criar um QGraphicsItemGroup para agrupar todos os padrões SWAMP
        swamp_group = QGraphicsItemGroup()

        for i in range(rows):
            for j in range(cols):
                # Posição central do padrão
                x_center = j * pattern_spacing + pattern_spacing / 2
                y_center = i * (vertical_length + space_between_patterns) + vertical_length / 2

                # Criando o caminho para o padrão SWAMP
                path = QPainterPath()
                # Linha horizontal
                path.moveTo(x_center - horizontal_length / 2, y_center)
                path.lineTo(x_center + horizontal_length / 2, y_center)
                # Linha vertical superior
                path.moveTo(x_center, y_center)
                path.lineTo(x_center, y_center - vertical_length)
                # Linhas inclinadas
                path.moveTo(x_center, y_center)
                path.lineTo(x_center - incline_length * math.cos(math.radians(45)),
                            y_center - incline_length * math.sin(math.radians(45)))
                path.moveTo(x_center, y_center)
                path.lineTo(x_center + incline_length * math.cos(math.radians(45)),
                            y_center - incline_length * math.sin(math.radians(45)))

                # Criando o item gráfico com o caminho e adicionando ao grupo
                swamp_item = QGraphicsPathItem(path)
                swamp_item.setPen(QPen(fill_color, 1))
                swamp_group.addToGroup(swamp_item)

        # Centralizar o grupo do padrão SWAMP em torno do ponto (0, 0)
        pattern_width = cols * pattern_spacing
        pattern_height = rows * (vertical_length + space_between_patterns)
        swamp_group.setTransformOriginPoint(pattern_width / 2, pattern_height / 2)

        # Aplicar escala e rotação
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        transform.rotate(rotation_angle)
        swamp_group.setTransform(transform)

        # Posicionar o grupo no centro do QGraphicsView
        view_center = self.graphicsView.viewport().rect().center()
        scene_center = self.graphicsView.mapToScene(view_center)
        swamp_group.setPos(scene_center.x() - pattern_width / 2, scene_center.y() - pattern_height / 2)

        # Adicionar o grupo à cena
        self.scene.addItem(swamp_group)

    def draw_approximate_triangle_pattern(self, fill_color):
        """
        Desenha um padrão de triângulos na cena gráfica, posicionando-os de forma regular para cobrir toda a área visível.
        Este método é útil para visualizações que requerem uma representação geométrica estilizada, como em interfaces de design gráfico ou visualização de dados.

        :param fill_color: A cor usada para desenhar o contorno dos triângulos.

        Funções e Ações Desenvolvidas:
        - Calcula o número de triângulos que cabem na largura e altura da área de visualização.
        - Cria e posiciona cada triângulo com base em seu índice de coluna e linha.
        - Adiciona cada triângulo à cena gráfica.
        """
        # Configurações para o tamanho e o espaçamento dos triângulos
        triangle_height = 15
        triangle_base = 15
        spacing = 10  # Espaço adicional entre os triângulos
        width = self.graphicsView.width()
        height = self.graphicsView.height()
        
        # Obter escala e rotação dos controles da interface
        scale_factor = self.scaleSpinBox.value()
        rotation_angle = self.angleScrollBar.value()

        # Calcular o número de colunas e linhas de triângulos e adicionar extra para cobrir área rotacionada
        cols = int(width / (triangle_base + spacing)) + 2
        rows = int(height / (triangle_height + spacing / 2)) + 2

        # Criar um QGraphicsItemGroup para agrupar todos os triângulos
        triangle_group = QGraphicsItemGroup()

        for col in range(cols):
            for row in range(rows):
                # Posiciona o triângulo baseado na coluna e linha atual
                x = col * (triangle_base + spacing)
                y = row * (triangle_height + spacing / 2)
                
                # Cria o caminho para o triângulo
                path = QPainterPath()
                path.moveTo(x, y)
                path.lineTo(x + triangle_base / 2, y + triangle_height)
                path.lineTo(x - triangle_base / 2, y + triangle_height)
                path.closeSubpath()
                
                # Cria o item gráfico e adiciona ao grupo
                triangle_item = QGraphicsPathItem(path)
                triangle_item.setPen(QPen(fill_color, 1))  # A cor da borda e a espessura
                triangle_group.addToGroup(triangle_item)

        # Centralizar o grupo de triângulos em torno do ponto (0, 0)
        pattern_width = cols * (triangle_base + spacing)
        pattern_height = rows * (triangle_height + spacing / 2)
        triangle_group.setTransformOriginPoint(pattern_width / 2, pattern_height / 2)

        # Aplicar escala e rotação
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        transform.rotate(rotation_angle)
        triangle_group.setTransform(transform)

        # Posicionar o grupo no centro do QGraphicsView
        view_center = self.graphicsView.viewport().rect().center()
        scene_center = self.graphicsView.mapToScene(view_center)
        triangle_group.setPos(scene_center.x() - pattern_width / 2, scene_center.y() - pattern_height / 2)

        # Adicionar o grupo à cena
        self.scene.addItem(triangle_group)

    def draw_approximate_flex_pattern(self, fill_color):
        """
        Desenha um padrão flexível em ziguezague na cena gráfica. Este padrão é formado por linhas retas com pequenas
        inclinações nas extremidades, dando a impressão de movimento ou flexibilidade.

        :param fill_color: Cor usada para desenhar o padrão.

        Funções e Ações Desenvolvidas:
        - Calcula a disposição do padrão na área de visualização.
        - Cria e posiciona linhas em um padrão de ziguezague com deslocamentos inclinados.
        - Adiciona cada linha criada à cena gráfica.
        """
        # Configurações iniciais para as dimensões e espaçamentos do padrão
        segment_length = 20  # Comprimento do segmento reto
        incline_offset = 5   # Deslocamento das partes inclinadas
        row_spacing = 10     # Espaçamento vertical entre as linhas do padrão
        pattern_spacing = 20 # Espaçamento entre os padrões ziguezague
        width = self.graphicsView.width()
        height = self.graphicsView.height()

        # Obter escala e rotação dos controles da interface
        scale_factor = self.scaleSpinBox.value()
        rotation_angle = self.angleScrollBar.value()

        # Calcular o número de colunas e linhas, adicionando extra para cobrir área rotacionada
        num_cols = int((width / (segment_length + pattern_spacing))) + 2
        num_rows = int((height / row_spacing)) + 2

        # Criar um QGraphicsItemGroup para agrupar todas as linhas do padrão FLEX
        flex_group = QGraphicsItemGroup()

        # Inicia o desenho do padrão
        for row in range(num_rows):
            y = row * row_spacing
            for col in range(num_cols):
                x = col * (segment_length + pattern_spacing)

                # Ponto inicial da linha retilínea do meio
                start_point = QPointF(x, y)
                # Ponto final da linha retilínea do meio
                end_point = QPointF(x + segment_length, y)

                # Calcula os pontos de inclinação com base nos ângulos dados
                left_incline = QPointF(
                    start_point.x() - incline_offset * math.cos(math.radians(-45)),
                    start_point.y() - incline_offset * math.sin(math.radians(-45))
                )
                right_incline = QPointF(
                    end_point.x() + incline_offset * math.cos(math.radians(-45)),
                    end_point.y() + incline_offset * math.sin(math.radians(-45))
                )

                # Cria o caminho para o padrão 'FLEX'
                path = QPainterPath()
                path.moveTo(left_incline)
                path.lineTo(start_point)
                path.lineTo(end_point)
                path.lineTo(right_incline)

                # Cria o item gráfico e adiciona ao grupo
                flex_item = QGraphicsPathItem(path)
                flex_item.setPen(QPen(fill_color, 2))
                flex_group.addToGroup(flex_item)

        # Calcular as dimensões totais do padrão
        pattern_width = num_cols * (segment_length + pattern_spacing)
        pattern_height = num_rows * row_spacing

        # Centralizar o grupo do padrão flex em torno do ponto (0, 0)
        flex_group.setTransformOriginPoint(pattern_width / 2, pattern_height / 2)

        # Aplicar escala e rotação
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        transform.rotate(rotation_angle)
        flex_group.setTransform(transform)

        # Posicionar o grupo no centro do QGraphicsView
        view_center = self.graphicsView.viewport().rect().center()
        scene_center = self.graphicsView.mapToScene(view_center)
        flex_group.setPos(scene_center.x() - pattern_width / 2, scene_center.y() - pattern_height / 2)

        # Adicionar o grupo à cena
        self.scene.addItem(flex_group)

    def draw_approximate_gravel_pattern(self, fill_color):
        """
        Desenha um padrão de cascalho simulando pedras irregulares espalhadas aleatoriamente.
        O padrão é centralizado, escalável e rotacionável de acordo com os controles da interface.

        A função executa as seguintes etapas:
        1. Define parâmetros iniciais, incluindo o número de formas (num_shapes) e o tamanho máximo das pedras (max_size).
        2. Calcula o tamanho da área do padrão (pattern_width e pattern_height) com base nas dimensões da `graphicsView`.
        3. Calcula o tamanho das células da grade (grid_size) para distribuir uniformemente as formas.
        4. Cria um grupo gráfico (`QGraphicsItemGroup`) para agrupar todas as formas de cascalho.
        5. Para cada célula na grade, posiciona aleatoriamente uma forma de cascalho dentro da célula, centralizando o padrão em torno da origem (0, 0).
        6. Cria formas irregulares para simular pedras, usando `QPainterPath`, e adiciona ao grupo.
        7. Centraliza o grupo de cascalho em torno do ponto (0, 0) no espaço gráfico.
        8. Aplica transformações de escala e rotação ao grupo com base nos controles da interface.
        9. Posiciona o grupo de forma que o centro do padrão coincida com o centro da área visível do `QGraphicsView`.
        10. Adiciona o grupo à cena gráfica para que o padrão seja exibido na interface.

        :param fill_color: A cor usada para desenhar as bordas das formas de cascalho.
        """
        num_shapes = 80
        max_size = 10  # Máximo tamanho dos "cascalhos"

        # Obter escala e rotação dos controles da interface
        scale_factor = self.scaleSpinBox.value()
        rotation_angle = self.angleScrollBar.value()

        # Definir as dimensões do padrão (ajustadas para centralização)
        pattern_width = self.graphicsView.width()
        pattern_height = self.graphicsView.height()

        # Calcula o tamanho da célula da grade com base no número desejado de cascalhos
        grid_size = int(math.sqrt(pattern_width * pattern_height / num_shapes))
        cols = int(pattern_width / grid_size) + 2  # Adiciona extra para cobrir área rotacionada
        rows = int(pattern_height / grid_size) + 2

        # Criar um QGraphicsItemGroup para agrupar todas as formas de cascalho
        gravel_group = QGraphicsItemGroup()

        for i in range(cols):
            for j in range(rows):
                # Posição inicial da célula, centralizada em torno de (0, 0)
                x_start = (i - cols / 2) * grid_size
                y_start = (j - rows / 2) * grid_size

                # Centraliza o cascalho na célula com algum deslocamento aleatório
                x_center = x_start + random.uniform(max_size, grid_size - max_size)
                y_center = y_start + random.uniform(max_size, grid_size - max_size)

                # Cria um caminho com pontos irregulares para simular um cascalho
                size = random.uniform(max_size * 0.5, max_size)
                path = QPainterPath()
                start_angle = random.uniform(0, 2 * math.pi)
                path.moveTo(x_center + size * math.cos(start_angle), y_center + size * math.sin(start_angle))
                for angle in range(1, 360, random.randint(20, 50)):  # Intervalo cria "lados" irregulares
                    irregularity = random.uniform(1, 1.2)
                    theta = math.radians(angle) + start_angle
                    x = x_center + irregularity * size * math.cos(theta)
                    y = y_center + irregularity * size * math.sin(theta)
                    path.lineTo(x, y)
                path.closeSubpath()

                # Cria um item gráfico com o caminho e adiciona ao grupo
                gravel = QGraphicsPathItem(path)
                gravel.setPen(QPen(fill_color, 1.1))
                gravel_group.addToGroup(gravel)

        # Centralizar o grupo de cascalhos em torno do ponto (0, 0)
        gravel_group.setTransformOriginPoint(0, 0)

        # Aplicar escala e rotação
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        transform.rotate(rotation_angle)
        gravel_group.setTransform(transform)

        # Posicionar o grupo no centro do QGraphicsView
        view_center = self.graphicsView.viewport().rect().center()
        scene_center = self.graphicsView.mapToScene(view_center)
        gravel_group.setPos(scene_center.x(), scene_center.y())

        # Adicionar o grupo à cena
        self.scene.addItem(gravel_group)

    def draw_approximate_brick_pattern(self, fill_color):
        """
        Desenha um padrão de tijolos retangulares em uma cena gráfica dentro do QGraphicsView. O padrão é ajustado
        para permitir rotação e escala com base nos controles de interface (scaleSpinBox e angleScrollBar), 
        e é centralizado na área visível da interface gráfica.

        A função executa as seguintes etapas:
        1. Define as dimensões dos tijolos (brick_width e brick_height).
        2. Obtém o valor da escala e rotação a partir dos controles da interface.
        3. Calcula o número de colunas e linhas de tijolos necessárias para cobrir a área visível, adicionando
           um extra para garantir que a área seja completamente coberta após a rotação.
        4. Cria um grupo de gráficos (`QGraphicsItemGroup`) para agrupar todos os tijolos.
        5. Para cada linha e coluna, cria tijolos individuais (`QGraphicsRectItem`), aplicando um deslocamento
           alternado em linhas ímpares para simular um padrão de alvenaria (offset horizontal).
        6. Centraliza o padrão de tijolos em torno do ponto (0, 0) no espaço gráfico, aplicando as transformações
           de escala e rotação.
        7. Posiciona o padrão de tijolos de forma que o centro do padrão coincida com o centro da área visível
           do `QGraphicsView`.
        8. Adiciona o grupo de tijolos à cena gráfica para que o padrão seja exibido na interface.

        :param fill_color: A cor usada para desenhar as bordas dos tijolos.
        """
        # Definir as dimensões do tijolo e obter escala e rotação dos controles da interface
        brick_width = 40
        brick_height = 20
        scale_factor = self.scaleSpinBox.value()
        rotation_angle = self.angleScrollBar.value()
        
        # Preparar variáveis
        width = self.graphicsView.width()
        height = self.graphicsView.height()
        
        # Determinar quantos tijolos cabem horizontalmente e verticalmente
        num_cols = int(width / brick_width) + 2  # Adicionar extra para cobrir área rotacionada
        num_rows = int(height / brick_height) + 2
        
        # Calcular as dimensões totais do padrão
        pattern_width = num_cols * brick_width
        pattern_height = num_rows * brick_height
        
        # Criar um QGraphicsItemGroup para agrupar todos os tijolos
        brick_group = QGraphicsItemGroup()
        
        for row in range(num_rows):
            # Alternar o deslocamento de linha (offset horizontal)
            row_offset = (row % 2) * (brick_width / 2)
            y = row * brick_height
            
            for col in range(num_cols):
                x = col * brick_width + row_offset
                # Criar um item retangular representando o tijolo
                brick = QGraphicsRectItem(x, y, brick_width, brick_height)
                brick.setPen(QPen(fill_color, 1))
                # Adicionar o tijolo ao grupo
                brick_group.addToGroup(brick)
        
        # Centralizar o padrão em torno do ponto (0, 0)
        brick_group.setTransformOriginPoint(pattern_width / 2, pattern_height / 2)
        
        # Aplicar escala e rotação
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        transform.rotate(rotation_angle)
        brick_group.setTransform(transform)
        
        # Posicionar o grupo no centro do QGraphicsView
        view_center = self.graphicsView.viewport().rect().center()
        scene_center = self.graphicsView.mapToScene(view_center)
        brick_group.setPos(scene_center.x() - pattern_width / 2, scene_center.y() - pattern_height / 2)
        
        # Adicionar o grupo à cena
        self.scene.addItem(brick_group)

    def draw_approximate_honey_pattern(self, fill_color):
        """
        Desenha um padrão de favo de mel com hexágonos regulares na cena gráfica. O padrão simula a estrutura natural
        de um favo de mel, amplamente utilizado em visualizações que necessitam de padrões geométricos repetidos.

        :param fill_color: Cor utilizada para desenhar o contorno dos hexágonos.

        Funções e Ações Desenvolvidas:
        - Calcula o número de colunas e linhas de hexágonos que cabem na área de visualização.
        - Alternância do deslocamento horizontal a cada linha para imitar a disposição natural de um favo de mel.
        - Criação e posicionamento de cada hexágono dentro da área da visualização.
        """
        # Configurações iniciais para o tamanho dos hexágonos
        hex_radius = 15  # Raio do hexágono
        hex_apothem = hex_radius * math.sqrt(3) / 2  # Distância do centro do hexágono ao meio de uma das arestas
        
        # Obter escala e rotação dos controles da interface
        scale_factor = self.scaleSpinBox.value()
        rotation_angle = self.angleScrollBar.value()

        # Dimensões da área de visualização
        width = self.graphicsView.width()
        height = self.graphicsView.height()

        # Calcula quantas colunas e linhas cabem na área disponível
        rows = int(height // (hex_radius * 1.5)) + 2  # Adiciona extra para cobrir área rotacionada
        cols = int(width // (hex_apothem * 2)) + 2

        # Criar um QGraphicsItemGroup para agrupar todos os hexágonos
        honeycomb_group = QGraphicsItemGroup()

        # Itera sobre cada linha e coluna para desenhar os hexágonos
        for row in range(rows):
            for col in range(cols):
                # Alternar o deslocamento a cada outra linha
                if row % 2 == 0:
                    x_offset = col * hex_apothem * 2
                else:
                    x_offset = col * hex_apothem * 2 + hex_apothem

                y_offset = row * (hex_radius * 1.5)

                # Cria o caminho do hexágono
                path = QPainterPath()
                angle_deg = 30
                angle_rad = math.pi / 180 * angle_deg

                # Adiciona os pontos para formar o hexágono
                for i in range(6):
                    x = hex_radius * math.cos(angle_rad + (math.pi / 3 * i)) + x_offset
                    y = hex_radius * math.sin(angle_rad + (math.pi / 3 * i)) + y_offset
                    if i == 0:
                        path.moveTo(x, y)
                    else:
                        path.lineTo(x, y)
                path.closeSubpath()

                # Cria o item do hexágono e adiciona ao grupo
                hex_item = QGraphicsPathItem(path)
                hex_item.setPen(QPen(fill_color, 1))  # Define a borda do favo de mel
                honeycomb_group.addToGroup(hex_item)

        # Centralizar o grupo de hexágonos em torno do ponto (0, 0)
        pattern_width = cols * hex_apothem * 2
        pattern_height = rows * hex_radius * 1.5
        honeycomb_group.setTransformOriginPoint(pattern_width / 2, pattern_height / 2)

        # Aplicar escala e rotação
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        transform.rotate(rotation_angle)
        honeycomb_group.setTransform(transform)

        # Posicionar o grupo no centro do QGraphicsView
        view_center = self.graphicsView.viewport().rect().center()
        scene_center = self.graphicsView.mapToScene(view_center)
        honeycomb_group.setPos(scene_center.x() - pattern_width / 2, scene_center.y() - pattern_height / 2)

        # Adicionar o grupo à cena
        self.scene.addItem(honeycomb_group)

    def update_hatch_style(self, currentRow):
        """
        Atualiza o estilo de hachura na cena gráfica com base na seleção do usuário. Manipula diferentes padrões de hachura,
        incluindo desenhos simulados e configurações de padrão e cor de elementos regulares.

        :param currentRow: Índice da linha atual selecionada no widget de lista que define o estilo de hachura.

        Funções e Ações Desenvolvidas:
        - Limpa a cena gráfica atual.
        - Reseta os controles de interface para valores padrão de escala e ângulo.
        - Aplica o estilo de hachura selecionado, desenhando padrões específicos ou configurando a aparência de um círculo.
        """
        # Limpa todos os itens gráficos da cena
        self.scene.clear()
        # Obtem o nome do estilo do item atual na lista
        style_name = self.listWidget.item(currentRow).text()

        # Resetar a escala e o ângulo para os valores padrão
        self.scaleSpinBox.setValue(1.0)
        self.angleScrollBar.setValue(0)

         # Checa se o estilo pertence a padrões simulados e desenha o padrão apropriado
        if style_name in ["Cascalho (Simulado)", "Tijolo (Simulado)", "Favo de Mel (Simulado)", "Triângulo (Simulado)", "Flex (Simulado)", "Plantas (Simulado)"]:
            # Obtemos a cor do estilo atual e desenhamos o padrão
            _, color, _ = self.hatchStyles[style_name]
            if style_name == "Cascalho (Simulado)":
                self.draw_approximate_gravel_pattern(color)
            elif style_name == "Tijolo (Simulado)":
                self.draw_approximate_brick_pattern(color)
            elif style_name == "Favo de Mel (Simulado)":
                self.draw_approximate_honey_pattern(color)
            elif style_name == "Triângulo (Simulado)":
                self.draw_approximate_triangle_pattern(color)
            elif style_name == "Flex (Simulado)":
                self.draw_approximate_flex_pattern(color)
            elif style_name == "Plantas (Simulado)":
                self.draw_approximate_swamp_pattern(color)
            return  # Encerrar a função para evitar desenhar o círculo

        # Desempacota o padrão, a cor e o padrão do ezdxf do estilo selecionado
        pattern, color, ezdxf_pattern = self.hatchStyles[style_name]

        # Configura e desenha um círculo grande para demonstrar o padrão no QGraphicsView
        circle_diameter = min(self.graphicsView.width(), self.graphicsView.height()) * 50
        circle_x = (self.graphicsView.width() - circle_diameter) / 2
        circle_y = (self.graphicsView.height() - circle_diameter) / 2
        circle = QGraphicsEllipseItem(circle_x, circle_y, circle_diameter, circle_diameter)

        # Configura a cor e o padrão do pincel
        if pattern == Qt.TexturePattern:
            brush = QBrush(color)  # Assumindo que 'color' é um QPixmap ou QColor apropriado
        else:
            brush = QBrush(pattern)
            brush.setColor(color)  # Define a cor para o pincel
        circle.setBrush(brush)

        # Configura a caneta como transparente
        pen = QPen(Qt.NoPen)
        circle.setPen(pen)
        # Define o ponto de transformação para o centro do círculo
        circle.setTransformOriginPoint(circle_diameter / 2, circle_diameter / 2)
        # Aplica a escala e rotação mantendo o hatch centralizado
        circle.setScale(self.scaleSpinBox.value())
        circle.setRotation(self.angleScrollBar.value())

        self.scene.addItem(circle) # Adiciona o círculo à cena
        self.scene.update()  # Atualiza a cena para refletir as mudanças

    def add_hatch_style(self, style_name, qt_pattern, color, ezdxf_pattern):
        """
        Adiciona um estilo de hachura ao dicionário interno e à lista de interface do usuário para seleção.
        Cada estilo contém um padrão do Qt, uma cor, e um padrão correspondente do EZDXF, permitindo que seja 
        usado tanto para renderização gráfica quanto para exportação para arquivos DXF.

        Funções e Ações Desenvolvidas:
        - Registro do estilo de hachura no dicionário interno para referência futura.
        - Adição do nome do estilo na lista de interface do usuário para facilitar a seleção pelo usuário.

        :param style_name: Nome descritivo do estilo de hachura.
        :param qt_pattern: Padrão de hachura do Qt usado para a renderização gráfica.
        :param color: Cor aplicada ao padrão de hachura.
        :param ezdxf_pattern: Padrão correspondente no formato EZDXF, utilizado para exportação para DXF.
        """
        # Armazena o estilo de hachura no dicionário com o nome como chave
        self.hatchStyles[style_name] = (qt_pattern, color, ezdxf_pattern)
        
        # Adiciona o nome do estilo ao listWidget para permitir seleção pelo usuário
        self.listWidget.addItem(style_name)

    def update_graphics_view_transform(self):
        """
        Atualiza a transformação aplicada ao QGraphicsView, ajustando a escala e a rotação conforme
        especificado pelos controles de interface do usuário. Este método permite que o usuário visualize
        as mudanças gráficas em tempo real ao interagir com os controles de escala e ângulo.

        Funções e Ações Desenvolvidas:
        - Leitura dos valores atuais dos controles de escala e ângulo.
        - Criação de uma nova transformação gráfica que aplica esses valores.
        - Aplicação da transformação ao QGraphicsView para atualizar a visualização.

        :return: None
        """
        # Obtém os valores de escala e ângulo dos respectivos controles da interface do usuário
        scale_factor = self.scaleSpinBox.value()
        angle = self.angleScrollBar.value()

        # Cria uma nova transformação QTransform
        transform = QTransform()
        # Aplica a escala à transformação
        transform.scale(scale_factor, scale_factor)
        # Aplica a rotação à transformação
        transform.rotate(angle)

        # Aplica a nova transformação ao QGraphicsView
        self.graphicsView.setTransform(transform)

    def centerDialog(self):
        """
        Centraliza o diálogo na tela do usuário. Este método calcula o ponto central da tela disponível
        e ajusta a posição da janela do diálogo para que esteja alinhada com este ponto central.

        Funções e Ações Desenvolvidas:
        - Obtenção da geometria atual da janela do diálogo.
        - Cálculo do ponto central da área de trabalho disponível.
        - Ajuste da posição da janela para que seu centro corresponda ao ponto central da tela.

        :return: None
        """
        # Captura a geometria atual da janela do diálogo
        frameGeometry = self.frameGeometry()
        # Acessa o ponto central da área de trabalho disponível na tela
        centerPoint = QDesktopWidget().availableGeometry().center()
        # Ajusta a geometria da janela para que seu centro alinhe-se com o ponto central da tela
        frameGeometry.moveCenter(centerPoint)
        # Move a janela para a nova posição calculada
        self.move(frameGeometry.topLeft())

    def Obter_Valores(self):
        """
        Coleta e retorna os valores configurados na interface do usuário para campos relacionados à camada,
        rótulos, escala de hachura, rotação e padrões de hachura. Este método é útil para operações que
        necessitam dessas configurações, como a exportação de dados ou a aplicação de estilos gráficos.

        Funções e Ações Desenvolvidas:
        - Obtenção do texto atual do comboBox para o campo da camada e do campo de rótulo.
        - Verificação se o checkbox para o campo de rótulo está marcado e, em caso afirmativo, obtenção do campo correspondente.
        - Coleta dos valores de escala e rotação das hachuras.
        - Obtenção do estilo de hachura selecionado e do padrão correspondente para exportação.

        :return: Tupla contendo o nome do campo da camada, campo de rótulo (ou None), padrão de hachura para DXF, escala e rotação de hachura.
        """
        # Obtém o texto do campo atualmente selecionado no comboBox da camada
        campo_camada = self.comboBoxCampoCamada.currentText()
        # Verifica se o checkbox para rótulos está marcado e obtém o campo correspondente, se aplicável
        campo_rotulo = self.comboBoxCampoRotulo.currentText() if self.checkBoxCampoRotulo.isChecked() else None
        # Coleta o valor de escala da hachura do spinBox
        escala_hachura = self.scaleSpinBox.value()
        # Coleta o valor de rotação da hachura da barra de rolagem
        rotacao_hachura = self.angleScrollBar.value()
        # Obtém o nome do estilo de hachura selecionado no listWidget
        estilo_hachura = self.listWidget.currentItem().text()
        # Acessa o padrão de hachura correspondente para exportação, definido no dicionário de estilos
        ezdxf_pattern = self.hatchStyles[estilo_hachura][2]

        return campo_camada, campo_rotulo, ezdxf_pattern, escala_hachura, rotacao_hachura

class PolygonDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index):
        """
        Sobrescreve o método de pintura para adicionar uma representação gráfica (retângulo) 
        que reflete a cor da camada do polígono e a cor da borda do símbolo antes da caixinha de visibilidade de cada item no treeView.
        """
        super().paint(painter, option, index)

        # Obtém o ID da camada do item do modelo
        layer_id = index.data(Qt.UserRole)
        if not layer_id:
            layer_id = index.model().itemFromIndex(index).data()

        layer = QgsProject.instance().mapLayer(layer_id)

        if layer:
            # Define a cor padrão para o retângulo e a borda
            rect_color = Qt.white
            border_color = Qt.black
            min_border_thickness = 1.1  # Espessura mínima da borda

            symbols = layer.renderer().symbols(QgsRenderContext())
            if symbols:
                rect_color = symbols[0].color()
                if symbols[0].symbolLayerCount() > 0:
                    border_layer = symbols[0].symbolLayer(0)
                    if hasattr(border_layer, 'strokeColor'):
                        border_color = border_layer.strokeColor()
                    if hasattr(border_layer, 'strokeWidth'):
                        # Certifica-se de que a espessura da borda não seja menor que a mínima definida
                        border_thickness = max(border_layer.strokeWidth(), min_border_thickness)
                    else:
                        border_thickness = min_border_thickness
                else:
                    border_thickness = min_border_thickness
            else:
                border_thickness = min_border_thickness

            # Desenho do retângulo com a cor da camada e borda
            polygonRect = QRect(option.rect.left() - 15, option.rect.top() + 12, 15, option.rect.height() - 25)
            painter.setBrush(QBrush(rect_color))
            painter.setPen(QPen(border_color, border_thickness))
            painter.drawRect(polygonRect)

            # Desloca o texto para a direita para dar espaço ao retângulo
            option.rect.setLeft(int(option.rect.left() + 20 + border_thickness))  # Converte border_thickness para int



