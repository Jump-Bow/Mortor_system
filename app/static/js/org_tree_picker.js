/**
 * OrgTreePicker - 樹狀組織選取器
 *
 * 使用方式：
 *   initOrgTreePicker({
 *     btnId:       'org-picker-btn',    // 觸發按鈕 ID
 *     dropId:      'org-picker-drop',   // 浮層容器 ID
 *     inputId:     'org-picker-val',    // 隱藏 input ID（存 org_id）
 *     placeholder: '全部組織',           // 未選取時的按鈕文字
 *   });
 *
 * 選取後可讀取 $('#org-picker-val').val() 取得 org_id（空字串 = 全部）
 */

(function (global) {
    'use strict';

    function initOrgTreePicker(opts) {
        const btnId      = opts.btnId;
        const dropId     = opts.dropId;
        const inputId    = opts.inputId;
        const placeholder = opts.placeholder || '全部組織';

        /* ---------- 浮層 HTML ---------- */
        if (!document.getElementById(dropId)) {
            const drop = document.createElement('div');
            drop.id = dropId;
            drop.style.cssText = [
                'position:absolute',
                'z-index:9999',
                'background:#fff',
                'border:1px solid #dee2e6',
                'border-radius:4px',
                'box-shadow:0 4px 16px rgba(0,0,0,.12)',
                'padding:8px',
                'min-width:240px',
                'max-height:360px',
                'overflow-y:auto',
                'display:none'
            ].join(';');
            document.body.appendChild(drop);
        }

        const $btn   = $('#' + btnId);
        const $drop  = $('#' + dropId);
        const $input = $('#' + inputId);

        /* 重新定位浮層到按鈕下方 */
        function repositionDrop() {
            const offset = $btn.offset();
            const h      = $btn.outerHeight();
            $drop.css({ top: offset.top + h + 4, left: offset.left });
        }

        /* 開關浮層 */
        $btn.on('click', function (e) {
            e.stopPropagation();
            if ($drop.is(':visible')) {
                $drop.hide();
                return;
            }
            repositionDrop();
            loadTree();
            $drop.show();
        });

        /* 點擊浮層外關閉 */
        $(document).on('click.orgpicker_' + btnId, function (e) {
            if (!$(e.target).closest('#' + dropId + ',#' + btnId).length) {
                $drop.hide();
            }
        });

        /* 動態搜尋過濾 */
        $drop.on('input', '.org-tree-search', function () {
            const kw = $(this).val().toLowerCase();
            const $tree = $('#tree-in-' + dropId);
            $tree.jstree(true).search(kw);
        });

        /* 載入樹狀資料（只載入一次） */
        let treeLoaded = false;
        function loadTree() {
            if (treeLoaded) return;
            treeLoaded = true;

            const treeId = 'tree-in-' + dropId;
            $drop.html(
                '<input class="org-tree-search form-control form-control-sm mb-1" placeholder="搜尋組織...">' +
                '<div id="' + treeId + '"></div>'
            );

            $.ajax({
                url: '/api/v1/organizations/tree',
                method: 'GET',
                headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') },
                success: function (res) {
                    if (res.status !== 'success') return;
                    const orgs = res.data.organizations || [];
                    const nodes = buildNodes(orgs, '#');

                    // 加一個「全部組織」根節點
                    nodes.unshift({
                        id: '__all__',
                        text: '✦ 全部組織',
                        parent: '#',
                        state: { opened: true }
                    });

                    $('#' + treeId).jstree({
                        core: {
                            data: nodes,
                            themes: { icons: false }
                        },
                        plugins: ['search'],
                        search: {
                            show_only_matches: true,
                            show_only_matches_children: true
                        }
                    }).on('select_node.jstree', function (e, data) {
                        if (data.node.id === '__all__') {
                            $input.val('');
                            $btn.text(placeholder);
                        } else {
                            $input.val(data.node.id);
                            $btn.text(data.node.text);
                        }
                        $drop.hide();
                        // 觸發自定事件讓頁面可以監聽
                        $btn.trigger('org:selected', [data.node.id]);
                    });
                },
                error: function () {
                    $drop.html('<p class="text-danger small p-2">載入失敗</p>');
                }
            });
        }

        /* 遞迴轉換為 jsTree flat 格式 */
        function buildNodes(orgs, parentId) {
            let result = [];
            (orgs || []).forEach(function (org) {
                result.push({
                    id:     org.id,
                    text:   org.name,
                    parent: parentId,
                    state:  { opened: true }
                });
                if (org.children && org.children.length) {
                    result = result.concat(buildNodes(org.children, org.id));
                }
            });
            return result;
        }
    }

    global.initOrgTreePicker = initOrgTreePicker;

})(window);
