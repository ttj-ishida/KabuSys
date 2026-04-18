CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。
過去のリリースや主要な変更点を日本語でまとめています。  
（内容はソースコードから推測して記載しています）

フォーマット:
- Unreleased: 今後の変更（空欄・プレースホルダ）
- 各リリース: 追加（Added）、変更（Changed）、修正（Fixed）、除去（Removed）などに分類

Unreleased
----------
- 今後の変更をここに追加してください。

[0.1.0] - 2026-04-18
-------------------
Added
- 基本アプリケーション構成を実装（初期リリース）。
  - パッケージ情報: kabusys（__version__ = "0.1.0"）
- 設定・環境変数管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - 高機能な .env パーサを実装: export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント考慮など。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスにより環境変数をラップ：J-Quants / kabu API / LINE / DB パス / 監視閾値 等のプロパティを提供。
  - PAPER_FILL_MODE の値検証（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH のサポート。
- 設定支援 CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新するツールを追加。
  - validate_config: .env と config/*.yaml の検証ツールを追加。--strict オプションで警告も失敗扱いにできる。
    - PyYAML 未インストール時のフォールバック（YAML 検証スキップ）を実装。
- 実行系 / 監視系 スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 専用 SQLite DB を使用（本番 DB と分離）。
    - BrokerClientFactory により本番/モックを切り替え可能。
    - Engine 起動時の PID ファイル管理と停止フラグ (data/stop_requested.flag) をサポート。スレッドでエンジンを実行し、安全停止を実装。
    - RiskManager/RiskConfig, Reconciler, OrderManager, OrderRepository の組み立てを行う。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する挙動を実装。
    - stop flag ファイル検知で安全にループ終了。
- ロギング・運用ユーティリティ
  - setup_logging: stdout 出力の StreamHandler と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR 環境変数 / 引数でログ保存先を指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラの flush/close と置換を行い二重設定を防止。
  - process_priority: Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定を提供（psutil ベース）。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: シグナルのスコアで上位 N 件選択（同点時に signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用（既存保有のセクター比率が上限を超える場合、新規候補を除外）。売却予定銘柄を除外してエクスポージャー計算。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは 1.0 でフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の配分方式を実装。損切り率・リスク率に基づく算出、単元株（lot_size）丸め、per-stock 上限および aggregate cap によるスケールダウンを実施。cost_buffer を用いて手数料・スリッページを保守的に見積もる。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、レイテンシ（平均・最大・P95）などを集計し PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db、--db オプションで上書き可能。
    - P95 計算、日付フィルタ（ISO8601 UTC 変換）を実装。
- リサーチ（ファクター計算）
  - research.factor_research: DuckDB 接続を受けてモメンタム / ボラティリティ / ボラティリティなどのファクター算出を行う設計を開始（prices_daily / raw_financials を参照）。（未完部分あり）
- DB 周り
  - duckdb と sqlite の接続管理を各起動処理で確実に open/close するよう実装。
  - 監視用テーブルの初期化処理（init_monitoring_db）を起動時に呼び出し、冪等にテーブル存在を保証。

Changed
- なし（初回リリース）

Fixed
- .env ファイル読み込みでの I/O エラーを warnings.warn で通知し安全に継続するように実装。
- logging ハンドラ作成に失敗する場合でもコンソール出力にフォールバックするように実装（ファイル出力失敗時の堅牢化）。
- ProcessPriority / CPU affinity の失敗時に警告を出して処理を続行する堅牢化（権限不足や未対応環境対策）。
- run_monitoring の MONITOR_POLL_INTERVAL に不正値が渡された場合にデフォルトへフォールバックし、警告ログを出すように実装。

Removed
- なし（初回リリース）

注意事項 / マイグレーションノート
- .env は絶対に Git にコミットしないでください（config_setup にも注意書きあり）。
- Paper Trading は本番 SQLite DB と完全分離されています。KABUSYS_ENV=paper_trading を使用することで paper_trading.db にデータを書きます。
- 監視（run_monitoring）は「環境にかかわらず本番 sqlite_path を使用する」挙動になっています。テスト時は SQLITE_PATH の設定に注意してください。
- MONITOR_POLL_INTERVAL は秒数を指定する環境変数です。1 以上の整数で指定してください（不正な値は 60 秒にフォールバック）。
- サービスの停止はプロジェクトルート/data/stop_requested.flag によるフラグ検知で行います。Kill/停止フラグ関連の挙動は validate_config と Settings で制御できます（KILL_FLAG_CLEAR_ON_START 等）。

補足
- 上記はソースコードを解析して推測した変更履歴です。実際のコミット履歴・意図と異なる場合があります。必要であれば各モジュール（特に未完の research.factor_research）の実装状況に合わせて調整してください。