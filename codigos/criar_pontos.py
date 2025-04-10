from qgis.core import (QgsField, QgsProject, QgsVectorLayer, QgsWkbTypes,
                       QgsFieldConstraints, QgsEditorWidgetSetup,
                       QgsTextFormat, QgsTextBufferSettings,
                       QgsVectorLayerSimpleLabeling, QgsPalLayerSettings,
                       QgsTextBackgroundSettings)
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QFont, QColor

def criar_camada_pontos(iface, nome_camada=None):
    crs_projeto = QgsProject.instance().crs()
    is_geografico = crs_projeto.isGeographic()
    
    nome_camada = nome_camada or gera_nome_camada("Ponto Temp")
    camada_pontos = QgsVectorLayer(f"Point?crs={crs_projeto.authid()}", nome_camada, "memory")
    
    configura_campos(camada_pontos, is_geografico)
    configura_etiquetas(camada_pontos)
    QgsProject.instance().addMapLayer(camada_pontos)
    conectar_sinais(camada_pontos, is_geografico)
    camada_pontos.startEditing()

    # Conexão dos sinais
    camada_pontos.featureAdded.connect(lambda fid: atualizar_valores_ponto(camada_pontos, fid, is_geografico))
    camada_pontos.geometryChanged.connect(lambda fid, geom: atualizar_valores_ponto(camada_pontos, fid, is_geografico))
    
def gera_nome_camada(nome_base):
    contador = 1
    nome_camada = f"{nome_base} {contador}" 
    while QgsProject.instance().mapLayersByName(nome_camada):
        contador += 1
        nome_camada = f"{nome_base} {contador}"
    return nome_camada

def conectar_sinais(camada, is_geografico):
    # Usa is_geografico ao conectar o sinal
    camada.geometryChanged.connect(lambda fid, geom: atualizar_valores_ponto(camada, fid, is_geografico))

    # A conexão com featureAdded provavelmente também precisa de is_geografico
    camada.featureAdded.connect(lambda fid: atualizar_valores_ponto(camada, fid, is_geografico))

def configura_campos(camada, is_geografico):
    # Cria e configura o campo ID com restrições
    id_field = QgsField("ID", QVariant.Int)
    
    constraints = QgsFieldConstraints()
    constraints.setConstraint(QgsFieldConstraints.ConstraintUnique)
    constraints.setConstraint(QgsFieldConstraints.ConstraintNotNull)
    id_field.setConstraints(constraints)

    # Cria os campos X e Y
    x_field = QgsField("X", QVariant.Double)
    y_field = QgsField("Y", QVariant.Double)

    # Inicializa a lista de campos a serem adicionados
    campos = [id_field, x_field, y_field]
    
    if is_geografico:
        campos.extend([QgsField('X_DMS', QVariant.String, len=20),
                       QgsField('Y_DMS', QVariant.String, len=20)])

    # Adiciona campos à camada
    camada.dataProvider().addAttributes(campos)
    camada.updateFields()

    # Configura os campos X e Y para serem ocultados na UI
    widget_setup_oculto = QgsEditorWidgetSetup("Hidden", {})
    camada.setEditorWidgetSetup(camada.fields().indexOf("X"), widget_setup_oculto)
    camada.setEditorWidgetSetup(camada.fields().indexOf("Y"), widget_setup_oculto)
    camada.setEditorWidgetSetup(camada.fields().indexOf("X_DMS"), widget_setup_oculto)
    camada.setEditorWidgetSetup(camada.fields().indexOf("Y_DMS"), widget_setup_oculto)
    
def atualizar_valores_ponto(camada, fid, is_geografico):
    index_x = camada.fields().indexOf("X")
    index_y = camada.fields().indexOf("Y")
    feature = camada.getFeature(fid)
    
    if feature.isValid() and feature.geometry() and not feature.geometry().isEmpty():
        ponto = feature.geometry().asPoint()
        x_val = round(ponto.x(), 6 if is_geografico else 3)
        y_val = round(ponto.y(), 6 if is_geografico else 3)
        camada.changeAttributeValue(fid, index_x, x_val)
        camada.changeAttributeValue(fid, index_y, y_val)

        if is_geografico:
            x_dms = dec_to_dms(ponto.x())
            y_dms = dec_to_dms(ponto.y())
            index_x_dms = camada.fields().indexOf("X_DMS")
            index_y_dms = camada.fields().indexOf("Y_DMS")
            camada.changeAttributeValue(fid, index_x_dms, x_dms)
            camada.changeAttributeValue(fid, index_y_dms, y_dms)

def dec_to_dms(valor):
    sinal = "-" if valor < 0 else ""
    valor = abs(valor)
    graus = int(valor)
    minutos = int((valor - graus) * 60)
    segundos = (valor - graus - minutos/60) * 3600
    return f"{sinal}{graus}° {minutos}' {segundos:.2f}\""

def configura_etiquetas(camada):
    settings_etiqueta = QgsPalLayerSettings()
    settings_etiqueta.fieldName = "ID"
    settings_etiqueta.enabled = True
    
    text_format = QgsTextFormat()
    text_format.setColor(QColor(0, 0, 255))
    fonte_etiqueta = QFont("Arial", 12)
    text_format.setFont(fonte_etiqueta)
    
    background_settings = QgsTextBackgroundSettings()
    background_settings.setEnabled(True)
    background_settings.setFillColor(QColor(255, 255, 255))
    text_format.setBackground(background_settings)
    
    settings_etiqueta.setFormat(text_format)
    camada.setLabelsEnabled(True)
    camada.setLabeling(QgsVectorLayerSimpleLabeling(settings_etiqueta))
