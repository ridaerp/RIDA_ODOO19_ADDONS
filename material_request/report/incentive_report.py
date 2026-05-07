from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import UserError


class OreIncentiveArchive(models.Model):
    _name = 'ore.incentive.archive'

    name=fields.Char("Ref")
    partner_id=fields.Many2one("res.partner","Rock Supplier")
    incentive_category_id=fields.Many2one("incentive.category","Incentive Category")
    incentive_classes_id=fields.Many2one("incentive.classes","Incentive Class")
    support=fields.Float("Support%")
    date=fields.Date('Date')
    ton=fields.Float("Ton")
    grade=fields.Float("Average Grade")

class PurchaseAnalysis(models.Model):
    _name = 'purchase.analysis'
    _description = 'Purchase Analysis'

    supplier_id = fields.Many2one('res.partner', string='Supplier')
    num_purchase_orders = fields.Integer(string='Number of Purchase Orders')



class OreIncentiveReport(models.TransientModel):
    _name = 'ore.incentive.report'

    date_from= fields.Date('Date From',default=fields.Date.today())
    date_to = fields.Date('Date To',default=fields.Date.today())
    # rock_vendor = fields.Many2one("res.partner", "Rock Vendor")
    # area_id = fields.Many2one("x_area", "Area")



    def generate(self):


        domain = [('ore_purchased', '=', True)]
        domain += [('create_date', '>=', self.date_from), ('create_date', '<=', self.date_to),('state','=','purchase')]

        incentive_categ_obg=self.env['incentive.category'].search([])
        incentive_class_obg=self.env['incentive.classes'].search([])
        ore_purchases = self.env['purchase.order'].search(domain)

        grade=0.0
        support=0.0
        incentive_records=None

        incentive_record = self.env['ore.incentive.archive']
        if ore_purchases:



            average=0.0


            supplier_ids = self.env['res.partner'].search([])
            purchase_order_data = []
            ton_sum_data = []
            for line in ore_purchases:


                average=line.weight_request_id.average
                quantity=line.weight_request_id.quantity
                supplier=line.partner_id.id



                ############second soultion ##########################################
                # supplier_grade_total={}


                # if  line.partner_id.id not in ton_sum_data :
                #     ton_sum_data.append([line.partner_id.id,quantity,average])

                # # print ("#######################",ton_sum_data)
                # customer_grade=0.0
                # for row in ton_sum_data:
                #     key=row[0]
                #     value=row[1]
                #     avg=row[2]
                #     customer_grade+=avg
                       
                #     if key in supplier_grade_total:
                #         supplier_grade_total[key]+=value
                #     else:
                #         supplier_grade_total[key]=value

                #     # for key, value in supplier_grade_total.items():
                

                #     # print ("#######################",supplier_grade_total)


                #     print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@",key,customer_grade)



                ############################# first solution##############################
                for cat in incentive_categ_obg:
                    flag=False
                    ton=0.0
                    if average >=cat.min_grade and  average<=cat.max_grade  or cat.min_grade == cat.max_grade and average >=cat.min_grade:
                        # print ("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@",average)
                        supplier_grade={}


                        if  line.partner_id.id not in purchase_order_data :
                            purchase_order_data.append([line.partner_id.id,cat.id,quantity])

                        print ("#######################",purchase_order_data)

                        for row in purchase_order_data:
                            # key=d[0]
                            supplier=row[0]
                            category=row[1]
                            qty=row[2]
                            key=(supplier,category)

                            if key in supplier_grade:
                                supplier_grade[key]+=qty
                            else:
                                supplier_grade[key]=qty
                       
                        for (customer_id, category), qty in supplier_grade.items():
                            print ("#######################",customer_id,qty,category)

    
                            for rec in incentive_class_obg:

                                categ=rec.incentive_category_id

                                if category ==categ.id :

                                    if (qty >=rec.min_ton and qty <=rec.max_ton) or rec.min_ton == rec.max_ton and qty >=rec.max_ton:
                                    # if average >=categ.min_grade and  average<=categ.max_grade :
                                        support=0.0
                                        support=rec.support
                                        

                                        # Check if the record already exists
                                        existing_record = incentive_record.sudo().search([
                                            ('partner_id', '=', customer_id),
                                            # ('incentive_classes_id', '=', rec.id),
                                            ('incentive_category_id','=' ,categ.id),
                                            ('date','=',self.date_to),


                                        ])

                                        for recc in existing_record:
                                            if recc.partner_id.id==customer_id:
                                                recc.ton=qty
                                                recc.support=rec.support
                                                recc.incentive_classes_id=rec.id
       
                                        if not existing_record :

                                            # if categ.min_grade
                                            incentive_record.sudo().create({
                                                'ton': qty,
                                                'partner_id': customer_id,
                                                'date':self.date_to,
                                                'support': rec.support,
                                                # 'name':'Ref'+str(self.id),
                                                'incentive_category_id': categ.id,
                                                'incentive_classes_id': rec.id,
                                            })
                                        else:
                                            print(f"Record already exists for customer_id: {customer_id}, ton: {qty}, incentive_class_id: {rec.id}")
               
                #########################################end of soultion##################