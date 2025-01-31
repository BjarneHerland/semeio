from ert_shared.libres_facade import LibresFacade
from ert_shared.plugins.plugin_manager import hook_implementation

import semeio.workflows.localisation.local_script_lib as local
from semeio.communication import SemeioScript
from semeio.workflows.localisation.localisation_config import LocalisationConfig


class LocalisationConfigJob(SemeioScript):
    def run(self, *args):
        ert = self.ert()
        facade = LibresFacade(self.ert())
        # Clear all correlations
        local.clear_correlations(ert)

        # Read yml file with specifications
        config_dict = local.read_localisation_config(args)

        # Get all observations from ert instance
        obs_keys = [
            facade.get_observation_key(nr)
            for nr, _ in enumerate(facade.get_observations())
        ]

        ert_parameters = local.get_param_from_ert(ert.ensembleConfig())

        config = LocalisationConfig(
            observations=obs_keys,
            parameters=ert_parameters.to_list(),
            **config_dict,
        )

        local.add_ministeps(
            config,
            ert_parameters.to_dict(),
            ert.getLocalConfig(),
            ert.ensembleConfig(),
            ert.eclConfig().getGrid(),
        )


DESCRIPTION = """
===================
Localisation setup
===================
LOCALISATION_JOB is used to define which pairs of model parameters and
observations to be active and which pairs to have reduced or 0 correlation.
If no localisation is specified, all model parameters and observations may be
correlated, although correlations can be small. With a finite ensemble of
realisations the estimate of correlations will have sampling uncertainty and
unwanted or unphysical correlations may appear.

By using the localisation job, it is possible to restrict the allowed correlations
or reduce the correlations by a factor between 0 and 1.

Features
----------
The following features are implemented:

 - The user defines groups of model parameters and observations.
 - Wildcard notation can be used to specify a selection of model parameter groups
   and observation groups.
 - For scalar parameters coming from the ERT keywords GEN_KW and GEN_PARAM,
   the correlation with observations can be specified to be active or inactive.
 - For field parameters coming from the ERT keywords FIELD and SURFACE,
   it is also possible to specify that the correlation between observations and
   model parameters may vary from location to location. A field parameter
   value corresponding to a grid cell (i,j,k) in location (x,y,z) is reduced by a
   scaling factor varying by distance from a reference point e.g at a location (X,Y,Z),
   usually specified to be close to an observation group.
 - Multiple pairs of groups of model parameters and observations can be specified
   to have active correlations.


Using the localisation setup in ERT
-------------------------------------

To setup localisation:
 - Specify a YAML format configuration file for localisation.
 - Create a workflow file containing the line:
   LOCALISATION_JOB <localisation_config_file>
 - Specify to load the workflow file in the ERT config file using
   LOAD_WORKFLOW keyword in ERT.
 - Specify to automatically run the workflow after the initial ensemble is created,
   but before the first update by using the HOOK_WORKFLOW keyword
   with the option PRE_FIRST_UPDATE.
"""

EXAMPLES = """
Example configuration
-------------------------

The configuration file is a YAML format file where pairs of groups of observations
and groups of model parameters are specified.

Per default, all correlations between the
observations from the observation group and model parameters from the model
parameter group are active and unmodified. All other combinations of pairs of
observations and model parameters not specified in a correlation group, are inactive
or set to 0. But it is possible to specify many correlation groups. If a pair of
observation and model parameter appear multiple times
(e.g. because they are member of multiple correlation groups),
an error message is raised.

It is also possible to scale down correlations that are specified for 3D and 2D fields.

In the example below, four correlation groups are defined.
The first correlation group is called ``CORR1`` (a user defined name),
and defines all observations to have active correlation with all model
parameters starting with ``aps_valysar_grf`` and with ``GEO:PARAM``.
The keyword **field_scale** defines a scaling of the correlations between the
observations in the group and the model parameters selected of type
``FIELD`` in the ERT configuration file.

The second correlation group (with name ``CORR2`` ) activates correlations
between observations matching the wildcard specification
["OP_2_WWCT*", "OP_5_*"] and all parameters except those starting
with ``aps_``. ::


  log_level:3
  write_scaling_factors: True
  correlations:
    - name: CORR1
       obs_group:
          add: ["*"]
       param_group:
          add: ["aps_valysar_grf*","GEO:PARAM*"]
       field_scale:
          method: gaussian_decay
          main_range: 1700
          perp_range: 850
          azimuth: 310
          ref_point: [463400, 5932915]

    - name: CORR2
       obs_group:
          add: ["OP_2_WWCT*", "OP_5_*"]
       param_group:
          add: ["*"]
          remove: ["aps_*"]
       surface_scale:
          method: exponential_decay
          main_range: 800
          perp_range: 350
          azimuth: 120
          ref_point: [463000, 5932850]
          surface_file: "../../rms/output/hum/TopVolantis.irap"


   - name: CORR3
       obs_group:
          add: ["*"]
       param_group:
          add: ["aps_volon_grf*"]
       field_scale:
          method: from_file
          filename: "scaling_aps_volon_grf.grdecl"
          param_name: "SCALING"

   - name: CORR4
       obs_group:
          add: ["*"]
       param_group:
          add: ["aps_therys_grf*"]
       field_scale:
          method: segment
          segment_filename: "region.grdecl"
          param_name: "REGION"
          active_segments: [ 1,2,4]
          scalingfactors: [1.0, 0.5, 0.3]


Keywords
-----------
:log_level:
      Optional. Defines how much information to write to the log file.
      Possible values: integer value from 0 to 4
      Default is 0 corresponding to minimum info output to the log file.

:write_scaling_factors:
      Optional.
      Default is not to write calculated scaling factor files.
      Possible values:  ``True`` or ``False``.
      Define whether output file with calculated scaling factors is to be
      created or not. The purpose is to QC the calculated scaling factors
      and make it possible to visualise them. Is only relevant when using
      **field_scale** with methods calculating the scaling factors.

:correlations:
      List of specifications of correlation groups. A correlation group
      specify a set of observations and a set of model parameters.
      The correlation between pairs of observations and model parameters
      from these groups is set active, but some of the pairs like correlation
      between a field parameter value and an observation may be scaled by a
      factor, but the default if no scaling is specified, is to keep the correlation
      unchanged.

:name:
      Name of correlation group. Sub keyword under a correlation group.

:obs_group:
      Sub keyword under a correlation group.
      Defines  a group of observations using the sub keywords **add**
      and **remove**.

:param_group:
      Sub keyword under a correlation group.
      Defines a group of  model parameters using sub keywords **add**
      and **remove**.

:field_scale:
      Optional.
      Sub keyword under a correlation group.
      Defines how correlations between *field* parameters and observations
      in the observation group are modified.
      Default (when this keyword is not used) is to keep the correlations between
      the observations  and model parameters of type *field* unchanged for
      the correlation group.

      For distance based localisation, this keyword is used. Typically, the correlations
      are reduced by distance from the observations to field parameter value.
      A reference point is specified in separate keyword
      and should usually be located close to the observations in the observation group
      when using scaling of correlations between field parameters and observations.
      Sub keywords: **method**. Depending on which method is chosen,
      additional keywords must be specified.

:surface_scale:
      Optional.
      Sub keyword under a correlation group.
      Defines how correlations between *surface* parameters and observations
      in the observation group are modified.
      Default (when this keyword is not used) is to keep the correlations between
      the observations  and model parameters of type *surface* unchanged for
      the correlation group.

      Similar to fields, surface parameters are also field parameters, but in 2D.
      Scaling of this is also done in a similar way as for 3D field parameters.
      Sub keywords: **method** and **surface_file**. Depending on which
      method is chosen, additional keywords must be specified.

:add:
      Sub keyword under **obs_group** and **param_group**. Both **add**
      and **remove** keywords are followed by a list of observations or
      parameter names. Wildcard notation can be specified, and all observations
      or parameters specified in the ERT config file which matches the wildcard
      expansion,  are included in the list.


      The keyword **add** will add new observations or parameters to the list of
      selected observations or parameters while the keyword **remove** will remove
      the specified observations or parameter from the selection. The **add** keyword
      is required while the **remove** keyword is optional.

      The specification of parameters in the list is of the form
      *node_name:parameter_name* where *node_name* is an ERT identifier
      and *parameter_name* is the name of a parameter belonging to the ERT node.


      For instance if the ``GEN_KW`` ERT keyword is used, the ERT identifier is
      the node name while the parameter names used in the distribution file, contains
      names of the parameters for that node.

      For ERT node of type ``GEN_PARAM`` the parameter names are only referred to
      by indices and not names. So in this case the parameter index is specified instead
      such that a parameter in a GEN_PARAM node is referred to
      by *node_name:index*.

      For ERT nodes defined by the ERT keywords  ``FIELD`` or ``SURFACE``,
      only the nodename is specified like ``aps_Valysar_grf1``.
      The nodename represents all field values for all grid cells in the whole
      3D or 2D grid the field belongs to.

:remove:
      For details see the keyword **add:**. The main purpose of **remove** is to
      have a quick and easy way to specify all parameters or observations
      except a few one by combining **add** and **remove**.


:method:
      Sub keyword under **field_scale** and **surface_scale**. Is required if
      **field_scale** or **surface_scale** is used.
      Define a method for calculating the scaling factor. The available methods
      depends on whether **method** is a sub keyword of the **field_scale**
      or **surface_scale** keyword.

      For **field_scale** the available methods are **gaussian_decay**,
      **exponential_decay**, **from_file** and **segment**.
      For **surface_scale** the available methods are **gaussian_decay** and
      **exponential_decay**.

:exponential_decay:
      Name of a method or scaling function of the form *exp(-3d/R)* where *d* is
      distance from reference point to location of a field value, and *R* is the
      range function, an ellipse with half-axes equal to **main_range** and
      **perp_range**.
      Requires specification of keywords **main_range**, **perp_range**,
      **azimuth** and **ref_point**.

:gaussian_decay:
      Scaling function of the form *exp(-3(d/R)^2)*.
      For more details see **exponential_decay** above.

:main_range:
      Sub keyword under **field_scale** or **surface_scale**. Is only used for
      method **exponential_decay** and **gaussian_decay**.
      It defines the distance where the scaling values are reduced to approximately
      0.05 and is measured in the **azimuth** direction.

:perp_range:
      Sub keyword under **field_scale** or **surface_scale**. Is only used for
      method  **exponential_decay** and **gaussian_decay**.
      It defines the distance where the scaling values are reduced to approximately
      0.05 and is measured orthogonal to the **azimuth** direction.

:azimuth:
      Sub keyword under **field_scale** or **surface_scale**. Is only used for
      method **exponential_decay** and **gaussian_decay**.
      It defines the azimuth direction for main anisotropy direction
      for the decay function for scaling factor.

:ref_point:
      Sub keyword under  **field_scale**  or **surface_scale**. Is only used for
      method **exponential_decay** and **gaussian_decay**.
      It defines the (x,y) position the used by the scaling functions when calculating
      distance to a grid cell with a field parameter value. A grid cell located at the
      reference point will have distance 0 which means that the scaling function is
      1.0 for correlations between observations and the field parameter in that
      location.

:surface_file:
      Sub keyword under **surface_scale**. Is required and specify filename for
      a surface file. Is used to find the size (number of grid cells) of the
      surface parameters.

:from_file:
      Scaling function defined externally and read from file. Requires keywords
      **filename** and **param_name** containing the file name and the name
      of the parameter in the GRDECL file to be used.

:segment:
      Scaling function method available for FIELDS, and is specified for methods
      under **field_scale**.
      Requires the following keywords: **segment_file**, **param_name**,
      **active_segments** and **scalingfactors**, all as sub keywords
      under **field_scale**. The segment file must contain integer values
      for segment numbers for each grid cell value for the field. The file format
      is GRDECL text format.
      The parameter name is the parameter to read from the supplied file
      for keyword **segment_file**.

:active_segments:
      Sub keyword under **field_scale**. Is only used if method is ``segment``.
      A list of integer numbers for the segments to use to define active field
      parameter values.

:scalingfactors:
      Sub keyword under **field_scale**. Is only used if method is ``segment``.
      A list of float values between 0 and 1 is specified. The values are
      scaling factors to be used in the active segments specified.
      The list in **active_segments** and **scalingfactors** must of same
      length and the first value in the **scalingfactors** list corresponds to
      the first segment number in the **active_segments** list and so on.


"""


@hook_implementation
def legacy_ertscript_workflow(config):
    workflow = config.add_workflow(LocalisationConfigJob, "LOCALISATION_JOB")
    workflow.description = DESCRIPTION
    workflow.examples = EXAMPLES
    workflow.category = "observations.correlation"
