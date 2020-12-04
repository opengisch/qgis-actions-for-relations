# QGIS Actions for relations

This is a QGIS 3.4+ plugin adding useful actions to enhance relations:

* show children features of a selection of parent features
* batch insert of children features

## Batch insert
1. Select some features in the referenced layer.
2. Switch on the editing of the referencing layer.
3. In the legend, in the context menu of the layer, click on the entry Add features in {referencing_layer} for the selected features in {referenced_layer}`
3. A form shows up to define attributes of the features to be created in the referencing layer (the referencing field(s) will not be shown since they are filled automatically).
4. The plugin will automatically create as many features as there are features selected in the referenced layer. Each of them will point to one of the selected referenced features. 