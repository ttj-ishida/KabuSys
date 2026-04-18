# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 初期リリースとして以下の主要機能・モジュールを実装しました。
  - 設定管理
    - 自動 .env ロード機能を実装（.env と .env.local、OS 環境変数の保護機構付き）。
    - .env パーサーの強化:
      - `export KEY=...` 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなどを考慮。
      - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - Settings クラスを提供し、環境変数をプロパティとして安全に取得可能に（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などの有効値チェック）を実装。

  - 環境設定ウィザード
    - `kabusys.config_setup`（python -m kabusys.config_setup）を実装。対話式で .env を初期作成・更新可能。
    - 機密値は入力時にマスク、生成される .env ファイルはコメント付きテンプレート形式。

  - 設定検証 CLI
    - `kabusys.validate_config`（python -m kabusys.validate_config）を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パス親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML 利用時）、本番（live）向けガードチェックを提供。
    - `--strict` オプションで警告を失敗扱いにできる。

  - 実行関連スクリプト
    - run_execution.py:
      - ExecutionEngine 起動スクリプトを実装。
      - `KABUSYS_ENV=paper_trading` の場合、paper trading 用の専用 SQLite DB（`PAPER_TRADING_SQLITE_PATH` / default `data/paper_trading.db`）を使用し、本番 DB と分離。
      - BrokerClientFactory を用いたブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動と停止フラグ監視（data/execution.pid、data/stop_requested.flag）を実装。
      - RiskManager の初期設定に `initial_portfolio_value = broker.get_available_cash()` を使用。

    - run_monitoring.py:
      - SystemMonitor ポーリングループ起動スクリプトを実装。
      - 監視は環境にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用して監視テーブルを管理。
      - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
      - 停止フラグ（data/stop_requested.flag）検知・ graceful shutdown を実装。

  - 監視/レポート/ツール
    - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）を追加。
      - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し、PASS/FAIL 判定を実施。
      - CLI 引数 `--from` / `--to` / `--db` をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` に対応。
      - デフォルト合格基準（定数）を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。

  - ポートフォリオ構築（純粋関数）
    - `kabusys.portfolio` パッケージを実装。
      - portfolio_builder:
        - select_candidates: スコア降順・タイブレークロジックで候補選択。
        - calc_equal_weights / calc_score_weights（全スコア 0 の場合は等分配にフォールバック）。
      - risk_adjustment:
        - apply_sector_cap: セクター集中制限（既存保有のセクター比率が閾値を超える場合に新規候補を除外）。"unknown" セクターは制限適用外。
        - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームは警告して 1.0 でフォールバック）。
      - position_sizing:
        - calc_position_sizes: risk_based / equal / score の配分方式に対応。単元（lot_size）丸め、ポジション上限・aggregate cap のスケールダウン、cost_buffer を考慮した保守的見積もり、残差を使った追加配分ロジックを実装。

  - ユーティリティ
    - logging_setup:
      - 統一的なログ設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
      - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - process_priority:
      - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを実装（psutil ベース、Windows/POSIX の差分吸収、権限不足時は警告してスキップ）。

  - 研究用モジュール（着手）
    - research/factor_research.py の基盤を追加（モメンタム等のファクター計算のための定数・calc_momentum の骨格を導入）。DuckDB を用いた prices_daily / raw_financials 参照設計。

### 変更 (Changed)
- なし（初期リリース）。

### 修正 (Fixed)
- なし（初期リリース）。

### 破壊的変更（注意点 / Breaking Changes）
- Settings クラスで環境変数の値検証を行うため、無効な値や欠落している必須環境変数により早期に例外が発生する可能性があります。起動前に `python -m kabusys.validate_config` で確認してください。
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings の各プロパティ参照時に未設定だと ValueError を送出）。
  - `KABUSYS_ENV` は "development" / "paper_trading" / "live" のいずれかである必要があります（それ以外は ValueError）。
  - `PAPER_FILL_MODE` は "instant" | "partial" | "never" | "reject" のいずれかである必要があります（無効値は ValueError）。

### ドキュメント / 使用メモ (Notes)
- 実行スクリプト:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper 投資検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 重要な環境変数（主なもの）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (default: development)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_LEVEL (default: INFO)
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔 / default: 60 秒)
  - PAPER_FILL_MODE (paper_trading の約定挙動 / default: instant)
  - KILL_FLAG_CLEAR_ON_START (0/1、default: 0)
  - LOG_DIR (ログ出力先ディレクトリ、default: logs/)
  - PAPER_TRADING_SQLITE_PATH は paper_trading モードの専用 DB を指す（本番 DB と分離されます）。

- ファイルベースの制御:
  - 停止フラグ: project_root/data/stop_requested.flag（存在すると監視/実行が停止）
  - PID ファイル: data/execution.pid（ExecutionEngine 用、Settings.pid_file_path で解決）
  - kill.flag: Settings.kill_flag_path（Kill Switch 管理）

- ログ:
  - デフォルトで stdout 出力とファイル出力を行います。ファイルは日次ローテーションで 30 日保持。

### 今後の予定 / TODO
- research/factor_research のファクター計算関数群の完成（現状はモメンタムの骨格を実装済み）。
- ExecutionEngine / broker の詳細実装およびテストカバレッジ拡充。
- 単体テスト、CI 環境での .env 自動ロード制御（KABUSYS_DISABLE_AUTO_ENV_LOAD）に関するドキュメント強化。
- 銘柄毎の lot_size マスタ対応（position_sizing の拡張）。

---

このリリースに関する質問や不明点があれば教えてください。必要であれば各機能ごとの使用例や移行手順（例: .env の初期作成手順）を追記します。