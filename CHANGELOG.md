# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

注: このリリースはコードベースの初回公開に相当する変更点をまとめたものです。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-18

### Added
- 初回リリースを追加。
- コア設定/環境管理:
  - 環境変数読み込み・管理モジュール `kabusys.config` を追加。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行うため、CWD に依存しない自動 .env 読み込みを実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能）。
    - .env パーサは `export KEY=val`、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントを考慮。
    - `Settings` クラスを提供。多くのプロパティを通じて設定値（DB パス、API トークン、監視閾値、環境種別など）を安全に取得可能。
    - `PAPER_FILL_MODE` の妥当性チェック（`instant|partial|never|reject`）を実装。
- 設定操作 CLI:
  - `kabusys.config_setup` — 対話式ウィザードで `.env` を初期作成 / 更新可能。シークレット値は表示マスク、項目ごとの説明・デフォルト提示。
  - `kabusys.validate_config` — .env および `config/*.yaml` の存在・基本妥当性検証 CLI を追加。`--strict` オプションで警告も失敗扱いに可能。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パス親ディレクトリの存在確認、YAML のパース検証（PyYAML があれば実施）、本番環境用の追加ガードを実装。
- 実行/監視エントリポイント:
  - `kabusys.run_execution` — ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper-trading SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と分離（`MockBrokerClient` を使用する想定）。
    - `BrokerClientFactory` を介してブローカークライアントを生成。
    - `OrderRepository` / `OrderManager` / `RiskManager` / `Reconciler` を組み立て、`ExecutionEngine` をスレッドで起動。停止フラグ (`data/stop_requested.flag`) と PID ファイル (`data/execution.pid`) を扱う。
    - `RiskConfig` の初期値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, max_drawdown=0.20）が設定され、初期ポートフォリオ値はブローカーの取得値を利用。
  - `kabusys.run_monitoring` — SystemMonitor ポーリングループ起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視は（KABUSYS_ENV に関わらず）本番用 `sqlite_path` を使用して監視テーブルを初期化する（`init_monitoring_db`）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 停止フラグファイル検出でループを終了し、例外発生時もログ出力後に次ポーリングへ継続。
- 監視 / DB:
  - `kabusys.monitoring.monitoring_db`（参照される初期化関数 `init_monitoring_db` を呼び出す箇所を含む）を利用し、監視テーブルを冪等に初期化。
  - DuckDB 接続を用いるためのデフォルトパスを設定（`DUCKDB_PATH`）。
- ロギング / プロセス管理ユーティリティ:
  - `kabusys.utils.logging_setup` を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日毎ローテート、30 日分保持）を設定。
    - ログディレクトリ/レベルの解決順を定義（引数 > 環境変数 > デフォルト）。
    - 既存ハンドラの二重登録を防止するため、一旦 flush/close してから再設定する。
    - ログファイル出力に失敗した場合はコンソール出力のみで継続。
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセスの優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。
    - CPU affinity 固定関数 `set_cpu_affinity` を実装（core 数指定、psutil 利用）。
    - 設定失敗時は警告ログを出してスキップ。
- ポートフォリオ構築モジュール:
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 `calc_equal_weights`。
    - スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等分配へフォールバック＆警告）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 `apply_sector_cap`（既存保有を考慮して特定セクターを除外。unknown セクターは制限対象外）。
    - 市場レジーム乗数 `calc_regime_multiplier`（'bull'=1.0, 'neutral'=0.7, 'bear'=0.3。未知レジームは警告して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - `calc_position_sizes` を実装。複数配分方式をサポート:
      - "risk_based": 損切り幅・許容リスク率から株数算出
      - "equal"/"score": 重みを用いた配分
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積）考慮、スケールダウン後の残差配分アルゴリズムを実装。
- リサーチ:
  - `kabusys.research.factor_research` にてモメンタム/Value/Volatility/Liquidity 等のファクター計算基盤を追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。（ファイル末尾で計算関数の実装が続くが本 CHANGELOG では主要方針を記載）
- ツール:
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）から統計を抽出し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計・判定してテキストレポートを出力。閾値はソース内定義（例: 稼働率 >= 99%、P95 <= 200 ms 等）。
- パッケージ情報:
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- 機密情報（API トークン等）は `.env` に保存する前提。`config_setup` での表示はシークレットはマスク。

---

注記:
- ここに記載した仕様や既知の挙動（例: MONITOR が常に本番 `sqlite_path` を使用する点、ログが stdout を使用する点、.env の詳細なパース挙動など）はソースコードからの推測に基づきまとめています。実運用前に `python -m kabusys.validate_config` や `python -m kabusys.config_setup` を使って環境を整備してください。