CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に従います。

[Unreleased]
------------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-04-17
-------------------

Added
- 初回リリース。KabuSys のコア機能群と CLI ツールを追加。
- パッケージメタ情報
  - バージョン: __version__ = 0.1.0
  - パッケージトップのエクスポート: data, strategy, execution, monitoring

- 設定管理
  - .env 自動読み込み実装（プロジェクトルートに基づく探索: .git または pyproject.toml を基準）。
  - .env パーサ実装: export プレフィックス・クォート文字列（シングル/ダブル）・エスケープ、インラインコメント処理などに対応。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - Settings クラス追加（環境変数取得ラッパー）。
    - DB パス (DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH)
    - Paper trading 用設定 (paper_fill_mode の検証: instant/partial/never/reject)
    - 監視・PID/kill flag 関連設定
    - 環境 (KABUSYS_ENV) とログレベルの検証 (許容値チェック)
    - is_live / is_paper / is_dev のショートカット

- 環境設定ウィザード CLI
  - config_setup.py を追加。対話式で .env を作成・更新可能。
  - シークレット項目はマスク表示。デフォルト・選択肢の提示、キャンセル対策、.env の書き込みロジックを実装。

- 設定検証 CLI
  - validate_config.py を追加。起動前に .env と config/*.yaml の存在/妥当性検査を実行。
  - --strict オプションで警告を FAIL 扱いにできる。
  - PyYAML 未インストール時は YAML 検証をスキップして警告出力。

- 実行系起動スクリプト
  - run_execution.py を追加。
    - プロセス優先度を起動時に "high" に設定（set_process_priority呼び出し）。
    - KABUSYS_ENV が paper_trading の場合、BrokerClientFactory によって MockBrokerClient を利用し、paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - duckdb 接続の初期化（duckdb_path）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て。RiskManager にデフォルト設定を渡し、initial_portfolio_value はブローカーの get_available_cash() を参照。
    - エンジンは別スレッドで実行。data/stop_requested.flag による外部停止に対応。実行中は execution.pid に PID を書き込む想定（pid_file 引数経由）。

- 監視起動スクリプト
  - run_monitoring.py を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視 DB を保持（init_monitoring_db 呼び出し）。
    - SystemMonitor.check_once() をループで呼び出し、例外はログに残して次回ポーリングへ継続。stop flag により安全停止。

- 監視 DB 初期化フック
  - init_monitoring_db 呼び出しを run_monitoring / run_execution の起動フローに組み込み、監視テーブルが存在することを保証（冪等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py
    - select_candidates: スコア順で候補選定（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化（全スコアが 0 の場合は等分にフォールバックして警告）。
  - risk_adjustment.py
    - apply_sector_cap: セクター別上限 (max_sector_pct) による候補除外。売却予定銘柄を除外して計算。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method に応じた株数算出（risk_based / equal / score サポート）。
    - lot_size（単元）考慮、per-stock 上限、aggregate cap（available_cash に合わせたスケーリング）および切り捨て・端数再配分ロジックを実装。
    - cost_buffer を考慮した保守的見積もり。

- リサーチ（因子計算）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュール。
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算。
    - ボラティリティ / 流動性: ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算するクエリを実装。
    - データ不足時は None を返す設計。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows (HIGH_PRIORITY_CLASS 等) と POSIX (nice 値) の差分を吸収して優先度設定を提供。失敗時は警告でスキップ（権限不足等を考慮）。
    - set_cpu_affinity(cpu_count): 指定コア数で CPU affinity を固定する機能を追加（未対応 OS や権限不足時は警告）。
  - utils パッケージ基礎ファイル追加。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime), 注文成功率 (fill_rate), 送信率 (send_rate), リスク却下数, レイテンシ (avg/max/P95)。
    - P95 計算、期間フィルタ（--from / --to）、DB パス解決ロジック（--db / 環境変数 / デフォルト）を実装。
    - PASS/FAIL 基準値を定義（稼働率 >= 99%、fill_rate >= 90% など）し、判定を出力。

Changed
- なし（初回リリースのため、多くは新規追加）。

Fixed
- なし（初回リリース）。

Notes
- 設計方針として、DB 書き込み・発注処理を行う実行系と分析用 DuckDB の責務を明確に分離しています。
- Paper trading は本番 DB と完全分離（paper_trading 用 SQLite）。これにより検証と本番運用の混同を防止します。
- .env のパース実装は柔軟に設計されていますが、完全な shell パーサではないため極端に複雑な構文はサポート外です。
- 一部の機能（例: Engine の詳細実装、BrokerClient 本体、SystemMonitor の内部）は本 CHANGELOG の対象外のモジュール内で実装されています。README やドキュメントを参照してください。