# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従っています。  

## [Unreleased]

## [0.1.0] - 2026-04-19
初回公開リリース。

### 追加 (Added)
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト / ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（既定: data/paper_trading.db）を使用して本番 DB と分離。  
    - 起動時にプロセス優先度を "high" に設定。停止は data/stop_requested.flag によるフラグで制御。PID ファイルの書き込みに対応。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を使用する仕様。

- 設定・環境管理
  - config.py: 環境変数読み込み・管理モジュールを実装。  
    - プロジェクトルート（.git または pyproject.toml）を自動探索して `.env` / `.env.local` を読み込む（OS 環境変数を保護）。  
    - .env パースはクォートやエスケープ、インラインコメント等に対応。  
    - Settings クラスで各種設定値（DB パス、ログレベル、KABUSYS_ENV、各種しきい値、paper_trading 関連設定等）をプロパティとして公開。  
    - 必須環境変数 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD) の参照メソッドを提供。

  - config_setup.py: 対話式ウィザードで `.env` を生成/更新する CLI を実装。  
    - 必須 / 任意項目、シークレット入力、既存値の再利用、保存キャンセルなどに対応。

  - validate_config.py: .env と config/*.yaml の妥当性を起動前に検査する CLI を実装。  
    - 必須環境変数や KABUSYS_ENV, LOG_LEVEL のチェック、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML がある場合）を実行。  
    - `--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ロジック（pure functions）
  - portfolio/portfolio_builder.py: 候補選定と重み計算
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等額配分。
    - calc_score_weights: スコア加重配分（全スコア 0 の場合は等額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有と当日売却予定を考慮）により候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告のうえ 1.0 フォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に応じて発注株数を算出。  
      - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer を考慮した保守的見積り、残差処理による追加配分などを実装。

- 研究用・ファクター計算基盤
  - research/factor_research.py: DuckDB を用いたモメンタム等ファクター計算の土台（モジュール、定数、calc_momentum の実装開始）。  
    - 設計として prices_daily / raw_financials テーブルのみ参照、DuckDB 接続受け取り等を採用。

- ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを実装。  
    - stdout StreamHandler（標準出力）、TimedRotatingFileHandler（日次ローテーション、デフォルト logs/、30日保持）をルートロガーに設定。  
    - 既存ハンドラのクリア、環境変数 LOG_DIR / LOG_LEVEL との連携、ファイル出力失敗時のフォールバックを実装。
  - utils/process_priority.py: プロセス優先度（Windows / POSIX 対応）と CPU affinity 設定ユーティリティを実装。  
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。失敗時は警告ログでスキップ。

- Execution コンポーネントの組み立て（起動時の依存注入）
  - run_execution において BrokerClientFactory、OrderRepository、OrderManager、RiskManager（デフォルト RiskConfig を含む）、Reconciler、ExecutionEngine を組み立てて起動する流れを実装。  
    - RiskConfig のデフォルト値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を設定。  
    - RiskManager の初期 cash は broker.get_available_cash() から取得。

- 監視 / モニタリング
  - monitoring DB 初期化用の init_monitoring_db 呼び出しを実装（冪等なテーブル作成保証）。  
  - SystemMonitor の check_once をポーリングで呼び出し、例外発生時もログに記録しループを継続する堅牢化を実装。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。  
    - 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、API レイテンシ（avg, max, P95）などを SQLite のログから集計し PASS/FAIL 判定を行う。  
    - デフォルトしきい値（稼働率 99%、Fill 90%、Send 95%、P95 レイテンシ 200ms）を定義。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

### 既知の制約 / TODO
- portfolio/position_sizing.py:
  - 銘柄ごとの単元（lot_size）を将来的に銘柄マスタで扱う予定（現在はグローバル lot_size を使用）。TODO コメントあり。
- portfolio/risk_adjustment.py:
  - price の欠損時のフォールバックロジックが未実装（TODO コメントあり）。欠損があるとエクスポージャーが過少見積りされる可能性あり。
- research/factor_research.py:
  - ファイル末尾で calc_momentum の実装途中で truncation が見られる（モジュールは土台を提供しているが、追加の factor 計算実装が必要）。
- 一部の外部依存（psutil、duckdb、PyYAML など）が環境にない場合は機能が限定されるため、実行環境の整備が必要。

### 使い方（簡易メモ）
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=30 等でポーリング間隔指定可能
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

## 互換性
- 初回リリースのため互換性に関する変更履歴はありません。将来的な互換性破壊はここに記載します。

(END)