Keep a Changelog に準拠した変更履歴

すべての変更はソースコードから推測して記載しています。実際のコミットログとは異なる場合があります。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------
Added
- プロジェクト初期リリース。パッケージ情報を kabusys.__version__ = "0.1.0" として定義。
- 実行エントリ:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境変数 KABUSYS_ENV により paper_trading 環境時は専用の MockBrokerClient と専用 SQLite DB（data/paper_trading.db）を使用する挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する。
- 設定管理:
  - kabusys.config.Settings: 環境変数/.env ファイル読み込みロジックを実装（.env 自動読み込み、.env.local 上書き、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env パーサーは export 形式、クォート文字列、インラインコメントの扱い等に対応。
  - 各種設定プロパティを提供（J-Quants, kabuAPI, LINE, DuckDB/SQLite パス、paper trading 関連、監視閾値、PID/kill フラグ等）。PAPER_FILL_MODE のバリデーションを実装（instant/partial/never/reject）。
- DB 初期化:
  - init_monitoring_db を使って監視用テーブル群の冪等な初期化を行う（run_* スクリプトで利用）。
- Execution サブシステム:
  - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動処理を追加（実行時に duckdb/SQLite 接続を利用）。
  - RiskManager に対する RiskConfig の既定値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 関連等）。初期ポートフォリオ値は broker.get_available_cash() を使用して設定。
- モニタリング:
  - SystemMonitor を起点としたポーリングループのエラーハンドリング（check_once() の例外をログに残して継続）を実装。
- ユーティリティ:
  - utils.process_priority: プロセス優先度設定と CPU affinity 設定関数を追加。Windows と POSIX（Linux, Darwin, FreeBSD）を吸収する実装で、権限不足や未サポート時に警告を出してスキップするフォールバックを備える。
- ポートフォリオ構築（純粋関数群）:
  - portfolio.portfolio_builder: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を追加。スコアが全てゼロの際に等配分へフォールバックして警告を出す。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、マーケットレジームに基づく乗数 calc_regime_multiplier を追加（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing: position size 計算 calc_position_sizes を追加。risk_based / equal / score の配分方式に対応し、lot_size（単元）丸め、per-stock 上限、aggregate cap（投下資金超過時のスケールダウンと端数調整）を実装。コストバッファを考慮した保守的見積りをサポート。
- リサーチ / ファクター計算:
  - research.factor_research: momentum/volatility/value ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。DuckDB の prices_daily / raw_financials テーブルを想定した SQL ベースの計算で、移動平均・ATR・各種リターン等を算出。データ不足時の None 扱いを明確化。
  - research.feature_exploration: 将来リターン計算 calc_forward_returns、IC（Spearman）計算 calc_ic、rank / factor_summary（count/mean/std/min/max/median）を実装。外部ライブラリ非依存で標準ライブラリのみを利用。
  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。
- AI / ニュース NLP:
  - ai.news_nlp: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込むスコアリング処理を追加。特徴:
    - ニュースウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）
    - 記事トリム（1 銘柄あたり最大記事数・文字数制限）
    - バッチサイズ（最大 20 銘柄）、JSON Mode 出力期待、レスポンス検証、スコアを ±1.0 にクリップ
    - 429/ネットワーク/5xx 等は指数バックオフでリトライ（上限あり）
    - 部分失敗を避けるため書き込み時は対象コードを限定して DELETE→INSERT を行う戦略
- ツール:
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH を参照して指定期間のシステム安定性、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し、閾値（稼働率 99.0%、注文成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づいて PASS/FAIL を判定する。P95 計算や各種欠損時の N/A 処理を実装。
- DuckDB を利用する箇所を導入（research, ai などの分析処理で使用）。

Changed
- .env 自動ロードの挙動: OS 環境変数を保護するため .env/.env.local 読み込み時に既存キーを保護（.env.local は override=True で上書き可能だが protected により OS 側キーは上書きされない）。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとする（set_process_priority を最初に呼び出す）。

Fixed
- 環境変数のパースに関する堅牢性向上:
  - export プレフィックスサポート、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等を実装し .env の柔軟な記述を許容。
- run_monitoring のポーリング間隔取得で不正値（0 以下・非整数）を検出した際にデフォルトへフォールバックし、ログ出力するように改善（sleep に渡す不正値による ValueError 回避）。
- DB 初期化呼び出し（init_monitoring_db）は冪等であることを明記/期待する実装に合わせて使用。

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY から解決する（未設定時は ValueError を送出して明示的に失敗）。

Notes / Known limitations
- 一部処理は外部リソース（DuckDB のテーブル、SQLite DB、外部ブローカー API、OpenAI）を前提としており、実行環境にそれらが整っている必要があります。
- position_sizing の price が欠損（0.0）の場合、現在は exposure が過小見積りされる可能性がある旨の TODO コメントが残されています（将来的にフォールバック価格導入の考慮）。
- ai.news_nlp の API 呼び出しの具体的な実装詳細（例: _fetch_articles, _score_chunk の実装）はソースの一部で省略/続きがある可能性があり、エラーハンドリングや部分書き込み戦略はコードを参照してください。

今後の作業候補（推奨）
- unit/integration テストの整備（.env パーサ・position sizing の境界条件・AI API のリトライ動作など）。
- position_sizing の銘柄別 lot_size サポート、価格フォールバック実装。
- ai.news_nlp のレスポンス検証・ログ強化と失敗時の部分復旧戦略の明文化。

--- 
（以上）