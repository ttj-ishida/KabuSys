# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

参考: https://keepachangelog.com/ (日本語訳に準拠)

## [Unreleased]
- なし（新規リリースに向けた未リリース変更はここに記載します）

## [0.1.0] - 2026-04-16
初回リリース。以下の機能群・ユーティリティ・ツールを追加しました（コードベースから推測して記載）。

### Added
- 基本情報
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
- 設定管理
  - kabusys.config.Settings：環境変数 / .env ファイルからアプリケーション設定を読み取るクラスを追加。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - .env/.env.local の読み込み順と上書きロジック（OS 環境変数の保護）。
    - 複雑な .env 行パース（export プレフィックス、クォートとエスケープ、コメント処理）に対応。
    - 各種プロパティ：J-Quants / kabu API、LINE、DuckDB/SQLite パス、PID/フラグパス、リソース閾値、環境種別（development/paper_trading/live）等を提供。
    - PAPER_FILL_MODE 等の値検証（不正値で ValueError を送出）。
- 実行スクリプト
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）の検知で安全終了。
    - 監視用 DB は環境にかかわらず production 用 sqlite_path を使用する設計。
    - DuckDB 接続、monitoring DB 初期化を実行。
    - プロセス優先度を "high" に設定（起動時）。
  - run_execution.py：ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite を使用（data/paper_trading.db デフォルト）し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント切替（モック/実運用）。
    - ExecutionEngine をバックグラウンドスレッドで実行、停止フラグによる安全停止、PID ファイル管理。
    - 依存コンポーネント組立（OrderRepository, OrderManager, RiskManager, Reconciler 等）とデフォルト RiskConfig を提供。
- ユーティリティ
  - kabusys.utils.process_priority：プラットフォームを吸収したプロセス優先度設定ユーティリティを追加。
    - set_process_priority("high"|"normal"|"low")
    - set_cpu_affinity(cpu_count)（指定が None の場合は変更しない）
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応、権限不足等は警告ログでスキップ。
- ポートフォリオ構築
  - kabusys.portfolio:
    - portfolio_builder.select_candidates / calc_equal_weights / calc_score_weights：候補選定と重み計算（等配分・スコア配分）を実装。
    - risk_adjustment.apply_sector_cap / calc_regime_multiplier：セクター上限適用とレジーム乗数（bull/neutral/bear）を実装。
    - position_sizing.calc_position_sizes：各銘柄の発注株数算出（risk_based / equal / score）、lot 単位丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りなどを実装。
- 研究（Research）モジュール
  - kabusys.research:
    - factor_research.calc_momentum / calc_volatility / calc_value：DuckDB 上の prices_daily / raw_financials を利用したモメンタム・ボラティリティ・バリュー計算を実装。MA200 / ATR20 /各種リターン等を算出。
    - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank：将来リターン計算、IC（Spearman）、ファクター統計サマリー、ランク生成（同順位は平均ランク）を追加。
    - zscore_normalize を data.stats から再公開するエクスポートを追加。
- AI / ニュース NLP
  - kabusys.ai.news_nlp：raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込むロジック（設計）を追加。
    - ニュースウィンドウ計算（JST→UTC 変換）、記事集約、銘柄ごとの文字数/記事数制限、バッチ送信（最大 20 銘柄）、JSON Mode 出力の期待、スコアクリップ（±1.0）、リトライ/バックオフ戦略、部分書き込み（既存スコア保護）の方針が記載されている。
    - OpenAI API キー未指定時は ValueError を送出。
- ツール
  - kabusys.tools.paper_verification_report：Paper Trading 検証レポート生成ツールを追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - レポートは稼働率・注文成功率・送信率・P95 レイテンシ等を集約して出力。
    - PASS/FAIL 判定に用いる閾値（稼働率 99%、注文成功率 90% 等）を内蔵。
    - コマンドライン引数 --from / --to / --db をサポート。
- DB 初期化ヘルパー
  - monitoring.monitoring_db.init_monitoring_db を呼ぶことで監視用テーブルの存在を保証（冪等）。
- DuckDB / SQLite の活用
  - DuckDB を分析用途（prices_daily / raw_financials 等）に利用、SQLite はランタイムログやトレード履歴等に使用する想定。

### Changed
- （初回リリースのため主に設計上の記載）
  - 環境読み込みポリシー: OS 環境変数 > .env.local > .env の順で読み込みされる自動ロードを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - run_monitoring: 監視用途は KABUSYS_ENV にかかわらず production 用 sqlite_path を使うという挙動（運用上の注意）。

### Fixed
- 実装上の堅牢化（入力検証・エラー時のフォールバック等）
  - Settings の各検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）で不正値は明示的にエラーとするよう実装。
  - .env パーサーはクォート内のエスケープ、インラインコメント処理を正しく扱うように実装。
  - research.feature_exploration.rank：同順位（ties）は平均ランクで処理し、丸め誤差対策として round(..., 12) を用いるなど精度面を考慮。
  - position_sizing: aggregate cap 適用時のスケール処理と lot 単位での残余配分を安定化。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で明示的に指定する必要があり、不在時はエラーを返す設計（安全性・明示性の確保）。

---

注記:
- 上記は提供されたソースコードから推測してまとめた CHANGELOG です。実際の開発履歴（コミットログ・公開履歴）とは差異がある可能性があります。必要であればリリースノートをもっと詳細（コンポーネント別の変更点や既知の制限・TODO）に展開します。