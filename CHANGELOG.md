CHANGELOG
=========

本 CHANGELOG は Keep a Changelog の形式に準拠しています。  
主にコードベースの追加・変更点をソースコードから推測して日本語でまとめています。

v0.1.0 - 2026-04-19
-------------------

Added
- 起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止制御はリポジトリ直下の data/stop_requested.flag を監視。
    - プロセス優先度を高 (high) に設定して起動。
    - 監視用 DB は KABUSYS_ENV にかかわらず設定の sqlite_path を使用。
    - duckdb 接続を併用、例外発生時のログ出力とループ継続処理を実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用（本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）の検知でエンジン停止。PID ファイル管理に対応。
    - プロセス優先度を高 (high) に設定して起動。
- 設定読み込み・管理機能を追加
  - config.py
    - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロード（無効化フラグあり）。
    - .env パーサは export プレフィックス、クォート文字列、エスケープ、インラインコメントに対応。
    - 環境変数保護（OS 環境変数を上書きしない）と .env.local による上書き制御をサポート。
    - Settings クラスを提供し、J-Quants / kabuステーション / DB パス / paper trading 用設定 / 監視閾値 / KABUSYS_ENV / LOG_LEVEL 等のプロパティと検証を実装。
    - PAPER_FILL_MODE の許容値検証（"instant","partial","never","reject"）や KABUSYS_ENV/LOG_LEVEL の検証を備える。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を実装。
    - 秘匿入力（マスク）、選択肢、デフォルト値、既存 .env の読み込み・再利用をサポート。
    - 保存前の確認とテンプレート形式での .env 出力を実装。
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数チェック、プレースホルダ検出、DB パスの親ディレクトリ存在チェック、PyYAML の有無に応じた YAML 検証、KABUSYS_ENV=live 時の追加ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築関連（純粋関数群）を追加
  - kabusys.portfolio.portfolio_builder
    - select_candidates（スコア降順選択）、calc_equal_weights、calc_score_weights を実装。スコア全ゼロ時のフォールバックと警告をサポート。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap（セクター集中制限。既存ポジションを評価し上限超過セクターの新規候補を除外）を実装。
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。未知レジームはフォールバックして警告。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes を実装。allocation_method に応じて risk_based / equal / score の株数算出を行う。
    - 単元株（lot_size）丸め、1 銘柄上限・総投資上限（aggregate cap）のスケーリング、cost_buffer による保守的見積り、残余配分ロジックを備える。
- ユーティリティを追加
  - kabusys.utils.logging_setup
    - 統一ロギング設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ設定。
    - LOG_DIR/LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップして安全に続行。
  - kabusys.utils.process_priority
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS の場合は警告を出してスキップ。
- ツールを追加
  - kabusys.tools.paper_verification_report
    - Paper Trading 用 SQLite DB から稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して検証レポートを生成する CLI を実装。
    - 判定基準（閾値）を定義し PASS/FAIL を出力。--from/--to/--db オプションに対応。
- 研究用モジュール（初期実装）
  - kabusys.research.factor_research
    - Momentum 等のファクター計算を行う関数群の骨子を実装。DuckDB 接続を受け prices_daily/raw_financials を参照して計算する設計（実装は継続中、ファイル末尾が未完の可能性あり）。
- パッケージメタ
  - パッケージバージョンを __version__ = "0.1.0" と設定。

Changed / Improved
- .env パーサを強化
  - export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント扱いの改善を実装。
  - .env.local による上書き（override）機構と OS 環境変数の保護（protected keys）を導入。
- ロギング出力は標準エラーではなく標準出力へ
  - StreamHandler を stdout に固定（cron 等で出力リダイレクトを想定）。
- 起動スクリプトの堅牢化
  - 監視・エンジン起動処理で例外キャッチ／ログ出力と安全なリソースクローズ（DB 接続／duckdb 接続）を実装。
  - 停止フラグの早期検出ロジックを導入し、意図しない起動や停止を抑制。

Fixed
- （コード内の注意点を改善）score_weights 全スコア 0 の場合のフォールバックと警告を追加。
- DB 初期化の冪等性確保
  - 起動時に監視テーブルが存在することを保証するため init_monitoring_db が呼ばれるようにした（並列実行や既存 DB に対する安全対策）。

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known limitations
- research/factor_research.py は実装途中（ファイル末尾が途中で切れているように見える）。詳細実装とテストは継続が必要です。
- 一部モジュール（監視 DB 初期化や SystemMonitor、ExecutionEngine、Broker 実装等）は本 CHANGELOG 作成時点で別ファイルに実装されている想定だが、ここでは存在を参照する起動スクリプト側の挙動を中心に記述しています。
- 実行スクリプトはローカルファイルによる停止フラグ / PID 管理に依存します。運用環境でのファイルパーミッションや競合に注意してください。

今後の作業候補
- factor_research の完全実装と単体テスト追加。
- ExecutionEngine / BrokerClient の統合テストおよび paper_trading の検証自動化。
- ログの構造化（JSON 形式オプション）やメトリクス出力（Prometheus 等）対応検討。