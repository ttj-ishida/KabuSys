# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

最新: Unreleased

## [Unreleased]

- 次回リリースに向けた差分はありません（現在の配布ソースは以下の 0.1.0 に対応）。

---

## [0.1.0] - 2026-04-18

初回公開リリース。日本株自動売買フレームワークのコア機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- 基本設定・環境変数管理
  - Settings クラスを提供し、環境変数から設定を取得する仕組みを実装（src/kabusys/config.py）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env のパースロジックを強化（export プレフィックス対応、シングル/ダブルクォート中のエスケープ、インラインコメント処理など）。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を追加。
  - PAPER_TRADING 用 DB パスのための paper_sqlite_path を追加。

- 起動・運用用スクリプト
  - 実行エンジン起動スクリプト: run_execution（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時は MockBroker を使い、本番 DB と分離して data/paper_trading.db に記録する仕組みを備えています。
    - 起動時にプロセス優先度を high に設定し、停止フラグ（data/stop_requested.flag）検出機構を実装。
    - ExecutionEngine をスレッドで実行し、停止フラグで安全に停止できるループを実装。
  - 監視（モニタリング）起動スクリプト: run_monitoring（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - 監視プロセスは本番 sqlite_path を環境にかかわらず使用して監視データを記録する設計。
    - 停止フラグ検出、例外時のログ出力保持など堅牢なポーリングループを実装。

- 監視・共通インフラ
  - 監視 DB 初期化ユーティリティ init_monitoring_db を利用する呼び出しを各スクリプトで組み込み（冪等にテーブル存在を保証）。
  - DuckDB 接続を利用した分析用 DB パス指定（Settings.duckdb_path）。

- ロギング・プロセスマネジメント
  - 統一的なログ設定ユーティリティ setup_logging を実装（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - LOG_DIR 環境変数や引数でログディレクトリを上書き可能。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで動作。
  - プロセス優先度設定ユーティリティ set_process_priority、CPU affinity 設定 set_cpu_affinity を実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX (Linux/Mac/FreeBSD) を吸収する処理を実装。権限不足や未対応プラットフォームでは警告ログを出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で候補抽出
    - calc_equal_weights / calc_score_weights: 等配分・スコア重み配分を実装（スコア合計が 0 の場合のフォールバックに対応）
  - セクター集中・レジーム調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有比率が閾値を超えるセクターの新規候補除外
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく乗数
  - 株数決定・丸めロジック（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method に対応
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）でのスケーリング、cost_buffer による保守見積り、余剰キャッシュによる端数配分を実装

- 設定支援 CLI / 検証
  - config_setup: 対話式 Wizard による .env の初期作成・更新ツール（src/kabusys/config_setup.py）
    - シークレット項目はマスク表示。生成テンプレートで .env ファイルを安全に作成。
  - validate_config: 起動前の設定検証ツール（src/kabusys/validate_config.py）
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がある場合は）パース検証、本番時の追加ガード等を実装。
    - --strict オプションで警告を FAIL 扱いにするモードを提供。

- ペーパートレーディング検証ツール
  - paper_verification_report: Paper Trading の検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを集計して PASS/FAIL を判定する CLI を提供。
    - 閾値はファイル先頭で定義（稼働率 99% 等）。--from/--to/--db オプションで期間・DB の指定に対応。

- リサーチ / ファクター計算（骨格）
  - factor_research モジュール（src/kabusys/research/factor_research.py）にモメンタム等のファクター計算設計と一部実装（モメンタム期間定義や関数設計の骨格）を追加。DuckDB 接続を受けて SQL/Python で完結する設計。

- パッケージメタ
  - パッケージ初期化に __version__ = "0.1.0" を設定（src/kabusys/__init__.py）。

### 変更 (Changed)
- 設定読み込み順:
  - OS 環境変数 > .env.local (> .env) の優先順位を明示的に実装。既存の OS 環境変数は保護（protected）され、.env.local の override は可能だが OS 環境変数は上書きしない。
- ロギング:
  - stdout を標準出力に使うことで、スケジューラ / cron 等のログリダイレクト運用に対応。

### 修正 (Fixed)
- .env のパースにおけるクォート処理とエスケープ処理の不整合を解消（複雑な値を含むトークンや URL の安全な読み込みに対応）。
- run_execution / run_monitoring における DB 接続のクローズ処理を finally ブロックで確実に実行するように改善。

### 注意点 (Notes)
- run_monitoring は監視データ記録のために常に Settings.sqlite_path（本番監視 DB）を使用します。環境にかかわらず同じ DB を参照する設計です。
- run_execution は paper_trading 環境時に専用 SQLite を使用します（Settings.paper_sqlite_path）。
- process_priority/CPU affinity の設定は OS 権限やプラットフォームに依存します。権限不足 (psutil.AccessDenied 等) の場合は警告ログを出して処理をスキップします。
- config/*.yaml の中身検証には PyYAML が必要です。未インストール時はパース検証をスキップして警告を出します。
- factor_research は一部実装の骨格を含みます。ファクターの計算は DuckDB の prices_daily / raw_financials テーブルを前提とします。

---

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の計算と標準化）
- ExecutionEngine、OrderManager、BrokerClient の詳細実装とテストカバレッジ拡充
- 運用監視のアラート送信（LINE 経由）やメトリクスの可視化連携

（以上）