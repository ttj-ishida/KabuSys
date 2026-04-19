# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]

### Added
- ドキュメントやユーティリティ的な CLI/スクリプトを多数追加
  - 環境設定ウィザード: python -m kabusys.config_setup による対話式 .env 作成 / 更新機能を追加。
  - 設定検証 CLI: python -m kabusys.validate_config で .env と config/*.yaml を起動前に検証する機能を追加（--strict オプション対応）。
  - Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report でペーパートレード DB から各種指標（稼働率、成功率、レイテンシ等）を出力する機能を追加。
- 実行系起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading 時には専用の paper_trading DB を使用し、MockBrokerClient を利用する設計を想定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔オーバーライド、停止フラグ（data/stop_requested.flag）検知による終了処理を実装。
- 設定管理
  - Settings クラスを実装し、環境変数経由で各種設定を取得できるように（J-Quants / kabu API / DB パス / 監視閾値 / 実行環境等）。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。優先順位: OS 環境 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースの強化: export 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応。
  - PAPER_FILL_MODE の検証ロジックを追加（instant/partial/never/reject の妥当性チェック）。
- ロギング・プロセス管理ユーティリティ
  - setup_logging(): stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler をルートロガーに設定するユーティリティを追加。ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の解決をサポート。
  - process_priority.py: cross-platform（Windows / POSIX）でプロセス優先度設定と CPU affinity 設定ユーティリティを追加。psutil を用い、権限不足時は警告でスキップ。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder: 候補選定（スコア降順・同点タイブレーク）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）を実装。
  - risk_adjustment: セクター集中上限チェック（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクター扱いの例外などを考慮。
  - position_sizing: risk_based / equal / score 方式に対応した株数計算を実装。単元株（lot_size）丸め、per-position 上限・aggregate cap（available_cash に収めるためのスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮した配分ロジックを実装。
- データベース周り
  - duckdb と sqlite3 を想定した接続処理を起動スクリプトに追加（duckdb は分析用、sqlite は監視 / 発注履歴用）。監視用テーブルの初期化を保証する init_monitoring_db 呼び出しを採用。
- 監視・実行の停止制御
  - data/stop_requested.flag（および execution.pid の取り扱い）を用いた外部停止フラグ検出に対応。停止検知時には安全にシャットダウン処理を実行。

### Changed
- ログ出力の標準化: すべての起動スクリプトから setup_logging を呼び出す前提でログ設定を統一。
- .env の読み込み動作: OS 環境変数を保護する protected パラメータを導入し、.env.local の上書き挙動を明確化。
- run_execution/run_monitoring のプロセス優先度設定を起動直後に実行するように変更（set_process_priority("high") を採用）。

### Fixed
- 環境変数の不正値に対してフォールバックする処理を追加
  - MONITOR_POLL_INTERVAL が不正（非整数または 0 以下）な場合、警告ログを出してデフォルト 60 秒にフォールバック。
  - LOG_LEVEL / KABUSYS_ENV / PAPER_FILL_MODE の不正値に対する ValueError あるいは警告の提示を明確化。
- validate_config にて、本番（live）環境での危険設定（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START が 1）を警告するチェックを追加。

### Security
- .env 取り扱いに関する注意書きを config_setup で強調（.env を絶対に Git にコミットしない旨のヘッダを出力）。

---

## [0.1.0] - 2026-04-19

初期リリース相当。上記 Unreleased に記載した機能群の初期実装をまとめて公開。

### Added
- パッケージのバージョン定義: kabusys.__version__ = "0.1.0"
- 基本的なモジュール群を初期実装
  - 実行/監視エントリポイント（run_execution, run_monitoring）
  - 設定管理（config.py）、対話式設定ウィザード（config_setup.py）、設定検証（validate_config.py）
  - ロギング設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity ユーティリティ（utils.process_priority）
  - ポートフォリオ構築（portfolio モジュール: portfolio_builder, risk_adjustment, position_sizing）
  - ペーパートレード検証ツール（tools.paper_verification_report）
  - 研究用ファクター計算のスケルトン（research.factor_research: 定数・calc_momentum の骨組み）
  - そのほかユーティリティ __init__ 等

### Fixed / Changed
- 初期実装における基本的な入力検証と安全弁を追加（環境変数チェック、ファイルパス存在チェック、例外時のログ出力など）。

---

記載内容はコードベースの構造と実装から推測して作成したものです。必要であれば各機能ごとにより詳細な変更点（関数単位の差分や既知の制限事項、今後の予定）を追記します。どの粒度で CHANGELOG を整備するかご希望があれば教えてください。