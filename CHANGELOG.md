# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
リリースはセマンティックバージョニングに従います。

全般メモ:
- このリポジトリの現在のバージョンは `0.1.0`（src/kabusys/__init__.py）です。
- リリース日: 2026-04-24

## [Unreleased]

（次回リリースに向けた変更はここに記載します）

## [0.1.0] - 2026-04-24

### 追加 (Added)
- 基本アプリケーション構成と実行スクリプトを追加
  - run_execution.py:
    - ExecutionEngine 起動スクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - 停止用フラグファイル（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）を利用した安全な起動/停止ロジック。
    - BrokerClientFactory, EngineConfig, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager などの組み立てが行われる。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用（監視テーブルの初期化を行う）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定・環境管理
  - config.py:
    - .env 自動読み込み機能（プロジェクトルート検出 .git / pyproject.toml）。
    - .env ファイルのパース実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
    - Settings クラスを導入し、各種環境変数（J-Quants, kabuAPI, LINE, DB パス, 監視閾値など）をプロパティとして提供。値の検証を含む。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）。
    - DB パス、PID / kill flag パス、閾値（CPU/MEM/DISK）等のデフォルトを定義。
- 環境設定支援 CLI
  - config_setup.py:
    - 対話式ウィザードで .env を初期作成・更新するスクリプトを追加。
    - 入力補助（デフォルト表示・シークレットマスク・選択肢）と .env の書式整形（.env に書き込むテンプレート）を提供。
- 設定検証 CLI
  - validate_config.py:
    - .env と config/*.yaml の事前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML がある場合）を実施。
    - KABUSYS_ENV=live に対する追加ガード（LINE 設定の有無や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告をエラー扱いにできる。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。
    - ログディレクトリ自動生成。作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベルとログディレクトリは引数、環境変数、デフォルトの順で解決。
  - utils/process_priority.py:
    - Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity ユーティリティを追加。
    - 権限不足や未対応環境では警告を出して安全にスキップ。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナル選別（select_candidates）、等重み/スコア重みの算出関数を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中上限の適用（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py:
    - allocation_method（"risk_based" / "equal" / "score"）に沿った発注株数計算。
    - 単元株（lot_size）丸め、per-position と aggregate の上限、cost_buffer を考慮したスケールダウンロジックを実装。
- レポート・調査ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定（閾値はソース内で定義）。
    - DB パスは引数または環境変数 PAPER_TRADING_SQLITE_PATH から指定可能。
- 研究モジュール（骨格）
  - research/factor_research.py:
    - ファクター計算用モジュールを追加（Momentum, Value, Volatility, Liquidity の設計と一部実装）。DuckDB 接続を使用する設計。

### 変更 (Changed)
- なし（初回公開のため、新規実装が中心）

### 修正 (Fixed)
- 環境変数パーサの堅牢化
  - export プレフィックスやクォート内のバックスラッシュエスケープに対応し、.env の現実的なフォーマット差異に耐性を向上。

### 既知の制限 / 注意点
- run_monitoring は「監視用」DB として settings.sqlite_path（本番用デフォルト）を用いる設計になっており、環境に関係なく本番の sqlite_path を参照します。監視データを本番 DB と分離したい場合は設定を明示的に変更してください。
- research/factor_research.py はファイル末尾で計算関数の途中（src 断片）で終わっているため、完全実装は今後の作業が必要です。
- process_priority の優先度設定、CPU affinity の操作は権限やプラットフォームに依存します。権限不足時はワーニングを出して処理をスキップします。
- .env は機密情報を含むため、リポジトリにコミットしないでください（config_setup.py の出力にも明示あり）。

### セキュリティ (Security)
- なし

---

参考: 主な環境変数とデフォルト（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 60（run_monitoring のポーリング秒。環境変数で上書き可）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の fill 振る舞い）

（以上）