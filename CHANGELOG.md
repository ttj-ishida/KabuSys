CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」準拠で記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（未リリースの小さな改善／調整）
- 監視ループのポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能に。0 または負の値、非整数を指定した場合はデフォルト（60秒）にフォールバックして警告を出力するように変更。
- SystemMonitor / ExecutionEngine 起動時にプロセス優先度を最初に「high」に設定するよう起動フローを明確化。
- DB 接続の初期化・クリーンアップの堅牢化（例外時も sqlite3/duckdb 接続を確実に close）。
- OpenAI 呼び出しのバッチ／リトライ処理の挙動改善（バッチサイズ・リトライ上限・エクスポネンシャルバックオフの導入）。
- いくつかのログ文言やデバッグ情報を追加して診断性を向上。

[0.1.0] - 2026-04-13
--------------------
Added
- 初回リリース。以下の主要機能を実装。
  - 起動スクリプト
    - run_execution: ExecutionEngine を起動する CLI エントリポイント（paper_trading 環境時は paper_trading 用 DB を使用し MockBroker を利用可能）。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL による間隔上書き対応、KeyboardInterrupt による graceful shutdown、例外時のログとループ継続。
  - 設定管理
    - kabusys.config: .env 自動ロード（プロジェクトルート検出）、.env/.env.local の読み込み順、export プレフィックス・クォート・インラインコメント対応のパーサ、各種環境変数プロパティ（DB パス、KABUSYS_ENV、閾値等）と入力検証を提供。
  - ポートフォリオ構築（pure functions、DB 非依存）
    - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額およびスコア加重（calc_equal_weights / calc_score_weights）。
    - portfolio.position_sizing: position sizing（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケールダウンロジック。
    - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear マップ）。
  - リサーチ／ファクター計算（DuckDB ベース）
    - research.factor_research: Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）。DuckDB 上でウィンドウ関数を用いた集計実装。
    - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC 計算 (calc_ic)、ファクター統計サマリー (factor_summary) とランク関数 (rank)。
    - research パッケージは pandas 等に依存せず純粋に標準ライブラリ + DuckDB SQL で動作する設計。
  - AI ニュース NLP
    - ai.news_nlp: raw_news から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）にバッチ送信しセンチメントスコアを ai_scores に書き込む機能。トークン過膨張対策（記事数・文字数トリム）、JSON Mode によるレスポンス検証、スコアの ±1.0 クリッピング、部分更新（該当コードのみ置換）による部分失敗耐性を備える。
  - ツール
    - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ等を集計して検証レポートを標準出力に表示する CLI ツール。P95 計算、閾値ベースの PASS/FAIL 判定を実装。
  - ユーティリティ
    - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX に対応）、CPU affinity 設定ユーティリティ。権限不足や未対応 OS では警告を出して安全にスキップ。
  - パッケージ初期化
    - kabusys.__init__ にバージョン 0.1.0 を設定。

Changed
- DuckDB を分析処理の主要バックエンドとして利用。prices_daily / raw_financials テーブルを前提とした SQL 実装により高速集計を実現。
- .env の自動ロード規則: OS 環境 > .env.local > .env の順で、既存 OS 環境は保護（上書き禁止）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- Execution と Monitoring 起動時に監視テーブルの初期化（init_monitoring_db）を行い、テーブル存在を保証（冪等）。

Fixed
- .env パーサの改善点:
  - export KEY=val 形式に対応。
  - クォートされた値のバックスラッシュエスケープ処理を正しく扱うように修正。
  - クォートなし値のインラインコメント解釈を条件付き（直前が空白／タブ）に限定して誤判定を減らすように改良。

Security
- ai.news_nlp.score_news: OpenAI API キー未設定時は明示的に ValueError を送出して失敗を早期に検出。

Other notes / Implementation details
- 実装はフェイルセーフを重視しており、API の部分的失敗や一時的な DB スキーマ未整備（テーブル欠如）を許容してログを残しつつ継続する設計になっています（例: paper_verification_report は OperationalError を捕捉してデフォルト値を返す）。
- DuckDB に対する executemany の制約等（空 params 回避）を考慮した実装方針が採られています。

Closed issues / Known limitations
- portfolio.position_sizing において price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性がある点は TODO コメントで指摘しており、将来的に前日終値等のフォールバックを導入予定。
- news_nlp の JSON レスポンスバリデーションや OpenAI API のレート制御は整備済みだが、実運用でのスロットリングやコスト管理については運用ルールが必要。

Acknowledgements
- 初版の設計は PortfolioConstruction.md / StrategyModel.md 等のドキュメントに基づいています（コード内コメント参照）。

-----