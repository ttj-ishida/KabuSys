CHANGELOG
=========
フォーマット: Keep a Changelog に準拠。  
日付はリポジトリ内のコード内容から推測して作成しています。

[Unreleased]
-------------
（なし）

[0.1.0] - 2026-04-16
--------------------
Added
- 全体
  - プロジェクト初期版リリース。自動売買エンジンのコア機能群を実装。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を設定。
- 設定管理 (kabusys.config)
  - .env 自動読み込み（プロジェクトルートの検出: .git / pyproject.toml 基準）。
  - .env / .env.local の読み込み順序と上書きルールを実装（OS環境変数は保護）。
  - export 付き行、クォートされた値、行末コメントを考慮した堅牢なパーサを実装。
  - 各種設定プロパティを提供（KABUSYS_ENV, SQLITE_PATH, DUCKDB_PATH, PAPER_FILL_MODE 等）。
  - PAPER_FILL_MODE の入力検証（instant/partial/never/reject のみ有効）。
  - 環境種別判定用ヘルパ（is_live / is_paper / is_dev）。
- 実行用ユーティリティ (kabusys.utils.process_priority)
  - Windows / POSIX を吸収するプロセス優先度設定 set_process_priority(level) を実装。
  - CPU affinity を制御する set_cpu_affinity(cpu_count) を実装。
  - 権限不足や未対応 OS に対するワーニングとフォールバックを用意。
- 起動スクリプト
  - 実行エンジン起動スクリプト run_execution.py を実装。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、ExecutionEngine の起動を行う。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理（data/execution.pid）をサポート。
    - プロセス優先度を起動時に High に設定。
  - 監視ループ起動スクリプト run_monitoring.py を実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知、例外発生時のログ出力・リトライ継続、KeyboardInterrupt のハンドリングを実装。
- データベース関連
  - sqlite3 / DuckDB 接続を使用する初期化フローを実装（init_monitoring_db 呼び出しを想定）。
- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選択（同点時 signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights を実装。全スコアが 0 の場合は等配分にフォールバックして警告。
  - risk_adjustment:
    - apply_sector_cap: セクター集中の上限チェック（max_sector_pct）と候補除外ロジック。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）と未知レジーム時のフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数算出、単元株（lot_size）丸め、per-stock と aggregate 上限、cost_buffer による保守的見積り、投資合計が現金を超えた場合のスケールダウンと残差の再配分ロジックを実装。
- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB の prices_daily から算出。データ不足時は None を返す設計。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を算出。true_range の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS 不在時は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons の入力検証あり。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を実装（有効レコード <3 の場合は None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）、各種統計量（count/mean/std/min/max/median）を計算。
  - research パッケージは zscore_normalize（kabusys.data.stats 由来）を re-export。
- AI ニュース NLP (kabusys.ai.news_nlp)
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込む設計を追加。
  - バッチ処理（最大 20 コード/リクエスト）、記事数・文字数トリム、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ等を想定したロジックを導入。
  - calc_news_window により target_date に対する JST ベースのニュース収集ウィンドウを正確に計算。
  - score_news は OpenAI API キー解決の検証（引数 または 環境変数 OPENAI_API_KEY）を行う。
- ツール (kabusys.tools)
  - paper_verification_report スクリプトを追加:
    - Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）からシステム安定性、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - パス/フェイル基準を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200ms）。
    - 日付フィルタ (--from/--to)、DB パス指定 (--db) をサポート。DB が存在しない場合のエラーメッセージを整備。
- ロギング / エラーハンドリング
  - 各所でログ出力を充実（INFO / WARNING / DEBUG / EXCEPTION の適切な使用）。
  - DB クエリの OperationalError を捕捉してフォールバックできるように設計（レポート生成等）。

Changed
- 監視と実行の挙動
  - run_monitoring は MONITOR_POLL_INTERVAL の不正値に対してフォールバックし、警告を出力するようになった。
  - run_monitoring は監視用 DB 初期化を常に行う仕様（環境に関わらず本番 sqlite_path を使用）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を利用して本番 DB との完全分離を確保。
- .env 読み込みの挙動
  - 自動読み込みを行う際、OS 環境変数を保護（protected set）して .env/local の上書き動作を制御。

Fixed
- position_sizing / portfolio
  - スコアが全て 0 の場合に 0 除算や不適切な配分が起きないよう等配分へフォールバックし WARN を出力。
  - lot_size を考慮した丸め処理と aggregate スケーリング時の端数処理の安定化を実装。
- factor / research
  - true_range の NULL 伝播を正しく扱うことで ATR 計算が過大評価されないよう修正。
  - calc_forward_returns の horizons 入力検証を追加（正の整数かつ <=252 日）。
- tools.paper_verification_report
  - DB が空またはテーブルが存在しない場合でも安全にレポートを生成（OperationalError をキャッチして N/A 表示）。
- utils.process_priority
  - 未対応 OS や権限不足時に例外を握りつぶさずワーニングでフォールバックするよう改良。

Known issues / Notes
- ai/news_nlp モジュールは安全設計（API リトライ、レスポンス検証など）を導入しているが、実運用時は OpenAI のコスト・レート制限に注意してください。
- position_sizing の price が 0.0（欠損）だった場合、現在はスキップしているためエクスポージャーの過少見積りが発生する恐れがある（将来的に前日終値等のフォールバックを検討）。
- calc_regime_multiplier のベア相場処理は追加の安全弁として multiplier を小さくしているが、実運用戦略側でレジーム検出とシグナル生成の整合性を保つ必要があります。

Contributors
- （コード内容から推測）コア実装者による初期整備。

---  
（注）本 CHANGELOG は提供されたソースコードの内容から機能追加・修正点を推測して作成したものであり、実際のコミット履歴とは一致しない可能性があります。必要に応じて日付やバージョン分割を実際の VCS 履歴に合わせて調整してください。