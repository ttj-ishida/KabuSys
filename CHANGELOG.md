CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。主要なリリースは日付付きで記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-20
-----------------

初回リリース。KabuSys の基本コンポーネントおよびユーティリティ群を追加しました。主な追加点は以下の通りです。

Added
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。0 以下や不正値の場合はデフォルトにフォールバックし警告を出力。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御はプロジェクト直下の data/stop_requested.flag を監視することで行う。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（BrokerClientFactory 経由）を利用し、ペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。PID ファイル / 停止フラグをサポートし、スレッド化されたエンジンの起動/停止を安全に行う。

- 設定管理
  - config.py
    - .env 自動読み込みロジックを追加（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env/.env.local のロード順序と上書きルール（OS 環境変数を保護）を実装。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env ファイルの行パースは export プレフィックス・ quoted 値・行内コメント等に対応。
    - Settings クラスを導入し、各種環境変数への型変換・バリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を提供。settings インスタンスをエクスポート。

  - config_setup.py
    - 対話式ウィザードで .env の作成・更新を支援する CLI を追加。
    - シークレット値はマスク表示、選択肢・デフォルトの扱い、保存前の確認などの UX を提供。

  - validate_config.py
    - 起動前に .env および config/*.yaml の基本検証を行う CLI を追加。
    - 必須環境変数チェック、パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML が存在する場合）を実行。
    - KABUSYS_ENV=live に対する追加警告（LINE 通知設定の未設定や Kill Switch の自動クリア設定など）。
    - --strict を指定すると警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等加重（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有比率に基づき新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear に対するマッピング）。未知レジームは警告のうえ 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - 株数算出ロジック calc_position_sizes を実装。
    - risk_based / equal / score の割当方式をサポートし、単元株（lot_size）丸め、1 銘柄上限 per-position、aggregate cap（available_cash を超える場合のスケーリング）や cost_buffer を考慮した保守的見積りを行う。
    - スケールダウン後の端数処理として fractional 残差を利用した再配分ロジックを備える。

- ユーティリティ
  - utils/logging_setup.py
    - 一貫したログ設定ユーティリティを追加。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する。
    - LOG_LEVEL / LOG_DIR と引数の優先順位で解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（set_process_priority）および CPU affinity 固定（set_cpu_affinity）を追加。psutil を利用し失敗時は警告でスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルを参照し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを算出。閾値による PASS/FAIL 判定を行う。
    - CLI オプション --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数でも DB パスを指定可能。

- 研究用モジュール（骨格）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（Momentum, Value, Volatility, Liquidity を想定）。DuckDB を用いた prices_daily / raw_financials の参照設計。モメンタム計算（calc_momentum）の実装開始（スキャン範囲や定数等を定義）。※ファイル末尾での実装途中（切り取りあり）。

- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注記 / 既知の制約
- Monitoring コンポーネントは run_monitoring 起動スクリプト内で sqlite_path を常に本番用パスとして開く仕様のため、開発環境での分離が必要な場合は環境変数 SQLITE_PATH を適切に設定してください。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的な拡張案として銘柄毎の単元情報を導入する旨の TODO コメントあり。
- research/factor_research の一部実装は継続中。DuckDB テーブル設計（prices_daily, raw_financials 等）に依存します。
- .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。

環境変数（主なもの）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — ログ出力先（デフォルト: logs/）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動 (instant|partial|never|reject)（デフォルト: instant）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

参考
- ログローテーション: 日次（midnight）、バックアップ 30 日。
- 停止制御: data/stop_requested.flag（起動・停止スクリプト共通で利用）。
- PID 管理: run_execution は data/execution.pid を利用。

今後の予定（予定を含む）
- research/factor_research の完全実装（Momentum/Value/Volatility/Liquidity の各ファクター算出）。
- SystemMonitor / ExecutionEngine 周りの統合テストとエラーハンドリング強化。
- 単元株情報の銘柄毎管理と position_sizing の拡張。
- 監視・アラートの LINE 通知連携実装（設定が存在すれば利用）。

-----