from dicom.sequence import Sequence
from dicom.valuerep import PersonName3
from girder import events
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType, TokenScope
from girder.utility.model_importer import ModelImporter
import dicom
import six


class DicomItem(Resource):

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get DICOM metadata, if any, for all files in the item.')
        .modelParam('id', 'The item ID',
                    model='item', level=AccessType.READ, paramType='path')
        .param('filters', 'Filter returned DICOM tags (comma-separated).',
               required=False, default='')
        .param('force', 'Force re-parsing the DICOM files. Write access required.',
               required=False, dataType='boolean', default=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the item.', 403)
    )
    def getDicom(self, item, filters, force):
        if force:
            self.model('item').requireAccess(
                item, user=self.getCurrentUser(), level=AccessType.WRITE)
        filters = set(filter(None, filters.split(',')))
        files = list(ModelImporter.model('item').childFiles(item))
        # process files if they haven't been processed yet
        for i, f in enumerate(files):
            if force or 'dicom' not in f:
                files[i] = process_file(f)
        # filter out non-dicom files
        files = [x for x in files if x.get('dicom')]
        # sort files
        files = sorted(files, key=sort_key)
        # execute filters
        if filters:
            for f in files:
                dicom = f['dicom']
                dicom = dict((k, dicom[k]) for k in filters if k in dicom)
                f['dicom'] = dicom
        return files

    # @access.public(scope=TokenScope.DATA_READ)
    # @autoDescribeRoute(
    #     Description('Get and store DICOM metadata, if any, for all files in the item.')
    #     .modelParam('id', 'The item ID',
    #                 model='item', level=AccessType.READ, paramType='path')
    #     .errorResponse('ID was invalid.')
    #     .errorResponse('Read permission denied on the item.', 403)
    # )
    # def storeMetaData(self, item):
    #     # The goal is to store extract common tag of dicom files
    #     # to store them into the dicom item as metadata
    #     item['dicomMeta'] = {}
    #     files = list(ModelImporter.model('item').childFiles(item))
    #     for i, f in enumerate(files):                     # EXTRACT METADATA
    #         f['dicom'] = parse_file(f)
    #         files[i] = f
    #     # filter out non-dicom files
    #     files = [x for x in files if x.get('dicom')]
    #     # sort files
    #     files = sorted(files, key=sort_key)
    #     for i, f in files:
    #         metadata[i] = f['dicom']
    #         ### SORT COMMON AND NON COMMON


def _1extractMetadata(item):
    item['dicomMeta'] = {}
    item['dicomFiles'] = []

    for file in ModelImporter.model('item').childFiles(item):
        if not isDicom(file):
            continue
        fileMeta = parse_file(file)
        item['dicomFiles'].append({
            'fileId': file['_id'],
            'meta': fileMeta
        })
    return item

def isDicom(file):
    if file.get('dicom'):
        return True
    return False

def _2extractCommonMetadata(item):          # MARCHE PAS ENCORE
    # find the common data
    old_k = []
    old_v  = []
    metadata = []
    uniqueMetadata = []
    commonMetadata = []
    uniqueListMetadata = []
    OK = False
    for file in item['dicomFiles']:
        meta = file['meta']
        # FIRST FILE AS REFERENCE
        if not old_k and not old_v:
            for k, v in meta.iteritems():
                old_k.append(k)
                old_v.append(v)
        else:
            for k, v in meta.iteritems():
                lgtV = len(commonMetadata)
                for j in old_v:
                    if j == v:
                        commonMetadata.append({k:v})
                if lgtV == len(commonMetadata):
                    uniqueMetadata.append({k:v})
            uniqueListMetadata.append(uniqueMetadata)
            uniqueMetadata = []
            # if OK == True:
            #     break
            # else:
            #     OK = True
    # Store common tags and values
    item['dicomMeta'] = setListObject(commonMetadata)
    print '\n--> COMMON META\n', item['dicomMeta']
    # Store list of different tags per files
    item['dicomFiles'] = uniqueListMetadata
    print '\n--> UNIQUE META\n', item['dicomFiles']

    return item

def setListObject(listObject):
    # Delete all the redundante object from the list
    for i in range(0,len(listObject)-1):
        removeObject = []
        for j in range(i+1,len(listObject)):
            if listObject[i] == listObject[j]:
                removeObject.append(j)
        for k in range(0,len(removeObject)):
            listObject.pop(removeObject[k])
            for h in range(0,len(removeObject)):
                removeObject[h] -= 1
    return listObject

def sort_key(f):
    dicom = f.get('dicom', {})
    return (
        dicom.get('SeriesNumber'),
        dicom.get('InstanceNumber'),
        dicom.get('SliceLocation'),
        f['name'],
    )


def coerce(x):
    if isinstance(x, Sequence):
        return None
    if isinstance(x, list):
        return [coerce(y) for y in x]
    if isinstance(x, PersonName3):
        return x.encode('utf-8')
    try:
        six.text_type(x)
        return x
    except Exception:
        return None


def parse_file(f):
    data = {}
    try:
        # download file and try to parse dicom
        with ModelImporter.model('file').open(f) as fp:
            ds = dicom.read_file(
                fp,
                # some dicom files don't have a valid header
                force=True,
                # don't read huge fields, esp. if this isn't even really dicom
                defer_size=1024,
                # don't read image data, just metadata
                stop_before_pixels=True)
            # does this look like a dicom file?
            if (len(ds.dir()), len(ds.items())) == (0, 1):
                return data
            # human-readable keys
            for key in ds.dir():
                value = coerce(ds.data_element(key).value)
                if value is not None:
                    data[key] = value
            # hex keys
            for key, value in ds.items():
                key = 'x%04x%04x' % (key.group, key.element)
                value = coerce(value.value)
                if value is not None:
                    data[key] = value
    except Exception:
        pass  # if an error occurs, probably not a dicom file
    return data


def process_file(f):
    f['dicom'] = parse_file(f)
    return ModelImporter.model('file').save(f)


def handler(event):
    process_file(event.info['file'])


def load(info):
    events.bind('data.process', 'dicom_viewer', handler)
    dicomItem = DicomItem()
    info['apiRoot'].item.route(
        'GET', (':id', 'dicom'), dicomItem.getDicom)
    # info['apiRoot'].item.route(
    #     'POST', (':id', 'parseDicom'), dicomItem.storeMetaData)
