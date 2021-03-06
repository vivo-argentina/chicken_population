# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
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

import openerp
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _
import datetime
from datetime import date , datetime
from dateutil.relativedelta import relativedelta


import logging
_logger = logging.getLogger(__name__)

AVAILABLE_EVENTS = [
        ('broken_egg','Huevos rotos'),
        ('food_charge','Carga de alimientos'),
        ('new_egg','Huevos recogidos'),
        ('other','Otros'),    
        ('chicken_disease','Enfermedad'),  
        ('chicken_dead','Muerte'),   
        ('temperature','Temperatura'),   
        ('temperature_max','Temperatura Maxima'),   
        ('temperature_min','Temperatura Minima'),   
        ('production','Postura'),   

    ]
UNCLASSIFIED_HEGG_ID=41

class chicken_population(osv.osv):
    _name = "chicken.population"
    _inherit = ['mail.thread']

    def _fnct_actual_food(self, cr, uid, ids, field_name, args, context=None):

        day_food=0.013

        if context is None:
            context = {}
        res = {}
        for chicken_population in self.browse(cr, uid, ids, context=context):
            if chicken_population.time_last_food_charge :

                start=datetime.strptime(chicken_population.time_last_food_charge,'%Y-%m-%d')
                end=datetime.today()
                diff =   end - start
                used = chicken_population.last_food_charge_qty -(diff.days * day_food * chicken_population.actual_population)
                
                res[chicken_population.id] = used
        return res



    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'description': fields.text('Description'),
        'startdate': fields.date('start date' , track_visibility='onchange'),
        'enddate': fields.date('end date', track_visibility='onchange'),
        'active': fields.boolean('Active', help="If the active field is set to False."),
        'start_population': fields.integer('Initial Population Quantity'),
        'actual_population': fields.integer('Population Quantity',track_visibility='onchange'),
        'time_last_food_charge': fields.date('Last Food charge time'),
        'last_food_charge_qty': fields.float('Last Food charge Kg'),
        'actual_food':  fields.function(_fnct_actual_food, string='Actual Food'),
        'location_id': fields.many2one('stock.location', 'Food Location', required=True, 
                        domain="[('usage', '=', 'internal')]"),

        #'events': fields.many2many('chicken.population.event'),
        'event_item': fields.many2many('chicken.population.event', 'chicken_population_event_item',
                                       'population_id', 'event_id', 'Events'),

        }
    _defaults = {
            'active': lambda self, cr, uid, context: True,

        }


class chicken_population_event(osv.osv):
    _name = "chicken.population.event"

    _columns = {
        'name': fields.char('Name',readonly=True, required=False, translate=True),
        'description': fields.text('Description'),
        'datetime': fields.datetime('event date'),
        'qty': fields.float('Quantity'),
        'total_qty': fields.float('Total Quantity'),
        'percent': fields.float('Percent',group_operator="avg"),
        'population_qty' : fields.integer('Population qty',group_operator="avg"),

        'active': fields.boolean('Active', help="If the active field is set to False."),
        'type': fields.selection(AVAILABLE_EVENTS, 'Event Type') ,
        'population': fields.many2many('chicken.population', 'chicken_population_event_item',
                                       'event_id','population_id',  'Events')   
 
        }

    _defaults = {
            'active': lambda self, cr, uid, context: True,

        }


    def create(self, cr, uid, vals, context=None):
        #vals['name'] = AVAILABLE_EVENTS[vals['type']] + ' '+ vals['datetime'] 
        
        
        return super(chicken_population_event, self).create(cr, uid, vals, context)


class chicken_population_event_wizard(osv.osv_memory):
        _name = 'chicken.population.event.wizard'

        _columns = {
                    'population_id': fields.many2one('chicken.population','Population',required=True,),
                    'datetime': fields.datetime('event date','Date'),
                    'new_egg' : fields.integer('New eggs'),
                    'food' : fields.integer('Food charge'),
                    'broken_egg' : fields.integer('Broken eggs'),
                    'chicken_dead' : fields.integer('Chicken dead'),
                    'description': fields.text('Description'),
                    'temperature_max' : fields.float('Temperature Max'),
                    'temperature_min' : fields.float('Temperature Min'),
                    'location_id': fields.many2one('stock.location', 'Location', required=True, 
                        domain="[('usage', '=', 'internal')]"),

                    'food_product': fields.many2one('product.template','product'),
                    'food_qty': fields.float('Quantity in kg'),
                    'food_stock_to_zero': fields.boolean('stock to zero'),


                    }
        _defaults= {
             'datetime' : fields.datetime.now
        }

        def do_set_event(self, cr, uid,ids,context=None):
            event_data=self.read(cr, uid, ids[0], ['population_id','datetime','new_egg','broken_egg',
                'chicken_dead','temperature_max','temperature_min','description','food_product','food_qty','food_stock_to_zero'])

            chicken_population=self.pool.get('chicken.population')
            chicken_population_event=self.pool.get('chicken.population.event')
            population=chicken_population.browse(cr,uid,event_data['population_id'][0],context=None)
  
            product_template=self.pool.get('product.template')
            unclassified_hegg=product_template.browse(cr,uid,UNCLASSIFIED_HEGG_ID,context=None)

            chicken_population_data={}
            events=[]
            actual_population=population['actual_population']
            total_eggs=event_data['broken_egg'] + event_data['new_egg']

            if(event_data['chicken_dead']):
                actual_population=population['actual_population']-event_data['chicken_dead']

                event={'name':'Muerte','qty':event_data['chicken_dead'],
                        'percent':event_data['chicken_dead']*100/population['start_population'],
                        'datetime':event_data['datetime'],'type':'chicken_dead','population_qty':actual_population,
                        'description':event_data['description']}
                #event_id=chicken_population_event.create(cr,uid,event,context=None)
                events.append((0,0,event))
                chicken_population_data['actual_population']=actual_population
  

            # Si huevos rotos agrego un evento y visualizo el procentual de rotura
            if(event_data['broken_egg']):
                event={'name':'Huevos Rotos','qty':event_data['broken_egg'],
                        'percent':event_data['broken_egg']*100/total_eggs,
                        'datetime':event_data['datetime'],'type':'broken_egg','population_qty':actual_population}
                #event_id=chicken_population_event.create(cr,uid,event,context=None)
                events.append((0,0,event))

            # Si  nuevos huevos  creo el evento new  hegg
            # y modifico el stock de UNCLASSIFIED_HEGG_ID
            # to-do: Deberia realizarlo con la funcion de ajuste de stock            

            if(event_data['new_egg']):
                event={'name':'Nuevos Huevos','qty':event_data['new_egg'],
                        'percent':event_data['new_egg']*100/actual_population,
                        'datetime':event_data['datetime'],'type':'new_egg','population_qty':actual_population}
                #event_id=chicken_population_event.create(cr,uid,event,context=None)
                events.append((0,0,event))
                
            if event_data['new_egg'] or event_data['broken_egg']:
                event={'name':'Postura','qty':total_eggs,
                        'percent':total_eggs*100/actual_population,
                        'datetime':event_data['datetime'],'type':'production','population_qty':actual_population}
                #event_id=chicken_population_event.create(cr,uid,event,context=None)
                events.append((0,0,event))


                qty_available=unclassified_hegg['qty_available']+ event_data['new_egg']
                nqty=self.change_product_qty( cr, uid, qty_available, context)

                #vals={}
                #vals['qty_available']=unclassified_hegg['qty_available']+ event_data['new_egg'];
                #product_template.write(cr, uid, [UNCLASSIFIED_HEGG_ID], vals, context=context)
            if(event_data['temperature_max']):
                event={'name':'Temperatura Maxima','qty':event_data['temperature_max'],
                        'datetime':event_data['datetime'],'type':'temperature_max','population_qty':actual_population}
                #event_id=chicken_population_event.create(cr,uid,event,context=None)
                events.append((0,0,event))

            if(event_data['temperature_min']):
                event={'name':'Temperatura Minima','qty':event_data['temperature_min'],
                        'datetime':event_data['datetime'],'type':'temperature_min','population_qty':actual_population}
                #event_id=chicken_population_event.create(cr,uid,event,context=None)
                events.append((0,0,event))
            
            if event_data['food_product'] :
                if event_data['food_stock_to_zero'] :
                    #seteo la nueva cantidad
                    last_food_charge_qty=event_data['food_qty']
                else :
                    #Agrego el aliment
                    last_food_charge_qty=population['actual_food']+event_data['food_qty']

                product_obj=self.pool.get('product.template')
                hegg_clasification=self.pool.get('hegg.clasification')
                
                food_product=product_obj.browse(cr, uid,event_data['food_product'][0])

                hegg_clasification.change_product_qty( cr, uid, last_food_charge_qty,food_product,population['location_id']['id'])




                for component in food_product['components_id']:

                    qty=hegg_clasification._convert_qty( cr, uid, component['qty']*event_data['food_qty'],component['uom_id'],component['product'])
                    
                    component_qty=component['product']['qty_available']-qty[0]
                    
                    hegg_clasification.change_product_qty( cr, uid, component_qty,component['product'],12)


                event={'name':'Carga de alimentos','qty':event_data['food_qty'],
                        'datetime':event_data['datetime'],'type':'food_charge'}
                events.append((0,0,event))
                
                #event_id=chicken_population_event.create(cr,uid,event,context=None)
                chicken_population_data['last_food_charge_qty']=last_food_charge_qty
                chicken_population_data['time_last_food_charge']=event_data['datetime']



            chicken_population_data['event_item']=events
            chicken_population.write(cr, uid, event_data['population_id'][0], chicken_population_data, context=context)



            return  True

        def change_product_qty(self, cr, uid, qty, context=None):
            """ Changes the Product Quantity by making a Physical Inventory.
            @param self: The object pointer.
            @param cr: A database cursor
            @param uid: ID of the user currently logged in
            @param ids: List of IDs selected
            @param context: A standard dictionary
            @return:
            """

            product_product=self.pool.get('product.product')
            hsc_ids=product_product.search(cr, uid, [('default_code', 'ilike','hsc')], context=None)
            #product_hsc=lines_obj.browse(cr, uid, hsc_ids[0], context=None)

            if context is None:
                context = {}

            inventory_obj = self.pool.get('stock.inventory')
            inventory_line_obj = self.pool.get('stock.inventory.line')

            inventory_id = inventory_obj.create(cr, uid, {
                'name': _('CH: x') ,
                'filter': 'product',
                'product_id': hsc_ids[0],
                'location_id': 12}, context=context)

            #product = data.product_id.with_context(location=1, lot_id= 1)
            #th_qty = product.qty_available
            
            line_data = {
                'inventory_id': inventory_id,
                'product_qty': qty,
                'location_id': 12,
                'product_id': hsc_ids[0],
                'product_uom_id': 1,
                'theoretical_qty': 0
            }
            
            inventory_line_obj.create(cr , uid, line_data, context=context)
            inventory_obj.action_done(cr, uid, [inventory_id], context=context)
            return {}


class hegg_clasification(osv.osv):
    _name = "hegg.clasification"
    #_inherit = ['mail.thread']

    _columns = {
        'name': fields.char('Name'),
        'date': fields.date('date' ),
        'active': fields.boolean('Active', help="If the active field is set to False."),
        'partner_id': fields.many2many('res.partner', 'hegg_clasification_parner',
                                       'partner_id', 'clasification_id', 'Clasificators'),

        'clasification_items': fields.many2many('hegg.clasification.lines', 'hegg_clasification_items',
                                       'clasification_id', 'line_id', 'Products'),
        'total_eggs': fields.integer('Total clasified Heggs'),
        'state': fields.selection((('draft', 'Draft'), ('done', 'done')), 'State'),
        }
    _defaults = {
            'active': lambda self, cr, uid, context: True,
            'date' : fields.datetime.now,
            'state': lambda self, cr, uid, context: 'draft',

        }

    def create(self, cr, uid, vals, context=None):
        vals['name'] = 'Clasificacion'+ vals['date'] 
        
        
        return super(hegg_clasification, self).create(cr, uid, vals, context)

    def hegg_do_clasification(self, cr, uid, ids, context=None):
        clasification=self.read(cr, uid, ids[0], ['clasification_items'])


        lines_obj=self.pool.get('hegg.clasification.lines')
        components_obj=self.pool.get('product.template.components')

        for item in clasification['clasification_items']:
            #Recorro los items que clasifico
            line=lines_obj.browse(cr, uid, item, context=None)
            #aumento la cantidad de productos selecionados 
            new_qty=line['product']['qty_available']+line['qty']
            self.change_product_qty( cr, uid, new_qty,line['product'],12)

            #redusco la cantidad de los otros
            for component in line['product']['components_id']:
                # 1 Obtengo el qty del procentual de qty en unidad de referencia
                # 2 Transformo ese qty en la unidad de el componente
                percent_in_qty=line['qty'] * (component['qty'] / 100) 
                qty=_convert_qty(cr, uid,percent_in_qty,line['product']['uom_id'],component['product'])
                # 3 reducco esto de el inventario del producto                
                component_qty=component['product']['qty_available']-qty[0]
                self.change_product_qty( cr, uid, component_qty,component['product'],12)

        vals={}
        vals['state']='done'
        #vals['total_eggs']=5 
        self.write(cr, uid, ids[0], vals, context=context)

    def _convert_qty_from_percent(self, cr, uid, qty, unit, product,percent, is_from_unit=True):
        import operator

        operator_function = is_from_unit and operator.truediv or operator.mul
        if unit != product['uom_id']:
            if unit['uom_type'] != 'reference':
                qty = operator_function(qty, unit['factor'])
                unit = unit['category_id']['reference_uom_ids'][0]

            if product['uom_id']['uom_type'] != 'bigger':
                qty = qty * product['uom_id']['factor'] 

            if product['uom_id']['uom_type'] != 'smaller':
                qty = qty / product['uom_id']['factor_inv'] 
                

            unit = product['uom_id']
        return qty, unit




        
    def _convert_qty(self, cr, uid, qty, unit, product, is_from_unit=True):
        import operator
        operator_function = is_from_unit and operator.truediv or operator.mul
        if unit != product['uom_id']:
            if unit['uom_type'] != 'reference':
                qty = operator_function(qty, unit['factor'])
                unit = unit['category_id']['reference_uom_ids'][0]

            if product['uom_id']['uom_type'] != 'bigger':
                qty = qty * product['uom_id']['factor'] 

            if product['uom_id']['uom_type'] != 'smaller':
                qty = qty / product['uom_id']['factor_inv'] 
                

            unit = product['uom_id']
        return qty, unit

            
    def change_product_qty(self, cr, uid, qty,product,location_id,context=None):
        product_product=self.pool.get('product.product')
        product_ids=product_product.search(cr, uid, [('product_tmpl_id', '=', product['id'])], context=None)

        if context is None:
            context = {}

        inventory_obj = self.pool.get('stock.inventory')
        inventory_line_obj = self.pool.get('stock.inventory.line')

        inventory_id = inventory_obj.create(cr, uid, {
            'name': _('cls: x') ,
            'filter': 'product',
            'product_id': product['id'],
            'location_id': location_id}, context=context)

        #product = data.product_id.with_context(location=1, lot_id= 1)
        #th_qty = product.qty_available
        
        line_data = {
            'inventory_id': inventory_id,
            'product_qty': qty,
            'location_id': location_id,               

            'product_id': product_ids[0],
            'product_uom_id': product['uom_id']['id'],
            'theoretical_qty': 0
        }
        
        inventory_line_obj.create(cr , uid, line_data, context=context)
        inventory_obj.action_done(cr, uid, [inventory_id], context=context)
        return {}
          

class hegg_clasification_lines(osv.osv):
    _name = "hegg.clasification.lines"
    #_inherit = ['mail.thread']

    _columns = {
        'product': fields.many2one('product.template','product'),
        'qty': fields.float('Quantity')

        }
    _defaults = {
            'active': lambda self, cr, uid, context: True,
        }
