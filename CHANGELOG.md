CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

Added
- 実行/監視用のエントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。環境変数 KABUSYS_ENV が `paper_trading` の場合はペーパー用 DB（data/paper_trading.db）を使用し MockBrokerClient を用いる（本番 DB と完全分離）。実行中は data/execution.pid を使用し stop フラグで停止可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を参照。

- 設定関連の CLI/ユーティリティを追加
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新するツールを追加（秘匿項目マスク、選択肢・デフォルト対応）。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。--strict オプションで警告を FAIL 扱いにできる。PyYAML があれば YAML のパース検証も行う。

- 環境変数 / 設定読み込みの改善
  - config.py に自動 .env 読み込み機能を追加（プロジェクトルート判定: .git または pyproject.toml）およびロード順序 OS 環境 > .env.local > .env。
  - .env パーサを強化: export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱いなどに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

- ポートフォリオ構築ライブラリを追加（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（スコア降順）、等重み・スコア重み計算。
  - portfolio.position_sizing: 複数の割当方式（risk_based, equal, score）に基づく株数決定、単元（lot）丸め、aggregate キャップ処理、コストバッファ対応。
  - portfolio.risk_adjustment: セクター集中の上限チェック（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。

- 研究用モジュール追加
  - research.factor_research: DuckDB を用いたファクター計算（モメンタム・ボラティリティ等）。prices_daily / raw_financials テーブルのみ参照する設計。

- 監視・運用ユーティリティ
  - monitoring.monitoring_db の初期化呼び出しをエントリポイントから実行することで監視テーブルの存在を保証（冪等）。
  - tools.paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を出力。閾値はファイル内定義で調整可能。

- プロセス制御ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度（high/normal/low）と CPU affinity 設定を提供。アクセス権限や未対応環境は警告でスキップ。

Changed
- データベース設計/接続方法の明確化
  - run_execution と run_monitoring で DuckDB（分析用）と SQLite（監視・発注履歴）をそれぞれ接続して利用するように実装。ペーパートレード時は paper 用 SQLite を使用して本番データと分離。

- デフォルト値・保護設定の導入
  - Settings で各種閾値（CPU/MEM/DISK）や PID/kill flag ファイルパス、PAPER_FILL_MODE の検証ルール等をプロパティ化し、無効値検出時に明確なエラー/例外を返すようにした。

Fixed
- 環境変数パースの不備を修正
  - .env parser の不適切なコメント切り取りやクォート内バックスラッシュ未処理などを改善し、より堅牢に。

- process_priority の例外処理強化
  - 権限不足やプラットフォーム差異によるエラー（AccessDenied / AttributeError / NotImplementedError 等）をキャッチして警告ログを出し処理を継続するようにした。

Security
- .env の扱いに関する注意文言を config_setup に明記（.env を Git にコミットしないことを強調）。

0.1.0 - 2026-04-17
-----------------

Added
- 初期リリース相当の機能を実装・公開。
  - コア: ExecutionEngine / SystemMonitor の起動スクリプト（run_execution, run_monitoring）。
  - 設定管理: Settings (環境変数ラッパ)、.env 自動読み込み、config_setup, validate_config CLI。
  - データ: DuckDB/SQLite を用いた分析・監視インフラの雛形。
  - ポートフォリオ: 銘柄選定・重み付け・ポジションサイズ計算・セクター制限・レジーム乗数。
  - 研究: factor_research モジュールによるファクター計算の初期実装。
  - ツール: Paper Trading 検証レポート生成スクリプト。
  - ユーティリティ: プロセス優先度・CPU affinity 設定ユーティリティ。

Changed
- パッケージの __version__ を 0.1.0 に設定。
- CLI やユーティリティ類の標準ログレベルを INFO に設定。

Notes / Migration
- .env の自動ロードはプロジェクトルートが見つからない場合スキップされます。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL 等は Settings で厳密に検証されます。不正な値は起動時に例外となるため .env の値を見直してください。
- run_execution/run_monitoring は起動前に data ディレクトリ下の stop/request/kill フラグや PID ファイルパスを参照します。運用時はこれらのファイル管理に注意してください。

追加要望・TODO（コード内注記より）
- position_sizing: 銘柄ごとの lot_size を stocks マスタ等から取得できるよう拡張予定。
- risk_adjustment.apply_sector_cap: 価格欠損（0.0）による過小評価を防ぐためのフォールバック価格導入の検討。
- factor_research: さらに多くのファクターや欠損データ取り扱いロジックの追加検討。

--- 
注: 本 CHANGELOG は提示されたソースコードから推測して作成しています。実際の変更履歴（コミット履歴やリリースノート）と差分がある可能性があります。必要であればコミット履歴に基づく正確な CHANGELOG 作成を支援します。