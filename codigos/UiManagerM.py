from qgis.core import QgsProject, QgsMapLayer, QgsWkbTypes, Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsLayerTreeLayer,  QgsGeometry, QgsLayerTree, QgsVectorLayer, QgsField, QgsPoint, QgsFeature, QgsMeshLayer, edit, QgsMeshRendererScalarSettings,  QgsProcessingException
from PyQt5.QtWidgets import QTreeView, QStyledItemDelegate, QColorDialog, QMenu, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog, QComboBox, QFrame, QCheckBox, QProgressBar, QListWidget, QScrollBar, QStyle, QGraphicsDropShadowEffect, QDoubleSpinBox, QSpinBox, QRadioButton, QSlider, QGridLayout, QSpacerItem, QSizePolicy, QWidget
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon, QPixmap, QPainter, QColor, QPen, QFont, QPalette
from PyQt5.QtCore import Qt, QPoint, QRect, QEvent, QCoreApplication, QSettings, QItemSelectionModel, QSize, QVariant
from pyqtgraph.opengl import GLViewWidget, GLLinePlotItem
import xml.etree.ElementTree as ET
import pyqtgraph.opengl as gl
from qgis.utils import iface
from lxml import etree
import pyqtgraph as pg
import numpy as np
import processing
import simplekml
import ezdxf
import time
import os

class UiManagerM:
    """
    Gerencia a interface do usuário, interagindo com um QTreeView para listar e gerenciar camadas de malhas no QGIS.
    """
    def __init__(self, iface, dialog):
        """
        Inicializa a instância da classe UiManagerM, responsável por gerenciar a interface do usuário
        que interage com um QTreeView para listar e gerenciar camadas de malhas no QGIS.

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

        self.dlg.treeViewListaMalha.setModel(self.treeViewModel)

        # Inicializa o QTreeView com as configurações necessárias
        self.init_treeView()

        # Conecta os sinais do QGIS e da interface do usuário para sincronizar ações e eventos
        self.connect_signals()

    def init_treeView(self):
        """
        Configura o QTreeView para listar e gerenciar camadas de malhas. 
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
        self.atualizar_treeView_lista_malha()

        # Conecta o evento de mudança em um item para atualizar a visibilidade da camada
        self.treeViewModel.itemChanged.connect(self.on_item_changed)

        # Configura a política de menu de contexto para permitir menus personalizados em cliques com o botão direito
        self.dlg.treeViewListaMalha.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dlg.treeViewListaMalha.customContextMenuRequested.connect(self.open_context_menu)

        # Aplica estilos CSS para aprimorar a interação visual com os itens do QTreeView
        self.dlg.treeViewListaMalha.setStyleSheet("""
            QTreeView::item:hover:!selected {
                background-color: #def2fc;
            }
            QTreeView::item:selected {
            }""")

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
        QgsProject.instance().layersRemoved.connect(self.atualizar_treeView_lista_malha)

        # Conecta o evento de mudança em um item do QTreeView para atualizar a visibilidade da camada no QGIS
        self.treeViewModel.itemChanged.connect(self.on_item_changed)

        # Define e aplica um delegado personalizado para customização da exibição de itens no QTreeView
        self.dlg.treeViewListaMalha.setItemDelegate(CustomDelegate(self.dlg.treeViewListaMalha))

        # Sincroniza o estado das camadas no QGIS com o checkbox do QTreeView sempre que as camadas do mapa mudam
        self.iface.mapCanvas().layersChanged.connect(self.sync_from_qgis_to_treeview)

        # Conecta mudanças na seleção do QTreeView para atualizar a camada ativa no QGIS
        self.dlg.treeViewListaMalha.selectionModel().selectionChanged.connect(self.on_treeview_selection_changed)

        # Sincroniza a seleção no QGIS com a seleção no QTreeView quando a camada ativa no QGIS muda
        self.iface.currentLayerChanged.connect(self.on_current_layer_changed)

        # Inicia a conexão de sinais para tratar a mudança de nome das camadas no projeto
        self.connect_name_changed_signals()

        # Conectar o botão à função 3D
        self.dlg.pushButtonMalha3D.clicked.connect(self.mostrar_dialogo_exporta_malha_3d)

        # Conectar o botão à função KML
        self.dlg.pushButtonMalhaKML.clicked.connect(self.exportar_malha_kml)

        # Conectando o botão pushButton3DMalha
        self.dlg.pushButton3DMalha.clicked.connect(self.abrir_visualizador_malha_3d)

        # Conectando o botão pushButtonFecharM à função que fecha o diálogo
        self.dlg.pushButtonFecharM.clicked.connect(self.close_dialog)

    def close_dialog(self):
        """
        Fecha o diálogo associado a este UiManagerM:
        """
        self.dlg.close()
        
    def on_treeview_selection_changed(self, selected, deselected):
        """
        Esta função é chamada quando a seleção no QTreeView muda. 
        Ela obtém o índice do item selecionado, extrai o nome da camada, 
        encontra a camada correspondente no projeto QGIS e define essa camada como ativa.

        Detalhes:
        - Obtém os índices dos itens selecionados no QTreeView.
        - Se houver itens selecionados:
            - Extrai o nome da camada do item selecionado.
            - Busca a camada no projeto QGIS pelo nome.
            - Se a camada for encontrada, define-a como a camada ativa no QGIS.
        """
        # Obtém os índices dos itens selecionados no QTreeView
        indexes = self.dlg.treeViewListaMalha.selectionModel().selectedIndexes()
        
        # Verifica se há algum índice selecionado
        if indexes:
            # Extrai o nome da camada do item selecionado no QTreeView
            selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
            
            # Busca a camada por nome no projeto do QGIS
            layers = QgsProject.instance().mapLayersByName(selected_layer_name)
            
            # Se a camada existir, define-a como a camada ativa
            if layers:
                self.iface.setActiveLayer(layers[0])

    def atualizar_treeView_lista_malha(self):
        """
        Esta função atualiza a lista de camadas raster no QTreeView. 
        Ela limpa o modelo existente, adiciona um cabeçalho, 
        itera sobre todas as camadas no projeto do QGIS, filtra as camadas raster,
        cria itens para essas camadas e ajusta a fonte dos itens conforme necessário.
        Por fim, garante que a última camada esteja selecionada no QTreeView.

        Detalhes:
        - Limpa o modelo do QTreeView.
        - Adiciona um item de cabeçalho ao modelo.
        - Obtém a raiz da árvore de camadas do QGIS e todas as camadas do projeto.
        - Itera sobre todas as camadas do projeto.
            - Filtra para incluir apenas camadas raster.
            - Cria um item para cada camada raster com nome, verificável e não editável diretamente.
            - Define o estado de visibilidade do item com base no estado do nó da camada.
            - Ajusta a fonte do item com base no tipo de camada (temporária ou permanente).
            - Adiciona o item ao modelo do QTreeView.
        - Seleciona a última camada no QTreeView.
        """
        # Limpa o modelo existente para assegurar que não haja itens desatualizados
        self.treeViewModel.clear()
        
        # Cria e configura um item de cabeçalho para a lista
        headerItem = QStandardItem('Lista de Camadas de Malhas')
        headerItem.setTextAlignment(Qt.AlignCenter)
        self.treeViewModel.setHorizontalHeaderItem(0, headerItem)

        # Acessa a raiz da árvore de camadas do QGIS para obter todas as camadas
        root = QgsProject.instance().layerTreeRoot()
        layers = QgsProject.instance().mapLayers().values()

        # Itera sobre todas as camadas do projeto
        for layer in layers:
            # Filtra para incluir apenas camadas malhas
            if layer.type() == QgsMapLayer.MeshLayer:
                # Cria um item para a camada com nome, verificável e não editável diretamente
                item = QStandardItem(layer.name())
                item.setCheckable(True)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(layer, Qt.UserRole) # Armazene o próprio objeto da camada

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
        Esta função garante que uma camada raster esteja sempre selecionada no QTreeView.
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
        model = self.dlg.treeViewListaMalha.model()
        
        # Conta o número de linhas (camadas) no modelo
        row_count = model.rowCount()

        # Verifica se há camadas no modelo
        if row_count > 0:
            # Obtém o índice da última camada no modelo
            last_index = model.index(row_count - 1, 0)
            
            # Define a seleção atual para o índice da última camada
            self.dlg.treeViewListaMalha.setCurrentIndex(last_index)
            
            # Garante que a última camada esteja visível no QTreeView
            self.dlg.treeViewListaMalha.scrollTo(last_index)
        else:
            # Obtém o índice da primeira camada no modelo
            first_index = model.index(0, 0)
            
            # Verifica se o índice da primeira camada é válido
            if first_index.isValid():
                # Define a seleção atual para o índice da primeira camada
                self.dlg.treeViewListaMalha.setCurrentIndex(first_index)
                
                # Garante que a primeira camada esteja visível no QTreeView
                self.dlg.treeViewListaMalha.scrollTo(first_index)

    def on_current_layer_changed(self, layer):
        """
        Esta função é chamada quando a camada ativa no QGIS muda.
        Ela verifica se a camada ativa é uma camada raster e, se for, 
        atualiza a seleção no QTreeView para corresponder à camada ativa.
        Se a camada ativa não for uma camada raster, reverte a seleção 
        para a última camada raster selecionada no QTreeView.

        Detalhes:
        - Verifica se a camada ativa existe e se é uma camada raster.
        - Se for uma camada raster:
            - Obtém o modelo associado ao QTreeView.
            - Itera sobre todas as linhas no modelo para encontrar a camada correspondente.
            - Quando encontrada, seleciona e garante que a camada esteja visível no QTreeView.
        - Se a camada ativa não for uma camada raster, seleciona a última camada raster no QTreeView.
        """
        # Verifica se a camada ativa existe e se é uma camada raster
        if layer and layer.type() == QgsMapLayer.MeshLayer:
            # Obtém o modelo associado ao QTreeView
            model = self.dlg.treeViewListaMalha.model()
            
            # Itera sobre todas as linhas no modelo
            for row in range(model.rowCount()):
                # Obtém o item da linha atual
                item = model.item(row, 0)
                
                # Verifica se o nome do item corresponde ao nome da camada ativa
                if item.text() == layer.name():
                    # Obtém o índice do item correspondente
                    index = model.indexFromItem(item)
                    
                    # Define a seleção atual para o índice do item correspondente
                    self.dlg.treeViewListaMalha.setCurrentIndex(index)
                    
                    # Garante que o item correspondente esteja visível no QTreeView
                    self.dlg.treeViewListaMalha.scrollTo(index)
                    
                    # Interrompe a iteração, pois a camada correspondente foi encontrada
                    break
        else:
            # Se a camada ativa não for uma camada raster, seleciona a última camada raster no QTreeView
            self.selecionar_ultima_camada()

    def adjust_item_font(self, item, layer):
        """
        Esta função ajusta a fonte do item no QTreeView com base no tipo de camada.
        Se a camada for temporária (dados em memória), ajusta a fonte para itálico.
        Se a camada for permanente, ajusta a fonte para negrito.

        Detalhes:
        - Cria um objeto QFont para ajustar a fonte do item.
        - Verifica se a camada é temporária usando o método isTemporary().
        - Se a camada for temporária, ajusta a fonte para itálico.
        - Se a camada for permanente, ajusta a fonte para negrito.
        - Aplica a fonte ajustada ao item no QTreeView.
        - Retorna o item com a fonte ajustada para uso posterior, se necessário.
        """
        # Cria um objeto QFont para ajustar a fonte do item
        fonte_item = QFont()

        # Verifica se a camada é temporária (dados em memória) e ajusta a fonte para itálico
        if layer.isTemporary():
            fonte_item.setItalic(True)
        # Se não for temporária, ajusta a fonte para negrito, indicando uma camada permanente
        else:
            fonte_item.setBold(True)

        # Aplica a fonte ajustada ao item no QTreeView
        item.setFont(fonte_item)

        # Retorna o item com a fonte ajustada para uso posterior se necessário
        return item

    def connect_name_changed_signals(self):
        """
        Conecta o sinal de mudança de nome de todas as camadas de raster existentes no projeto QGIS.
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
        e conectando sinais de mudança de nome para camadas de malhas recém-adicionadas.

        Este método verifica cada camada adicionada para determinar se é uma camada de vetor de malhas.
        Se for, ele atualiza a lista de camadas no QTreeView e conecta o sinal de mudança de nome à função
        de callback apropriada.

        :param layers: Lista de camadas recém-adicionadas ao projeto.

        Funções e Ações Desenvolvidas:
        - Verificação do tipo e da geometria das camadas adicionadas.
        - Atualização da visualização da lista de camadas no QTreeView para incluir novas camadas de malhas.
        - Conexão do sinal de mudança de nome da camada ao método de tratamento correspondente.
        """
        # Itera por todas as camadas adicionadas
        for layer in layers:
            # Verifica se a camada é do tipo vetor e se sua geometria é de raster
            if layer.type() == QgsMapLayer.MeshLayer:
                # Atualiza a lista de camadas no QTreeView
                self.atualizar_treeView_lista_malha()
                # Conecta o sinal de mudança de nome da nova camada ao método on_layer_name_changed
                layer.nameChanged.connect(self.on_layer_name_changed)
                # Interrompe o loop após adicionar o sinal à primeira camada de raster encontrada
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
        self.atualizar_treeView_lista_malha()

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

    def open_context_menu(self, position):
        """
        Esta função abre um menu de contexto ao clicar com o botão direito na árvore de visualização (QTreeView).
        Se um item for selecionado, cria e exibe um menu de contexto com a opção de abrir as propriedades da camada.
        
        Detalhes:
        - Obtém os índices dos itens selecionados no QTreeView.
        - Verifica se há algum item selecionado.
        - Se houver um item selecionado:
            - Cria um novo menu de contexto.
            - Adiciona a opção "Abrir Propriedades da Camada" ao menu de contexto.
            - Exibe o menu de contexto na posição do cursor.
            - Executa a ação correspondente se a opção "Abrir Propriedades da Camada" for selecionada.
        """
        # Obtém os índices dos itens selecionados na árvore de visualização
        indexes = self.dlg.treeViewListaMalha.selectedIndexes()
        
        # Verifica se algum item foi selecionado
        if indexes:
            # Cria um novo menu de contexto
            menu = QMenu()
            
            # Adiciona uma ação ao menu de contexto
            layer_properties_action = menu.addAction("Abrir Propriedades da Camada")
            
            # Exibe o menu de contexto na posição do cursor e obtém a ação selecionada pelo usuário
            action = menu.exec_(self.dlg.treeViewListaMalha.viewport().mapToGlobal(position))
            
            # Verifica se a ação selecionada foi "Abrir Propriedades da Camada"
            if action == layer_properties_action:
                # Abre as propriedades da camada para o item selecionado
                self.abrir_layer_properties(indexes[0])

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
        layer = QgsProject.instance().mapLayer(layer_id.id())
        
        # Se a camada for encontrada, exibe a janela de propriedades da camada
        if layer:
            self.iface.showLayerProperties(layer)

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
        progressMessageBar = self.iface.messageBar().createMessage("Exportando camada para KML")
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

    def mostrar_dialogo_exporta_malha_3d(self):
        """
        Exibe o diálogo para exportação da malha 3D e conecta os botões para exportação em diferentes formatos.

        Funções e Ações Desenvolvidas:
        - Cria e exibe o diálogo ExportaMalha3D.
        - Conecta os botões do diálogo às funções de exportação correspondentes (DXF, DAE, OBJ, STL).
        - Executa o diálogo de exportação de malha 3D.

        """
        # Cria uma instância do diálogo ExportaMalha3D passando o diálogo principal como pai
        self.dlg_exporta_malha = ExportaMalha3D(self.dlg)
        
        # Conecta o botão DXF à função de exportação de malha para DXF
        self.dlg_exporta_malha.button_dxf.clicked.connect(lambda: self.exportar_malha("DXF"))
        
        # Conecta o botão DAE à função de exportação de malha para DAE
        self.dlg_exporta_malha.button_dae.clicked.connect(lambda: self.exportar_malha("DAE"))
        
        # Conecta o botão OBJ à função de exportação de malha para OBJ
        self.dlg_exporta_malha.button_obj.clicked.connect(lambda: self.exportar_malha("OBJ"))
        
        # Conecta o botão STL à função de exportação de malha para STL
        self.dlg_exporta_malha.button_stl.clicked.connect(lambda: self.exportar_malha("STL"))
        
        # Executa o diálogo de exportação de malha 3D
        self.dlg_exporta_malha.exec_()

    def exportar_malha(self, formato):
        """
        Exporta a camada de malha selecionada para o formato especificado (DXF, DAE, OBJ, STL).

        Funções e Ações Desenvolvidas:
        - Verifica a seleção da camada no TreeView.
        - Obtém a camada selecionada do projeto QGIS.
        - Converte a camada de malha para polígonos e pontos.
        - Permite ao usuário escolher o local para salvar o arquivo.
        - Exporta a camada de malha para o formato especificado.
        - Exibe uma mensagem de sucesso ao final da exportação.
        
        :param formato: O formato para o qual a camada de malha será exportada (DXF, DAE, OBJ, STL).
        """
        # Marca o tempo de início da operação
        start_time = time.time()

        # Obtém os índices selecionados no TreeView
        indexes = self.dlg.treeViewListaMalha.selectedIndexes()
        if not indexes:
            # Exibe uma mensagem de erro se nenhuma camada estiver selecionada
            self.mostrar_mensagem("Nenhuma camada selecionada", "Erro")
            return

        # Obtém o nome da camada selecionada
        selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
        
        # Obtém a camada do projeto QGIS pelo nome
        layers = QgsProject.instance().mapLayersByName(selected_layer_name)
        if not layers:
            # Exibe uma mensagem de erro se a camada não for encontrada
            self.mostrar_mensagem("Camada não encontrada", "Erro")
            return

        # Obtém a camada
        layer = layers[0]

        # Verifica se a camada é do tipo QgsMeshLayer
        if not isinstance(layer, QgsMeshLayer):
            # Exibe uma mensagem de erro se a camada não for uma malha
            self.mostrar_mensagem("A camada selecionada não é uma malha", "Erro")
            return

        # Converte a camada de malha para polígonos e extrai os valores de Z dos pontos
        polygon_layer, point_z_values = self.convert_mesh_to_polygons_and_points(layer)
        if not polygon_layer or not point_z_values:
            # Exibe uma mensagem de erro se a conversão falhar
            self.mostrar_mensagem("Falha na conversão da malha para polígonos e pontos", "Erro")
            return

        # Inicializa o caminho do arquivo de salvamento como None
        save_path = None

        # Define o caminho de salvamento com base no formato especificado
        if formato == "DXF":
            save_path = self.escolher_local_para_salvar(layer.name() + ".dxf", "DXF Files (*.dxf)")
            if save_path:
                self.export_to_dxf(polygon_layer, point_z_values, save_path)
        elif formato == "DAE":
            save_path = self.escolher_local_para_salvar(layer.name() + ".dae", "DAE Files (*.dae)")
            if save_path:
                self.export_to_dae(polygon_layer, point_z_values, save_path)
        elif formato == "OBJ":
            save_path = self.escolher_local_para_salvar(layer.name() + ".obj", "OBJ Files (*.obj)")
            if save_path:
                self.export_to_obj(polygon_layer, point_z_values, save_path)
        elif formato == "STL":
            save_path = self.escolher_local_para_salvar(layer.name() + ".stl", "STL Files (*.stl)")
            if save_path:
                self.export_to_stl(polygon_layer, point_z_values, save_path)

        # Se o caminho de salvamento for definido, exibe uma mensagem de sucesso
        if save_path:
            end_time = time.time()  # Marca o tempo de término da operação
            duration = end_time - start_time  # Calcula a duração da operação
            self.mostrar_mensagem(f"Camada exportada para {formato} em {duration:.2f} segundos", "Sucesso", 
                                  caminho_pasta=os.path.dirname(save_path), caminho_arquivo=save_path)
            self.dlg_exporta_malha.close()  # Fecha o diálogo após a exportação

    def convert_mesh_to_polygons_and_points(self, mesh_layer):
        """
        Converte uma camada de malha para polígonos e extrai os pontos com coordenadas Z.

        A função usa algoritmos de processamento nativos do QGIS para exportar faces da malha como polígonos e vértices da malha como pontos.
        Em seguida, adiciona campos ID e Altitude às feições resultantes.

        Funções e Ações Desenvolvidas:
        - Exporta as faces da malha como polígonos.
        - Adiciona um campo ID à camada de polígonos.
        - Converte a camada de polígonos para MultiSurface (MultiPolygonZ).
        - Exporta os vértices da malha como pontos.
        - Adiciona campos ID e Altitude à camada de pontos.
        - Cria um dicionário para mapear as coordenadas dos pontos às suas altitudes.

        :param mesh_layer: Camada de malha a ser convertida (QgsMeshLayer).
        :return: Uma tupla contendo a camada de polígonos MultiSurface (MultiPolygonZ) e um dicionário de valores de altitude dos pontos.
        """
        # Obter o CRS da camada de malha
        crs = mesh_layer.crs()
        
        # Configurar parâmetros para o algoritmo de processamento de polígonos
        params_polygons = {
            'INPUT': mesh_layer,
            'DATASET_GROUPS': [],  # Ajuste conforme necessário
            'DATASET_TIME': {'type': 'static'},  # Configurar o tipo de tempo como estático
            'CRS_OUTPUT': crs.toWkt(),  # Definir o CRS de saída como o mesmo da camada de malha
            'VECTOR_OPTION': 0,  # 0 para Polygons
            'OUTPUT': 'memory:Polygons from TIN Mesh'
        }
        
        # Executar o algoritmo de processamento para polígonos
        result_polygons = processing.run("native:exportmeshfaces", params_polygons)
        
        # Obter a camada de polígonos resultante
        poly_layer = result_polygons['OUTPUT']
        
        # Adicionar campo ID à camada de polígonos
        provider_poly = poly_layer.dataProvider()
        provider_poly.addAttributes([QgsField("ID", QVariant.Int)])
        poly_layer.updateFields()
        
        # Atribuir valores de ID para cada feição
        with edit(poly_layer):
            for i, feature in enumerate(poly_layer.getFeatures()):
                feature.setAttribute("ID", i + 1)  # ID começa em 1
                poly_layer.updateFeature(feature)
        
        # Converter a camada de polígonos para MultiSurface (MultiPolygonZ)
        multi_poly_layer = self.convert_to_multisurface(poly_layer)
        
        # Configurar parâmetros para o algoritmo de processamento de pontos
        params_points = {
            'INPUT': mesh_layer,
            'DATASET_GROUPS': [],  # Ajuste conforme necessário
            'DATASET_TIME': {'type': 'static'},  # Configurar o tipo de tempo como estático
            'CRS_OUTPUT': crs.toWkt(),  # Definir o CRS de saída como o mesmo da camada de malha
            'VECTOR_OPTION': 1,  # 1 para pontos
            'OUTPUT': 'memory:Mesh Vertices'
        }
        
        # Executar o algoritmo de processamento para pontos
        result_points = processing.run("native:exportmeshvertices", params_points)
        
        # Obter a camada de pontos resultante
        point_layer = result_points['OUTPUT']
        
        # Adicionar campo ID e Altimetria à camada de pontos
        provider_point = point_layer.dataProvider()
        provider_point.addAttributes([QgsField("ID", QVariant.Int), QgsField("Altitude", QVariant.Double)])
        point_layer.updateFields()
        
        # Atribuir valores de ID e Altimetria para cada feição
        point_z_values = {}
        with edit(point_layer):
            for i, feature in enumerate(point_layer.getFeatures()):
                geom = feature.geometry()
                if QgsWkbTypes.hasZ(geom.wkbType()):  # Verificar se a geometria tem coordenada Z
                    point = geom.constGet()  # Obter a geometria como QgsPoint
                    feature.setAttribute("ID", i + 1)  # ID começa em 1
                    feature.setAttribute("Altitude", point.z())  # Define a altimetria (z-coordinate)
                    point_z_values[(point.x(), point.y())] = point.z() # Adicionar ao dicionário de valores de Z
                    point_layer.updateFeature(feature) # Atualizar feição
        # Retornar a camada de polígonos e o dicionário de valores de Z
        return multi_poly_layer, point_z_values 

    def convert_to_multisurface(self, poly_layer):
        """
        Converte uma camada de polígonos simples em uma camada de MultiSurface (MultiPolygonZ).

        A função cria uma nova camada de memória que armazena polígonos como MultiPolygonZ, preservando os atributos e IDs das feições originais.

        Funções e Ações Desenvolvidas:
        - Cria uma nova camada de MultiSurface (MultiPolygonZ) com o mesmo CRS da camada de entrada.
        - Adiciona um campo ID à nova camada.
        - Converte cada feição da camada de polígonos simples para MultiPolygon e adiciona à nova camada.
        
        :param poly_layer: Camada de polígonos simples a ser convertida (QgsVectorLayer).
        :return: A nova camada de MultiSurface (MultiPolygonZ) (QgsVectorLayer).
        """
        # Criar uma nova camada de MultiSurface (MultiPolygonZ)
        multi_poly_layer = QgsVectorLayer(f"MultiPolygonZ?crs={poly_layer.crs().authid()}", "MultiSurface Polygons", "memory")
        provider_multi_poly = multi_poly_layer.dataProvider()
        
        # Adicionar campo ID à nova camada
        provider_multi_poly.addAttributes([QgsField("ID", QVariant.Int)])
        multi_poly_layer.updateFields()
        
        # Converter cada feição para MultiPolygon e adicionar à nova camada
        with edit(multi_poly_layer):
            for feature in poly_layer.getFeatures():
                geom = feature.geometry() # Obter a geometria da feição
                if geom.isMultipart():
                    multi_geom = geom # Se a geometria já for multipart, mantê-la como está
                else:
                    multi_geom = QgsGeometry.fromMultiPolygonXY([geom.asPolygon()])  # Converter para MultiPolygon
                new_feature = QgsFeature()  # Criar uma nova feição
                new_feature.setGeometry(multi_geom)  # Definir a geometria da nova feição
                new_feature.setAttributes(feature.attributes())  # Copiar atributos da feição original
                multi_poly_layer.addFeature(new_feature)  # Adicionar a nova feição à camada
        
        return multi_poly_layer  # Retornar a nova camada de MultiSurface (MultiPolygonZ)

    def are_vertices_collinear(self, p1, p2, p3):
        """
        Verifica se três vértices são colineares.

        A função calcula se os pontos p1, p2 e p3 estão alinhados na mesma linha reta. 
        Isso é feito verificando a relação entre as coordenadas dos pontos. 
        Se a relação se mantiver igual, os pontos são considerados colineares.

        :param p1: Primeiro ponto (QgsPoint).
        :param p2: Segundo ponto (QgsPoint).
        :param p3: Terceiro ponto (QgsPoint).
        :return: True se os pontos forem colineares, False caso contrário.
        """
        # Calcular a diferença das coordenadas X e Y dos pontos
        # Verificar se a relação entre as diferenças é igual
        return (p2.x() - p1.x()) * (p3.y() - p1.y()) == (p3.x() - p1.x()) * (p2.y() - p1.y())

    def export_to_dxf(self, multi_poly_layer, point_z_values, output_path):
        """
        Exporta uma camada de MultiPolygonZ para um arquivo DXF, representando polígonos como 3DFACE.

        Funções e Ações Desenvolvidas:
        - Cria um novo documento DXF.
        - Adiciona polígonos da camada MultiPolygonZ ao documento DXF como entidades 3DFACE.
        - Atribui coordenadas Z a partir de um dicionário de valores de pontos.
        - Garante que faces duplicadas não sejam adicionadas.
        - Salva o documento DXF no caminho especificado.
        
        :param multi_poly_layer: Camada de MultiPolygonZ a ser exportada (QgsVectorLayer).
        :param point_z_values: Dicionário com coordenadas X, Y como chaves e coordenadas Z como valores.
        :param output_path: Caminho onde o arquivo DXF será salvo.
        """
        # Criar um novo documento DXF
        doc = ezdxf.new(dxfversion='R2013')  # Versão do DXF
        msp = doc.modelspace()  # Espaço do modelo do DXF

        # Conjunto para rastrear faces já vistas
        faces_seen = set()

        # Inicializar a barra de progresso
        total_faces = sum(len(ring) - 2 for feature in multi_poly_layer.getFeatures() 
                          for geom in (feature.geometry().asMultiPolygon() if feature.geometry().isMultipart() else [feature.geometry().asPolygon()]) 
                          for ring in geom)
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_faces)
        step = 0

        # Adicionar polígonos como 3DFACE
        for feature in multi_poly_layer.getFeatures():
            geom = feature.geometry()  # Obter a geometria da feição
            if geom.isMultipart():
                polygons = geom.asMultiPolygon()  # Obter multipolígonos se multipart
            else:
                polygons = [geom.asPolygon()]  # Caso contrário, obter como polígono
            
            for polygon in polygons:
                for ring in polygon:
                    for i in range(1, len(ring) - 1):
                        p1 = ring[0]  # Primeiro ponto do anel
                        p2 = ring[i]  # Ponto atual do anel
                        p3 = ring[i + 1]  # Próximo ponto do anel
                        if not self.are_vertices_collinear(p1, p2, p3):  # Verificar se os vértices não são colineares
                            face = frozenset([(p1.x(), p1.y()), (p2.x(), p2.y()), (p3.x(), p3.y())])  # Criar um conjunto imutável para a face
                            if face not in faces_seen:  # Verificar se a face já não foi adicionada
                                faces_seen.add(face)  # Adicionar a face ao conjunto
                                # Atribuir Z a partir do dicionário de valores de pontos
                                p1_z = point_z_values.get((p1.x(), p1.y()), 0)  # Obter Z de p1
                                p2_z = point_z_values.get((p2.x(), p2.y()), 0)  # Obter Z de p2
                                p3_z = point_z_values.get((p3.x(), p3.y()), 0)  # Obter Z de p3
                                # Adicionar 3DFACE ao espaço do modelo
                                msp.add_3dface([(p1.x(), p1.y(), p1_z), 
                                                (p2.x(), p2.y(), p2_z), 
                                                (p3.x(), p3.y(), p3_z), 
                                                (p3.x(), p3.y(), p3_z)])  # Adicionar o quarto ponto como p3 para 3DFACE

                                # Atualizar a barra de progresso
                                step += 1
                                progressBar.setValue(step)

        # Salvar o documento DXF
        doc.saveas(output_path)  # Salvar o DXF no caminho especificado

        # Remover a barra de progresso
        self.iface.messageBar().clearWidgets()

    def export_to_obj(self, multi_poly_layer, point_z_values, output_path):
        """
        Exporta uma camada de MultiPolygonZ para um arquivo OBJ.

        Funções e Ações Desenvolvidas:
        - Inicializa a barra de progresso com o número total de faces a serem processadas.
        - Itera sobre as feições da camada de polígonos.
        - Constrói a lista de vértices e faces para o arquivo OBJ.
        - Atualiza a barra de progresso conforme as faces são processadas.
        - Escreve os vértices e faces no arquivo OBJ.
        - Remove a barra de progresso ao final da exportação.

        :param multi_poly_layer: Camada de polígonos a ser exportada (QgsVectorLayer).
        :param point_z_values: Dicionário com coordenadas X, Y como chaves e coordenadas Z como valores.
        :param output_path: Caminho onde o arquivo OBJ será salvo.
        """
        vertices = []  # Lista para armazenar os vértices
        faces = []  # Lista para armazenar as faces

        # Inicializar a barra de progresso
        total_faces = sum(len(ring) - 2 for feature in multi_poly_layer.getFeatures() 
                          for geom in (feature.geometry().asMultiPolygon() if feature.geometry().isMultipart() else [feature.geometry().asPolygon()]) 
                          for ring in geom)
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_faces)
        step = 0  # Inicializa o contador de passos

        # Itera sobre as feições da camada de polígonos
        for feature in multi_poly_layer.getFeatures():
            geom = feature.geometry()  # Obtém a geometria da feição
            if geom.isMultipart():
                polygons = geom.asMultiPolygon()  # Obtém multipolígonos se multipart
            else:
                polygons = [geom.asPolygon()]  # Caso contrário, obtém como polígono

            # Itera sobre os polígonos
            for polygon in polygons:
                face = []  # Inicializa a lista para a face
                # Itera sobre os anéis do polígono
                for ring in polygon:
                    # Itera sobre os pontos do anel
                    for point in ring:
                        if (point.x(), point.y()) in point_z_values:
                            z = point_z_values[(point.x(), point.y())]  # Obtém o valor Z do ponto
                            vertices.append(f"v {point.x()} {point.y()} {z}")  # Adiciona o vértice à lista
                            face.append(len(vertices))  # Adiciona o índice do vértice à face
                    if face:
                        faces.append(f"f {' '.join(map(str, face))}")  # Adiciona a face à lista
                        # Atualizar a barra de progresso
                        step += 1
                        progressBar.setValue(step)  # Atualiza a barra de progresso

        # Abre o arquivo de saída para escrita
        with open(output_path, 'w') as file:
            file.write("\n".join(vertices))  # Escreve os vértices no arquivo
            file.write("\n")  # Adiciona uma linha em branco
            file.write("\n".join(faces))  # Escreve as faces no arquivo

        # Remover a barra de progresso
        self.iface.messageBar().clearWidgets()  # Remove a barra de progresso da interface

    def export_to_stl(self, multi_poly_layer, point_z_values, output_path):
        """
        Exporta uma camada de MultiPolygonZ para um arquivo STL.

        Funções e Ações Desenvolvidas:
        - Inicializa a barra de progresso com o número total de faces a serem processadas.
        - Itera sobre as feições da camada de polígonos.
        - Constrói as faces para o arquivo STL.
        - Atualiza a barra de progresso conforme as faces são processadas.
        - Escreve as faces no arquivo STL.
        - Remove a barra de progresso ao final da exportação.

        :param multi_poly_layer: Camada de polígonos a ser exportada (QgsVectorLayer).
        :param point_z_values: Dicionário com coordenadas X, Y como chaves e coordenadas Z como valores.
        :param output_path: Caminho onde o arquivo STL será salvo.
        """
        with open(output_path, 'w') as file:
            file.write("solid mesh\n")  # Escreve a linha inicial do arquivo STL

            # Inicializar a barra de progresso
            total_faces = sum(len(ring) - 2 for feature in multi_poly_layer.getFeatures() 
                              for geom in (feature.geometry().asMultiPolygon() if feature.geometry().isMultipart() else [feature.geometry().asPolygon()]) 
                              for ring in geom)
            progressBar, progressMessageBar = self.iniciar_progress_bar(total_faces)  # Inicializa a barra de progresso
            step = 0  # Inicializa o contador de passos

            # Itera sobre as feições da camada de polígonos
            for feature in multi_poly_layer.getFeatures():
                geom = feature.geometry()  # Obtém a geometria da feição
                if geom.isMultipart():
                    polygons = geom.asMultiPolygon()  # Obtém multipolígonos se multipart
                else:
                    polygons = [geom.asPolygon()]  # Caso contrário, obtém como polígono

                # Itera sobre os polígonos
                for polygon in polygons:
                    # Itera sobre os anéis do polígono
                    for ring in polygon:
                        # Itera sobre os pontos do anel
                        for i in range(1, len(ring) - 1):
                            p1 = ring[0]
                            p2 = ring[i]
                            p3 = ring[i + 1]

                            # Verifica se as coordenadas dos pontos estão no dicionário de valores Z
                            if (p1.x(), p1.y()) in point_z_values and (p2.x(), p2.y()) in point_z_values and (p3.x(), p3.y()) in point_z_values:
                                z1 = point_z_values[(p1.x(), p1.y())]  # Obtém o valor Z de p1
                                z2 = point_z_values[(p2.x(), p2.y())]  # Obtém o valor Z de p2
                                z3 = point_z_values[(p3.x(), p3.y())]  # Obtém o valor Z de p3

                                # Escreve a face no arquivo STL
                                file.write("facet normal 0 0 0\n")
                                file.write("  outer loop\n")
                                file.write(f"    vertex {p1.x()} {p1.y()} {z1}\n")
                                file.write(f"    vertex {p2.x()} {p2.y()} {z2}\n")
                                file.write(f"    vertex {p3.x()} {p3.y()} {z3}\n")
                                file.write("  endloop\n")
                                file.write("endfacet\n")

                                # Atualizar a barra de progresso
                                step += 1
                                progressBar.setValue(step)  # Atualiza a barra de progresso

            file.write("endsolid mesh\n")  # Escreve a linha final do arquivo STL

        # Remover a barra de progresso
        self.iface.messageBar().clearWidgets()  # Remove a barra de progresso da interface

    def export_to_dae(self, multi_poly_layer, point_z_values, output_path):
        """
        Exporta uma camada de MultiPolygonZ para um arquivo DAE (COLLADA).

        Funções e Ações Desenvolvidas:
        - Cria um documento COLLADA.
        - Adiciona metadados ao documento COLLADA.
        - Cria uma biblioteca de geometrias no documento COLLADA.
        - Obtém valores únicos de Z e cria uma simbologia gradiente.
        - Constrói listas de posições e cores dos vértices.
        - Adiciona fontes de posições e cores à malha COLLADA.
        - Define vértices e triângulos da malha COLLADA.
        - Adiciona a malha a uma cena visual.
        - Salva o documento COLLADA no caminho especificado.

        :param multi_poly_layer: Camada de MultiPolygonZ a ser exportada (QgsVectorLayer).
        :param point_z_values: Dicionário com coordenadas X, Y como chaves e coordenadas Z como valores.
        :param output_path: Caminho onde o arquivo DAE será salvo.
        """

        # Cria o elemento raiz do arquivo COLLADA
        collada = ET.Element("COLLADA", xmlns="http://www.collada.org/2005/11/COLLADASchema", version="1.4.1")
        
        # Cria e preenche o elemento asset com metadados
        asset = ET.SubElement(collada, "asset")
        ET.SubElement(asset, "contributor").append(ET.Element("author"))
        ET.SubElement(asset, "created").text = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        ET.SubElement(asset, "modified").text = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        ET.SubElement(asset, "unit", name="meter", meter="1")
        ET.SubElement(asset, "up_axis").text = "Z_UP"
        
        # Cria o elemento library_geometries e seus elementos filhos para armazenar a geometria
        library_geometries = ET.SubElement(collada, "library_geometries")
        geometry = ET.SubElement(library_geometries, "geometry", id="mesh", name="mesh")
        mesh = ET.SubElement(geometry, "mesh")

        # Obtendo valores únicos e criando simbologia gradiente
        valores_unicos = list(set(point_z_values.values()))
        cores = self.criar_simbologia_gradiente(valores_unicos)

        positions = []  # Lista para armazenar as posições dos vértices
        colors = []  # Lista para armazenar as cores dos vértices
        indices = {}  # Dicionário para armazenar os índices dos vértices

        # Constrói as listas de posições e cores dos vértices
        for (x, y), z in point_z_values.items():
            idx = len(positions) // 3
            positions.extend([x, y, z])
            color = cores[z]
            colors.extend(color)
            indices[(x, y)] = idx

        # Cria e preenche os elementos source para posições e cores dos vértices
        source_positions = ET.SubElement(mesh, "source", id="mesh-positions")
        float_array_positions = ET.SubElement(source_positions, "float_array", id="mesh-positions-array", count=str(len(positions)))
        float_array_positions.text = " ".join(map(str, positions))
        technique_common_positions = ET.SubElement(source_positions, "technique_common")
        accessor_positions = ET.SubElement(technique_common_positions, "accessor", source="#mesh-positions-array", count=str(len(positions)//3), stride="3")
        ET.SubElement(accessor_positions, "param", name="X", type="float")
        ET.SubElement(accessor_positions, "param", name="Y", type="float")
        ET.SubElement(accessor_positions, "param", name="Z", type="float")

        source_colors = ET.SubElement(mesh, "source", id="mesh-colors")
        float_array_colors = ET.SubElement(source_colors, "float_array", id="mesh-colors-array", count=str(len(colors)))
        float_array_colors.text = " ".join(map(str, colors))
        technique_common_colors = ET.SubElement(source_colors, "technique_common")
        accessor_colors = ET.SubElement(technique_common_colors, "accessor", source="#mesh-colors-array", count=str(len(colors)//4), stride="4")
        ET.SubElement(accessor_colors, "param", name="R", type="float")
        ET.SubElement(accessor_colors, "param", name="G", type="float")
        ET.SubElement(accessor_colors, "param", name="B", type="float")
        ET.SubElement(accessor_colors, "param", name="A", type="float")

        # Cria o elemento vertices e associa as posições e cores
        vertices = ET.SubElement(mesh, "vertices", id="mesh-vertices")
        ET.SubElement(vertices, "input", semantic="POSITION", source="#mesh-positions")
        ET.SubElement(vertices, "input", semantic="COLOR", source="#mesh-colors")

        # Cria o elemento triangles para armazenar as faces
        triangles = ET.SubElement(mesh, "triangles", count=str(len(point_z_values) // 3))
        ET.SubElement(triangles, "input", semantic="VERTEX", source="#mesh-vertices", offset="0")
        p = ET.SubElement(triangles, "p")

        p_text = []  # Lista para armazenar os índices das faces

        # Inicializar a barra de progresso
        total_faces = sum(len(ring) - 2 for feature in multi_poly_layer.getFeatures() 
                          for geom in (feature.geometry().asMultiPolygon() if feature.geometry().isMultipart() else [feature.geometry().asPolygon()]) 
                          for ring in geom)
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_faces)  # Inicializa a barra de progresso
        step = 0  # Inicializa o contador de passos

        # Itera sobre as feições da camada de polígonos
        for feature in multi_poly_layer.getFeatures():
            geom = feature.geometry()  # Obtém a geometria da feição
            if geom.isMultipart():
                polygons = geom.asMultiPolygon()  # Obtém multipolígonos se multipart
            else:
                polygons = [geom.asPolygon()]  # Caso contrário, obtém como polígono

            # Itera sobre os polígonos
            for polygon in polygons:
                # Itera sobre os anéis do polígono
                for ring in polygon:
                    # Itera sobre os pontos do anel
                    for i in range(1, len(ring) - 1):
                        p1 = ring[0]
                        p2 = ring[i]
                        p3 = ring[i + 1]
                        # Verifica se os vértices não são colineares
                        if not self.are_vertices_collinear(p1, p2, p3):
                            # Adiciona os índices dos vértices à lista de faces
                            p_text.append(str(indices[(p1.x(), p1.y())]))
                            p_text.append(str(indices[(p2.x(), p2.y())]))
                            p_text.append(str(indices[(p3.x(), p3.y())]))
                            # Atualizar a barra de progresso
                            step += 1
                            progressBar.setValue(step)  # Atualiza a barra de progresso

        p.text = " ".join(p_text)  # Define o texto do elemento p com os índices das faces
        
        # Cria e preenche os elementos library_visual_scenes e visual_scene
        library_visual_scenes = ET.SubElement(collada, "library_visual_scenes")
        visual_scene = ET.SubElement(library_visual_scenes, "visual_scene", id="Scene", name="Scene")
        node = ET.SubElement(visual_scene, "node", id="mesh", name="mesh", type="NODE")
        matrix = ET.SubElement(node, "matrix", sid="transform")
        matrix.text = "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"
        instance_geometry = ET.SubElement(node, "instance_geometry", url="#mesh")
        
        # Cria o elemento scene e associa a visual_scene
        scene = ET.SubElement(collada, "scene")
        ET.SubElement(scene, "instance_visual_scene", url="#Scene")

        # Escreve a estrutura COLLADA no arquivo de saída
        tree = ET.ElementTree(collada)
        tree.write(output_path, encoding="UTF-8", xml_declaration=True)

        # Remover a barra de progresso
        self.iface.messageBar().clearWidgets()  # Remove a barra de progresso da interface

    def criar_simbologia_gradiente(self, valores):
        """
        Cria uma simbologia gradiente de vermelho, laranja, amarelo e verde baseada nos valores fornecidos.

        Funções e Ações Desenvolvidas:
        - Calcula os valores mínimo e máximo da lista fornecida.
        - Interpola cores entre vermelho, laranja, amarelo e verde com base nos valores fornecidos.
        - Cria um dicionário onde as chaves são os valores fornecidos e os valores são listas RGBA.

        :param valores: Lista de valores para os quais a simbologia será aplicada.
        :return: Um dicionário com valores como chave e a cor RGBA correspondente como valor.
        """
        cores = {}  # Dicionário para armazenar as cores
        min_valor = min(valores)  # Calcula o valor mínimo da lista
        max_valor = max(valores)  # Calcula o valor máximo da lista

        # Itera sobre cada valor na lista de valores
        for valor in valores:
            ratio = (valor - min_valor) / (max_valor - min_valor)  # Calcula a razão normalizada do valor

            # Interpola a cor com base na razão
            if ratio < 0.33:
                # Interpolação de vermelho para laranja
                r = 1.0  # Vermelho constante
                g = ratio * 3.0  # Verde cresce de 0 a 1
                b = 0.0  # Azul constante
            elif ratio < 0.66:
                # Interpolação de laranja para amarelo
                r = 1.0 - (ratio - 0.33) * 3.0  # Vermelho decresce de 1 a 0
                g = 1.0  # Verde constante
                b = 0.0  # Azul constante
            else:
                # Interpolação de amarelo para verde
                r = 0.0  # Vermelho constante
                g = 1.0  # Verde constante
                b = (ratio - 0.66) * 3.0  # Azul cresce de 0 a 1
            a = 1.0  # Alfa constante
            cores[valor] = [r, g, b, a]  # Adiciona a cor interpolada ao dicionário

        return cores  # Retorna o dicionário de cores

    def exportar_malha_kml(self):
        """
        Esta função exporta uma camada de malha para um arquivo KML com opções de estilização personalizadas fornecidas pelo usuário.

        Detalhamento:
        1. Abre um diálogo de personalização para o usuário definir opções de estilo (largura da linha, opacidade da linha, cor da linha, opacidade das faces, cor das faces).
        2. Verifica se o usuário confirmou ou cancelou o diálogo. Se cancelado, a função retorna.
        3. Obtém as opções de estilo definidas pelo usuário.
        4. Inicia um cronômetro para medir a duração da exportação.
        5. Obtém a camada de malha selecionada no TreeView.
        6. Verifica se há uma camada selecionada. Se não, exibe uma mensagem de erro e retorna.
        7. Verifica se a camada selecionada é do tipo QgsMeshLayer. Se não, exibe uma mensagem de erro e retorna.
        8. Converte a camada de malha em polígonos e pontos com valores Z.
        9. Verifica se a conversão foi bem-sucedida. Se não, exibe uma mensagem de erro e retorna.
        10. Abre um diálogo para o usuário escolher o local para salvar o arquivo KML.
        11. Exporta os dados para um arquivo KML com as opções de estilo personalizadas.
        12. Calcula a duração da exportação e exibe uma mensagem de sucesso com o tempo gasto.

        Retorno:
        - Nenhum retorno direto. A função realiza a exportação e exibe mensagens de status.

        Exceções tratadas:
        - Nenhuma camada selecionada.
        - Camada não encontrada.
        - Camada selecionada não é uma malha.
        - Falha na conversão da malha para polígonos e pontos.
        """

        # Abre o diálogo de personalização
        style_dialog = KMLStyleDialog()
        if not style_dialog.exec_():
            return  # Se o usuário cancelar, saia da função
        
        # Obtém as opções de estilo definidas pelo usuário
        style_options = style_dialog.get_style_options()

        # Inicia um cronômetro para medir a duração da exportação
        start_time = time.time()

        # Obtém a camada de malha selecionada no TreeView
        indexes = self.dlg.treeViewListaMalha.selectedIndexes()
        if not indexes:
            # Verifica se há uma camada selecionada
            self.mostrar_mensagem("Nenhuma camada selecionada", "Erro")
            return

        # Obtém o nome da camada selecionada
        selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
        layers = QgsProject.instance().mapLayersByName(selected_layer_name)
        if not layers:
            # Verifica se a camada foi encontrada
            self.mostrar_mensagem("Camada não encontrada", "Erro")
            return

        # Verifica se a camada selecionada é do tipo QgsMeshLayer
        layer = layers[0]
        if not isinstance(layer, QgsMeshLayer):
            self.mostrar_mensagem("A camada selecionada não é uma malha", "Erro")
            return

        # Converte a camada de malha em polígonos e pontos com valores Z
        polygon_layer, point_z_values = self.convert_mesh_to_polygons_and_points(layer)
        if not polygon_layer or not point_z_values:
            # Verifica se a conversão foi bem-sucedida
            self.mostrar_mensagem("Falha na conversão da malha para polígonos e pontos", "Erro")
            return

        # Abre um diálogo para o usuário escolher o local para salvar o arquivo KML
        save_path = self.escolher_local_para_salvar(layer.name() + ".kml", "KML Files (*.kml)")
        if save_path:
            # Exporta os dados para um arquivo KML com as opções de estilo personalizadas
            self.export_to_kml(polygon_layer, point_z_values, save_path, style_options)

            # Calcula a duração da exportação
            end_time = time.time()
            duration = end_time - start_time

            # Exibe uma mensagem de sucesso com o tempo gasto
            self.mostrar_mensagem(f"Camada exportada para KML em {duration:.2f} segundos", "Sucesso",
                                  caminho_pasta=os.path.dirname(save_path), caminho_arquivo=save_path)

    def export_to_kml(self, multi_poly_layer, point_z_values, output_path, style_options):
        """
        Esta função exporta uma camada de polígonos múltiplos (multi_poly_layer) e seus valores de pontos Z associados (point_z_values)
        para um arquivo KML, aplicando estilos personalizados definidos pelo usuário.

        Detalhamento:
        1. Converte o sistema de referência de coordenadas (CRS) da camada para WGS84.
        2. Cria a estrutura XML básica do KML.
        3. Adiciona estilos personalizados ao KML, incluindo cor e largura de linha, e cor e opacidade de polígonos.
        4. Calcula o número total de faces para configuração da barra de progresso.
        5. Itera sobre os recursos da camada, convertendo geometrias em polígonos e adicionando-os ao KML.
        6. Atualiza a barra de progresso durante a iteração.
        7. Salva o KML em um arquivo no caminho especificado.
        8. Limpa a barra de mensagens da interface do usuário ao concluir.

        Parâmetros:
        - multi_poly_layer: Camada de polígonos múltiplos a ser exportada.
        - point_z_values: Dicionário contendo valores de Z para os pontos na camada.
        - output_path: Caminho onde o arquivo KML será salvo.
        - style_options: Dicionário contendo as opções de estilo definidas pelo usuário.

        Retorno:
        - Nenhum retorno direto. A função realiza a exportação e exibe uma barra de progresso durante o processo.

        Exceções tratadas:
        - Nenhuma exceção específica tratada nesta função.
        """

        # Converter CRS para WGS84
        crs_src = multi_poly_layer.crs()  # Obtém o CRS da camada original
        crs_dest = QgsCoordinateReferenceSystem(4326)  # Define o CRS de destino como WGS84 (EPSG:4326)
        xform = QgsCoordinateTransform(crs_src, crs_dest, QgsProject.instance())  # Cria a transformação CRS

        # Cria a estrutura XML básica do KML
        kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
        document = ET.SubElement(kml, "Document")

        # Adicionar estilos personalizados
        style = ET.SubElement(document, "Style", id="customStyle")
        linestyle = ET.SubElement(style, "LineStyle")
        line_color = style_options["line_color"]
        ET.SubElement(linestyle, "color").text = f"{style_options['line_opacity']:02x}{line_color.blue():02x}{line_color.green():02x}{line_color.red():02x}"  # Define a cor da linha no formato ABGR
        ET.SubElement(linestyle, "width").text = str(style_options["line_width"])  # Define a largura da linha

        polystyle = ET.SubElement(style, "PolyStyle")
        face_color = style_options["face_color"]
        ET.SubElement(polystyle, "color").text = f"{style_options['face_opacity']:02x}{face_color.blue():02x}{face_color.green():02x}{face_color.red():02x}"  # Define a cor da face no formato ABGR
        ET.SubElement(polystyle, "fill").text = "1"  # Ativa o preenchimento
        ET.SubElement(polystyle, "outline").text = "1"  # Ativa o contorno

        # Calcula o número total de faces para a barra de progresso
        total_faces = sum(len(ring) - 2 for feature in multi_poly_layer.getFeatures()
                          for geom in (feature.geometry().asMultiPolygon() if feature.geometry().isMultipart() else [feature.geometry().asPolygon()])
                          for ring in geom)
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_faces)  # Inicia a barra de progresso
        step = 0  # Inicializa o contador de progresso

        # Itera sobre os recursos da camada
        for feature in multi_poly_layer.getFeatures():
            geom = feature.geometry()
            if geom.isMultipart():
                polygons = geom.asMultiPolygon()  # Converte a geometria para múltiplos polígonos se multipartida
            else:
                polygons = [geom.asPolygon()]  # Converte a geometria para um único polígono

            # Adiciona polígonos ao KML
            for polygon in polygons:
                for ring in polygon:
                    placemark = ET.SubElement(document, "Placemark")
                    ET.SubElement(placemark, "styleUrl").text = "#customStyle"  # Aplica o estilo personalizado
                    polygon_elem = ET.SubElement(placemark, "Polygon")
                    ET.SubElement(polygon_elem, "altitudeMode").text = "absolute"  # Define o modo de altitude como absoluto
                    outer_boundary_is = ET.SubElement(polygon_elem, "outerBoundaryIs")
                    linear_ring = ET.SubElement(outer_boundary_is, "LinearRing")
                    coordinates = ET.SubElement(linear_ring, "coordinates")
                    coord_text = " ".join([f"{xform.transform(point).x()},{xform.transform(point).y()},{point_z_values.get((point.x(), point.y()), 0)}" for point in ring])
                    coordinates.text = coord_text  # Adiciona as coordenadas dos pontos
                    step += 1  # Incrementa o contador de progresso
                    progressBar.setValue(step)  # Atualiza a barra de progresso

        # Salva o KML em um arquivo no caminho especificado
        tree = ET.ElementTree(kml)
        tree.write(output_path, xml_declaration=True, encoding='utf-8')

        # Limpa a barra de mensagens da interface do usuário
        self.iface.messageBar().clearWidgets()

    def exportar_malha_para_dae(self, layer):
        """
        Exporta a malha selecionada para o formato DAE (COLLADA).

        Este método verifica se a camada está no modo de edição e, em caso afirmativo, interrompe a operação,
        pedindo ao usuário que salve ou cancele as edições. Se a camada não estiver no modo de edição,
        o método converte a malha em polígonos e pontos, exporta para um arquivo DAE temporário e retorna
        o caminho do arquivo DAE exportado.

        Parâmetros:
        - layer: A camada selecionada, que pode ser uma QgsVectorLayer ou uma QgsMeshLayer.

        Retorno:
        - dae_file_path (str): O caminho do arquivo DAE exportado, ou None em caso de erro.

        Exceções:
        - QgsProcessingException: Se ocorrer um erro de processamento relacionado ao modo de edição ou
                                  restrições da camada.
        - Exception: Para qualquer outro erro inesperado.
        """
        try:
            # Verifica se a camada é uma camada vetorial (QgsVectorLayer) e está no modo de edição
            if isinstance(layer, QgsVectorLayer) and layer.isEditable():
                self.mostrar_mensagem(f"A camada '{layer.name()}' está no modo de edição. Por favor, salve ou cancele as edições antes de exportar.", "Erro")
                return None

            # Definir um caminho temporário para salvar o arquivo DAE
            temp_dir = os.path.join(os.path.expanduser("~"), "Temp")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            dae_file_path = os.path.join(temp_dir, layer.name() + ".dae")

            # Chamar a função de exportação para DAE
            polygon_layer, point_z_values = self.convert_mesh_to_polygons_and_points(layer)
            if not polygon_layer or not point_z_values:
                self.mostrar_mensagem("Falha na conversão da malha para polígonos e pontos", "Erro")
                return None

            # Exportar a malha para o arquivo DAE
            self.export_to_dae(polygon_layer, point_z_values, dae_file_path)
            return dae_file_path

        except QgsProcessingException as pe:
            # Caso o erro seja relacionado ao processamento, mostrar uma mensagem específica
            self.mostrar_mensagem(f"Erro ao exportar a malha para DAE: {str(pe)}. Verifique o modo de edição ou as restrições da camada.", "Erro")
            return None

        except Exception as e:
            # Para outros tipos de erro, mostrar a mensagem genérica
            self.mostrar_mensagem(f"Erro inesperado: {str(e)}", "Erro")
            return None # Retorna None em caso de erro inesperado

    def abrir_visualizador_malha_3d(self):
        """
        Abre o visualizador 3D para a malha selecionada.

        Esta função obtém a camada selecionada na interface de usuário, verifica se ela é uma camada de malha (QgsMeshLayer),
        exporta a malha para o formato DAE e, em seguida, abre o visualizador 3D com o arquivo DAE exportado.

        Parâmetros:
        - Nenhum parâmetro explícito. A função depende do estado interno do objeto, como a seleção de camadas no QGIS.

        Retorno:
        - Nenhum retorno explícito. Abre o visualizador 3D ou exibe mensagens de erro em caso de falhas.

        Exceções:
        - Exibe mensagens de erro se a camada não for encontrada, não for uma malha, ou se ocorrer um erro na exportação.
        """
        # Obter a camada selecionada na treeView
        indexes = self.dlg.treeViewListaMalha.selectedIndexes()  # Obtém os índices selecionados na treeView
        if not indexes:  # Se nenhum índice for selecionado, mostra uma mensagem de erro
            self.mostrar_mensagem("Nenhuma camada selecionada", "Erro")
            return  # Interrompe a execução da função

        # Obter o nome da camada selecionada no modelo treeViewModel
        selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
        
        # Procurar a camada pelo nome no projeto QGIS
        layers = QgsProject.instance().mapLayersByName(selected_layer_name)
        if not layers:  # Se nenhuma camada com esse nome for encontrada, mostra uma mensagem de erro
            self.mostrar_mensagem("Camada não encontrada", "Erro")
            return  # Interrompe a execução da função

        # Obter a primeira camada encontrada
        layer = layers[0]  # Pega a primeira camada encontrada com o nome selecionado
        
        # Verificar se a camada é uma camada de malha (QgsMeshLayer)
        if not isinstance(layer, QgsMeshLayer):  # Se a camada não for do tipo QgsMeshLayer, mostra uma mensagem de erro
            self.mostrar_mensagem("A camada selecionada não é uma malha", "Erro")
            return  # Interrompe a execução da função

        # Exportar a malha para DAE
        dae_file_path = self.exportar_malha_para_dae(layer)  # Chama a função para exportar a malha para um arquivo DAE
        if dae_file_path:  # Se a exportação for bem-sucedida (dae_file_path não é None)
            # Abrir o visualizador de DAE em 3D
            visualizador = VisualizadorDAE3D(dae_file_path, self.dlg, self)  # Cria uma instância do visualizador DAE 3D
            visualizador.show()  # Exibe a janela do visualizador 3D

class VisualizadorDAE3D(QDialog):
    def __init__(self, dae_file_path, parent=None, ui_manager=None):
        """
        Inicializa o visualizador 3D de malhas em formato DAE (COLLADA).

        Esta função configura a janela de visualização 3D, incluindo a interface lateral com
        várias opções de configuração, como inverter o gradiente, salvar a visualização em PNG, e alternar a exibição dos eixos XYZ e das linhas dos vértices.

        Parâmetros:
        - dae_file_path (str): O caminho do arquivo DAE que será visualizado.
        - parent (QWidget): O widget pai da janela de visualização (opcional).
        - ui_manager (UiManagerM): Instância da classe UiManagerM para acessar métodos auxiliares, como salvar arquivos e exibir mensagens.

        Atributos:
        - view (GLViewWidget): O widget principal que renderiza a malha 3D.
        - mesh_data (GLMeshItem): Os dados da malha carregados a partir do arquivo DAE.
        - mesh_item (GLMeshItem): O item da malha renderizada.
        - checkbox_xyz (QCheckBox): Checkbox para exibir ou ocultar os eixos XYZ.
        """
        super().__init__(parent)
        self.dae_file_path = dae_file_path # Caminho do arquivo DAE a ser carregado
        self.ui_manager = ui_manager  # Instância de UiManagerM
        self.setWindowTitle("Visualização 3D da Malha")

        # Definir a geometria da janela (largura=1400, altura=900)
        self.setGeometry(100, 100, 1400, 900)

        # Ativar botões de minimizar e maximizar
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

        # Definir a janela como não modal
        self.setWindowModality(Qt.NonModal)

        # Layout principal
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # Visualizador 3D
        self.view = gl.GLViewWidget()  # Inicializa o widget de visualização 3D
        self.view.setCameraPosition(distance=200)  # Define a distância inicial da câmera
        self.view.opts['antialias'] = True  # Ativar suavização para melhor renderização
        main_layout.addWidget(self.view)  # Adicionar o visualizador 3D ao layout principal

        # Frame lateral para botões
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        frame.setFrameShadow(QFrame.Raised)
        frame.setFixedWidth(200)
        
        # Layout para os widgets dentro do frame
        side_layout = QVBoxLayout()
        frame.setLayout(side_layout)

        # Fixar o texto "Configurações:" no topo
        label = QLabel("Configurações:")
        label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        side_layout.addWidget(label, alignment=Qt.AlignTop)

        # Adicionar um espaçador vertical para garantir que o texto e o slider fiquem juntos
        vertical_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        side_layout.addItem(vertical_spacer)

        # Botão para salvar a visualização como PNG
        self.botao_salvar_png = QPushButton("Salvar como PNG")
        self.botao_salvar_png.clicked.connect(self.salvar_visualizacao_como_png)
        side_layout.addWidget(self.botao_salvar_png)

        # Linha Horizontal (acima do texto "Número de faixas de cores:")
        hline_above_slider = QFrame()
        hline_above_slider.setFrameShape(QFrame.HLine)
        hline_above_slider.setFrameShadow(QFrame.Sunken)
        side_layout.addWidget(hline_above_slider)

        # Criar o layout em grade (grid layout)
        grid_layout = QGridLayout()

        # Adicionar o texto "Número de faixas de cores" na primeira linha, coluna 0
        label_faixas = QLabel("Número de faixas de cores:")
        grid_layout.addWidget(label_faixas, 0, 0)

         # Adicionar um QSpinBox para selecionar o número de faixas de cores
        self.spinbox_faixas = QSpinBox()
        self.spinbox_faixas.setMinimum(1)
        self.spinbox_faixas.setMaximum(10)
        self.spinbox_faixas.setValue(10)  # Valor padrão
        self.spinbox_faixas.valueChanged.connect(self.atualizar_malha_com_faixas)
        grid_layout.addWidget(self.spinbox_faixas, 1, 0)

        # Crie um novo layout horizontal para os botões e o slider
        h_layout = QHBoxLayout()

        # Botão para diminuir o valor
        self.button_decrease = QPushButton()
        self.button_decrease.setIcon(self.style().standardIcon(QStyle.SP_ArrowLeft))
        self.button_decrease.setFixedSize(QSize(20, 20))
        self.button_decrease.clicked.connect(self.decrease_slider_value)
        h_layout.addWidget(self.button_decrease)

        # Adicione o slider ao layout horizontal
        self.slider_faixas = QSlider(Qt.Horizontal)
        self.slider_faixas.setMinimum(1)
        self.slider_faixas.setMaximum(10)
        self.slider_faixas.setValue(10)
        self.slider_faixas.setTickPosition(QSlider.TicksAbove)
        self.slider_faixas.setTickInterval(1)
        self.slider_faixas.valueChanged.connect(self.atualizar_malha_com_faixas)
        h_layout.addWidget(self.slider_faixas)

        # Botão para aumentar o valor
        self.button_increase = QPushButton()
        self.button_increase.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self.button_increase.setFixedSize(QSize(20, 20))
        self.button_increase.clicked.connect(self.increase_slider_value)
        h_layout.addWidget(self.button_increase)

        # Adicione o layout horizontal ao grid_layout
        grid_layout.addLayout(h_layout, 1, 0)

        # Adicionar o layout em grid ao layout principal (side_layout)
        side_layout.addLayout(grid_layout)

        # CheckBox para inverter as cores do gradiente
        self.checkbox_inverter_cores = QCheckBox("Inverter Cores do Gradiente")
        self.checkbox_inverter_cores.setChecked(False)  # Desativado por padrão
        self.checkbox_inverter_cores.stateChanged.connect(self.atualizar_malha_com_faixas)
        side_layout.addWidget(self.checkbox_inverter_cores)

        # Linha Horizontal (abaixo do slider)
        hline_below_slider = QFrame()
        hline_below_slider.setFrameShape(QFrame.HLine)
        hline_below_slider.setFrameShadow(QFrame.Sunken)
        side_layout.addWidget(hline_below_slider)

        # RadioButton para mudar a cor do fundo
        self.radio_white = QRadioButton("Fundo Branco")
        self.radio_black = QRadioButton("Fundo Preto")

        # Definir o fundo branco como padrão
        self.radio_white.setChecked(True)
        self.view.setBackgroundColor('w')

        # Conectar os RadioButtons às funções para alterar a cor do fundo
        self.radio_white.toggled.connect(self.mudar_fundo)
        self.radio_black.toggled.connect(self.mudar_fundo)

        # Adicionar RadioButtons ao layout do frame
        side_layout.addWidget(self.radio_white)
        side_layout.addWidget(self.radio_black)

        # **Adicionar o CheckBox para exibir/ocultar as linhas dos vértices**
        self.checkbox_edges = QCheckBox("Exibir Linhas dos Vértices")
        self.checkbox_edges.setChecked(True)  # Exibir as linhas por padrão
        self.checkbox_edges.stateChanged.connect(self.alternar_linhas_vertices)
        side_layout.addWidget(self.checkbox_edges)

        # Adicionando o checkbox para exibir ou ocultar eixos XYZ
        self.checkbox_xyz = QCheckBox("Exibir Eixos XYZ")
        self.checkbox_xyz.setChecked(True)  # Exibir os eixos por padrão
        self.checkbox_xyz.stateChanged.connect(self.alternar_eixos_xyz)
        side_layout.addWidget(self.checkbox_xyz)

        # Adiciona o frame ao layout principal
        main_layout.addWidget(frame)

        # Variável para armazenar os dados da malha
        self.mesh_data = None  # Inicializa a variável mesh_data como None
        self.mesh_item = None  # Inicializa a variável mesh_item como None

        # Carregar e desenhar o arquivo DAE
        self.load_and_draw_dae() # Chama a função para carregar e desenhar o arquivo DAE

        # Desenhar os eixos XYZ diretamente na cena
        self.adicionar_eixos_xyz() # Adiciona os eixos XYZ à cena 3D

    def salvar_visualizacao_como_png(self):
        """
        Salva a visualização 3D atual como uma imagem PNG.

        Esta função usa o método escolher_local_para_salvar de UiManagerM para permitir que o
        usuário escolha o local e o nome do arquivo PNG. Depois de capturar a imagem da área 3D
        (GLViewWidget), ela é salva no local escolhido. Se o processo for concluído com sucesso, uma
        mensagem de sucesso é exibida; caso contrário, uma mensagem de erro é exibida.

        Parâmetros:
        - Nenhum parâmetro explícito. A função usa o estado interno do objeto para capturar e salvar a visualização.

        Retorno:
        - Nenhum retorno explícito. Salva um arquivo PNG no local escolhido ou exibe mensagens de erro em caso de falha.
        """
        # Usar a função escolher_local_para_salvar da classe UiManagerM para obter o caminho do arquivo
        file_path = self.ui_manager.escolher_local_para_salvar("visualizacao_malha", "PNG Files (*.png)")
        
        if not file_path:
            # Se o usuário cancelar a operação, mostrar uma mensagem de erro e sair
            self.ui_manager.mostrar_mensagem("Operação cancelada pelo usuário.", "Erro")
            return  # Se não houver caminho, interrompe a função

        # Capturar a visualização da área 3D e salvar como PNG
        try:
            # Capturar a imagem da visualização 3D (tamanho atual da janela)
            img = self.view.grabFramebuffer()  # Captura o conteúdo da área 3D como uma imagem
            
            # Salvar a imagem no caminho escolhido com formato PNG
            img.save(file_path, 'PNG')

            # Mostrar uma mensagem de sucesso usando a função mostrar_mensagem de UiManagerM
            self.ui_manager.mostrar_mensagem(
                f"Visualização salva com sucesso em {file_path}", "Sucesso", 
                caminho_pasta=os.path.dirname(file_path), caminho_arquivo=file_path
            )
        except Exception as e:
            # Se houver um erro, mostrar a mensagem de erro
            self.ui_manager.mostrar_mensagem(f"Erro ao salvar a visualização: {str(e)}", "Erro")

    def remover_eixos_xyz(self):
        """
        Remove os eixos XYZ da visualização 3D.

        Esta função verifica se os eixos XYZ foram previamente adicionados à visualização. 
        Se os eixos estiverem presentes, eles são removidos da cena 3D, e a variável que os armazena 
        (`self.eixos_xyz`) é redefinida para None.

        Parâmetros:
        - Nenhum parâmetro explícito. A função opera sobre o estado atual da visualização 3D.

        Retorno:
        - Nenhum retorno explícito. Remove os eixos da visualização ou não faz nada se os eixos não existirem.
        """
        # Verifica se os eixos XYZ foram previamente adicionados (self.eixos_xyz não é None)
        if self.eixos_xyz:
            # Itera sobre os eixos (X, Y e Z) armazenados e remove cada um da visualização
            for eixo in self.eixos_xyz:
                self.view.removeItem(eixo)  # Remove o item da visualização 3D
            
            # Após remover, redefine a variável eixos_xyz para None, indicando que não há mais eixos na visualização
            self.eixos_xyz = None

    def alternar_eixos_xyz(self, state):
        """
        Alterna a exibição dos eixos XYZ na visualização 3D com base no estado de um checkbox.

        Esta função é usada para:
        - Controlar a adição ou remoção dos eixos XYZ da cena 3D.
        - Se o checkbox estiver marcado (`Qt.Checked`):
          - Os eixos XYZ são adicionados à visualização.
        - Se o checkbox estiver desmarcado (qualquer outro estado):
          - Os eixos XYZ são removidos da visualização.

        Parâmetros:
        - state (int): O estado do checkbox, que pode ser `Qt.Checked` (marcado) ou `Qt.Unchecked` (desmarcado).

        Retorno:
        - Nenhum retorno explícito. Adiciona ou remove os eixos da visualização com base no estado do checkbox.
        """
        # Verifica o estado do checkbox para adicionar ou remover os eixos XYZ
        if state == Qt.Checked:
            # Se o checkbox estiver marcado, adiciona os eixos XYZ à visualização
            self.adicionar_eixos_xyz()
        else:
            # Se o checkbox estiver desmarcado, remove os eixos XYZ da visualização
            self.remover_eixos_xyz()

    def adicionar_eixos_xyz(self):
        """
        Adiciona os eixos XYZ à visualização 3D.

        Esta função cria três linhas coloridas que representam os eixos X, Y e Z, e as adiciona
        à cena 3D para ajudar a orientar o usuário sobre a posição e a escala dos objetos renderizados.

        Ações realizadas:
        - Define as cores para cada eixo:
          - Vermelho para o eixo X.
          - Verde para o eixo Y.
          - Azul para o eixo Z.
        - Define o comprimento de cada eixo.
        - Cria as linhas que representam cada eixo com as cores e comprimentos definidos.
        - Adiciona os eixos à visualização 3D.
        - Armazena os objetos de linha (eixos) em uma lista para possível remoção futura.

        Parâmetros:
        - Nenhum parâmetro explícito. A função opera sobre o estado atual da visualização 3D.

        Retorno:
        - Nenhum retorno explícito. Os eixos são adicionados diretamente à cena 3D.
        """
        # Definindo as cores para cada eixo
        cor_x = (1, 0, 0, 1)  # Vermelho para o eixo X
        cor_y = (0, 1, 0, 1)  # Verde para o eixo Y
        cor_z = (0, 0, 1, 1)  # Azul para o eixo Z

        # Comprimento dos eixos
        tamanho_eixo = 120  # Ajuste conforme necessário para definir o comprimento dos eixos

        # Coordenadas para o eixo X
        eixo_x = np.array([[0, 0, 0], [tamanho_eixo, 0, 0]])  # Linha do eixo X, do ponto (0, 0, 0) até (120, 0, 0)
        # Criando o item para o eixo X
        linha_x = GLLinePlotItem(pos=eixo_x, color=cor_x, width=2, antialias=True)  # Linha do eixo X com cor e suavização

        # Coordenadas para o eixo Y
        eixo_y = np.array([[0, 0, 0], [0, tamanho_eixo, 0]])  # Linha do eixo Y, do ponto (0, 0, 0) até (0, 120, 0)
        # Criando o item para o eixo Y
        linha_y = GLLinePlotItem(pos=eixo_y, color=cor_y, width=2, antialias=True)  # Linha do eixo Y com cor e suavização

        # Coordenadas para o eixo Z
        eixo_z = np.array([[0, 0, 0], [0, 0, tamanho_eixo]])  # Linha do eixo Z, do ponto (0, 0, 0) até (0, 0, 120)
        # Criando o item para o eixo Z
        linha_z = GLLinePlotItem(pos=eixo_z, color=cor_z, width=2, antialias=True)  # Linha do eixo Z com cor e suavização

        # Armazena os eixos em uma lista para controle posterior (remover ou alterar)
        self.eixos_xyz = [linha_x, linha_y, linha_z]

        # Adicionando as linhas dos eixos à visualização 3D
        self.view.addItem(linha_x)  # Adiciona o eixo X à visualização
        self.view.addItem(linha_y)  # Adiciona o eixo Y à visualização
        self.view.addItem(linha_z)  # Adiciona o eixo Z à visualização

    def decrease_slider_value(self):
        """
        Diminui o valor atual do slider de faixas de cores em 1 unidade.

        Esta função verifica o valor atual do slider (`self.slider_faixas`). Se o valor atual for maior
        que o valor mínimo permitido pelo slider, ele é diminuído em 1 unidade.

        Ações realizadas:
        - Verifica o valor atual do slider.
        - Compara o valor atual com o valor mínimo permitido.
        - Se o valor atual for maior que o mínimo, diminui o valor do slider em 1 unidade.

        Parâmetros:
        - Nenhum parâmetro explícito. A função opera sobre o estado atual do slider de faixas de cores.

        Retorno:
        - Nenhum retorno explícito. Atualiza o valor do slider diretamente.
        """
        # Obtém o valor atual do slider de faixas de cores
        current_value = self.slider_faixas.value()
        
        # Verifica se o valor atual é maior que o valor mínimo permitido pelo slider
        if current_value > self.slider_faixas.minimum():
            # Se for maior, diminui o valor do slider em 1 unidade
            self.slider_faixas.setValue(current_value - 1)

    def increase_slider_value(self):
        """
        Aumenta o valor atual do slider de faixas de cores em 1 unidade.

        Esta função verifica o valor atual do slider (`self.slider_faixas`). Se o valor atual for menor
        que o valor máximo permitido pelo slider, ele é aumentado em 1 unidade.

        Ações realizadas:
        - Verifica o valor atual do slider.
        - Compara o valor atual com o valor máximo permitido.
        - Se o valor atual for menor que o máximo, aumenta o valor do slider em 1 unidade.

        Parâmetros:
        - Nenhum parâmetro explícito. A função opera sobre o estado atual do slider de faixas de cores.

        Retorno:
        - Nenhum retorno explícito. Atualiza o valor do slider diretamente.
        """
        # Obtém o valor atual do slider de faixas de cores
        current_value = self.slider_faixas.value()

        # Verifica se o valor atual é menor que o valor máximo permitido pelo slider
        if current_value < self.slider_faixas.maximum():
            # Se for menor, aumenta o valor do slider em 1 unidade
            self.slider_faixas.setValue(current_value + 1)

    def mudar_fundo(self):
        """
        Altera a cor de fundo da visualização 3D com base no RadioButton selecionado.

        Esta função verifica qual dos RadioButtons está selecionado: se o fundo branco ou o fundo preto.
        Dependendo da seleção, a função altera a cor de fundo da visualização 3D para branco ou preto.

        Ações realizadas:
        - Verifica qual RadioButton está marcado:
          - Se o RadioButton "Fundo Branco" estiver marcado, o fundo é definido como branco.
          - Se o RadioButton "Fundo Preto" estiver marcado, o fundo é definido como preto.

        Parâmetros:
        - Nenhum parâmetro explícito. A função opera sobre o estado dos RadioButtons e da visualização 3D.

        Retorno:
        - Nenhum retorno explícito. Atualiza a cor de fundo da visualização diretamente.
        """
        # Verifica se o RadioButton para fundo branco está selecionado
        if self.radio_white.isChecked():
            # Define a cor de fundo da visualização como branca
            self.view.setBackgroundColor('w')
        # Verifica se o RadioButton para fundo preto está selecionado
        elif self.radio_black.isChecked():
            # Define a cor de fundo da visualização como preta
            self.view.setBackgroundColor('k')

    def enquadrar_malha(self, vertices_np):
        """
        Ajusta a posição da câmera e centraliza a visualização da malha 3D com base nas coordenadas dos vértices.

        Esta função calcula os limites (bounding box) da malha 3D a partir das coordenadas dos vértices fornecidos.
        Com esses limites, a função ajusta a distância da câmera e centraliza a visualização da malha para garantir
        que toda a malha esteja visível no visualizador.

        Ações realizadas:
        - Calcula os limites mínimos e máximos da malha (bounding box).
        - Ajusta a distância da câmera para que toda a malha seja visível.
        - Centraliza a visualização da malha no centro dos limites calculados.

        Parâmetros:
        - vertices_np (numpy.ndarray): Um array NumPy contendo as coordenadas dos vértices da malha (Nx3),
          onde N é o número de vértices e 3 são as coordenadas X, Y e Z de cada vértice.

        Retorno:
        - Nenhum retorno explícito. A câmera é ajustada diretamente para enquadrar a malha.
        """
        # Calcular os limites mínimos e máximos da malha (bounding box)
        min_bounds = vertices_np.min(axis=0)  # Limites mínimos para X, Y, Z
        max_bounds = vertices_np.max(axis=0)  # Limites máximos para X, Y, Z
        size = max_bounds - min_bounds  # Calcula o tamanho da malha ao subtrair os limites mínimos dos máximos

        # Ajustar a distância da câmera para garantir que toda a malha esteja visível
        # A distância da câmera é ajustada com base na norma do tamanho da malha, multiplicada por um fator (3)
        self.view.opts['distance'] = np.linalg.norm(size) * 3

        # Centralizar a visualização da malha
        # O ponto central da visualização é ajustado para o centro da bounding box da malha
        self.view.opts['center'] = pg.Vector(size[0] / 2, size[1] / 2, size[2] / 2)

    def alternar_linhas_vertices(self):
        """
        Atualiza a exibição das linhas dos vértices (arestas) da malha 3D.

        Esta função verifica se os dados da malha (mesh_data) estão disponíveis. Se estiverem, a função remove
        a malha atual da visualização e a recria com a opção de exibir ou ocultar as linhas das arestas com base no estado do checkbox.
        A exibição das arestas é controlada pelo checkbox `self.checkbox_edges`.

        Ações realizadas:
        - Verifica se a malha (mesh_data) está carregada.
        - Remove o item da malha atual da visualização.
        - Recria o item da malha com a opção de desenhar ou não as arestas, dependendo do estado do checkbox.
        - Adiciona novamente o item da malha à visualização.
        - Atualiza a visualização para refletir as mudanças.

        Parâmetros:
        - Nenhum parâmetro explícito. A função opera sobre o estado atual da visualização 3D e o checkbox.

        Retorno:
        - Nenhum retorno explícito. Atualiza a visualização 3D diretamente.
        """
        # Verifica se os dados da malha estão carregados
        if self.mesh_data is not None:
            # Remove o item da malha atual da visualização
            self.view.removeItem(self.mesh_item)  # Remove o item da malha atual

            # Recria o item da malha com a opção de desenhar as arestas (drawEdges) controlada pelo checkbox
            self.mesh_item = gl.GLMeshItem(
                meshdata=self.mesh_data,  # Dados da malha
                smooth=True,  # Habilita suavização
                drawEdges=self.checkbox_edges.isChecked(),  # Controla a exibição das arestas com base no checkbox
                edgeColor=(0.5, 0.5, 0.5, 0.5),  # Define a cor das arestas (transparência incluída)
                shader=None  # Nenhum shader é aplicado
            )

            # Remove qualquer shader aplicado para garantir que o padrão seja usado
            self.mesh_item.setShader(None)

            # Ajusta o tamanho da malha
            self.mesh_item.scale(10, 10, 10)

            # Adiciona o item da malha de volta à visualização
            self.view.addItem(self.mesh_item)

            # Atualiza a visualização para aplicar as mudanças
            self.view.update()

    def load_and_draw_dae(self):
        """
        Carrega e desenha um arquivo DAE (COLLADA) na visualização 3D.

        Esta função lê um arquivo DAE, extrai os vértices e faces da malha, aplica um gradiente de cores baseado
        nos valores Z dos vértices, e renderiza a malha 3D na visualização. Além disso, ela centraliza e ajusta a
        visualização para garantir que a malha seja exibida corretamente.

        Ações realizadas:
        - Carrega o arquivo DAE e extrai os vértices e faces da malha.
        - Constrói um array de vértices e faces para uso na visualização.
        - Aplica um gradiente de cores baseado nos valores Z dos vértices, distribuídos em faixas.
        - Cria e exibe a malha 3D na visualização.
        - Ajusta a visualização centralizando e enquadrando a malha.

        Parâmetros:
        - Nenhum parâmetro explícito. A função usa o arquivo DAE carregado e o estado atual dos widgets.

        Retorno:
        - Nenhum retorno explícito. Atualiza a visualização 3D com a malha carregada e renderizada.
        """
        # Inicializa as listas para armazenar os vértices e faces
        vertices = []  # Lista para armazenar os vértices da malha
        faces = []  # Lista para armazenar as faces da malha

        try:
            # Carregar o arquivo DAE usando o módulo ElementTree
            tree = ET.parse(self.dae_file_path)  # Carrega o arquivo DAE
            root = tree.getroot()  # Obtém a raiz do XML

            # Definir o namespace padrão do COLLADA para procurar pelos elementos
            namespace = "{http://www.collada.org/2005/11/COLLADASchema}"

            # Extrair os vértices do arquivo DAE
            for source in root.findall(f".//{namespace}float_array"):
                if 'positions' in source.attrib['id']:
                    raw_vertices = list(map(float, source.text.split()))  # Converte os vértices para floats
                    for i in range(0, len(raw_vertices), 3):
                        # Adiciona os vértices na lista em grupos de 3 (X, Y, Z)
                        vertices.append([raw_vertices[i], raw_vertices[i + 1], raw_vertices[i + 2]])
                    break  # Sai do loop após encontrar os vértices

            # Extrair as faces (triângulos) do arquivo DAE
            for p in root.findall(f".//{namespace}p"):
                raw_faces = list(map(int, p.text.split()))  # Converte os índices das faces para inteiros
                for i in range(0, len(raw_faces), 3):
                    # Adiciona as faces na lista em grupos de 3 (definindo os triângulos)
                    faces.append([raw_faces[i], raw_faces[i + 1], raw_faces[i + 2]])

            # Verifica se os vértices ou faces estão vazios
            if not vertices or not faces:
                self.ui_manager.mostrar_mensagem("Nenhuma geometria encontrada no arquivo DAE.", "Erro")
                return  # Sai da função se não houver geometria

            # Converte as listas de vértices e faces para arrays NumPy
            vertices_np = np.array(vertices)  # Array de vértices
            faces_np = np.array(faces)  # Array de faces

            # Centralizar os vértices ao redor da origem (0, 0, 0)
            center = vertices_np.mean(axis=0)  # Calcula o centro da malha
            vertices_np -= center  # Desloca os vértices para que a malha seja centralizada

            # Extrair os valores Z dos vértices para criar o gradiente de cores
            z_values = vertices_np[:, 2]  # Valores Z para determinar as cores

            # Gerar as cores com o número de faixas selecionado no slider
            num_faixas = self.slider_faixas.value()  # Obtém o número de faixas de cores do slider
            colors = self.criar_simbologia_gradiente_discreta(z_values, num_faixas)  # Cria o gradiente de cores

            # Armazenar os dados da malha usando MeshData
            self.mesh_data = gl.MeshData(vertexes=vertices_np, faces=faces_np, vertexColors=colors)

            # Criar o GLMeshItem para exibir a malha 3D com as arestas controladas pelo checkbox
            self.mesh_item = gl.GLMeshItem(
                meshdata=self.mesh_data,  # Dados da malha
                smooth=True,  # Habilita suavização
                drawEdges=self.checkbox_edges.isChecked(),  # Controla a exibição das arestas
                edgeColor=(0.5, 0.5, 0.5, 0.5),  # Cor das arestas (com transparência)
                shader=None  # Nenhum shader específico aplicado
            )
            self.mesh_item.setShader(None)  # Remove qualquer shader
            self.mesh_item.scale(10, 10, 10)  # Ajusta a escala da malha
            self.view.addItem(self.mesh_item)  # Adiciona a malha à visualização 3D

            # Define o fundo da visualização como branco
            self.view.setBackgroundColor('w')

            # Centraliza e enquadra a malha na visualização
            self.enquadrar_malha(vertices_np)

            # Exibe uma mensagem de sucesso após a renderização
            self.ui_manager.mostrar_mensagem("Renderização da malha DAE concluída com sucesso.", "Sucesso")

        except Exception as e:
            # Se houver um erro durante o carregamento ou processamento do DAE, exibe uma mensagem de erro
            self.ui_manager.mostrar_mensagem(f"Erro ao carregar ou processar o arquivo DAE: {str(e)}", "Erro")

    def criar_simbologia_gradiente_discreta(self, valores, num_faixas=5, inverter_gradiente=False):
        """
        Cria um gradiente discreto de cores baseado nos valores fornecidos para os vértices da malha.

        Esta função gera um gradiente de cores aplicável aos vértices da malha, com base nos valores Z fornecidos
        (ou outra propriedade dos vértices). As cores são distribuídas em faixas discretas e aplicadas aos vértices
        de acordo com o número de faixas selecionado. As cores podem ser invertidas se o parâmetro inverter_gradiente
        for verdadeiro.

        Ações realizadas:
        - Calcula os limites mínimos e máximos dos valores fornecidos.
        - Divide os valores em faixas discretas com base no número de faixas selecionado.
        - Aplica cores pré-definidas às faixas.
        - Opcionalmente, inverte o gradiente de cores se o checkbox de inversão estiver marcado.
        - Aplica a cor correspondente a cada vértice com base na faixa em que o valor se encontra.

        Parâmetros:
        - valores (numpy.ndarray): Um array contendo os valores (geralmente Z) dos vértices da malha.
        - num_faixas (int): O número de faixas discretas de cores a serem aplicadas (padrão: 5).
        - inverter_gradiente (bool): Se True, inverte o gradiente de cores (padrão: False).

        Retorno:
        - cores (numpy.ndarray): Um array contendo as cores RGBA para cada vértice, aplicadas com base no gradiente.
        """
        # Calcula os valores mínimos e máximos dos vértices (normalmente os valores Z)
        min_valor = min(valores)  # Valor mínimo no array de valores
        max_valor = max(valores)  # Valor máximo no array de valores

        # Dividindo os valores em 'num_faixas' faixas discretas
        # Gera um array com os limites das faixas, do valor mínimo ao máximo
        faixas = np.linspace(min_valor, max_valor, num_faixas + 1)

        # Cores pré-definidas para as faixas
        cores_faixa_predefinidas = [
            (1.0, 0.0, 0.0, 1.0),  # Vermelho
            (1.0, 0.3, 0.0, 1.0),  # Vermelho-laranja
            (1.0, 0.5, 0.0, 1.0),  # Laranja
            (1.0, 0.75, 0.0, 1.0), # Amarelo-alaranjado
            (1.0, 1.0, 0.0, 1.0),  # Amarelo
            (0.5, 1.0, 0.0, 1.0),  # Amarelo-esverdeado
            (0.0, 1.0, 0.0, 1.0),  # Verde
            (0.0, 1.0, 0.5, 1.0),  # Verde-azulado
            (0.0, 0.5, 1.0, 1.0),  # Azul claro
            (0.0, 0.0, 0.8, 1.0)   # Azul
        ]

        total_cores = len(cores_faixa_predefinidas)  # Número total de cores predefinidas

        # Selecionar 'num_faixas' cores distribuídas uniformemente ao longo das cores predefinidas
        # Os índices das cores são escolhidos de forma a cobrir o total de cores disponível
        indices_cores = np.linspace(0, total_cores - 1, num_faixas).astype(int)
        cores_faixa = [cores_faixa_predefinidas[i] for i in indices_cores]  # Seleciona as cores para as faixas

        # Inverter as cores se o parâmetro inverter_gradiente for True
        if inverter_gradiente:
            cores_faixa = cores_faixa[::-1]  # Inverte a ordem das cores

        # Inicializa um array de zeros para armazenar as cores de cada vértice (RGBA)
        cores = np.zeros((len(valores), 4))  # Cria um array para armazenar as cores para cada vértice

        # Aplica a cor correspondente a cada vértice com base no valor
        for i, valor in enumerate(valores):
            # Percorre as faixas de valores para encontrar em qual faixa o valor se encaixa
            for j in range(num_faixas):
                if faixas[j] <= valor < faixas[j + 1]:
                    cores[i] = cores_faixa[j]  # Atribui a cor correspondente à faixa
                    break
            else:
                cores[i] = cores_faixa[-1]  # Atribui a última cor se o valor for o máximo ou além

        return cores  # Retorna o array de cores para cada vértice

    def atualizar_malha_com_faixas(self):
        """
        Atualiza a malha 3D com o número de faixas de cores selecionado e, opcionalmente, inverte o gradiente de cores.

        Esta função refaz a malha 3D com base no número de faixas de cores selecionado pelo usuário através de um slider,
        e também verifica se o gradiente de cores deve ser invertido. A malha 3D é removida da visualização, recriada
        com as novas cores, e re-adicionada à cena. Após a atualização, os eixos XYZ são re-adicionados se estiverem habilitados.

        Ações realizadas:
        - Remove o item da malha atual da visualização.
        - Verifica o estado do checkbox para inverter o gradiente de cores.
        - Recria as cores da malha com base no número de faixas selecionado no slider.
        - Atualiza a malha com as novas cores e adiciona à visualização.
        - Verifica o estado do checkbox para exibir os eixos XYZ e os re-adiciona se necessário.

        Parâmetros:
        - Nenhum parâmetro explícito. A função usa os widgets e o estado atual da malha para realizar as operações.

        Retorno:
        - Nenhum retorno explícito. Atualiza diretamente a visualização 3D.
        """
        # Verifica se a malha (mesh_data) está carregada
        if self.mesh_data is not None:
            # Remove o item da malha atual da visualização
            self.view.removeItem(self.mesh_item)  # Remove o item da malha atual

            # Verifica se o gradiente de cores deve ser invertido com base no estado do checkbox
            inverter_cores = self.checkbox_inverter_cores.isChecked()

            # Recriar as cores com base no número de faixas selecionado no slider
            num_faixas = self.slider_faixas.value()  # Obtém o número de faixas de cores do slider
            vertices_np = self.mesh_data.vertexes()  # Obtém os vértices da malha
            z_values = vertices_np[:, 2]  # Obtém os valores Z dos vértices para aplicar o gradiente
            colors = self.criar_simbologia_gradiente_discreta(z_values, num_faixas, inverter_cores)  # Cria as cores

            # Atualizar os dados da malha com as novas cores
            self.mesh_data.setVertexColors(colors)  # Define as novas cores para os vértices

            # Recriar o GLMeshItem com as novas cores e a opção de desenhar as arestas controlada pelo checkbox
            self.mesh_item = gl.GLMeshItem(
                meshdata=self.mesh_data,  # Dados da malha
                smooth=True,  # Habilita suavização
                drawEdges=self.checkbox_edges.isChecked(),  # Controla a exibição das arestas
                edgeColor=(0.5, 0.5, 0.5, 0.5),  # Cor das arestas (com transparência)
                shader=None  # Nenhum shader específico aplicado
            )
            self.mesh_item.setShader(None)  # Remove qualquer shader
            self.mesh_item.scale(10, 10, 10)  # Ajusta a escala da malha

            # Adiciona o item da malha de volta à visualização
            self.view.addItem(self.mesh_item)

            # Atualiza a visualização para aplicar as mudanças
            self.view.update()

            # Verifica se os eixos XYZ devem ser exibidos e os re-adiciona se necessário
            if self.checkbox_xyz.isChecked():
                self.adicionar_eixos_xyz()  # Re-adiciona os eixos XYZ

class KMLStyleDialog(QDialog):
    """
    Esta classe cria um diálogo para a personalização dos estilos de exportação KML. O usuário pode definir
    a largura da linha, a transparência da linha, a cor da linha, a transparência das faces e a cor das faces.
    
    Detalhamento:
    1. Inicialização dos valores padrão para a cor da linha e a cor das faces.
    2. Configuração do layout principal do diálogo.
    3. Criação de um QFrame para manter os widgets de configuração.
    4. Adição de widgets para configurar a largura da linha.
    5. Adição de widgets para configurar a transparência da linha e escolher a cor da linha.
    6. Adição de widgets para configurar a transparência das faces e escolher a cor das faces.
    7. Adição de botões para confirmar ou cancelar a exportação.
    8. Configuração das interações, como a alteração da transparência da linha que desativa a largura da linha.

    Parâmetros:
    - parent: Widget pai do diálogo (padrão: None).

    Retorno:
    - Nenhum retorno direto. O diálogo coleta as configurações de estilo do usuário.

    Exceções tratadas:
    - Nenhuma exceção específica tratada nesta função.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Personalização de Estilos KML")
        
        self.line_color = QColor(0, 0, 255)  # Cor padrão azul
        self.face_color = QColor(0, 255, 0)  # Cor padrão verde

        # Layout principal
        main_layout = QVBoxLayout()  # Cria o layout vertical principal

        # QFrame
        frame = QFrame()  # Cria um frame
        frame.setFrameShape(QFrame.StyledPanel)  # Define o estilo do frame
        frame.setFrameShadow(QFrame.Raised)  # Define a sombra do frame
        frame_layout = QVBoxLayout()  # Cria um layout vertical para o frame

        # Largura da Linha
        line_width_layout = QHBoxLayout()  # Cria um layout horizontal para a largura da linha
        line_width_label = QLabel("Largura da Linha:")  # Cria um rótulo
        self.line_width_spinbox = QDoubleSpinBox()  # Cria um spinbox para a largura da linha
        self.line_width_spinbox.setRange(0.5, 10.0)  # Define o intervalo de valores
        self.line_width_spinbox.setSingleStep(0.5)  # Define o passo dos valores
        self.line_width_spinbox.setValue(1.0)  # Define o valor padrão
        line_width_layout.addWidget(line_width_label)  # Adiciona o rótulo ao layout
        line_width_layout.addWidget(self.line_width_spinbox)  # Adiciona o spinbox ao layout
        
        # Opacidade da Linha
        line_opacity_layout = QHBoxLayout()  # Cria um layout horizontal para a opacidade da linha
        line_opacity_label = QLabel("Transparência das Linhas:")  # Cria um rótulo
        self.line_opacity_spinbox = QSpinBox()  # Cria um spinbox para a opacidade da linha
        self.line_opacity_spinbox.setRange(0, 100)  # Define o intervalo de valores
        self.line_opacity_spinbox.setSingleStep(5)  # Define o passo dos valores
        self.line_opacity_spinbox.setSuffix("%")  # Define o sufixo "%" para o spinbox
        self.line_opacity_spinbox.setValue(100)  # Define o valor padrão
        self.line_opacity_spinbox.valueChanged.connect(self.update_line_width_state)  # Conecta o sinal de alteração de valor ao método update_line_width_state
        self.line_color_button = QPushButton("Cor")  # Cria um botão para escolher a cor da linha
        self.line_color_button.setFixedSize(30, 20)  # Define o tamanho fixo do botão
        self.line_color_button.clicked.connect(self.choose_line_color)  # Conecta o clique do botão ao método choose_line_color
        self.update_button_color(self.line_color_button, self.line_color)  # Atualiza a cor do botão
        line_opacity_layout.addWidget(line_opacity_label)  # Adiciona o rótulo ao layout
        line_opacity_layout.addWidget(self.line_opacity_spinbox)  # Adiciona o spinbox ao layout
        line_opacity_layout.addWidget(self.line_color_button)  # Adiciona o botão ao layout
        
        # Transparência das Faces
        face_opacity_layout = QHBoxLayout()  # Cria um layout horizontal para a opacidade das faces
        face_opacity_label = QLabel("Transparência das Faces:")  # Cria um rótulo
        self.face_opacity_spinbox = QSpinBox()  # Cria um spinbox para a opacidade das faces
        self.face_opacity_spinbox.setRange(0, 100)  # Define o intervalo de valores
        self.face_opacity_spinbox.setSingleStep(5)  # Define o passo dos valores
        self.face_opacity_spinbox.setSuffix("%")  # Define o sufixo "%" para o spinbox
        self.face_opacity_spinbox.setValue(50)  # Define o valor padrão
        self.face_color_button = QPushButton("Cor")  # Cria um botão para escolher a cor das faces
        self.face_color_button.setFixedSize(30, 20)  # Define o tamanho fixo do botão
        self.face_color_button.clicked.connect(self.choose_face_color)  # Conecta o clique do botão ao método choose_face_color
        self.update_button_color(self.face_color_button, self.face_color)  # Atualiza a cor do botão
        face_opacity_layout.addWidget(face_opacity_label)  # Adiciona o rótulo ao layout
        face_opacity_layout.addWidget(self.face_opacity_spinbox)  # Adiciona o spinbox ao layout
        face_opacity_layout.addWidget(self.face_color_button)  # Adiciona o botão ao layout
        
        # Botões
        self.ok_button = QPushButton("Exportar")  # Cria o botão de confirmação
        self.ok_button.clicked.connect(self.accept)  # Conecta o clique do botão ao método accept
        self.cancel_button = QPushButton("Cancelar")  # Cria o botão de cancelamento
        self.cancel_button.clicked.connect(self.reject)  # Conecta o clique do botão ao método reject
        buttons_layout = QHBoxLayout()  # Cria um layout horizontal para os botões
        buttons_layout.addWidget(self.ok_button)  # Adiciona o botão de confirmação ao layout
        buttons_layout.addWidget(self.cancel_button)  # Adiciona o botão de cancelamento ao layout
        
        # Adicionando ao frame layout
        frame_layout.addLayout(line_width_layout)  # Adiciona o layout da largura da linha ao layout do frame
        frame_layout.addLayout(line_opacity_layout)  # Adiciona o layout da opacidade da linha ao layout do frame
        frame_layout.addLayout(face_opacity_layout)  # Adiciona o layout da opacidade das faces ao layout do frame
        frame_layout.addLayout(buttons_layout)  # Adiciona o layout dos botões ao layout do frame
        frame.setLayout(frame_layout)  # Define o layout do frame
        
        # Adicionando ao layout principal
        main_layout.addWidget(frame)  # Adiciona o frame ao layout principal
        self.setLayout(main_layout)  # Define o layout principal do diálogo

    def choose_line_color(self):
        """
        Abre um diálogo de seleção de cores para escolher a cor da linha.
        Atualiza a cor do botão de seleção de cor da linha se uma cor válida for escolhida.

        Detalhamento:
        1. Abre o diálogo de seleção de cores com a cor atual da linha como padrão.
        2. Verifica se a cor escolhida pelo usuário é válida.
        3. Atualiza a cor da linha com a cor escolhida.
        4. Atualiza a cor do botão de seleção de cor da linha para refletir a nova cor.

        Parâmetros:
        - Nenhum

        Retorno:
        - Nenhum retorno direto. A função atualiza a cor da linha e a cor do botão de seleção.

        Exceções tratadas:
        - Nenhuma exceção específica tratada nesta função.
        """

        # Abre o diálogo de seleção de cores com a cor atual da linha como padrão
        color = QColorDialog.getColor(self.line_color, self)

        # Verifica se a cor escolhida pelo usuário é válida
        if color.isValid():
            # Atualiza a cor da linha com a cor escolhida
            self.line_color = color

            # Atualiza a cor do botão de seleção de cor da linha para refletir a nova cor
            self.update_button_color(self.line_color_button, self.line_color)

    def choose_face_color(self):
        """
        Abre um diálogo de seleção de cores para escolher a cor das faces.
        Atualiza a cor do botão de seleção de cor das faces se uma cor válida for escolhida.

        Detalhamento:
        1. Abre o diálogo de seleção de cores com a cor atual das faces como padrão.
        2. Verifica se a cor escolhida pelo usuário é válida.
        3. Atualiza a cor das faces com a cor escolhida.
        4. Atualiza a cor do botão de seleção de cor das faces para refletir a nova cor.

        Parâmetros:
        - Nenhum

        Retorno:
        - Nenhum retorno direto. A função atualiza a cor das faces e a cor do botão de seleção.

        Exceções tratadas:
        - Nenhuma exceção específica tratada nesta função.
        """
        
        # Abre o diálogo de seleção de cores com a cor atual das faces como padrão
        color = QColorDialog.getColor(self.face_color, self)

        # Verifica se a cor escolhida pelo usuário é válida
        if color.isValid():
            # Atualiza a cor das faces com a cor escolhida
            self.face_color = color
            # Atualiza a cor do botão de seleção de cor das faces para refletir a nova cor
            self.update_button_color(self.face_color_button, self.face_color)

    def update_button_color(self, button, color):
        """
        Atualiza a cor de fundo de um botão para refletir a cor selecionada.

        Detalhamento:
        1. Obtém a paleta atual do botão.
        2. Define a nova cor de fundo do botão na paleta.
        3. Habilita o preenchimento automático de fundo do botão.
        4. Aplica a nova paleta ao botão.
        5. Atualiza o botão para refletir as mudanças.

        Parâmetros:
        - button: O botão cuja cor de fundo será atualizada.
        - color: A nova cor a ser aplicada ao botão.

        Retorno:
        - Nenhum retorno direto. A função atualiza a cor de fundo do botão.

        Exceções tratadas:
        - Nenhuma exceção específica tratada nesta função.
        """

        # Obtém a paleta atual do botão
        palette = button.palette()

        # Define a nova cor de fundo do botão na paleta
        palette.setColor(QPalette.Button, color)

        # Habilita o preenchimento automático de fundo do botão
        button.setAutoFillBackground(True)

        # Aplica a nova paleta ao botão
        button.setPalette(palette)

        # Atualiza o botão para refletir as mudanças
        button.update()

    def update_line_width_state(self):
        """
        Atualiza o estado de habilitação do spinbox da largura da linha com base no valor da opacidade da linha.

        Detalhamento:
        1. Verifica se o valor do spinbox de opacidade da linha é igual a 0.
        2. Se a opacidade da linha for 0, desativa o spinbox da largura da linha.
        3. Se a opacidade da linha for diferente de 0, ativa o spinbox da largura da linha.

        Parâmetros:
        - Nenhum

        Retorno:
        - Nenhum retorno direto. A função atualiza o estado de habilitação do spinbox da largura da linha.

        Exceções tratadas:
        - Nenhuma exceção específica tratada nesta função.
        """
        
        # Verifica se o valor do spinbox de opacidade da linha é igual a 0
        if self.line_opacity_spinbox.value() == 0:
            # Se a opacidade da linha for 0, desativa o spinbox da largura da linha
            self.line_width_spinbox.setEnabled(False)
        else:
            # Se a opacidade da linha for diferente de 0, ativa o spinbox da largura da linha
            self.line_width_spinbox.setEnabled(True)

    def get_style_options(self):
        """
        Retorna as opções de estilo definidas pelo usuário para a exportação KML.

        Detalhamento:
        1. Obtém o valor da largura da linha do spinbox correspondente.
        2. Converte o valor da opacidade da linha de percentual (0-100%) para uma escala de 0 a 255.
        3. Obtém a cor da linha selecionada pelo usuário.
        4. Converte o valor da opacidade das faces de percentual (0-100%) para uma escala de 0 a 255.
        5. Obtém a cor das faces selecionada pelo usuário.

        Parâmetros:
        - Nenhum

        Retorno:
        - Um dicionário contendo as opções de estilo:
            - "line_width": Largura da linha (float).
            - "line_opacity": Opacidade da linha (int, 0-255).
            - "line_color": Cor da linha (QColor).
            - "face_opacity": Opacidade das faces (int, 0-255).
            - "face_color": Cor das faces (QColor).

        Exceções tratadas:
        - Nenhuma exceção específica tratada nesta função.
        """
        
        # Retorna um dicionário com as opções de estilo
        return {
            "line_width": self.line_width_spinbox.value(),  # Obtém o valor da largura da linha
            "line_opacity": int(self.line_opacity_spinbox.value() * 2.55),  # Converte a opacidade da linha de % para 0-255
            "line_color": self.line_color,  # Obtém a cor da linha
            "face_opacity": int(self.face_opacity_spinbox.value() * 2.55),  # Converte a opacidade das faces de % para 0-255
            "face_color": self.face_color  # Obtém a cor das faces
        }

class ExportaMalha3D(QDialog):
    def __init__(self, parent=None):
        """
        Inicializa a interface de diálogo para exportação de malha 3D.

        Funções e Ações Desenvolvidas:
        - Configura o título da janela do diálogo.
        - Cria e organiza os layouts e botões do diálogo.
        - Aplica estilos personalizados aos botões.
        - Adiciona efeitos de sombra aos textos dos botões.

        :param parent: O widget pai do diálogo, se houver.
        """
        super().__init__(parent)
        
        self.setWindowTitle("Exportar Malha 3D")  # Define o título da janela do diálogo
        
        main_layout = QVBoxLayout()  # Cria o layout principal do tipo QVBoxLayout
        
        # Cria um frame para os botões com estilo de painel
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Raised)
        
        frame_layout = QVBoxLayout()  # Cria o layout do frame do tipo QVBoxLayout
        
        # Layout superior com dois botões (DXF e DAE)
        top_layout = QHBoxLayout()
        self.button_dxf = QPushButton("DXF")
        self.button_dae = QPushButton("DAE")
        top_layout.addWidget(self.button_dxf)
        top_layout.addWidget(self.button_dae)
        
        # Layout inferior com dois botões (STL e OBJ)
        bottom_layout = QHBoxLayout()
        self.button_stl = QPushButton("STL")
        self.button_obj = QPushButton("OBJ")
        bottom_layout.addWidget(self.button_stl)
        bottom_layout.addWidget(self.button_obj)
        
        # Adiciona os layouts superior e inferior ao layout do frame
        frame_layout.addLayout(top_layout)
        frame_layout.addLayout(bottom_layout)
        frame.setLayout(frame_layout)  # Define o layout do frame
        
        # Botão de cancelar
        self.button_cancel = QPushButton("Cancelar")
        self.button_cancel.clicked.connect(self.reject)  # Conecta o botão cancelar à função reject
        
        # Adiciona o frame e o botão de cancelar ao layout principal
        main_layout.addWidget(frame)
        main_layout.addWidget(self.button_cancel)
        
        self.setLayout(main_layout)  # Define o layout principal do diálogo
        
        # Personalizar os botões
        self.estilizar_botoes()
        self.adicionar_sombra_nos_textos()

    def estilizar_botoes(self):
        """
        Aplica estilos personalizados aos botões de formato de exportação.

        Funções e Ações Desenvolvidas:
        - Define um estilo base para todos os botões.
        - Aplica estilos específicos para cada botão (DXF, DAE, STL, OBJ).
        """
        estilo_base = """
            QPushButton {
                border: 2px solid #8f8f91;
                border-radius: 5px;
                background-color: #f0f0f0;
                min-width: 70px;
                padding: 5px;
                font: bold 12px;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """

        # Estilo personalizado para o botão DXF
        self.button_dxf.setStyleSheet(estilo_base + """
            QPushButton {
                border-color: #0078d7;
                color: #0078d7;
            }
            QPushButton:pressed {
                background-color: #005bb5;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3399ff;
            }
        """)

        # Estilo personalizado para o botão DAE
        self.button_dae.setStyleSheet(estilo_base + """
            QPushButton {
                border-color: #d70022;
                color: #d70022;
            }
            QPushButton:pressed {
                background-color: #b5001a;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #ff3344;
            }
        """)

        # Estilo personalizado para o botão STL
        self.button_stl.setStyleSheet(estilo_base + """
            QPushButton {
                border-color: #008000;
                color: #008000;
            }
            QPushButton:pressed {
                background-color: #005500;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #33cc33;
            }
        """)

        # Estilo personalizado para o botão OBJ
        self.button_obj.setStyleSheet(estilo_base + """
            QPushButton {
                border-color: #ffa500;
                color: #ffa500;
            }
            QPushButton:pressed {
                background-color: #cc8400;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #ffc966;
            }
        """)

    def adicionar_sombra_nos_textos(self):
        """
        Adiciona efeitos de sombra aos textos dos botões de formato de exportação.

        Funções e Ações Desenvolvidas:
        - Cria um efeito de sombra para cada botão.
        - Aplica o efeito de sombra aos botões de formato de exportação.
        """
        botoes = [self.button_dxf, self.button_dae, self.button_stl, self.button_obj]  # Lista de botões

        # Itera sobre cada botão e aplica o efeito de sombra
        for botao in botoes:
            efeito_sombra = QGraphicsDropShadowEffect()
            efeito_sombra.setBlurRadius(10)  # Define o raio do desfoque da sombra
            efeito_sombra.setColor(QColor(0, 0, 0, 160))  # Define a cor da sombra com opacidade
            efeito_sombra.setOffset(2, 2)  # Define o deslocamento da sombra
            botao.setGraphicsEffect(efeito_sombra)  # Aplica o efeito de sombra ao botão

class CustomDelegate(QStyledItemDelegate):
    """
    CustomDelegate é uma classe que herda de QStyledItemDelegate.
    Esta classe é usada para personalizar a aparência de itens em um QTreeView, especificamente
    para desenhar ícones que representam camadas de malha no QGIS.
    
    Métodos:
    - __init__: Inicializa a classe CustomDelegate.
    - paint: Desenha o ícone personalizado para a camada de malha.
    - sizeHint: Define o tamanho dos itens no QTreeView.
    """
    def __init__(self, parent=None):
        """
        Inicializa a instância de CustomDelegate.

        Parâmetros:
        - parent: O pai do delegado, geralmente o QTreeView.
        """
        super(CustomDelegate, self).__init__(parent)

    def paint(self, painter, option, index):
        """
        Desenha o ícone personalizado para a camada de malha.

        Parâmetros:
        - painter: O QPainter usado para desenhar o ícone.
        - option: As opções de estilo usadas para desenhar o item.
        - index: O índice do item no modelo.
        """
        super(CustomDelegate, self).paint(painter, option, index)  # Chama o método paint da classe base
        layer = index.data(Qt.UserRole)  # Obtém a camada do item usando o papel UserRole
        if isinstance(layer, QgsMeshLayer):  # Verifica se a camada é do tipo QgsMeshLayer
            icon_size = 14  # Define o tamanho do ícone
            pixmap = QPixmap(icon_size, icon_size)  # Cria um QPixmap do tamanho do ícone
            pixmap.fill(Qt.transparent)  # Preenche o QPixmap com transparência
            icon_painter = QPainter(pixmap)  # Cria um QPainter para desenhar no QPixmap
            icon_painter.setRenderHint(QPainter.Antialiasing)  # Habilita antialiasing para suavizar o desenho

            pen = QPen(Qt.blue)  # Cria uma caneta com a cor azul
            pen.setWidth(1)  # Define a largura da caneta
            icon_painter.setPen(pen)  # Define a caneta no QPainter

            # Define points for the triangles
            points = [
                QPoint(0, 0), QPoint(icon_size // 2, 0), QPoint(icon_size - 1, 0),
                QPoint(0, icon_size // 2), QPoint(icon_size // 2, icon_size // 2), QPoint(icon_size - 1, icon_size // 2),
                QPoint(0, icon_size - 1), QPoint(icon_size // 2, icon_size - 1), QPoint(icon_size - 1, icon_size - 1)
            ]

            # Define triangles with corresponding colors
            triangles = [
                (0, 1, 4, QColor(255, 255, 0)),  # Amarelo
                (0, 3, 4, QColor(255, 165, 0)),  # Laranja
                (1, 2, 4, QColor(255, 0, 255)),  # Roxo
                (3, 4, 7, QColor(255, 0, 255)),  # Roxo
                (3, 6, 7, QColor(255, 165, 0)),  # Laranja
                (4, 5, 8, QColor(255, 255, 0)),  # Amarelo
                (4, 7, 8, QColor(255, 0, 255))   # Roxo
            ]

            # Draw the triangles with colors
            for t in triangles:
                icon_painter.setBrush(t[3])  # Define o pincel com a cor do triângulo
                icon_painter.drawPolygon(points[t[0]], points[t[1]], points[t[2]])  # Desenha o triângulo

            icon_painter.end()  # Finaliza o desenho

            icon = QIcon(pixmap)  # Cria um ícone a partir do QPixmap
            icon_rect = option.rect  # Obtém o retângulo de desenho
            icon_rect.setSize(QSize(icon_size, icon_size))  # Define o tamanho do retângulo do ícone
            icon_rect.moveLeft(option.rect.left() - 16)  # Move o ícone para a esquerda
            icon.paint(painter, icon_rect, Qt.AlignVCenter | Qt.AlignLeft)  # Desenha o ícone no retângulo

    def sizeHint(self, option, index):
        """
        Define o tamanho dos itens no QTreeView.

        Parâmetros:
        - option: As opções de estilo usadas para desenhar o item.
        - index: O índice do item no modelo.

        Retorna:
        - QSize: O tamanho sugerido para o item.
        """
        size = super(CustomDelegate, self).sizeHint(option, index)  # Obtém o tamanho sugerido da classe base
        return QSize(size.width(), max(size.height(), 15))  # Retorna o tamanho ajustado