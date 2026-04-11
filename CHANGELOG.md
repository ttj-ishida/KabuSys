CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに従って記載しています。
このファイルはコードベースの現状をコードから推測してまとめたもので、実際のコミット履歴とは異なる場合があります。

Unreleased
----------
（次回リリースに向けた変更内容をここに記載します）

0.1.0 - 2026-04-11
-----------------

Added
- 基本初期リリースを追加。
- 実行エントリ:
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。Paper Trading（KABUSYS_ENV=paper_trading）向けに本番 DB と分離された専用 SQLite（data/paper_trading.db をデフォルト）を使用する処理を実装。プロセス優先度を最初に High に設定する処理を含む。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
- 設定管理:
  - config.py: .env/.env.local の自動ロード（優先順位: OS 環境変数 > .env.local > .env）と、ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を実装。プロジェクトルートの自動検出（.git または pyproject.toml による）を実装。環境変数の厳密チェック・取得用 Settings クラスを提供（多くのプロパティとバリデーションを実装）。
  - .env パーサ: export プレフィックス対応、クォートとバックスラッシュエスケープの処理、インラインコメントの取り扱いを実装。
- DB / 分析基盤:
  - DuckDB 統合: 各種研究・AI モジュールは DuckDB 接続を受け取って prices_daily / raw_financials / raw_news 等のテーブルを参照する設計。
  - init_monitoring_db を使用した監視テーブル初期化を run スクリプトで確実に実行。
- Execution コンポーネント（実行系）:
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager を用いた注文実行パイプラインを追加。RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装。ExecutionEngine は PID ファイルの扱い、duckdb 接続の受け渡し、run_session による実行を想定。
- Portfolio 構築:
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順で上位 N を選択（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を提供。スコア合計が 0 の場合は等金額へフォールバックし WARNING を出力。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数決定ロジックを実装。単元株（lot_size）丸め、ポートフォリオ単位・銘柄単位の上限、aggregate cap（現金上限）に応じたスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮するロジックを実装。端数処理で残差に基づく追加配分も実装。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を防ぐため既存保有比率に応じて候補を除外する処理（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた資金投入乗数（1.0/0.7/0.3）を提供。未知レジームは 1.0 へフォールバックし WARNING を出力。
- Research（因子・解析）:
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離率を計算。データ不足時は None を返す。
    - calc_volatility: ATR(20)・相対 ATR・20日平均売買代金・出来高比率を計算。NULL 伝播に注意した実装。
    - calc_value: raw_financials から最新の EPS/ROE を取得して PER/ROE を算出。target_date 以前の最新レコード取得でルックアヘッドを防止。
  - research.feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括で取得するクエリ実装。入力バリデーション（horizons の範囲）あり。
    - calc_ic / rank / factor_summary: スピアマン IC（ランク相関）計算、ランク付け（同順位は平均ランク）、ファクター統計サマリーを実装。最小有効件数チェックや None / 非数値の除外も対応。
  - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート。
- AI / NLP:
  - ai.news_nlp:
    - raw_news テーブルから銘柄別に記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を推定して ai_scores テーブルへ書き込む一連の処理を実装。チャンク（最大 20 銘柄）単位で API 呼び出し、トークン肥大化対策（記事数・文字数制限）を実装。
    - API 呼び出しはリトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。レスポンスの厳格バリデーション（JSON パース、results 配列、code の正規化、スコアの有限性）を行い、スコアは ±1.0 にクリップ。
    - DB 書き込みは部分失敗時に既存データを保護するため、スコア取得済みコードのみに対して DELETE → INSERT を実行（トランザクション制御、DuckDB executemany の空リスト制約に対応）。
    - API キーが未設定の場合は ValueError を送出して明示的に失敗するようにした（呼び出し側でキャッチ可能）。
  - ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次市場レジーム判定を行うモジュールを追加。マクロニュース抽出はキーワードベース、LLM 呼び出しは独立実装で news_nlp と結合を避ける設計。API 失敗時は macro_sentiment=0.0（中立）で継続するフェイルセーフあり。
- Utils:
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX の差分を吸収してカレントプロセスの優先度（high/normal/low）を設定。権限不足や非対応 OS の場合は安全にスキップして警告ログを出力。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアにピン留めする util。引数バリデーションと例外ハンドリングを実装。

Changed
- 環境変数ロードの挙動を明確化:
  - OS 環境変数は保護され、.env/.env.local による上書きは制限される（protected set の導入）。
  - .env のパース仕様を拡張（export プレフィックス、クォート中のバックスラッシュエスケープ処理など）。
- ルックアヘッドバイアス対策:
  - ai/news_nlp と ai/regime_detector、research のクエリ・日付扱いで datetime.today()/date.today() を直接参照しない実装方針に従う設計になっている点を明記（target_date を明示的に受け取る API）。
- モニタリング:
  - run_monitoring は監視用 DB として常に Settings.sqlite_path（本番側）を使用する点をドキュメント化。

Fixed
- ファクター重みが全て 0 の場合、calc_score_weights が等金額配分にフォールバックして警告を出すように改善（div/0 回避）。
- .env パースの不正行やコメント処理、クォート・エスケープの取り扱いによる環境変数読み込みの安定性を向上。
- DuckDB に対する executemany の空リスト問題に対処するため、空パラメータのチェックを導入（ai.news_nlp の DB 書き込み箇所）。

Security
- OpenAI API キーが未設定の場合は明示的にエラーを返す箇所を追加（ai モジュール）。これにより誤った無音失敗を防止。
- プロセス優先度・CPU affinity の設定で権限不足が発生しても例外を露出せず警告に留めることで実行継続性を確保。

Notes / Known limitations
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別単元対応を想定）。
- price の欠損（0.0）によりエクスポージャーが過少見積りされる可能性があるため、将来的に前日終値や取得原価などのフォールバック価格の導入を検討する旨の TODO が残されている。
- ai.news_nlp のレスポンスバリデーションは保守的に設計されており、LLM の返答フォーマット逸脱時には該当チャンクをスキップする（部分欠損が発生する可能性あり）。
- run_monitoring が本番 sqlite_path を常に使用する点は運用上の意図的な設計であるため、テスト環境で同じ挙動を期待しないこと。

ライセンスや貢献ガイド等のメタ情報はこの CHANGELOG に含めていません。必要であれば追記してください。