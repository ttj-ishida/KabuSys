# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョン: 0.1.0 (初回公開)

## [Unreleased]

### Added
- run_monitoring 起動スクリプトを追加
  - SystemMonitor のポーリングループを提供（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可、デフォルト 60 秒）。
  - 監視は環境 (KABUSYS_ENV) にかかわらず production の sqlite_path を使用する設計。
  - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。
  - duckdb と sqlite の接続初期化、監視用 DB スキーマの初期化処理呼び出し。

- run_execution 起動スクリプトを追加
  - ExecutionEngine を起動して注文実行セッションをバックグラウンドスレッドで実行。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て。
  - 停止フラグ（data/stop_requested.flag）および PID 管理（data/execution.pid）による制御。

- 設定管理モジュール (kabusys.config) を追加
  - .env 自動読み込み機能（プロジェクトルート検出に .git または pyproject.toml を使用）。
  - .env ファイルの堅牢なパース実装（export プレフィックス、引用符・エスケープ、行内コメント処理、保護付き上書きオプション）。
  - 環境変数取得ヘルパ（必須変数検証）、各種パス・閾値・フラグのプロパティ化（duckdb/sqlite/paper_sqlite/ログ・監視閾値等）。
  - KABUSYS_ENV / LOG_LEVEL の検証と既定値処理。

- 設定検証 CLI (kabusys.validate_config) を追加
  - .env と config/*.yaml の起動前検証。必須環境変数チェック、パス存在チェック、YAML パース検証（PyYAML 未インストール時は警告スキップ）。
  - KABUSYS_ENV=live 用の追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START 設定の警告）。
  - --strict オプションで警告も失敗扱いにできる。

- 環境設定ウィザード CLI (kabusys.config_setup) を追加
  - インタラクティブに .env を作成 / 更新するウィザード。シークレット入力のマスク、選択肢・デフォルト対応、保存前確認などを提供。
  - デフォルトで生成される .env テンプレートのフォーマット関数を実装。

- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）
  - portfolio_builder: シグナルの候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全0 の場合は等配分にフォールバックして警告。
  - risk_adjustment: セクター集中上限 (apply_sector_cap) と市場レジーム乗数 (calc_regime_multiplier) を実装。unknown セクターは上限適用外、未知レジームはフォールバックで 1.0 を返す（警告）。
  - position_sizing: allocation_method (risk_based / equal / score) に基づく株数算出を実装。単元株（lot_size）単位で丸め、per-stock 上限・aggregate 上限（available_cash）を考慮したスケールダウン処理を実装。cost_buffer による保守的コスト見積りと残余キャッシュを利用した端数配分ロジックを備える。

- 共通ユーティリティを追加（kabusys.utils）
  - logging_setup: stdout ストリームハンドラと日次ローテーション (TimedRotatingFileHandler) を持つログ設定ユーティリティ。ログディレクトリ自動作成、既存ハンドラのクリア、環境変数/引数からのログレベル・ディレクトリ解決をサポート。
  - process_priority: Windows / POSIX を抽象化したプロセス優先度設定と CPU affinity 設定ユーティリティ。アクセス拒否等の例外を安全にハンドリングして警告出力。

- 研究・ツール群を追加
  - research.factor_research: DuckDB の prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計で着手（モジュール構成と定数、calc_momentum の骨組みを含む。実装途中）。
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）などを SQLite の監視テーブルから集計し PASS/FAIL 判定を出力。閾値はソースに定義（稼働率 99% 等）。日時フィルタ、--db オプション、環境変数経由の DB パス解決をサポート。

### Changed
- ルートパッケージメタ情報を追加 (kabusys.__init__.py) として __version__ = "0.1.0" を設定。

### Fixed
- 多くの I/O / OS 呼び出しで失敗時に警告出力して処理を継続する設計（ログディレクトリ作成失敗や psutil による権限不足等を安全に扱う改善）。

### Documentation
- 各モジュールに日本語ドキュメント文字列（docstring）を充実させ、設計意図・使用例・引数説明・注意点（TODO）を明記。

## [0.1.0] - 2026-04-20

初回公開リリース。上記の機能群をまとめてリリース。

- 主な追加機能:
  - 監視 (monitoring) と実行エンジン (execution) の起動スクリプト
  - 環境設定管理 (.env 自動読み込み / ウィザード / 検証 CLI)
  - ポートフォリオ構築・ポジションサイジング・リスク調整ロジック
  - ロギング・プロセス優先度ユーティリティ
  - Paper Trading 検証レポート生成ツール
  - 研究用ファクタ計算モジュール（部分実装）

- 既知の注意点（Breaking / Behavioral）
  - run_monitoring は KABUSYS_ENV の値にかかわらず production 用の sqlite_path（Settings.sqlite_path）を使用する設計です。意図的な分離が必要な場合は設定を変更してください。
  - process_priority / cpu_affinity の機能はプラットフォームによって利用可否・挙動が異なります。権限不足時は警告を出してスキップします。
  - .env 自動読み込みはデフォルトで有効。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 既知の問題・今後の改善予定
- research/factor_research モジュールは未完（calc_momentum の途中で終了）。完全実装が必要。
- risk_adjustment.apply_sector_cap:
  - price が欠損した場合のエクスポージャー推定が過小見積りになる可能性あり（TODO コメントあり）。前日終値や取得原価でのフォールバック実装を検討。
- position_sizing:
  - lot_size が全銘柄共通前提になっている（将来的に銘柄毎 lot_map をサポートする予定）。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイル出力が無効化されコンソールのみの出力になる点を明確にしている。

---

著者注: 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートとして使用する場合は、リリース日・バージョン・重要な API 変更点などをプロジェクトの実際の運用状況に合わせて確認・編集してください。