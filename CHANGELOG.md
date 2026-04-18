CHANGELOG
=========

すべての重要な変更点を記録します。本プロジェクトはセマンティックバージョニングに従います。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリース。KabuSys 自動売買基盤のコアユーティリティ、実行・監視スクリプト、ポートフォリオ構築ロジック、検証ツールなどを追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用して paper_trading 専用 DB（data/paper_trading.db をデフォルト）に記録する設計（BrokerClientFactory 経由）。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止処理を実装。
    - PID ファイル出力（data/execution.pid 想定）をサポート。
    - RiskManager の初期設定（最大ポジション割合、利用率、レート制限、サーキットブレーカー等）を追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計。
    - 停止フラグによる優雅な終了処理を実装。
- 設定関連
  - config.py
    - .env 自動読み込み機能（プロジェクトルートに .git または pyproject.toml がある場合に有効）。
    - .env/.env.local 読み込みの優先度管理（OS 環境変数は保護される）。
    - Settings クラスを提供し、環境変数経由で設定をアクセスできる抽象化。
    - PAPER_FILL_MODE の値検証、paper_sqlite_path、各種監視閾値、ログ関連設定などを実装。
  - config_setup.py
    - 対話式 .env 作成ウィザード（既存 .env の読み込み・更新、シークレット項目はマスク表示）。
    - .env ファイルの生成ロジック（テンプレート化されたヘッダ・セクション付き）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性をチェックする CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML パース確認（PyYAML があれば実施）などを行い、errors/warnings/infos を出力。--strict オプションで警告も失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分）をセットする共通関数を追加。
    - LOG_LEVEL / LOG_DIR の解決ロジックと既存ハンドラの安全な再設定を実装。
    - ログディレクトリ作成に失敗した場合はコンソール出力モードにフォールバック。
  - utils/process_priority.py
    - psutil によるクロスプラットフォームのプロセス優先度設定（"high"/"normal"/"low"）と CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/macOS での差分を吸収し、権限不足等の失敗は警告してスキップする挙動。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順・タイブレークロジック）、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（既存保有割合が閾値を越えるセクターの候補除外）を実装。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知は 1.0 でフォールバック）を実装。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based"/"equal"/"score") に基づく発注株数計算、単元株（lot_size）丸め、1銘柄上限・aggregate cap のスケールダウン処理、手数料・スリッページ見積り（cost_buffer）考慮を実装。
    - aggregate cap スケールダウン時に残差を考慮して lot_size 単位で追加配分する仕組みを実装。
- research/factor_research.py（ファクター計算）
  - DuckDB 接続を受け、prices_daily / raw_financials テーブルから Momentum / Value / Volatility / Liquidity 系のファクターを算出する設計を追加（calc_momentum 等、設計方針と定数を実装。実装途中の箇所あり）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読み、稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）等を集計して PASS/FAIL 判定を出力するレポートジェネレータを追加。期間フィルタ（--from / --to）と --db オプションをサポート。
- パッケージ初期化
  - __init__.py にバージョン 0.1.0 を追加。

Changed
- N/A（初回リリースのため過去の変更はなし）

Fixed
- N/A（初回リリースのため過去の修正はなし）

Security
- .env ファイルは自動生成されるが「絶対に Git にコミットしないこと」と明記（config_setup の出力ヘッダに記載）。

Notes / Implementation details
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- .env/.env.local の読み込みは OS 環境変数を保護（protected set）する挙動。
- run_monitoring は監視データベースとして sqlite_path（Settings.sqlite_path）を使用し、環境に依存せず本番 DB を参照する点に注意。
- run_execution は paper_trading 環境では paper_sqlite_path を使用して本番 DB と分離する設計。
- 一部関数・箇所に TODO コメントあり（例: price 欠損時のフォールバック価格処理など）。今後の改良で追加のデータ補完やマスタ参照が想定される。

Acknowledgements
- 本リリースはコードベースの初期機能群を包含しており、今後の patch / minor / major リリースで機能追加・改善・バグ修正を行っていきます。