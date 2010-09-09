#!/usr/bin/python

profiles = {
	#SingleNodesCount (unused)
	'SingleNodesCount': {
		'Params' : {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Number of Nodes',
		'Base' : '1000',
		'GraphType' : 'LINE2',
		'HeartBeat' : 5,
		'Query' : ''' select s.ts,
                             'Number of Nodes' ds,
                             count(1)
                        from nodes_snapshots ns,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = ns.snap_id
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by s.ts
                    order by s.ts ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#NodesCount - Done
	'NodesCount': {
		'Params' : {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Number of Nodes',
		'Base' : '1000',
		'GraphType' : 'LINE2',
		'TextType' : ['Count','node(s)'],
		'HeartBeat' : 5,
		'Query' : ''' select ts,
                             ifnull(n.platform_name, 'Unknown') ds,
                             count(1)
                        from nodes_snapshots ns, nodes n,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = ns.snap_id
                         and ns.node_name = n.node_name
                         and n.nodetype = 'CLIENT'
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by n.platform_name, s.ts
                    order by ifnull(n.platform_name, 'ZZZ') asc, s.ts; ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#NodesDailyBackupTX - Done
	'NodesDailyBackupTX': {
		'Params' : {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Daily Amount of Backup',
		'Base' : '1024',
		'HeartBeat' : 0,
		'Query' : ''' select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                             'Bytes Transfered' ds,
                             sum(bytes) val
                        from summary s, nodes n, nodes_snapshots ns
                       where activity='BACKUP'
                         and s.entity = n.node_name
                         and n.node_name = ns.node_name
                         and n.snap_id = ns.snap_id
                         and n.nodetype = 'CLIENT'
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by date_format(start_time,'%Y-%m-%d'); ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#NodesDailyRestoreTX - Done 
	'NodesDailyRestoreTX': {
		'Params' : {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Daily Amount Restored',
		'Base' : '1024',
		'HeartBeat' : 0,
		'Query' : ''' select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                             'Bytes Transfered' ds,
                             sum(bytes) val
                        from summary s, nodes n, nodes_snapshots ns
                       where activity='RESTORE'
                         and s.entity = n.node_name
                         and n.node_name = ns.node_name
                         and n.snap_id = ns.snap_id
                         and n.nodetype = 'CLIENT'
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by date_format(start_time,'%Y-%m-%d'); ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#NodesTotalArchive - Done 
	'NodesTotalArchive': {
		'Params' : {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Total Amount in Archive',
		'Base' : '1024',
		'TextType' : ['Size',' %SB (size)'],
		'HeartBeat' : 5,
		'Query' : ''' select s.ts,
                             o.stgpool_name ds,
                             round(sum(o.logical_mb) * 1024 * 1024) value
                        from occupancy_snapshots o,
                             nodes n, nodes_snapshots ns,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = o.snap_id
                         and o.node_name = n.node_name
                         and o.node_name = ns.node_name
                         and n.snap_id = ns.snap_id
                         and o.logical_mb > 0
                         and o.type = 'Arch'
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by o.stgpool_name, s.ts
                    order by o.stgpool_name asc, s.ts; ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#NodesTotalBackup
	'NodesTotalBackup': {
		'Params' : {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Total Amount in Backup',
		'Base' : '1024',
		'TextType' : ['Size',' %SB (size)'],
		'HeartBeat' : 5,
		'Query' : ''' select s.ts,
                             o.stgpool_name ds,
                             round(sum(o.logical_mb) * 1024 * 1024) value
                        from occupancy_snapshots o,
                             nodes n, nodes_snapshots ns,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = o.snap_id
                         and o.node_name = n.node_name
                         and o.node_name = ns.node_name
                         and n.snap_id = ns.snap_id
                         and o.logical_mb > 0
                         and o.type = 'Bkup'
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by o.stgpool_name, s.ts
                    order by o.stgpool_name asc, s.ts; ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#StorageUtilization - Done
	'StorageUtilization': {
		'Params' : {
			'stgpoolfilter': {'Hash':1,'EscapeFilter':1},
			'stgpoollist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Storage Utilization',
		'Base' : '1024',
		'UpperLimit' : '100',
		'GraphType' : 'LINE2',
		'HeartBeat' : 5,
		'Query' : ''' select s.ts,
                             v.stgpool_name ds,
                             sum(1024*1024*vs.pct_utilized*vs.est_capacity_mb)/
                                 sum(1024*1024*vs.est_capacity_mb)
                        from volumes v, volumes_snapshots vs,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where v.volume_name = vs.volume_name
                         and s.snap_id = vs.snap_id
                         and (v.stgpool_name like @stgpoolfilter@ or v.stgpool_name in @stgpoollist@)
                    group by v.stgpool_name, s.ts; ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#StorageUtilization
	'OldStorageUtilization': {
		'Params' : {
			'stgpoolfilter': {'Hash':1,'EscapeFilter':1},
			'stgpoollist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Storage Utilization',
		'Base' : '1024',
		'HeartBeat' : 5,
		'Query' : ''' select s.ts,
                             'Used / Estimated Capacity' ds,
                             sum( round( pct_utilized*est_capacity_mb*1024*1024/100 ) ) v,
                             sum( est_capacity_mb*1024*1024 ) max
                        from stgpools_snapshots ps,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = ps.snap_id
                         and (ps.stgpool_name like @stgpoolfilter@ or ps.stgpool_name in @stgpoollist@)
                    group by s.ts; ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#VolumesCount - Done 
	'VolumesCount': {
		'Params' : {
			'stgpoolfilter': {'Hash':1,'EscapeFilter':1},
			'stgpoollist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Number of Volumes',
		'Base' : '1000',
		'HeartBeat' : 5,
		'GraphType' : 'LINE2',
		'TextType' : ['Count','volume(s)'],
		'Query' : ''' select s.ts,
                             v.stgpool_name ds,
                             count(1)
                        from volumes v, volumes_snapshots vs,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = vs.snap_id
                         and v.volume_name = vs.volume_name
                         and (v.stgpool_name like @stgpoolfilter@ or v.stgpool_name in @stgpoollist@)
                    group by v.stgpool_name, s.ts
                    order by v.stgpool_name, s.ts; ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#NodeFilespaces - Done 
	'NodeFilespaces': {
		'Params' : {
			'node':
				{'Hash':1,'Escape':1},
		},
		'Title' : 'Filespaces',
		'Base' : '1000',
		'HeartBeat' : 5,
		'UpperLimit' : '100',
		'GraphType' : 'LINE2',
		'TextType' : ['PercentMax','%SB (size)\t\:','%SB (used)\t\:','%%'],
		'Query' : ''' select s.ts,
                             f.filespace_name name,
                             pct_util value,
                             fs.capacity*1024*1024 max
                        from filespaces f, filespaces_snapshots fs,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = fs.snap_id
                         and f.filespace_id = fs.filespace_id
                         and f.node_name = fs.node_name
                         and not f.filespace_type = 'SYSTEM'
                         and not (f.filespace_type = 'NTFS' and f.filespace_name = 'ASR')
                         and f.node_name = @node@
                    order by ts''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#Old NodeTransferSpeed - Done
	'NodeTransferSpeed': {
		'Params' : {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Average Transfer Speed',
		'Base' : '1024',
		'HeartBeat' : 0,
		'Query' : ''' select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                             'Speed Bytes/Sec' ds,
                             sum(bytes)/
                             sum(unix_timestamp(end_time)-unix_timestamp(start_time)) val
                        from summary s, nodes n, nodes_snapshots ns
                       where activity='BACKUP'
                         and s.entity = n.node_name
                         and n.node_name = ns.node_name
                         and n.snap_id = ns.snap_id
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by date_format(start_time,'%Y-%m-%d') ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#NodeTransferSpeed - TODO check, bit slow?
	'NodeTransferSpeed2': {
		'Params' : {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Average Transfer Speed',
		'Base' : '1024',
		'HeartBeat' : 0,
		'Query' : ''' select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                             'Speed in Bytes/Sec' ds,
                             count(distinct entity)*sum(bytes)/
                             sum(unix_timestamp(end_time)-unix_timestamp(start_time)) val
                        from summary s, nodes n, nodes_snapshots ns
                       where activity='BACKUP'
                         and s.entity = n.node_name
                         and n.node_name = ns.node_name
                         and n.snap_id = ns.snap_id
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by date_format(start_time,'%Y-%m-%d') ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#NodeSessionDuration - Done
	'NodeSessionDuration': {
		'Params' : {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Average Session Duration',
		'Base' : '1000',
		'HeartBeat' : 0,
		'Query' : ''' select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                             'Duration in Minutes' ds,
                             avg(unix_timestamp(end_time)-unix_timestamp(start_time))/60 val
                        from summary s, nodes n, nodes_snapshots ns
                       where activity='BACKUP'
                         and s.entity = n.node_name
                         and n.node_name = ns.node_name
                         and n.snap_id = ns.snap_id
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by date_format(start_time,'%Y-%m-%d') ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
	#NodeSessionCount - Done
	'NodeSessionCount': {
		'Params' : {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
		},
		'Title' : 'Daily Number of Sessions',
		'Base' : '1000',
		'HeartBeat' : 0,
		#'GraphType' : 'LINE2',
		'Query' : ''' select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                             'Number of Sessions' ds,
                             count(1) val
                        from summary s, nodes n, nodes_snapshots ns
                       where activity='BACKUP'
                         and s.entity = n.node_name
                         and n.node_name = ns.node_name
                         and n.snap_id = ns.snap_id
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by date_format(start_time,'%Y-%m-%d') ''',
		'Filename' : '@profile@-@hashid@-@ds@.@ending@',
	},
}
