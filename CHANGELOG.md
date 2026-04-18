# Changelog

すべての重要な変更を Keep a Changelog の形式に従って日本語で記載します。  
フォーマットの簡易説明: https://keepachangelog.com/ja/1.0.0/

最新版: Unreleased

---

## [Unreleased]

追加予定 / 既知の点（コードから推測）
- 研究モジュールの継続実装
  - kabusys.research.factor_research のモメンタム計算関数は実装途中の箇所があり、追加のテスト／完成実装が必要。
- position_sizing の拡張予定
  - 将来的に銘柄ごとの lot_size 対応（stocks マスタを想定）などの拡張がコメントで示唆されている。
- ログ作成失敗時の更なるフェールオーバーやユニットテストの追加
  - logging_setup はファイルハンドラ作成失敗時にコンソールのみで継続する設計だが、そのカバレッジ強化を予定。
- ドキュメント整備
  - PortfolioConstruction.md / StrategyModel.md 等へ参照している仕様書との差分確認・明文化を推奨。

---

## [0.1.0] - 2026-04-18

Added
- 基本アプリケーション構成と初期機能群を実装
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"
- 環境設定関連
  - .env ファイルの自動読み込み機能を実装（.env / .env.local、OS 環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 環境変数パーサを実装（クォート／エスケープ／コメント処理対応）
  - Settings クラスを実装し、アプリ全体で環境変数を集中管理（各種パス、閾値、env 判定、paper_trading 用設定など）
  - 対話式ウィザード CLI: kabusys.config_setup（.env の初期作成・更新を支援）
  - 設定検証 CLI: kabusys.validate_config（.env と config/*.yaml の存在・整合性チェック。--strict オプション対応）
- 起動スクリプト
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV=paper_trading 時の DB 分離（PAPER_TRADING_SQLITE_PATH）と MockBroker の利用想定
    - 停止フラグ（data/stop_requested.flag）検知による安全停止
    - 実行エンジンの PID ファイル管理（data/execution.pid）
    - スレッド駆動の ExecutionEngine 起動／監視ループを実装
  - 監視モジュール起動スクリプト: src/kabusys/run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は本番用 sqlite_path を常に使用（環境にかかわらず本番監視 DB を想定）
    - 停止フラグ検知でループ終了
- DB / ストレージ
  - DuckDB と SQLite の併用設計（duckdb は分析用、sqlite は監視・発注ログ用）
  - 監視テーブル初期化ユーティリティ（init_monitoring_db）を利用して冪等に DB 準備
- 実行／注文周り（骨格）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の呼び出し・組み立てロジックを統合
  - RiskManager に対するデフォルト設定を実装（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker など）
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（signal_rank によるタイブレーク）
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等配分へフォールバック）
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存保有のセクター比率計算と候補除外）
    - calc_regime_multiplier: レジームに応じた乗数（bull/neutral/bear を実装、未知はフォールバック）
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score に対応した株数決定ロジック（単元株丸め、aggregate cap スケーリング、cost_buffer を考慮）
    - aggregate スケールダウン後の端数処理（lot_size 単位での追加配分ロジックを実装）
- ユーティリティ
  - ログ設定ユーティリティ: kabusys.utils.logging_setup
    - stdout ストリームハンドラ + 日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーへ統一的に設定
    - ログレベル・ログディレクトリの環境変数優先解決
    - ファイルハンドラ作成失敗時にコンソール出力のみで継続するフォールバック
  - プロセス優先度／CPU affinity ユーティリティ: kabusys.utils.process_priority
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（psutil 利用）
    - CPU affinity を最初の N コアに固定する機能を提供
- 運用ツール
  - Paper Trading 検証レポート生成スクリプト: kabusys.tools.paper_verification_report
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出
    - デフォルトと比較する閾値（稼働率 >= 99%, fill >= 90%, send >= 95%, P95 <= 200 ms）で PASS/FAIL 判定
    - --from / --to / --db オプション対応
- 監視／ロギング等の運用配慮
  - 起動時にプロセス優先度を "high" に設定する呼び出しを実行スクリプトの先頭で行う（set_process_priority("high")）
  - stop/kill フラグや PID ファイル管理を使った安全停止の仕組みを備える
- 設定検証の実用性向上
  - validate_config は PyYAML の有無に応じて YAML 検証をスキップ可能にし、設定ファイルの存在・パース検査を行う
  - 本番環境向けの警告チェック（LINE 通知設定の未設定、KILL_FLAG_CLEAR_ON_START=1 の危険性など）を追加

Changed
- アプリ全体で Settings を通じた環境依存設定の参照に統一
- ロギングの初期化処理を共通化（すべての主要起動スクリプトで setup_logging を使用）
- run_monitoring と run_execution で DuckDB/SQLite 接続確保とクローズ処理を明確にした（finally でのクローズ）

Fixed
- 細かな堅牢性強化
  - 環境変数パーサで quote 内のバックスラッシュエスケープ、インラインコメント処理を考慮
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルトにフォールバックし、警告ログを出力

Deprecated
- （現状なし）

Removed
- （現状なし）

Security
- 環境変数の必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を明示し、未設定時に起動前にエラーを報告する仕組みを提供

---

注意事項（実装から推測）
- research モジュール等、未完成の関数が残っている箇所があるため本番導入前に追加実装・テストが必要。
- position_sizing の price 欠損（0.0）の扱いに関する注記が残っており、価格取得失敗時のフォールバックロジックの検討が推奨される。
- 一部の操作（プロセス優先度変更、CPU affinity 設定、ファイル作成等）は権限不足やプラットフォーム差異により失敗する可能性があり、ログで警告を出してスキップする設計となっている。

---

作成: コードベースの内容から推測して CHANGELOG を作成しました。必要であれば、各項目をより詳細に分解（コミット単位や PR 単位の記述）したり、日付や担当者を追加することもできます。どの粒度で記載したいか指示してください。