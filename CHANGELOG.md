CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（なし）

v0.1.0 - 2026-04-20
-------------------

Added
- 初回リリース。KabuSys のコア機能を実装しました。
  - 環境設定 / 起動関連
    - Settings クラス（kabusys.config）を実装。環境変数経由で各種設定を取得。
      - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL 等を検証。
      - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等の Path を提供。
      - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
      - pid/kill フラグ関連設定を提供。
    - 自動 .env ロード機能を実装（.env, .env.local）。OS 環境変数は保護され上書きされない。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - 対話式環境設定ウィザード（kabusys.config_setup）を追加。
      - .env の生成 / 更新を支援。シークレット項目はマスク表示。
      - .env の読み書きロジック、既存値の取り扱い、確認プロンプトを実装。
    - 設定検証 CLI（kabusys.validate_config）を追加。
      - 必須環境変数の検出、KABUSYS_ENV や LOG_LEVEL のチェック、DB パス・config/*.yaml の存在確認。
      - --strict オプションで警告を FAIL 扱いにできる。
      - PyYAML が未インストール時は YAML の内容検証をスキップして警告を出力。

  - 起動スクリプト / ランタイム
    - 実行エンジン起動スクリプト run_execution を追加。
      - 起動時にプロセス優先度を "high" に設定（kabusys.utils.process_priority）。
      - KABUSYS_ENV=paper_trading 時は paper 用 DB（data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient を利用）。
      - ExecutionEngine / OrderManager / OrderRepository / RiskManager / Reconciler の組み立てと実行ループを実装。停止フラグ（data/stop_requested.flag）検出で安全に停止。
      - 起動時に監視テーブルの存在を保証（init_monitoring_db を呼び出し冪等に作成）。
      - PID ファイルの取り扱いを実装（data/execution.pid）。
    - 監視ループ起動スクリプト run_monitoring を追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトを使用）。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
      - 停止フラグ（data/stop_requested.flag）検出でループ終了。
      - check_once() 実行時の例外はログに記録して次ポーリングに進む耐障害性を確保。
    - ログ設定ユーティリティ（kabusys.utils.logging_setup）を追加。
      - コンソール stdout（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。
      - LOG_DIR / LOG_LEVEL の解決、既存ハンドラの再設定、ログディレクトリ作成失敗時のフォールバック（ファイル出力を無効化して stdout のみ）を実装。
      - 日次ローテーション・30 日分保持。
    - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加。
      - Windows / POSIX を吸収する set_process_priority を実装（psutil を利用）。
      - set_cpu_affinity を実装（指定コア数でプロセスをピン留め）。
      - 権限不足や未対応環境での失敗は警告として処理。

  - ポートフォリオ構築（Portfolio）
    - portfolio_builder
      - select_candidates: BUY シグナルからスコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。全スコア 0 の場合は等金額にフォールバックして警告。
    - risk_adjustment
      - apply_sector_cap: セクター集中リスクの除外ロジック。既存保有をセクター別に集計して上限を超えるセクターの候補銘柄を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
    - position_sizing
      - calc_position_sizes: weight / candidates / risk_based に対応した発注株数計算を実装。
      - 単元株（lot_size）で丸め、1銘柄上限・aggregate 上限（available_cash）を適用。
      - cost_buffer を加味した保守的見積もりと、総コストが available_cash を超えた場合のスケールダウン（小数端数を基に優先配分）を実装。
      - 価格欠損時のスキップやログ出力を行う。

  - 研究 / ファクター（research）
    - factor_research モジュールにモメンタム等のファクター計算基盤を実装（DuckDB 接続を受け prices_daily / raw_financials を参照して計算）。
      - mom_1m / mom_3m / mom_6m / ma200_dev 等の算出方針を記載（実装の一部にスキャン範囲や定数定義あり）。
      - （注）ファイルは途中までの実装・スケルトンを含む。

  - ツール
    - tools/paper_verification_report を追加。
      - Paper Trading 用の検証レポートを生成する CLI。
      - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出して PASS/FAIL を判定する閾値を定義。
      - --from / --to / --db オプションをサポートし、PAPER_TRADING_SQLITE_PATH 環境変数を利用可能。
      - SQL クエリと P95 計算ロジック（_p95）を実装。DB のテーブル欠如時は N/A 扱いで安全に処理。

  - パッケージ情報
    - パッケージバージョンを __version__ = "0.1.0" として定義。
    - portfolio モジュールのエクスポートを整理。

Fixed
- 初期リリースにつき修正履歴は無し。

Changed
- 初回リリースにつき変更履歴は無し。

Removed
- 初回リリースにつき削除履歴は無し。

Deprecated
- 初回リリースにつき非推奨項目は無し。

Security
- 初回リリースにつきセキュリティ項目は無し。

Notes / 実装上の重要点（運用時の注意）
- run_monitoring は監視用 DB として常に Settings.sqlite_path を使用します（環境に関わらず本番監視 DB を参照する設計）。
- run_execution は paper_trading モード時に PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）を用い、本番 DB と分離します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。プロジェクトルートが特定できない場合は自動ロードをスキップします。
- ログディレクトリ作成やプロセス優先度設定は権限不足や未対応環境で失敗する可能性がありますが、失敗時は警告を出してフェイルセーフ（処理継続）します。
- calc_position_sizes 等の数値ロジックは丸めや端数配分の動作により微妙な差異が生じます。運用前に unit test / スモークテストによる検証を推奨します。

データベース / ファイルパスのデフォルト
- DuckDB デフォルト: data/kabusys.duckdb
- SQLite（監視）デフォルト: data/monitoring.db
- Paper Trading SQLite デフォルト: data/paper_trading.db
- ログディレクトリデフォルト: logs/
- 停止フラグ・PID 等: data/stop_requested.flag, data/execution.pid など

--- 
（今後のリリースではバグ修正・機能追加・API 変更をここに記載します）