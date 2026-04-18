# CHANGELOG

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このファイルはリポジトリの初回公開リリース（0.1.0）を想定して、コードベースから推測した機能一覧・変更点・注意点を日本語でまとめたものです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-18

初回公開リリース。KabuSys 自動売買フレームワークのコアユーティリティ、設定管理、実行/監視スクリプト、ポートフォリオ構築ロジック、ペーパートレード検証ツールなどを含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを定義: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - .env ファイルおよび環境変数から設定を読み込む `kabusys.config` を追加。
    - プロジェクトルート（.git または pyproject.toml）を探索して自動的に .env / .env.local を読み込む。
    - 自動ロードを無効化するための環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
    - .env パーサは `export KEY=val` 形式とクォート・エスケープ、インラインコメントを考慮して読み込み可能。
    - 必須環境変数取得ヘルパ `_require()` を提供。
  - Settings クラス (`kabusys.config.Settings`) に多数の設定プロパティを追加:
    - J-Quants / kabuステーション / LINE API 関連、DuckDB/SQLite パス、Paper Trading 用パス、監視閾値、PID/kill flag パス、環境種別判定など。
    - `PAPER_FILL_MODE` の妥当性チェック（instant/partial/never/reject）。
    - `KABUSYS_ENV` の妥当性チェック（development/paper_trading/live）。

- 環境設定ウィザード CLI
  - `kabusys.config_setup` を追加。対話式で .env を生成・更新するウィザードを実装。
  - 出力フォーマット・テンプレートを提供し、機密値はマスク表示。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。必須環境変数や config/*.yaml の存在・パース（PyYAML があれば）をチェック。
  - `--strict` フラグで警告を失敗扱いにするオプションを提供。
  - 本番環境 (`KABUSYS_ENV=live`) 向けの安全チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認）を実装。

- 実行・監視起動スクリプト
  - `kabusys.run_execution`（ExecutionEngine 起動スクリプト）
    - プロセス優先度を高く設定して起動（`set_process_priority("high")`）。
    - `KABUSYS_ENV=paper_trading` の場合、paper_trading 専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを生成（paper/live に応じた実装を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで起動。停止フラグ（data/stop_requested.flag）で安全停止。
    - Execution 用 PID ファイル管理（`data/execution.pid`）。
  - `kabusys.run_monitoring`（SystemMonitor ポーリングループ起動スクリプト）
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境（development/paper_trading/live）にかかわらず本番 sqlite_path を使用して監視テーブルを管理。
    - Stop フラグ（プロジェクト data/stop_requested.flag）検出でループを終了。

- 監視 DB 初期化ユーティリティ
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を参照して監視テーブルの冪等初期化を実施（起動時に呼び出し）。

- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）を使ったファイル出力をルートロガーへ設定。
    - ログディレクトリ自動作成、失敗時はコンソール出力のみで継続。
    - デフォルトのログディレクトリは `logs/`、ローテーション保持は 30 日。
    - ログレベル解決順: 明示引数 > 環境変数 `LOG_LEVEL` > "INFO"。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX で差分を吸収して current process の優先度（high/normal/low）を設定。
    - CPU affinity を最初 N コアに固定する `set_cpu_affinity` を提供。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定: `select_candidates`（スコア降順、タイブレークは signal_rank）。
    - 重み計算: `calc_equal_weights`, `calc_score_weights`（スコア全0 の場合は等分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター上限適用: `apply_sector_cap`（既存保有比率を計算して同一セクター超過時は除外）。
    - レジーム乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" に基づく乗数。未知レジームはフォールバック 1.0）。
  - `kabusys.portfolio.position_sizing`
    - 株数算出: `calc_position_sizes`
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）超過時のスケーリングと切捨て/再配分ロジックを実装。
      - cost_buffer による保守的見積りをサポート。

- 研究・ファクター計算
  - `kabusys.research.factor_research`（DuckDB を用いたファクター計算の骨格）
    - モメンタム、移動平均乖離、ATR、流動性等の計算設計。関数は DuckDB 接続と prices_daily/raw_financials テーブルを前提。
    - 実装はファイル内で計算ロジックの骨組みを示している（continued/未完の箇所あり）。

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）を読み、稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出してレポート出力。
    - P95 計算、日付フィルタ（--from/--to）、閾値に基づく PASS/FAIL 判定を備える。
    - 標準的な閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms。

### Changed
- なし（初回リリースのため既存リファクタリング履歴はありません）

### Fixed
- なし（初回リリース）

### Notes / Implementation details / 注意事項
- 環境変数読み込み
  - 自動的に .env を読み込む際、OS 環境変数を保護するため `.env` 読み込み時に既存の OS 環境変数は上書きされません（`.env.local` は override=True で読み込まれるが、protected set により OS 環境変数は上書きされない）。
  - `.env` のパースは一般的なケースをカバーするが、非常に複雑なシェル式や複数行値はサポートしていません。
- ロギング
  - ログファイルの作成に失敗した場合はコンソール（stdout）への出力のみにフォールバック。
- プロセス優先度 / CPU affinity
  - 権限不足（Linux の nice 値の制御や Windows 権限）や未対応プラットフォームでは警告を出し、安全にスキップします。
- データベース
  - Monitoring は常に `Settings.sqlite_path`（デフォルト `data/monitoring.db`）を使用して監視データを保存します。Execution は `KABUSYS_ENV=paper_trading` の場合に限り `paper_sqlite_path`（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離します。
- Paper Trading
  - Paper モードでは MockBroker 相当の実装を使用することを想定（`BrokerClientFactory` が生成）。ペーパーデータは専用 DB に蓄積されるため本番とは隔離されます。
- 未実装 / TODO
  - `kabusys.research.factor_research` は設計の骨格を含むが、ファイル末尾で実装が途切れている箇所があります（追加実装が必要）。
  - position_sizing の価格フォールバック（価格が欠損した場合に前日終値や取得原価でフォールバックするなど）は未実装だが TODO コメントあり。

### Upgrade notes
- 既存の環境で導入する場合:
  - 必須環境変数（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）を `.env` に設定してください。
  - 本番運用時は `KABUSYS_ENV=live` を設定し、LINE 通知設定（`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`）を確認してください。
  - `.env` を生成するには `python -m kabusys.config_setup` を利用できます。生成後は `python -m kabusys.validate_config` で検証してください。

---

今後のリリースでは以下を想定しています:
- factor_research の完成（各ファクター計算・正規化の実装）
- ExecutionEngine / BrokerClient の詳細実装とテスト
- 監視・アラートの強化（LINE 通知連携、自動復旧 / 再起動機能）
- 単体テストおよび CI 設定の追加

もし CHANGELOG に加えてリリースノートや導入手順（README や quickstart）が必要であれば、用途に合わせて別途作成します。