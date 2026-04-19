# CHANGELOG

すべての変更は Keep a Changelog に準拠して記載しています。  
慣例: 重要な変更のみを項目化しています。日付は本コードスナップショット作成日（2026-04-19）を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネント群を追加。
  - パッケージ初期バージョン定義
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下 data/stop_requested.flag ファイルで検知。
    - 監視は環境に依らず本番用 sqlite_path を使用して初期化（init_monitoring_db 呼び出し）。
    - duckdb との接続を確立して利用。
    - プロセス優先度を "high" に設定して起動。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離される設計。
    - BrokerClientFactory によるブローカークライアント生成（MockBrokerClient 対応を想定）。
    - ExecutionEngine を別スレッドで実行し、stop_flag による停止制御を実装。
    - デフォルトでプロセス優先度を "high" に設定。

- 設定管理・CLI
  - config.py
    - 環境変数 / .env 自動読み込み機能を実装（.env, .env.local の優先度ルール）。
    - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env 内の export 形式、シングル/ダブルクォート、エスケープ、インラインコメントなどを正しくパースする実装を提供。
    - 多数の設定プロパティを用意（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 実行環境等）。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
    - 環境（KABUSYS_ENV）の有効値チェック（development, paper_trading, live）。

  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。
    - シークレット項目はマスク表示、既存 .env の読み込み・再利用をサポート。
    - .env のテンプレート書き出し機能を実装（安全上の注意書きも出力）。

  - validate_config.py
    - .env および config/*.yaml の検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスや config ファイル存在チェック、live 環境向けガード（LINE 設定や Kill Switch 設定）等を実装。
    - --strict モードで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、同点は signal_rank による tiebreak）を実装。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights を提供（スコア全て 0 の場合は等金額へフォールバックして警告）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存ポジションからセクター比率を計算して新規候補を除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング・未知レジームはフォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。
    - リスクベース算出（risk_pct, stop_loss_pct を利用）と、単元株（lot_size）での丸め、1 銘柄上限・aggregate cap（available_cash）でのスケーリングをサポート。
    - cost_buffer を用いた保守的コスト見積り、スケールダウン時の端数処理（lot 単位での再配分）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 一貫したログ設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、バックアップ 30 日）を root ロガーへ設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装し、既存ハンドラのクリーンアップを行う。

  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定と CPU affinity 設定を追加（psutil を利用）。
    - Windows / POSIX(nice) 対応、アクセス権限不足時は警告を出してスキップ。

- DuckDB / SQLite 統合
  - 各エンジンで duckdb 接続を受け取る設計を採用（分析用 DuckDB と SQLite を併用）。
  - 監視テーブル初期化用の init_monitoring_db 呼び出しを run_monitoring と run_execution の起動時に実施（冪等に監視テーブルを保証）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加（期間指定や DB パス指定可能）。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出し PASS/FAIL 判定（閾値はソース内定義）。
    - P95 計算や各種 SQL クエリを実装し、欠損テーブルに対して安全に N/A を返すフォールバックを備える。

- 研究用モジュール（factor 計算）
  - research/factor_research.py（骨格）
    - DuckDB を用いたモメンタム / Value / Volatility / Liquidity 等のファクター計算モジュールの骨格を追加。prices_daily / raw_financials テーブルを前提にした設計。
    - 実装途中の箇所あり（スニペット末尾で切れているため、続き実装が必要）。

### 変更 (Changed)
- なし（初回リリースのため新規追加中心）

### 修正 (Fixed)
- なし（初回リリース）

### 注意 / マイグレーション (Notes)
- 環境変数の自動読み込み
  - デフォルトでプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env を自動ロードします。CI/テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Paper Trading 分離
  - paper_trading（KABUSYS_ENV=paper_trading）は SQLite DB を完全に分離して運用する設計です（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）。
  - 実運用（live）環境では設定ミスに注意してください（validate_config の live ガードを参照）。

- ログ出力
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソール出力のみで継続します。デフォルトは logs/（LOG_DIR 環境変数で変更可能）。

- 権限関連
  - process priority / cpu affinity の設定は OS 権限により失敗する場合があります。失敗時は警告ログが出力され、処理は継続されます。

### 既知の制限 (Known issues)
- factor_research.py は途中で切れており、完全な実装が未完了です（今後実装予定）。
- 一部 TODO コメントが残っており（例: price のフォールバックロジック、銘柄別 lot_size のサポートなど）、将来的な拡張ポイントがあります。

---

今後の予定（例）
- factor_research の完成（ファクター算出の SQL / 正規化ロジック追加）
- ExecutionEngine / BrokerClient の具体的な統合テストとドキュメント整備
- 単体テストの追加と CI 設定
- 運用向けの監視・アラート（LINE 通知）の実運用検証

もし CHANGELOG の粒度・書式（例えば Unreleased を常に置く等）や特定のファイルに関する補足を希望される場合は指示してください。