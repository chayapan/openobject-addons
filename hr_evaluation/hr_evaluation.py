# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from mx import DateTime as dt

from osv import fields, osv
import tools
from tools.translate import _

class hr_evaluation_plan(osv.osv):
    _name = "hr_evaluation.plan"
    _description = "Evaluation Plan"
    _columns = {
        'name': fields.char("Evaluation Plan", size=64, required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'phase_ids': fields.one2many('hr_evaluation.plan.phase', 'plan_id', 'Evaluation Phases'),
        'month_first': fields.integer('First Evaluation After'),
        'month_next': fields.integer('Next Evaluation After'),
        'active': fields.boolean('Active')
    }
    _defaults = {
        'active' : lambda *a: True,
    }
hr_evaluation_plan()

class hr_evaluation_plan_phase(osv.osv):
    _name = "hr_evaluation.plan.phase"
    _description = "Evaluation Plan Phase"
    _order = "sequence"
    _columns = {
        'name': fields.char("Phase", size=64, required=True),
        'sequence': fields.integer("Sequence"),
        'company_id': fields.related('plan_id','company_id',type='many2one',relation='res.company',string='Company',store=True),
        'plan_id': fields.many2one('hr_evaluation.plan','Evaluation Plan', required=True, ondelete='cascade'),
        'action': fields.selection([
            ('top-down','Top-Down Appraisal Requests'),
            ('bottom-up','Bottom-Up Appraisal Requests'),
            ('self','Self Appraisal Requests'),
            ('final','Final Interview')], 'Action', required=True),
        'survey_id': fields.many2one('survey','Appraisal Form',required=True),
        'send_answer_manager': fields.boolean('All Answers',
            help="Send all answers to the manager"),
        'send_answer_employee': fields.boolean('All Answers',
            help="Send all answers to the employee"),
        'send_anonymous_manager': fields.boolean('Anonymous Summary',
            help="Send an anonymous summary to the manager"),
        'send_anonymous_employee': fields.boolean('Anonymous Summary',
            help="Send an anonymous summary to the employee"),
        'wait': fields.boolean('Wait Previous Phases',
            help="Check this box if you want to wait that all preceeding phases " +
              "are finished before launching this phase."),
        'mail_feature': fields.boolean('Send mail for this phase',help="Check this box if you want to send mail to employees"+
                                       "coming under this phase"),
        'mail_body': fields.text('Email'),
        'email_subject':fields.text('char')
    }
    _defaults = {
        'sequence' : lambda *a: 1,
        'email_subject':_('''Regarding '''),
        'mail_body' : lambda *a:_('''
Date : %(date)s

Dear %(employee_name)s,

I am doing an evaluation regarding %(eval_name)s.

Kindly submit your response.


Thanks,
--
%(user_signature)s

        '''),
    }


hr_evaluation_plan_phase()

class hr_employee(osv.osv):
    _name = "hr.employee"
    _inherit="hr.employee"
    _columns = {
        'evaluation_plan_id': fields.many2one('hr_evaluation.plan', 'Evaluation Plan'),
        'evaluation_date': fields.date('Next Evaluation', help="Date of the next evaluation"),
    }

    def run_employee_evaluation(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        for id in self.browse(cr, uid, self.search(cr, uid, [],context=context),context=context):
            if id.evaluation_plan_id and id.evaluation_date:
                if (dt.ISO.ParseAny(id.evaluation_date) + dt.RelativeDateTime(months = int(id.evaluation_plan_id.month_next))).strftime('%Y-%m-%d') <= time.strftime("%Y-%m-%d"):
                    self.write(cr, uid, id.id, {'evaluation_date' : (dt.ISO.ParseAny(id.evaluation_date) + dt.RelativeDateTime(months =+ int(id.evaluation_plan_id.month_next))).strftime('%Y-%m-%d')},context=context)
                    self.pool.get("hr_evaluation.evaluation").create(cr, uid, {'employee_id' : id.id, 'plan_id': id.evaluation_plan_id},context)
        return True

    def onchange_evaluation_plan_id(self, cr, uid, ids, evaluation_plan_id, evaluation_date, context={}):
        evaluation_date = evaluation_date or False
        evaluation_plan_obj=self.pool.get('hr_evaluation.plan')
        if evaluation_plan_id:
            flag = False
            evaluation_plan =  evaluation_plan_obj.browse(cr, uid, [evaluation_plan_id],context=context)[0]
            if not evaluation_date:
               evaluation_date=(dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d'))+ dt.RelativeDateTime(months=+evaluation_plan.month_first)).strftime('%Y-%m-%d')
               flag = True
            else:
                if (dt.ISO.ParseAny(evaluation_date) + dt.RelativeDateTime(months = int(evaluation_plan.month_next))).strftime('%Y-%m-%d') <= time.strftime("%Y-%m-%d"):
                    evaluation_date=(dt.ISO.ParseAny(evaluation_date)+ dt.RelativeDateTime(months=+evaluation_plan.month_next)).strftime('%Y-%m-%d')
                    flag = True
            if ids and flag:
                self.pool.get("hr_evaluation.evaluation").create(cr, uid, {'employee_id' : ids[0], 'plan_id': evaluation_plan_id},context=context)
        return {'value': {'evaluation_date':evaluation_date}}

    def create(self, cr, uid, vals, context={}):
        id = super(hr_employee, self).create(cr, uid, vals, context=context)
        if vals.get('evaluation_plan_id', False):
            self.pool.get("hr_evaluation.evaluation").create(cr, uid, {'employee_id' : id, 'plan_id': vals['evaluation_plan_id']},context=context)
        return id

hr_employee()

class hr_evaluation(osv.osv):
    _name = "hr_evaluation.evaluation"
    _description = "Employee Evaluation"
    _rec_name = 'employee_id'
    _columns = {
        'date': fields.date("Evaluation Deadline", required=True),
        'employee_id': fields.many2one('hr.employee', "Employee", required=True),
        'note_summary': fields.text('Evaluation Summary'),
        'note_action': fields.text('Action Plan',
            help="If the evaluation does not meet the expectations, you can propose"+
              "an action plan"),
        'rating': fields.selection([
            ('0','Significantly bellow expectations'),
            ('1','Did not meet expectations'),
            ('2','Meet expectations'),
            ('3','Exceeds expectations'),
            ('4','Significantly exceeds expectations'),
        ], "Overall Rating", help="This is the overall rating on that summarize the evaluation"),
        'survey_request_ids': fields.one2many('hr.evaluation.interview','evaluation_id','Appraisal Forms'),
        'plan_id': fields.many2one('hr_evaluation.plan', 'Plan', required=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('wait','Plan In Progress'),
            ('progress','Final Validation'),
            ('done','Done'),
            ('cancel','Cancelled'),
        ], 'State', required=True,readonly=True),
        'date_close': fields.date('Ending Date'),
        'progress' : fields.float("Progress"),
    }
    _defaults = {
        'date' : lambda *a: (dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d')) + dt.RelativeDateTime(months =+ 1)).strftime('%Y-%m-%d'),
        'state' : lambda *a: 'draft',
    }

    def onchange_employee_id(self,cr,uid,ids,employee_id,context={}):
        employee_obj=self.pool.get('hr.employee')
        evaluation_plan_id=''
        if employee_id:
            for employee in employee_obj.browse(cr,uid,[employee_id],context=context):
                if employee and employee.evaluation_plan_id and employee.evaluation_plan_id.id:
                    evaluation_plan_id=employee.evaluation_plan_id.id
                employee_ids=employee_obj.search(cr,uid,[('parent_id','=',employee.id)],context=context)
        return {'value': {'plan_id':evaluation_plan_id}}

    def button_plan_in_progress(self,cr, uid, ids, context={}):
        user_obj = self.pool.get('res.users')
        employee_obj = self.pool.get('hr.employee')
        hr_eval_inter_obj = self.pool.get('hr.evaluation.interview')
        survey_request_obj = self.pool.get('survey.request')
        hr_eval_plan_obj = self.pool.get('hr_evaluation.plan.phase')
        curr_employee=self.browse(cr,uid, ids, context=context)[0].employee_id
        child_employees=employee_obj.browse(cr,uid, employee_obj.search(cr,uid,[('parent_id','=',curr_employee.id)],context=context))
        manager_employee=curr_employee.parent_id
        for evaluation in self.browse(cr,uid,ids):
            if evaluation and evaluation.plan_id:
                apprai_id = []
                for phase in evaluation.plan_id.phase_ids:
                    if phase.action == "bottom-up":
                        for child in child_employees:
                            user = False
                            if child.user_id:
                                user = child.user_id.id
                            id = hr_eval_inter_obj.create(cr, uid, {'evaluation_id':evaluation.id ,'user_id' : user,'survey_id' : phase.survey_id.id, 'user_to_review_id' : child.id, 'date_deadline' :(dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d')) + dt.RelativeDateTime(months =+ 1)).strftime('%Y-%m-%d')},context=context)
                            if not phase.wait:
                                hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [id], context=context)
                            if phase.mail_feature:
                                src = tools.config.options['email_from']
                                user_obj_id = user_obj.browse(cr,uid,uid)
                                val = {
                                        'employee_name':child.name,
                                        'user_signature':curr_employee.name,
#                                        'company_name':user_obj_id.company_id.name,
                                        'eval_name':phase.survey_id.title,
                                        'date':time.strftime('%Y-%m-%d'),
                                      }
                                mailbody = hr_eval_plan_obj.read(cr,uid,phase.id,['mail_body','email_subject'],context=context)
                                body = mailbody['mail_body']%val
                                sub = mailbody['email_subject']+phase.survey_id.title
                                dest=[child.work_email]
                                if dest:
                                   tools.email_send(src,dest,sub,body)
                            apprai_id.append(id)

                    elif phase.action == "top-down":
                        if manager_employee:
                            user = False
                            if manager_employee.user_id:
                                user = manager_employee.user_id.id
                            id = hr_eval_inter_obj.create(cr, uid, {'evaluation_id':evaluation.id,'user_id': user ,'survey_id' : phase.survey_id.id, 'user_to_review_id' :manager_employee.id, 'date_deadline' :(dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d')) + dt.RelativeDateTime(months =+ 1)).strftime('%Y-%m-%d')},context=context)
                            if not phase.wait:
                                hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [id], context=context)
                            if phase.mail_feature:
                                val.update({'employee_name':manager_employee.name})
                                mailbody = hr_eval_plan_obj.read(cr,uid,phase.id,['mail_body'],context=context)
                                body = mailbody['mail_body']%val
                                dest = [manager_employee.work_email]
                                if dest:
                                        tools.email_send(src,dest,sub,body)
                            apprai_id.append(id)
                    elif phase.action == "self":
                        if curr_employee:
                            user = False
                            if curr_employee.user_id:
                                user = curr_employee.user_id.id
                            id = hr_eval_inter_obj.create(cr, uid, {'evaluation_id':evaluation.id,'user_id' : user, 'survey_id' : phase.survey_id.id, 'user_to_review_id' :curr_employee.id, 'date_deadline' :(dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d')) + dt.RelativeDateTime(months =+ 1)).strftime('%Y-%m-%d')},context=context)
                            if not phase.wait:
                                hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [id], context=context)
                            apprai_id.append(id)
                    elif phase.action == "final":
                        if manager_employee:
                            user = False
                            if manager_employee.user_id:
                                user = manager_employee.user_id.id
                            id = hr_eval_inter_obj.create(cr, uid, {'evaluation_id':evaluation.id,'user_id' : user, 'survey_id' : phase.survey_id.id, 'user_to_review_id' :manager_employee.id, 'date_deadline' :(dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d')) + dt.RelativeDateTime(months =+ 1)).strftime('%Y-%m-%d')},context=context)
                            if not phase.wait:
                                hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [id], context=context)
                            apprai_id.append(id)
                self.write(cr, uid, evaluation.id, {'survey_request_ids':[[6, 0, apprai_id]]})
        self.write(cr,uid,ids,{'state':'wait'},context=context)
        return True

    def button_final_validation(self,cr, uid, ids, context={}):
        self.write(cr,uid,ids,{'state':'progress'})
        request_obj = self.pool.get('hr.evaluation.interview')
        for id in self.browse(cr, uid ,ids,context=context):
            if len(id.survey_request_ids) != len(request_obj.search(cr, uid, [('evaluation_id', '=', id.id),('state', '=', 'done')],context=context)):
                raise osv.except_osv(_('Warning !'),_("You cannot change state, because some appraisal in waiting answer or draft state"))
        return True

    def button_done(self,cr, uid, ids, context={}):
        self.write(cr,uid,ids,{'state':'done', 'date_close': time.strftime('%Y-%m-%d')}, context=context)
        return True

    def button_cancel(self,cr, uid, ids, context={}):
        self.write(cr,uid,ids,{'state':'cancel'}, context=context)
        return True

hr_evaluation()

class survey_request(osv.osv):
    _inherit="survey.request"
    _columns = {
        'is_evaluation':fields.boolean('Is Evaluation?'),
    }

survey_request()

class hr_evaluation_interview(osv.osv):
    _name='hr.evaluation.interview'
    _inherits={'survey.request':'request_id'}
    _description='Evaluation Interview'
    _columns = {
        'request_id': fields.many2one('survey.request','Request_id', ondelete='cascade'),
        'user_to_review_id': fields.many2one('hr.employee', 'Employee'),
        'evaluation_id' : fields.many2one('hr_evaluation.evaluation', 'Evaluation'),
        }
    _defaults = {
        'is_evaluation': lambda *a: True,
        }

    def survey_req_waiting_answer(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, { 'state' : 'waiting_answer'})
#        for id in self.browse(cr, uid, ids):
#            print"id",id
#            if id.user_to_review_id and id.user_to_review_id.work_email:
#                msg = " Hello %s, \n\n We are inviting you for %s survey. \n\n Thanks,"  %(id.user_to_review_id.name, id.survey_id.title)
#                tools.email_send(tools.config['email_from'], [id.user_to_review_id.work_email],\
#                                              'Invite to fill up Survey', msg)
        return True

    def survey_req_done(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, { 'state' : 'done'})
        hr_eval_obj = self.pool.get('hr_evaluation.evaluation')
        for id in self.browse(cr, uid, ids,context=context):
            flag = False
            wating_id = 0
            tot_done_req = 0
            records = self.pool.get("hr_evaluation.evaluation").browse(cr, uid, [id.evaluation_id.id],context=context)[0].survey_request_ids
            for child in records:
                if child.state == "draft" :
                    wating_id = child.id
                    continue
                if child.state != "done":
                    flag = True
                else :
                    tot_done_req += 1
            if not flag and wating_id:
                self.survey_req_waiting_answer(cr, uid, [wating_id], context)
            hr_eval_obj.write(cr, uid, [id.evaluation_id.id], {'progress' :tot_done_req * 100 / len(records)}, context=context)

        return True
    def survey_req_draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, { 'state' : 'draft'}, context=context)
        return True

    def survey_req_cancel(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, { 'state' : 'cancel'}, context=context)
        return True

hr_evaluation_interview()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:1
