CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」準拠です。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース。KabuSys の主要コンポーネントを追加:
  - 実行関連
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用して paper_trading 専用 DB（data/paper_trading.db）へ記録する。停止フラグ / PID ファイル管理、デーモンスレッドによる engine.run_session の実行と安全な停止処理を実装。
    - RiskManager / OrderManager / Reconciler 等の組み立てとデフォルト RiskConfig を定義。
  - 監視関連
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境に関わらず本番 sqlite_path を使用する実装。
    - 監視 DB 初期化ユーティリティ（init_monitoring_db）を使用してテーブルの存在を保証。
  - 設定管理
    - config.py: 環境変数と .env ロードの包括的な取り扱いを実装。
      - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD 非依存で .env を自動ロード。
      - .env / .env.local の読み込み順序と OS 環境変数保護（protected keys）を実装。
      - export KEY=val、クォート付き値、行末コメントなどのパースに対応する堅牢な .env パーサを提供。
      - Settings クラスで各種設定値の取得と検証を実装（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の妥当性チェック）。
  - ポートフォリオ構築（pure functions）
    - portfolio.portfolio_builder: シグナルのソート/上位選出 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。スコアが全て 0 の場合は等分配にフォールバック。
    - portfolio.position_sizing: position ごとの株数算出ロジック（risk_based / equal / score）、単元株（lot）丸め、利用可能現金に応じたスケーリング（aggregate cap）を実装。cost_buffer による保守的コスト見積もりをサポート。
    - portfolio.risk_adjustment: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジームはフォールバックしてログ出力。
  - リサーチ / ファクター
    - research.factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB を用いた SQL 実装）。MA200、ATR20、リターンホライズン等を算出。
    - research.feature_exploration: 将来リターン計算、IC（Spearman）の計算、ファクターの統計サマリ実装。ランク化（同順位は平均ランク）や ties への配慮を含む。
  - AI
    - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを計算し ai_scores テーブルへ書き込むフローを実装（バッチ送信、トークン肥大対策、スコアクリッピング、リトライ等の設計方針を含む）。ニュース収集ウィンドウ計算ユーティリティ calc_news_window を提供。
  - ツール
    - tools.paper_verification_report: Paper Trading 用 SQLite DB から各種指標（稼働率 / 注文成功率 / 送信率 / レイテンシ P95 等）を集計し CLI でレポート出力するツールを追加。閾値判定（PASS/FAIL）と期間フィルタ（--from/--to）をサポート。
  - ユーティリティ
    - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定を行うユーティリティを追加。CPU affinity 設定 (set_cpu_affinity) も実装。権限不足や未対応 OS 時は警告を出してスキップ。
  - DB
    - DuckDB を解析用途に採用（複数モジュールが DuckDB 接続を受け取る設計）。
  - パッケージ情報
    - __init__.py にバージョン 0.1.0 を設定。

Changed
- 設計上の決定:
  - 監視プロセス（run_monitoring）は環境に依存せず本番 sqlite_path を使用するようにした（監視は運用データを参照する前提）。
  - Paper Trading 環境は本番 DB から分離（paper_sqlite_path を利用）し、発注シミュレーションログ等を独立管理。

Fixed
- 安全性 / 堅牢性改善:
  - MONITOR_POLL_INTERVAL のパースで 0 以下や不正な値を検出した場合にデフォルト（60 秒）へフォールバックして time.sleep の ValueError 回避。
  - .env ファイル読み込みでファイル読み込みエラー時に警告を出すように変更（読み込み失敗でアプリケーションをクラッシュさせない）。
  - calc_score_weights: 全スコアが 0.0 の場合に等金額配分へフォールバックしてゼロ除算を回避。
  - calc_position_sizes:
    - 単元（lot_size）丸めロジックと aggregate cap のスケーリング処理で残差の配分を安定化（fractional remainder に基づく追加配分）し、利用可能現金超過時のスケールダウンを改善。
    - 価格欠損（price <= 0）をスキップして安全に動作するように改善。
  - apply_sector_cap: sector_map に存在しないコードは "unknown" 扱いとしてセクター制限の適用対象外にすることで誤除外を防止。
  - factor_research / feature_exploration: データ不足時の None ハンドリングや horizons 引数検証を追加して不正入力での例外を防止。
  - set_process_priority / set_cpu_affinity: 未対応 OS や権限不足時に警告して失敗をスキップするようにし、堅牢性を向上。
  - tools.paper_verification_report:
    - P95 計算で空リストを適切に扱い None を返すように実装。
    - SQL 実行時の OperationalError を捕捉してテーブル欠如時でも生成処理が停止しないように改善。

Documentation
- 各モジュールに詳細な docstring を追加。設計方針、入力/出力、想定制約や TODO を明記。
  - portfolio/*、research/*、ai/news_nlp、config.py、utils/process_priority.py、tools/paper_verification_report.py などに注釈・使用例を追加。

Security
- 環境変数の取り扱い: .env の自動ロード時に OS 環境変数を上書きしないデフォルト挙動と、.env.local による上書きを OS 環境変数を保護しつつ行う運用を導入。

Notes / Known limitations
- ai.news_nlp は外部 API（OpenAI）へアクセスするため API キーの設定が必須。失敗時は例外またはスキップ動作となる実装のため、運用時はキーとレート制限に注意。
- 一部モジュールは DuckDB/SQLite のテーブル構造に依存する（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, trade_logs 等）。テーブル未作成時のフォールバックやエラーハンドリングはあるが、運用前にスキーマ整備が必要。
- run_monitoring は監視 DB を本番 DB と同一で参照するため、監視だけの検証環境が必要なら別途環境を用意すること。

以上

（補足）本 CHANGELOG はソースコードの実装から推測して作成しています。実際のリリースノートや変更履歴はリポジトリのコミット履歴・リリースポリシーに基づいて適宜調整してください。