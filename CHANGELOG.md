# CHANGELOG

すべての変更は「Keep a Changelog」の形式に従い、日本語で記載しています。

なお、本リリースはパッケージ内の主要スクリプト・ユーティリティ群を含む初期公開（v0.1.0）相当のまとめです。ファイル内容から推測して機能説明・注意点を盛り込んでいます。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 初期リリース: KabuSys 基盤機能群を追加。
  - パッケージバージョンを src/kabusys/__init__.py にて "0.1.0" に設定。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を検出してループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず production 相当の sqlite_path を使用する点を明記。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）・OrderRepository・OrderManager・RiskManager・Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ検出時に安全停止する制御を実装。pid ファイルパス管理あり（data/execution.pid）。
- 設定管理
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルートの検出は .git / pyproject.toml を基準）。
    - .env / .env.local のパース実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い、保護された OS 環境変数の上書き制御。
    - Settings クラスを実装し、各種設定値（J-Quants / kabu API / DB パス / Paper Trading 関連 / 監視閾値 / 環境種別など）をプロパティとして提供。バリデーションやデフォルト値を保持。
    - 環境自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD オプションをサポート。
- 設定ツール・検証
  - config_setup.py
    - 対話式ウィザードで .env の作成・更新を支援する CLI を追加。既存 .env の読み込み・デフォルトの提示・シークレットマスク表示・確認プロンプトを実装。
  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL/DB パス/設定 YAML の存在とパースチェック、live 環境向けの追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定する統一ロギングセットアップを提供。
    - ログディレクトリの自動作成、LOG_LEVEL / LOG_DIR の解決順をサポート。ファイルハンドラ作成失敗時のフォールバック処理あり。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加。Windows / POSIX の差を吸収。
    - CPU affinity 設定用 set_cpu_affinity を提供（未指定時は変更しない）。アクセス権限や未サポート環境時に警告でスキップ。
- Portfolio 建設・リスク・ポジション決定
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等分配にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定の銘柄を除外可能、unknown セクターは制限対象外）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームは警告とフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、per-position / aggregate 上限、cost_buffer による保守的見積り、スケールダウン・端数配分ロジックを実装。
    - 価格欠損時のスキップやログ出力等の安全処理を備える。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定（しきい値はソース内定義: 稼働率 99%、成功率 90%、送信率 95%、P95 200ms）。
    - 日付フィルタ、DB パス指定（--db または PAPER_TRADING_SQLITE_PATH）をサポート。DB 存在チェックと OperationalError の扱いを実装。
- その他ユーティリティ
  - monitoring.monitoring_db に対する初期化呼び出しを起動スクリプトから行う（存在しない監視テーブルの作成を保証）。
  - duckdb を分析用 DB として各スクリプトで接続する取り回しを追加（設定経由でパス指定）。
- 研究用モジュール（骨格）
  - research/factor_research.py
    - DuckDB 接続を受け、Momentum/Value/Volatility/Liquidity ファクターを計算するための設計と一部実装（定数、API、設計方針）を追加。prices_daily / raw_financials テーブルを前提とした純関数設計。

### Changed
- なし（初期リリース相当のまとめのため、既存機能の変更はなしと推定）。

### Fixed
- なし（特定のバグ修正の痕跡はコードからは明示できません）。

### Deprecated
- なし

### Security
- なし（機密情報は .env に保持する設計、.env は Git にコミットしない旨を config_setup.py に注記）。

---

注意:
- 上記はソースコード内容から推測した機能一覧および挙動説明です。実際のリリースノートとして公開する際は、実行環境での動作確認、外部依存（psutil、duckdb、PyYAML など）のバージョンやインストール要件、各種デフォルトパスの存在チェック・マイグレーション手順、バックアップ方針などを合わせて記載することを推奨します。