from PyQt5.QtWidgets import QTreeWidgetItem, QTreeWidget, QInputDialog, QTreeView, QFileDialog, QColorDialog, QMessageBox, QMenu, QStyledItemDelegate, QDialog, QVBoxLayout, QListWidget, QPushButton, QWidget, QHBoxLayout, QLabel, QCheckBox, QLineEdit, QRadioButton, QSpinBox, QDialogButtonBox, QGridLayout,QComboBox, QDoubleSpinBox, QButtonGroup, QFrame, QScrollArea, QSizePolicy, QApplication, QGraphicsView, QGraphicsScene, QSpacerItem, QFontComboBox, QAction, QProgressBar, QGraphicsTextItem, QGraphicsRectItem, QToolTip
from qgis.core import (QgsMapLayer, QgsField, QgsProject, QgsWkbTypes, QgsVectorFileWriter, QgsVectorLayer,  QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer, QgsSymbol, Qgis, QgsVectorLayerSimpleLabeling, QgsEditorWidgetSetup, QgsPalLayerSettings, QgsTextFormat, QgsLayerTreeLayer, QgsProperty, QgsFeature, QgsRendererCategory, QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsPointXY, QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsDefaultValue, QgsFeatureRequest, QgsFields, QgsMessageLog, QgsSpatialIndex, QgsDataSourceUri, QgsCoordinateTransformContext, QgsRuleBasedRenderer, QgsLineSymbol, QgsProviderRegistry)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon, QPixmap, QPainter, QColor, QPen, QFont, QPainter, QGuiApplication, QPainterPath, QPalette, QCursor, QFontMetrics
from PyQt5.QtCore import Qt, QSize, QRect, QVariant, QSettings, QRectF, QObject, QEvent
from qgis.gui import QgsProjectionSelectionDialog
from PIL import Image, UnidentifiedImageError
import xml.etree.ElementTree as ET
from functools import partial
from io import BytesIO
import processing
import functools
import requests
import openpyxl
import random
import ezdxf
import math
import time
import csv
import os
import re

# Importe a função criar_camada_linhas
from .criar_linhas import criar_camada_linhas

class UiManager:

    def __init__(self, iface, dialog):
        """
        Construtor da classe.

        :param iface: Interface do QGIS, usada para interagir com o ambiente do QGIS.
        :param dialog: Diálogo ou janela que esta classe controlará.
        """
        self.iface = iface # Atribui a interface do QGIS à variável de instância
        self.dlg = dialog  # Referência ao diálogo principal
        self.tree_view_event_filter = TreeViewEventFilter(self)  # Instanciar o filtro de eventos
        self.init_treeView() # Chama a função para inicializar a visualização em árvore

        # Atualiza o QTreeView com as camadas de linha
        self.atualizar_treeView_lista_linha()

        # Conectar ao sinal de adição de camadas
        QgsProject.instance().layerWasAdded.connect(self.atualizar_treeView_lista_linha)

        # Conectar ao sinal de remoção de camadas
        QgsProject.instance().layersRemoved.connect(self.atualizar_treeView_lista_linha)      

        # Conecta o botão para criar uma camada de linhas ao método que adiciona a camada e atualiza o treeView
        self.dlg.ButtonCriarLinha.clicked.connect(self.adicionar_camada_e_atualizar)
        self.dlg.ButtonCriarLinhaNome.clicked.connect(self.abrir_caixa_nome_camada)

        # Conectar o botão de deletar à função de remover a camada
        self.dlg.pushButtonDel.clicked.connect(self.remover_camada_selecionada)

        # Conectar o botão de renomear à função de renomear a camada
        self.dlg.pushButtonRenome.clicked.connect(self.renomear_camada_selecionada)

        # Conectar o botão de salvar permanente à função de salvar a camada
        self.dlg.pushButton_Permanente.clicked.connect(self.salvar_camada_permanente)

        # Conectar o botão 'salvar como' à função 'salvar_camada_multiplo' para salvar em múltiplos formatos
        self.dlg.pushButtonSalvaMultiplos.clicked.connect(self.salvar_camada_multiplo)

        # Sincroniza o seleção da lista de camadas do QGis
        self.iface.currentLayerChanged.connect(self.sincronizar_selecao_com_qgis)

        # Conecta o botão pushButtonFechar ao método fechar_dialogo
        self.dlg.pushButtonFechar.clicked.connect(self.fechar_dialogo)

        # Cria uma seleção sobre a Camada no treeView
        self.dlg.treeViewListaLinha.setStyleSheet("""
            QTreeView::item:hover:!selected {
                background-color: #def2fc; /* Cor de fundo ao passar o mouse sobre itens não selecionados */}
            QTreeView::item:selected {/* Estilo para itens selecionados, se necessário */}""")

        # Mantém na memória a última posição  
        self.ultimo_caminho_salvo = ""  # Inicializa a variável para armazenar o último caminho

        # Conectar o botão 'pushButtonTabela' à função de abrir a tabela de atributos
        self.dlg.pushButtonTabela.clicked.connect(self.abrir_tabela_atributos)

        # Conecta a alteração da cor da linha do treeView
        self.dlg.treeViewListaLinha.doubleClicked.connect(self.on_treeViewItem_doubleClicked)

        # Conectando o botão à função tooButtonAbrir
        self.dlg.pushButtonAbrir.clicked.connect(self.abrir_adicionar_arquivo)

        #Diálogo que permite ao usuário selecionar campos da camada atual que serão
        # usados para compor as etiquetas (rótulos) das feições no mapa.
        self.dlg.pushButtonCampo.clicked.connect(self.abrir_dialogo_selecao_campos)

        # Escrever a função
        self.fieldColors = {}  # Armazenará as cores atribuídas aos campos
        self.fieldVisibility = {}  # Armazena a visibilidade dos campos

        #Conecta o botão para exportar a camada para DXF
        self.dlg.pushButtonExporta.clicked.connect(self.exportar_para_dxf)

        # Conecta o botão para exportar a camada para KML
        self.dlg.pushButtonExportaKml_1.clicked.connect(self.exportar_para_kml)

        # Conecta o botão para Zoom
        self.dlg.pushButtonVisualizarLinha.clicked.connect(self.visualizar_linha_selecionada)

        # Conecta o botão para Clocar a Camada de Linha
        self.dlg.pushButtonClonarLinha.clicked.connect(self.clone_layer)

       # Conectamos as mudanças de camadas no QGIS para SINCRONIZAR com TreeView
        self.iface.mapCanvas().layersChanged.connect(self.sync_from_qgis_to_treeview)

    def init_treeView(self):
        """
        Inicializa a visualização em árvore (treeView) para a lista de camadas de linhas na interface.
        Ações realizadas:
        1. Conecta o clique no item da árvore ao método on_treeViewItem_clicked para tratar cliques nos itens.
        2. Define a política de menu de contexto para customizada, permitindo a exibição de um menu de contexto personalizado.
        3. Conecta a requisição de menu de contexto ao método open_context_menu para abrir um menu de contexto.
        4. Atualiza a lista de camadas exibidas na árvore chamando o método atualizar_treeView_lista_linha.
        5. Configura um delegado personalizado para os itens da árvore para modificar sua apresentação visual.
        6. Aplica o delegado ao treeView.
        7. Atualiza o treeView para refletir quaisquer mudanças feitas.
        8. Atualiza o estado dos botões da interface baseando-se no modelo de dados do treeView.

        Atribuição no código:
        Este método é responsável por preparar e configurar a árvore de visualização de camadas no diálogo,
        permitindo interações do usuário com as camadas listadas e garantindo a sincronia visual dos estados dos botões
        e itens conforme mudanças ocorrem no modelo de dados.
        """

        # Conectar o sinal selectionChanged após o modelo estar configurado
        self.dlg.treeViewListaLinha.clicked.connect(self.on_treeViewItem_clicked)

        # Conectar o sinal do tooltip
        self.dlg.treeViewListaLinha.setMouseTracking(True)
        self.dlg.treeViewListaLinha.viewport().installEventFilter(self.tree_view_event_filter)  # Usar o filtro de eventos

        self.dlg.pushButtonReprojetarLinha.clicked.connect(self.abrir_dialogo_crs)

        # Configura o treeView para aceitar um menu de contexto personalizado
        self.dlg.treeViewListaLinha.setContextMenuPolicy(Qt.CustomContextMenu)

        # Conecta o evento de solicitação de menu de contexto ao método open_context_menu
        self.dlg.treeViewListaLinha.customContextMenuRequested.connect(self.open_context_menu)

        # Chamar a função para atualizar a lista inicialmente
        self.atualizar_treeView_lista_linha() 

        # Configura o delegado personalizado
        custom_delegate = CustomDelegate(self.dlg.treeViewListaLinha)
        self.dlg.treeViewListaLinha.setItemDelegate(custom_delegate)
        self.dlg.treeViewListaLinha.update()  # Força a atualização do QTreeView

        # Chama a função para atualizar o estado dos botões
        self.atualizar_estado_botoes()

    def atualizar_treeView_lista_linha(self):
        """
        Atualiza a visualização em árvore (treeView) com a lista atualizada de camadas de linhas, refletindo quaisquer mudanças como adições ou remoções de camadas.

        Funcionalidades:
        - Cria um novo modelo para o treeView, redefinindo completamente sua estrutura e conteúdo.
        - Adiciona todas as camadas de linha disponíveis no projeto ao novo modelo, garantindo que a lista esteja sempre atualizada.
        - Verifica se o índice atual na árvore é válido; se não for, ajusta a seleção para a última camada disponível, evitando que a seleção fique em um estado inválido.
        - Atualiza o estado dos botões na interface (habilitados ou desabilitados) baseado na existência ou não de camadas no modelo.

        Atribuição no código:
        Essa função é crucial para manter a interface do usuário sincronizada com o estado atual das camadas dentro do projeto. É chamada após qualquer modificação no conjunto de camadas (como adição ou remoção), durante inicializações da interface, ou quando necessário revalidar e atualizar a visualização após mudanças significativas no modelo de dados.
        """
        self.criar_modelo_para_treeview() # Cria um novo modelo para a árvore de visualização
        self.adicionar_camadas_ao_modelo() # Adiciona as camadas ao modelo

        # Obtém o índice do item atualmente selecionado
        current_index = self.dlg.treeViewListaLinha.currentIndex()

        # Verifica se nenhum item está selecionado
        if not current_index.isValid():
            # Seleciona a última camada
            self.selecionar_ultima_camada()

        # Chama a função para atualizar o estado dos botões
        self.atualizar_estado_botoes()

    def atualizar_estado_botoes(self):
        """
        Atualiza o estado de habilitação dos botões na interface com base na presença ou ausência de camadas no modelo do treeView.

        Funcionalidades:
        - Verifica se o modelo do treeView está vazio, ou seja, se não contém nenhuma camada.
        - Habilita ou desabilita todos os botões relevantes com base na presença de camadas. Se não houver camadas, todos os botões são desabilitados para evitar operações que requerem uma camada selecionada.
        - Os botões afetados incluem: deletar camada, renomear camada, salvar permanentemente, salvar múltiplos formatos, abrir tabela de atributos, escolher campos para operações, exportar para DXF, exportar para KML, visualizar linha e clonar linha.

        Atribuição no código:
        Essencial para a usabilidade da interface do usuário, garantindo que o usuário só possa interagir com funções que requerem uma camada quando houver camadas disponíveis. Isso previne erros e melhora a experiência do usuário ao proporcionar um feedback visual claro sobre as ações permitidas em cada momento.
        """
        # Verifica se o modelo do treeView está vazio
        modelo_vazio = self.dlg.treeViewListaLinha.model().rowCount() == 0

        # Atualiza o estado dos botões baseado na presença ou ausência de itens no modelo
        self.dlg.pushButtonDel.setEnabled(not modelo_vazio)
        self.dlg.pushButtonRenome.setEnabled(not modelo_vazio)
        self.dlg.pushButton_Permanente.setEnabled(not modelo_vazio)
        self.dlg.pushButtonSalvaMultiplos.setEnabled(not modelo_vazio)
        self.dlg.pushButtonTabela.setEnabled(not modelo_vazio)
        self.dlg.pushButtonCampo.setEnabled(not modelo_vazio)
        self.dlg.pushButtonExporta.setEnabled(not modelo_vazio)
        self.dlg.pushButtonExportaKml_1.setEnabled(not modelo_vazio)
        self.dlg.pushButtonVisualizarLinha.setEnabled(not modelo_vazio)
        self.dlg.pushButtonClonarLinha.setEnabled(not modelo_vazio)
        self.dlg.pushButtonReprojetarLinha.setEnabled(not modelo_vazio)

    def configurar_tooltip(self, index):
        """
        Configura um tooltip para exibir informações sobre a camada de linha selecionada no treeView.

        A função extrai informações sobre a camada de linha, como o tipo de linha (ex: LineString) e o sistema
        de referência de coordenadas (SRC) atual da camada. Essas informações são exibidas em um tooltip
        que aparece quando o usuário passa o mouse sobre o item correspondente no treeView.

        Parâmetros:
        - self: Referência à instância atual do objeto. (UiManager)
        - index: QModelIndex do item atualmente sob o cursor no treeView.

        A função não retorna valores.
        """
        item = index.model().itemFromIndex(index)  # Obtém o item do modelo de dados com base no índice fornecido
        layer_id = item.data()  # Obtém o ID da camada associada ao item
        layer = QgsProject.instance().mapLayer(layer_id)  # Recupera a camada correspondente ao ID no projeto QGIS
        if layer:  # Verifica se a camada existe
            tipo_linha = self.obter_tipo_de_linha(layer)  # Obtém o tipo de linha (ex: LineString) da camada
            crs = layer.crs().description() if layer.crs().isValid() else "Sem Georreferências"  # Obtém a descrição do SRC da camada ou "Sem Georreferências" se inválido
            tooltip_text = f"Tipo: {tipo_linha}\nSRC: {crs}"  # Formata o texto do tooltip com as informações da camada
            QToolTip.showText(QCursor.pos(), tooltip_text)  # Exibe o tooltip na posição atual do cursor

    def obter_tipo_de_linha(self, layer):
        """
        Retorna uma string que descreve o tipo de geometria da camada fornecida.

        A função obtém o tipo de geometria WKB (Well-Known Binary) da camada e converte esse tipo
        em uma string legível, como 'LineString', 'MultiLineStringZM', etc.

        Parâmetros:
        - self: Referência à instância atual do objeto. (UiManager)
        - layer: Objeto QgsVectorLayer representando a camada de onde o tipo de linha será extraído.

        Retorno:
        - tipo_linha (str): Uma string que descreve o tipo de geometria da camada.
        """
        geometry_type = layer.wkbType()  # Obtém o tipo de geometria WKB (Well-Known Binary) da camada
        tipo_linha = QgsWkbTypes.displayString(geometry_type)  # Converte o tipo de geometria em uma string legível
        return tipo_linha  # Retorna a string que descreve o tipo de geometria

    def visualizar_linha_selecionada(self):
        """
        Aproxima a visualização do mapa para a camada de linha selecionada no treeView.

        A função obtém a camada de linha atualmente selecionada no treeView e ajusta a extensão do mapa
        para que a camada selecionada seja centralizada e visível na tela. Caso a camada não tenha feições
        ou o índice não seja válido, a função retorna sem fazer alterações.

        Parâmetros:
        - self: Referência à instância atual do objeto. (UiManager)

        A função não retorna valores.
        """
        index = self.dlg.treeViewListaLinha.currentIndex()  # Obtém o índice atualmente selecionado no treeView
        if not index.isValid():  # Verifica se o índice é válido (se há uma seleção)
            return  # Sai da função se o índice não for válido
        
        layer_id = index.model().itemFromIndex(index).data()  # Obtém o ID da camada associada ao item selecionado
        layer = QgsProject.instance().mapLayer(layer_id)  # Recupera a camada correspondente ao ID no projeto QGIS
        if not layer or layer.extent().isEmpty():  # Verifica se a camada existe e se possui uma extensão válida
            return  # Sai da função se a camada não existir ou não tiver feições
        
        # Usa o método "Aproximar à" do QGIS para ajustar a visualização à extensão da camada ativa
        self.iface.zoomToActiveLayer()

    def abrir_dialogo_crs(self):
        """
        Abre um diálogo de seleção de CRS e reprojeta a camada selecionada no treeView.

        A função permite ao usuário escolher um novo sistema de referência de coordenadas (SRC) para a camada 
        selecionada no treeView. Após a seleção, a camada é reprojetada usando o novo SRC, e a nova camada é 
        adicionada ao projeto QGIS com a mesma cor e estilo de rótulo da camada original.

        Parâmetros:
        - self: Referência à instância atual do objeto. (UiManager)

        A função não retorna valores, mas adiciona uma nova camada reprojetada ao projeto QGIS.
        """
        index = self.dlg.treeViewListaLinha.currentIndex()  # Obtém o índice atualmente selecionado no treeView
        if not index.isValid():  # Verifica se o índice é válido (se há uma seleção)
            return  # Sai da função se o índice não for válido
        
        layer_id = index.model().itemFromIndex(index).data()  # Obtém o ID da camada associada ao item selecionado
        layer = QgsProject.instance().mapLayer(layer_id)  # Recupera a camada correspondente ao ID no projeto QGIS
        if not layer:  # Verifica se a camada existe
            return  # Sai da função se a camada não existir
        
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

                # Aplicar a cor da camada original
                self.aplicar_cor_linha(nova_camada, self.obter_cor_linha(layer))  # Copia a cor da camada original

                # Aplicar o estilo de rótulo da camada original
                self.aplicar_estilo_rotulo(nova_camada, layer)  # Copia o estilo de rótulo da camada original

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

    def obter_estilo_rotulo(self, layer):
        """
        Obtém as configurações de rótulo da camada fornecida.

        A função recupera as configurações de rotulagem da camada especificada. Se a camada tiver 
        um estilo de rotulagem definido, a função retorna uma cópia (clone) dessas configurações 
        para que possam ser aplicadas a outra camada. Se a camada não tiver rotulagem definida, 
        a função retorna None.

        Parâmetros:
        - self: Referência à instância atual do objeto. (UiManager)
        - layer: Objeto QgsVectorLayer representando a camada da qual as configurações de rótulo 
          serão extraídas.

        Retorno:
        - labeling (QgsAbstractVectorLayerLabeling ou None): Retorna uma cópia das configurações 
          de rotulagem se existirem, caso contrário, retorna None.
        """
        labeling = layer.labeling()  # Obtém as configurações de rotulagem da camada
        if labeling:  # Verifica se a camada possui rotulagem definida
            return labeling.clone()  # Retorna uma cópia das configurações de rotulagem
        return None  # Retorna None se não houver rotulagem definida

    def aplicar_estilo_rotulo(self, nova_camada, camada_original):
        """
        Aplica o estilo de rótulo da camada original à nova camada reprojetada.

        A função tenta copiar as configurações de rótulo da camada original para a nova camada 
        reprojetada. Se a cópia direta do estilo de rótulo não for bem-sucedida, a função tenta 
        configurar manualmente o estilo de rótulo baseado no campo de rótulo da camada original.

        Se os rótulos não estiverem ativados na camada original, não serão aplicados à nova camada.

        Parâmetros:
        - self: Referência à instância atual do objeto. (UiManager)
        - nova_camada: Objeto QgsVectorLayer representando a nova camada para a qual o estilo de rótulo será aplicado.
        - camada_original: Objeto QgsVectorLayer representando a camada original da qual o estilo de rótulo será copiado.

        A função não retorna valores, mas aplica o estilo de rótulo à nova camada.
        """
        # Verifica se a camada original tem rotulagem ativa
        if camada_original.labelsEnabled():
            # Obtém as configurações de rótulo da camada original
            label_settings = self.obter_estilo_rotulo(camada_original)
            if label_settings:  # Verifica se as configurações de rótulo foram obtidas
                nova_camada.setLabeling(label_settings)  # Aplica as configurações de rótulo à nova camada
                nova_camada.setLabelsEnabled(True)  # Certifica-se de que os rótulos estão ativados na nova camada
                nova_camada.triggerRepaint()  # Recarrega a camada para aplicar as mudanças visuais

            # Se ainda não funcionar, tenta configurar manualmente o estilo dos rótulos
            else:
                provider = camada_original.dataProvider()  # Obtém o provedor de dados da camada original
                if provider:  # Verifica se o provedor de dados foi obtido
                    # Tenta acessar as configurações de rótulo manualmente, se disponível
                    expression = camada_original.labeling().settings().fieldName
                    if expression:  # Verifica se o campo de rótulo foi obtido
                        nova_camada.setLabelsEnabled(True)  # Ativa os rótulos na nova camada
                        label_settings = QgsPalLayerSettings()  # Cria uma nova instância de configurações de rótulo
                        label_settings.fieldName = expression  # Define o campo de rótulo
                        label_settings.isExpression = True  # Define que o rótulo é baseado em uma expressão
                        label_settings.placement = QgsPalLayerSettings.Line  # Define o posicionamento dos rótulos
                        labeling = QgsVectorLayerSimpleLabeling(label_settings)  # Cria o sistema de rotulagem simples
                        nova_camada.setLabeling(labeling)  # Aplica o sistema de rotulagem à nova camada
                        nova_camada.triggerRepaint()  # Recarrega a camada para aplicar as mudanças visuais

    def abrir_caixa_nome_camada(self):
        """
        Abre uma caixa de diálogo para o usuário inserir o nome da nova camada de linha,
        selecionar uma cor opcional e escolher um sistema de referência de coordenadas (CRS).

        Funcionalidades e Ações Desenvolvidas:
        1. Criação de uma interface gráfica com campos de:
            - Nome da nova camada (obrigatório).
            - Botão para escolher cor da linha (opcional).
            - Botão para escolher o CRS da camada (opcional).
        2. Validação do campo de nome para garantir que não seja vazio.
        3. Uso de QColorDialog para seleção de cor personalizada.
        4. Uso de QgsProjectionSelectionDialog para escolha do sistema de coordenadas (CRS).
        5. Criação da nova camada chamando a função `criar_camada_linhas`, com os parâmetros definidos.
        6. Atualização da visualização no QTreeView após a adição da camada.

        Observações:
        - A função assume que `criar_camada_linhas` está adaptada para aceitar os parâmetros `nome_camada`, `cor` e `crs`.
        - A cor e o CRS são opcionais. Se não forem definidos pelo usuário, são usados valores padrão.
        """
        dialog = QDialog(self.dlg)
        dialog.setWindowTitle("Nome da Camada")
        layout = QVBoxLayout(dialog)

        # Criação do frame com estilo Box e Raised
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        frame_layout = QVBoxLayout(frame)

        # 1) Nome da Camada
        frame_layout.addWidget(QLabel("Digite o nome da camada:"))
        lineEdit = QLineEdit()
        lineEdit.setPlaceholderText("Camada Temporária")
        frame_layout.addWidget(lineEdit)

        # 2) Botões para cor e reprojeção
        hLayoutBotoesCorReproj = QHBoxLayout()

        pushButtonCor = QPushButton("Escolher Cor")
        hLayoutBotoesCorReproj.addWidget(pushButtonCor)

        pushButtonReproj = QPushButton("Projetar SRC")
        hLayoutBotoesCorReproj.addWidget(pushButtonReproj)

        frame_layout.addLayout(hLayoutBotoesCorReproj)

        # Adiciona o frame ao layout principal
        layout.addWidget(frame)
        
        # Variáveis para armazenar cor e CRS escolhidos (opcionais)
        selectedColor = None
        selectedCrs = None

        # 3) Função para escolher cor
        def escolher_cor():
            nonlocal selectedColor
            cor = QColorDialog.getColor(
                QColor(0, 0, 0) if selectedColor is None else selectedColor,
                dialog,
                "Escolher Cor da Linha"
            )
            if cor.isValid():
                selectedColor = cor
                # Ajusta a cor do botão para indicar visualmente a escolha
                pushButtonCor.setStyleSheet(f"background-color: {cor.name()}")

        pushButtonCor.clicked.connect(escolher_cor)

        # 4) Função para escolher CRS (usando lógica semelhante à abrir_dialogo_crs existente)
        def escolher_crs():
            nonlocal selectedCrs
            # Podemos criar temporariamente uma camada só para abrir o mesmo diálogo,
            # ou abrir diretamente o QgsProjectionSelectionDialog
            dialog_crs = QgsProjectionSelectionDialog(self.dlg)
            
            # Seta como default o CRS do projeto atual
            crs_padrao = QgsProject.instance().crs()
            dialog_crs.setCrs(crs_padrao)
            
            if dialog_crs.exec_():
                novo_crs = dialog_crs.crs()
                if novo_crs.isValid():
                    selectedCrs = novo_crs
                    pushButtonReproj.setText(novo_crs.authid())
        
        pushButtonReproj.clicked.connect(escolher_crs)

        # 5) Botões "Adicionar" e "Cancelar" no rodapé
        okButton = QPushButton("Adicionar")
        cancelButton = QPushButton("Cancelar")
        okButton.setEnabled(False)
        lineEdit.textChanged.connect(lambda: okButton.setEnabled(bool(lineEdit.text().strip())))

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)
        layout.addLayout(buttonLayout)
        
        okButton.clicked.connect(dialog.accept)
        cancelButton.clicked.connect(dialog.reject)

        # 6) Execução do diálogo
        if dialog.exec_() == QDialog.Accepted and lineEdit.text().strip():
            nome_camada = lineEdit.text().strip()

            # Se o usuário não escolheu CRS, usamos o CRS padrão do projeto
            if selectedCrs is None:
                selectedCrs = QgsProject.instance().crs()

            # Cria a camada com nome, cor e CRS escolhidos
            # Ajuste a função criar_camada_linhas para aceitar 'cor' e 'crs'
            # e retornar a camada criada.
            nova_camada = criar_camada_linhas(
                self.iface,
                nome_camada=nome_camada,
                cor=selectedColor,                     # pode ser None se o usuário não escolheu
                crs=selectedCrs.authid()               # passamos o authid do CRS escolhido
            )

            # Atualiza a treeView
            self.atualizar_treeView_lista_linha()

    def conectar_sinal_de_visibilidade(self, layer):
        """
        Conecta sinais do `layer_tree_layer` para monitorar mudanças na visibilidade, nome, e simbologia da camada.

        Parâmetros:
        - self: Referência à instância da classe `UiManager`.
        - layer: `QgsVectorLayer` que representa a camada para a qual os sinais serão conectados.

        Atribuição:
        - Monitora e atualiza a interface do `treeView` para refletir mudanças na visibilidade, nome e simbologia da camada.

        - Obtém o `layer_tree_layer` associado à camada.
        - Conecta o sinal de mudança de visibilidade à função `atualizar_item_visibilidade`.
        - Conecta o sinal de mudança de nome à função `atualizar_nome_camada`.
        - Conecta o sinal de mudança de simbologia à função `atualizar_cor_simbologia`.
        """
        layer_tree_layer = QgsProject.instance().layerTreeRoot().findLayer(layer.id())  # Obtém o objeto `layer_tree_layer` correspondente à camada `layer` no projeto QGIS.
        if layer_tree_layer:  # Verifica se o `layer_tree_layer` foi encontrado.
            layer_tree_layer.visibilityChanged.connect(self.atualizar_item_visibilidade)  # Conecta o sinal de mudança de visibilidade à função `atualizar_item_visibilidade`.
            layer_tree_layer.nameChanged.connect(self.atualizar_nome_camada)  # Conecta o sinal de mudança de nome à função `atualizar_nome_camada`.
            layer.rendererChanged.connect(lambda: self.atualizar_cor_simbologia(layer))  # Conecta o sinal de mudança de simbologia à função `atualizar_cor_simbologia` usando uma lambda.

    def atualizar_cor_simbologia(self, layer):
        """
        Atualiza a cor associada ao item do `treeView` quando a simbologia da camada é alterada.

        Parâmetros:
        - self: Referência à instância da classe `UiManager`.
        - layer: `QgsVectorLayer` cuja cor de simbologia foi alterada e precisa ser refletida no `treeView`.

        Atribuição:
        - Garante que a cor da simbologia da camada seja imediatamente refletida no item correspondente do `treeView`.

        - Obtém o modelo do `treeView`.
        - Itera pelas linhas do modelo para encontrar o item correspondente à camada.
        - Se o item for encontrado, atualiza a cor associada no `treeView` com a nova cor da simbologia da camada.
        """
        model = self.dlg.treeViewListaLinha.model()  # Obtém o modelo associado ao `treeView`.
        for row in range(model.rowCount()):  # Itera por todas as linhas do modelo.
            item = model.item(row)  # Obtém o item na linha atual.
            if item and item.data() == layer.id():  # Verifica se o item é válido e se o ID do item corresponde ao ID da camada.
                cor_linha = self.obter_cor_linha(layer)  # Obtém a cor da linha da camada utilizando o método `obter_cor_linha`.
                item.setData(cor_linha, Qt.UserRole)  # Atualiza a cor associada ao item no `treeView`.
                break  # Interrompe o loop após encontrar e atualizar o item correspondente.

    def atualizar_nome_camada(self, layer_tree_layer):
        """
        Atualiza o nome de uma camada na visualização treeView quando o nome da camada é alterado no projeto.

        Parâmetros:
        - layer_tree_layer (QgsLayerTreeLayer): A camada do projeto cujo nome foi alterado.

        Funcionalidades:
        - Acessa o modelo de dados associado ao treeView.
        - Percorre todas as linhas do modelo para encontrar a camada correspondente pelo ID.
        - Quando a camada é encontrada, atualiza o texto do item no treeView com o novo nome da camada.
        - Interrompe a busca assim que a camada correta é atualizada, para eficiência.

        Atribuição no código:
        Essencial para manter a sincronia entre os nomes das camadas no projeto e a sua representação na interface do usuário, garantindo que as mudanças sejam refletidas imediatamente e que o usuário tenha uma visão correta e atualizada das camadas disponíveis.
        """
        model = self.dlg.treeViewListaLinha.model()
        for row in range(model.rowCount()):
            item = model.item(row)
            if item and item.data() == layer_tree_layer.layerId():
                novo_nome = layer_tree_layer.name()
                item.setText(novo_nome)
                break

    def atualizar_item_visibilidade(self, layer_tree_layer):
        """
        Atualiza o estado de visibilidade de uma camada no treeView quando o estado de visibilidade da camada é alterado no projeto.

        Parâmetros:
        - layer_tree_layer (QgsLayerTreeLayer): A camada do projeto cuja visibilidade foi alterada.

        Funcionalidades:
        - Verifica se o objeto passado é uma instância de QgsLayerTreeLayer, retornando imediatamente se não for, para evitar erros.
        - Acessa o modelo de dados associado ao treeView.
        - Percorre todas as linhas do modelo para encontrar a camada correspondente pelo ID.
        - Quando a camada é encontrada, atualiza o estado de seleção (check state) do item no treeView para refletir a nova visibilidade da camada (marcado se visível, desmarcado se não visível).
        - Interrompe a busca assim que a camada correta é atualizada, para eficiência.

        Atribuição no código:
        Essencial para manter a sincronia entre a visibilidade das camadas no projeto e a sua representação no treeView. Garante que as alterações na visibilidade das camadas sejam refletidas imediatamente na interface do usuário, permitindo uma visualização consistente do estado das camadas.
        """
        # Verifica se o objeto é uma camada na árvore de camadas
        if not isinstance(layer_tree_layer, QgsLayerTreeLayer):
            return # Não executa o resto do código se o objeto não for uma camada
        model = self.dlg.treeViewListaLinha.model() # Acessa o modelo da TreeView
        # Itera sobre as camadas na TreeView para encontrar a camada correspondente
        for row in range(model.rowCount()):
            item = model.item(row) # Acessa o item na posição atual
            # Verifica se o ID da camada corresponde e atualiza seu estado de visibilidade
            if item and item.data() == layer_tree_layer.layerId():
                # Define o estado do checkbox com base na visibilidade da camada
                item.setCheckState(Qt.Checked if layer_tree_layer.isVisible() else Qt.Unchecked)
                break  # Sai do loop após encontrar e atualizar a camada correta

    def selecionar_ultima_camada(self):
        """
        Seleciona a última camada listada no treeView.

        Funcionalidades:
        - Acessa o modelo de dados associado ao treeView.
        - Obtém o número de linhas (camadas) no modelo para determinar a quantidade de camadas presentes.
        - Se houver pelo menos uma camada no modelo, calcula o índice da última camada.
        - Define o índice atual do treeView para a última camada, efetivamente selecionando-a na interface.

        Atribuição no código:
        Esta função é útil para garantir que sempre haja uma camada selecionada no treeView, especialmente após operações que alteram o número de camadas, como a adição de uma nova camada ou a remoção de outras. Facilita a interação do usuário, mantendo sempre uma camada prontamente selecionada e visível para operações subsequentes.
        """
        model = self.dlg.treeViewListaLinha.model() # Obtém o modelo associado à QTreeView
        row_count = model.rowCount() # Conta o número de linhas (camadas) no modelo
        
        if row_count > 0:
            last_index = model.index(row_count - 1, 0) # Índice da última linha
            # Define o índice atual e seleciona o índice
            self.dlg.treeViewListaLinha.setCurrentIndex(last_index)

    def adicionar_camada_e_atualizar(self):
        """
        Cria uma nova camada de linhas e atualiza a visualização no treeView para incluir essa nova camada.

        Funcionalidades:
        - Chama a função criar_camada_linhas, que é responsável por criar e configurar uma nova camada de linhas no projeto.
        - Atualiza a árvore de visualização de camadas (treeView) chamando o método atualizar_treeView_lista_linha. Isso garante que a nova camada seja imediatamente visível na lista de camadas na interface do usuário.

        Atribuição no código:
        Essencial para a funcionalidade de adição de novas camadas no projeto. Permite ao usuário criar rapidamente uma nova camada de linhas e ver essa adição refletida na interface do usuário sem ações adicionais, melhorando a fluidez e a interação no uso do aplicativo.
        """
        # Chamada para a função que cria uma nova camada de linhas
        criar_camada_linhas(self.iface)

        # Após adicionar a camada, atualize o treeView
        self.atualizar_treeView_lista_linha()

    def criar_modelo_para_treeview(self):
        """
        Cria e configura o modelo (QStandardItemModel) a ser usado pelo QTreeView. 

        Funções e Ações Desenvolvidas:
        - Instancia um QStandardItemModel e define o texto do cabeçalho.
        - Conecta o sinal itemChanged do modelo à função on_item_changed, 
          para detectar alterações no checkbox de cada item (camada) da TreeView.
        - Associa o modelo recém-criado ao self.dlg.treeViewListaLinha.
        - Ajusta a aparência do cabeçalho chamando configurar_treeview_header().
        
        Observações Importantes:
        - A substituição da antiga conexão dataChanged -> on_data_changed 
          pela conexão itemChanged -> on_item_changed faz a lógica de sincronia 
          ficar equivalente ao UiManagerP.
        """
        self.model = QStandardItemModel() # Cria o modelo de dados para a TreeView
        self.model.setHorizontalHeaderLabels(["Lista de Camadas de Linhas"])
        self.model.itemChanged.connect(self.on_item_changed) # Define o cabeçalho da TreeView
        # Define o modelo de dados criado como o modelo a ser usado pela TreeView
        self.dlg.treeViewListaLinha.setModel(self.model)
        self.configurar_treeview_header() # Configura o cabeçalho da TreeView

    def adicionar_camadas_ao_modelo(self):
        """
        Adiciona as camadas de linha do projeto QGIS ao modelo do QTreeView.

        Funções e Ações Desenvolvidas:
        - Obtém a raiz da árvore de camadas (layerTreeRoot) do QGIS, embora não seja
          estritamente necessária na nova lógica de sincronização.
        - Percorre todas as camadas de linha retornadas por obter_camadas_de_linha().
        - Para cada camada de linha, cria um item chamando criar_item_para_camada(layer).
        - Insere o item no modelo do QTreeView (self.model.appendRow(item)).

        Observações Importantes:
        - A lógica antiga de conectar sinais de visibilidade da camada foi substituída 
          pela abordagem baseada em itemChanged + layersChanged, tal como no UiManagerP.
        """
        root = QgsProject.instance().layerTreeRoot() # Acessa a raiz da árvore de camadas do projeto QGIS
        # Itera sobre todas as camadas de linha obtidas por um método específico
        for layer in self.obter_camadas_de_linha(): # item = self.criar_item_para_camada(layer)
            item = self.criar_item_para_camada(layer) # Conecta o sinal de mudança de visibilidade da camada
            self.model.appendRow(item)

    def on_item_changed(self, item):
        """
        É acionada sempre que um item do modelo (QStandardItem) tem seu estado de
        checkbox alterado (marcado ou desmarcado), atualizando a visibilidade da
        camada no QGIS de maneira equivalente ao UiManagerP.

        Funções e Ações Desenvolvidas:
        - Obtém o ID da camada (layer_id) armazenado no item (item.data()).
        - Localiza a camada no projeto QGIS usando mapLayer(layer_id).
        - Encontra o nó correspondente na árvore de camadas (layerTreeRoot().findLayer(layer_id)).
        - Ajusta a visibilidade da camada chamando node.setItemVisibilityChecked(...)
          com base no estado do checkbox (item.checkState()).
        
        Observações Importantes:
        - Substitui a lógica anterior baseada em dataChanged e signals individuais 
          (visibilityChanged) para cada camada, simplificando a sincronização via 
          checagem e layersChanged.
        """
        # Obtém o ID da camada do próprio item
        layer_id = item.data()
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            return

        # Acha o nó da camada na árvore do QGIS
        root = QgsProject.instance().layerTreeRoot()
        node = root.findLayer(layer_id)

        if node:
            # Ajusta a visibilidade com base no estado do checkbox
            node.setItemVisibilityChecked(item.checkState() == Qt.Checked)

    def sync_from_qgis_to_treeview(self):
        """
        Sincroniza o estado do checkbox no QTreeView com a visibilidade real das
        camadas no QGIS. Equivale ao método sync_from_qgis_to_treeview do UiManagerP.

        Funções e Ações Desenvolvidas:
        - Acessa a raiz da árvore de camadas (layerTreeRoot()).
        - Itera por todas as linhas (itens) do modelo do QTreeView.
        - Para cada item, obtém o ID da camada correspondente (item.data()) e localiza
          seu nó no layerTreeRoot.
        - Verifica se a camada está visível (node.isVisible()) e ajusta o estado do 
          checkbox (item.setCheckState(Qt.Checked/Qt.Unchecked)) de acordo.

        Observações Importantes:
        - Essa função é chamada quando o sinal layersChanged do mapCanvas é disparado.
        - Garantimos, assim, que se a visibilidade for alterada em outro local (p.ex.,
          painel nativo de camadas do QGIS), o QTreeView permanecerá consistente.
        """
        root = QgsProject.instance().layerTreeRoot()

        # Percorre cada item do modelo do TreeView
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            if not item:
                continue

            layer_id = item.data()
            node = root.findLayer(layer_id)
            if node:
                # Marca/desmarca o checkbox de acordo com a visibilidade no QGIS
                item.setCheckState(Qt.Checked if node.isVisible() else Qt.Unchecked)

    def on_data_changed(self, topLeft, bottomRight, roles):
        """
        Reage a mudanças no modelo de dados do treeView, especificamente às alterações relacionadas ao estado de visibilidade das camadas (checkbox).

        Parâmetros:
        - topLeft (QModelIndex): O índice superior esquerdo da célula onde os dados foram alterados.
        - bottomRight (QModelIndex): O índice inferior direito da célula onde os dados foram alterados (não usado diretamente aqui, mas parte da assinatura da função).
        - roles (list): Lista de papéis que foram alterados; utilizado para verificar se a mudança envolve o estado do checkbox.

        Funcionalidades:
        - Verifica se a alteração envolve o 'CheckStateRole', que indica uma mudança no checkbox de visibilidade da camada.
        - Obtém o item do modelo que foi alterado a partir do índice fornecido.
        - Recupera o ID da camada associada ao item do modelo.
        - Encontra a camada correspondente no projeto QGIS usando o ID.
        - Se a camada for encontrada, sincroniza o estado de visibilidade da camada no projeto QGIS com o estado do checkbox no modelo (marcado para visível, desmarcado para invisível).

        Atribuição no código:
        Essencial para garantir que as alterações na visibilidade das camadas feitas através da interface do usuário sejam refletidas no projeto QGIS. Permite que o usuário controle a visibilidade das camadas diretamente do treeView, melhorando a interatividade e a usabilidade da interface.
        """
        # Verifica se a alteração foi no estado do checkbox (visibilidade)
        if Qt.CheckStateRole in roles: # A mudança é relevante para a visibilidade da camada?
            item = topLeft.model().itemFromIndex(topLeft) # Obtém o item alterado
            layer_id = item.data() # Recupera o ID da camada associada ao item
            layer_tree = QgsProject.instance().layerTreeRoot().findLayer(layer_id) # Encontra a camada no projeto
            # Atualiza a visibilidade da camada no projeto QGIS
            if layer_tree:
                layer_tree.setItemVisibilityChecked(item.checkState() == Qt.Checked) # Sincroniza a visibilidade

    def configurar_treeview_header(self):
        """
        Configura o cabeçalho do treeView, definindo o alinhamento padrão do texto do cabeçalho.

        Funcionalidades:
        - Acessa o cabeçalho do treeView, que é a parte superior da visualização onde os títulos das colunas são exibidos.
        - Define o alinhamento padrão do texto do cabeçalho para centralizado (Qt.AlignCenter), garantindo que os títulos das colunas sejam apresentados de forma clara e esteticamente agradável.

        Atribuição no código:
        Melhora a legibilidade e a aparência da interface do usuário, contribuindo para uma experiência visual mais organizada e profissional. Essa configuração é fundamental para manter um padrão visual consistente em toda a aplicação.
        """
        # Acessa o cabeçalho da TreeView
        header = self.dlg.treeViewListaLinha.header()
        # Define o alinhamento padrão para o texto do cabeçalho
        header.setDefaultAlignment(Qt.AlignCenter)

    def obter_camadas_de_linha(self):
        """
        Itera sobre todas as camadas no projeto QGIS e retorna aquelas que são camadas de linha.

        Funcionalidades:
        - Acessa todas as camadas atualmente carregadas no projeto QGIS através do método mapLayers() do QgsProject.
        - Verifica cada camada para determinar se ela é uma camada de linha utilizando o método eh_camada_de_linha, que compara o tipo da geometria da camada com o tipo de geometria de linha.
        - Se a camada for identificada como uma camada de linha, ela é retornada para o chamador através do uso de 'yield', permitindo que a função seja usada em um loop para processar apenas camadas de linha.

        Atribuição no código:
        Essencial para filtrar e trabalhar especificamente com camadas de linha dentro de uma variedade de camadas em um projeto QGIS. Facilita a implementação de funcionalidades que dependem exclusivamente de manipulação ou visualização de camadas de linha, como análises topológicas ou estilização baseada em atributos específicos de linha.
        """
        # Itera sobre todas as camadas no projeto QGIS
        for layer in QgsProject.instance().mapLayers().values():
            # Verifica se a camada é uma camada de linha
            if self.eh_camada_de_linha(layer):
                yield layer # Retorna a camada se ela for uma camada de linha

    def eh_camada_de_linha(self, layer):
        """
        Determina se uma camada especificada é uma camada de linha dentro do projeto QGIS.

        Parâmetros:
        - layer (QgsMapLayer): A camada que está sendo verificada.

        Funcionalidades:
        - Verifica se o tipo da camada é VectorLayer, indicando que a camada é uma camada vetorial.
        - Adicionalmente, verifica se o tipo de geometria da camada é LineGeometry, confirmando que a camada consiste em geometrias de linha.
        - Retorna True se ambas as condições forem atendidas, indicando que a camada é uma camada de linha, ou False caso contrário.

        Atribuição no código:
        Fundamental para filtrar e manipular apenas as camadas de linha dentro de várias funcionalidades do sistema, como análises específicas para linhas, operações de visualização ou processamento de dados de linha. Permite que a aplicação trate de forma eficiente e específica as camadas baseadas em sua tipologia geométrica, otimizando o desempenho e a precisão das operações realizadas.
        """
        # Verifica se o tipo da camada é VectorLayer e o tipo de geometria é LineGeometry
        return layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.LineGeometry

    def criar_item_para_camada(self, layer):
        """
        Cria um item de visualização para uma camada específica para ser usado no modelo do treeView.

        Parâmetros:
        - layer (QgsMapLayer): A camada para a qual o item será criado.

        Funcionalidades:
        - Cria um novo item QStandardItem com o nome da camada como texto de exibição.
        - Configura o item com propriedades adicionais, como o estado de seleção (checkable), através do método configurar_item. Esse método também ajusta propriedades de visibilidade e edição.
        - Obtém a cor associada à camada usando o método obter_cor_linha, que busca a cor atual da representação da camada no mapa.
        - Define a cor obtida como um dado adicional do item, usando o Qt.UserRole para armazenar essa informação, permitindo que a cor seja utilizada em outros contextos da interface, como na customização da exibição.

        Atribuição no código:
        Essencial para a representação visual de cada camada dentro do treeView. Permite uma personalização detalhada de como cada camada é apresentada ao usuário, facilitando a identificação visual das camadas através de suas cores. Também assegura que as propriedades essenciais de cada camada sejam acessíveis para manipulação através da interface do usuário, como a visibilidade e a edição do nome.
        """
        # Cria um novo item com o nome da camada
        item = QStandardItem(layer.name())
        # Configura o item com propriedades adicionais (como o estado de seleção)
        self.configurar_item(item, layer)
        # Obtém a cor associada à camada e a define como um dado do item
        cor_linha = self.obter_cor_linha(layer)
        item.setData(cor_linha, Qt.UserRole)  # Define a cor da linha como um dado do item
        return item # Retorna o item configurado

    def configurar_item(self, item, layer):
        """
        Configura as propriedades de um item QStandardItem para refletir as características e o estado de uma camada específica no treeView.

        Parâmetros:
        - item (QStandardItem): O item a ser configurado no modelo do treeView.
        - layer (QgsMapLayer): A camada associada ao item, cujas propriedades influenciarão a configuração do item.

        Funcionalidades:
        - Torna o item selecionável com um checkbox, permitindo que o usuário altere a visibilidade da camada diretamente através do treeView.
        - Armazena o ID da camada como um dado do item para facilitar a identificação e manipulação posterior da camada através do item.
        - Desabilita a capacidade de arrastar o item para evitar reordenamento ou movimentação inapropriada do item no treeView.
        - Define o estado inicial do checkbox do item com base na visibilidade atual da camada, garantindo que o estado do checkbox reflita corretamente o estado de visibilidade da camada.
        - Remove a capacidade de editar o texto do item para manter a integridade do nome da camada como fornecido pelo sistema ou pelo usuário.
        - Configura a fonte do item com base em propriedades específicas da camada, como itálico para camadas temporárias e negrito para outras, ajudando na distinção visual das camadas no treeView.

        Atribuição no código:
        Essencial para a representação adequada das camadas dentro do treeView, garantindo que os itens reflitam de forma precisa e útil as propriedades e o estado das camadas associadas. Facilita a interação do usuário com as camadas, oferecendo controles visuais intuitivos para visibilidade e organização.
        """
        # Torna o item selecionável (checkable)
        item.setCheckable(True)
        # Armazena o ID da camada como um dado do item
        item.setData(layer.id())
        # Desabilita a capacidade de arrastar o item (drag)
        item.setDragEnabled(False)
        # Define o estado do checkbox do item com base na visibilidade da camada
        item.setCheckState(Qt.Checked if self.camada_esta_visivel(layer) else Qt.Unchecked)
        # Remove a possibilidade de editar o texto do item
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        # Define a fonte do item com base em propriedades específicas da camada
        item.setFont(self.obter_fonte_para_camada(layer))

    def camada_esta_visivel(self, layer):
        """
        Verifica se uma camada específica está visível no projeto QGIS.

        Parâmetros:
        - layer (QgsMapLayer): A camada que está sendo verificada quanto à sua visibilidade.

        Funcionalidades:
        - Encontra a representação da camada na árvore de camadas do projeto QGIS usando o ID da camada.
        - Retorna True se a camada estiver visível, ou False se não estiver visível ou se a camada não puder ser encontrada na árvore de camadas. Isso é determinado verificando a propriedade de visibilidade da camada na árvore de camadas.

        Atribuição no código:
        Essencial para controlar a visibilidade das camadas dentro de operações que dependem da exibição da camada no projeto. Permite a sincronização do estado de visibilidade das camadas no modelo do treeView com o estado real no projeto QGIS, garantindo que as operações de interface refletem precisamente o estado de visibilidade das camadas.
        """
        # Encontra a camada na árvore de camadas do projeto
        layer_tree_layer = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
        
        # Retorna True se a camada estiver visível, caso contrário, retorna False
        return layer_tree_layer.isVisible() if layer_tree_layer else False

    def obter_fonte_para_camada(self, layer):
        """
        Determina a fonte apropriada para um item no treeView com base no tipo de provedor de dados da camada associada.

        Parâmetros:
        - layer (QgsMapLayer): A camada cujas propriedades do provedor de dados influenciam a estilização da fonte do item no treeView.

        Funcionalidades:
        - Cria um objeto QFont para definir as propriedades da fonte.
        - Configura a fonte para ser itálica se o provedor de dados da camada for 'memory', indicativo de que a camada é temporária e armazenada apenas na memória.
        - Configura a fonte para ser negrito se o provedor de dados da camada não for 'memory', destacando camadas que são persistentes e possivelmente armazenadas em fontes de dados externas ou permanentes.
        - Retorna o objeto QFont configurado, pronto para ser aplicado ao item representativo da camada no treeView.

        Atribuição no código:
        Essencial para fornecer um feedback visual imediato sobre o tipo de armazenamento das camadas no treeView, facilitando a distinção entre camadas temporárias e permanentes. Esta diferenciação ajuda os usuários a entenderem rapidamente a natureza da camada sem a necessidade de inspeção adicional, melhorando a usabilidade e a eficiência da interface do usuário.
        """
        fonte_item = QFont()
        # Define o estilo da fonte com base no tipo de camada (memória ou não)
        fonte_item.setItalic(layer.dataProvider().name() == 'memory')
        fonte_item.setBold(layer.dataProvider().name() != 'memory')
        return fonte_item

    def on_treeViewItem_doubleClicked(self, index):
        """
        Responde a eventos de duplo clique em um item no treeView, permitindo ao usuário alterar a cor da linha da camada correspondente.

        Parâmetros:
        - index (QModelIndex): O índice do item no modelo do treeView que foi duplamente clicado.

        Funcionalidades:
        - Obtém o ID da camada associada ao item clicado no treeView, permitindo a recuperação da camada correspondente no projeto QGIS.
        - Verifica se a camada existe e, em caso afirmativo, recupera a cor atual da linha da camada usando o método obter_cor_linha.
        - Abre um diálogo de seleção de cor pré-configurado com a cor atual da linha, permitindo ao usuário escolher uma nova cor para a linha da camada.
        - Se o usuário selecionar uma cor válida (isto é, não cancelar o diálogo), aplica a nova cor à linha da camada usando o método aplicar_cor_linha.

        Atribuição no código:
        Proporciona uma interação direta e intuitiva para personalizar a aparência das camadas de linha no projeto QGIS diretamente através da interface do usuário. Este método melhora significativamente a experiência do usuário ao permitir ajustes visuais rápidos e eficientes, facilitando a personalização da representação das camadas no mapa.
        """
        # Obtém o ID da camada a partir do índice
        layer_id = index.model().itemFromIndex(index).data()
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:
            # Obtém a cor atual da linha da camada
            cor_atual = self.obter_cor_linha(layer)
            # Abre um diálogo de seleção de cor e permite que o usuário escolha uma nova cor
            cor_selecionada = QColorDialog.getColor(cor_atual, self.dlg, "Escolher Cor da Linha")
            
            if cor_selecionada.isValid():
                # Aplica a nova cor à linha da camada
                self.aplicar_cor_linha(layer, cor_selecionada)

    def obter_cor_linha(self, layer):
        """
        Retorna a cor atual da linha para uma camada específica no projeto QGIS, com base no tipo de renderizador que a camada usa.

        Parâmetros:
        - layer (QgsMapLayer): A camada para a qual a cor da linha será obtida.

        Funcionalidades:
        - Obtém o renderizador associado à camada. O tipo de renderizador determina como as características visuais da camada são geradas e gerenciadas.
        - Verifica se o renderizador é do tipo QgsSingleSymbolRenderer, que usa um único símbolo para todas as feições da camada. Se for, retorna a cor desse símbolo.
        - Caso o renderizador seja do tipo QgsCategorizedSymbolRenderer, que usa diferentes símbolos baseados em categorias de feições, tenta retornar a cor do símbolo da primeira categoria, assumindo que categorias estão definidas e presentes.
        - Se nenhuma dessas condições for satisfeita ou se não houver categorias definidas para um renderizador categorizado, retorna uma cor padrão (preto), como fallback.

        Atribuição no código:
        Essencial para operações que requerem manipulação ou exibição da cor da linha de uma camada, como ajustes de estilo ou quando se está customizando a representação gráfica de camadas no mapa. Facilita a sincronização visual entre a interface do usuário e as propriedades visuais das camadas no projeto.
        """
        # Obtém o renderizador da camada
        renderer = layer.renderer()
        cor_default = QColor(0, 0, 0)  # Cor padrão (preto)
        # Verifica se o renderizador é do tipo QgsSingleSymbolRenderer
        if isinstance(renderer, QgsSingleSymbolRenderer):
            return renderer.symbol().color()
        # Verifica se o renderizador é do tipo QgsCategorizedSymbolRenderer
        elif isinstance(renderer, QgsCategorizedSymbolRenderer):
            # Se a camada usa categorias, pegue a cor da primeira categoria
            if renderer.categories(): # Verifica se existem categorias no renderizador
                # Retorna a cor do símbolo da primeira categoria
                return renderer.categories()[0].symbol().color() 
        return cor_default # Retorna a cor preta padrão se nenhum caso acima se aplicar

    def aplicar_cor_linha(self, layer, nova_cor):
        """
        Aplica uma nova cor à simbologia da camada de linha especificada,
        garantindo que a cor seja modificada corretamente independentemente do tipo de renderer atual.

        Funcionalidades e Ações Desenvolvidas:
        - Detecta o tipo de renderer (simbologia) atual da camada (SingleSymbol, Categorized, RuleBased, ou outro).
        - Para cada tipo de renderer, aplica a cor fornecida (`nova_cor`) da forma apropriada:
            - Se for um `QgsSingleSymbolRenderer`: modifica diretamente a cor do símbolo.
            - Se for um `QgsCategorizedSymbolRenderer`: modifica a cor de cada categoria individualmente.
            - Se for um `QgsRuleBasedRenderer`: percorre todas as regras e aplica a nova cor a cada símbolo.
            - Se o renderer for de tipo desconhecido ou não manipulável diretamente, 
              força a substituição por um novo `QgsSingleSymbolRenderer` com a cor desejada.
        - Garante que a camada seja redesenhada após a mudança de simbologia com `triggerRepaint()`.
        - Atualiza a visualização da simbologia no painel de camadas do QGIS usando `refreshLayerSymbology(...)`.
        - Reatualiza a árvore `treeViewListaLinha` da interface, caso a cor esteja sendo refletida visualmente ali.

        Motivação:
        - Essa abordagem é necessária especialmente para camadas importadas de arquivos como KML,
          que podem vir com simbologias embutidas complexas ou não-editáveis diretamente.
        - Ao tratar todos os tipos de renderers, inclusive os que não suportam edição direta,
          garantimos que o usuário sempre poderá alterar a cor da camada com sucesso.

        Parâmetros:
        - layer (QgsVectorLayer): A camada de linha que terá sua cor modificada.
        - nova_cor (QColor): A nova cor a ser aplicada à simbologia da camada.
        """
        renderer = layer.renderer()

        # Se for um renderer de Linhas SIMPLES (SingleSymbolRenderer)
        if isinstance(renderer, QgsSingleSymbolRenderer):
            symbol = renderer.symbol()
            symbol.setColor(nova_cor)
            layer.setRenderer(renderer)

        # Se for um renderer CATEGORIZADO
        elif isinstance(renderer, QgsCategorizedSymbolRenderer):
            for categoria in renderer.categories():
                categoria.symbol().setColor(nova_cor)
            layer.setRenderer(renderer)

        # Se for um renderer BASEADO EM REGRAS (RuleBasedRenderer)
        elif isinstance(renderer, QgsRuleBasedRenderer):
            # Vamos iterar por todas as rules e alterar as cores
            root_rule = renderer.rootRule()
            if root_rule:
                for rule in root_rule.children():
                    symbol = rule.symbol()
                    if symbol:
                        symbol.setColor(nova_cor)
            layer.setRenderer(renderer)

        else:
            # Se for qualquer outro tipo de renderer, forçamos
            # um SingleSymbolRenderer para garantir a mudança de cor.
            symbol = QgsLineSymbol.createSimple({'color': nova_cor.name()})
            novo_renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(novo_renderer)

        # Reforçar o "repaint" e atualizar a symbologia no painel
        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

        # Caso você queira também forçar a atualização no seu QTreeView
        # (para o caso de exibir a cor ali de alguma forma)
        self.atualizar_treeView_lista_linha()

    def sincronizar_selecao_com_qgis(self, layer):
        """
        Sincroniza a seleção atual no treeView da interface do usuário com a camada ativa no projeto QGIS.

        Parâmetros:
        - layer (QgsMapLayer): A camada que se tornou ativa no QGIS e que deve ser refletida como selecionada no treeView.

        Funcionalidades:
        - Verifica se a camada fornecida é nula, interrompendo a função se for o caso, para evitar erros.
        - Obtém o modelo de dados associado ao treeView, que lista as camadas.
        - Itera sobre todas as linhas (itens) do modelo para encontrar o item correspondente à camada ativa.
        - Verifica se o item existe no modelo e se o ID da camada associada ao item corresponde ao ID da camada ativa.
        - Se um item correspondente for encontrado, obtém o índice desse item no modelo.
        - Define o índice atual no treeView para o índice do item encontrado, efetivamente selecionando o item na interface do usuário.

        Atribuição no código:
        Essencial para manter a consistência entre a camada selecionada na interface do usuário e a camada ativa no projeto QGIS. Facilita a usabilidade e melhora a interação do usuário, garantindo que as mudanças de contexto no QGIS sejam imediatamente refletidas na interface, ajudando o usuário a identificar qual camada está atualmente ativa e sendo manipulada.
        """
        # Verifica se a camada é nula
        if layer is None:
            return
        # Obtém o modelo da árvore de camadas
        model = self.dlg.treeViewListaLinha.model()
        # Itera sobre as linhas do modelo
        for row in range(model.rowCount()):
            item = model.item(row)
            # Verifica se o item existe e se corresponde à camada atual
            if item and item.data() == layer.id():
                index = model.indexFromItem(item)  # Obtém o índice do item
                # Define o índice atual na árvore de camadas como o índice do item
                self.dlg.treeViewListaLinha.setCurrentIndex(index)
                break

    def on_treeViewItem_clicked(self, index):
        """
        Ativa a camada correspondente no projeto QGIS quando um item é clicado no treeView da interface do usuário.

        Parâmetros:
        - index (QModelIndex): O índice do item no treeView que foi clicado.

        Funcionalidades:
        - Obtém o ID da camada a partir do dado associado ao item no índice especificado, que é armazenado no modelo do treeView.
        - Usa esse ID para obter a camada correspondente do projeto QGIS.
        - Verifica se a camada obtida realmente existe para evitar erros caso o índice seja inválido ou a camada tenha sido removida.
        - Se a camada existe, define essa camada como a camada ativa no QGIS, permitindo que o usuário interaja com ela diretamente através das ferramentas e menus do QGIS.

        Atribuição no código:
        Essencial para garantir que a interação do usuário com a lista de camadas no treeView seja refletida no contexto de trabalho do QGIS. Isso facilita a gestão de camadas, permitindo que o usuário selecione rapidamente diferentes camadas para visualização ou edição, melhorando a eficiência e a usabilidade da interface do usuário.
        """
        # Obtém o ID da camada a partir do índice do item
        layer_id = index.model().itemFromIndex(index).data()
        # Obtém a camada correspondente com base no ID
        layer = QgsProject.instance().mapLayer(layer_id)
        
        # Verifica se a camada existe
        if layer:
            # Define a camada como ativa no QGIS
            self.iface.setActiveLayer(layer)

    def remover_camada_selecionada(self):
        """
        Remove a camada selecionada no treeView após verificar o estado de edição e as mudanças pendentes, solicitando ao usuário que salve as alterações se necessário.

        Funcionalidades:
        - Obtém os índices selecionados no treeView. Se um índice estiver selecionado, identifica a camada associada ao item selecionado.
        - Verifica se a camada está atualmente em um estado editável com mudanças não salvas. Se estiver, apresenta uma caixa de diálogo perguntando se o usuário deseja salvar as mudanças antes de remover a camada.
        - Se o usuário optar por salvar, tenta salvar a camada usando o método `salvar_camada_como`. Se o usuário confirmar o salvamento e este for bem-sucedido, a camada é removida do projeto QGIS.
        - Se o usuário optar por não salvar, descarta as mudanças pendentes e desliga a edição antes de remover a camada do projeto.
        - Se o usuário cancelar a ação, a remoção é abortada.
        - Se a camada não estiver editável ou não tiver mudanças pendentes, remove a camada diretamente do projeto.
        - Após a remoção da camada, atualiza o treeView para refletir a alteração na lista de camadas.

        Atribuição no código:
        Essencial para a gestão segura das camadas dentro do projeto, garantindo que mudanças importantes não sejam perdidas inadvertidamente e que o usuário tenha controle total sobre as operações de edição e remoção de camadas. Melhora a usabilidade e segurança do sistema ao lidar com dados potencialmente críticos.
        """
        selected_indexes = self.dlg.treeViewListaLinha.selectedIndexes()
        if selected_indexes:
            selected_index = selected_indexes[0]
            layer_id = selected_index.model().itemFromIndex(selected_index).data()
            layer_to_remove = QgsProject.instance().mapLayer(layer_id)
            if layer_to_remove:
                # Se a camada estiver editável e com mudanças pendentes, pergunte se o usuário quer salvar
                if layer_to_remove.isEditable() and layer_to_remove.isModified():
                    resposta = QMessageBox.question(
                        self.dlg, "Confirmar Remoção",
                        "Existem alterações não salvas, deseja salvar antes de Remover?",
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                        QMessageBox.Yes)
                    
                    if resposta == QMessageBox.Yes:
                        if self.salvar_camada_como():  # Se o usuário salvou a camada com sucesso
                            QgsProject.instance().removeMapLayer(layer_id)  # Remove a camada
                        else:
                            return  # O usuário cancelou o salvamento
                    elif resposta == QMessageBox.No:
                        layer_to_remove.rollBack()  # Descarta as mudanças
                        self.iface.actionToggleEditing().trigger()  # Desliga a edição
                        QgsProject.instance().removeMapLayer(layer_id)  # Remove a camada
                    elif resposta == QMessageBox.Cancel:
                        return  # Ação cancelada pelo usuário
                else:
                    # Se a camada não estiver editável ou não tiver mudanças pendentes, remova diretamente
                    QgsProject.instance().removeMapLayer(layer_id)
                    self.atualizar_treeView_lista_linha()
                    self.iface.mapCanvas().refresh()

    def renomear_camada_selecionada(self):
        """
        Permite ao usuário renomear uma camada selecionada no treeView através de uma caixa de diálogo, garantindo que o nome seja único dentro do projeto.

        Funcionalidades:
        - Obtém os índices selecionados no treeView. Se um índice estiver selecionado, identifica a camada associada ao item selecionado.
        - Se uma camada estiver associada ao item selecionado, exibe uma caixa de diálogo que solicita ao usuário um novo nome para a camada, pré-preenchendo o campo de entrada com o nome atual da camada.
        - Verifica se o usuário confirmou a ação e forneceu um novo nome. Se sim, chama a função `gerar_nome_unico` para ajustar o nome para um formato único dentro do projeto.
        - Define o novo nome para a camada no projeto QGIS e atualiza o texto do item correspondente no treeView para refletir o novo nome.

        Atribuição no código:
        Essencial para a administração eficaz das camadas, permitindo ao usuário personalizar os nomes das camadas de acordo com suas necessidades e garantindo que não haja conflitos de nomeação dentro do projeto. Facilita a organização e a identificação das camadas, melhorando a gestão de dados e a experiência do usuário ao trabalhar com múltiplas camadas.
        """
        selected_indexes = self.dlg.treeViewListaLinha.selectedIndexes()
        if selected_indexes:
            selected_index = selected_indexes[0]
            layer_id = selected_index.model().itemFromIndex(selected_index).data()
            selected_layer = QgsProject.instance().mapLayer(layer_id)
            if selected_layer:
                novo_nome, ok = QInputDialog.getText(
                    self.dlg,
                    "Renomear Camada",
                    "Digite o novo nome da camada:",
                    text=selected_layer.name())
                if ok and novo_nome:
                    novo_nome = self.gerar_nome_unico(novo_nome, selected_layer.id())
                    selected_layer.setName(novo_nome)
                    selected_index.model().itemFromIndex(selected_index).setText(novo_nome)

    def gerar_nome_unico(self, base_nome, current_layer_id):
        """
        Gera um nome único para uma camada dentro do projeto QGIS, assegurando que não haja conflitos de nomeação com outras camadas existentes.

        Parâmetros:
        - base_nome (str): O nome base proposto para a camada.
        - current_layer_id (str): O ID da camada que está sendo renomeada, usado para excluir seu nome atual da verificação de duplicidade.

        Funcionalidades:
        - Cria um dicionário dos nomes de todas as camadas existentes no projeto QGIS, excluindo a camada que está sendo renomeada, para evitar considerar seu próprio nome como duplicado.
        - Verifica se o nome base já existe entre as camadas. Se não existir, retorna o nome base como um nome válido.
        - Se o nome base já existir, gera variações do nome acrescentando um sufixo numérico (por exemplo, "Nome_1", "Nome_2") até encontrar um nome não utilizado.
        - Retorna o novo nome único gerado.

        Atribuição no código:
        Essencial para prevenir problemas de gerenciamento de dados causados por nomes duplicados de camadas. A função apoia operações de renomeação e criação de camadas, garantindo que cada camada possa ser identificada de forma única dentro do projeto. Isso melhora a organização do projeto e previne erros de referência entre camadas.
        """
        existing_names = {layer.name(): layer.id() for layer in QgsProject.instance().mapLayers().values() if layer.id() != current_layer_id}
        if base_nome not in existing_names:
            return base_nome
        else:
            i = 1
            novo_nome = f"{base_nome}_{i}"
            while novo_nome in existing_names:
                i += 1
                novo_nome = f"{base_nome}_{i}"
            return novo_nome

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

    def salvar_camada_como(self):
        """
        Permite ao usuário salvar uma camada selecionada em um formato de arquivo específico através de uma caixa de diálogo interativa.

        Funcionalidades:
        - Obtém o índice da camada selecionada no treeView. Se uma camada estiver selecionada, recupera o ID dessa camada.
        - Usa o ID para obter a camada correspondente do projeto QGIS.
        - Apresenta uma caixa de diálogo que permite ao usuário escolher entre vários formatos de arquivo para salvar a camada, como DXF, KML, Shapefile, GeoJSON, CSV, TXT, Excel e Geopackage.
        - Se o usuário confirmar a escolha de um formato, tenta salvar a camada no formato escolhido usando a função `salvar_no_formato_especifico`, que gerencia o processo de salvamento baseado no formato.
        - Retorna True se o arquivo for salvo com sucesso, False se o usuário cancelar a caixa de diálogo ou se ocorrer um erro no salvamento.

        Atribuição no código:
        Essencial para proporcionar flexibilidade no gerenciamento de dados geoespaciais, permitindo que o usuário exporte camadas para diferentes formatos conforme necessário para uso em outros softwares ou para backup. Esta funcionalidade aumenta a utilidade do sistema, oferecendo suporte a diversas operações de compartilhamento e publicação de dados geográficos.
        """
        selected_indexes = self.dlg.treeViewListaLinha.selectedIndexes()
        if selected_indexes:
            selected_index = selected_indexes[0]
            layer_id = selected_index.model().itemFromIndex(selected_index).data()
            layer_to_save = QgsProject.instance().mapLayer(layer_id)
            if layer_to_save:
                # Adicione a opção para salvar como
                formatos = {"DXF": ".dxf", "KML": ".kml", "Shapefile": ".shp", "GeoJSON": ".geojson", "CSV": ".csv", "TXT": ".txt", "Excel": ".xlsx", "Geopackage": ".gpkg"}
                formato, ok = QInputDialog.getItem(
                    self.dlg, "Salvar Como", "Escolha o formato de arquivo:", formatos.keys(), 0, False)
                if ok and formato:
                    # Substitua esta linha pelo seu código real de salvamento
                    resultado_salvar = True  # ou False, dependendo do sucesso do salvamento

                    return self.salvar_no_formato_especifico(layer_to_save, formatos[formato])
                else:
                    return False  # Usuário cancelou o diálogo
            else:
                return False
        return False

    def salvar_como_txt(self, layer, fileName):
        """
        Salva a camada especificada em um arquivo de texto (.txt) delimitado por tabulações, incluindo todos os campos e feições da camada.

        Parâmetros:
        - layer (QgsVectorLayer): A camada do QGIS que será salva no arquivo.
        - fileName (str): O caminho completo do arquivo onde a camada será salva.

        Funcionalidades:
        - Abre o arquivo especificado em modo de escrita, configurando para usar a codificação UTF-8 e para não adicionar novas linhas automaticamente.
        - Utiliza o módulo csv para criar um escritor que delimita os dados com tabulações.
        - Obtém os campos da camada e escreve os nomes dos campos como cabeçalho do arquivo.
        - Itera sobre cada feição da camada, escrevendo seus atributos no arquivo.
        - Exibe uma mensagem de sucesso na interface do usuário se o arquivo for salvo com sucesso.
        - Em caso de erro durante o salvamento, captura a exceção, exibe uma mensagem de erro na interface do usuário e retorna False.

        Atribuição no código:
        Proporciona uma maneira eficiente e direta de exportar dados geoespaciais para um formato .txt
        """
        try:
            # Abre o arquivo para escrita, configurando para não adicionar novas linhas e usando UTF-8
            with open(fileName, 'w', newline='', encoding='utf-8') as txtfile:
                writer = csv.writer(txtfile, delimiter='\t')  # Cria um objeto writer para csv delimitado por tabulações
                fields = layer.fields()  # Obtém os campos da camada
                writer.writerow([field.name() for field in fields])  # Escreve o cabeçalho com os nomes dos campos
                
                # Itera sobre cada feição da camada
                for feature in layer.getFeatures():
                    writer.writerow(feature.attributes())  # Escreve os atributos de cada feição

            # Exibe uma mensagem de sucesso se não houver exceções
            self.mostrar_mensagem("Camada salva como TXT com sucesso.", "Sucesso")
            return True
        except Exception as e:
            # Captura qualquer exceção que ocorra durante o processo de escrita e exibe uma mensagem de erro
            self.mostrar_mensagem(f"Erro ao salvar a camada como TXT: {e}", "Erro")
            return False

    def salvar_como_xlsx(self, layer, fileName):
        """
        Salva os atributos de uma camada QGIS em um arquivo Excel (XLSX).
        
        Funções e Ações Desenvolvidas:
        - Cria um novo livro do Excel e seleciona a planilha ativa.
        - Escreve o nome de cada campo da camada como cabeçalho da planilha.
        - Itera sobre cada feição da camada e escreve seus atributos nas linhas subsequentes da planilha.
        - Salva o livro do Excel no caminho especificado.
        - Exibe uma mensagem de sucesso ou erro após a tentativa de salvar os dados.

        Args:
        - layer: A camada QGIS da qual os dados são extraídos.
        - fileName: O nome do arquivo para o qual os dados serão salvos (deve terminar em .xlsx).

        Returns:
        - True se os dados forem salvos com sucesso, False caso contrário.
        """
        try:
            # Cria um novo livro do Excel
            workbook = openpyxl.Workbook()
            sheet = workbook.active  # Seleciona a planilha ativa

            # Obtém os campos da camada e escreve como cabeçalho da planilha
            fields = layer.fields()
            sheet.append([field.name() for field in fields])  # Adiciona os nomes dos campos como cabeçalho

            # Itera sobre cada feição da camada
            for feature in layer.getFeatures():
                sheet.append(feature.attributes())  # Adiciona os atributos de cada feição na planilha

            # Salva o livro do Excel no caminho especificado
            workbook.save(fileName)

            # Exibe uma mensagem de sucesso
            self.mostrar_mensagem("Camada salva como XLSX com sucesso.", "Sucesso")
            return True
        except Exception as e:
            # Captura qualquer exceção que ocorra durante o processo e exibe uma mensagem de erro
            self.mostrar_mensagem(f"Erro ao salvar a camada como XLSX: {e}", "Erro")
            return False

    def salvar_no_formato_especifico(self, layer, extensao, nome_arquivo=None):
        """
        Salva uma camada QGIS em um formato de arquivo específico escolhido pelo usuário, com suporte para vários formatos comuns.
        
        Funções e Ações Desenvolvidas:
        - Determina o tipo de arquivo e o nome do driver baseado na extensão fornecida.
        - Oferece ao usuário a possibilidade de escolher um local para salvar o arquivo se o nome do arquivo não for fornecido.
        - Checa se o arquivo já existe para evitar sobreposições e renomeia o arquivo se necessário.
        - Invoca funções específicas de salvamento baseadas na extensão do arquivo.
        
        Args:
        - layer: A camada QGIS que será salva.
        - extensao: A extensão do arquivo que indica o formato desejado.
        - nome_arquivo: O caminho completo do arquivo para salvar. Se None, será solicitado ao usuário.

        Returns:
        - True se o arquivo for salvo com sucesso, False se o salvamento falhar ou for cancelado.
        """
        # Mapeia as extensões para os tipos de arquivo correspondentes e seus drivers
        tipos_de_arquivo = {
            ".dxf": ("DXF Files (*.dxf)", "DXF"),
            ".kml": ("KML Files (*.kml)", "KML"),
            ".shp": ("Shapefile Files (*.shp)", "ESRI Shapefile"),
            ".txt": ("Text Files (*.txt)", "TXT"),
            ".csv": ("CSV Files (*.csv)", "CSV"),
            ".geojson": ("GeoJSON Files (*.geojson)", "GeoJSON"),
            ".gpkg": ("Geopackage Files (*.gpkg)", "GPKG"),
            ".xlsx": ("Excel Files (*.xlsx)", "XLSX")}
            
        tipo_arquivo, driver_name = tipos_de_arquivo.get(extensao, ("", ""))

        if tipo_arquivo:
            if nome_arquivo is None:  # Se o nome do arquivo não foi fornecido, abra o diálogo para escolher o local para salvar
                nome_arquivo = self.escolher_local_para_salvar(
                    os.path.join(self.ultimo_caminho_salvo, layer.name() + extensao), tipo_arquivo)

            # Checagem e renomeação do arquivo, se necessário
            if nome_arquivo:
                base_nome_arquivo = os.path.splitext(nome_arquivo)[0]
                contador = 1
                while os.path.exists(nome_arquivo):  # Se o arquivo já existir
                    nome_arquivo = f"{base_nome_arquivo}_{contador}{extensao}"
                    contador += 1 
                    
                if nome_arquivo and not nome_arquivo.endswith(extensao):
                    nome_arquivo += extensao

            if nome_arquivo:  # Se o nome do arquivo foi fornecido ou escolhido, proceda com o salvamento
                if extensao == ".txt":
                    return self.salvar_como_txt(layer, nome_arquivo)
                elif extensao == ".xlsx":
                    return self.salvar_como_xlsx(layer, nome_arquivo)
                else:
                    return self.salvar_camada(layer, nome_arquivo, driver_name)
            else:
                return False  # O usuário cancelou o diálogo ou ocorreu um erro
        else:
            return False # Extensão não suportada

        # Atualiza o último caminho de salvamento usado
        self.ultimo_caminho_salvo = os.path.dirname(nome_arquivo)

    def tratar_linhas(self, new_layer):
        """
        Configura sinais e comportamentos personalizados para uma nova camada de linhas, incluindo a atualização do comprimento das linhas e a geração automática de IDs.

        Parâmetros:
        - new_layer (QgsVectorLayer): A camada recém-criada ou modificada que precisa de configuração adicional.

        Funcionalidades:
        - Conecta um sinal para atualizar automaticamente o comprimento das linhas quando novas feições são adicionadas ou quando a geometria das feições existentes é alterada.
        - Conecta um sinal para definir um novo ID automaticamente quando novas feições são adicionadas, garantindo que cada feição tenha um identificador único.
        - Oculta todos os campos exceto o campo ID na interface de usuário da camada, para simplificar a visualização e edição de feições na camada.
        - Inicia a edição da camada e atualiza o campo de comprimento ('Comprimento') para todas as feições existentes baseado em suas geometrias, e depois salva as alterações.

        Atribuição no código:
        Essencial para garantir que as camadas de linhas estejam configuradas com todas as funcionalidades necessárias para um gerenciamento eficaz dentro do projeto QGIS. Automatiza a manutenção de atributos críticos como o comprimento e o ID das feições, o que é crucial para análises subsequentes e para a integridade dos dados. 
        Facilita a administração de camadas ao reduzir a necessidade de ajustes manuais frequentes pelos usuários.
        """
        # Conecta o sinal para atualizar o comprimento das linhas quando novas feições são adicionadas
        new_layer.featureAdded.connect(lambda fid: self.atualizar_comprimento_linha(new_layer, fid))
        # Conecta o sinal para atualizar o comprimento das linhas depois de tornar Permanente
        new_layer.geometryChanged.connect(lambda fid, geom: self.atualizar_comprimento_linha(new_layer, fid))

        # Conecta o sinal para tratar a adição de novas feições de forma personalizada
        new_layer.featureAdded.connect(lambda fid: self.definir_novo_id(new_layer, fid))

        # Configura todos os campos para serem ocultados, exceto o campo ID
        fields = new_layer.fields()
        id_index = fields.indexOf("ID")  # Substitua "ID" pelo nome exato do seu campo ID, se for diferente
        for i in range(fields.count()):
            widget_setup = QgsEditorWidgetSetup("Hidden", {}) # Configura o widget para ocultar o campo
            if i == id_index:
                # Para o campo ID, você pode querer definir um widget diferente, ou simplesmente não ocultá-lo
                continue  # Não oculta o campo ID, apenas continua sem alterar seu widget
            else:
                new_layer.setEditorWidgetSetup(i, widget_setup)

        # Atualiza os valores de "Comprimento" para todas as feições existentes, se necessário
        index_comp = fields.indexOf("Comprimentorimento") # Obtém o índice do campo 'Comprimento'
        if index_comp != -1:
            new_layer.startEditing() # Inicia a edição da camada
            for feature in new_layer.getFeatures():
                if feature.geometry():  # Se a feição possui geometria
                    comprimento = round(feature.geometry().length(), 3) # Calcula o comprimento
                    new_layer.changeAttributeValue(feature.id(), index_comp, comprimento) # Atualiza o atributo 'Comprimento'
            new_layer.commitChanges() # Salva as mudanças
   
    def definir_novo_id(self, layer, fid):
        """
        Atribui um novo ID único para uma feição adicionada recentemente em uma camada do QGIS,
        garantindo que todos os IDs sejam sequenciais e únicos dentro da camada.

        Funções e Ações Desenvolvidas:
        - Verifica a existência do campo 'ID' na camada.
        - Calcula o próximo valor de ID baseando-se no maior ID existente.
        - Configura o widget do campo 'ID' para garantir que os IDs sejam atribuídos automaticamente e sejam imutáveis.
        - Atualiza o valor do ID para a nova feição adicionada.
        
        Args:
        - layer: A camada onde o novo ID será definido.
        - fid: O identificador da feição que receberá o novo ID.
        """
        # Verifica se o campo "ID" existe na camada
        index_id = layer.fields().indexOf("ID")
        if index_id == -1:
            # Exibe uma MessageBox informando que o campo "ID" não foi encontrado
            QMessageBox.critical(None, "Erro de Campo", "Campo 'ID' não encontrado na camada.")
            return  # Sai da função se o campo "ID" não existir
            
        # Encontra o maior ID existente na camada
        max_id = 0
        for feature in layer.getFeatures():
            id_value = feature.attribute("ID")  # Assumindo que o campo ID é numérico
            if id_value and id_value > max_id:
                max_id = id_value # Atualiza o máximo ID encontrado

        # Define o novo ID para a feição adicionada como max_id + 1
        novo_id = max_id + 0

        # Atualiza o widget de ID para refletir o próximo valor disponível
        index_id = layer.fields().indexOf("ID")
        widget_setup = QgsEditorWidgetSetup("Range", {
            "Min": novo_id + 1, # 1 # Ajusta para o próximo valor de ID disponível
            "Max": 99999,
            "Step": 1,
            "Style": "SpinBox",
            "AllowNull": False,
            "ReadOnly": True}) # Garante que o valor não possa ser editado manualmente

        # Aplica a configuração do widget ao campo 'ID'
        layer.setEditorWidgetSetup(index_id, widget_setup)

        # Inicia a edição para atualizar o valor do ID
        if not layer.isEditable():
            layer.startEditing()

        # Atualiza o atributo 'ID' da feição com o novo ID
        layer.changeAttributeValue(fid, index_id, novo_id)

    def atualizar_comprimento_linha(self, camada, fid):
        """
        Atualiza o valor do campo 'Comprimento' com o comprimento da geometria de uma feição específica, sempre que essa feição é adicionada ou modificada na camada.

        Parâmetros:
        - camada (QgsVectorLayer): A camada que contém a feição a ser atualizada.
        - fid (int): O ID da feição dentro da camada cujo comprimento da linha será calculado e atualizado.

        Funcionalidades:
        - Encontra o índice do campo 'Comprimento' que deve armazenar o comprimento da linha dentro dos atributos da feição.
        - Obtém a feição pelo seu ID para acessar sua geometria.
        - Verifica se a feição possui uma geometria válida. Se sim, calcula o comprimento da geometria usando uma precisão de três casas decimais.
        - Atualiza o valor do campo 'Comprimento' com o comprimento calculado para a feição especificada, garantindo que o atributo esteja sempre sincronizado com a geometria atual.

        Atribuição no código:
        Fundamental para manter a precisão dos dados geométricos, especialmente em camadas onde o comprimento das linhas é relevante para análises subsequentes ou para a exibição de informações detalhadas sobre as feições. Esta função apoia a integridade dos dados e a precisão analítica ao assegurar que os valores de comprimento sejam corretamente calculados e armazenados cada vez que uma feição é alterada.
        """
        # Encontra o índice do campo 'Comprimento' na camada
        index_comp = camada.fields().indexOf("Comprimento")

        # Obtém a feição pelo seu ID
        feature = camada.getFeature(fid)

        # Se a feição tem geometria válida, calcula o comprimento
        if feature.geometry():
            comprimento = round(feature.geometry().length(), 3)
            # Atualiza o valor do campo 'Comprimento' com o comprimento calculado
            camada.changeAttributeValue(fid, index_comp, comprimento)

    def salvar_camada_permanente(self):
        """
        Salva uma camada temporária como permanente em um arquivo externo, transferindo todas as configurações e dados para uma nova camada persistente.

        Funcionalidades:
        - Obtém a camada atualmente selecionada na interface do usuário a partir do treeView.
        - Verifica se a camada é temporária (armazenada na memória).
        - Clona as configurações de renderização e etiquetas da camada temporária para preservar sua aparência e configurações.
        - Salva quaisquer alterações pendentes se a camada estiver em modo de edição.
        - Permite ao usuário escolher um local para salvar o arquivo, utilizando uma caixa de diálogo para selecionar o formato Shapefile.
        - Salva a camada no local especificado e verifica se o arquivo foi criado com sucesso.
        - Carrega a nova camada salva no projeto QGIS como uma camada permanente.
        - Aplica as configurações clonadas à nova camada, incluindo renderizador, etiquetas e habilitação de etiquetas.
        - Trata das linhas da nova camada chamando a função específica para atualizar comprimentos ou IDs conforme necessário.
        - Adiciona a nova camada a um grupo "Camadas Salvas" na árvore de camadas do projeto.
        - Remove a camada temporária do projeto se ela foi salva com sucesso.
        - Exibe mensagens de status ao usuário sobre o sucesso ou falha da operação.

        Atribuição no código:
        Esta função é crucial para transformar camadas temporárias em permanentes, permitindo que os dados sejam preservados e gerenciados de forma mais eficaz. É especialmente útil para manter a integridade dos dados após o término das sessões de trabalho, garantindo que todas as alterações e configurações da camada sejam salvas e possam ser recuperadas posteriormente.
        """
        # Obtém a camada selecionada atualmente na interface do usuário
        selected_indexes = self.dlg.treeViewListaLinha.selectedIndexes()
        if selected_indexes:
            selected_index = selected_indexes[0]
            layer_id = selected_index.model().itemFromIndex(selected_index).data()
            layer_to_save = QgsProject.instance().mapLayer(layer_id)

            # Verifica se a camada é temporária
            if layer_to_save:
                is_temporary = layer_to_save.dataProvider().name() == 'memory'

                # Clona as configurações de renderização e etiquetas da camada original
                cor_atual = self.obter_cor_linha(layer_to_save)
                renderer = layer_to_save.renderer().clone()
                etiquetas = layer_to_save.labeling().clone() if layer_to_save.labeling() else None

                # Salva as alterações pendentes na camada antes de torná-la permanente
                if layer_to_save.isEditable():
                    layer_to_save.commitChanges()

                # Define o nome e o local para salvar a camada no formato Shapefile
                nome_arquivo = self.escolher_local_para_salvar(os.path.join(self.ultimo_caminho_salvo, layer_to_save.name() + ".shp"), "ESRI Shapefile Files (*.shp)")

                # Verifica se o usuário selecionou um local e prossegue com o salvamento
                if nome_arquivo:
                    resultado_salvar = self.salvar_camada(layer_to_save, nome_arquivo, "ESRI Shapefile")

                    if resultado_salvar:
                        # Carrega a camada salva como permanente
                        new_layer = QgsVectorLayer(nome_arquivo, layer_to_save.name(), "ogr")

                        # Se a nova camada é válida, transfere as configurações para ela
                        if new_layer.isValid():
                            new_layer.setRenderer(renderer)
                            if etiquetas:
                                new_layer.setLabeling(etiquetas)
                                new_layer.setLabelsEnabled(layer_to_save.labelsEnabled())

                            # Chama a função para tratar das linhas
                            self.tratar_linhas(new_layer)

                            # Adiciona a nova camada ao projeto e remove a camada temporária
                            QgsProject.instance().addMapLayer(new_layer, False)

                            # Procura por um grupo chamado "Camadas Salvas" ou cria um novo se não existir
                            root = QgsProject.instance().layerTreeRoot()
                            my_group = root.findGroup("Camadas Salvas")
                            if not my_group:
                                my_group = root.addGroup("Camadas Salvas")

                            # Adiciona a nova camada ao grupo "Camadas Salvas"
                            my_group.addLayer(new_layer)

                            if is_temporary:
                                QgsProject.instance().removeMapLayer(layer_id)
                            self.aplicar_cor_linha(new_layer, cor_atual)

                            # Inicia a edição da camada para permitir atualizações futuras
                            new_layer.startEditing()
                        else:
                            self.mostrar_mensagem("Falha ao carregar a nova camada. A camada não é válida.", "Erro")
                    else:
                        self.mostrar_mensagem("Falha ao salvar a camada no formato Shapefile.", "Erro")

    def salvar_camada(self, layer, fileName, driverName):
        """
        Salva uma camada especificada para um arquivo externo usando o formato especificado pelo driverName.

        Parâmetros:
        - layer (QgsVectorLayer): A camada do QGIS que será salva.
        - fileName (str): O caminho completo do arquivo onde a camada será salva.
        - driverName (str): O nome do driver que define o formato de arquivo (por exemplo, "DXF", "KML").

        Funcionalidades:
        - Configura as opções de salvamento adequadas para o formato especificado, como codificação de arquivo e tratamento de simbologia.
        - Aplica configurações específicas para formatos como KML e DXF, adaptando o processo de salvamento às particularidades desses formatos.
        - Executa a operação de salvamento e verifica o resultado. Se bem-sucedido, exibe uma mensagem de sucesso. Caso contrário, exibe uma mensagem de erro detalhando o problema.
        - Para KML, realiza modificações adicionais no arquivo salvo para garantir a adequação às necessidades específicas (como tessellation).

        Atribuição no código:
        Facilita a exportação de camadas para diversos formatos, permitindo a utilização dos dados em outros softwares ou para fins de arquivamento e compartilhamento. A função é crucial para a interoperabilidade e gerenciamento eficaz dos dados geoespaciais, adaptando a camada às especificações requeridas pelos diferentes formatos de arquivo e garantindo que os dados sejam exportados corretamente.
        """
        options = QgsVectorFileWriter.SaveVectorOptions() # Configurações de salvamento da camada
        options.driverName = driverName # Define o driver de acordo com o formato desejado
        options.fileEncoding = "UTF-8" # Define a codificação do arquivo como UTF-8

        # Configurações específicas para KML
        if driverName == "KML":
            options.symbologyExport = QgsVectorFileWriter.FeatureSymbology

        # Configurações específicas para DXF
        if driverName == "DXF":
            options.skipAttributeCreation = True # Pula a criação de atributos para DXF

        # Tenta salvar a camada com as opções configuradas
        error, errorMessage = QgsVectorFileWriter.writeAsVectorFormat(layer, fileName, options)

        # Verifica se a camada foi salva com sucesso
        if error == QgsVectorFileWriter.NoError:
            self.mostrar_mensagem(f"Camada salva como {driverName} com sucesso.", "Sucesso")
            # Modificações adicionais para KML, se necessário
            if driverName == "KML":
                self.modificar_kml_para_tessellation(fileName)
            return True
        else:
            # Exibe uma mensagem de erro com a descrição do problema
            self.mostrar_mensagem(f"Erro ao salvar a camada como {driverName}: {errorMessage}", "Erro")
            return False
 
    def escolher_local_para_salvar(self, nome_padrao, tipo_arquivo):
        """
        Salva uma camada especificada para um arquivo externo usando o formato especificado pelo driverName.

        Parâmetros:
        - layer (QgsVectorLayer): A camada do QGIS que será salva.
        - fileName (str): O caminho completo do arquivo onde a camada será salva.
        - driverName (str): O nome do driver que define o formato de arquivo (por exemplo, "DXF", "KML").

        Funcionalidades:
        - Configura as opções de salvamento adequadas para o formato especificado, como codificação de arquivo e tratamento de simbologia.
        - Aplica configurações específicas para formatos como KML e DXF, adaptando o processo de salvamento às particularidades desses formatos.
        - Executa a operação de salvamento e verifica o resultado. Se bem-sucedido, exibe uma mensagem de sucesso. Caso contrário, exibe uma mensagem de erro detalhando o problema.
        - Para KML, realiza modificações adicionais no arquivo salvo para garantir a adequação às necessidades específicas (como tessellation).

        Atribuição no código:
        Facilita a exportação de camadas para diversos formatos, permitindo a utilização dos dados em outros softwares ou para fins de arquivamento e compartilhamento. A função é crucial para a interoperabilidade e gerenciamento eficaz dos dados geoespaciais, adaptando a camada às especificações requeridas pelos diferentes formatos de arquivo e garantindo que os dados sejam exportados corretamente.
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

    def modificar_kml_para_tessellation(self, caminho_kml):
        """
        Modifica um arquivo KML para incluir a tag <tessellate> em cada elemento LineString, garantindo a visualização correta das linhas em plataformas que suportam KML, como o Google Earth.

        Parâmetros:
        - caminho_kml (str): O caminho do arquivo KML que será modificado.

        Funcionalidades:
        - Faz o parse do arquivo KML para acessar e modificar sua estrutura XML.
        - Registra o namespace do KML para garantir que as modificações no XML sejam corretamente reconhecidas e validadas.
        - Itera por cada elemento LineString no arquivo KML e adiciona um elemento filho <tessellate> com o valor '1'. Isso indica que o Google Earth e outros visualizadores devem tentar renderizar a linha de forma contínua, mesmo através do horizonte.
        - Salva as alterações no mesmo arquivo KML, substituindo o conteúdo anterior.

        Atribuição no código:
        Essencial para a preparação de arquivos KML para uso em visualizações que exigem uma representação precisa de linhas sobre superfícies curvas, como o globo terrestre no Google Earth. Melhora a interoperabilidade do arquivo KML com diferentes plataformas e dispositivos, assegurando que as linhas sejam exibidas de maneira adequada e contínua.
        """
        try:
            # Faz o parse do arquivo KML
            tree = ET.parse(caminho_kml)
            root = tree.getroot()

            # Registra o namespace KML para a manipulação correta do XML
            ET.register_namespace('', "http://www.opengis.net/kml/2.2")

            # Itera por cada LineString no arquivo KML
            for line_string in root.findall(".//{http://www.opengis.net/kml/2.2}LineString"):
                # Cria e adiciona o elemento tessellate
                tessellate = ET.SubElement(line_string, "tessellate")
                tessellate.text = "1" # Define o valor de tessellate como '1'

            # Salva as alterações feitas no arquivo KML
            tree.write(caminho_kml)
        except Exception as e:
            # Em caso de erro, exibe uma mensagem com a descrição do problema
            self.mostrar_mensagem(f"Erro ao modificar o arquivo KML: {e}", "Erro")

    def obter_cor_rotulo_kml(self, layer):
        """
        Obtém a cor dos rótulos de uma camada em formato adequado para uso em arquivos KML, considerando a configuração de visibilidade e estilização dos rótulos.

        Parâmetros:
        - layer (QgsVectorLayer): A camada do QGIS de onde as configurações de cor do rótulo serão extraídas.

        Funcionalidades:
        - Verifica se os rótulos estão habilitados para a camada. Se não estiverem, retorna uma cor padrão (branco).
        - Obtém as configurações de formatação do rótulo, que incluem detalhes sobre a cor do texto.
        - Extrai a cor do texto dessas configurações e a converte para o formato de cor KML (AABBGGRR), que organiza os canais de cor de forma diferente do padrão RGB usado em muitas outras aplicações.
        - Formata a cor convertida em um valor hexadecimal de 8 dígitos, adequado para uso direto em arquivos KML.

        Atribuição no código:
        Essencial para garantir que a visualização de rótulos em KML reflita as configurações definidas no QGIS, proporcionando consistência visual quando os dados são exportados para visualizações em plataformas que suportam KML, como o Google Earth. Facilita a personalização e o detalhamento na representação de rótulos, melhorando a acessibilidade e a compreensão das informações geográficas.
        """
        if layer.labelsEnabled(): # Verifica se os rótulos estão habilitados para a camada
            text_format = layer.labeling().settings().format() # Obtém as configurações de formatação do rótulo
            cor_texto = text_format.color() # Extrai a cor do texto das configurações de formatação
            # Converte a cor do Qt para o formato de cor KML (AABBGGRR)
            cor_kml = cor_texto.alpha() << 24 | cor_texto.blue() << 16 | cor_texto.green() << 8 | cor_texto.red()
            cor_kml_hex = format(cor_kml, '08x')  # Formata o valor da cor para hexadecimal
            return cor_kml_hex # Retorna a cor formatada
        return 'ffffffff'  # Branco como cor padrão se não houver configuração de rótulo

    def cor_rgb_para_kml(self, cor_rgb):
        """
        Converte uma cor no formato RGB (usado comumente em interfaces gráficas) para o formato ABGR hexadecimal usado em arquivos KML.

        Parâmetros:
        - cor_rgb (QColor): O objeto QColor que representa a cor no formato RGB.

        Funcionalidades:
        - Extrai os componentes vermelho, verde, azul e alfa (transparência) da cor fornecida.
        - Converte esses valores para uma string hexadecimal.
        - Reorganiza a string para se adequar ao formato ABGR, que é o requerido pelo KML para especificar cores. No KML, a ordem dos componentes é alfa (transparência), azul, verde e vermelho, o que difere do padrão RGB mais comum.

        Atribuição no código:
        Facilita a integração e a exportação de dados visuais do QGIS para formatos que utilizam o padrão KML, como o Google Earth. A função assegura que a representação de cores seja mantida corretamente ao transferir informações de cor entre diferentes sistemas e formatos de arquivo, mantendo a fidelidade visual e a clareza das representações geográficas.
        """
        r = cor_rgb.red()
        g = cor_rgb.green()
        b = cor_rgb.blue()
        a = cor_rgb.alpha()

        # Converte os valores RGB para um formato hexadecimal e inverte a ordem para ABGR
        return f'{a:02x}{b:02x}{g:02x}{r:02x}'

    def gerar_cor_suave(self):
        """
        Gera uma cor aleatória com tonalidades suaves, geralmente inclinadas para cores claras, utilizando valores altos no espectro RGB.

        Funcionalidades:
        - Gera valores aleatórios para cada um dos componentes vermelho, verde e azul (RGB), garantindo que os valores estejam no intervalo de 180 a 255. Isso assegura que as cores geradas sejam suaves e claras, ideais para fundos ou para áreas onde cores menos saturadas são desejáveis.
        - Formata os valores RGB gerados em uma string hexadecimal que pode ser usada diretamente em estilos de interfaces gráficas ou em páginas web.

        Atribuição no código:
        Útil para a criação de interfaces de usuário atraentes e agradáveis visualmente, onde cores suaves e menos invasivas são necessárias. Também pode ser utilizada em gráficos, mapas e qualquer aplicativo que beneficie de uma paleta de cores mais suave e menos saturada.
        """
        # Gera valores aleatórios para os componentes RGB dentro do intervalo de cores suaves
        r = random.randint(180, 255) # Comprimentoonente vermelho
        g = random.randint(180, 255) # Comprimentoonente verde
        b = random.randint(180, 255) # Comprimentoonente azul
        return f'#{r:02x}{g:02x}{b:02x}' # Retorna a cor formatada como uma string hexadecimal

    def exportar_para_kml(self):
        """
        Exporta uma camada selecionada do QGIS para o formato KML, permitindo configurações detalhadas através de um diálogo interativo.

        Funcionalidades:
        - Verifica se uma camada está selecionada para exportação. Exibe uma mensagem de erro e encerra se nenhuma camada estiver selecionada.
        - Recupera a camada selecionada e verifica sua existência no projeto QGIS.
        - Inicializa um diálogo com opções detalhadas de exportação para KML, incluindo seleção de campos, configurações de visualização 3D, e outros.
        - Se o diálogo for aceito pelo usuário, inicia o processo de exportação, incluindo a escolha do local para salvar o arquivo.
        - Cria um documento KML em memória com as configurações definidas, escreve no local especificado e aplica modificações adicionais se necessário.
        - Calcula e exibe o tempo decorrido para a operação de exportação, informando o usuário sobre a conclusão bem-sucedida.

        Atribuição no código:
        Essencial para a interoperabilidade com outras plataformas que suportam KML, como Google Earth. Esta funcionalidade facilita a visualização e compartilhamento de dados geográficos, permitindo que informações detalhadas das camadas do QGIS sejam apresentadas eficazmente em um formato amplamente utilizado. O diálogo interativo garante que os usuários possam personalizar a exportação para atender suas necessidades específicas.
        """
        # Seleciona a camada antes de escolher o local de salvamento
        indexes = self.dlg.treeViewListaLinha.selectedIndexes()  # Obtém a camada do projeto QGIS usando o ID
        if not indexes:
            self.mostrar_mensagem("Nenhuma camada selecionada.", "Erro") # Exibe mensagem de erro se nenhuma camada estiver selecionada
            return

        # Obtém o ID da camada selecionada
        layer_id = indexes[0].model().itemFromIndex(indexes[0]).data()
        layer = QgsProject.instance().mapLayer(layer_id)

        if not layer:
            self.mostrar_mensagem("Camada não encontrada.", "Erro")
            return

        campos = [field.name() for field in layer.fields()] # Lista os nomes dos campos da camada
        dialog = ExportarKMLDialog(campos) # Inicializa o diálogo de exportação com os campos da camada

        if dialog.exec_() == QDialog.Accepted: # Verifica se o usuário aceitou o diálogo de exportação
            start_time = time.time()  # Inicia o temporizador

            # Obtém os valores definidos no diálogo de exportação
            campo_rotulo, espessura_linha, altitude, url_imagem, url_imagem_2, incluir_tabela, use_3d, num_repeticoes = dialog.getValues()

            # Define o nome padrão do arquivo e o local de salvamento
            nome_padrao = f"{layer.name()}.kml"
            tipo_arquivo = "KML Files (*.kml)"
            caminho_arquivos = self.escolher_local_para_salvar(nome_padrao, tipo_arquivo)

            if not caminho_arquivos:
                self.mostrar_mensagem("Exportação cancelada.", "Info") # Cancela a exportação se o usuário não escolher um local para salvar
                return

            # Cria o KML em memória com as opções definidas
            kml_element = self.criar_kml_em_memoria(layer, campo_rotulo, espessura_linha, altitude, url_imagem, url_imagem_2, incluir_tabela, use_3d, num_repeticoes)

            # Escreve o KML no arquivo
            tree = ET.ElementTree(kml_element)
            tree.write(caminho_arquivos, xml_declaration=True, encoding='utf-8', method="xml")

            # Modificar KML para tessellation (se necessário)
            self.modificar_kml_para_tessellation(caminho_arquivos)

            elapsed_time = time.time() - start_time  # Calcula o tempo decorrido
            # self.mostrar_mensagem(f"Arquivo KML salvo com sucesso. Tempo de execução: {elapsed_time:.2f} segundos.", "Sucesso")

            # Exibir mensagem de sucesso com o tempo de execução e caminhos dos arquivos
            self.mostrar_mensagem(
                f"Camada exportada para KMZ em {elapsed_time:.2f} segundos", 
                "Sucesso", 
                caminho_pasta=os.path.dirname(caminho_arquivos), 
                caminho_arquivo=caminho_arquivos)

        else:
            self.mostrar_mensagem("Exportação cancelada.", "Info")

    def criar_placemark_kml(self, document, feature, campo_rotulo, cor_linha_kml, espessura_linha, altitude_base, transformar, transform, url_imagem, url_imagem_2, incluir_tabela, use_3d, num_repeticoes):
        """
        Cria múltiplos Placemarks no documento KML para uma camada selecionada, permitindo configurações detalhadas de visualização e inclusão de dados em 3D.

        Parâmetros:
        - document (ET.Element): O elemento XML do documento KML onde os Placemarks serão adicionados.
        - feature (QgsFeature): A feição geográfica da qual o Placemark será criado.
        - campo_rotulo, cor_linha_kml, espessura_linha, altitude_base, transformar, transform, url_imagem, url_imagem_2, incluir_tabela, use_3d, num_repeticoes: Diversos parâmetros que definem as propriedades visuais e funcionais do Placemark, como cor, espessura, altitude, transformação geométrica, e opções de repetição para representações múltiplas.

        Funcionalidades:
        - Itera sobre o número de repetições especificadas para criar várias instâncias do Placemark, cada uma em uma altitude incremental.
        - Configura cada Placemark com linhas que podem ser simples ou multipartes, adaptando-se à geometria da feição.
        - Define estilos visuais detalhados, incluindo cor e espessura das linhas.
        - Se solicitado, adiciona uma tabela de atributos ao Placemark usando um BalloonStyle, enriquecendo a representação com informações detalhadas.
        - Permite a inclusão de imagens e estilos visuais personalizados para melhorar a apresentação dos dados.

        Atribuição no código:
        A função é crucial para exportações detalhadas para KML, proporcionando uma representação rica e interativa das camadas do QGIS em plataformas como o Google Earth. Permite a visualização eficaz de informações complexas e é essencial em contextos onde a clareza e a profundidade da apresentação de dados geográficos são necessárias.
        """
        for i in range(num_repeticoes):
            altitude = altitude_base + i * altitude_base
            placemark = ET.SubElement(document, 'Placemark')

            if feature.geometry().isMultipart():
                lines = feature.geometry().asMultiPolyline()
                multi_geometry = ET.SubElement(placemark, 'MultiGeometry')
                for part in lines:
                    self.add_line_string_kml(multi_geometry, part, altitude, transformar, transform, cor_linha_kml, espessura_linha, use_3d)
            else:
                lines = feature.geometry().asPolyline()
                self.add_line_string_kml(placemark, lines, altitude, transformar, transform, cor_linha_kml, espessura_linha, use_3d)

            # Configura o estilo do Placemark para cada repetição
            style = ET.SubElement(placemark, 'Style')
            line_style = ET.SubElement(style, 'LineStyle')
            color = ET.SubElement(line_style, 'color')
            color.text = cor_linha_kml
            width = ET.SubElement(line_style, 'width')
            width.text = f'{espessura_linha:.1f}'

        # Se incluir_tabela for True, adiciona os atributos da feature e configura o BalloonStyle
        if incluir_tabela:        
            name = ET.SubElement(placemark, 'name')
            name.text = str(feature[campo_rotulo]) # Define o nome do Placemark

            extended_data = ET.SubElement(placemark, 'ExtendedData') # Cria ExtendedData para os atributos
            # Adiciona cada campo da feature como um elemento Data em ExtendedData
            for field in feature.fields():
                data = ET.SubElement(extended_data, 'Data', name=field.name())
                value = ET.SubElement(data, 'value')
                value.text = str(feature[field.name()])

            # Inserindo visibilidade do rótulo
            label_visibility = ET.SubElement(line_style, '{http://www.google.com/kml/ext/2.2}labelVisibility')
            label_visibility.text = '1'

            # Início da construção da tabela de atributos
            tabela_geral_html = '<table border="1" style="border-collapse: collapse; border: 2px solid black; width: 100%;">'

            for field in feature.fields():
                cor_fundo = self.gerar_cor_suave()  # Gera uma cor suave para o fundo de cada campo
                # Tabela externa para cada campo
                tabela_geral_html += '<tr><td>'

                # Tabela interna para o conteúdo do campo, com alinhamento específico para cada coluna
                tabela_campo_html = f'<table border="0" style="background-color: {cor_fundo}; width: 100%;">'
                tabela_campo_html += f'<tr><td style="text-align: left;"><b>{field.name()}</b></td><td style="text-align: right;">{str(feature[field.name()])}</td></tr>'
                tabela_campo_html += '</table>'

                tabela_geral_html += tabela_campo_html
                tabela_geral_html += '</td></tr>'

            tabela_geral_html += '</table>'

            # Checagem se a URL da imagem foi fornecida
            imagem_html = ""

            if url_imagem:  # Se url_imagem não estiver vazia
                # Redimensiona a imagem para caber dentro de width="72" e height="36"
                imagem_redimensionada, nova_largura, nova_altura = self.redimensionar_imagem_proporcional_url(url_imagem, 150, 75)
                
                # Se a imagem foi redimensionada com sucesso, aplica as novas dimensões ao HTML
                if imagem_redimensionada is not None:
                    imagem_html = f'<div style="text-align: center;"><img src="{url_imagem}" alt="Ícone" width="{nova_largura}" height="{nova_altura}" style="margin-top: 1px; margin-bottom: -15px; margin-left: 0px; margin-right: 0px;"></div>'

            # BalloonStyle com a imagem condicional e tabela de atributos
            balloon_style = ET.SubElement(style, 'BalloonStyle')
            text = ET.SubElement(balloon_style, 'text')
            balloon_html = f"""
            {imagem_html}
            <h3 style="margin-bottom:1px;">{campo_rotulo}: {str(feature[campo_rotulo])}</h3>
            <p>Tabela de Informações:</p>
            {tabela_geral_html}
            $[description]
            """
            text.text = balloon_html

    def add_line_string_kml(self, parent, line_points, altitude, transformar, transform, cor_linha_kml, espessura_linha, use_3d):
        """
        Adiciona uma representação KML de uma linha (LineString) ao elemento KML pai fornecido, configurando opções como altitude, tesselação e transformação de coordenadas conforme necessário.

        Parâmetros:
        - parent (ElementTree Element): O elemento pai KML ao qual a LineString será adicionada.
        - line_points (list of QgsPointXY): Lista dos pontos que compõem a linha.
        - altitude (float): A altitude que cada ponto da linha deve ter.
        - transformar (bool): Se verdadeiro, aplica uma transformação geográfica aos pontos da linha.
        - transform (QgsCoordinateTransform): A transformação a ser aplicada, se transformar for verdadeiro.
        - cor_linha_kml (str): Cor da linha no formato KML.
        - espessura_linha (float): A espessura da linha para a visualização.
        - use_3d (bool): Se verdadeiro, habilita a extrusão para efeito tridimensional.

        Funcionalidades:
        - Cria um subelemento LineString dentro do elemento parente especificado.
        - Configura o modo de altitude para a LineString baseado no valor de altitude fornecido.
        - Habilita a tesselação se a altitude for zero para garantir uma renderização correta no Google Earth.
        - Habilita a extrusão se `use_3d` estiver ativo e a altitude for diferente de zero, criando um efeito tridimensional.
        - Transforma os pontos da linha se necessário e os formata em uma string de coordenadas que inclui a altitude.
        - Adiciona as coordenadas transformadas e formatadas ao elemento LineString.

        Atribuição no código:
        Essencial para criar visualizações detalhadas e precisas de linhas em arquivos KML, permitindo a representação adequada de características geográficas em plataformas que suportam KML, como o Google Earth. A funcionalidade de transformação e a inclusão de altitude são cruciais para garantir que as linhas sejam visualizadas corretamente em relação ao terreno e em diferentes contextos geográficos.
        """
        # Cria um subelemento LineString dentro do elemento parente
        line_string = ET.SubElement(parent, 'LineString')

        # Configura o modo de altitude para a LineString
        altitude_mode = ET.SubElement(line_string, 'altitudeMode')
        # Define o texto do modo de altitude com base no valor da altitude
        altitude_mode.text = 'relativeToGround' if altitude != 0 else 'clampToGround'
        
        # Se a altitude é 0, habilita a tesselação para melhorar a renderização no Google Earth
        if altitude != 0 and use_3d:
            extrude = ET.SubElement(line_string, 'extrude')
            extrude.text = '1'
        tessellate = ET.SubElement(line_string, 'tessellate')
        tessellate.text = '1'
        
        # Cria um subelemento para as coordenadas
        coordinates = ET.SubElement(line_string, 'coordinates')
        coords = [] # Inicializa uma lista para armazenar as coordenadas formatadas

        for point in line_points: # Itera sobre cada ponto na linha fornecida
            if transformar:  # Se a transformação estiver habilitada, transforma o ponto
                point = transform.transform(point)  # Transforma o ponto se necessário
            # Adiciona o ponto transformado (ou não) à lista de coordenadas, incluindo a altitude
            coords.append(f"{point.x()},{point.y()},{altitude}")
        # Junta todas as coordenadas em uma string e a define como texto do elemento de coordenadas
        coordinates.text = ' '.join(coords) 

    def criar_kml_em_memoria(self, layer, campo_rotulo, espessura_linha, altitude, url_imagem, url_imagem_2, incluir_tabela, use_3d, num_repeticoes):
        """
        Cria uma representação KML em memória de uma camada do QGIS, incluindo opções para visualização 3D, repetição de elementos, tabelas de atributos e a possibilidade de adicionar uma imagem como ScreenOverlay.

        Parâmetros:
        - layer (QgsVectorLayer): A camada de onde os dados serão extraídos.
        - campo_rotulo (str): O campo utilizado para o rótulo dos placemarks.
        - espessura_linha (float): A espessura das linhas no KML.
        - altitude (int): A altitude base para os placemarks.
        - url_imagem (str): URL para uma imagem usada como ícone nos placemarks.
        - url_imagem_2 (str): URL para uma imagem usada como ScreenOverlay no KML.
        - incluir_tabela (bool): Se verdadeiro, inclui uma tabela de atributos em cada placemark.
        - use_3d (bool): Se verdadeiro, aplica extrusão para efeito tridimensional.
        - num_repeticoes (int): Número de vezes que cada placemark será repetido com incremento de altitude.

        Funcionalidades:
        - Cria o elemento KML e um subelemento Documento.
        - Utiliza um índice espacial para otimizar a criação de placemarks.
        - Para cada feição na camada, um placemark é criado com opções de visualização configuráveis.
        - Utiliza uma barra de progresso para indicar o progresso da criação do KML.
        - Adiciona um ScreenOverlay ao KML se uma segunda URL de imagem for fornecida e a imagem for processada corretamente.
        - Caso a imagem do ScreenOverlay não possa ser processada, o KML é gerado normalmente sem o ScreenOverlay.
        - Retorna o elemento KML criado para uso posterior, como salvar em um arquivo ou enviar por rede.

        Atribuição no código:
        Facilita a exportação de dados geográficos complexos para o formato KML, amplamente utilizado em aplicações como Google Earth. Esta função é essencial para projetos que requerem visualização avançada de dados geoespaciais e oferece uma maneira de personalizar intensamente a apresentação desses dados.
        Além disso, a função é robusta o suficiente para lidar com falhas no processamento de imagens, garantindo que a exportação do KML continue sem interrupções, mesmo que um ScreenOverlay não possa ser adicionado.
        """
        progressBar, messageBar = self.iniciar_progress_bar(layer)  # Inicia a barra de progresso

        # Cria o elemento raiz do KML e um subelemento Documento
        kml = ET.Element('kml', xmlns="http://www.opengis.net/kml/2.2")
        document = ET.SubElement(kml, 'Document')

        # Criar um índice espacial para a camada
        index = QgsSpatialIndex()
        for feat in layer.getFeatures():
            index.insertFeature(feat)

        # Cria placemarks para cada recurso na camada
        total_features = layer.featureCount()
        for count, feature in enumerate(layer.getFeatures()):
            self.criar_placemark_kml(document, feature, campo_rotulo, self.cor_rgb_para_kml(self.obter_cor_linha(layer)), espessura_linha, altitude, layer.crs().authid() != 'EPSG:4326', None if layer.crs().authid() == 'EPSG:4326' else QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem(4326), QgsProject.instance()), url_imagem, url_imagem_2, incluir_tabela, use_3d, num_repeticoes)
            progressBar.setValue(count + 1)  # Atualiza a barra de progresso

        # Obtém e converte a cor da linha da camada para o formato KML
        cor_linha = self.obter_cor_linha(layer)
        # Converte a cor da linha para o formato de cor KML (AABBGGRR)
        cor_linha_kml = self.cor_rgb_para_kml(cor_linha)

        # Prepara a transformação de coordenadas se a camada não estiver em EPSG:4326
        if layer.crs().authid() != 'EPSG:4326':
            crsDestino = QgsCoordinateReferenceSystem(4326)
            transform = QgsCoordinateTransform(layer.crs(), crsDestino, QgsProject.instance())
            transformar = True # Habilita a flag de transformação
        else:
            transformar = False # Desabilita a flag de transformação, não é necessária

        # Cria placemarks para cada recurso na camada
        for feature in layer.getFeatures():
            self.criar_placemark_kml(document, feature, campo_rotulo, cor_linha_kml, espessura_linha, altitude, transformar, transform if transformar else None, url_imagem, url_imagem_2, incluir_tabela, use_3d, num_repeticoes)

        # Adiciona ScreenOverlay apenas se url_imagem_2 for fornecida e não for vazia
        if url_imagem_2:
            # Redimensiona a imagem obtida a partir do URL
            imagem_redimensionada, nova_largura, nova_altura = self.redimensionar_imagem_proporcional_url(url_imagem_2, 300, 150)

            if imagem_redimensionada is not None:
                # Adiciona o ScreenOverlay ao KML usando a imagem redimensionada
                screen_overlay = ET.SubElement(document, 'ScreenOverlay') # Cria o elemento ScreenOverlay no documento KML
                name = ET.SubElement(screen_overlay, 'name')  # Define o nome do ScreenOverlay
                name.text = 'logo'

                # Define o ícone do ScreenOverlay, utilizando a URL da imagem fornecida
                icon = ET.SubElement(screen_overlay, 'Icon')
                href = ET.SubElement(icon, 'href')
                href.text = url_imagem_2

                # Configura a posição e o tamanho do overlay na tela
                overlay_xy = ET.SubElement(screen_overlay, 'overlayXY', x="1", y="1", xunits="fraction", yunits="fraction")
                screen_xy = ET.SubElement(screen_overlay, 'screenXY', x=f"{nova_largura}", y=f"{nova_altura}", xunits="pixels", yunits="pixels")
                rotation_xy = ET.SubElement(screen_overlay, 'rotationXY', x="0", y="0", xunits="fraction", yunits="fraction")
                # Define o tamanho do ScreenOverlay
                size = ET.SubElement(screen_overlay, 'size', x=f"{nova_largura}", y=f"{nova_altura}", xunits="pixels", yunits="pixels")

        # Continua o processo normalmente, mesmo se o ScreenOverlay não foi adicionado
        progressBar.setValue(total_features)  # Garante que a barra de progresso esteja completa no fim do processo
        self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens

        return kml

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

    def abrir_tabela_atributos(self):
        """
        Abre a tabela de atributos para a camada selecionada no treeView, permitindo a visualização e edição dos atributos da camada no QGIS.

        Funcionalidades:
        - Verifica se existe alguma camada selecionada no treeView.
        - Se uma camada estiver selecionada, obtém o ID dessa camada a partir do índice selecionado.
        - Usa o ID para obter a camada correspondente do projeto QGIS.
        - Se a camada for válida, invoca o método para mostrar a tabela de atributos da camada na interface do usuário do QGIS, facilitando a interação com os dados da camada.

        Atribuição no código:
        Essencial para proporcionar acesso direto e fácil à edição e visualização dos atributos das camadas dentro do projeto QGIS. Esta funcionalidade é crucial para o gerenciamento de dados geográficos, permitindo aos usuários ajustar, analisar e entender os dados associados a cada camada visualmente. Melhora a usabilidade e a eficiência do trabalho ao permitir manipulações rápidas e diretas nos dados.
        """
        selected_indexes = self.dlg.treeViewListaLinha.selectedIndexes()
        if selected_indexes:
            selected_index = selected_indexes[0] # Assume o primeiro item selecionado (se houver)
            layer_id = selected_index.model().itemFromIndex(selected_index).data() # Obtém o ID da camada do item selecionado
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                self.iface.showAttributeTable(layer)

    def abrir_adicionar_arquivo(self):
        """
        Abre um diálogo para selecionar um arquivo de formato de dados geoespaciais e tenta adicioná-lo ao projeto QGIS como uma nova camada.

        Funcionalidades:
        - Apresenta um diálogo de seleção de arquivo com filtros para diferentes formatos suportados pelo QGIS, incluindo DXF, KML, KMZ, Shapefiles, GeoJSON e Geopackages.
        - Permite ao usuário escolher um arquivo desses formatos para ser adicionado ao projeto como uma camada.
        - Extrai o nome da camada do nome do arquivo selecionado e tenta carregar o arquivo como uma camada do QGIS.
        - Verifica se a camada carregada é válida. Se não for, exibe uma mensagem de erro.
        - Para DXF, carrega apenas as entidades do tipo "linhas".
        - Para KML e KMZ, carrega apenas as camadas do tipo "linhas" automaticamente.
        - Se a camada for válida mas não tiver um SRC definido, exibe um diálogo para o usuário escolher o SRC.
        - Adiciona a camada ao projeto e a torna visível.
        - Atualiza a visualização da árvore de camadas para refletir a adição da nova camada e garante que a camada esteja visível no mapa.
        """
        # Cria a string de filtro para o diálogo de seleção de arquivos
        file_filter = "All Supported Formats (*.dxf *.kml *.kmz *.shp *.geojson *.gpkg);;" \
                      "DXF Files (*.dxf);;" \
                      "KML Files (*.kml);;" \
                      "KMZ Files (*.kmz);;" \
                      "Shapefiles (*.shp);;" \
                      "GeoJSON Files (*.geojson);;" \
                      "Geopackage Files (*.gpkg)"

        # Abre a janela de diálogo para selecionar um arquivo
        filePath, _ = QFileDialog.getOpenFileName(self.dlg, "Abrir Arquivo", "", file_filter)
        if not filePath:
            return

        # Determina o nome da camada baseado no nome do arquivo
        layerName = os.path.basename(os.path.splitext(filePath)[0])

        # Define as opções de carregamento de acordo com o tipo de arquivo
        options = {}
        extensao = os.path.splitext(filePath)[1].lower()

        if extensao == ".dxf":
            # Configurações para carregar apenas as entidades do tipo "linhas" em DXF
            layer = QgsVectorLayer(f"{filePath}|layername=entities|geometrytype=LineString", layerName, "ogr")
        elif extensao in [".kml", ".kmz"]:
            # Configurações para KML e KMZ: carrega apenas as camadas do tipo "linhas"
            uri = f"{filePath}|geometrytype=LineString"
            layer = QgsVectorLayer(uri, layerName, "ogr")
        else:
            # Carregamento padrão para outros formatos
            layer = QgsVectorLayer(filePath, layerName, "ogr")

        # Verifica se a camada é válida
        if not layer.isValid():
            self.mostrar_mensagem("O arquivo selecionado não é um arquivo válido.", "Erro")
            return

        # Verifica se a camada tem um SRC definido
        if not layer.crs().isValid():
            # Exibe um diálogo para o usuário escolher o SRC
            projectionSelector = QgsProjectionSelectionDialog()
            if projectionSelector.exec_():
                selectedCrs = projectionSelector.crs()
                if selectedCrs.isValid():
                    # Define o SRC escolhido pelo usuário
                    layer.setCrs(selectedCrs)
                else:
                    self.mostrar_mensagem("Nenhum SRC foi selecionado. A camada não será adicionada.", "Erro")
                    return
            else:
                self.mostrar_mensagem("Operação cancelada pelo usuário. A camada não será adicionada.", "Aviso")
                return

        # Adiciona a camada ao projeto
        QgsProject.instance().addMapLayer(layer)
        self.mostrar_mensagem(f"Camada '{layerName}' adicionada com sucesso.", "Sucesso")

        # Atualizar a visibilidade da camada na TreeView
        self.atualizar_treeView_lista_linha()

        # Garantir que a camada adicionada esteja visível
        layer_tree_layer = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
        if layer_tree_layer:
            layer_tree_layer.setItemVisibilityChecked(True)

    def open_context_menu(self, position):
        """
        Abre um menu de contexto para a camada selecionada na árvore de visualização de camadas, fornecendo opções rápidas como mudar a espessura da linha e abrir propriedades da camada.

        Parâmetros:
        - position (QPoint): A posição do cursor do mouse no momento do clique direito, usada para posicionar o menu de contexto.

        Funcionalidades:
        - Verifica se existe algum item selecionado na árvore de camadas.
        - Cria um menu de contexto com opções específicas relacionadas à camada selecionada, como alterar a espessura da linha ou abrir as propriedades da camada.
        - Exibe o menu de contexto na posição do cursor e aguarda o usuário escolher uma ação.
        - Responde à seleção do usuário, chamando a função apropriada com base na ação escolhida.

        Atribuição no código:
        Facilita o acesso rápido às funções de modificação e visualização de propriedades das camadas diretamente da árvore de visualização, melhorando a eficiência do fluxo de trabalho e permitindo ajustes rápidos sem necessidade de navegar por menus adicionais. Essencial para a usabilidade e acessibilidade em interfaces ricas em funcionalidades.
        """
        # Obtém os índices dos itens selecionados na lista de camadas
        indexes = self.dlg.treeViewListaLinha.selectedIndexes() # Acessa os índices selecionados no treeView
        if indexes:
            menu = QMenu() # Cria um objeto QMenu para o menu de contexto
            change_thickness_action = menu.addAction("Espessura da Linha") # Adiciona uma ação para mudar a espessura da linha
            layer_properties_action = menu.addAction("Abrir Propriedades da Camada") # Adiciona uma ação para abrir propriedades da camada
            action = menu.exec_(self.dlg.treeViewListaLinha.viewport().mapToGlobal(position)) # Exibe o menu e aguarda uma ação ser selecionada
            if action == layer_properties_action: # Verifica se a ação selecionada é abrir propriedades da camada
                self.abrir_layer_properties(indexes[0]) # Chama função para abrir propriedades da camada selecionada
            elif action == change_thickness_action:  # Verifica se a ação selecionada é alterar a espessura da linha
                self.prompt_for_new_line_thickness(indexes[0]) # Chama função para ajustar a espessura da linha

    def prompt_for_new_line_thickness(self, index):
        """
        Abre um diálogo para que o usuário possa ajustar a espessura da linha de uma camada selecionada no QGIS.

        Parâmetros:
        - index (QModelIndex): O índice da camada selecionada no QTreeView.

        Funcionalidades:
        - Recupera o ID da camada a partir do item selecionado no QTreeView usando o UserRole + 1.
        - Busca a camada correspondente no projeto QGIS usando o ID recuperado.
        - Verifica se a camada foi encontrada e prossegue se for positivo.
        - Obtém a espessura atual da linha da camada para uso como valor inicial no diálogo.
        - Cria um diálogo personalizado com um QDoubleSpinBox para permitir ao usuário definir uma nova espessura da linha.
        - O diálogo permite definir a espessura da linha de 0 a 10 com passos de 0.1 e duas casas decimais.
        - Exibe o diálogo e aplica a nova espessura à camada se o usuário confirmar a mudança.

        Atribuição no código:
        Facilita a personalização visual das camadas no projeto QGIS, permitindo ajustes finos na apresentação das linhas, o que é crucial para a clareza visual e a precisão em representações cartográficas. A função melhora a interatividade do usuário com o QGIS, oferecendo controle direto sobre as propriedades estilísticas das camadas.
        """
        # Recupera o ID da camada do item selecionado no QTreeView usando o UserRole + 1
        layer_id = index.model().itemFromIndex(index).data(Qt.UserRole + 1)
        # Busca a camada correspondente no projeto QGIS usando o ID
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:  # Verifica se a camada foi encontrada
            # Obtém a espessura atual da linha da camada
            current_thickness = self.get_current_line_thickness(layer)
            # Cria um diálogo personalizado para ajuste de espessura
            dlg = QDialog(self.dlg)
            dlg.setWindowTitle("Alterar Espessura da Linha")  # Define o título do diálogo
            layout = QVBoxLayout(dlg)  # Cria um layout vertical para o diálogo
            # Configura um QDoubleSpinBox para escolha da nova espessura
            spinBox = QDoubleSpinBox(dlg)
            spinBox.setRange(0, 10)  # Define o intervalo de valores
            spinBox.setSingleStep(0.1)  # Define o incremento de ajuste
            spinBox.setValue(current_thickness)  # Define o valor inicial com a espessura atual
            spinBox.setDecimals(2)  # Define a precisão decimal
            layout.addWidget(spinBox)  # Adiciona o QDoubleSpinBox ao layout
            # Cria um layout horizontal para os botões
            buttonLayout = QHBoxLayout()
            okButton = QPushButton("OK", dlg)  # Cria um botão de OK
            okButton.clicked.connect(dlg.accept)  # Conecta o botão OK à ação de aceitar o diálogo
            buttonLayout.addWidget(okButton)  # Adiciona o botão OK ao layout de botões
            layout.addLayout(buttonLayout)  # Adiciona o layout de botões ao layout principal
            # Exibe o diálogo e espera pela ação do usuário
            if dlg.exec_():  # Se o usuário clicar em OK
                new_thickness = spinBox.value()  # Obtém o novo valor da espessura
                # Aplica a nova espessura à camada se o usuário confirmar
                self.apply_new_line_thickness(layer, new_thickness)

    def get_current_line_thickness(self, layer):
        """
        Recupera a espessura atual da linha para uma camada específica no QGIS, usando o símbolo associado ao seu renderizador.

        Parâmetros:
        - layer (QgsVectorLayer): A camada do QGIS da qual a espessura da linha será obtida.

        Funcionalidades:
        - Acessa o renderizador da camada para obter o símbolo que está atualmente sendo usado para desenhar a camada no mapa.
        - Extrai a espessura da linha configurada no símbolo e a retorna.

        Atribuição no código:
        Essencial para operações que requerem conhecimento ou ajuste da espessura da linha de uma camada, como funções de personalização visual ou verificações de consistência de estilo. Facilita a manipulação e adaptação de propriedades visuais das camadas, permitindo que ajustes sejam feitos de maneira informada e precisa.
        """
        # Acessa o renderizador da camada para obter o símbolo atual
        symbol = layer.renderer().symbol()  # Acessa o símbolo usado pelo renderizador da camada
        # Retorna a espessura da linha configurada no símbolo
        return symbol.width()  # Retorna o valor da largura (espessura) do símbolo

    def apply_new_line_thickness(self, layer, new_thickness):
        """
        Aplica uma nova espessura de linha a uma camada no QGIS, atualizando o símbolo usado pelo renderizador da camada.

        Parâmetros:
        - layer (QgsVectorLayer): A camada do QGIS à qual a nova espessura da linha será aplicada.
        - new_thickness (float): O novo valor de espessura para a linha.

        Funcionalidades:
        - Acessa o renderizador da camada para obter o símbolo atualmente utilizado.
        - Atualiza a espessura do símbolo para o novo valor especificado.
        - Dispara uma ação de repintura na camada para garantir que as mudanças na espessura da linha sejam visualmente refletidas no mapa.
        - Reaplica o renderizador atualizado à camada para garantir que as alterações sejam permanentes e consistentes.

        Atribuição no código:
        Permite ajustes dinâmicos e precisos na apresentação visual das camadas, essencial para tarefas de design e visualização cartográfica onde a clareza e a distinção visual são críticas. A função é crucial para manter a flexibilidade e a adaptabilidade do QGIS em responder às necessidades estéticas e funcionais dos usuários, facilitando a personalização e ajustes finos das propriedades de renderização das camadas.
        """
        # Acessa o renderizador da camada para obter o símbolo atual
        symbol = layer.renderer().symbol()  # Acessa o símbolo usado pelo renderizador da camada
        # Define a nova espessura no símbolo
        symbol.setWidth(new_thickness)  # Atualiza a espessura do símbolo
        # Dispara uma ação de repintura na camada
        layer.triggerRepaint()  # Força a camada a repintar-se para refletir a nova configuração de espessura
        # Reaplica o renderizador para garantir que as mudanças sejam aplicadas
        layer.setRenderer(layer.renderer())  # Atualiza o renderizador com o novo símbolo

    def abrir_layer_properties(self, index):
        """
        Abre a janela de propriedades para uma camada específica selecionada no QGIS, permitindo que os usuários ajustem configurações detalhadas da camada.

        Parâmetros:
        - index (QModelIndex): O índice no treeView que representa a camada selecionada.

        Funcionalidades:
        - Recupera o ID da camada a partir do índice fornecido.
        - Busca a camada correspondente no projeto QGIS usando o ID.
        - Se a camada for encontrada, abre a janela de propriedades da camada na interface do QGIS, permitindo ao usuário acessar e modificar uma ampla variedade de configurações da camada.

        Atribuição no código:
        Essencial para oferecer acesso direto às configurações avançadas de camadas, como simbologia, rótulos, e configurações de renderização. Facilita a gestão detalhada das camadas, melhorando a eficiência e a precisão na personalização das propriedades das camadas. A função é particularmente útil em fluxos de trabalho de gestão de dados geográficos, onde ajustes frequentes nas configurações das camadas são comuns.
        """
        # Obtém o ID da camada do item selecionado no treeView
        layer_id = index.model().itemFromIndex(index).data()
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:
            self.iface.showLayerProperties(layer)

    def abrir_dialogo_selecao_campos(self):
        """
        Abre um diálogo para gerenciar as configurações de etiquetas de campos de uma camada selecionada no treeView do QGIS.

        Funcionalidades:
        - Verifica se há alguma camada selecionada na árvore de visualização de camadas. Retorna imediatamente se não houver seleção.
        - Obtém o índice da primeira camada selecionada, assumindo que apenas uma camada é selecionada para esta ação.
        - Recupera o identificador (ID) da camada do item selecionado para localizar a camada no projeto QGIS.
        - Busca a camada correspondente no projeto QGIS usando o ID recuperado.
        - Se a camada for encontrada, cria e exibe um diálogo para gerenciar as configurações de etiquetas dessa camada, usando dados de cores e visibilidade previamente definidos.

        Atribuição no código:
        Essencial para permitir a personalização detalhada das configurações de etiquetas das camadas, facilitando o gerenciamento de como as informações são visualizadas no mapa. Melhora a interatividade do usuário com as camadas, permitindo ajustes específicos nas etiquetas que melhoram a legibilidade e a apresentação das informações geográficas. Essa funcionalidade é crucial em ambientes profissionais de SIG onde a representação precisa e a clareza dos dados são prioritárias.
        """
        # Obtém os índices selecionados na árvore de visualização de camadas
        selected_indexes = self.dlg.treeViewListaLinha.selectedIndexes()
        if not selected_indexes:
            return # Retorna imediatamente se nenhuma camada estiver selecionada

        # Obtém o primeiro índice selecionado, pois espera-se uma única seleção
        selected_index = selected_indexes[0]
        # Extrai o identificador da camada do item selecionado
        layer_id = selected_index.model().itemFromIndex(selected_index).data()
        # Busca a camada no projeto QGIS usando o identificador
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            return # Retorna se a camada não for encontrada
        
        # Cria e exibe o diálogo de gerenciamento de etiquetas para a camada selecionada
        dialog = GerenciarEtiquetasDialog(layer, self.fieldColors, self.fieldVisibility, self.iface, self.dlg)
        dialog.exec_()

    def salvar_camada_multiplo(self):
        """
        Permite ao usuário salvar uma camada selecionada em múltiplos formatos de arquivo simultaneamente, utilizando um diálogo de seleção.

        Funcionalidades:
        - Verifica se alguma camada está selecionada na árvore de visualização de camadas.
        - Extrai o identificador (ID) da camada selecionada para localizar a camada no projeto QGIS.
        - Apresenta um diálogo para que o usuário escolha quais formatos de arquivo deseja salvar a camada (DXF, KML, GeoJSON, etc.).
        - Permite ao usuário selecionar um diretório onde os arquivos serão salvos.
        - Salva a camada nos formatos escolhidos no diretório especificado, aplicando as configurações necessárias para cada formato.
        - Retorna um status de sucesso ou falha com base na ação do usuário (selecionar formatos, diretório, ou cancelar operação).

        Atribuição no código:
        Facilita a exportação de camadas para diferentes formatos de maneira eficiente, permitindo aos usuários do QGIS maximizar a interoperabilidade com outros softwares e plataformas de dados geoespaciais. Esta funcionalidade é crucial para profissionais que necessitam disponibilizar seus dados geográficos em diversos formatos para atender a diferentes requisitos técnicos e operacionais.
        """
        # Obtém os índices das linhas selecionadas
        selected_indexes = self.dlg.treeViewListaLinha.selectedIndexes()
        if selected_indexes:
            selected_index = selected_indexes[0] # Obtém o índice da primeira linha selecionada
            
             # Obtém o ID da camada a partir do item da árvore de lista
            layer_id = selected_index.model().itemFromIndex(selected_index).data()
            
            # Obtém a camada do projeto QGIS
            layer_to_save = QgsProject.instance().mapLayer(layer_id)
            if layer_to_save:
                # Mostrar diálogo para escolha dos formatos
                formatos = {
                    "DXF": ".dxf",
                    "KML": ".kml",
                    "GeoJSON": ".geojson",
                    "CSV": ".csv",
                    "Shapefile": ".shp",
                    "TXT": ".txt",
                    "Excel": ".xlsx",
                    "Geopackage": ".gpkg"}
                
                # Mostra um diálogo para que o usuário escolha os formatos
                dialogo = DialogoSalvarFormatos(formatos, self.dlg)
                resultado = dialogo.exec_()
                
                # Mostra um diálogo para que o usuário escolha os formatos
                if resultado:
                    diretorio = QFileDialog.getExistingDirectory(self.dlg, "Escolha um diretório para salvar os arquivos")
                    if diretorio:  # Verifica se um diretório foi selecionado
                        for extensao in dialogo.formatos_selecionados:
                            nome_arquivo = os.path.join(diretorio, layer_to_save.name() + extensao)
                            self.salvar_no_formato_especifico(layer_to_save, extensao, nome_arquivo)
                        return True  # Retorna True (operação bem-sucedida)
                    else:
                        return False  # O usuário cancelou a escolha do diretório
                else:
                    return False  # O usuário cancelou a escolha dos formatos
            else:
                return False # O usuário cancelou a escolha do local de salvamento
        return False

    def clone_layer(self):
        """
        Clona uma camada selecionada na interface do usuário do QGIS, permitindo ao usuário criar uma cópia exata de uma camada existente dentro do projeto.

        Funcionalidades:
        - Verifica se uma camada está selecionada na árvore de visualização de camadas.
        - Recupera o identificador (ID) da camada selecionada para localizar a camada no projeto QGIS.
        - Verifica se a camada selecionada é válida. Se não for, exibe uma mensagem de erro e encerra a função.
        - Utiliza um gerenciador de clonagem para clonar a camada, oferecendo ao usuário a opção de configurar parâmetros específicos para a clonagem, como cópia de atributos e configurações de estilo.
        - Atualiza a visualização da lista de camadas na interface após a clonagem para refletir a nova camada adicionada.

        Atribuição no código:
        Essencial para operações que requerem duplicação de camadas, permitindo aos usuários multiplicar camadas eficientemente sem recriar manualmente as configurações. Facilita a gestão de versões e experimentações com diferentes configurações de uma mesma camada, melhorando a eficácia do trabalho em projetos complexos de mapeamento e análise geoespacial.
        """
        # Obtém os índices das camadas selecionadas na interface do usuário
        selected_indexes = self.dlg.treeViewListaLinha.selectedIndexes()

        # Verifica se alguma camada foi realmente selecionada
        if not selected_indexes:
            # Exibe uma mensagem de erro se nenhuma camada estiver selecionada
            self.mostrar_mensagem("Nenhuma camada selecionada.", "Erro")
            return # Encerra a execução da função

        # Obtém o primeiro índice selecionado, assumindo uma única seleção
        selected_index = selected_indexes[0]
        # Recupera o ID da camada a partir do índice selecionado
        layer_id = selected_index.model().itemFromIndex(selected_index).data()
        # Busca a camada no projeto QGIS usando o ID recuperado
        layer_to_clone = QgsProject.instance().mapLayer(layer_id)

        if not layer_to_clone: # Verifica se a camada recuperada é válida
            self.mostrar_mensagem("A camada selecionada não é válida.", "Erro")
            return # Encerra a execução da função

        # Cria uma instância do CloneManager para gerenciar o processo de clonagem
        clone_manager = CloneManager(self, layer_to_clone)
        clone_manager.show_clone_options() # Exibe as opções de clonagem ao usuário

        # Atualiza a lista de camadas no treeView
        self.atualizar_treeView_lista_linha()

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

    def calcular_angulo_entre_pontos(self, ponto_inicial, ponto_final):
        """
        Calcula o ângulo entre dois pontos em graus, considerando o ponto inicial como referência.
        O resultado é ajustado para ficar no intervalo de 0 a 360 graus.

        Parâmetros:
        ponto_inicial (QgsPointXY): O ponto de partida para o cálculo do ângulo.
        ponto_final (QgsPointXY): O ponto de chegada para o cálculo do ângulo.

        Retorna:
        float: O ângulo entre os dois pontos em graus, ajustado para estar no intervalo de 0 a 360 graus.
        """
        # Calcula o ângulo em radianos e converte para graus
        angle = math.degrees(math.atan2(ponto_final.y() - ponto_inicial.y(), ponto_final.x() - ponto_inicial.x()))
        angle = (angle + 180) % 360 # Ajusta o ângulo para garantir que seja positivo
        if 90 < angle < 180: # Se o ângulo estiver no segundo quadrante, ajusta para o terceiro quadrante
            angle += 180
        elif 180 <= angle < 270: # Se o ângulo estiver no terceiro quadrante, ajusta para o quarto quadrante
            angle -= 180
        return angle % 360 # Retorna o ângulo ajustado para estar dentro do intervalo de 0 a 360 graus

    def calcular_rotulo_centralizado(self, geometry):
        """
        Identifica o segmento mais longo de uma geometria e calcula tanto seu ponto médio quanto o ângulo.

        Parâmetros:
        - geometry (QgsGeometry): A geometria sobre a qual os cálculos serão realizados.

        Retorna:
        - tuple: Retorna uma tupla contendo o ângulo e o ponto central (QgsPointXY) do segmento mais longo.

        Detalhes:
        - A função verifica primeiro se a geometria é multipartida (composta por várias linhas) ou uma única linha.
        - Para cada linha da geometria, a função itera sobre os segmentos formados por pontos consecutivos.
        - Para cada segmento, a função calcula o comprimento e, se este for o maior até então encontrado, atualiza as informações de comprimento máximo,
          além de calcular e armazenar o ponto médio e o ângulo desse segmento.
        - O ângulo é calculado a partir da função `calcular_angulo_entre_pontos`, que presume existir em algum local do mesmo objeto ou módulo.

        Exemplo de utilização:
        - A função pode ser utilizada para otimizar a posição de rótulos em mapas ou outras representações gráficas,
          colocando o rótulo no ponto médio do maior segmento de uma estrada, curso de rio, ou outra entidade linear.
        """
        max_length = -1  # Inicializa a variável para armazenar o comprimento máximo encontrado
        longest_segment_center = None  # Inicializa a variável para armazenar o centro do segmento mais longo
        angle = 0  # Inicializa o ângulo do segmento mais longo

        # Verifica se a geometria é multipartida
        if geometry.isMultipart():
            lines = geometry.asMultiPolyline() # Obtém as linhas da geometria multipartida
        else:
            lines = [geometry.asPolyline()] # Trata a geometria simples como uma lista de uma linha

        # Itera sobre cada linha na geometria
        for line in lines:
            # Itera sobre cada segmento na linha (ponto inicial até o penúltimo ponto)
            for i in range(len(line) - 1):
                segment_start = QgsPointXY(line[i]) # Ponto inicial do segmento
                segment_end = QgsPointXY(line[i + 1]) # Ponto final do segmento
                segment_length = segment_start.distance(segment_end) # Calcula o comprimento do segmento

                # Verifica se o comprimento atual é o maior encontrado até agora
                if segment_length > max_length:
                    max_length = segment_length # Atualiza o comprimento máximo
                    # Calcula o ponto médio do segmento
                    mid_x = (segment_start.x() + segment_end.x()) / 2
                    mid_y = (segment_start.y() + segment_end.y()) / 2
                    longest_segment_center = QgsPointXY(mid_x, mid_y)
                    # Calcula o ângulo do segmento usando a função definida anteriormente
                    angle = self.calcular_angulo_entre_pontos(segment_start, segment_end)

        # Retorna o ângulo e o centro do segmento mais longo
        return angle, longest_segment_center

    def calcular_rotulo_equidistante(self, geometry, distancia_intervalo):
        """
        Identifica o segmento mais longo de uma geometria e calcula tanto seu ponto médio quanto o ângulo.

        Parâmetros:
        - geometry (QgsGeometry): A geometria sobre a qual os cálculos serão realizados.

        Retorna:
        - tuple: Retorna uma tupla contendo o ângulo e o ponto central (QgsPointXY) do segmento mais longo.

        Detalhes:
        - A função verifica primeiro se a geometria é multipartida (composta por várias linhas) ou uma única linha.
        - Para cada linha da geometria, a função itera sobre os segmentos formados por pontos consecutivos.
        - Para cada segmento, a função calcula o comprimento e, se este for o maior até então encontrado, atualiza as informações de comprimento máximo,
          além de calcular e armazenar o ponto médio e o ângulo desse segmento.
        - O ângulo é calculado a partir da função `calcular_angulo_entre_pontos`, que presume existir em algum local do mesmo objeto ou módulo.

        Exemplo de utilização:
        - A função pode ser utilizada para otimizar a posição de rótulos em mapas ou outras representações gráficas,
          colocando o rótulo no ponto médio do maior segmento de uma estrada, curso de rio, ou outra entidade linear.
        """
        posicoes_rotulos = [] # Inicializa a lista que armazenará as posições dos rótulos
        
        # Verifica se a geometria é multipartida
        if geometry.isMultipart():
            lines = geometry.asMultiPolyline() # Obtém as linhas da geometria multipartida
        else:
            lines = [geometry.asPolyline()] # Trata a geometria simples como uma lista de uma linha

        for line in lines: # Itera sobre cada linha na geometria
            distancia_acumulada_desde_ultimo_rotulo = 0 # Inicia a distância acumulada desde o último rótulo

            # Itera sobre cada segmento na linha
            for i in range(len(line) - 1):
                segment_start = QgsPointXY(line[i]) # Ponto inicial do segmento
                segment_end = QgsPointXY(line[i + 1])  # Ponto final do segmento
                segment_length = segment_start.distance(segment_end) # Calcula o comprimento do segmento

                # Se for o primeiro segmento ou após adicionar um rótulo
                if i == 0 or distancia_acumulada_desde_ultimo_rotulo == 0:
                    angle = self.calcular_angulo_entre_pontos(segment_start, segment_end)
                    posicoes_rotulos.append((segment_start, angle))

                # Enquanto a distância acumulada e o comprimento do segmento forem suficientes para adicionar outro rótulo
                while distancia_acumulada_desde_ultimo_rotulo + segment_length >= distancia_intervalo:
                    # Calcula o excesso além do último rótulo
                    excesso = distancia_intervalo - distancia_acumulada_desde_ultimo_rotulo
                    ratio = excesso / segment_length  # Calcula a proporção do segmento que corresponde ao excesso
                    x = segment_start.x() + ratio * (segment_end.x() - segment_start.x()) # Calcula a posição x equidistante
                    y = segment_start.y() + ratio * (segment_end.y() - segment_start.y()) # Calcula a posição Y equidistante
                    angle = self.calcular_angulo_entre_pontos(segment_start, QgsPointXY(x, y)) # Calcula o ângulo no novo ponto
                    posicoes_rotulos.append((QgsPointXY(x, y), angle)) # Adiciona a nova posição e o ângulo
                    segment_start = QgsPointXY(x, y)  # Atualiza o ponto inicial do segmento para continuar a partir do novo ponto
                    segment_length -= excesso # Reduz o comprimento restante do segmento
                    distancia_acumulada_desde_ultimo_rotulo = 0 # Reseta a distância acumulada

                # Atualiza a distância acumulada com o comprimento restante do segmento
                distancia_acumulada_desde_ultimo_rotulo += segment_length

        # Se sobrou uma distância acumulada no final da linha, adiciona o último ponto
            if distancia_acumulada_desde_ultimo_rotulo > 0 and distancia_acumulada_desde_ultimo_rotulo < distancia_intervalo:
                final_point = QgsPointXY(line[-1]) # Último ponto da linha
                penultimate_point = QgsPointXY(line[-2]) # Penúltimo ponto da linha
                final_angle = self.calcular_angulo_entre_pontos(penultimate_point, final_point) # Calcula o ângulo no último segmento
                posicoes_rotulos.append((final_point, final_angle)) # Adiciona o último ponto e o ângulo
        
        return posicoes_rotulos # Retorna a lista de posições dos rótulos

    def calcular_rotulo_segmentado(self, geometry):
        """
        Calcula o ponto médio e o ângulo de cada segmento de uma geometria, normalmente utilizada para posicionar rótulos.

        Parâmetros:
        - geometry (QgsGeometry): A geometria sobre a qual os cálculos serão realizados.

        Retorna:
        - list: Uma lista de tuplas, cada uma contendo um objeto QgsPointXY (ponto médio do segmento) e um ângulo (orientação do segmento).

        Funcionalidades:
        - Verifica se a geometria é composta por múltiplas partes (multipartida) ou uma única linha.
        - Itera sobre cada linha da geometria.
        - Para cada linha, itera sobre cada segmento, calculando o ponto médio e o ângulo de inclinação.
        - Armazena cada ponto médio e ângulo em uma lista para uso posterior, como na colocação de rótulos.

        Utilização:
        - Esta função é especialmente útil em aplicações GIS onde rótulos precisam ser alinhados de maneira precisa com segmentos de linha.
          Pode ser usada para rotular estradas, rios, ou outras entidades lineares em mapas, garantindo que os rótulos sejam facilmente legíveis
          e esteticamente posicionados.
        """
        posicoes_rotulos = []  # Inicializa a lista que armazenará as posições dos rótulos

        # Verifica se a geometria é multipartida
        posicoes_rotulos = []
        if geometry.isMultipart():
            lines = geometry.asMultiPolyline() # Obtém as linhas da geometria multipartida
        else:
            lines = [geometry.asPolyline()] # Trata a geometria simples como uma lista de uma linha

        # Itera sobre cada linha na geometria
        for line in lines:
            # Itera sobre cada segmento na linha (ponto inicial até o penúltimo ponto)
            for i in range(len(line) - 1):
                segment_start = QgsPointXY(line[i]) # Ponto inicial do segmento
                segment_end = QgsPointXY(line[i + 1]) # Ponto final do segmento
                mid_x = (segment_start.x() + segment_end.x()) / 2
                mid_y = (segment_start.y() + segment_end.y()) / 2
                mid_point = QgsPointXY(mid_x, mid_y) # Cria o objeto QgsPointXY para o ponto médio

                # Calcula o ângulo do segmento usando a função definida anteriormente
                angle = self.calcular_angulo_entre_pontos(segment_start, segment_end)
                # Adiciona o ponto médio e o ângulo à lista de posições de rótulos
                posicoes_rotulos.append((mid_point, angle))

        return posicoes_rotulos # Retorna a lista de posições dos rótulos

    def exportar_rotulos_para_dxf(self, layer, msp, selected_attribute, rotulo_modo, distancia_intervalo, text_style=None):
        """
        Exporta rótulos para um arquivo DXF com base no modo de rotulagem especificado,
        utilizando as propriedades de texto fornecidas e os atributos selecionados de cada feição da camada.

        Parâmetros:
        - layer (QgsVectorLayer): Camada de onde os atributos e geometrias serão extraídos.
        - msp (Modelspace): Espaço de modelo do arquivo DXF onde os textos serão inseridos.
        - selected_attribute (str): Nome do atributo que será usado como texto do rótulo.
        - rotulo_modo (str): Modo de rotulagem ('Centralizado', 'Segmentado', 'Equidistante').
        - distancia_intervalo (float): Distância entre rótulos no modo 'Equidistante'.
        - text_style (dict, optional): Dicionário contendo estilo de texto como fonte e tamanho.

        Funcionalidades:
        - Verifica se o modo de rotulagem foi definido.
        - Itera sobre cada feição na camada para extrair a geometria e o valor do atributo selecionado.
        - Determina o modo de rotulagem e calcula as posições e ângulos correspondentes para os rótulos.
        - Adiciona cada rótulo ao espaço de modelo do arquivo DXF com os atributos de texto configurados.
        """
        # Verifica se o modo de rotulagem foi definido
        if not rotulo_modo:
            return  # Encerra a função se nenhum modo de rotulagem foi especificado

        # Itera sobre cada feição na camada
        for feat in layer.getFeatures():
            geom = feat.geometry() # Extrai a geometria da feição
            attribute_value = feat.attribute(selected_attribute) # Extrai o valor do atributo selecionado
            posicoes_rotulos = []  # Inicializa a lista que armazenará as posições e ângulos dos rótulos

            # Determina o modo de rotulagem e calcula as posições e ângulos correspondentes
            if rotulo_modo == "Centralizado":
                angle, position = self.calcular_rotulo_centralizado(geom)  # Calcula posição centralizada e ângulo
                posicoes_rotulos.append((position, angle)) # Adiciona a posição e ângulo à lista
            elif rotulo_modo == "Segmentado":
                posicoes_rotulos = self.calcular_rotulo_segmentado(geom)  # Calcula posições e ângulos para cada segmento
            elif rotulo_modo == "Equidistante" and distancia_intervalo:
                posicoes_rotulos = self.calcular_rotulo_equidistante(geom, distancia_intervalo) # Calcula posições equidistantes

            # Adiciona cada rótulo ao espaço de modelo do arquivo DXF
            for position, angle in posicoes_rotulos:
                msp.add_text(
                    str(attribute_value), # Converte o valor do atributo para string
                    dxfattribs={
                        'insert': (position.x(), position.y()), # Define a posição de inserção do texto
                        'height': text_style['size'], # Define a altura do texto baseada no estilo
                        'rotation': angle, # Define a rotação do texto baseada no ângulo calculado
                        'style': text_style['font'], # Define o estilo da fonte baseado no estilo
                        'layer': selected_attribute, # Define a camada do DXF baseada no atributo selecionado
                        'color': text_style.get('aci_color', 7)  # Usa o índice ACI ou padrão se não definido
                    })

    def definir_estilos_de_texto(self, doc, text_style):
        """
        Define os estilos de texto para um documento DXF, criando novos estilos conforme necessário.

        Parâmetros:
        - doc (ezdxf.document.Drawing): O documento DXF onde o estilo de texto será definido.
        - text_style (dict): Dicionário contendo as propriedades de estilo do texto, como a fonte.

        Funcionalidades:
        - Verifica se o estilo de texto especificado já existe no documento.
        - Se não existir, cria um novo estilo com os atributos fornecidos.
        """
        # Verifica se o estilo de texto já existe no documento
        if text_style['font'] not in doc.styles:
            # Cria um novo estilo no documento DXF com o nome e os atributos de fonte especificados
            doc.styles.new(name=text_style['font'], dxfattribs={'font': text_style['font']})

    def exportar_para_dxf(self):
        """
        Exporta uma camada selecionada para um arquivo DXF, utilizando diálogo de exportação para configurar detalhes.

        Funcionalidades:
        - Verifica se uma camada foi selecionada.
        - Valida se a camada selecionada é adequada para exportação (deve ser espacial e de geometria de linhas).
        - Abre um diálogo para o usuário configurar opções de exportação, como campo selecionado, atributos, estilo de texto, etc.
        - Executa a exportação para DXF se as configurações forem aceitas no diálogo.
        - Exibe mensagens de erro ou sucesso conforme o resultado da operação.
        """
        # Obtém o índice do item atualmente selecionado na árvore de camadas
        index = self.dlg.treeViewListaLinha.currentIndex()
        # Verifica se o índice é válido (ou seja, se há uma camada selecionada)
        if not index.isValid():
            self.mostrar_mensagem("Nenhuma camada selecionada.", "Erro")
            return

        # Obtém o ID da camada a partir do índice selecionado
        layer_id = index.model().itemFromIndex(index).data()
        # Busca a camada no projeto QGIS pelo ID
        layer = QgsProject.instance().mapLayer(layer_id)
        # Verifica se a camada é válida, espacial e do tipo de geometria de linhas
        if not layer or not layer.isSpatial() or layer.geometryType() != QgsWkbTypes.LineGeometry:
            self.mostrar_mensagem("A camada selecionada não é válida ou não é uma camada de linhas.", "Erro")
            return

        # Cria e exibe o diálogo de exportação
        dialog = ExportDialogDXF(layer, self.iface.mainWindow(), self.obter_cor_linha(layer))
        if dialog.exec_() == QDialog.Accepted:
            # Obtém as configurações do diálogo
            selected_field, selected_attribute, scale_factor = dialog.get_Values()
            rotulo_modo, distancia_intervalo = dialog.get_labeling_options()
            text_style = dialog.get_text_style()  # Acessa o estilo de texto configurado
            linetype_selected = dialog.get_selected_linetype()  # Obtém o linetype selecionado
            # Solicita ao usuário escolher o local para salvar o arquivo DXF
            filePath = self.escolher_local_para_salvar(layer.name() + ".dxf", "DXF Files (*.dxf)")
            if filePath:
                start_time = time.time()  # Inicia o cronômetro para medir a duração da exportação
                # Realiza a exportação com as configurações obtidas
                self.realizar_exportacao_para_dxf(layer, filePath, selected_field, selected_attribute, rotulo_modo, distancia_intervalo, text_style, dialog, linetype_selected, scale_factor)
                duration = time.time() - start_time  # Calcula a duração da operação

                # Exibir mensagem de sucesso com o tempo de execução e caminhos dos arquivos
                self.mostrar_mensagem(
                    f"Camada exportada para DXF em {duration:.2f} segundos", 
                    "Sucesso", 
                    caminho_pasta=os.path.dirname(filePath), 
                    caminho_arquivo=filePath)
        else:
            # Exibe mensagem de cancelamento se o diálogo de exportação não for aceito
            self.mostrar_mensagem("Exportação cancelada.", "Info")

    def obter_dxf_atributos_cor(self, feat, layer, linetype_selected, selected_field):
        """
        Obtém os atributos DXF relacionados à cor com base na simbologia da camada.

        Parâmetros:
        - feat (QgsFeature): A feição atual a ser processada.
        - layer (QgsVectorLayer): A camada de onde a feição foi extraída.
        - linetype_selected (str): O tipo de linha selecionado para exportação (ex.: CONTINUOUS, PERSONALIZAR).
        - selected_field (str): O campo selecionado para a camada DXF.

        Funcionalidades:
        - Verifica se o renderizador da camada é categorizado ou de símbolo único.
        - Avalia expressões para renderizadores categorizados para determinar o valor da categoria.
        - Converte a cor do símbolo associado à feição para o formato DXF (RGB).
        - Retorna um dicionário contendo a cor em formato DXF, o tipo de linha e o nome da camada.
        """

        symbol = None
        dxf_color = ezdxf.colors.rgb2int((255, 255, 255))  # Cor padrão (branco)

        # Verifica se o renderizador da camada é categorizado
        if isinstance(layer.renderer(), QgsCategorizedSymbolRenderer):
            renderer = layer.renderer()
            class_attribute = renderer.classAttribute()

            # Avalia a expressão para obter o valor da categoria
            expression = QgsExpression(class_attribute)
            context = QgsExpressionContext()
            context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
            context.setFeature(feat)
            
            class_value = expression.evaluate(context)
            
            # Encontra a categoria correspondente ao valor da feição
            for category in renderer.categories():
                if category.value() == class_value:
                    symbol = category.symbol()
                    break

        elif isinstance(layer.renderer(), QgsSingleSymbolRenderer):
            # Para renderização de símbolo único, obtém a cor do símbolo
            symbol = layer.renderer().symbol()

        # Se encontrou um símbolo, converte a cor RGB para o formato DXF
        if symbol is not None:
            line_color = symbol.color()
            dxf_color = ezdxf.colors.rgb2int((line_color.red(), line_color.green(), line_color.blue()))

        # Retorna os atributos DXF com a cor e o tipo de linha
        return {'true_color': dxf_color, 'linetype': linetype_selected, 'layer': selected_field}

    def realizar_exportacao_para_dxf(self, layer, filePath, selected_field, selected_attribute, rotulo_modo, distancia_intervalo, text_style, dialog, linetype_selected, scale_factor):
        """
        Exporta uma camada para o formato DXF, incluindo geometrias, atributos e rótulos.

        Parâmetros:
        - layer (QgsVectorLayer): A camada que será exportada.
        - filePath (str): O caminho do arquivo DXF onde a camada será salva.
        - selected_field (str): O campo selecionado para nomear a camada DXF.
        - selected_attribute (str): O atributo da feição que será utilizado para rotulagem.
        - rotulo_modo (str): O modo de rotulagem (Centralizado, Segmentado, Equidistante).
        - distancia_intervalo (float): A distância para a rotulagem equidistante (se aplicável).
        - text_style (dict): Dicionário contendo estilo de texto (fonte, tamanho, cor).
        - dialog (QDialog): A instância do diálogo que contém opções e configurações de exportação.
        - linetype_selected (str): O tipo de linha selecionado para exportação (ex.: CONTINUOUS, PERSONALIZAR).
        - scale_factor (float): O fator de escala a ser aplicado às linhas.

        Funcionalidades:
        - Inicia uma barra de progresso para acompanhar o processo de exportação.
        - Cria um novo documento DXF e define o modelspace.
        - Insere geometrias no DXF de acordo com o tipo de renderizador da camada.
        - Suporta a exportação de rótulos com diferentes modos de posicionamento.
        - Aplica padrões personalizados ou complexos às linhas dependendo das opções selecionadas.
        - Salva o arquivo DXF no caminho especificado.
        """

        # Inicia uma barra de progresso para o processo de exportação
        progressBar, progressMessageBar = self.iniciar_progress_bar(layer)

        # Cria um novo documento DXF e define o modelspace
        doc = ezdxf.new('R2013')
        msp = doc.modelspace()

        # Cria um índice espacial para a camada
        index = QgsSpatialIndex()
        for feat in layer.getFeatures():
            index.insertFeature(feat)

        # Define o estilo de linha no documento DXF
        dialog.definir_estilo_linha(doc, linetype_selected, scale_factor)

        # Define os estilos de texto no documento DXF
        self.definir_estilos_de_texto(doc, text_style)

        # Verifica se o campo selecionado existe na camada DXF, caso contrário, cria um novo
        if selected_field not in doc.layers:
            doc.layers.new(name=selected_field, dxfattribs={'color': 7})

        processed_features = 0
        for feat in layer.getFeatures():
            geom = feat.geometry()
            feature_length = geom.length()

            # Obtém os atributos DXF relacionados à cor usando a função atualizada
            dxfattribs = self.obter_dxf_atributos_cor(feat, layer, linetype_selected, selected_field)

            # Define o padrão personalizado ou complexo dependendo da seleção
            if linetype_selected == 'PERSONALIZAR':
                # Obtém o texto personalizado do usuário
                custom_text = dialog.linetypeInput.text()
                linetype_name = 'PERSONALIZAR'
                dialog.adicionar_padrao_personalizado(doc, linetype_name, scale_factor, feature_length, custom_text)
                dxfattribs['linetype'] = linetype_name
            elif linetype_selected == 'CERCA':
                linetype_name = 'CERCA'
                dialog.adicionar_padrao_complexo1(doc, linetype_name, scale_factor, feature_length)
                dxfattribs['linetype'] = linetype_name
            elif linetype_selected == 'CERCA 2':
                linetype_name = 'CERCA 2'
                dialog.adicionar_padrao_complexo2(doc, linetype_name, scale_factor, feature_length)
                dxfattribs['linetype'] = linetype_name
            elif linetype_selected == 'SETAS':
                linetype_name = 'SETAS'
                dialog.adicionar_padrao_setas(doc, linetype_name, scale_factor, feature_length)
                dxfattribs['linetype'] = linetype_name
            else:
                dxfattribs['linetype'] = linetype_selected

            # Adiciona as geometrias ao modelspace com os atributos definidos
            self.adicionar_geometrias_ao_modelspace(msp, geom, dxfattribs)
            processed_features += 1
            progressBar.setValue(processed_features)

        # Exporta os rótulos para o DXF
        self.exportar_rotulos_para_dxf(layer, msp, selected_attribute, rotulo_modo, distancia_intervalo, text_style)

        # Salva o documento DXF no caminho especificado
        doc.saveas(filePath)

        # Limpa a barra de mensagens após a exportação
        self.iface.messageBar().clearWidgets()

    def adicionar_geometrias_ao_modelspace(self, msp, geom, dxfattribs):
        """
        Adiciona geometrias ao espaço de modelo (modelspace) de um documento DXF.

        Parâmetros:
        - msp (ezdxf.layouts.Modelspace): O espaço de modelo no qual as geometrias serão adicionadas.
        - geom (QgsGeometry): A geometria que será adicionada ao DXF.
        - dxfattribs (dict): Atributos DXF a serem aplicados às linhas ou polilinhas criadas.

        Funcionalidades:
        - Verifica se a geometria é 3D e ajusta o tipo de objeto DXF a ser criado (polilinha 3D ou 2D).
        - Suporta geometrias simples e multipartidas, processando cada parte adequadamente.
        - Converte as coordenadas das geometrias do QGIS para o formato necessário no DXF.
        """
        # Verifica se a geometria é 3D
        is3D = QgsWkbTypes.hasZ(geom.wkbType())

        # Verifica se a geometria é multipartida
        if geom.isMultipart():
            parts = geom.constGet()  # Obtém as partes da geometria multipartida
            for part in parts:
                # Converte as coordenadas dos pontos para o formato DXF necessário
                points = [(point.x(), point.y(), point.z()) for point in part] if is3D else [(point.x(), point.y()) for point in part]
                if is3D:
                    # Adiciona uma polilinha 3D ao modelspace com os atributos DXF especificados
                    msp.add_polyline3d(points=points, dxfattribs=dxfattribs)
                else:
                    # Adiciona uma polilinha leve (LWPolyline) ao modelspace com os atributos DXF especificados
                    msp.add_lwpolyline(points, dxfattribs=dxfattribs)
        else:
            # Para geometrias simples, obtém as coordenadas diretamente
            points = geom.constGet()
            # Converte as coordenadas dos pontos para o formato necessário
            points_list = [(point.x(), point.y(), point.z()) for point in points] if is3D else [(point.x(), point.y()) for point in points]
            if is3D:
                # Adiciona uma polilinha 3D ao modelspace
                msp.add_polyline3d(points=points_list, dxfattribs=dxfattribs)
            else:
                # Adiciona uma polilinha leve ao modelspace
                msp.add_lwpolyline(points_list, dxfattribs=dxfattribs)

    def fechar_dialogo(self):
        """
        Fecha o diálogo associado a este UiManager.

        Este método é chamado quando o botão 'Fechar' é clicado. Ele simplesmente fecha o diálogo
        que está sendo gerenciado por este UiManager.

        Parâmetros:
        - self: Referência à instância atual do objeto (UiManager).

        A função não retorna valores.
        """
        self.dlg.close()  # Fecha o diálogo associado a este UiManager

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
        - self: Referência à instância atual do objeto (TreeViewEventFilter).
        - ui_manager: Instância do UiManager que será usada para acessar e manipular a interface do usuário.
        """
        super().__init__()  # Inicializa a classe base QObject
        self.ui_manager = ui_manager  # Armazena a referência ao UiManager para uso posterior

    def eventFilter(self, obj, event):
        """
        Filtra os eventos de movimentação do mouse sobre o treeView e exibe tooltips quando aplicável.

        Esta função intercepta eventos que ocorrem no treeView especificado. Se o evento for de movimento
        do mouse (QEvent.MouseMove) e o mouse estiver sobre um item válido no treeView, a função chama
        o método 'configurar_tooltip' do UiManager para exibir um tooltip com informações sobre o item.

        Parâmetros:
        - self: Referência à instância atual do objeto (TreeViewEventFilter).
        - obj: O objeto que está sendo monitorado (neste caso, o viewport do treeView).
        - event: O evento que está sendo filtrado (como QEvent.MouseMove).

        Retorno:
        - bool: O resultado da chamada à função 'eventFilter' da classe base, indicando se o evento foi processado.
        """
        # Verifica se o objeto é o viewport do treeView e se o evento é de movimento do mouse
        if obj == self.ui_manager.dlg.treeViewListaLinha.viewport() and event.type() == QEvent.MouseMove:
            # Obtém o índice do item no treeView sob o cursor do mouse
            index = self.ui_manager.dlg.treeViewListaLinha.indexAt(event.pos())
            if index.isValid():  # Verifica se o índice é válido (se o mouse está sobre um item)
                self.ui_manager.configurar_tooltip(index)  # Chama o método para configurar e exibir o tooltip
        # Retorna o resultado padrão do filtro de eventos
        return super().eventFilter(obj, event)  # Chama a implementação da classe base para continuar o processamento normal

class ExportDialogDXF(QDialog):
    def __init__(self, layer, parent=None, line_color=None):
        """
        Inicializa o diálogo de exportação DXF com opções configuráveis para rotulagem, estilo de linha e outros atributos.

        Parâmetros:
        - layer (QgsVectorLayer): Camada de origem para a exportação.
        - parent (QWidget): Widget pai do diálogo.
        - line_color (QColor): Cor padrão das linhas, preto se não especificado.

        Funcionalidades:
        - Configura opções interativas para seleção de atributos e estilos.
        - Permite ajustar a escala e o estilo das linhas diretamente no diálogo.
        - Integra com métodos para aplicar estilos personalizados e pré-configurados.
        """
        super(ExportDialogDXF, self).__init__(parent)
        self.layer = layer
        self.line_color = line_color if line_color else QColor(0, 0, 0)  # Usa a cor passada ou preto como padrão
        self.setWindowTitle("Exportar para DXF")

        # Inicializa as opções de rotulagem
        self.rotulo_modo = None
        self.distancia_intervalo = None
        self.text_style = {'font': 'Arial', 'size': 1, 'color': QColor(0, 0, 0)}
        self.is_linetypeInput_connected = False

        # Configuração do layout principal do diálogo
        layout = QVBoxLayout(self)
        frame = QFrame(self)
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Raised)
        layout.addWidget(frame)
        frame_layout = QVBoxLayout(frame)

        # Layout para seleção do campo da camada
        field_layout = QHBoxLayout()
        label = QLabel("Selecione o Campo da Camada:", frame)
        field_layout.addWidget(label)
        self.comboBox = QComboBox(frame)
        self.comboBox.addItems([field.name() for field in layer.fields()])
        field_layout.addWidget(self.comboBox)
        frame_layout.addLayout(field_layout)

        # Layout para seleção de atributos e botões de configuração de rotulagem e estilo
        attribute_layout = QHBoxLayout()
        attribute_label = QLabel("Selecione o Rótulo:", frame)
        attribute_layout.addWidget(attribute_label)
        self.attributeComboBox = QComboBox(frame)
        self.attributeComboBox.setFixedWidth(75)
        self.attributeComboBox.addItems([field.name() for field in layer.fields()])
        attribute_layout.addWidget(self.attributeComboBox)

        # Botões para configuração de rotulagem e estilo.
        self.labelingButton = QPushButton("Rotulagem", frame)
        self.labelingButton.clicked.connect(self.show_labeling_options)
        self.labelingButton.setFixedWidth(75)
        attribute_layout.addWidget(self.labelingButton)

        self.estiloButton = QPushButton("Estilo", frame)
        self.estiloButton.clicked.connect(self.choose_estilo)
        self.estiloButton.setFixedWidth(50)
        attribute_layout.addWidget(self.estiloButton)
        frame_layout.addLayout(attribute_layout)

        # ListWidget, DoubleSpinBox e GraphicsView
        list_layout = QVBoxLayout()
        
        self.linetypeList = QListWidget(frame)
        self.linetypeList.setMaximumSize(120, 101)
        list_layout.addWidget(self.linetypeList)

        # Em algum lugar após adicionar itens ao QListWidget, como no construtor do ExportDialogDXF:
        if self.linetypeList.count() > 0:
            self.linetypeList.setCurrentRow(0)  # Define o primeiro item como selecionado

        self.init_linetype_list()  # Método para preencher a lista de tipos de linha

        # Layout para os elementos à direita (DoubleSpinBox e GraphicsView)
        right_layout = QVBoxLayout()
        
        # Layout horizontal para o rótulo "Escala" e o QDoubleSpinBox
        scale_layout = QHBoxLayout()
        linetypeSizeLabel = QLabel("Escala: (Linear)", frame)
        scale_layout.addWidget(linetypeSizeLabel)
        
        self.linetypeSize = QDoubleSpinBox(frame)
        self.linetypeSize.setRange(0.5, 10.0)
        self.linetypeSize.setSingleStep(0.5)
        self.linetypeSize.setValue(1.0)
        scale_layout.addWidget(self.linetypeSize)

        self.linetypeSize.valueChanged.connect(self.update_linetype_preview)

        # Adiciona o layout da escala ao layout à direita
        right_layout.addLayout(scale_layout)

        # Layout horizontal para o linetypeInput e o botão Aplicar
        linetypeInputLayout = QHBoxLayout()
        self.linetypeInput = QLineEdit(frame)
        self.linetypeInput.setPlaceholderText("Digite o padrão personalizado...")
        self.linetypeInput.setMaxLength(8) # Limita o número de caracteres a 8
        linetypeInputLayout.addWidget(self.linetypeInput)

        self.applyButton = QPushButton("Aplicar", frame)
        self.applyButton.clicked.connect(self.apply_custom_linetype)
        self.applyButton.setFixedSize(36, 22)
        linetypeInputLayout.addWidget(self.applyButton)

        right_layout.addLayout(linetypeInputLayout)

        self.linetypeInput.setEnabled(False)
        self.applyButton.setEnabled(False)

        self.linetypePreview = QGraphicsView(frame)
        self.scene = QGraphicsScene()  # Cria uma cena para o QGraphicsView
        self.linetypePreview.setScene(self.scene)
        self.linetypePreview.setMaximumSize(190, 45)
        right_layout.addWidget(self.linetypePreview)

        # Conecta a seleção do QListWidget ao método de atualização do preview
        self.linetypeList.currentTextChanged.connect(self.update_linetype_preview)

        # Cria um layout horizontal e adiciona o layout da lista e o layout à direita
        horizontal_layout = QHBoxLayout()
        horizontal_layout.addLayout(list_layout)
        horizontal_layout.addLayout(right_layout)

        # Adiciona o layout horizontal ao layout principal do frame
        frame_layout.addLayout(horizontal_layout)

        # Botões de controle do diálogo.
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Exportar", frame)
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        self.cancel_button = QPushButton("Cancelar", frame)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        frame_layout.addLayout(button_layout)

    def update_linetype_input_status(self):
        """
        Atualiza o estado do campo de entrada e do botão de aplicação com base no tipo de linha selecionado pelo usuário.
        Habilita a entrada para padrões de linha personalizados e gerencia a conexão do evento de mudança de texto.

        Funcionalidades:
        - Verifica se um item está selecionado na lista de tipos de linha.
        - Habilita ou desabilita o campo de entrada e o botão de aplicar com base se o tipo de linha selecionado é personalizável.
        - Conecta ou desconecta o evento de mudança de texto para ativar o botão de aplicar somente quando há texto válido.
        """
        # Verifica se algum item está selecionado na lista de tipos de linha
        current_item = self.linetypeList.currentItem()
        if current_item is not None:
            # Verifica se o tipo de linha selecionado é "PERSONALIZAR"
            is_custom = current_item.text() == "PERSONALIZAR"
            self.linetypeInput.setEnabled(is_custom)
            # Habilita o botão de aplicar apenas se é personalizado e há texto no campo de entrada
            self.applyButton.setEnabled(is_custom and self.linetypeInput.text().strip() != "")

             # Gerencia a conexão do evento textChanged para atualizar o status do botão de aplicar
            if is_custom and not self.is_linetypeInput_connected:
                # Conecta o evento se ainda não estiver conectado
                self.linetypeInput.textChanged.connect(self.update_apply_button_status)
                self.is_linetypeInput_connected = True
            elif not is_custom and self.is_linetypeInput_connected:
                # Desconecta o evento se o tipo de linha não é personalizado e estava conectado
                self.linetypeInput.textChanged.disconnect(self.update_apply_button_status)
                self.is_linetypeInput_connected = False
        else:
            # Desativa o campo de entrada e o botão de aplicar se nenhum item está selecionado
            self.linetypeInput.setEnabled(False)
            self.applyButton.setEnabled(False)

    def update_apply_button_status(self):
        """
        Atualiza o estado de ativação do botão 'Aplicar' com base na presença de texto no campo de entrada 'linetypeInput'
        e se o item 'PERSONALIZAR' está selecionado na lista de tipos de linha.

        Funcionalidades:
        - Ativa o botão 'Aplicar' somente se houver texto no campo 'linetypeInput' e o tipo de linha 'PERSONALIZAR' estiver selecionado.
        """
        # Ativa o botão 'Aplicar' somente se o tipo de linha 'PERSONALIZAR' está selecionado e há texto não vazio no campo de entrada
        self.applyButton.setEnabled(self.linetypeList.currentItem().text() == "PERSONALIZAR" and self.linetypeInput.text().strip() != "")

    def apply_custom_linetype(self):
        """
        Aplica o tipo de linha personalizado selecionado, atualizando a pré-visualização conforme o padrão definido no campo de entrada.

        Funcionalidades:
        - Verifica se o item 'PERSONALIZAR' está selecionado na lista de tipos de linha.
        - Se 'PERSONALIZAR' está selecionado, chama a função para atualizar a pré-visualização da linha no visualizador gráfico.
        """
        # Verifica se o item selecionado na lista é 'PERSONALIZAR'
        if self.linetypeList.currentItem().text() == "PERSONALIZAR":
            # Chama a função para atualizar a pré-visualização baseada no padrão de linha definido pelo usuário
            self.update_linetype_preview()

    def init_linetype_list(self):
        """
        Inicializa a lista de tipos de linha no diálogo de exportação, oferecendo opções pré-definidas e uma opção para personalizar.

        Funcionalidades:
        - Limpa a lista atual de tipos de linha para garantir que não haja duplicatas ou entradas antigas.
        - Adiciona um conjunto padrão de tipos de linha, incluindo opções comuns e uma opção para personalização.
        - Conecta o evento de mudança de seleção na lista para atualizar o status do campo de entrada e do botão de aplicar conforme necessário.
        """
        # Limpa a lista existente para remover qualquer item anteriormente adicionado
        self.linetypeList.clear()

        # Adiciona itens à lista de tipos de linha
        # "PERSONALIZAR" permite ao usuário inserir um padrão de linha customizado
        # "CONTINUOUS", "DOTTED", "DASHED", "CENTER", "CERCA" são tipos padrões comuns em desenhos DXF
        self.linetypeList.addItems(["PERSONALIZAR", "CONTINUOUS", "DOTTED", "DASHED", "CENTER", "CERCA", "CERCA 2", "SETAS"])
         # Conecta a mudança de texto na lista de tipos de linha ao método que atualiza a habilitação do campo de entrada e do botão de aplicar
        self.linetypeList.currentTextChanged.connect(self.update_linetype_input_status)

    def adicionar_padrao_personalizado(self, doc, linetype_name, scale_factor, feature_length, text):
        """
        Adiciona um tipo de linha personalizado ao documento DXF que inclui texto especificado pelo usuário.

        Parâmetros:
        - doc (ezdxf.document.Drawing): O documento DXF ao qual o novo tipo de linha será adicionado.
        - linetype_name (str): Nome do novo tipo de linha.
        - scale_factor (float): Fator de escala usado para ajustar a escala do texto e do padrão.
        - feature_length (float): Comprimentorimento da feição a ser usado para calcular o número de repetições do padrão.
        - text (str): Texto a ser incorporado no padrão de linha.

        Funcionalidades:
        - Calcula a escala e o posicionamento do texto dentro do padrão.
        - Estima a largura do texto para centrar visualmente dentro do padrão.
        - Constrói o padrão de linha DXF que incorpora o texto.
        - Adiciona o novo tipo de linha ao documento DXF, se ainda não existir.
        """
        # Configurações iniciais de escalas e espaçamentos com base no fator de escala
        text_scale = 0.5 * scale_factor  # Escala do texto
        long_dash = 0.5 * scale_factor
        short_space = 2 * scale_factor
        text_gap = 0.25 * scale_factor  # Espaço após o texto

        # Estima a largura do texto (ajustando aqui para tentar centralizar melhor visualmente)
        estimated_text_width = len(text) * 1 * text_scale

        # Ajustes de posicionamento para o texto dentro do padrão de linha
        text_x_offset = -estimated_text_width / 2  # Ajuste baseado na largura estimada
        text_y_offset = -text_scale / 2  # Ajuste vertical para centralizar

        # Define o código para incorporar texto ao padrão com ajustes de posicionamento
        text_code = f'["{text}",STANDARD,S={text_scale},X={text_x_offset},Y={text_y_offset}]'

        # Calcula o comprimento total de uma repetição do padrão de linha
        single_pattern_length = 2 * (long_dash + text_gap + abs(short_space))

        # Determina o número de repetições necessárias para cobrir a feição
        num_repeats = max(1, int(feature_length / single_pattern_length))

        # Monta a string do padrão de linha incorporando o texto
        pattern_str = ("A," + ",".join([str(long_dash), str(-short_space), text_code, str(-short_space), "1"]) * num_repeats).rstrip(',')

        # Adiciona o novo tipo de linha ao documento DXF, caso ainda não exista
        if linetype_name not in doc.linetypes:
            doc.linetypes.add(
                name=linetype_name,
                pattern=pattern_str,
                description=f"Custom line with text '{text}' repeated",
                length=single_pattern_length)

    def adicionar_padrao_setas(self, doc, linetype_name, scale_factor, feature_length):
        """
        Adiciona um padrão de linha complexo com setas ">>" intercaladas ao documento DXF.

        Parâmetros:
        - doc: Documento DXF onde o padrão será adicionado.
        - linetype_name: Nome do tipo de linha a ser adicionado.
        - scale_factor: Fator de escala para ajustar o tamanho dos componentes do padrão.
        - feature_length: Comprimentorimento da feição para calcular o número de repetições do padrão.

        Descrição:
        A função define um padrão de linha complexo com setas ">>" intercaladas e adiciona esse padrão ao documento DXF.
        O tamanho e a posição dos componentes são ajustados de acordo com o fator de escala fornecido.
        """

        # Ajuste da escala dos componentes do padrão com base no fator de escala
        scale_symbol = 0.5 * scale_factor  # Mantém o tamanho das setas ">>"
        long_dash = 0.3 * scale_factor  # Comprimentorimento do traço ajustado
        short_dash = 0.5 * scale_factor  # Comprimentorimento do traço curto
        space_between_dashes = 0.1 * scale_factor  # Espaço entre traços

        # Código para as setas ">>", ajustando a posição vertical para centralizar na linha
        shape_code = f"[\">>\",STANDARD,S={scale_symbol},R=0.0,X=-0.25,Y=-0.25]"

        # Define o comprimento total de uma repetição do padrão
        single_pattern_length = long_dash + short_dash + space_between_dashes + scale_symbol

        # Calcula o número de repetições do padrão com base no comprimento da feição
        num_repeats = max(1, int(feature_length / single_pattern_length))

        # Monta a string do padrão de linha incorporando as setas ">>"
        pattern_str = f"A,{long_dash},{-space_between_dashes},{short_dash},{-space_between_dashes},{shape_code},{-space_between_dashes},{short_dash},{-space_between_dashes},{long_dash}"

        # Adiciona o novo tipo de linha ao documento DXF, se ainda não estiver presente
        if linetype_name not in doc.linetypes:
            doc.linetypes.add(
                name=linetype_name,
                pattern=pattern_str,
                description="Linha com setas ---->>---->>---->>",
                length=single_pattern_length
            )

    def draw_custom_setas_pattern(self, scene, x_start, y_start, x_end, y_end, scale_factor):
        """
        Desenha um padrão de linha com setas ">>" intercaladas no QGraphicsScene.

        Parâmetros:
        - scene: QGraphicsScene onde o padrão será desenhado.
        - x_start: Coordenada X inicial da linha.
        - y_start: Coordenada Y inicial da linha.
        - x_end: Coordenada X final da linha.
        - y_end: Coordenada Y final da linha.
        - scale_factor: Fator de escala para ajustar o tamanho dos componentes do padrão.

        Descrição:
        A função desenha uma linha horizontal no QGraphicsScene com setas ">>" intercaladas e traços contínuos entre elas.
        O tamanho e a posição dos componentes são ajustados de acordo com o fator de escala fornecido.
        """

        # Define a espessura da linha, garantindo uma espessura mínima de 1
        line_thickness = max(1, 1)
        pen = QPen(self.line_color, line_thickness)  # Configura a caneta para desenhar a linha com a cor especificada

        # Calcula a largura e altura do símbolo ">>" com base no fator de escala
        symbol_width = max(8, 20 * scale_factor)
        symbol_height = max(8, 20 * scale_factor)

        # Define o comprimento dos traços entre os símbolos ">>" e nos extremos da linha
        inter_symbol_dash_length = max(15, 15 * scale_factor)
        start_end_dash_length = max(15, 15 * scale_factor)

        # Calcula o comprimento total disponível para desenhar a linha
        total_length = x_end - x_start - 2 * start_end_dash_length

        # Calcula o número de símbolos ">>" que podem ser desenhados ao longo da linha
        num_symbols = max(3, int((total_length + inter_symbol_dash_length) / (symbol_width + inter_symbol_dash_length)))

        # Calcula o espaçamento entre os símbolos, garantindo que haja espaço suficiente
        symbol_spacing = (total_length - num_symbols * symbol_width - (num_symbols - 1) * inter_symbol_dash_length) / (num_symbols - 1) if num_symbols > 1 else 0

        # Desenha o primeiro traço da linha
        scene.addLine(x_start, y_start, x_start + start_end_dash_length, y_start, pen)
        current_pos = x_start + start_end_dash_length  # Atualiza a posição atual ao longo da linha

        # Itera sobre o número de símbolos ">>" para desenhá-los ao longo da linha
        for i in range(num_symbols):
            pos_x = current_pos  # Posição X atual para o símbolo ">>"
            text_item = scene.addText(">>")  # Adiciona o texto ">>" na cena
            font = text_item.font()
            font.setPointSizeF(10 * scale_factor)  # Ajusta o tamanho da fonte com base no fator de escala
            text_item.setFont(font)
            text_item.setPos(pos_x, y_start - (text_item.boundingRect().height() / 2))  # Centraliza o ">>" verticalmente na linha
            text_item.setDefaultTextColor(self.line_color)  # Define a cor do ">>"
            current_pos += symbol_width  # Atualiza a posição atual ao longo da linha após desenhar o ">>"

            # Desenha o traço entre os símbolos ">>" se não for o último símbolo
            if i < num_symbols - 1:
                scene.addLine(current_pos, y_start, current_pos + inter_symbol_dash_length, y_start, pen)
                current_pos += inter_symbol_dash_length  # Atualiza a posição atual ao longo da linha após desenhar o traço

        # Desenha o último traço da linha até o ponto final
        scene.addLine(current_pos, y_start, x_end, y_start, pen)

        # Ajusta os limites da cena para incluir todos os elementos desenhados
        scene.setSceneRect(scene.itemsBoundingRect())

        # Ajusta a visualização da linha para garantir que ela se encaixe corretamente na área visível
        self.linetypePreview.fitInView(scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def adicionar_padrao_complexo1(self, doc, linetype_name, scale_factor, feature_length):
        """
        Adiciona um tipo de linha complexo ao documento DXF que inclui símbolos definidos pelo usuário.

        Parâmetros:
        - doc (ezdxf.document.Drawing): O documento DXF ao qual o novo tipo de linha será adicionado.
        - linetype_name (str): Nome do novo tipo de linha.
        - scale_factor (float): Fator de escala usado para ajustar a escala dos componentes do padrão.
        - feature_length (float): Comprimentorimento da feição para calcular o número de repetições do padrão.

        Funcionalidades:
        - Ajusta a escala dos componentes do padrão, incluindo traços e espaços.
        - Define um código de símbolo personalizado que é incorporado ao padrão de linha.
        - Calcula o número necessário de repetições para cobrir a feição de forma eficaz.
        - Cria e adiciona o novo tipo de linha ao documento DXF, caso ainda não exista.
        """
        # Ajuste da escala dos componentes do padrão com base no fator de escala
        scale_symbol = 0.5 * scale_factor  # Mantém o tamanho dos símbolos "[]"
        long_dash = 0.5 * scale_factor # Comprimentorimento do traço ajustado para coincidir com o símbolo
        short_space = 0.5 * scale_factor  # Define o espaço entre os componentes do padrão

        # Código para o símbolo customizado
        shape_code = f"[132,ltypeshp.shx,x={-scale_symbol},s={scale_symbol}]"

        # Define o comprimento total de uma repetição do padrão
        single_pattern_length = 2  # Aumentar para melhorar a visualização

        # Calcula o número de repetições do padrão com base no comprimento da feição
        num_repeats = max(1, int(feature_length / single_pattern_length))

        # Criando o padrão como uma string
        pattern_str = ("A," + ",".join([str(long_dash), str(-short_space), shape_code, str(-short_space), "1"]) * num_repeats).rstrip(',')

        # Adiciona o novo tipo de linha ao documento DXF, se ainda não estiver presente
        if linetype_name not in doc.linetypes:
            doc.linetypes.add(linetype_name,
                pattern=pattern_str,
                description="Grenze eckig ----[]-----[]----[]-----[]----[]--",
                length=single_pattern_length)  # Ajuste do comprimento para flexibilidade

    def adicionar_padrao_complexo2(self, doc, linetype_name, scale_factor, feature_length):
        """
        Adiciona um padrão de linha complexo com símbolos "X" intercalados ao documento DXF.

        Parâmetros:
        - doc: Documento DXF onde o padrão será adicionado.
        - linetype_name: Nome do tipo de linha a ser adicionado.
        - scale_factor: Fator de escala para ajustar o tamanho dos componentes do padrão.
        - feature_length: Comprimentorimento da feição para calcular o número de repetições do padrão.

        Descrição:
        A função define um padrão de linha complexo com símbolos "X" intercalados e adiciona esse padrão ao documento DXF.
        O tamanho e a posição dos componentes são ajustados de acordo com o fator de escala fornecido.
        """

        # Ajuste da escala dos componentes do padrão com base no fator de escala
        scale_symbol = 0.5 * scale_factor  # Mantém o tamanho dos símbolos "X"
        long_dash = 0.5 * scale_factor  # Comprimentorimento do traço ajustado
        short_space = 0.1 * scale_factor  # Define o espaço entre os componentes do padrão

        # Ajuste dinâmico das posições horizontal e vertical do símbolo "X"
        x_offset = -0.17 * scale_factor  # Ajusta a posição horizontal de acordo com o fator de escala
        y_offset = -0.25 * scale_factor  # Ajusta a posição vertical de acordo com o fator de escala

        # Código para o símbolo "X", ajustando as posições horizontal e vertical para centralizar na linha
        shape_code = f"[\"X\",STANDARD,S={scale_symbol},R=0.0,X={x_offset},Y={y_offset}]"

        # Define o comprimento total de uma repetição do padrão
        single_pattern_length = long_dash + short_space + scale_symbol

        # Calcula o número de repetições do padrão com base no comprimento da feição
        num_repeats = max(1, int(feature_length / single_pattern_length))

        # Monta a string do padrão de linha incorporando o símbolo "X"
        pattern_str = f"A,{long_dash},{-short_space},{shape_code},{-short_space},1"

        # Adiciona o novo tipo de linha ao documento DXF, se ainda não estiver presente
        if linetype_name not in doc.linetypes:
            doc.linetypes.add(
                name=linetype_name,
                pattern=pattern_str,
                description="Linha com X ----X-----X----X-----X----X--",
                length=single_pattern_length
            )

    def draw_custom_complex_pattern2(self, scene, x_start, y_start, x_end, y_end, scale_factor):
        """
        Desenha um padrão complexo personalizado no QGraphicsScene, representando uma linha com o símbolo "X" intercalado.
        
        Parâmetros:
        - scene: QGraphicsScene onde o padrão será desenhado.
        - x_start: Coordenada X inicial da linha.
        - y_start: Coordenada Y inicial da linha.
        - x_end: Coordenada X final da linha.
        - y_end: Coordenada Y final da linha.
        - scale_factor: Fator de escala para ajustar o tamanho dos componentes do padrão.
        
        Descrição:
        A função desenha uma linha horizontal no QGraphicsScene com o símbolo "X" intercalado. O padrão é ajustado
        de acordo com o fator de escala fornecido. A linha entre os símbolos "X" é contínua e próxima ao símbolo.
        """

        # Define a espessura da linha, garantindo uma espessura mínima de 1
        line_thickness = max(1, 1)
        pen = QPen(self.line_color, line_thickness)  # Configura a caneta para desenhar a linha com a cor especificada

        # Calcula a largura e altura do símbolo "X" com base no fator de escala
        symbol_width = max(8, 20 * scale_factor)
        symbol_height = max(8, 20 * scale_factor)

        # Define o comprimento dos traços entre os símbolos "X" e nos extremos da linha
        inter_symbol_dash_length = max(15, 15 * scale_factor)
        start_end_dash_length = max(15, 15 * scale_factor)

        # Calcula o comprimento total disponível para desenhar a linha
        total_length = x_end - x_start - 2 * start_end_dash_length

        # Calcula o número de símbolos "X" que podem ser desenhados ao longo da linha
        num_symbols = max(3, int((total_length + inter_symbol_dash_length) / (symbol_width + inter_symbol_dash_length)))

        # Calcula o espaçamento entre os símbolos, garantindo que haja espaço suficiente
        symbol_spacing = (total_length - num_symbols * symbol_width - (num_symbols - 1) * inter_symbol_dash_length) / (num_symbols - 1) if num_symbols > 1 else 0

        # Desenha o primeiro traço da linha
        scene.addLine(x_start, y_start, x_start + start_end_dash_length, y_start, pen)
        current_pos = x_start + start_end_dash_length  # Atualiza a posição atual ao longo da linha

        # Itera sobre o número de símbolos "X" para desenhá-los ao longo da linha
        for i in range(num_symbols):
            pos_x = current_pos  # Posição X atual para o símbolo "X"
            text_item = scene.addText("X")  # Adiciona o texto "X" na cena
            font = text_item.font()
            font.setPointSizeF(10 * scale_factor)  # Ajusta o tamanho da fonte com base no fator de escala
            text_item.setFont(font)
            text_item.setPos(pos_x, y_start - (text_item.boundingRect().height() / 2))  # Centraliza o "X" verticalmente na linha
            text_item.setDefaultTextColor(self.line_color)  # Define a cor do "X"
            current_pos += symbol_width  # Atualiza a posição atual ao longo da linha após desenhar o "X"

            # Desenha o traço entre os símbolos "X" se não for o último símbolo
            if i < num_symbols - 1:
                scene.addLine(current_pos, y_start, current_pos + inter_symbol_dash_length, y_start, pen)
                current_pos += inter_symbol_dash_length  # Atualiza a posição atual ao longo da linha após desenhar o traço

        # Desenha o último traço da linha até o ponto final
        scene.addLine(current_pos, y_start, x_end, y_start, pen)

        # Ajusta os limites da cena para incluir todos os elementos desenhados
        scene.setSceneRect(scene.itemsBoundingRect())

        # Ajusta a visualização da linha para garantir que ela se encaixe corretamente na área visível
        self.linetypePreview.fitInView(scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def definir_estilo_linha(self, doc, linetype_selected, scale_factor):
        """
        Define ou atualiza um estilo de linha no documento DXF com base no tipo de linha selecionado e no fator de escala aplicado.

        Parâmetros:
        - doc (ezdxf.document.Drawing): O documento DXF onde o estilo de linha será definido.
        - linetype_selected (str): O tipo de linha selecionado pelo usuário.
        - scale_factor (float): Fator de escala que ajusta o tamanho e o espaçamento dos elementos do padrão de linha.

        Funcionalidades:
        - Verifica se o tipo de linha já existe no documento.
        - Se não existir, cria um novo estilo de linha baseado no tipo selecionado e ajusta de acordo com o scale_factor.
        - Adiciona padrões de linha como CONTINUOUS, DOTTED, DASHED e CENTER com especificações detalhadas.
        - Atualiza a lista de tipos de linha na interface do usuário, se necessário.
        """
        # Verifica se o tipo de linha já está definido no documento DXF
        if linetype_selected not in doc.linetypes:
            # Adiciona o tipo de linha CONTINUOUS sem padrão específico
            if linetype_selected == 'CONTINUOUS':
                doc.linetypes.new(linetype_selected, dxfattribs={'pattern': []})

            # Define o padrão para linhas pontilhadas ajustando com o scale_factor
            elif linetype_selected == 'DOTTED':
                # Aplica o scale_factor ao padrão para estilo DOTTED
                dotted_pattern = [0.0, 1.0 * scale_factor, 0.0, -1.0 * scale_factor]
                doc.linetypes.new(linetype_selected, dxfattribs={'pattern': dotted_pattern})

            # Define o padrão para linhas tracejadas ajustando com o scale_factor
            elif linetype_selected == 'DASHED':
                # Aplica o scale_factor ao padrão para estilo DASHED
                dashed_pattern = [1.0 * scale_factor, -1.0 * scale_factor]
                doc.linetypes.new(linetype_selected, dxfattribs={'pattern': dashed_pattern})

            # Adiciona um estilo de linha CENTER com segmentos e espaços definidos pelo scale_factor
            elif linetype_selected == 'CENTER':
                # Adiciona o novo estilo de linha CENTER
                center_pattern = [4.0 * scale_factor, -1.0 * scale_factor, 2.0 * scale_factor, -1.0 * scale_factor, 4.0 * scale_factor]
                doc.linetypes.new(linetype_selected, dxfattribs={'pattern': center_pattern})

            # Após adicionar o novo estilo de linha, atualiza a lista de tipos de linha na interface do usuário para refletir as mudanças
            self.init_linetype_list()

    def update_linetype_preview(self):
        """
        Atualiza a pré-visualização do tipo de linha selecionado no diálogo de exportação, 
        ajustando a visualização conforme o estilo e o fator de escala definidos.

        Funcionalidades:
        - Verifica se um item está selecionado na lista de tipos de linha.
        - Limpa a cena gráfica anterior para garantir que a nova visualização seja limpa.
        - Aplica as configurações de estilo de linha baseadas na seleção do usuário.
        - Ajusta a pré-visualização de acordo com o tipo de linha, aplicando escala e estilo correspondentes.
        - Desenha a linha na cena gráfica para visualização.
        """
        # Verifica se há um item selecionado na lista de tipos de linha no QListWidget
        current_item = self.linetypeList.currentItem()
        if not current_item:
            return  # Retorna imediatamente se não houver item selecionado

        # Obtém o tipo de linha e o fator de escala da interface
        linetype = current_item.text()
        scale_factor = self.linetypeSize.value()  # Obtém o valor atual do QDoubleSpinBox
        self.scene.clear()  # Limpa a cena para desenhar o novo estilo de linha

        # Configura o objeto QPen com a cor da linha selecionada e a espessura básica
        pen = QPen(self.line_color, 1)

        # Aplica estilos diferentes dependendo do tipo de linha selecionado
        if linetype == "DOTTED":
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern([4 * scale_factor, 5 * scale_factor]) # Aplica a escala ao padrão de traço

        elif linetype == "DASHED":
            pen.setStyle(Qt.DotLine)
            pen.setDashPattern([0.5 * scale_factor, 5 * scale_factor]) # Aplica a escala ao padrão de traço

        elif linetype == "CENTER":
            pen.setStyle(Qt.CustomDashLine)
            # Aqui, ajustamos o padrão de acordo com a descrição anterior
            pen.setDashPattern([10.0 * scale_factor, 4.0 * scale_factor, 6.0 * scale_factor, 4.0 * scale_factor, 10.0 * scale_factor])

        elif linetype == "CONTINUOUS":
            pen.setStyle(Qt.SolidLine)  # Linha contínua

        elif linetype == "CERCA":
            # Chama uma função auxiliar para desenhar um padrão complexo específico
            self.draw_custom_complex_pattern(self.scene, 10, 20, 180, 20, scale_factor)

        elif linetype == "CERCA 2":
            self.draw_custom_complex_pattern2(self.scene, 10, 20, 180, 20, scale_factor)

        elif linetype == "SETAS":
            self.draw_custom_setas_pattern(self.scene, 10, 20, 180, 20, scale_factor)

        elif linetype == "PERSONALIZAR":
            # Obtém texto personalizado e chama função para desenhar padrão de texto
            custom_text = self.linetypeInput.text()  # Supõe que há um QLineEdit chamado linetypeInput para entrada de texto
            if custom_text:
                self.draw_custom_text_pattern(self.scene, 10, 20, 180, 20, scale_factor, custom_text)

        # Desenha a linha na cena, exceto para os tipos especiais que já adicionam suas próprias linhas
        if linetype != "CERCA" and linetype != "CERCA 2" and linetype != "SETAS" and linetype != "PERSONALIZAR":
            self.scene.addLine(10, 20, 180, 20, pen)

        # Ajusta a visualização para enquadrar corretamente a linha dentro da área visível
        self.linetypePreview.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def draw_custom_text_pattern(self, scene, x_start, y_start, x_end, y_end, scale_factor, text):
        """
        Desenha um padrão personalizado de texto na cena gráfica.

        Parâmetros:
        - scene (QGraphicsScene): A cena onde o padrão será desenhado.
        - x_start, y_start (float): Posição inicial da linha no eixo x e y.
        - x_end, y_end (float): Posição final da linha no eixo x e y.
        - scale_factor (float): Fator de escala usado para ajustar o tamanho dos elementos gráficos.
        - text (str): Texto a ser incluído no padrão.

        Funcionalidades:
        - Configura a caneta para desenho com espessura e cor adequadas.
        - Define a fonte e tamanho do texto com base no fator de escala.
        - Calcula a largura do texto e ajusta o padrão de traços para combinar visualmente com o texto.
        - Desenha repetidamente o texto e traços ao longo da linha, garantindo que o padrão preencha o comprimento definido.
        """
        # Configurações de espessura da linha e da fonte
        line_thickness = max(1, 0.5 * scale_factor)  # Garante uma espessura mínima para a linha
        pen = QPen(self.line_color, line_thickness)
        
        # Definindo a fonte para o texto
        font_size = max(5, 5 * scale_factor)  # Garante um tamanho mínimo para a fonte
        font = QFont("Arial", int(font_size))

        # Comprimentorimento estimado do texto
        text_width = QFontMetrics(font).boundingRect(text).width()

        # Comprimentorimento dos traços
        dash_length = max(5, 5 * scale_factor)  # Garante um comprimento mínimo para os traços

        # Espaço adicional entre traços e texto
        additional_space = max(2, 5 * scale_factor)  # Garante um espaço mínimo

        # Comprimentorimento total de uma repetição do padrão
        pattern_length = dash_length + text_width + dash_length + 2 * additional_space

        # Calculando o número de repetições do texto baseado no comprimento da linha
        total_length = x_end - x_start
        num_repeats = max(1, int(total_length / pattern_length))  # Garante pelo menos uma repetição

        # Posição inicial
        current_pos = x_start

        # Adiciona o texto e os traços repetidamente ao longo da linha
        for i in range(num_repeats):
            # Desenha o traço inicial
            scene.addLine(current_pos, y_start, current_pos + dash_length, y_start, pen)
            current_pos += dash_length + additional_space

            # Adiciona o texto
            text_item = scene.addText(text, font)
            # Ajusta a posição y para centralizar verticalmente com a linha
            text_y_position = y_start/2 - QFontMetrics(font).height() / 2 + QFontMetrics(font).ascent() / 2
            text_item.setPos(current_pos, text_y_position)
            text_item.setDefaultTextColor(self.line_color)
            current_pos += text_width + additional_space

            # Desenha o traço final
            scene.addLine(current_pos, y_start, current_pos + dash_length, y_start, pen)
            current_pos += dash_length

        # Assegura que tudo seja visível dentro dos limites da visualização
        scene.setSceneRect(scene.itemsBoundingRect())  # Ajusta a área da cena para incluir todos os itens
        self.linetypePreview.fitInView(scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def draw_custom_complex_pattern(self, scene, x_start, y_start, x_end, y_end, scale_factor):
        """
        Desenha um padrão complexo com símbolos e traços numa cena gráfica.

        Parâmetros:
        - scene (QGraphicsScene): Cena onde o padrão será desenhado.
        - x_start, y_start (int): Coordenadas iniciais da linha no eixo X e Y.
        - x_end, y_end (int): Coordenadas finais da linha no eixo X e Y.
        - scale_factor (float): Fator de escala para ajustar o tamanho dos símbolos e traços.

        Funcionalidades:
        - Configura a caneta para desenhar com espessura adequada.
        - Calcula o tamanho e a disposição dos símbolos e traços com base no comprimento total disponível.
        - Desenha um padrão repetitivo de símbolos e traços ajustados para visualização clara.
        """
        # Define a espessura da linha baseada no scale_factor
        line_thickness = max(1, 1)  # Ajuste para evitar excesso

        # Configura a caneta para desenhar a linha e os símbolos
        pen = QPen(self.line_color, line_thickness)

        # Configurações para o símbolo "[]"
        symbol_width = max(8, 12 * scale_factor)  # Garante tamanho adequado
        symbol_height = max(8, 12 * scale_factor)  # Mantém proporção

        # Comprimentorimento dos traços entre os símbolos e nos extremos
        inter_symbol_dash_length = max(5, 8 * scale_factor)
        start_end_dash_length = max(5, 8 * scale_factor)

        # Comprimentorimento disponível para símbolos e traços
        total_length = x_end - x_start - 2 * start_end_dash_length
        num_symbols = max(3, int((total_length + inter_symbol_dash_length) / (symbol_width + inter_symbol_dash_length)))
        symbol_spacing = (total_length - num_symbols * symbol_width - (num_symbols - 1) * inter_symbol_dash_length) / (num_symbols - 1) if num_symbols > 1 else 0

        # Desenha o primeiro traço
        scene.addLine(x_start, y_start, x_start + start_end_dash_length, y_start, pen)
        current_pos = x_start + start_end_dash_length

        # Adiciona os retângulos como símbolos "[]"
        for i in range(num_symbols):
            pos_x = current_pos
            rect_item = QGraphicsRectItem(QRectF(pos_x, y_start - (symbol_height / 2), symbol_width, symbol_height))
            rect_item.setPen(pen)
            rect_item.setBrush(QColor(255, 255, 255))
            scene.addItem(rect_item)
            current_pos += symbol_width

            if i < num_symbols - 1:
                scene.addLine(current_pos, y_start, current_pos + inter_symbol_dash_length, y_start, pen)
                current_pos += inter_symbol_dash_length

        # Desenha o último traço
        scene.addLine(current_pos, y_start, x_end, y_start, pen)

        # Ajusta os limites da cena para incluir todos os elementos
        scene.setSceneRect(scene.itemsBoundingRect())
        self.linetypePreview.fitInView(scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def show_labeling_options(self):
        """
        Exibe um diálogo de opções de rotulagem, permitindo ao usuário escolher entre modos de rotulagem diferentes
        e definir parâmetros específicos para cada modo.
        """
        # Cria um novo diálogo de opções de rotulagem
        dialog = QDialog(self)
        dialog.setWindowTitle("Opções de Rotulagem")
        layout = QVBoxLayout(dialog)

        # Cria um quadro para conter os widgets de opção
        frame = QFrame(dialog)
        frame.setFrameShape(QFrame.StyledPanel)  # Estilo do painel
        frame.setFrameShadow(QFrame.Raised)  # Sombra elevada
        layout.addWidget(frame)  # Adiciona o frame ao layout

        # Layout vertical para os widgets dentro do frame       
        frame_layout = QVBoxLayout(frame)

        # Cria botões de opção para diferentes modos de rotulagem
        radioButtonCentralizado = QRadioButton("Centralizado")
        radioButtonSegmentado = QRadioButton("Segmentado")
        radioButtonEquidistante = QRadioButton("Equidistante")

        # Cria e configura uma SpinBox para definir a distância no modo Equidistante
        spinBoxDistancia = QSpinBox()
        spinBoxDistancia.setMinimum(1)
        spinBoxDistancia.setMaximum(1000)
        spinBoxDistancia.setSingleStep(1)
        spinBoxDistancia.setValue(10)
        spinBoxDistancia.setSuffix(" m")
        spinBoxDistancia.setEnabled(False) # Desabilitada inicialmente

        # Adiciona os botões de rádio ao layout
        frame_layout.addWidget(radioButtonCentralizado)
        frame_layout.addWidget(radioButtonSegmentado)

        # Adiciona os botões de rádio ao layout
        equidistante_layout = QHBoxLayout()
        equidistante_layout.addWidget(radioButtonEquidistante)
        equidistante_layout.addWidget(spinBoxDistancia)
        frame_layout.addLayout(equidistante_layout)

        # Conecta o sinal de alteração do botão Equidistante para habilitar/desabilitar a SpinBox
        radioButtonEquidistante.toggled.connect(lambda checked: spinBoxDistancia.setEnabled(checked))

        # Cria e configura o botão OK
        ok_button = QPushButton("OK", dialog)
        ok_button.setEnabled(False)  # Inicia com o botão OK desativado
        # Ativar o botão OK quando qualquer radioButton for selecionado
        radioButtonCentralizado.toggled.connect(lambda checked: ok_button.setEnabled(True))
        radioButtonSegmentado.toggled.connect(lambda checked: ok_button.setEnabled(True))
        radioButtonEquidistante.toggled.connect(lambda checked: ok_button.setEnabled(checked))

        # Cria e configura o botão Cancelar
        cancel_button = QPushButton("Cancelar", dialog)
        cancel_button.clicked.connect(dialog.reject)

        # Atualiza o estado do botão OK com base na seleção dos radio buttons
        def update_ok_button_status():
            """
            Atualiza o estado do botão OK baseado na seleção dos botões de rádio.
            Habilita o botão OK se algum dos modos de rotulagem estiver selecionado.
            """
            # Verifica se algum dos botões de rádio está selecionado para habilitar o botão OK
            if radioButtonCentralizado.isChecked() or radioButtonSegmentado.isChecked() or radioButtonEquidistante.isChecked():
                ok_button.setEnabled(True)
            else:
                ok_button.setEnabled(False)

        # Conecta os sinais dos botões de rádio ao método que atualiza o estado do botão OK
        radioButtonCentralizado.toggled.connect(update_ok_button_status)
        radioButtonSegmentado.toggled.connect(update_ok_button_status)
        radioButtonEquidistante.toggled.connect(update_ok_button_status)

        # Layout para os botões OK e Cancelar
        button_layout = QHBoxLayout()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        frame_layout.addLayout(button_layout)

        # Quando OK for clicado, salve as opções e atualize o texto do botão
        ok_button.clicked.connect(lambda: self.update_labeling_options(radioButtonCentralizado, radioButtonSegmentado, radioButtonEquidistante, spinBoxDistancia, dialog))

        # Quando clicar em Cancelar, redefina o texto do botão para remover a marca de seleção
        cancel_button.clicked.connect(lambda: self.reset_labeling_button(dialog))

        dialog.exec_()

    def reset_labeling_button(self, dialog):
        """
        Redefine o estado do botão de rotulagem para remover a marca de seleção e fecha o diálogo.
        """
        self.labelingButton.setText("Rotulagem")  # Reset the text to remove the check mark
        self.labelingButton.setStyleSheet("")  # Clear any custom styles to restore default appearance
        dialog.reject()

    def update_labeling_options(self, rb1, rb2, rb3, spinBox, dialog):
        """
        Atualiza as opções de rotulagem com base na seleção do usuário e fecha o diálogo.

        Parâmetros:
        - rb1 (QRadioButton): Botão para selecionar o modo de rotulagem 'Centralizado'.
        - rb2 (QRadioButton): Botão para selecionar o modo de rotulagem 'Segmentado'.
        - rb3 (QRadioButton): Botão para selecionar o modo de rotulagem 'Equidistante'.
        - spinBox (QSpinBox): Caixa de entrada para definir a distância no modo 'Equidistante'.
        - dialog (QDialog): Diálogo que contém as opções de rotulagem.

        Funcionalidades:
        - Verifica qual botão de rádio está marcado e define o modo de rotulagem apropriado.
        - No caso do modo 'Equidistante', também captura o valor da distância definido pelo usuário.
        - Fecha o diálogo e atualiza o texto e o estilo do botão de rotulagem para refletir a seleção.
        """
        # Verifica qual modo de rotulagem foi selecionado e atualiza a propriedade rotulo_modo
        if rb1.isChecked():
            self.rotulo_modo = "Centralizado"
        elif rb2.isChecked():
            self.rotulo_modo = "Segmentado"
        elif rb3.isChecked():
            self.rotulo_modo = "Equidistante"
            self.distancia_intervalo = spinBox.value()
        dialog.accept()
        # Atualiza o texto do botão de rotulagem na interface principal para indicar que uma configuração foi selecionada
        self.labelingButton.setText("Rotulagem ✓")  # Atualiza o texto do botão para incluir um "✓"
        # Altera a cor do texto do botão para verde, fornecendo um feedback visual de que a configuração foi aplicada
        self.labelingButton.setStyleSheet("QPushButton { color: green; }")

    def choose_estilo(self):
        """
        Abre uma caixa de diálogo para que o usuário escolha o estilo de texto, incluindo fonte, tamanho e cor.

        Funcionalidades:
        - Inicia uma caixa de diálogo com o título "Estilo do Texto".
        - Utiliza um QVBoxLayout para organizar os elementos verticalmente dentro do diálogo.
        - Adiciona um QFrame ao diálogo para delimitar visualmente a área de interação do usuário.
        - Utiliza um QVBoxLayout dentro do QFrame para organizar os controles de seleção de estilo.
        - Configura uma QHBoxLayout para a seleção da família de fontes:
            - Adiciona um QLabel para rotular a seleção de fonte.
            - Cria um QComboBox para listar as fontes suportadas.
            - Limita a visualização para 5 itens no QComboBox para evitar sobrecarga visual.
            - Seleciona a fonte atualmente configurada no QComboBox com base nas preferências salvas.
        - Configura uma QHBoxLayout para a seleção do tamanho da fonte:
            - Adiciona um QLabel para rotular o controle de tamanho.
            - Cria um QDoubleSpinBox para ajustar o tamanho da fonte, com limites e incrementos definidos.
            - Define o valor atual do tamanho da fonte no QDoubleSpinBox.
        - Configura uma QHBoxLayout para a seleção da cor da fonte:
            - Adiciona um QLabel para rotular a seleção de cor.
            - Cria um QPushButton que, quando clicado, abre um seletor de cores.
        - Adiciona um QDialogButtonBox para gerenciar as ações de OK e Cancelar:
            - Configura ações para salvar as alterações ou cancelar e fechar o diálogo.
        - Organiza os botões centralmente utilizando QHBoxLayout com espaçadores à esquerda e à direita.
        - Executa o diálogo para permitir que o usuário interaja com as opções de estilo de texto.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Estilo do Texto")
        layout = QVBoxLayout(dialog)

        # Configura um quadro para conter os elementos da interface
        frame = QFrame(dialog)
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Raised)
        layout.addWidget(frame)

        frame_layout = QVBoxLayout(frame) # Layout vertical para os controles dentro do frame

        # Font family selection
        fontLayout = QHBoxLayout()
        fontLabel = QLabel("Fonte:")
        fontComboBox = QComboBox()  # Usando QComboBox para controlar as entradas
        supported_fonts = ["Arial", "Arial Narrow", "Courier New", "Times New Roman", "Verdana", "Tahoma",
                           "Helvetica", "Calibri", "Garamond", "Lucida Console", "Consolas", "Georgia",
                           "Lucida Sans Unicode", "Palatino Linotype", "Comic Sans MS", "Trebuchet MS", 
                           "Impact", "Century Gothic", "Berlin Sans FB", "Franklin Gothic Medium"]
        fontComboBox.addItems(supported_fonts)
        fontComboBox.setMaxVisibleItems(5)  # Limita a quantidade de itens visíveis na lista dropdown
        fontComboBox.setStyleSheet("""
        QComboBox { combobox-popup: 0; }
        QComboBox QAbstractItemView {
            min-height: 80px; /* Ajuste conforme necessário para mostrar apenas 5 itens */
            max-height: 80px; /* Ajuste conforme necessário para mostrar apenas 5 itens */
        }
        """)
        fontComboBox.setCurrentIndex(supported_fonts.index(self.text_style['font']))  # Define a fonte atual baseada no estilo salvo
        fontLayout.addWidget(fontLabel)
        fontLayout.addWidget(fontComboBox)
        frame_layout.addLayout(fontLayout)
        dialog.fontComboBox = fontComboBox  # Store the fontComboBox in the dialog

        # Configuração da seleção do tamanho da fonte
        sizeLayout = QHBoxLayout()
        sizeLabel = QLabel("Tamanho:")
        sizeSpinBox = QDoubleSpinBox()
        sizeSpinBox.setRange(0.2, 100)
        sizeSpinBox.setSingleStep(0.2)
        sizeSpinBox.setValue(1.0)
        sizeSpinBox.setValue(self.text_style['size'])
        sizeLayout.addWidget(sizeLabel)
        sizeLayout.addWidget(sizeSpinBox)
        frame_layout.addLayout(sizeLayout)
        dialog.sizeSpinBox = sizeSpinBox  # Store the sizeSpinBox in the dialog

        # Configuração da seleção de cor
        colorLayout = QHBoxLayout()
        colorLabel = QLabel("Cor:")
        colorButton = QPushButton("Escolher Cor")
        colorButton.clicked.connect(lambda: self.choose_color(colorButton))
        colorLayout.addWidget(colorLabel)
        colorLayout.addWidget(colorButton)
        frame_layout.addLayout(colorLayout)
        dialog.colorButton = colorButton  # Store the colorButton in the dialog

        # Configuração dos botões de ação
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(lambda: self.update_text_style_and_close(dialog, True))
        buttonBox.rejected.connect(lambda: self.update_text_style_and_close(dialog, False))
        buttonBox.rejected.connect(dialog.reject)
        frame_layout.addWidget(buttonBox)

        # Adiciona espaçadores para centralizar os botões
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()  # Espaçador à esquerda
        buttonLayout.addWidget(buttonBox)
        buttonLayout.addStretch()  # Espaçador à direita

        frame_layout.addLayout(buttonLayout)

        dialog.exec_()

    def update_text_style_and_close(self, dialog, accepted):
        """
        Finaliza a configuração do estilo de texto, atualizando ou rejeitando as mudanças com base na ação do usuário.

        Parâmetros:
        - dialog (QDialog): A caixa de diálogo de onde as configurações são obtidas.
        - accepted (bool): Indica se as alterações foram aceitas ou não.

        Funcionalidades:
        - Verifica se as alterações foram aceitas.
        - Se aceitas, atualiza o dicionário de estilo de texto com os valores selecionados para fonte, tamanho e cor.
        - Atualiza o texto e o estilo do botão de estilo na interface principal para refletir a aceitação das mudanças.
        - Fecha a caixa de diálogo com 'accept', indicando que as mudanças foram confirmadas.
        - Se não aceitas, redefine o texto e estilo do botão de estilo para o estado original.
        - Fecha a caixa de diálogo com 'reject', indicando que as mudanças foram descartadas.
        """
        if accepted:
            # Atualiza o dicionário de estilo de texto com as novas configurações obtidas da caixa de diálogo
            self.text_style['font'] = dialog.fontComboBox.currentText()
            self.text_style['size'] = dialog.sizeSpinBox.value()
            # Atualiza a cor usando a cor atual do botão na paleta de cores
            self.text_style['color'] = dialog.colorButton.palette().color(QPalette.Button)
            # Atualiza o texto do botão de estilo para mostrar que as configurações foram aplicadas
            self.estiloButton.setText("Estilo ✓")
            self.estiloButton.setStyleSheet("QPushButton { color: blue; }")
            dialog.accept()
        else:
            # Redefine o texto do botão de estilo para o estado original
            self.estiloButton.setText("Estilo")
            # Remove qualquer estilo personalizado aplicado anteriormente ao botão
            self.estiloButton.setStyleSheet("")
            dialog.reject()

    def choose_color(self, button):
        """
        Exibe um menu de seleção de cores, permitindo ao usuário escolher uma cor que é aplicada a um botão e armazenada para uso posterior.

        Parâmetros:
        - button (QPushButton): O botão ao qual a cor selecionada será aplicada.

        Funcionalidades:
        - Cria um menu contextual com opções de cores nomeadas.
        - Associa cada opção de cor a um índice ACI específico.
        - Usa ícones coloridos para representar visualmente as cores no menu.
        - Aplica a cor selecionada ao estilo do botão e armazena o índice ACI correspondente.
        """
        # Cria um objeto QMenu para o menu de seleção de cores
        menu = QMenu()
        # Define um dicionário de cores com seus respectivos valores RGB e índice ACI
        colors = {
            'Red': (255, 0, 0, 1),
            'Yellow': (255, 255, 0, 2),
            'Green': (0, 255, 0, 3),
            'Cyan': (0, 255, 255, 4),
            'Blue': (0, 0, 255, 5),
            'Magenta': (255, 0, 255, 6),
            'White': (255, 255, 255, 7)}

        # Itera sobre o dicionário de cores para adicionar cada cor ao menu
        for name, (r, g, b, aci) in colors.items():
            color_action = QAction(name, self) # Cria uma ação com o nome da cor
            color_action.setData(aci) # Armazena o índice ACI como dado associado à ação
            color_action.setIcon(self.create_color_icon(r, g, b)) # Define um ícone colorido para a ação
            menu.addAction(color_action)

        # Exibe o menu na posição atual do cursor e aguarda uma seleção
        action = menu.exec_(QCursor.pos())

        if action: # Verifica se uma ação foi selecionada
            aci_index = action.data() # Obtém o índice ACI da ação selecionada
            color = QColor(*colors[action.text()][:3])
            button.setStyleSheet(f"background-color: {color.name()};")
            # Armazena a cor selecionada no botão para uso futuro
            button.palette().setColor(QPalette.Button, color)
            # Armazena o índice ACI no estilo de texto
            self.text_style['aci_color'] = aci_index

    def create_color_icon(self, r, g, b):
        """
        Cria um ícone colorido que representa uma cor específica usando valores RGB.

        Parâmetros:
        - r (int): Valor do componente vermelho da cor, de 0 a 255.
        - g (int): Valor do componente verde da cor, de 0 a 255.
        - b (int): Valor do componente azul da cor, de 0 a 255.

        Retorna:
        - QIcon: O objeto QIcon criado com a cor especificada.

        Funcionalidades:
        - Cria um QPixmap de tamanho 16x16 pixels.
        - Preenche o QPixmap com a cor especificada pelos valores RGB.
        - Converte o QPixmap em um QIcon para uso em elementos da interface do usuário.
        """
        # Cria um QPixmap de 16x16 pixels para o ícone
        pixmap = QPixmap(16, 16)
        # Preenche o pixmap com a cor especificada
        pixmap.fill(QColor(r, g, b))
        # Cria um QIcon a partir do pixmap
        return QIcon(pixmap)

    def get_Values(self):
        """
        Retorna os valores atuais selecionados em comboboxes e um spinbox da interface gráfica do usuário.

        Retorna:
        - tuple: Uma tupla contendo o texto selecionado no comboBox de campos, no attributeComboBox de atributos,
                 e o valor numérico do linetypeSize (tamanho ou escala de linha).

        Detalhes:
        - self.comboBox.currentText(): Recupera e retorna o texto atualmente selecionado no comboBox.
          Este comboBox pode estar listando opções como nomes de campos, camadas, ou outros parâmetros configuráveis.
        
        - self.attributeComboBox.currentText(): Recupera e retorna o texto atualmente selecionado no attributeComboBox.
          Este comboBox é geralmente usado para selecionar atributos específicos de um objeto ou entidade,
          como características de dados geográficos ou propriedades de elementos em um projeto.

        - self.linetypeSize.value(): Recupera e retorna o valor atual do linetypeSize, que é um QDoubleSpinBox.
          Este controlador ajusta o tamanho ou a escala das linhas, podendo influenciar a visualização ou a impressão
          de desenhos técnicos ou diagramas.

        Utilização:
        Esta função é útil para coletar configurações essenciais de usuário que impactam operações subsequentes,
        como ajustes em visualizações gráficas, configurações de exportação para formatos como DXF, ou ajustes
        de renderização em aplicações de CAD.
        """
        return (
        self.comboBox.currentText(), 
        self.attributeComboBox.currentText(),
        self.linetypeSize.value())

    def get_labeling_options(self):
        """
        Recupera as opções de rotulagem atualmente configuradas no sistema.

        Retorna:
        - tuple: Uma tupla contendo duas entradas:
            1. self.rotulo_modo (str): O modo de rotulagem selecionado, como 'Centralizado', 'Segmentado', ou 'Equidistante'.
            2. self.distancia_intervalo (int): A distância entre rótulos, aplicável no modo 'Equidistante'.

        Funcionalidades:
        - Recupera e retorna as configurações de rotulagem que influenciam como os rótulos são aplicados a entidades ou dados
          em uma visualização ou exportação. Essas configurações podem afetar diretamente a legibilidade e a utilidade
          da informação apresentada, sendo críticas em aplicações de mapeamento, CAD, ou visualização de dados.

        Utilização:
        - Esta função é utilizada para acessar as configurações de rotulagem correntes para serem aplicadas ou ajustadas
          em operações de renderização ou quando se prepara a exportação de dados para formatos que suportam rotulagem,
          como DXF ou outros formatos de arquivo específicos de indústria.
        """
        return self.rotulo_modo, self.distancia_intervalo

    def get_text_style(self):
        """
        Retorna o estilo de texto atual como um dicionário.
        """
        return self.text_style

    def get_selected_linetype(self):
        """
        Obtém o tipo de linha selecionado no QListWidget responsável por listar os tipos de linha disponíveis.

        Retorna:
        - str: O nome do tipo de linha selecionado, ou 'CONTINUOUS' como valor padrão se nenhuma linha estiver selecionada.

        Funcionalidades:
        - Acessa o item atualmente selecionado na lista de tipos de linha.
        - Retorna o texto associado a esse item, que descreve o tipo de linha.
        - Se nenhum item estiver selecionado, retorna 'CONTINUOUS' como um padrão seguro, assumindo que o tipo de linha contínua é o padrão desejado.

        Utilização:
        - Esta função é útil para aplicações que necessitam configurar propriedades gráficas ou de exportação baseadas no tipo de linha selecionado,
          como em sistemas de desenho assistido por computador (CAD) ou outras ferramentas gráficas que lidam com representações visuais detalhadas.
        """
        # Tenta obter o item atualmente selecionado no QListWidget
        current_item = self.linetypeList.currentItem()
        if current_item:
            return current_item.text()
        return 'CONTINUOUS'  # Se nenhum item estiver selecionado, retorna 'CONTINUOUS' como padrão

class CustomDelegate(QStyledItemDelegate):
    """
    CustomDelegate é uma subclasse de QStyledItemDelegate usada para personalizar
    a forma como os itens são desenhados em um QTreeView.

    Esta classe é responsável por desenhar um traço representativo da linha
    para cada camada no QTreeView. A cor e a posição do traço são baseadas nos
    dados do item do modelo.
    """
    def paint(self, painter, option, index):
        """
        Reimplementação do método de pintura para desenhar um traço representativo da linha.

        :param painter: O QPainter usado para desenhar os itens.
        :param option: Fornece as opções de estilo utilizadas para desenhar o item.
        :param index: O QModelIndex do item que está sendo desenhado.
        """
        super().paint(painter, option, index)   # Desenha o item padrão (texto, caixa de seleção, etc.)

        # Obter dados necessários da camada (por exemplo, cor da linha)
        cor_linha = index.data(Qt.UserRole)  # Qt.UserRole pode ser usado para passar dados personalizados
        if not cor_linha:
            cor_linha = QColor(0, 0, 0)  # Cor padrão se não houver cor específica

        # Configurações do traço
        espessura_linha = 7
        comprimento_linha = 10
        espaco_linha = - 13  # Espaço entre o início da célula e o traço

        # Calcular posição do traço
        linha_x = option.rect.x() + espaco_linha
        linha_y = option.rect.y() + (option.rect.height() - espessura_linha) // 2 + 4

        # Desenhar o traço
        painter.setPen(QPen(cor_linha, espessura_linha))
        painter.drawLine(linha_x, linha_y, linha_x + comprimento_linha, linha_y)

class DialogoSalvarFormatos(QDialog):
    """
    DialogoSalvarFormatos cria uma interface de usuário com checkboxes para seleção de formatos de arquivo.
    Ele permite ao usuário escolher um ou mais formatos de arquivo para operações de salvamento.
    """
    def __init__(self, formatos, parent=None):
        """
        Inicializa o diálogo com checkboxes para cada formato disponível e botões OK e Cancelar.
        """
        super(DialogoSalvarFormatos, self).__init__(parent)
        self.setWindowTitle('Escolha o(s) Formato(s)')  # Define o título do diálogo
        self.formatos = formatos  # Dicionário de formatos disponíveis
        self.formatos_selecionados = []  # Lista para armazenar formatos selecionados

        # Layout para caixas de seleção em grade
        grid_layout = QGridLayout(self)  # Cria um layout de grade para o diálogo

        # Caixas de seleção para formatos
        self.caixas_de_selecao = {}  # Dicionário para armazenar as checkboxes
        formatos_keys = list(formatos.keys())  # Lista de chaves de formatos
        for i, formato in enumerate(formatos_keys):
            caixa = QCheckBox(formato, self)  # Cria checkbox para o formato
            grid_layout.addWidget(caixa, i % 4, i // 4)  # Adiciona checkbox à grade
            self.caixas_de_selecao[formato] = caixa  # Armazena checkbox no dicionário
            caixa.stateChanged.connect(self.verificar_selecoes)  # Conecta sinal de alteração

        # Botões OK e Cancelar
        self.botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)  # Cria botões OK e Cancelar
        grid_layout.addWidget(self.botoes, 4, 0, 1, 2)  # Adiciona botões ao layout de grade
        self.botoes.accepted.connect(self.accept)  # Conecta o botão OK a função accept
        self.botoes.rejected.connect(self.reject)  # Conecta o botão Cancelar a função reject

        self.botoes.button(QDialogButtonBox.Ok).setEnabled(False)  # Desativa o botão OK inicialmente

    def verificar_selecoes(self):
        """
        Habilita o botão OK se pelo menos uma caixa de seleção estiver marcada.
        """
        algum_selecionado = any(caixa.isChecked() for caixa in self.caixas_de_selecao.values())  # Verifica se alguma caixa está marcada
        self.botoes.button(QDialogButtonBox.Ok).setEnabled(algum_selecionado)  # Habilita ou desabilita o botão OK

    def accept(self):
        """
        Armazena os formatos selecionados e fecha o diálogo com um estado de "aceito".
        """
        for formato, caixa in self.caixas_de_selecao.items():
            if caixa.isChecked():  # Se a caixa de seleção estiver marcada
                self.formatos_selecionados.append(self.formatos[formato])  # Adiciona o formato à lista de selecionados
        super(DialogoSalvarFormatos, self).accept()  # Chama a implementação padrão para fechar o diálogo

class ExportarKMLDialog(QDialog):
    """
    Diálogo personalizado para configurar a exportação de camadas do QGIS para o formato KML, com opções avançadas incluindo atributos de linha, URLs de imagem, e configurações 3D.

    Atributos de classe:
    - ultimoTextoUrl (str): Armazena o último URL de imagem válido usado para a tabela.
    - ultimoTextoUrl2 (str): Armazena o último URL de imagem válido usado para o ScreenOverlay.

    Métodos:
    - __init__(self, campos): Construtor que inicializa o diálogo com opções configuráveis baseadas nos campos da camada.
    - checkAltitudeValue(self): Verifica o valor da altitude para ativar ou desativar opções dependentes de altura.
    - toggleWidgets(self): Ativa ou desativa widgets com base no estado de uma CheckBox.
    - verificarValidadeURL(self, url): Valida URLs usando uma expressão regular.
    - colarTexto(self): Cola texto do clipboard para o campo URL da imagem da tabela.
    - colarTexto2(self): Cola texto do clipboard para o campo URL do ScreenOverlay.
    - verificarValidadeURLImagem(self, url): Checa se a URL termina com uma extensão de arquivo de imagem válida.
    - verificarTexto(self): Verifica e atualiza o estilo do campo URL da imagem da tabela com base na sua validade.
    - verificarTexto2(self): Verifica e atualiza o estilo do campo URL do ScreenOverlay com base na sua validade.
    - getValues(self): Retorna os valores configurados no diálogo.

    Utilização:
    - Usuários podem abrir este diálogo para configurar detalhadamente como uma camada será exportada para KML, incluindo opções visuais e de dados, facilitando a integração com plataformas como Google Earth.
    """
    # Atributos de classe para armazenar os URLs
    ultimoTextoUrl = ""
    ultimoTextoUrl2 = ""

    def __init__(self, campos):
        super().__init__()

        self.setWindowTitle("Exportar para KML")

        # Criação do layout principal
        mainLayout = QVBoxLayout(self) # Define o título da janela

        # Adiciona um QFrame com estilo Raised ao layout principal
        frame = QFrame() # Cria um frame para conter os widgets
        frame.setFrameShape(QFrame.StyledPanel) # Define o estilo do frame para StyledPanel
        frame.setFrameShadow(QFrame.Raised) # Sombra do frame definida como elevada
        layout = QVBoxLayout(frame)  # Layout para conter todos os outros widgets dentro do frame

        # Adiciona o frame ao layout principal
        mainLayout.addWidget(frame)

        # Layout horizontal para o rótulo, ComboBox, e CheckBox
        rotuloCampoLayout = QHBoxLayout()

        # Label para escolher o campo para o rótulo
        self.labelCampo = QLabel("Campo de Identificação:")
        rotuloCampoLayout.addWidget(self.labelCampo)

        # ComboBox para escolher o campo para o rótulo
        self.comboBoxCampo = QComboBox()
        self.comboBoxCampo.addItems(campos)
        rotuloCampoLayout.addWidget(self.comboBoxCampo)

        # CheckBox para escolher se inclui a tabela de atributos
        self.checkBoxTabela = QCheckBox("Tabela") # Cria CheckBox
        self.checkBoxTabela.setChecked(True) # CheckBox marcada por padrão
        rotuloCampoLayout.addWidget(self.checkBoxTabela)

        # Conecta o sinal stateChanged do checkBox a um método que controla o estado do comboBox, lineEdit, e botão
        self.checkBoxTabela.stateChanged.connect(self.toggleWidgets)

        # Adiciona o layout horizontal do rótulo, ComboBox, e CheckBox ao layout principal
        layout.addLayout(rotuloCampoLayout)

        # Layout horizontal para Espessura da Linha e Altitude
        linhaAltitudeLayout = QHBoxLayout()

        # DoubleSpinBox para a espessura da linha
        self.labelEspessura = QLabel("Espessura:")
        self.doubleSpinBoxEspessura = QDoubleSpinBox()
        self.doubleSpinBoxEspessura.setSingleStep(0.1)
        self.doubleSpinBoxEspessura.setDecimals(1)
        self.doubleSpinBoxEspessura.setValue(1.0)
        linhaAltitudeLayout.addWidget(self.labelEspessura)
        linhaAltitudeLayout.addWidget(self.doubleSpinBoxEspessura)

        # DoubleSpinBox para a altitude
        self.labelAltitude = QLabel("Altura:")
        self.doubleSpinBoxAltitude = QDoubleSpinBox()
        self.doubleSpinBoxAltitude.setSingleStep(0.5)
        self.doubleSpinBoxAltitude.setDecimals(1)
        self.doubleSpinBoxAltitude.setValue(0.0)
        linhaAltitudeLayout.addWidget(self.labelAltitude)
        linhaAltitudeLayout.addWidget(self.doubleSpinBoxAltitude)

        # Layout separado para "3D" e checkBox3D
        linha3DLayout = QHBoxLayout()
        self.checkBox3D = QCheckBox("3D")
        linha3DLayout.addWidget(self.checkBox3D)

        linhaAltitudeLayout.addLayout(linha3DLayout) # Adiciona o layout de 3D ao layout de linha e altitude

        layout.addLayout(linhaAltitudeLayout) # Adiciona o layout horizontal de linha e altitude ao layout principal

        # Layout para "Repetições" e spinBoxRepete
        linhaRepeteLayout = QHBoxLayout()
        linhaRepeteLayout.addStretch(1)  # Empurra tudo para a direita
        labelRepete = QLabel("Repetições:")
        linhaRepeteLayout.addWidget(labelRepete)
        self.spinBoxRepete = QSpinBox()
        self.spinBoxRepete.setMinimum(1)
        self.spinBoxRepete.setMaximum(100)
        linhaRepeteLayout.addWidget(self.spinBoxRepete)

        layout.addLayout(linhaRepeteLayout)

        self.checkAltitudeValue()  # Verifica inicialmente o valor para configurar a atividade do spinBoxRepete
        # Conecta mudança de valor para verificação
        self.doubleSpinBoxAltitude.valueChanged.connect(self.checkAltitudeValue)

        # Primeiro QLineEdit e QPushButton para o URL da imagem
        self.labelImageUrl = QLabel("URL da Imagem para a Tabela:")
        layout.addWidget(self.labelImageUrl)

        urlLayout1 = QHBoxLayout()
        self.lineEditImageUrl = QLineEdit()
        self.lineEditImageUrl.setPlaceholderText("Colar o URL da IMG para a Tabela: Opcional")
        self.lineEditImageUrl.setClearButtonEnabled(True)  # Habilita o botão de limpeza
        self.btnAbrirImagem = QPushButton("Colar")
        self.btnAbrirImagem.setMaximumWidth(40)
        urlLayout1.addWidget(self.lineEditImageUrl)
        urlLayout1.addWidget(self.btnAbrirImagem)

        layout.addLayout(urlLayout1)   # Adiciona layout de URL da imagem ao layout principal

        self.btnAbrirImagem.clicked.connect(self.colarTexto) # Conecta botão para colar texto

        # Segundo QLineEdit e QPushButton para o URL da imagem
        self.labelImageUrl2 = QLabel("URL para ScreenOverlay:")
        layout.addWidget(self.labelImageUrl2)

        urlLayout2 = QHBoxLayout()
        self.lineEditImageUrl2 = QLineEdit()
        self.lineEditImageUrl2.setPlaceholderText("Colar o URL para o ScreenOverlay: Opcional")
        self.lineEditImageUrl2.setClearButtonEnabled(True)  # Habilita o botão de limpeza
        self.btnAbrirImagem2 = QPushButton("Colar")
        self.btnAbrirImagem2.setMaximumWidth(40)
        urlLayout2.addWidget(self.lineEditImageUrl2)
        urlLayout2.addWidget(self.btnAbrirImagem2)
        layout.addLayout(urlLayout2)

        self.btnAbrirImagem2.clicked.connect(self.colarTexto2)

        # Setar o texto dos QLineEdit com os últimos valores usados
        self.lineEditImageUrl.setText(self.ultimoTextoUrl)
        self.lineEditImageUrl2.setText(self.ultimoTextoUrl2)

        # Conecta o sinal textChanged a um novo método para lidar com a atualização do texto
        self.lineEditImageUrl.textChanged.connect(self.verificarTexto)
        self.lineEditImageUrl2.textChanged.connect(self.verificarTexto2)

        # Layout para os botões
        buttonLayout = QHBoxLayout()
        self.btnConfirmar = QPushButton("Confirmar")
        self.btnConfirmar.clicked.connect(self.accept)
        buttonLayout.addWidget(self.btnConfirmar)

        self.btnCancelar = QPushButton("Cancelar")
        self.btnCancelar.clicked.connect(self.reject)
        buttonLayout.addWidget(self.btnCancelar)

        layout.addLayout(buttonLayout)  # Adiciona o layout dos botões ao layout principal do frame

        if not campos:
            self.doubleSpinBoxEspessura.setEnabled(True)  # Habilita SpinBox de espessura se não há campos
            self.doubleSpinBoxAltitude.setEnabled(True)  # Habilita SpinBox de altitude se não há campos
            self.btnConfirmar.setEnabled(False)  # Desabilita botão de confirmar se não há campos

    def checkAltitudeValue(self):
        """
        Verifica o valor atual da altitude para determinar se determinados widgets devem ser habilitados ou desabilitados. 
        Se a altitude for zero, desabilita as opções de repetição e a funcionalidade 3D, que dependem de uma altitude não nula para serem aplicáveis.

        Funcionalidades:
        - Verifica o valor da altitude a partir do widget DoubleSpinBox.
        - Habilita ou desabilita os widgets de número de repetições e a caixa de seleção 3D com base no valor da altitude.
        
        Utilização:
        - Essencial para garantir que as configurações de visualização 3D e repetições sejam aplicáveis apenas quando há uma altitude definida, evitando configurações não suportadas ou sem sentido em altitudes zero.
        """
        # Verifica se o valor da altitude é diferente de zero
        enable = self.doubleSpinBoxAltitude.value() != 0

        # Habilita ou desabilita o spinBox de repetições com base no valor da altitude
        self.spinBoxRepete.setEnabled(enable)

        # Habilita ou desabilita a caixa de seleção 3D com base no valor da altitude
        self.checkBox3D.setEnabled(enable)

    def toggleWidgets(self):
        """
        Alterna a ativação de diversos widgets com base no estado do checkBox para inclusão de tabela de atributos. 
        Quando ativado, permite a seleção do campo de rótulo e o uso de URLs de imagem.

        Funcionalidades:
        - Obtém o estado atual do checkBoxTabela.
        - Habilita ou desabilita o comboBox para escolha do campo de rótulo, o campo de entrada de URL da imagem, e o botão associado à entrada de URL, com base no estado do checkBox.

        Utilização:
        - Essencial para garantir que o usuário só possa selecionar ou inserir informações relevantes para a inclusão da tabela de atributos no KML, mantendo a interface limpa e prevenindo entradas desnecessárias quando a tabela não é desejada.
        """
        # O estado do checkBoxTabela determina a ativação dos outros widgets
        is_checked = self.checkBoxTabela.isChecked()
        
        # Ativar ou desativar widgets com base no estado do checkBox
        self.comboBoxCampo.setEnabled(is_checked)
        self.lineEditImageUrl.setEnabled(is_checked)
        self.btnAbrirImagem.setEnabled(is_checked)

    def verificarValidadeURL(self, url):
        """
        Verifica se a string fornecida é uma URL válida usando uma expressão regular.

        Parâmetros:
        - url (str): A URL a ser validada.

        Funcionalidades:
        - Comprimentoila uma expressão regular que valida URLs de forma abrangente, cobrindo protocolos, domínios, IPs, portas, caminhos, query strings e fragmentos.
        - Verifica se a URL fornecida corresponde à expressão regular.

        Retorno:
        - Retorna True se a URL for válida, False caso contrário.

        Utilização:
        - Utilizada para garantir que as URLs inseridas para imagens ou links em campos de URL sejam válidas antes de serem utilizadas para evitar erros na aplicação ou na visualização do KML.
        """
        # Expressão regular atualizada para validar URLs de forma mais abrangente.
        padrao_url = re.compile(
            r'^(https?:\/\/)?'  # http:// ou https://
            r'((([a-z\d]([a-z\d-]*[a-z\d])*)\.)+[a-z]{2,}|'  # domínio
            r'((\d{1,3}\.){3}\d{1,3}))'  # ou ip
            r'(\:\d+)?(\/[-a-z\d%_.~+]*)*'  # porta e caminho
            r'(\?[;&a-z\d%_.~+=-]*)?'  # query string
            r'(\#[-a-z\d_]*)?$', re.IGNORECASE)  # fragmento
        return re.match(padrao_url, url) is not None

    def colarTexto(self):
        """
        Obtém o texto do clipboard e insere no campo QLineEdit destinado ao URL da imagem, 
        se o texto for uma URL válida.

        Funcionalidades:
        - Acessa o conteúdo do clipboard do sistema.
        - Verifica se o texto é uma URL válida.
        - Insere a URL válida no campo de texto se for válida.

        Utilização:
        - Usado para facilitar a inserção de URLs por meio do uso de clipboard, evitando a necessidade de digitação manual, 
          aumentando a eficiência do usuário e reduzindo a chance de erro de entrada.
        """
        # Acessa o clipboard do sistema
        clipboard = QGuiApplication.clipboard() # Obtém o objeto clipboard do sistema
        texto = clipboard.text() # Lê o texto atualmente armazenado no clipboard
        
        # Verifica se o texto copiado é uma URL válida
        if self.verificarValidadeURL(texto): # Chama o método para verificar a validade da URL
            self.lineEditImageUrl.setText(texto) # Insere o texto no QLineEdit se for uma URL válida

    def colarTexto2(self):
        """
        Obtém o texto do clipboard e insere no campo QLineEdit destinado ao URL para ScreenOverlay,
        se o texto for uma URL válida.

        Funcionalidades:
        - Acessa o conteúdo do clipboard do sistema.
        - Verifica se o texto é uma URL válida.
        - Insere a URL válida no campo de texto destinado ao ScreenOverlay se for válida.

        Utilização:
        - Usado para facilitar a inserção de URLs de ScreenOverlay por meio do uso de clipboard, 
          evitando a necessidade de digitação manual e melhorando a eficiência do usuário.
        """
        # Acessa o clipboard do sistema
        clipboard = QGuiApplication.clipboard() # Obtém o objeto clipboard do sistema
        texto = clipboard.text() # Lê o texto atualmente armazenado no clipboard

        # Verifica se o texto copiado é uma URL válida
        if self.verificarValidadeURL(texto): # Chama o método para verificar a validade da URL
            self.lineEditImageUrl2.setText(texto) # Insere o texto no QLineEdit destinado ao ScreenOverlay se for uma URL válida

    def verificarValidadeURLImagem(self, url):
        """
        Verifica se a URL fornecida termina com uma extensão de arquivo de imagem aceitável. 
        Este método é usado para garantir que URLs inseridas para imagens sejam de formatos compatíveis para visualização.

        Parâmetros:
        - url (str): A URL da imagem a ser validada.

        Funcionalidades:
        - Define uma lista de extensões de arquivo de imagem que são aceitáveis.
        - Verifica se a URL fornecida termina com uma dessas extensões.

        Retorno:
        - Retorna True se a URL terminar com uma extensão de arquivo de imagem válida, False caso contrário.

        Utilização:
        - Utilizada para validar URLs de imagens, assegurando que os links fornecidos apontem para arquivos de imagem reais que podem ser carregados e exibidos corretamente no KML.
        """
        # Define as extensões de arquivo de imagem que são aceitáveis
        extensoes_validas = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.webp']
        # Verifica se a URL termina com alguma das extensões válidas
        return any(url.lower().endswith(ext) for ext in extensoes_validas) # Verifica se a URL corresponde a uma extensão válida

    def verificarTexto(self):
        """
        Verifica o conteúdo do campo de entrada para URL da imagem, ajusta a cor do texto baseada na validade da URL
        e atualiza o último texto de URL válido armazenado. Este método é usado para fornecer feedback visual imediato 
        sobre a validade da URL inserida.

        Funcionalidades:
        - Obtém o texto atual do campo QLineEdit destinado à URL da imagem.
        - Verifica se o texto é uma URL válida e se corresponde a uma extensão de arquivo de imagem aceitável.
        - Atualiza o armazenamento do último texto válido ou o limpa se o texto atual não for válido.
        - Altera a cor do texto do QLineEdit para azul se a URL for válida, para vermelho se for inválida, e retorna para a cor padrão se o campo estiver vazio.

        Utilização:
        - Essencial para fornecer uma resposta visual instantânea ao usuário sobre a validade da URL inserida, 
          facilitando a correção de erros e garantindo que apenas URLs válidas sejam utilizadas.
        """
        # Obtém o texto atual do QLineEdit
        texto = self.lineEditImageUrl.text() # Lê o texto da caixa de entrada de URL da imagem
        
        # Verifica a validade da URL e se a URL é uma imagem
        if self.verificarValidadeURL(texto) and self.verificarValidadeURLImagem(texto):
            ExportarKMLDialog.ultimoTextoUrl = texto # Atualiza o último texto válido se a URL for válida
            self.lineEditImageUrl.setStyleSheet("QLineEdit { color: blue; }") # Muda a cor do texto para azul
        else:
            ExportarKMLDialog.ultimoTextoUrl = "" # Limpa o último texto válido se a URL for inválida
            if texto.strip() != "": # Verifica se o campo não está vazio
                self.lineEditImageUrl.setStyleSheet("QLineEdit { color: red; }") # Muda a cor do texto para vermelho se houver texto inválido
            else:
                self.lineEditImageUrl.setStyleSheet("") # Retorna a cor do texto para o padrão se o campo estiver vazio

    def verificarTexto2(self):
        """
        Verifica o conteúdo do campo de entrada para o URL do ScreenOverlay, ajusta a cor do texto baseada na validade da URL,
        e atualiza o último texto de URL válido armazenado. Este método é usado para fornecer feedback visual imediato 
        sobre a validade da URL inserida.

        Funcionalidades:
        - Obtém o texto atual do campo QLineEdit destinado ao URL do ScreenOverlay.
        - Verifica se o texto é uma URL válida e se corresponde a uma extensão de arquivo de imagem aceitável.
        - Atualiza o armazenamento do último texto válido ou o limpa se o texto atual não for válido.
        - Altera a cor do texto do QLineEdit para azul se a URL for válida, para vermelho se for inválida, e retorna para a cor padrão se o campo estiver vazio.

        Utilização:
        - Essencial para fornecer uma resposta visual instantânea ao usuário sobre a validade da URL inserida para o ScreenOverlay,
          facilitando a correção de erros e garantindo que apenas URLs válidas sejam utilizadas para o ScreenOverlay.
        """
        # Obtém o texto atual do QLineEdit destinado ao URL do ScreenOverlay
        texto = self.lineEditImageUrl2.text()  # Lê o texto da caixa de entrada de URL para o ScreenOverlay

        # Verifica a validade da URL e se a URL é uma imagem
        if self.verificarValidadeURL(texto) and self.verificarValidadeURLImagem(texto):
            ExportarKMLDialog.ultimoTextoUrl2 = texto # Atualiza o último texto válido se a URL for válida
            self.lineEditImageUrl2.setStyleSheet("QLineEdit { color: blue; }") # Muda a cor do texto para azul
        else:
            ExportarKMLDialog.ultimoTextoUrl2 = "" # Limpa o último texto válido se a URL for inválida
            if texto.strip() != "": # Verifica se o campo não está vazio
                self.lineEditImageUrl2.setStyleSheet("QLineEdit { color: red; }") # Muda a cor do texto para vermelho se houver texto inválido
            else:
                self.lineEditImageUrl2.setStyleSheet("") # Retorna a cor do texto para o padrão se o campo estiver vazio

    def getValues(self):
        """
        Coleta e retorna todos os valores dos controles de entrada definidos no diálogo. 
        Isso inclui informações sobre o campo de rótulo, espessura da linha, altitude, URLs de imagem,
        e opções como tabela de atributos, visualização em 3D e número de repetições.

        Retorno:
        - Retorna uma tupla contendo:
          - O texto atual do comboBox para seleção do campo de rótulo.
          - O valor atual da espessura da linha.
          - O valor atual da altitude.
          - O texto do campo de entrada para a URL da imagem da tabela.
          - O texto do campo de entrada para a URL do ScreenOverlay.
          - O estado atual da caixa de seleção para incluir tabela de atributos.
          - O estado atual da caixa de seleção para visualização em 3D.
          - O valor atual do número de repetições.

        Utilização:
        - Usado para capturar todas as configurações do usuário em um único ponto, facilitando a passagem dessas informações 
          para outras partes do sistema que processam a exportação para KML.
        """
        # Retorna todos os valores relevantes como uma tupla
        return (
            self.comboBoxCampo.currentText(),  # Texto atual do comboBox para o campo de rótulo
            self.doubleSpinBoxEspessura.value(),  # Valor atual da espessura da linha
            self.doubleSpinBoxAltitude.value(),  # Valor atual da altitude
            self.lineEditImageUrl.text(),  # Texto atual do campo de entrada para a URL da imagem
            self.lineEditImageUrl2.text(),  # Texto atual do campo de entrada para a URL do ScreenOverlay
            self.checkBoxTabela.isChecked(),  # Estado atual da caixa de seleção para incluir tabela de atributos
            self.checkBox3D.isChecked(),  # Estado atual da caixa de seleção para visualização em 3D
            self.spinBoxRepete.value()  # Número de repetições definido pelo usuário
        )

class GerenciarEtiquetasDialog(QDialog):
    """
    Esta classe cria um diálogo para gerenciar as etiquetas de uma camada no QGIS, oferecendo funcionalidades para selecionar campos, ajustar suas cores e definir a visibilidade das etiquetas.

    Atributos:
    - layer: Referência à camada do QGIS para a qual as configurações de etiquetas serão aplicadas.
    - fieldColors: Um dicionário que mapeia os nomes dos campos às suas cores selecionadas para a etiqueta.
    - fieldVisibility: Um dicionário que mapeia os nomes dos campos à sua visibilidade (True para visível, False para oculto).
    - iface: Uma referência à interface do QGIS, permitindo interações com o ambiente do QGIS.

    Processo:
    1. Inicializa o diálogo com os valores padrão e configurações recebidas.
    2. Configura a interface do usuário chamando `setupUi`, que constrói todos os elementos gráficos necessários.
    3. Define os tamanhos mínimo e máximo do diálogo para garantir uma apresentação adequada dos elementos da interface.
    
    Detalhes:
    - A janela do diálogo é intitulada "Selecionar Campos para Etiquetas", refletindo seu propósito de permitir a seleção e personalização das etiquetas da camada.
    - A interface do diálogo é construída para ser intuitiva, com checkboxes para a seleção de campos e botões para a escolha de cores, facilitando a personalização das etiquetas pelo usuário.
    """
    def __init__(self, layer, fieldColors, fieldVisibility, iface, parent=None):
        super().__init__(parent)
        self.layer = layer  # A camada do QGIS que será manipulada
        self.fieldColors = fieldColors # Mapeamento dos campos para suas cores de etiqueta
        self.fieldVisibility = fieldVisibility # Mapeamento dos campos para a visibilidade da etiqueta
        self.iface = iface # Interface do QGIS para interações com o ambiente
        self.setWindowTitle("Selecionar Campos para Etiquetas")
        self.setupUi() # Chama a função para configurar a interface do usuário
        self.setMinimumSize(225, 150)  # Define o tamanho mínimo do diálogo para 600x400
        self.setMaximumSize(400, 300)  # Define o tamanho máximo do diálogo
        self.update_buttons_state()

    def setupUi(self):
        """
        Esta função configura a interface do usuário para um diálogo personalizado de configuração de etiquetas em camadas GIS.
        Ela faz o seguinte:
        1. Cria um layout vertical principal para organizar os widgets.
        2. Adiciona uma área de rolagem (QScrollArea) ao layout para acomodar muitos campos.
        3. Configura um container dentro da área de rolagem para conter todos os widgets de configuração de campo.
        4. Itera sobre todos os campos da camada, criando um layout horizontal para cada campo com um checkbox e um botão de seleção de cor.
        5. Mapeia o estado do checkbox ao botão de seleção de cor, habilitando-o somente se o checkbox estiver marcado.
        6. Adiciona botões para aplicar configurações de etiqueta HTML ou Simples.
        """
        layout = QVBoxLayout(self) # Cria um layout vertical para organizar os elementos da UI

        # Cria uma QScrollArea
        scrollArea = QScrollArea(self)
        scrollArea.setWidgetResizable(True)

        # Pode ajustar o tamanho da QScrollArea conforme necessário, ou deixá-la expansível
        scrollArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        container = QWidget() # Widget que conterá todos os campos e botões
        containerLayout = QVBoxLayout(container) # Define o layout do contêiner como vertical.

        self.fieldColorMapping = {} # Dicionário para mapear os campos aos seus respectivos widgets de UI
        
        # Itera sobre os campos da camada, criando widgets para cada um
        for field in self.layer.fields():
            fieldLayout = QHBoxLayout()  # Cria um layout horizontal para cada campo
            checkBox = QCheckBox(field.name()) # Checkbox para ativar/desativar o campo
            checkBox.setChecked(self.fieldVisibility.get(field.name(), False)) # Define o estado inicial baseado em configurações prévias
            checkBox.stateChanged.connect(self.update_buttons_state)  # Conecta para verificar se os botões devem ser ativados/desativados
            fieldLayout.addWidget(checkBox) # Adiciona o checkbox ao layout do campo.

            colorButton = QPushButton("Cor") # Cria o botão para seleção de cor
            colorButton.setEnabled(checkBox.isChecked()) # Habilita baseado no estado do checkbox
            # Conecta o botão a uma função para abrir o seletor de cor
            colorButton.clicked.connect(functools.partial(self.abrir_seletor_de_cor, fieldName=field.name(), colorButton=colorButton))
            # Conecta a mudança de estado do checkbox para habilitar/desabilitar o botão de cor
            checkBox.stateChanged.connect(functools.partial(self.toggle_color_button, checkBox=checkBox, colorButton=colorButton))
            
            # Configura a cor inicial se já estiver definida
            if field.name() in self.fieldColors:
                colorName = self.fieldColors[field.name()]
                colorButton.setStyleSheet(f"background-color: {colorName}")
                colorButton.color = QColor(colorName)
            fieldLayout.addWidget(colorButton)

            # Adiciona o mapeamento do campo ao dicionário
            self.fieldColorMapping[field.name()] = (checkBox, colorButton)
            containerLayout.addLayout(fieldLayout)

        scrollArea.setWidget(container) # Define o container como o widget da QScrollArea
        layout.addWidget(scrollArea) # Adiciona a QScrollArea ao layout principal

        # Cria e configura botões para aplicação de etiquetas HTML ou Simples
        buttonsLayout = QHBoxLayout()
        self.btnHtml = QPushButton("HTML")
        self.btnSimples = QPushButton("Simples")
        self.btnSimples.clicked.connect(self.on_btn_simples_clicked) # Conecta ao slot para config simples
        self.btnHtml.clicked.connect(self.on_btn_html_clicked) # Conecta ao slot para configuração HTML
        buttonsLayout.addWidget(self.btnHtml)
        buttonsLayout.addWidget(self.btnSimples)
        layout.addLayout(buttonsLayout)

        # Botão "Cancelar" abaixo dos outros
        btnCancelar = QPushButton("Cancelar")
        btnCancelar.clicked.connect(self.reject)
        layout.addWidget(btnCancelar)
        
        self.setLayout(layout)
        self.update_buttons_state()  # Atualiza o estado dos botões ao iniciar

    def update_buttons_state(self):
        """
        Atualiza o estado dos botões "HTML" e "Simples" com base na seleção dos checkboxes.
        
        Processo:
        - Verifica se algum checkbox está selecionado.
        - Habilita ou desabilita os botões "HTML" e "Simples" dependendo da seleção.
        """

        # Verifica se há algum checkbox selecionado para habilitar ou desabilitar os botões.
        any_checked = any(checkBox.isChecked() for checkBox, _ in self.fieldColorMapping.values())
        
        # Habilita ou desabilita o botão "HTML" com base na variável 'any_checked'.
        self.btnHtml.setEnabled(any_checked)
        
        # Habilita ou desabilita o botão "Simples" com base na variável 'any_checked'.
        self.btnSimples.setEnabled(any_checked)

    def abrir_seletor_de_cor(self, fieldName, colorButton):
        """
        Abre um diálogo de seleção de cor para o usuário escolher uma cor, e aplica essa cor ao botão de cor correspondente a um campo da camada.
        
        Processo:
        1. Abre o diálogo de seleção de cor e aguarda o usuário escolher uma cor.
        2. Verifica se a cor selecionada é válida (o usuário não cancelou o diálogo).
        3. Aplica a cor selecionada ao botão, mudando seu estilo para refletir a nova cor.
        4. Armazena a cor selecionada no dicionário `fieldColors`, associando-a ao nome do campo especificado.
        
        Parâmetros:
        - fieldName: Nome do campo ao qual o botão de seleção de cor está associado.
        - colorButton: O botão de seleção de cor que terá sua cor atualizada.
        """
        
        # 1. Abre o diálogo de seleção de cor. O QColorDialog.getColor retorna uma instância QColor.
        color = QColorDialog.getColor()

        # 2. Verifica se a cor selecionada pelo usuário é válida (i.e., o usuário não pressionou "Cancelar").
        if color.isValid():
            colorName = color.name(QColor.HexArgb)
            # 3. Aplica a cor selecionada ao botão, alterando o estilo (cor de fundo) do botão.
            colorButton.setStyleSheet(f"""
                background-color: {colorName};
                border: 1px solid {colorName};
                border-radius: 5px;
                width: 50px;
                height: 20px;
                text-align: center;
            """)
            colorButton.color = color  # Salva a instância QColor no botão para uso posterior.
            # 4. Atualiza o dicionário `fieldColors`, associando o nome do campo à cor selecionada (como uma string hexadecimal).
            self.fieldColors[fieldName] = color.name()

    def toggle_color_button(self, state, checkBox, colorButton):
        """
        Alterna a habilitação do botão de seleção de cor com base no estado de uma caixa de seleção associada e atualiza o dicionário de visibilidade de campos.

        Processo:
        1. Habilita ou desabilita o botão de seleção de cor com base no estado da caixa de seleção (marcada ou não).
        2. Obtém o nome do campo a partir do texto da caixa de seleção.
        3. Atualiza o dicionário `fieldVisibility`, registrando o estado atual (marcado ou não) da caixa de seleção para o campo correspondente.

        Parâmetros:
        - state: O estado atual da caixa de seleção (Qt.Checked se estiver marcada).
        - checkBox: A caixa de seleção que determina a habilitação do botão de cor.
        - colorButton: O botão de seleção de cor cuja habilitação é controlada pela caixa de seleção.
        """

        # 1. Habilita o botão de seleção de cor se a caixa de seleção estiver marcada, caso contrário, desabilita.
        colorButton.setEnabled(state == Qt.Checked)
        fieldName = checkBox.text() # 2. Obtém o nome do campo a partir do texto da caixa de seleção.
        # 3. Atualiza o dicionário `fieldVisibility`, definindo o estado de visibilidade do campo com base no estado da caixa de seleção.
        self.fieldVisibility[fieldName] = checkBox.isChecked()
        self.update_checkboxes()  # Atualiza a habilitação dos checkboxes cada vez que um é marcado ou desmarcado.

    def update_checkboxes(self):
        """
        Atualiza a habilitação das caixas de seleção com base no número total de caixas marcadas, limitando o número máximo de caixas que podem ser marcadas simultaneamente.

        Processo:
        - Calcula o número total de caixas de seleção marcadas.
        - Percorre todas as caixas de seleção.
        - Desabilita caixas de seleção não marcadas se o limite de caixas marcadas for atingido; caso contrário, todas as caixas de seleção permanecem habilitadas.

        Detalhes:
        - O limite máximo de caixas de seleção que podem ser marcadas simultaneamente é definido como 5.
        - As caixas de seleção marcadas permanecem sempre habilitadas, garantindo que o usuário possa desmarcar uma opção caso deseje selecionar outra.
        """

        # Conta o número total de caixas de seleção que estão atualmente marcadas.
        selected_count = sum(1 for checkBox, _ in self.fieldColorMapping.values() if checkBox.isChecked())

        # Itera sobre cada caixa de seleção e seu respectivo botão de cor no mapeamento.
        for fieldName, (checkBox, colorButton) in self.fieldColorMapping.items():
            # Habilita a caixa de seleção se menos de 5 estiverem marcadas ou se a própria caixa já estiver marcada; 
            checkBox.setEnabled(selected_count < 5 or checkBox.isChecked())

            # Isso garante que o botão de cor só possa ser interagido quando o checkbox está marcado.
            colorButton.setEnabled(checkBox.isChecked())

    def on_btn_simples_clicked(self):
        """
        Manipula o evento de clique no botão "Simples", iniciando o processo de reconfiguração das etiquetas da camada para um formato de exibição simples.

        Processo:
        1. Chama a função `reconfigurar_etiquetas_simples` para ajustar a configuração das etiquetas da camada selecionada.

        Detalhes:
        - Este manipulador de eventos é vinculado ao botão "Simples" na interface do usuário.
        - Ao ser acionado, inicia o processo de ajuste das etiquetas de acordo com os campos selecionados e as preferências de cores definidas pelo usuário, se aplicável.
        - O ajuste é feito para simplificar a visualização das etiquetas, focando na exibição dos valores dos campos sem formatação HTML avançada.
        """

        # Chama a função que reconfigura as etiquetas para o modo simples.
        self.reconfigurar_etiquetas_simples()

    def on_btn_html_clicked(self):
        """
        Este método é chamado quando o usuário clica no botão "HTML". Ele inicia o processo de reconfiguração das etiquetas da camada para usar formatação HTML, permitindo um estilo mais complexo e visualmente atraente nas etiquetas.

        Processo:
        1. Invoca a função `reconfigurar_etiquetas_HTML` que ajusta as configurações de etiquetas da camada selecionada para utilizar expressões HTML.
        
        Detalhes:
        - Este método é conectado ao evento de clique no botão "HTML" na interface gráfica do usuário.
        - A função `reconfigurar_etiquetas_HTML` é projetada para permitir que informações adicionais e estilos personalizados sejam aplicados às etiquetas, usando a linguagem de marcação HTML.
        - Isso possibilita a inclusão de cores, tamanhos de fonte variados, e outras customizações visuais que melhoram a apresentação dos dados na camada.
        """

        # Chama a função que configura as etiquetas da camada para usar expressões HTML,
        # permitindo a personalização avançada das etiquetas exibidas no mapa.
        self.reconfigurar_etiquetas_HTML()

    def reconfigurar_etiquetas_HTML(self):
        """
        Configura as etiquetas da camada com base nas seleções de campo e cores definidas pelo usuário.
        
        A função percorre o mapeamento de campos para os widgets de seleção e cor, construindo uma expressão de etiqueta
        que incorpora o nome do campo e a cor selecionada para cada campo ativo. As etiquetas são formatadas em HTML para
        permitir a estilização com cores. A função também habilita as etiquetas na camada e aplica as configurações de etiqueta,
        ativando o repintura da camada para refletir as mudanças imediatamente. Ao final, o diálogo é fechado, e a janela de
        propriedades da camada é aberta para mostrar as atualizações.

        Funcionalidades:
        - Cria expressões de etiqueta combinando campos selecionados com suas cores definidas.
        - Aplica formatação HTML para estilizar as etiquetas com as cores escolhidas.
        - Habilita a visualização de etiquetas na camada com as configurações definidas.
        - Fecha o diálogo de configuração de etiquetas após aplicar as mudanças.
        - Abre a janela de propriedades da camada no QGIS para visualização das configurações aplicadas.
        """

        # Inicializa uma lista para armazenar as expressões de etiqueta com base nos campos selecionados e suas cores
        label_expressions = []
        # Itera sobre o mapeamento de campos para coletar os campos selecionados e suas cores definidas
        for fieldName, (checkBox, colorButton) in self.fieldColorMapping.items():
            if checkBox.isChecked():  # Verifica se o campo está selecionado para etiquetagem
                # Obtém a cor do botão de cor, padrão preto se não houver atributo de cor
                color = colorButton.color.name() if hasattr(colorButton, 'color') else '#000000'
                # Constrói a expressão de etiqueta com formatação HTML para o campo e cor
                label_expressions.append(f'concat(\'<span style="color: {color};">[\', \"{fieldName}\", \']</span>\' )')
        # Combina as expressões de etiqueta com quebras de linha em HTML para etiquetas multilinha, se houver mais de uma
        label_expression = ' || \'<br>\' || '.join(label_expressions) if label_expressions else "''"
        
        label_settings = QgsPalLayerSettings() # Configura as definições de etiqueta para a camada
        label_settings.drawBackground = True # Habilita o fundo das etiquetas
        label_settings.fieldName = label_expression # Define a expressão de etiqueta
        label_settings.isExpression = True # Indica que a fieldName é uma expressão
        
        # Aplica as configurações de etiqueta à camada
        self.layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        self.layer.setLabelsEnabled(True) # Habilita as etiquetas na camada
        self.layer.triggerRepaint() # Solicita a repintura da camada para aplicar as mudanças
        
        self.accept()  # Fecha o diálogo de configuração de etiquetas
        self.iface.showLayerProperties(self.layer)  # Abre a janela de propriedades da camada para mostrar as configurações

    def reconfigurar_etiquetas_simples(self):
        """
        Reconfigura as etiquetas para exibir campos selecionados de forma simples, concatenando os valores dos campos selecionados em uma única linha por registro.

        Processo:
        - Coleta os campos que foram selecionados pelos checkboxes.
        - Cria uma expressão concatenada para exibir os valores dos campos selecionados.
        - Configura as propriedades de etiquetagem da camada, levando em consideração a versão do QGIS para garantir compatibilidade.

        Detalhes:
        - A expressão gerada usa a função '||' para concatenar os valores dos campos selecionados com uma quebra de linha entre eles.
        - A configuração de posicionamento das etiquetas (placement) é ajustada dependendo da versão do QGIS:
            * Para QGIS 3.38 ou superior, usa-se `QgsPalLayerSettings.Placement.OverPoint`.
            * Para versões anteriores, usa-se `QgsPalLayerSettings.OverPoint`.
        - As etiquetas são ativadas e a camada é repintada para refletir as novas configurações.
        """

        # Filtra os campos que estão marcados nos checkboxes.
        selected_fields = [field for field, (checkBox, _) in self.fieldColorMapping.items() if checkBox.isChecked()]

        # Se nenhum campo foi selecionado, a função retorna sem fazer alterações.
        if not selected_fields:
            return

        # Cria uma expressão concatenada com os nomes dos campos selecionados, separados por quebras de linha.
        expression = ' || \'\\n\' || '.join([f'\"{field}\"' for field in selected_fields])

        # Instancia um objeto QgsPalLayerSettings para configurar as propriedades de etiquetagem.
        settings = QgsPalLayerSettings()
        
        # Verifica a versão do QGIS para ajustar o modo de definir o posicionamento das etiquetas.
        version = Qgis.QGIS_VERSION_INT
        if version >= 33800:
            # Para versões 3.38 ou superiores, utiliza a enumeração Placement.OverPoint.
            settings.placement = QgsPalLayerSettings.Placement.OverPoint
        else:
            # Para versões anteriores, utiliza OverPoint diretamente.
            settings.placement = QgsPalLayerSettings.OverPoint
        
        # Ativa as etiquetas na camada.
        settings.enabled = True

        # Define que o campo das etiquetas é uma expressão em vez de um campo simples.
        settings.isExpression = True

        # Atribui a expressão criada anteriormente ao campo de nome das etiquetas.
        settings.fieldName = expression

        # Aplica a configuração de etiquetagem à camada.
        self.layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))

        # Ativa a exibição das etiquetas e repinta a camada para atualizar a visualização.
        self.layer.setLabelsEnabled(True)
        self.layer.triggerRepaint()

        # Aceita o diálogo, confirmando as mudanças feitas.
        self.accept()

        # Atualiza a interface do usuário para refletir as novas configurações de etiquetagem.
        self.iface.mapCanvas().refreshAllLayers()
        self.iface.showLayerProperties(self.layer)

class CloneManager:
    def __init__(self, ui_manager, layer_to_clone):
        """
        Inicializa a classe CloneManager, que gerencia as operações de clonagem de camadas dentro de um aplicativo GIS.
        
        :param ui_manager: Uma referência ao gerenciador de interface do usuário, responsável por interações e atualizações da UI.
        :param layer_to_clone: A camada que será clonada. Esta camada pode ser qualquer tipo de camada suportada pelo GIS, como camadas vetoriais.
        """
        self.ui_manager = ui_manager  # Armazena a referência ao gerenciador de interface do usuário para operações relacionadas à UI.
        self.layer_to_clone = layer_to_clone  # Armazena a camada que será clonada, usada nas diversas operações de clonagem.
    
    def show_clone_options(self):
        """
        Exibe uma janela de diálogo com opções para o usuário selecionar o tipo de clonagem desejado.
        
        A função cria um diálogo modal que permite ao usuário escolher entre diferentes tipos de clonagem:
        1. Clonar apenas a geometria das feições, sem copiar a tabela de atributos.
        2. Copiar apenas a tabela de atributos, sem as feições.
        3. Combinar ambos, copiando as feições e a tabela de atributos, e tratar linhas específicas.
        4. Excluir a tabela de atributos da clonagem, mantendo apenas as feições e tratando linhas específicas.
        
        A escolha é feita por meio de botões de rádio, e a opção selecionada é passada para a função de clonagem correspondente.
        """
        # Criação de um diálogo como um subdiálogo do diálogo principal
        dialog = QDialog(self.ui_manager.dlg)  # Acesso ao dlg através de ui_manager
        dialog.setWindowTitle("Escolher Tipo de Clonagem") # Define o título do diálogo
        layout = QVBoxLayout(dialog) # Layout vertical para organizar os elementos internos

        # Criação de um grupo de botões para gerenciar as opções de clonagem
        button_group = QButtonGroup(dialog)  # Deve ser criado antes de ser usado

        # Definição dos botões de rádio para cada opção de clonagem
        self.radio_buttons = {
            1: QRadioButton("Clonar Feição, sem a Tabela"),
            2: QRadioButton("Copiar Tabela de Atributos"),
            3: QRadioButton("Combinar Tabela e Tratar Linhas"),
            4: QRadioButton("Excluir Tabela e Tratar Linhas")}

        for id, radio in self.radio_buttons.items():
            # Cria um QFrame como contêiner para cada QRadioButton
            frame = QFrame(dialog)
            frame_layout = QVBoxLayout(frame)
            frame.setFrameShape(QFrame.StyledPanel) # Estilo do contêiner
            frame.setFrameShadow(QFrame.Raised)
            frame.setFixedSize(200, 30)  # Define a largura e altura do QFrame

            # Adição do botão de rádio ao layout do contêiner
            frame_layout.addWidget(radio)
            layout.addWidget(frame)
            
            # Adiciona o QRadioButton ao QButtonGroup para garantir a seleção exclusiva
            button_group.addButton(radio, id)

            # Seleciona por padrão a primeira opção de clonagem
            if id == 1:
                radio.setChecked(True)

        # Criação e configuração de botões de ação para confirmar ou cancelar
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(dialog.accept) # Conecta o botão OK à aceitação do diálogo
        buttonBox.rejected.connect(dialog.reject)   # Conecta o botão Cancelar à rejeição do diálogo
        layout.addWidget(buttonBox)

        # Criação de um layout horizontal para centralizar os botões
        hLayout = QHBoxLayout()
        hLayout.addStretch()  # Adiciona um espaço flexível antes dos botões
        hLayout.addWidget(buttonBox)  # Adiciona o QDialogButtonBox ao layout horizontal
        hLayout.addStretch()  # Adiciona um espaço flexível após os botões

        # Adiciona o layout horizontal ao layout principal do diálogo
        layout.addLayout(hLayout)

        result = dialog.exec_() # Executa o diálogo e verifica o resultado após o fechamento
        if result == QDialog.Accepted:
            # Identifica o botão de rádio selecionado e realiza a clonagem correspondente
            for id, radio in self.radio_buttons.items():
                if radio.isChecked():
                    self.realizar_clonagem(id) # Chama a função de clonagem com o tipo selecionado
                    break

    def realizar_clonagem(self, tipo_clonagem):
        """
        Determina o tipo de clonagem a ser realizado na camada e chama a função correspondente.
        
        Esta função serve como um controlador que, com base no tipo de clonagem fornecido como argumento,
        direciona para a função específica de clonagem. As opções de clonagem incluem:
        1. Clonar apenas as feições sem os atributos.
        2. Clonar apenas os atributos sem as feições.
        3. Combinar os atributos e feições em uma clonagem completa.
        4. Clonar a camada excluindo certos atributos.
        
        Parâmetros:
        - tipo_clonagem: Inteiro que indica o tipo de clonagem desejada.
        """
        # Verificação do tipo de clonagem e chamada da função correspondente
        if tipo_clonagem == 1:
            self.clone_feicao()  # Chama a função para clonar apenas as feições
        elif tipo_clonagem == 2:
            self.clone_atributos()  # Chama a função para clonar apenas os atributos
        elif tipo_clonagem == 3:
            self.clone_combinar()  # Chama a função para combinar clonagem de atributos e feições
        elif tipo_clonagem == 4:
            self.clone_excluir()  # Chama a função para clonar a camada excluindo certos atributos

    def criar_camada_clonada(self, name_suffix, fields=None, features_to_add=None, set_renderer=True, only_id_comp=False):
        """
        Cria uma camada clonada baseada na camada original, com opções para customizar os campos,
        as feições a serem adicionadas, e se o renderizador da camada original deve ser copiado.
        A camada clonada é adicionada a um grupo específico no projeto chamado "Camadas Clonadas".

        Processo:
        1. Prepara o nome e verifica se a camada original é temporária.
        2. Define o tipo de geometria e o sistema de referência de coordenadas (CRS) baseando-se na camada original.
        3. Cria a camada clonada como uma camada de memória.
        4. Verifica se a camada clonada foi criada corretamente.
        5. Adiciona os campos especificados à camada clonada.
        6. Adiciona as feições especificadas à camada clonada.
        7. Copia o renderizador da camada original, se solicitado.
        8. Adiciona a camada clonada ao grupo "Camadas Clonadas" no projeto.

        Parâmetros:
        - name_suffix: Sufixo para o nome da camada clonada.
        - fields: Campos a serem adicionados à camada clonada. Se None, copia todos os campos da original.
        - features_to_add: Feições a serem adicionadas à camada clonada. Se None, copia todas as feições da original.
        - set_renderer: Booleano para decidir se o renderizador da camada original será copiado.
        - only_id_comp: Não utilizado diretamente nesta função, pode ser parte de uma implementação futura ou customização.
        """

        # Preparação do nome da camada clonada e verificação se a camada original é temporária
        clone_name = f"{name_suffix}_{self.layer_to_clone.name()}"
        is_temporary = "memory:" in self.layer_to_clone.source()

        # Define o tipo de geometria e o CRS baseados na camada original, para todas as novas camadas
        geom_type = self.layer_to_clone.geometryType()
        geom_type_str = ["Point", "LineString", "Polygon"][geom_type]  # Ajuste conforme necessário
        crs = self.layer_to_clone.crs().authid()
        clone = QgsVectorLayer(f"{geom_type_str}?crs={crs}", clone_name, "memory")

        # Verificação da validade da camada clonada
        if not clone.isValid():
            QMessageBox.critical(None, "Erro", "Não foi possível criar a camada clonada.")
            return None

        # Adiciona campos à camada clonada
        clone_provider = clone.dataProvider()

        # Adiciona apenas os campos especificados, se fornecidos
        if fields is not None:
            clone_provider.addAttributes(fields.toList())
        else:
             # Se não forem especificados campos, copia todos os campos da camada original
            clone_provider.addAttributes(self.layer_to_clone.fields().toList())
        clone.updateFields() # Atualiza os campos na camada clonada

        # Adiciona feições à camada clonada
        if features_to_add is not None:
            clone_provider.addFeatures(features_to_add)
        else:
            # Se não especificado, copia todas as feições da camada original
            all_features = [feat for feat in self.layer_to_clone.getFeatures()]
            clone_provider.addFeatures(all_features)

        # Copia o renderizador da camada original se solicitado
        if set_renderer:
            clone.setRenderer(self.layer_to_clone.renderer().clone())

        # Adiciona a camada clonada ao projeto e ao grupo "Camadas Clonadas"
        QgsProject.instance().addMapLayer(clone, False) # Adiciona a camada ao projeto sem mostrá-la imediatamente
        root = QgsProject.instance().layerTreeRoot()
        my_group = root.findGroup("Camadas Clonadas") # Procura o grupo de camadas clonadas
        if not my_group:
            my_group = root.addGroup("Camadas Clonadas") # Cria o grupo se não existir
        my_group.addLayer(clone) # Adiciona a camada ao grupo

        return clone # Retorna a camada clonada

    def clone_feicao(self):
        """
        Clona as feições de uma camada selecionada, excluindo seus atributos, resultando em uma nova camada apenas com geometrias.

        Processo:
        1. Itera por cada feição na camada original, copiando apenas a geometria para uma nova feição sem atributos.
        2. Cria uma nova camada "clone" que contém apenas as geometrias das feições, sem os campos de atributos.
        3. Armazena a camada clonada para uso posterior.
        4. Exibe uma mensagem de sucesso ao concluir a clonagem.
        """

        # Cria uma lista para armazenar as novas feições sem atributos
        features_to_add = []
        for feat in self.layer_to_clone.getFeatures():
            new_feat = QgsFeature() # Cria uma nova feição sem atributos, copiando apenas a geometria
            new_feat.setGeometry(feat.geometry())
            features_to_add.append(new_feat) # Adiciona a nova feição à lista

        # Cria a camada clonada sem passar os campos (ou seja, sem tabela de atributos)
        clone = self.criar_camada_clonada("Clone_SemTabela", features_to_add=features_to_add, fields=QgsFields())

        if clone is not None: # Verifica se a clonagem foi bem-sucedida e armazena a camada clonada
            self.cloned_layer = clone  # Armazenar a camada clonada para uso posterior

        # Exibe uma mensagem de sucesso na interface do usuário
        self.ui_manager.mostrar_mensagem("Clonagem de feição realizada com sucesso.", "Sucesso")

    def clone_atributos(self):
        """
        Clona uma camada selecionada, incluindo tanto as geometrias quanto os atributos das feições, 
        resultando em uma nova camada idêntica à original.

        Processo:
        1. Copia todos os campos (atributos) da camada original.
        2. Itera por cada feição na camada original, copiando tanto a geometria quanto os atributos para novas feições.
        3. Cria uma nova camada clonada que contém as novas feições com geometrias e atributos.
        4. Define o renderizador da camada clonada para ser o mesmo da camada original.
        5. Armazena a camada clonada para uso posterior.
        6. Exibe uma mensagem de sucesso ao concluir a clonagem dos atributos.
        """

        # Recupera os campos e as feições da camada original
        fields = self.layer_to_clone.fields() # Campos (atributos) da camada original
        features = [feat for feat in self.layer_to_clone.getFeatures()] # Lista de feições da camada original

        # Prepara uma nova lista para armazenar as feições clonadas com atributos
        new_features = []
        for feature in features:
            new_feature = QgsFeature(fields) # Cria uma nova feição com os mesmos campos da camada original
            new_feature.setGeometry(feature.geometry())  # Copia a geometria da feição original
            for field in fields.names():
                new_feature.setAttribute(field, feature[field])  # Copia cada atributo da feição original
            new_features.append(new_feature)  # Adiciona a nova feição à lista

        # Utiliza a função criar_camada_clonada para criar e adicionar a camada clonada ao projeto
        clone = self.criar_camada_clonada("Clone_Tabela", fields, new_features)

        # Verifica se a clonagem foi bem-sucedida
        if not clone:
            return  # Falha ao criar a camada clonada, a mensagem de erro já foi exibida

        # Configura o renderizador da camada clonada para ser igual ao da camada original
        clone.setRenderer(self.layer_to_clone.renderer().clone())

        # Armazena a referência à camada clonada para uso posterior
        self.cloned_layer = clone

        # Exibe uma mensagem de sucesso na interface do usuário
        self.ui_manager.mostrar_mensagem("Clonagem de atributos realizada com sucesso.", "Sucesso")

    def clone_combinar(self):
        """
        Combina a clonagem de feições com a adição e ajuste de campos específicos ("ID" e "Comprimento"), 
        resultando em uma camada clonada que inclui campos originais, excluindo possíveis duplicatas 
        de "ID" e "Comprimento", e adiciona estes dois campos com valores atualizados.

        Processo:
        1. Prepara uma nova estrutura de campos, adicionando campos "ID" e "Comprimento" antes dos campos originais.
        2. Exclui os campos "ID" e "Comprimento" da camada original se já existirem, para evitar duplicatas.
        3. Itera por cada feição na camada original, criando novas feições com geometrias idênticas.
        4. Ajusta os valores de "ID" (incremental) e "Comprimento" (comprimento da geometria) para cada nova feição.
        5. Copia os atributos restantes da feição original para a nova feição, ajustando os índices conforme necessário.
        6. Cria uma nova camada clonada com a estrutura de campos ajustada e as novas feições.
        7. Aplica um tratamento adicional para os campos "ID" e "Comprimento" na camada clonada, se necessário.
        8. Exibe uma mensagem de sucesso ao concluir a operação.
        """

        # Inicializa a estrutura de campos para a nova camada, incluindo "ID" e "Comprimento"
        fields_to_add = QgsFields()

        # Adiciona primeiramente os campos "ID" e "Comprimento"
        fields_to_add.append(QgsField("ID", QVariant.Int))
        fields_to_add.append(QgsField("Comprimento", QVariant.Double))

        # Recupera os campos da camada original
        original_fields = self.layer_to_clone.fields()

        # Adiciona os campos da camada original, excluindo "ID" e "Comprimento" se já existirem
        for field in original_fields:
            if field.name() not in ["ID", "Comprimento"]:
                fields_to_add.append(field)

        # Lista para armazenar as novas feições com campos ajustados
        new_features = []
        for index, feature in enumerate(self.layer_to_clone.getFeatures(), start=1):
            new_feature = QgsFeature(fields_to_add)  # Cria uma nova feição com a estrutura de campos atualizada
            new_feature.setGeometry(feature.geometry()) # Copia a geometria

            # Prepara uma lista de atributos com espaços reservados para todos os campos
            new_attributes = [None] * len(fields_to_add)

            # Ajusta os valores de "ID" e "Comprimento" diretamente
            new_attributes[0] = index  # ID baseado no índice da iteração
            new_attributes[1] = round(feature.geometry().length(), 3) # Comprimento calculado a partir da geometria

            # Copia os atributos da feição original, ajustando para a nova estrutura de campos
            original_attributes = feature.attributes()
            for i, field in enumerate(original_fields):
                if field.name() not in ["ID", "Comprimento"]:
                    # Encontra o índice correto para o atributo na nova lista de campos
                    new_index = fields_to_add.indexOf(field.name()) # Encontra o novo índice do campo
                    new_attributes[new_index] = original_attributes[i] # Atribui o valor correspondente

            new_feature.setAttributes(new_attributes) # Atualiza os atributos da nova feição
            new_features.append(new_feature) # Adiciona a feição à lista

        # Cria a camada clonada com os campos e feições preparados
        clone = self.criar_camada_clonada("Clone_Combinado", fields=fields_to_add, features_to_add=new_features)

        # Chama a função tratar_linhas para tratar os campos "ID" e "Comprimento" na camada clonada
        self.ui_manager.tratar_linhas(clone)

        if clone: # Aplica tratamento adicional se necessário
            # Chama a função para tratar "ID" e "Comprimento" se necessário
            self.ui_manager.mostrar_mensagem("Combinação de tabela e tratamento de linhas realizados com sucesso.", "Sucesso")

        return clone # Retorna a camada clonada

    def clone_excluir(self):
        """
        Cria uma camada clonada que exclui todos os campos originais exceto a geometria,
        adicionando apenas dois novos campos: "ID" e "Comprimento". "ID" é um identificador sequencial
        e "Comprimento" representa o comprimento da geometria da feição. Esta função é útil para simplificar
        a camada, mantendo apenas informações essenciais e a geometria.

        Processo:
        1. Prepara uma nova estrutura de campos contendo apenas "ID" e "Comprimento".
        2. Itera pelas feições da camada original, copiando suas geometrias.
        3. Para cada nova feição, calcula e atribui um ID sequencial e o comprimento da geometria.
        4. Cria uma camada clonada com a nova estrutura de campos e as novas feições.
        5. Aplica um tratamento adicional para os campos "ID" e "Comprimento", se necessário.
        6. Exibe uma mensagem de sucesso ao concluir a operação.
        """

        # Inicializa os campos para a nova camada com "ID" e "Comprimento"
        new_fields = QgsFields()
        new_fields.append(QgsField("ID", QVariant.Int))
        new_fields.append(QgsField("Comprimento", QVariant.Double))

        # Lista para armazenar as novas feições com os valores de "ID" e "Comprimento" definidos
        new_features = []
        for index, feature in enumerate(self.layer_to_clone.getFeatures(), start=1):
            new_feature = QgsFeature(new_fields) # Cria uma nova feição com a estrutura de campos atualizada
            new_feature.setGeometry(feature.geometry()) # Copia a geometria da feição original
            new_feature.setAttribute("ID", index)   # Atribui um ID sequencial
            new_feature.setAttribute("Comprimento", round(feature.geometry().length(), 3))  # Calcula e atribui o comprimentodecimais
            new_features.append(new_feature) # Adiciona a nova feição à lista

        # Utiliza a função de utilidade para criar a camada clonada com os novos campos e feições
        clone = self.criar_camada_clonada("Clone_Excluir", new_fields, new_features)

        if clone is None:
            QMessageBox.critical(None, "Erro", "Falha ao criar a camada clonada.") # Exibe uma mensagem de erro se a clonagem falhar
            return

        # Chamada para tratar os campos "ID" e "Comprimento" após a clonagem
        self.ui_manager.tratar_linhas(clone)

        # Armazena a referência à camada clonada para uso posterior
        self.cloned_layer = clone

        # Mensagem de sucesso ao finalizar o processo
        self.ui_manager.mostrar_mensagem("Exclusão de tabela e tratamento de linhas realizados com sucesso.", "Sucesso")