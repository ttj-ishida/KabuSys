CHANGELOG
=========

すべての重要な変更履歴を Keep a Changelog の形式で記載します。
このファイルは人間向けの要約が主目的です。

フォーマット:
  - Added, Changed, Fixed, Deprecated, Removed, Security セクションを使用しています。

[0.1.0] - 2026-04-18
--------------------

Added
- プロジェクト初回リリース。基本的な自動売買フレームワークを実装。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - Engine はデーモンスレッドで動作し、data/stop_requested.flag を検知すると安全に停止する。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - 起動時 pid ファイルを data/execution.pid に書き込む仕組み（設定経由でパス変更可）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db デフォルト）を利用する仕様に注意。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理
  - config.py: 環境変数・.env 読み込み・Settings クラスを追加。  
    - 自動 .env ロード機能（プロジェクトルート検出 .git / pyproject.toml）を実装。.env と .env.local の読み込み順をサポート。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト等向け）。  
    - 多数のプロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID/KILL フラグ関連、閾値等）。PAPER_FILL_MODE の妥当性チェックと有効値一覧を実装。
- 設定支援・検証 CLI
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。既存値再利用、シークレットマスク、保存確認などを実装。
  - validate_config.py: 起動前に .env と config/*.yaml の基本検証を行う CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML がある場合）を実施。  
    - --strict オプションで警告も失敗扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。  
    - stdout (StreamHandler) と 日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーへ設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR / app_name による柔軟な設定。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（および CPU affinity）を設定するユーティリティを追加。Windows/Linux/macOS 対応、権限不足や未対応環境での安全なフォールバックを実装。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（スコア順）と等配分 / スコア配分の重み計算を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック動作（警告ログ）。
  - portfolio/position_sizing.py: 発注株数算出の純粋関数を実装。  
    - risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate キャップ（available_cash 超過時のスケーリングおよび端数割当）を実装。手数料・スリッページ見積り用 cost_buffer を考慮。
  - portfolio/__init__.py で上記関数をエクスポート。
- 研究・計算モジュール（骨格）
  - research/factor_research.py: Momentum 等のファクター計算を行うモジュールを追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する設計）。（計算関数の実装途中の箇所あり）
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。  
    - 指標: 稼働率（uptime）、注文成立率（fill rate）、送信率（send rate）、P95 レイテンシ等。しきい値による PASS/FAIL 判定を行う。  
    - オプションで期間指定（--from / --to）と DB パス指定（--db）。PAPER_TRADING_SQLITE_PATH 環境変数を参照。
- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を用いて起動時に監視用テーブルの存在を保証（冪等）。
- パッケージ情報
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

Changed
- .env パーサーの強化
  - config._parse_env_line において、export プレフィックス対応、引用符つき値のバックスラッシュエスケープ処理、インラインコメントの扱い、クォート無しのコメント判定などを実装し堅牢化。
  - .env 読み込みロジックは既存 OS 環境変数を保護する protected パラメータを導入（.env.local の上書き制御）。
- ロギングの既存ハンドラのクリア処理を追加。複数起動時の二重出力を回避。

Notes / Migration
- 監視（run_monitoring）は明示的に「本番 sqlite_path」を使用する仕様です。テストや paper_trading 環境で監視を分離したい場合は Settings.sqlite_path を別途指定してください。
- 実行エンジン（run_execution）は KABUSYS_ENV=paper_trading のときに PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。本番 DB と完全に分離されます。
- 停止制御はプロジェクトルート/data/stop_requested.flag を用いる仕組みです（環境によりパスが異なる場合はスクリプト内の定数を変更してください）。
- ログディレクトリ作成に失敗した場合でもコンソールログは出力されます（ファイル出力は無効化されます）。これは権限のない環境での安全なフォールバック処理です。

Fixed
- （この初回リリースでは明示的なバグ修正履歴はありません）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- （該当なし）

今後の予定（概略）
- research/factor_research の完全実装（ファクター計算ロジックの続き）。
- Strategy / Execution の各コンポーネントの単体テスト拡充、モック注入の整備。
- 銘柄別 lot_size 対応（stocks マスタの導入）。
- .env 値の暗号化 / シークレット管理機構の検討。