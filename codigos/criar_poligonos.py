from qgis.core import (QgsField, QgsProject, QgsVectorLayer, QgsWkbTypes,
                       QgsFieldConstraints, QgsEditorWidgetSetup,
                       QgsTextFormat, QgsTextBufferSettings,
                       QgsVectorLayerSimpleLabeling, QgsPalLayerSettings,
                       QgsTextBackgroundSettings, QgsDistanceArea)
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QFont, QColor

def criar_camada_poligonos(iface, nome_camada=None):
    """
    Cria e adiciona uma nova camada de polígonos temporária ao painel de camadas do QGIS.
    Args:
        iface: Interface principal do QGIS.
        nome_camada: Nome opcional para a nova camada. Se não fornecido, um nome padrão é gerado.

    Esta função cria uma camada de polígonos com três campos (ID, Perímetro e Área) e configura
    as etiquetas para exibir o ID com fonte negrito, itálico, cor azul e fundo branco.
    """

    crs_projeto = QgsProject.instance().crs().authid() # Obtém o CRS do projeto atual

    nome_camada = nome_camada or gera_nome_camada("Polígono Temp") # Gera um nome único para a camada se não for fornecido

    # Cria uma nova camada de polígonos na memória com o CRS e o nome fornecidos
    camada_poligonos = QgsVectorLayer(f"Polygon?crs={crs_projeto}", nome_camada, "memory")
    configura_campos(camada_poligonos) # Configura os campos da camada

    # Conecta o sinal 'featureAdded' à função 'atualizar_valores_poligono'
    camada_poligonos.featureAdded.connect(lambda fid: atualizar_valores_poligono(camada_poligonos, fid))

    configura_etiquetas(camada_poligonos) # Configura e aplica as definições de etiqueta

    QgsProject.instance().addMapLayer(camada_poligonos) # Adiciona a camada ao projeto atual

    conectar_sinais(camada_poligonos) # Conecta os sinais depois que a camada é adicionada ao projeto
 
    camada_poligonos.startEditing() # Inicia a edição da camada

def gera_nome_camada(nome_base):
    """
    Esta função gera um nome único para uma camada com base em um nome base fornecido.
    Ela faz isso adicionando um contador ao nome base e incrementando-o até que um nome único seja encontrado.
    """
    contador = 1
    nome_camada = f"{nome_base} {contador}"  # Começa a contagem a partir de 1
    while QgsProject.instance().mapLayersByName(nome_camada): # Verifica se o nome já existe
        contador += 1
        nome_camada = f"{nome_base} {contador}"  # Atualiza o nome da camada com o novo contador
    return nome_camada # Retorna o nome único

def conectar_sinais(camada):
    """
    Esta função conecta os sinais 'featureAdded' e 'geometryChanged' à função 'atualizar_valores_poligono'.
    Isso garante que os valores do polígono sejam atualizados sempre que um recurso for adicionado ou sua geometria alterada.
    """
    camada.featureAdded.connect(lambda fid: atualizar_valores_poligono(camada, fid)) # Conecta o sinal 'featureAdded'
    camada.geometryChanged.connect(lambda fid, geom: atualizar_valores_poligono(camada, fid)) # Conecta o sinal 'geometryChanged'

def atualizar_valores_poligono(camada, fid):
    """
    Esta função atualiza os valores de 'Perimetro' e 'Area' de um polígono quando ele é adicionado ou sua geometria é alterada.
    Considera cálculos específicos caso o sistema de referência seja geográfico.
    """
    index_perimetro = camada.fields().indexOf("Perimetro")
    index_area = camada.fields().indexOf("Area")

    feature = camada.getFeature(fid)
    if feature.isValid() and feature.geometry() and not feature.geometry().isEmpty():
        geom = feature.geometry()

        d = QgsDistanceArea()
        d.setSourceCrs(camada.crs(), QgsProject.instance().transformContext())
        d.setEllipsoid(QgsProject.instance().crs().ellipsoidAcronym())

        if camada.crs().isGeographic():
            perimetro = round(d.measurePerimeter(geom), 3)
            area = round(d.measureArea(geom), 3)
        else:
            perimetro = round(geom.length(), 3)
            area = round(geom.area(), 3)

        camada.changeAttributeValue(fid, index_perimetro, perimetro)
        camada.changeAttributeValue(fid, index_area, area)

def configura_campos(camada):
    """
    Esta função configura os campos de uma camada.
    Ela adiciona campos para 'ID', 'Perimetro' e 'Area', e configura suas restrições e widgets.
    """
    id_field = QgsField("ID", QVariant.Int) # Cria um campo 'ID'
    perimetro_field = QgsField("Perimetro", QVariant.Double) # Cria um campo 'Perimetro'
    area_field = QgsField("Area", QVariant.Double) # Cria um campo 'Area'

    constraints = QgsFieldConstraints() # Cria um novo objeto de restrições
    constraints.setConstraint(QgsFieldConstraints.ConstraintUnique) # Define a restrição 'Unique'
    constraints.setConstraint(QgsFieldConstraints.ConstraintNotNull) # Define a restrição 'NotNull'
    id_field.setConstraints(constraints) # Aplica as restrições ao campo 'ID'

    # Adiciona campos à camada
    camada.dataProvider().addAttributes([id_field, perimetro_field, area_field])
    camada.updateFields() # Atualiza os campos da camada

    # Oculta os campos Perímetro e Área inicialmente
    widget_setup_oculto = QgsEditorWidgetSetup("Hidden", {}) # Cria um novo setup de widget oculto
    # Configura os widgets dos campos 'Perimetro' e 'Area' para serem ocultos
    camada.setEditorWidgetSetup(camada.fields().indexOf("Perimetro"), widget_setup_oculto)
    camada.setEditorWidgetSetup(camada.fields().indexOf("Area"), widget_setup_oculto)

    def atualizar_valores_poligono(camada, fid):
        """
        Esta função atualiza os valores de 'Perimetro' e 'Area' de um polígono quando ele é adicionado ou sua geometria é alterada.
        Considera cálculos específicos caso o sistema de referência seja geográfico.
        """
        index_perimetro = camada.fields().indexOf("Perimetro")
        index_area = camada.fields().indexOf("Area")

        feature = camada.getFeature(fid)
        if feature.isValid() and feature.geometry() and not feature.geometry().isEmpty():
            geom = feature.geometry()

            d = QgsDistanceArea()
            d.setSourceCrs(camada.crs(), QgsProject.instance().transformContext())
            d.setEllipsoid(QgsProject.instance().crs().ellipsoidAcronym())

            if camada.crs().isGeographic():
                perimetro = round(d.measurePerimeter(geom), 3)
                area = round(d.measureArea(geom), 3)
            else:
                perimetro = round(geom.length(), 3)
                area = round(geom.area(), 3)

            camada.changeAttributeValue(fid, index_perimetro, perimetro)
            camada.changeAttributeValue(fid, index_area, area)

def configura_etiquetas(camada):
    """
    Esta função configura as etiquetas de uma camada.
    Ela habilita as etiquetas, define o campo de etiqueta para 'ID' e configura o formato das etiquetas.
    """
    settings_etiqueta = QgsPalLayerSettings() # Cria um novo objeto de configurações de etiqueta
    settings_etiqueta.fieldName = "ID" # Define o campo de etiqueta para 'ID'
    settings_etiqueta.enabled = True # Habilita as etiquetas

    text_format = QgsTextFormat() # Cria um novo objeto de formato de texto
    text_format.setColor(QColor(0, 0, 255)) # Define a cor do texto para azul
    fonte_etiqueta = QFont("Arial", 14, QFont.Bold, True)  # Cria uma nova fonte para as etiquetas, negrito e itálico
    text_format.setFont(fonte_etiqueta) # Define a fonte das etiquetas

    background_settings = QgsTextBackgroundSettings() # Cria um novo objeto de configurações de fundo
    background_settings.setEnabled(True) # Habilita o fundo
    background_settings.setFillColor(QColor(255, 255, 255)) # Define a cor de preenchimento do fundo para branco
    text_format.setBackground(background_settings) 

    settings_etiqueta.setFormat(text_format) # Aplica o formato de texto às configurações de etiqueta
    camada.setLabelsEnabled(True) # Habilita as etiquetas na camada
    camada.setLabeling(QgsVectorLayerSimpleLabeling(settings_etiqueta)) # Aplica as configurações de etiqueta à camada
