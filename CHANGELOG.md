CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （現時点ではなし）

0.1.0 - 2026-04-19
-----------------

Added
- 初回リリース: KabuSys 自動売買フレームワークの基本機能を追加。
  - 実行スクリプト
    - run_execution: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite (デフォルト: data/paper_trading.db) を使用し、本番 DB と完全に分離。
      - 起動時にプロセス優先度を "high" に設定するためのユーティリティ呼び出しを実行。
      - stop フラグファイル (data/stop_requested.flag) を監視し、安全に停止できる仕組みを実装。
      - ExecutionEngine を別スレッドで実行し、停止検出時に engine.stop() を呼び出して終了する制御を実装。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
      - stop フラグファイルを検知してループを終了する仕組みを実装。
  - 設定管理
    - config.Settings: 環境変数ラッパーを実装。
      - 自動ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env と .env.local の自動読み込みを実施（OS 環境変数は保護）。
      - 各種設定プロパティ（DB パス、ペーパートレード用パス、閾値や PID ファイルパスなど）を提供。
      - PAPER_FILL_MODE の妥当性チェック（"instant" | "partial" | "never" | "reject"）を実装。
      - KABUSYS_ENV / LOG_LEVEL の値検証を実装（有効値チェック）。
    - config_setup: .env 初期作成/更新ウィザード CLI を追加。
      - 対話式に主要環境変数を編集・保存可能。シークレットはマスク表示。
      - 保存時には .env ファイルのテンプレートを書き出す。
  - 設定検証
    - validate_config: 起動前に .env と config/*.yaml の検証を行う CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェックを実装。
      - PyYAML がインストールされている場合は config/*.yaml のパースチェックも実行。
      - --strict オプションで警告を失敗扱いに可能。
  - ログ・プロセス管理ユーティリティ
    - utils.logging_setup:
      - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（デフォルト logs/、日次ローテーション、30日保持）を設定するユーティリティを提供。
      - 既存ハンドラのクリアやログレベル / ログディレクトリの解決ロジックを備える。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils.process_priority:
      - Windows / POSIX の差分を吸収したプロセス優先度設定を提供（"high"/"normal"/"low"）。
      - CPU affinity を最初の N コアに固定する関数を提供（権限不足等は警告でスキップ）。
      - アクセス権限や未実装 OS に対するフォールバックと警告処理を実装。
  - ポートフォリオ構築モジュール（純粋関数）
    - portfolio.portfolio_builder:
      - select_candidates: BUY シグナルのスコア降順ソートと上位 N 抽出。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア比率に基づく重み計算（全スコアが 0 の場合は等金額にフォールバックし WARN）。
    - portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中制限の適用。既存保有価値に基づいてセクター上限を超過しているセクターの新規候補を除外（"unknown" セクターは制限対象外）。
      - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未定義レジームは 1.0 でフォールバックし WARN）。
    - portfolio.position_sizing:
      - calc_position_sizes: risk_based / equal / score 方式に対応した株数計算を実装。
      - 単元株（lot_size）での丸め、1 銘柄上限・aggregate cap（利用可能現金によるスケールダウン）、cost_buffer（手数料・スリッページ見積り）を考慮。
      - スケールダウン時は残差を考慮して lot 単位で追加配分するロジックを実装。
  - 分析・検証ツール
    - tools.paper_verification_report:
      - ペーパートレード用 SQLite から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して検証レポートを出力。
      - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL を判定。
      - --from/--to/--db オプションをサポート。
  - 研究モジュール（factor_research）
    - 定量ファクター（Momentum / Value / Volatility / Liquidity）設計の枠組みを実装。
      - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算を行う設計。
      - モメンタム計算用の定数（1M/3M/6M、MA200 等）を定義。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Known issues
- factor_research.calc_momentum の実装が途中で終了している箇所が見受けられます（ソース末尾が途中で切れている）。本機能を使用する前に未完成部分の実装が必要です。
- 一部外部ライブラリ（psutil, duckdb, PyYAML）が必須またはあると便利です。validate_config や一部の実行機能はこれらの有無によって挙動が異なります（PyYAML がない場合は YAML 検証をスキップ）。
- run_execution/run_monitoring はファイルによる停止フラグ（data/stop_requested.flag）や PID ファイルを利用します。運用環境では data ディレクトリの配置・権限に注意してください。
- .env 自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

開発者向けメモ
- コマンド例:
  - .env の対話式作成/更新: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視ループ起動: python -m kabusys.run_monitoring

バージョン情報
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

もし特定の変更点（コミット単位や差分の追加情報）をより詳細に反映したい場合は、該当するコミットメッセージや差分を提供してください。