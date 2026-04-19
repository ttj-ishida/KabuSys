# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  

リリースのポリシー: バグ修正は Fixed、新機能は Added、動作変更は Changed に記載します。

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ初期実装（KabuSys v0.1.0）。
  - パッケージ情報: `__version__ = "0.1.0"`。
- 実行用スクリプト / デーモン起動ロジックを実装
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループ終了。
    - Monitoring は環境にかかわらず本番用の SQLite (settings.sqlite_path) を使用。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 DB（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - 停止フラグ・PID ファイル管理・バックグラウンドスレッドでのセッション実行をサポート。
- 設定・環境管理
  - Settings クラスを実装（`kabusys.config`）
    - 多数のプロパティ経由で環境変数を取得（DB パス、API トークン、運用環境フラグ、しきい値等）。
    - `PAPER_FILL_MODE` の検証、有効値制約を実装。
    - `is_live`, `is_paper`, `is_dev` の便利プロパティを追加。
  - 自動 .env ロード機構を実装（プロジェクトルート検出）。
    - 読み込み順: OS 環境 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
    - .env パーサは export プレフィックス、クォート（エスケープ含む）、インラインコメントの取り扱いに対応。
- 設定関連 CLI
  - `kabusys.config_setup` — 対話式ウィザードで .env の初期作成/更新を支援。
    - 入力プロンプト、デフォルト/既存値再利用、シークレット項目のマスク表示、保存確認など。
  - `kabusys.validate_config` — 起動前の設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、`config/*.yaml` の存在と（PyYAML があれば）パース検証。
    - `--strict` オプションで警告も失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純函数）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア重み（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）。
    - 未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）
    - allocation_method: `risk_based` / `equal` / `score` をサポート。
    - lot_size 単位で丸め、1銘柄上限・aggregate cap（利用可能現金）超過時のスケーリング処理、cost_buffer（手数料/スリッページ見積）を考慮した計算を実装。
    - スケールダウン時は残差（fraction）に基づく追加配分ロジックを実装して再現性を確保。
- ユーティリティ
  - logging_setup: 統一的ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）のファイルハンドラを設定。
    - LOG_DIR / LOG_LEVEL の優先解決、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - 出力フォーマット・タイムスタンプは ISO ライク形式。
  - process_priority: プロセス優先度 & CPU affinity 設定ユーティリティを追加。
    - Windows（psutil の定数）と POSIX（nice 値）を吸収してプラットフォーム非依存の API を提供。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を実装。権限不足等は警告でスキップ。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - デフォルト thresholds を定義（例: 稼働率 >= 99%、P95 <= 200ms など）。
    - 日付範囲フィルタ（--from / --to）、DB パス指定（--db）をサポート。
- 研究用モジュール（着手）
  - research.factor_research: DuckDB を使ったファクター計算モジュールの骨格を追加（モメンタム等の定義・定数を含む）。実装は継続中（ファイル末尾が途中で切れている状態）。

### Changed
- 初期リリースにつき既存コード構成の整理・エクスポートを定義。
  - `kabusys.__init__` に主要サブパッケージを列挙（data, strategy, execution, monitoring）。
  - `kabusys.portfolio.__init__` でポートフォリオ関連関数を公開するよう整理。

### Fixed
- 実務での運用上の堅牢化をいくつか実装
  - .env 読み込みでファイルオープン失敗時に警告を出して続行するように修正（例: 権限エラー）。
  - logging_setup でログディレクトリ作成失敗時にファイルハンドラ追加を回避し、標準出力のみでログを残すように変更。
  - process_priority や set_cpu_affinity の呼び出しで権限不足や未サポート OS の場合に例外を投げず警告でスキップするように変更。

### Known issues / Notes
- apply_sector_cap のエクスポージャ計算で price が欠損（0.0）だと過少見積りになる可能性があり、将来的に前日終値や取得原価をフォールバック価格として使う拡張を検討中（TODO コメントあり）。
- research.factor_research モジュールは途中実装（ファイル末尾が切れている）。将来的に DuckDB クエリと計算ロジックを完成させる予定。
- run_monitoring は Monitoring 用 DB を環境に依存せず本番 sqlite_path を使用する仕様：テスト環境で監視 DB を分離したい場合は運用手順で DB パスを変更する必要あり。
- ExecutionEngine のブローカーファクトリは `BrokerClientFactory.create(settings)` を使って Mock/Real を切り替えるが、実際の Broker 実装や接続詳細は別モジュールに依存。

### Security
- 本リポジトリでは `.env` を Git 管理下に含めないよう強く注意する旨を config_setup のヘッダに記述（.env を絶対にコミットしない指示を追加）。

---

今後の予定:
- research.factor_research の実装完了とテスト追加。
- ExecutionEngine / Monitoring の統合テスト強化、DI やモックを使った単体テスト整備。
- ポートフォリオ構築・発注ロジックの追加最適化（銘柄別 lot_size 対応、価格フォールバック改善など）。