# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のリリース: 0.1.0

## [0.1.0] - 2026-04-18

### 追加
- 基本アプリケーション初期実装を追加。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。

- 実行用スクリプト / デーモン
  - run_monitoring: システム監視ポーリングループの起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒）。
    - 停止フラグ: `data/stop_requested.flag` を検知して安全に終了。
    - 監視コンポーネントは `monitoring_db` の初期化および `SystemMonitor.check_once()` 呼び出しで動作。
    - Monitoring は環境にかかわらず本番の `sqlite_path` を使用する設計。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、Paper Trading 用 DB（`data/paper_trading.db` など）に完全分離して記録。
    - 実行中は `data/execution.pid` に PID を管理し、`data/stop_requested.flag` による停止制御をサポート。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境関連
  - `kabusys.config.Settings` クラスを追加。
    - 各種環境変数をプロパティとして提供（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_FILL_MODE` 等）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の値検証を実装。
    - Paper Trading 用 DB パスや PID / kill flag のパスなどを標準化。
    - `PAPER_FILL_MODE` の検証（"instant" / "partial" / "never" / "reject"）。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - 優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。

- 設定支援 CLI
  - config_setup: 対話式ウィザードで `.env` を作成 / 更新する CLI を追加。
    - J-Quants / kabu API のトークンなど必須項目を対話形式で入力可能。
    - 既存値の読み込み・マスク表示・デフォルトサポート。
  - validate_config: 起動前検証 CLI を追加。
    - 必須環境変数の存在確認、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けの追加ガードチェック等を実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコアとランクに基づく候補選定。
    - calc_equal_weights / calc_score_weights: 等比率およびスコア加重の重み計算（スコア全て 0 のときは等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮して当日の売却予定を除外可）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 対応、未知値はフォールバックと警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数決定（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）での丸め、per-position 上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料/スリッページ見積り）対応。

- 研究 / ファクター計算
  - research.factor_research: Momentum 等のファクター計算モジュールの骨格を追加（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。（モジュールは計算ロジックを含むが一部未完の箇所あり）

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。
    - 閾値はソース内で定義（例: 稼働率 >= 99%、P95 <= 200 ms 等）。
    - CLI 引数で期間指定（--from / --to）と DB パス指定（--db）をサポート。

- ロギング / プロセス運用ユーティリティ
  - utils.logging_setup:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）を設定する共通関数 `setup_logging` を追加。
    - ログディレクトリ自動作成処理、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト "INFO"。
  - utils.process_priority:
    - `set_process_priority(level: "high"|"normal"|"low")` を追加。Windows / POSIX 系で適切に nice 値 / priority を設定し、失敗時は警告を出してスキップ。
    - `set_cpu_affinity(cpu_count)` を追加（最初の N コアに固定、権限や未サポート環境では警告を出してスキップ）。

- DB 接続周り
  - run_* スクリプトで SQLite3 と DuckDB 接続の初期化を標準化（duckdb 用パスは Settings.duckdb_path）。
  - 監視用テーブルの初期化関数 `init_monitoring_db` を呼び出し（冪等）。

### 変更
- .env パーサの強化（kabusys.config）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行末コメント処理の改善。
  - .env 読み込み時の上書き挙動を `override` と `protected`（OS 環境変数保護）で制御。

- ログ出力先は stdout を優先（cron 等で stdout/stderr を一本化しやすくするため）。

### 修正
- run_monitoring のポーリング間隔取得で無効値が与えられた場合のフォールバック処理を追加（0 以下や非整数は警告を出してデフォルト 60 秒を使用）。

### 注意（設計上の重要点）
- Monitoring は環境変数 `KABUSYS_ENV` にかかわらず本番用 `SQLITE_PATH` を使用する意図的な設計になっています。Paper Trading を完全分離したい場合は Execution 側で `paper_sqlite_path` を使用するか、環境設定で `SQLITE_PATH` を分けてください。
- `PAPER_FILL_MODE` 等の設定値に対して厳格なバリデーションを行うため、誤った値を設定すると起動時に例外が発生します。
- 一部モジュール（例: research.factor_research）には未完成の箇所があります。今後追加で実装・テストを行う予定です。

---

今後の予定（非網羅）
- factor_research の残り実装とテストカバレッジ強化
- ExecutionEngine / RiskManager / Broker クライアントの詳細なテストとドキュメント追加
- CI による設定検証・Lint・型チェックの導入

もし CHANGELOG に追記してほしい点（たとえば日付修正、追加の説明やセクション分け）があれば教えてください。