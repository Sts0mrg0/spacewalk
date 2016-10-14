/**
 * Copyright (c) 2009--2013 Red Hat, Inc.
 *
 * This software is licensed to you under the GNU General Public License,
 * version 2 (GPLv2). There is NO WARRANTY for this software, express or
 * implied, including the implied warranties of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
 * along with this software; if not, see
 * http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
 *
 * Red Hat trademarks are not licensed under GPLv2. No permission is
 * granted to use or replicate Red Hat trademarks that are incorporated
 * in this software or its documentation.
 */
package com.redhat.rhn.frontend.action.systems;

import com.redhat.rhn.common.db.datasource.DataResult;
import com.redhat.rhn.domain.rhnset.RhnSet;
import com.redhat.rhn.domain.user.User;
import com.redhat.rhn.frontend.dto.SystemOverview;
import com.redhat.rhn.frontend.dto.VirtualSystemOverview;
import com.redhat.rhn.frontend.listview.PageControl;
import com.redhat.rhn.frontend.struts.RequestContext;
import com.redhat.rhn.frontend.struts.RhnAction;
import com.redhat.rhn.frontend.struts.RhnHelper;
import com.redhat.rhn.frontend.taglibs.list.ListTagHelper;
import com.redhat.rhn.frontend.taglibs.list.TagHelper;
import com.redhat.rhn.frontend.taglibs.list.helper.ListRhnSetHelper;
import com.redhat.rhn.frontend.taglibs.list.helper.Listable;
import com.redhat.rhn.manager.rhnset.RhnSetDecl;
import com.redhat.rhn.manager.system.SystemManager;

import org.apache.log4j.Logger;
import org.apache.struts.action.ActionForm;
import org.apache.struts.action.ActionForward;
import org.apache.struts.action.ActionMapping;

import java.util.Iterator;
import java.util.List;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 * VirtualSystemsListSetupAction
 * @version $Rev$
 */
public class VirtualSystemSetupAction extends RhnAction
        implements Listable<SystemOverview> {

    private static final Logger LOG = Logger.getLogger(VirtualSystemSetupAction.class);

    /** {@inheritDoc} */
    @Override
    public ActionForward execute(ActionMapping mapping,
            ActionForm formIn,
            HttpServletRequest request,
            HttpServletResponse response) {

        RequestContext requestContext = new RequestContext(request);

        User user = requestContext.getCurrentUser();
        DataResult<VirtualSystemOverview> result = getDataResult(user, null, formIn);

        for (VirtualSystemOverview vso : result) {
            LOG.error("RESULT: " + vso.getName() + "   " + vso.getId() + "  " +
                    vso.getServerName());
        }
        if (result.isEmpty()) {
            request.setAttribute(BaseSystemsAction.SHOW_NO_SYSTEMS, Boolean.TRUE);
        }

        RhnSet set =  RhnSetDecl.SYSTEMS.get(user);


        ListRhnSetHelper helper =
                new ListRhnSetHelper(this, request, RhnSetDecl.SYSTEMS);
        helper.execute();

        if (!set.isEmpty()) {
            //helper.syncSelections(set, result);
            ListTagHelper.setSelectedAmount("systemList", set.size(), request);
        }


        ListTagHelper.bindSetDeclTo("systemList", RhnSetDecl.SYSTEMS, request);

        request.setAttribute(RequestContext.PAGE_LIST, result);
        request.setAttribute(ListTagHelper.PARENT_URL, request.getRequestURI());

        TagHelper.bindElaboratorTo("systemList", result.getElaborator(), request);

        return mapping.findForward(RhnHelper.DEFAULT_FORWARD);
    }

    /**
     * Sets the status and entitlementLevel variables of each System Overview
     * @param dr The list of System Overviews
     * @param user The user viewing the System List
     */
    public void setStatusDisplay(DataResult dr, User user) {
        Iterator i = dr.iterator();

        while (i.hasNext()) {

            VirtualSystemOverview next = (VirtualSystemOverview) i.next();

            // If the system is not registered with RHN, we cannot show a status
            if (next.getSystemId() != null) {
                Long instanceId = next.getId();
                next.setId(next.getSystemId());
                SystemListHelper.setSystemStatusDisplay(user, next);
                next.setId(instanceId);
            }
        }
    }

    protected DataResult<VirtualSystemOverview> getDataResult(User user, PageControl pc,
            ActionForm formIn) {
        DataResult<VirtualSystemOverview> dr = SystemManager.virtualSystemsList(user, pc);

        for (int i = 0; i < dr.size(); i++) {
            VirtualSystemOverview current = (VirtualSystemOverview) dr.get(i);
            if (current.isFakeNode()) {
                continue;
            }
            else if (current.getUuid() == null && current.getHostSystemId() != null) {
                current.setSystemId(current.getHostSystemId());
            }
            else {
                current.setSystemId(current.getVirtualSystemId());
            }
        }

        return dr;
    }

    @Override
    public List getResult(RequestContext context) {
        User user = context.getCurrentUser();
        DataResult<VirtualSystemOverview> dr = SystemManager.virtualSystemsList(user, null);

        for (VirtualSystemOverview current : dr) {
            if (current.isFakeNode()) {
                continue;
            }
            else if (current.getUuid() == null && current.getHostSystemId() != null) {
                current.setSystemId(current.getHostSystemId());
            }
            else {
                current.setSystemId(current.getVirtualSystemId());
            }
        }

        return dr;
    }

}
