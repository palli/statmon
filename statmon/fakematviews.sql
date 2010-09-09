
drop view if exists last_snap_view;
create view last_snap_view as
     select s.*
       from snapshots s
      where snap_id = (select max(snap_id) from snapshots);

drop view if exists server_name;
create view server_name as
     select server_name from status
      where snap_id = (select snap_id from last_snap_view);

drop table if exists occupancy_snapshots_mv;
create table occupancy_snapshots_mv as
    select snap_id,
           node_name,
           ns.domain_name,
           o.stgpool_name,
           (select server_name from server_name) server_name,
           sum( if(o.type = 'Arch', o.logical_mb, 0) )*1024*1024 logical_bytes_arch,
           sum( if(o.type = 'Arch', o.physical_mb, 0) )*1024*1024 physical_bytes_arch,
           sum( if(o.type = 'Arch', o.num_files, 0) ) num_files_arch,
           sum( if(o.type = 'Bkup', o.logical_mb, 0) )*1024*1024 logical_bytes_bkup,
           sum( if(o.type = 'Bkup', o.physical_mb, 0) )*1024*1024 physical_bytes_bkup,
           sum( if(o.type = 'Bkup', o.num_files, 0) ) num_files_bkup
      from nodes_snapshots ns inner join occupancy_snapshots o using (node_name,snap_id)
  group by snap_id,node_name,o.stgpool_name;
alter table occupancy_snapshots_mv add primary key ( snap_id,node_name,stgpool_name );

drop table if exists occupancy_mv;
create table occupancy_mv as
    select *
      from occupancy_snapshots_mv
     where snap_id = (select max(snap_id) from occupancy_snapshots_mv);
alter table occupancy_mv add primary key ( node_name,stgpool_name );

drop table if exists filespaces_mv ;
create table filespaces_mv as
    select f.*,
           '' domain_name,
           (select server_name from server_name) server_name,
           capacity*1024*1024 capacity_bytes,
           capacity*(pct_util/100)*1024*1024 used_bytes,
           pct_util,
           backup_start,
           backup_end,
           delete_occurred,
           greatest(
              if(f.filespace_name = 'ASR', 1, 0),
              if(f.filespace_type = 'SYSTEM', 1, 0),
              if(f.filespace_type like 'API:%', 1, 0) ) virtual_fs,
           sum( if(o.type = 'Arch', o.logical_mb, 0) )*1024*1024 logical_bytes_arch,
           sum( if(o.type = 'Arch', o.physical_mb, 0) )*1024*1024 physical_bytes_arch,
           sum( if(o.type = 'Arch', o.num_files, 0) ) num_files_arch,
           sum( if(o.type = 'Bkup', o.logical_mb, 0) )*1024*1024 logical_bytes_bkup,
           sum( if(o.type = 'Bkup', o.physical_mb, 0) )*1024*1024 physical_bytes_bkup,
           sum( if(o.type = 'Bkup', o.num_files, 0) ) num_files_bkup
      from filespaces f inner join filespaces_snapshots fs
           using (node_name, filespace_id, snap_id) left join
           occupancy_snapshots o using (node_name, filespace_id, snap_id)
     where snap_id = (select max(snap_id) from filespaces)
  group by node_name, filespace_id;
alter table filespaces_mv
     change domain_name domain_name varchar( 64 );
alter table filespaces_mv add primary key ( node_name,filespace_id );

-- drop table if exists nodes_version_history_mv;
-- create table nodes_version_history_mv as
--    select node_name,
--           min( start_date ) from_date,
--           max( start_date ) to_date,
--           concat( client_version, '.',
--                   client_release, '.',
--                   client_level, '.',
--                   if(client_sublevel<10, '0', ''),
--                   client_sublevel ) node_version
--      from nodes_snapshots inner join snapshots using (snap_id)
--  group by node_name, node_version;

-- changing to table rather than view to workround mysql bugs in some versions
drop view if exists nodes_view;
drop table if exists nodes_view;
create table nodes_view as
   select n.*,
          ns.domain_name,
          (select server_name from server_name) server_name,
          concat( ns.client_version, '.',
                  ns.client_release, '.',
                  ns.client_level, '.',
                  if(ns.client_sublevel<10, '0', ''),
                  ns.client_sublevel ) node_version,
          ns.option_set
     from nodes n inner join nodes_snapshots ns using (node_name,snap_id)
    where snap_id = (select max(snap_id) from nodes) order by node_name;
-- alter table nodes_mv add primary key ( node_name );

drop view if exists occupancy_node_view;
create view occupancy_node_view as
   select node_name,
          sum( ifnull(logical_bytes_arch,0) ) logical_bytes_arch,
          sum( ifnull(physical_bytes_arch,0) ) physical_bytes_arch,
          sum( ifnull(num_files_arch,0) ) num_files_arch,
          sum( ifnull(logical_bytes_bkup,0) ) logical_bytes_bkup,
          sum( ifnull(physical_bytes_bkup,0) ) physical_bytes_bkup,
          sum( ifnull(num_files_bkup,0) ) num_files_bkup
     from nodes_view nv left join occupancy_mv om using (node_name)
 group by nv.node_name;

drop view if exists occupancy_anza_node_view;
create view occupancy_anza_node_view as
   select node_name,
          nv.domain_name,
          contact,
          sum( if(stgpool_name not like '%_DUP_%',ifnull(logical_bytes_arch,0),0) ) logical_bytes_arch,
          sum( if(stgpool_name not like '%_DUP_%',ifnull(physical_bytes_arch,0),0) ) physical_bytes_arch,
          sum( if(stgpool_name not like '%_DUP_%',ifnull(num_files_arch,0),0) ) num_files_arch,
          sum( if(stgpool_name not like '%_DUP_%',ifnull(logical_bytes_bkup,0),0) ) logical_bytes_bkup,
          sum( if(stgpool_name not like '%_DUP_%',ifnull(physical_bytes_bkup,0),0) ) physical_bytes_bkup,
          sum( if(stgpool_name not like '%_DUP_%',ifnull(num_files_bkup,0),0) ) num_files_bkup,
          sum( if(stgpool_name like '%_DUP_%',ifnull(logical_bytes_arch,0),0) ) dup_logical_bytes_arch,
          sum( if(stgpool_name like '%_DUP_%',ifnull(physical_bytes_arch,0),0) ) dup_physical_bytes_arch,
          sum( if(stgpool_name like '%_DUP_%',ifnull(num_files_arch,0),0) ) dup_num_files_arch,
          sum( if(stgpool_name like '%_DUP_%',ifnull(logical_bytes_bkup,0),0) ) dup_logical_bytes_bkup,
          sum( if(stgpool_name like '%_DUP_%',ifnull(physical_bytes_bkup,0),0) ) dup_physical_bytes_bkup,
          sum( if(stgpool_name like '%_DUP_%',ifnull(num_files_bkup,0),0) ) dup_num_files_bkup
     from nodes_view nv left join occupancy_mv om using (node_name)
 group by nv.node_name;

drop view if exists nodes_fs_view;
create view nodes_fs_view as
   select nv.*,
          count(1) fs_count,
          sum( ifnull(capacity_bytes, 0) ) fs_capacity_bytes,
          sum( ifnull(used_bytes, 0) ) fs_used_bytes,
          min( backup_start ) fs_min_backup_started,
          max( backup_start ) fs_max_backup_started,
          min( backup_end ) fs_min_backup_end,
          max( backup_end ) fs_max_backup_end,
          min( delete_occurred ) fs_min_delete_occurred,
          max( delete_occurred ) fs_max_delete_occurred
     from nodes_view nv left join filespaces_mv using (node_name)
 group by node_name;

drop table if exists nodes_mv;
create table nodes_mv as
   select *
     from nodes_fs_view nfv inner join occupancy_node_view onv using (node_name)
 group by nfv.node_name;
alter table nodes_mv add primary key ( node_name );

update filespaces_mv f, nodes_mv n
   set f.domain_name = n.domain_name
 where f.node_name = n.node_name;

drop view if exists domains_view;
create view domains_view as
   select *
     from domains d inner join domains_snapshots ds using (domain_name,snap_id)
    where snap_id = (select max(snap_id) from domains);

drop table if exists domains_mv;
create table domains_mv as
   select dv.*,
          sum( ifnull(logical_bytes_arch,0) ) logical_bytes_arch,
          sum( ifnull(physical_bytes_arch,0) ) physical_bytes_arch,
          sum( ifnull(num_files_arch,0) ) num_files_arch,
          sum( ifnull(logical_bytes_bkup,0) ) logical_bytes_bkup,
          sum( ifnull(physical_bytes_bkup,0) ) physical_bytes_bkup,
          sum( ifnull(num_files_bkup,0) ) num_files_bkup
     from domains_view dv left join occupancy_mv om using (domain_name)
 group by dv.domain_name;
alter table domains_mv add primary key ( domain_name );

drop table if exists volumes_snapshots_summary_mv;
create table volumes_snapshots_summary_mv as
    select v.stgpool_name,
           vs.snap_id vol_snap_id, /*?!*/
           count(1) volumes,
           sum(ifnull(vs.read_errors,0)) read_errors,
           sum(ifnull(vs.write_errors,0)) write_errors,
           sum(if(vs.access = 'READWRITE', 1, 0)) readwrite,
           sum(if(vs.access = 'READONLY', 1, 0)) readonly,
           sum(if(vs.access = 'UNAVAILABLE', 1, 0)) unavailable,
           sum(if(vs.status = 'ONLINE', 1, 0)) online,
           sum(if(vs.status = 'EMPTY', 1, 0)) empty,
           sum(if(vs.status = 'FILLING', 1, 0)) filling,
           sum(if(vs.status = 'FULL', 1, 0)) full,
           sum(vs.est_capacity_mb)*1024*1024 est_capacity_bytes,
           sum(vs.pct_utilized*vs.est_capacity_mb/100)*1024*1024 est_used_bytes,
           sum(if(vs.access = 'READWRITE',
                  if(vs.status = 'FULL',(100-vs.pct_utilized)*vs.est_capacity_mb/100,0),0)
               )*1024*1024 est_useable_bytes,
           sum(if(vs.access = 'READWRITE',ifnull(vs.pct_reclaim,0)*vs.est_capacity_mb/100,0)
               )*1024*1024 est_reclaimable_bytes
      from volumes v inner join volumes_snapshots vs using (volume_name)
  group by v.stgpool_name, vs.snap_id;
alter table volumes_snapshots_summary_mv add primary key ( stgpool_name, vol_snap_id );

drop table if exists volumes_snapshots_status_mv;
create table volumes_snapshots_status_mv as
  select vs.snap_id,
         v.stgpool_name,
         concat(vs.access,'+',vs.status) volume_status,
         count(1) volume_count
    from volumes v, volumes_snapshots vs
   where v.volume_name = vs.volume_name
group by vs.snap_id, stgpool_name, concat(vs.access,'+',vs.status);
alter table volumes_snapshots_status_mv add primary key ( snap_id, stgpool_name, volume_status );

drop table if exists volumes_summary_mv;
create table volumes_summary_mv as
      select *
        from volumes_snapshots_summary_mv
       where vol_snap_id = (select max(snap_id) from volumes);
 alter table volumes_summary_mv add primary key ( stgpool_name );

drop view if exists stgpools_view;
create view stgpools_view as
     select *
       from stgpools s inner join stgpools_snapshots ss using (stgpool_name,snap_id)
      where snap_id = (select max(snap_id) from stgpools);

drop view if exists associations_view;
create view associations_view as
    select *
      from associations
     where snap_id = (select max(snap_id) from stgpools);

drop table if exists summary_daily_backup;
-- create table summary_daily_backup as
--   select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
--          ns.domain_name,
--          ns.node_name,
--          sum(s.bytes) bytes,
--          count(1) count
--     from summary s, nodes n, nodes_snapshots ns
--    where s.activity='BACKUP'
--      and s.entity = n.node_name
--      and n.node_name = ns.node_name
--      and n.snap_id = ns.snap_id
--      and n.nodetype = 'CLIENT'
-- group by date_format(start_time,'%Y-%m-%d'),ns.domain_name,ns.node_name;
-- alter table summary_daily_backup add primary key ( node_name, domain_name, ts );

drop table if exists summary_daily_restore;
create table summary_daily_restore as
  select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
         ns.domain_name,
         ns.node_name,
         sum(s.bytes) bytes,
         count(1) count
    from summary s, nodes n, nodes_snapshots ns
   where s.activity='RESTORE'
     and s.entity = n.node_name
     and n.node_name = ns.node_name
     and n.snap_id = ns.snap_id
     and n.nodetype = 'CLIENT'
group by date_format(start_time,'%Y-%m-%d'),ns.domain_name,ns.node_name;
alter table summary_daily_restore add primary key ( node_name, domain_name, ts );

drop table if exists summary_activities_mv;
create table summary_activities_mv as
    select activity from summary group by activity ;

drop table if exists actlog_count_mv;
create table actlog_count_mv as
    select severity,
           msgno,
           count(msgno) msg_count,
           sum(length(message)) msg_size,
           sum(if(date_sub(now(),interval 1 day)<date_time,1,0)) count_last24,
           sum(if(date_sub(now(),interval 1 day)<date_time,length(message),0)) size_last24,
           max(date_time) newest_date_time,
           '' newest_message
      from actlog
  group by severity, msgno;
alter table actlog_count_mv
     change newest_message newest_message varchar( 255 );

update actlog_count_mv ac, actlog a
   set ac.newest_message = if(length(a.message)>255,concat(left(a.message,251),' ...'),a.message)
 where ac.newest_date_time = a.date_time
   and ac.msgno = a.msgno
   and ac.severity = a.severity;

-- legacy view
drop view if exists actlog_count_view;
create view actlog_count_view as
  select msgno, msg_count count
    from actlog_count_mv;

drop table if exists stgpools_mv;
create table stgpools_mv as
      select *
        from stgpools_view left join volumes_summary_mv using (stgpool_name);

drop table if exists actlog_failed_files_mv;
create table actlog_failed_files_mv as
     select a.*
       from actlog a
      where (a.msgno=4005 or a.msgno=4987 or a.msgno=4037)
        and a.date_time > subtime(now(),'30 0:0:0')
   order by a.date_time;
alter table actlog_failed_files_mv add index idx_date ( date_time ) ;

drop table if exists actlog_backup_history_mv;
create table actlog_backup_history_mv as
     select a.*
       from actlog a
      where a.msgno=2579 or a.msgno=2578 or a.msgno=2507
   order by a.date_time;
alter table actlog_backup_history_mv add index idx_date ( date_time ) ;

drop view if exists alert_stgpools_view;
create view alert_stgpools_view as
    select distinct stgpool_name
    from occupancy_mv
    where stgpool_name not in ( select distinct stgpool_name from stgpools );

drop view if exists clientopts_view ;
create view clientopts_view as
    select node_name,clientopts.*
    from clientopts,nodes_mv
    where clientopts.optionset_name = nodes_mv.option_set ;
