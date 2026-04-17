# CHANGELOG

すべての重要な変更を記録します。本プロジェクトは Keep a Changelog の方針に従って管理しています。

フォーマット:
- 変更はセクション (Added / Changed / Fixed / Deprecated / Removed / Security) に分類しています。
- バージョンはリリース日とともに記載します。

## [Unreleased]
（変更待ち）

## [0.1.0] - 2026-04-17
初回リリース。以下の機能を実装・追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 環境設定および自動読み込み
  - `kabusys.config.Settings`：アプリケーション設定のプロパティラッパーを実装。環境変数（.env）から以下を取得／検証:
    - J-Quants / kabuステーション / LINE のトークン類、DBパス、実行環境（KABUSYS_ENV）、ログレベル等。
    - PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject"）のバリデーション。
    - PAPER_TRADING_SQLITE_PATH、PID/kill flag パス、しきい値（CPU/Memory/Disk）等。
  - 自動 .env ロード機能:
    - プロジェクトルートを `.git` または `pyproject.toml` から検出し、`.env` と `.env.local` を読み込む（OS 環境変数の上書き防止機構あり）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パースは `export KEY=...`、クォート／エスケープ、コメントの扱いに対応。

- 環境設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を作成／更新する機能を提供。
    - 各設定項目のラベル・説明・選択肢・デフォルトを表示。
    - 秘密情報はマスクして表示。保存前の確認プロンプトあり。
    - 生成される `.env` のテンプレートを定義。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前チェックツールを追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック。
    - `config/*.yaml` ファイル存在チェックと（PyYAML がある場合）パース検証。
    - `--strict` モードで警告を FAIL 扱いにできる。

- 実行エントリスクリプト
  - `run_execution.py`：
    - プロセス優先度を起動時に設定（既定は "high"）。
    - KABUSYS_ENV が `paper_trading` の場合、Paper専用の SQLite（`PAPER_TRADING_SQLITE_PATH`、デフォルト: `data/paper_trading.db`）を使用して本番データと分離。
    - BrokerClientFactory を経由してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて `ExecutionEngine` を起動。
    - 停止フラグ（data/stop_requested.flag）および PID 管理をサポート。
    - エンジンは別スレッドで実行され、停止フラグ検知で安全に停止。

- 監視エントリスクリプト
  - `run_monitoring.py`：
    - SystemMonitor のポーリングループを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番用の sqlite_path（`Settings.sqlite_path`）を使用する旨を明示。
    - init_monitoring_db を呼び出して監視用テーブルの存在を保証。
    - 停止フラグ検知、例外ハンドリング、KeyboardInterrupt 対応、接続クローズを実装。

- モニタリング DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` 呼び出しの利用により、監視用テーブルが存在することを保証（冪等）。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority`：
    - `set_process_priority(level)`：Windows（HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）に対応。アクセス権限不足等の例外を許容して安全にスキップ。
    - `set_cpu_affinity(cpu_count)`：指定コア数にプロセスをピン留め。引数チェックと例外処理を実装。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - `select_candidates`：BUY シグナルを score 降順・signal_rank 昇順でソートして上位 N を選択。
    - `calc_equal_weights`：等金額配分。
    - `calc_score_weights`：スコア加重配分（全スコアが 0 の場合は等配分にフォールバックして警告）。
  - `kabusys.portfolio.risk_adjustment`：
    - `apply_sector_cap`：既存保有のセクター別エクスポージャが閾値を超える場合、同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - `calc_regime_multiplier`：市場レジーム ("bull"/"neutral"/"bear") に応じた資金乗数を返す。未知レジームはフォールバック (1.0)。
  - `kabusys.portfolio.position_sizing`：
    - `calc_position_sizes`：allocation_method("risk_based"/"equal"/"score") に応じた発注株数計算。単元（lot_size）で丸め、ポジション上限・総投下上限・コストバッファを考慮したスケーリングロジックを実装。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`：
    - DuckDB の prices_daily テーブルを用いたモメンタム（1/3/6M、MA200乖離）、ボラティリティ（ATR）、流動性指標等の計算関数を実装（純粋関数、DB参照のみ）。
    - 計算窓長やスキャン範囲は定数で管理（例: MA200, ATR=20 日等）。
    - 不足データ時の None 扱いを明確化。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計してレポートを出力する CLI を実装。
    - P95 計算、日付フィルタ、欠損時の N/A 処理、閾値（稼働率 99%、注文成功率 90% 等）に基づく PASS/FAIL 判定を導入。
    - CLI オプション: --from / --to / --db。

- パッケージ初期エクスポート
  - `kabusys.portfolio` で主要関数を __all__ にエクスポート。

### Changed
- （初回リリースのため特段の "変更" はなし。各モジュールは設計方針・挙動を明確にドキュメント化。）

### Fixed
- （初回リリースのため既知のバグ修正履歴なし）

### Notes / その他
- 各 CLI スクリプトはエラー時に丁寧なログ／メッセージを出力し、外部依存（psutil, duckdb, sqlite3, PyYAML 等）に対して存在チェックまたは例外ハンドリングを行う設計になっています。
- セキュリティ注意:
  - `.env` は絶対に Git にコミットしない旨を config_setup の生成ヘッダで明示。
  - 本番環境（KABUSYS_ENV=live）向けの追加チェック（LINE 通知設定や kill flag の自動クリア設定）を validate_config が警告出力。

---

履歴に反映すべき追加情報（実際のリリース日変更、細かな実装差分、将来の変更履歴の分割など）があれば教えてください。必要に応じて各項目をさらに細分化して更新します。