from qgis.core import (
    QgsField, QgsProject, QgsVectorLayer, QgsFieldConstraints, 
    QgsEditorWidgetSetup, QgsPalLayerSettings, QgsTextFormat, 
    QgsVectorLayerSimpleLabeling, QgsUnitTypes, QgsDistanceArea, QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import QVariant 

def criar_camada_linhas(iface, nome_camada=None, cor=None, crs=None):
    """Cria e configura uma nova camada de linhas temporária, adicionando-a ao painel de camadas do QGIS.
    
    Parâmetros:
      - iface: interface do QGIS.
      - nome_camada: nome desejado para a camada. Se None, é gerado um nome único.
      - cor: (opcional) um objeto QColor. Se fornecido, a cor é aplicada ao símbolo da camada.
      - crs: (opcional) o authid do CRS para a nova camada. Se None, utiliza o CRS do projeto.
    
    Retorna:
      A camada de linhas criada.
    """
    # Se o CRS não foi informado, usa o CRS atual do projeto.
    if crs is None:
        crs = obter_crs_projeto_atual()
    nome_camada = gerar_nome_camada(nome_camada)

    camada_linhas = criar_camada_vectorial(nome_camada, crs)
    adicionar_campos(camada_linhas)
    configurar_campo_oculto(camada_linhas, "Comprimento")

    # Inicia a edição da camada
    camada_linhas.startEditing()

    conectar_sinais(camada_linhas)

    # Aplica a cor, se fornecida
    if cor is not None:
        renderer = camada_linhas.renderer()
        from qgis.core import QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer
        if isinstance(renderer, QgsSingleSymbolRenderer):
            symbol = renderer.symbol()
            symbol.setColor(cor)
            camada_linhas.triggerRepaint()
        elif isinstance(renderer, QgsCategorizedSymbolRenderer):
            for categoria in renderer.categories():
                categoria.symbol().setColor(cor)
            camada_linhas.triggerRepaint()

    QgsProject.instance().addMapLayer(camada_linhas)

    return camada_linhas

def obter_crs_projeto_atual():
    """Obtém o Sistema de Referência de Coordenadas (SRC) do projeto atual."""
    return QgsProject.instance().crs().authid()

def gerar_nome_camada(nome_camada):
    """Gera um nome único para a camada se nenhum for fornecido."""
    if not nome_camada:
        nome_base = "Linha Temp"
        contador = 1
        while QgsProject.instance().mapLayersByName(f"{nome_base} {contador}"):
            contador += 1
        return f"{nome_base} {contador}"
    return nome_camada

def criar_camada_vectorial(nome, crs):
    """Cria uma nova camada vectorial de linhas temporária."""
    return QgsVectorLayer(f"LineString?crs={crs}", nome, "memory")

def adicionar_campos(camada):
    """Adiciona campos ID e Comprimento à camada, com restrições no campo ID."""
    id_field = QgsField("ID", QVariant.Int)
    comp_field = QgsField("Comprimento", QVariant.Double)

    id_field.setConstraints(constraints_com_incremente())

    # Adiciona ambos os campos de uma vez
    camada.dataProvider().addAttributes([id_field, comp_field])
    camada.updateFields()

def constraints_com_incremente():
    """Define restrições para o campo de incremento."""
    constraints = QgsFieldConstraints()
    constraints.setConstraint(QgsFieldConstraints.ConstraintUnique)
    constraints.setConstraint(QgsFieldConstraints.ConstraintNotNull)
    return constraints

def configurar_campo_oculto(camada, nome_campo):
    """Configura um campo da camada para ser oculto na interface."""
    index_campo = camada.fields().indexOf(nome_campo)
    widget_setup = QgsEditorWidgetSetup("Hidden", {})
    camada.setEditorWidgetSetup(index_campo, widget_setup)

def conectar_sinais(camada):
    """Conecta sinais relevantes para atualizações automáticas na camada."""
    camada.featureAdded.connect(lambda fid: atualizar_comprimento_linha(camada, fid))
    camada.geometryChanged.connect(lambda fid, geom: atualizar_comprimento_linha(camada, fid))

def atualizar_comprimento_linha(camada, fid):
    """Atualiza o comprimento da linha adicionada e configura etiquetas."""
    index_comp = camada.fields().indexOf("Comprimento")
    feature = camada.getFeature(fid)
    d = QgsDistanceArea()

    if camada.crs().isGeographic():
        d.setSourceCrs(camada.crs(), QgsProject.instance().transformContext())
        d.setEllipsoid(QgsProject.instance().crs().ellipsoidAcronym())
        comprimento = round(d.measureLength(feature.geometry()), 3)
    else:
        comprimento = round(feature.geometry().length(), 3)

    # Atualiza o comprimento para a feição que foi modificada
    camada.changeAttributeValue(fid, index_comp, comprimento)

    if not hasattr(camada, "etiquetas_configuradas"):
        configurar_etiquetas(camada)
        camada.etiquetas_configuradas = True

def configurar_etiquetas(camada):
    """Configura as etiquetas para a camada."""
    etiquetas = QgsPalLayerSettings()
    etiquetas.enabled = True
    etiquetas.fieldName = 'ID'
    etiquetas.placement = QgsPalLayerSettings.Line
    etiquetas.setFormat(formato_texto_etiqueta())

    camada.setLabelsEnabled(True)
    camada.setLabeling(QgsVectorLayerSimpleLabeling(etiquetas))
    camada.triggerRepaint()

def formato_texto_etiqueta():
    """Retorna o formato do texto para as etiquetas."""
    texto_formato = QgsTextFormat()
    fonte = QFont("Arial", 12, QFont.Bold, True)  # Negrito e itálico
    texto_formato.setFont(fonte)
    texto_formato.setColor(QColor("blue"))
    texto_formato.buffer().setEnabled(True)
    texto_formato.buffer().setSize(3)
    texto_formato.buffer().setColor(QColor("white"))
    return texto_formato
