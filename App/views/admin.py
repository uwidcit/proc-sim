from flask_admin.contrib.sqla import ModelView
import io
from functools import wraps
from flask_jwt_extended import jwt_required, current_user
from flask_admin import Admin as FlaskAdmin
from flask import flash, redirect, url_for, request, Blueprint, render_template, send_file, Response
from App.database import db
from App.models import User, Student, Group, StudentGroup, Lot, LotGroup, Bid, Evaluation, RFP
from App.controllers import *
from App.utils import format_timestamp

class AdminView(ModelView):
    @jwt_required()
    def is_accessible(self):
        return current_user is not None and current_user.is_admin()

    def inaccessible_callback(self, name, **kwargs):
        flash("Login as admin to access this page", "info")
        return redirect(url_for('index_views.index_page', next=request.url))

def setup_admin(app):
    # Flask-Admin 1.x uses template_mode; 2.x removed it
    try:
        admin = FlaskAdmin(app, name='FlaskMVC', template_mode='bootstrap3')
    except TypeError:
        admin = FlaskAdmin(app, name='FlaskMVC')
    admin.add_view(AdminView(User, db.session))

admin_views = Blueprint('admin_views', __name__, template_folder='../templates/admin')

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash("You are logged in as a student and therefore cannot access admin page", "failed")
            return redirect(url_for('index_views.index_page'))
        return f(*args, **kwargs)
    return decorated_function

# ─── Lot Routes ───────────────────────────────────────────────────────────────

@admin_views.route('/admin/lots', methods=['GET'])
@admin_required
def admin_manage_lots():
    year = get_current_year()
    lots = db.session.scalars(
        db.select(Lot).filter_by(academic_year=year).order_by(Lot.id)
    ).all()

    lab_types = get_all_lab_types()

    return render_template('admin/manage_lots.html', title='Manage Lots', lots=lots, lab_types=lab_types, active_page="lots")

@admin_views.route('/admin/lots/add', methods=['POST'])
@admin_required
def admin_add_lot():
    lab_type_id = request.form.get('lab_type_id')
    lab_type_name = None
    if lab_type_id:
        lab_type = get_lab_type(int(lab_type_id))
        lab_type_name = lab_type.name if lab_type else None

    lab_size = request.form.get('lab_size') or ""
    num_machines = request.form.get('num_machines') or 0
    budget = request.form.get('budget')

    create_lot(
        lab_type_name or request.form.get('lab_type'),
        lab_size,
        budget,
        labTypeId=int(lab_type_id) if lab_type_id else None,
        numMachines=num_machines,
    )

    return redirect(url_for('admin_views.admin_manage_lots'))

@admin_views.route('/admin/lots/<int:lot_id>/edit', methods=['POST'])
@admin_required
def admin_edit_lot(lot_id):
    lab_type_id = request.form.get('lab_type_id')
    lab_type_name = None
    if lab_type_id:
        lab_type = get_lab_type(int(lab_type_id))
        lab_type_name = lab_type.name if lab_type else None

    lab_size = request.form.get('lab_size')
    num_machines = request.form.get('num_machines')
    budget = request.form.get('budget')

    edit_lot(
        lot_id,
        lab_type_name or request.form.get('lab_type'),
        int(lab_type_id) if lab_type_id else None,
        lab_size,
        budget,
        numMachines=num_machines,
    )

    return redirect(url_for('admin_views.admin_manage_lots'))

@admin_views.route('/admin/lots/<int:lot_id>/remove', methods=['POST'])
@admin_required
def admin_remove_lot(lot_id):
    
    remove_lot(lot_id)

    flash(f"Lot {lot_id} removed successfully", "success")
    return redirect(url_for('admin_views.admin_manage_lots'))

@admin_views.route('/admin/lab-types', methods=['GET'])
@admin_required
def admin_manage_lab_types():
    lab_types = get_all_lab_types()
    return render_template('admin/manage_lab_types.html', title='Manage Lab Types', lab_types=lab_types, active_page='types')

@admin_views.route('/admin/lab-types/add', methods=['POST'])
@admin_required
def admin_add_lab_type():
    name = request.form.get('name')
    description = request.form.get('description')
    create_lab_type(name, description)
    flash('Lab type added successfully', 'success')
    return redirect(url_for('admin_views.admin_manage_lab_types'))

@admin_views.route('/admin/lab-types/<int:type_id>/edit', methods=['POST'])
@admin_required
def admin_edit_lab_type(type_id):
    name = request.form.get('name')
    description = request.form.get('description')
    edit_lab_type(type_id, name, description)
    flash('Lab type updated successfully', 'success')
    return redirect(url_for('admin_views.admin_manage_lab_types'))

@admin_views.route('/admin/lab-types/<int:type_id>/remove', methods=['POST'])
@admin_required
def admin_remove_lab_type(type_id):
    lab_type = get_lab_type(type_id)
    if lab_type:
        in_use = db.session.scalars(
            db.select(Lot).filter_by(labTypeId=type_id)
        ).first()
        if in_use:
            flash('Cannot remove a lab type that is assigned to lots', 'failed')
            return redirect(url_for('admin_views.admin_manage_lab_types'))

        remove_lab_type(type_id)
        flash('Lab type removed successfully', 'success')

    return redirect(url_for('admin_views.admin_manage_lab_types'))

# ─── Bid Routes ───────────────────────────────────────────────────────────────

@admin_views.route('/admin/manage-bids')
@admin_required
def admin_manage_bids():
    year = get_current_year()
    groups = db.session.scalars(
        db.select(Group)
        .filter_by(status="approved", academic_year=year)
    ).all()

    bids = []
    vendor_filters = []

    for group in groups:
        bid_objs = db.session.scalars(
            db.select(Bid).filter_by(sourceGroupID=group.id)
        ).all()
        if not bid_objs:
            continue

        vendor_filters.append({"id": group.id, "name": group.groupName, "count": len(bid_objs)})

        for bid_obj in bid_objs:
            to_group = get_group(bid_obj.recipientGroupID)
            to_lot = get_lot(bid_obj.lotID)
            bids.append({
                "id": bid_obj.id,
                "source_group_id": group.id,
                "source_group_name": group.groupName,
                "to_group_name": to_group.groupName if to_group else "—",
                "to_lot_id": to_lot.id if to_lot else None,
                "to_lot_label": display_lot_label(to_lot) if to_lot else "—",
                "to_lot_name": to_lot.labType if to_lot else "—",
                "timestamp": format_timestamp(bid_obj.timestamp),
                "filename": bid_obj.bidDocumentName,
                "quotation": bid_obj.quotationAmount,
                "message": bid_obj.message or "",
                "pdf_url": url_for(
                    'admin_views.admin_view_bid_document',
                    group_id=group.id,
                    bid_id=bid_obj.id,
                ),
            })

    return render_template(
        'admin/manage_bids.html',
        bids=bids,
        vendor_filters=vendor_filters,
        title='Manage Bids',
        active_page='bids',
    )

@admin_views.route('/admin/manage-bids/group/<int:group_id>')
@admin_required
def admin_view_group_bids(group_id):
    return redirect(url_for('admin_views.admin_manage_bids', vendor=group_id))

@admin_views.route('/admin/view-bid/<int:group_id>/<int:bid_id>')
@admin_required
def admin_view_bid_document(group_id, bid_id):
    bid = get_bid(bid_id)
    if not bid:
        flash("Bid not found", "failed")
        return redirect(url_for('admin_views.admin_manage_bids'))

    return send_file(
        io.BytesIO(bid.bidDocument),
        download_name=bid.bidDocumentName,
        mimetype='application/pdf'
    )

@admin_views.route('/admin/manage-bids/group/<int:group_id>/bid/<int:bid_id>/remove', methods=['POST'])
@admin_required
def admin_remove_bid(group_id, bid_id):
    remove_bid(bid_id)
    flash("Bid removed successfully", "success")
    return redirect(url_for('admin_views.admin_manage_bids', vendor=group_id))

# ─── Group Routes ─────────────────────────────────────────────────────────────

@admin_views.route('/admin/manage-groups')
@admin_required
def admin_manage_groups():

    GROUPS = []
    GROUP_REQUESTS = []
    year = get_current_year()

    groups = db.session.scalars(
        db.select(Group).filter_by(academic_year=year)
    ).all()

    group_name_by_student = {}

    for group in groups:
        dic = {}
        dic["id"] = group.id
        dic["name"] = group.groupName

        students = db.session.scalars(
            db.select(Student)
            .join(StudentGroup, Student.id == StudentGroup.studentID)
            .filter(StudentGroup.groupID == group.id)
            .order_by(Student.name)
        ).all()

        members = []
        for student in students:
            members.append({
                "db_id": student.id,
                "name": student.name,
                "id": student.username,
            })
            group_name_by_student[student.id] = group.groupName

        dic["members"] = members
        dic["member_ids"] = [m["db_id"] for m in members]
        dic["display_name"] = display_group_name(group)
        dic["status"] = group.status

        if group.status == "requested":
            dic["lots"] = []
            dic["lot_ids"] = []
            GROUP_REQUESTS.append(dic)
        else:
            entries = db.session.scalars(
                db.select(LotGroup)
                .filter_by(groupID=group.id)
            ).all()
            lot_rows = []
            for entry in entries:
                lot = get_lot(entry.lotID)
                lot_rows.append({
                    "id": entry.lotID,
                    "label": display_lot_label(lot) if lot else f"Lot {entry.lotID}",
                })
            dic["lots"] = lot_rows
            dic["lot_ids"] = [row["id"] for row in lot_rows]
            GROUPS.append(dic)

    LOTS = db.session.scalars(
        db.select(Lot)
        .outerjoin(LotGroup, LotGroup.lotID == Lot.id)
        .where(Lot.academic_year == year, LotGroup.lotID == None)
    ).all()

    year_students = db.session.scalars(
        db.select(Student)
        .filter_by(academic_year=year)
        .order_by(Student.name)
    ).all()

    student_rows = []
    ungrouped_count = 0
    unclaimed_count = 0
    for student in year_students:
        group_name = group_name_by_student.get(student.id)
        if not group_name:
            ungrouped_count += 1
        if not student.account_claimed:
            unclaimed_count += 1
        membership = check_studentGroup(student.id, academic_year=year)
        student_rows.append({
            "id": student.id,
            "name": student.name,
            "student_id": student.username,
            "email": student.email or "",
            "claimed": bool(student.account_claimed),
            "group": group_name,
            "group_id": membership.groupID if membership else None,
        })

    all_groups_options = [
        {
            "id": g.id,
            "name": g.groupName,
            "display_name": display_group_name(g),
            "status": g.status,
        }
        for g in groups
    ]

    group_name_by_id = {g.id: g.groupName for g in groups}
    lot_owner = {
        e.lotID: e.groupID
        for e in db.session.scalars(
            db.select(LotGroup)
            .join(Lot, Lot.id == LotGroup.lotID)
            .filter(Lot.academic_year == year)
        ).all()
    }
    year_lots = []
    for lot in db.session.scalars(
        db.select(Lot).filter_by(academic_year=year).order_by(Lot.id)
    ).all():
        owner_id = lot_owner.get(lot.id)
        year_lots.append({
            "id": lot.id,
            "name": display_lot_label(lot),
            "group_id": owner_id,
            "group_name": group_name_by_id.get(owner_id) if owner_id else None,
        })

    return render_template('admin/manage_groups.html',
                         tab='requests',
                         title='Manage Groups',
                         group_requests=GROUP_REQUESTS,
                         groups=GROUPS,
                         all_groups=all_groups_options,
                         lots=LOTS,
                         year_lots=year_lots,
                         students=student_rows,
                         ungrouped_count=ungrouped_count,
                         unclaimed_count=unclaimed_count,
                         academic_year=year,
                         active_page='groups')


@admin_views.route('/admin/manage-groups/import-class-list', methods=['POST'])
@admin_required
def admin_import_class_list():
    file = request.files.get('csv_file')
    if not file or not file.filename:
        flash("Please upload a CSV file", "failed")
        return redirect(url_for('admin_views.admin_manage_groups'))

    count, errors = import_class_list_from_csv(file)
    if errors:
        for err in errors:
            flash(err, "failed")
        return redirect(url_for('admin_views.admin_manage_groups'))

    flash(
        f"Imported {count} ungrouped students. They can claim accounts with matching ID and email.",
        "success",
    )
    return redirect(url_for('admin_views.admin_manage_groups'))


@admin_views.route('/admin/manage-groups/groups/create', methods=['POST'])
@admin_required
def admin_create_group_route():
    year = get_current_year()
    member_ids = request.form.getlist('member_ids')
    approve = request.form.get('approve') == '1'
    group, err = admin_create_group(
        request.form.get('group_name'),
        member_ids=member_ids,
        approve=approve,
        academic_year=year,
    )
    if err and not group:
        flash(err, "failed")
    elif err and group:
        flash(err, "failed")
        flash(f"Created {group.groupName}", "success")
    else:
        flash(f"Created {group.groupName}", "success")
    return redirect(url_for('admin_views.admin_manage_groups'))


@admin_views.route('/admin/manage-groups/groups/<int:group_id>/edit', methods=['POST'])
@admin_required
def admin_edit_group_route(group_id):
    group = get_group(group_id)
    if not group or group.academic_year != get_current_year():
        flash("Group not found for this year", "failed")
        return redirect(url_for('admin_views.admin_manage_groups'))

    renamed, err = rename_group(group_id, request.form.get('group_name'))
    if err:
        flash(err, "failed")
        return redirect(url_for('admin_views.admin_manage_groups'))

    member_ids = request.form.getlist('member_ids')
    _, mem_err = set_group_members(group_id, member_ids)
    if mem_err:
        flash(mem_err, "failed")
        return redirect(url_for('admin_views.admin_manage_groups'))

    lot_ids = request.form.getlist('lot_ids')
    _, lot_err = set_group_lots(group_id, lot_ids)
    if lot_err:
        flash(lot_err, "failed")
    else:
        flash(f"Updated {renamed.groupName}", "success")
    return redirect(url_for('admin_views.admin_manage_groups'))


@admin_views.route('/admin/manage-groups/students/<int:student_id>/move', methods=['POST'])
@admin_required
def admin_move_student(student_id):
    year = get_current_year()
    raw = (request.form.get('group_id') or '').strip()
    group_id = None if raw in ('', '0', 'none') else int(raw)
    ok, err = move_student_to_group(student_id, group_id=group_id, academic_year=year)
    if not ok:
        flash(err or "Could not move student", "failed")
    elif group_id is None:
        flash("Student ungrouped", "success")
    else:
        group = get_group(group_id)
        flash(f"Moved to {group.groupName if group else 'group'}", "success")
    return redirect(url_for('admin_views.admin_manage_groups'))


@admin_views.route('/admin/manage-groups/students/<int:student_id>/edit', methods=['POST'])
@admin_required
def admin_edit_class_student(student_id):
    student, err = update_student(
        student_id,
        name=request.form.get('name'),
        username=request.form.get('student_id'),
        email=request.form.get('email'),
    )
    if err:
        flash(err, "failed")
        return redirect(url_for('admin_views.admin_manage_groups'))

    raw = (request.form.get('group_id') or '').strip()
    group_id = None if raw in ('', '0', 'none') else int(raw)
    ok, move_err = move_student_to_group(
        student_id, group_id=group_id, academic_year=get_current_year()
    )
    if not ok:
        flash(move_err or "Student details saved, but group could not be updated", "failed")
    else:
        flash(f"Updated {student.name}", "success")
    return redirect(url_for('admin_views.admin_manage_groups'))


@admin_views.route('/admin/manage-groups/students/<int:student_id>/delete', methods=['POST'])
@admin_required
def admin_delete_class_student(student_id):
    ok, err = delete_student(student_id)
    if not ok:
        flash(err or "Could not delete student", "failed")
    else:
        flash("Student removed from the class list", "success")
    return redirect(url_for('admin_views.admin_manage_groups'))


@admin_views.route('/admin/manage-groups/students/delete-all', methods=['POST'])
@admin_required
def admin_delete_all_class_students():
    year = get_current_year()
    count = delete_all_students_for_year(year)
    if count:
        flash(f"Removed {count} students from the {year} class list", "success")
    else:
        flash(f"No students to remove for {year}", "info")
    return redirect(url_for('admin_views.admin_manage_groups'))


@admin_views.route('/admin/groups/<int:group_id>/remove', methods=['POST'])
@admin_required
def admin_remove_group(group_id):
    group = get_group(group_id)

    if group:
        removed = remove_group(group_id)
        flash("Group Removed", "success")

    return redirect(url_for('admin_views.admin_manage_groups'))

@admin_views.route('/admin/groups/<int:group_id>/reopen', methods=['POST'])
@admin_required
def admin_reopen_group(group_id):
    group = get_group(group_id)
    if group:
        lot_entries = db.session.scalars(
            db.select(LotGroup)
            .filter_by(groupID=group_id)
        ).all()
        for entry in lot_entries:
            remove_lotGroup(entry.lotID, entry.groupID)

        group.status = "requested"
        db.session.commit()
        flash("Group moved back to pending status", "success")

    return redirect(url_for('admin_views.admin_manage_groups'))

@admin_views.route('/admin/group-requests/<int:group_id>/approve', methods=['POST'])
@admin_required
def admin_approve_group(group_id):
    ok, err = assign_exclusive_lots(group_id, count=2)
    if ok:
        flash("Group approved and 2 exclusive lots auto-assigned", "success")
    else:
        flash(err or "Could not approve group", "failed")
    return redirect(url_for('admin_views.admin_manage_groups'))

@admin_views.route('/admin/group-requests/<int:group_id>/decline', methods=['POST'])
@admin_required
def admin_decline_group(group_id):
    group = get_group(group_id)

    if group:
        remove_group(group_id)
        flash("Group Rejected", "success")

    return redirect(url_for('admin_views.admin_manage_groups'))

@admin_views.route('/admin/group-requests/<int:group_id>/approve-and-assign', methods=['POST'])
@admin_required
def admin_approve_and_assign_group(group_id):
    # Legacy route: same as one-click approve
    return admin_approve_group(group_id)

# ─── RFP Routes ───────────────────────────────────────────────────────────────

@admin_views.route('/admin/manage-rfps', methods=['GET', 'POST'])
@admin_required
def admin_manage_rfps():
    if request.method == 'POST':
        action = request.form.get('action')
        lotID = request.form.get('lotID')
        groupID = request.form.get('groupID')

        if action in ("reject", "remove"):
            remove_rfp(groupID, lotID)
            flash(f'RFP for Lot {lotID} removed successfully', "success")

        return redirect(url_for('admin_views.admin_manage_rfps'))

    year = get_current_year()
    rfp_drafts = db.session.scalars(
        db.select(RFP)
        .join(Lot, Lot.id == RFP.lotID)
        .filter(Lot.academic_year == year, RFP.status == "draft")
    ).all()

    rfp_gallery = db.session.scalars(
        db.select(RFP)
        .join(Lot, Lot.id == RFP.lotID)
        .filter(Lot.academic_year == year, RFP.status == "submitted")
    ).all()

    def rfp_to_dict(entry):
        group = get_group(entry.groupID)
        lot = get_lot(entry.lotID)
        return {
            "groupID": entry.groupID,
            "lotID": entry.lotID,
            "lot_label": display_lot_label(lot) if lot else f"Lot {entry.lotID}",
            "name": group.groupName,
            "Lot": lot.labType if lot else "—",
            "timestamp": format_timestamp(entry.timestamp),
            "status": entry.status,
            "deviceType": entry.deviceType,
            "resolution": entry.resolution,
            "os": entry.os,
            "cpu": entry.cpu,
            "ram": entry.ram,
            "drive": entry.drive,
            "gpu": entry.gpu,
            "io": entry.io,
            "peripherals": entry.peripherals,
            "features": entry.features,
        }

    return render_template(
        'admin/manage_rfps.html',
        rfp_requests=[rfp_to_dict(e) for e in rfp_drafts],
        rfp_gallery=[rfp_to_dict(e) for e in rfp_gallery],
        title='Manage RFPs',
        active_page='rfps',
    )


# ─── Evaluation Routes ────────────────────────────────────────────────────────

def _evaluation_compare_payload(evaluation, bid=None, lot=None, rfp=None, client=None, vendor=None):
    """Serialize one bid (+ optional evaluation) for the compare modal."""
    if bid is None and evaluation is not None:
        bid = get_bid(evaluation.bidID)
    if evaluation:
        lot = lot or get_lot(evaluation.lotID)
        client = client or get_group(evaluation.sourceGroupID)
        vendor = vendor or get_group(evaluation.recipientGroupID)
        rfp = rfp or get_rfp(evaluation.sourceGroupID, evaluation.lotID)
        lot_id = evaluation.lotID
        client_id = evaluation.sourceGroupID
        vendor_id = evaluation.recipientGroupID
        snap = evaluation
    else:
        if bid is None:
            return None
        lot_id = bid.lotID
        client_id = bid.recipientGroupID
        vendor_id = bid.sourceGroupID
        lot = lot or get_lot(lot_id)
        client = client or get_group(client_id)
        vendor = vendor or get_group(vendor_id)
        rfp = rfp or get_rfp(client_id, lot_id)
        snap = None

    def spec(attr):
        live = getattr(rfp, attr, None) if rfp else None
        saved = getattr(snap, attr, None) if snap else None
        return (live or saved or "").strip() or "—"

    return {
        "id": evaluation.id if evaluation else None,
        "has_evaluation": evaluation is not None,
        "status": evaluation.status if evaluation else None,
        "client_id": client_id,
        "name": client.groupName if client else "—",
        "to_group_name": vendor.groupName if vendor else "—",
        "lotID": lot_id,
        "lot_label": display_lot_label(lot) if lot else f"Lot {lot_id}",
        "labType": lot.labType if lot else "—",
        "lot_budget": lot.budget if lot else None,
        "timestamp": format_timestamp(evaluation.timestamp) if evaluation else "",
        "specsMet": evaluation.specsMet if evaluation else None,
        "professionalism": evaluation.professionalism if evaluation else None,
        "presentation": evaluation.presentation if evaluation else None,
        "budgetScore": evaluation.budget if evaluation else None,
        "overall": evaluation.overallScore if evaluation else None,
        "specs_selected": [
            s for s in ((evaluation.specsSelected or "") if evaluation else "").split(",") if s
        ],
        "bid_id": bid.id if bid else None,
        "bid_filename": bid.bidDocumentName if bid else "—",
        "bid_quotation": bid.quotationAmount if bid else None,
        "pdf_url": url_for(
            'admin_views.admin_view_bid_document',
            group_id=vendor_id,
            bid_id=bid.id,
        ) if bid and vendor_id else "",
        "rfp": {
            "deviceType": spec("deviceType"),
            "resolution": spec("resolution"),
            "os": spec("os"),
            "cpu": spec("cpu"),
            "ram": spec("ram"),
            "drive": spec("drive"),
            "gpu": spec("gpu"),
            "io": spec("io"),
            "peripherals": spec("peripherals"),
            "features": spec("features"),
        },
    }


@admin_views.route('/admin/manage-evaluations')
@admin_required
def admin_manage_evaluations():
    from App.controllers.settings import are_results_published

    year = get_current_year()
    evaluations = db.session.scalars(
        db.select(Evaluation)
        .join(Lot, Lot.id == Evaluation.lotID)
        .filter(Lot.academic_year == year, Evaluation.status == "selected")
    ).all()
    results_published = are_results_published()

    evaluation_groups = []
    client_counts = {}
    peers_by_lot = {}

    for evaluation in evaluations:
        client_id = evaluation.sourceGroupID
        client = get_group(client_id)
        client_name = client.groupName if client else "—"
        client_counts[client_id] = client_counts.get(
            client_id, {"id": client_id, "name": client_name, "count": 0}
        )
        client_counts[client_id]["count"] += 1

        lot_id = evaluation.lotID
        if lot_id not in peers_by_lot:
            lot = get_lot(lot_id)
            rfp = get_rfp(client_id, lot_id)
            lot_bids = db.session.scalars(
                db.select(Bid).filter_by(lotID=lot_id).order_by(Bid.timestamp, Bid.id)
            ).all()
            peers = []
            for bid in lot_bids:
                peer_eval = db.session.scalars(
                    db.select(Evaluation).filter_by(bidID=bid.id)
                ).first()
                peer = _evaluation_compare_payload(
                    peer_eval,
                    bid=bid,
                    lot=lot,
                    rfp=rfp,
                    client=client,
                    vendor=get_group(bid.sourceGroupID),
                )
                if peer:
                    peers.append(peer)
            peers_by_lot[lot_id] = peers

        peers = peers_by_lot[lot_id]
        peer_index = next(
            (i for i, p in enumerate(peers) if p.get("bid_id") == evaluation.bidID),
            0,
        )
        payload = dict(peers[peer_index])
        payload["id"] = evaluation.id
        payload["lot_peers"] = peers
        payload["peer_index"] = peer_index
        payload["lot_bid_count"] = len(peers)
        evaluation_groups.append(payload)

    return render_template(
        'admin/manage_evaluations.html',
        evaluation_groups=evaluation_groups,
        client_filters=list(client_counts.values()),
        title='Manage Evaluations',
        active_page='evaluations',
        results_published=results_published,
    )

@admin_views.route('/admin/manage-evaluations/<int:evaluationID>/remove', methods=['POST'])
@admin_required
def admin_remove_evaluation(evaluationID):
    
    evaluation = get_evaluation(evaluationID)

    evaluation.status = "draft"

    db.session.commit()
    
    flash("Evaluation removed successfully", "success")
    return redirect(url_for('admin_views.admin_manage_evaluations'))


# ─── Settings & CSV Import ────────────────────────────────────────────────────

@admin_views.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        from App.controllers.settings import update_settings
        from App.controllers.academic_year import set_current_year

        settings, err = update_settings(
            request.form.get('group_size_min'),
            request.form.get('group_size_max'),
            active_year=request.form.get('active_academic_year'),
            results_published=request.form.get('results_published') == '1',
        )
        if err:
            flash(err, "failed")
        else:
            set_current_year(settings.active_academic_year)
            publish_label = "published" if settings.results_published else "hidden"
            flash(
                f"Settings saved — year {settings.active_academic_year}; "
                f"group size {settings.group_size_min}-{settings.group_size_max}; "
                f"award results {publish_label}",
                "success",
            )
        return redirect(url_for('admin_views.admin_settings'))

    settings = get_or_create_settings()
    return render_template(
        'admin/settings.html',
        title='Settings',
        active_page='settings',
        settings=settings,
        free_lots=count_unassigned_lots(),
    )


@admin_views.route('/admin/publish-results', methods=['POST'])
@admin_required
def admin_publish_results():
    from App.controllers.settings import set_results_published

    publish = request.form.get('results_published') == '1'
    set_results_published(publish)
    if publish:
        flash("Award results are now visible to vendors", "success")
    else:
        flash("Award results are hidden from vendors again", "info")
    next_url = request.form.get('next') or url_for('admin_views.admin_manage_evaluations')
    return redirect(next_url)


@admin_views.route('/admin/import-groups', methods=['GET', 'POST'])
@admin_required
def admin_import_groups():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or not file.filename:
            flash("Please upload a CSV file", "failed")
            return redirect(url_for('admin_views.admin_import_groups'))

        credentials, errors = import_groups_from_csv(file)
        if errors:
            for err in errors:
                flash(err, "failed")
            return redirect(url_for('admin_views.admin_import_groups'))

        flash(f"Imported {len(credentials)} students across groups (auto-approved)", "success")
        csv_body = credentials_to_csv(credentials)
        return Response(
            csv_body,
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=import_credentials.csv'
            },
        )

    min_size, max_size = get_group_size_range()
    return render_template(
        'admin/import_groups.html',
        title='Import Groups',
        active_page='import',
        min_size=min_size,
        max_size=max_size,
        free_lots=count_unassigned_lots(),
    )