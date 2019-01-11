import os
import re
import time
import uuid

from AssemblyUtil.AssemblyUtilClient import AssemblyUtil
from kb_SPAdes.utils.spades_utils import SPAdesUtils


def log(message, prefix_newline=False):
    """Logging function, provides a hook to suppress or redirect log messages."""
    print(('\n' if prefix_newline else '') + '{0:.2f}'.format(time.time()) + ': ' + str(message))


def mkdir_p(path):
    """
    mkdir_p: make directory for given path
    """
    if not path:
        return
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == os.errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class SPAdesAssembler(object):
    INVALID_WS_OBJ_NAME_RE = re.compile('[^\\w\\|._-]')
    INVALID_WS_NAME_RE = re.compile('[^\\w:._-]')

    PARAM_IN_CS_NAME = 'output_contigset_name'
    SPAdes_PROJECT_DIR = 'spades_project_dir'
    SPAdes_final_scaffold_sequences = 'scaffolds.fasta'  # resulting scaffolds sequences
    SPAdes_final_contigs = 'contigs.fasta'  # resulting contigs

    def __init__(self, config, provenance):
        """
        __init__: construct SPAdesAssembler
        """
        # BEGIN_CONSTRUCTOR
        self.workspace_url = config["workspace-url"]
        self.callback_url = config["SDK_CALLBACK_URL"]
        self.token = config["KB_AUTH_TOKEN"]
        self.provenance = provenance

        self.au = AssemblyUtil(self.callback_url)

        self.scratch = os.path.join(config['scratch'], str(uuid.uuid4()))
        mkdir_p(self.scratch)

        self.spades_version = 'SPADES-' + os.environ['SPADES_VERSION']
        self.proj_dir = self._create_proj_dir(self.scratch)
        self.s_utils = SPAdesUtils(self.proj_dir, config)
        # END_CONSTRUCTOR
        pass

    def _save_assembly(self, params, asmbl_ok, contig_fa_file):
        """
        save_assembly: save the assembly to KBase and, if everything has gone well, create a report
        """
        returnVal = {
            "report_ref": None,
            "report_name": None
        }

        wsname = params['workspace_name']
        fa_file_dir = self._find_file_path(self.proj_dir, contig_fa_file)

        if (asmbl_ok == 0 and fa_file_dir != ''):
            fa_file_dir = os.path.join(self.proj_dir, fa_file_dir)
            fa_file_path = os.path.join(fa_file_dir, contig_fa_file)

            log("Load assembly from fasta file {}...".format(fa_file_path))
            self.s_utils.save_assembly(fa_file_path, wsname,
                                       params[self.PARAM_IN_CS_NAME])
            if params['create_report'] == 1:
                report_name, report_ref = self.s_utils.generate_report(
                                            fa_file_path, params, fa_file_dir, wsname)
                returnVal = {'report_name': report_name, 'report_ref': report_ref}
        else:
            log("run_hybrid_spades failed.")

        return returnVal

    def _find_file_path(self, search_dir, search_file_name):
        """
        _find_file_path: search a given directory to find the given file with path
        """
        for dirName, subdirList, fileList in os.walk(search_dir):
            for fname in fileList:
                if fname == search_file_name:
                    log('Found file {} in {}'.format(fname, dirName))
                    return dirName
        log('Could not find file {}!'.format(search_file_name))
        return ''

    def _create_proj_dir(self, home_dir):
        """
        _creating the project directory for SPAdes
        """
        prjdir = os.path.join(home_dir, self.SPAdes_PROJECT_DIR)
        mkdir_p(prjdir)
        return prjdir

    def _get_version_from_subactions(self, module_name, subactions):
        """
        _get_version_from_subactions: as the name says
        """
        # go through each sub action looking for
        if not subactions:
            return 'dev'  # 'release'  # default to release if we can't find anything
        for sa in subactions:
            if 'name' in sa:
                if sa['name'] == module_name:
                    # local-docker-image implies that we are running in kb-test, so return 'dev'
                    if sa['commit'] == 'local-docker-image':
                        return 'dev'
                    # to check that it is a valid hash, make sure it is the right
                    # length and made up of valid hash characters
                    if re.match('[a-fA-F0-9]{40}$', sa['commit']):
                        return sa['commit']
        # again, default to setting this to release
        return 'dev'  # 'release'

    def run_hybrid_spades(self, params):
        # 1. validate & process the input parameters
        validated_params = self.s_utils.check_spades_params(params)

        # 2. create the yaml input data set file
        yaml_file = self.s_utils.construct_yaml_dataset_file(validated_params)

        # 3. run the spades.py against the yaml file
        if os.path.isfile(yaml_file):
            assemble_ok = self.s_utils.run_assemble(yaml_file, validated_params)
        else:
            assemble_ok = -1

        # 5. save the assembly to KBase and, if everything has gone well, create a report
        return self._save_assembly(params, assemble_ok, self.SPAdes_final_contigs)
