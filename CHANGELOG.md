Keep a Changelog 準拠 — このファイルはこのリポジトリ内で行われた注目すべき変更点を記録します。
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: 以下の CHANGELOG は、提示されたソースコードから実装内容を推測して作成した初期の変更履歴です。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-13
-----------------

Added
- 全体
  - 初回リリース。モジュール群を公開。
  - パッケージメタデータ: kabusys.__version__ = "0.1.0" を設定。

- 環境設定 / ロード (.env)
  - 自動 .env のロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env / .env.local の読み込み順序および上書きルールを導入（OS 環境変数を保護）。
  - export KEY=val、引用符付き値、行内コメントの扱い等に対応する堅牢なパーサを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - Settings クラスを実装し、各種環境変数をプロパティとして取得・検証（例: KABUSYS_ENV/LOG_LEVEL/PAPER_FILL_MODE 等）。

- 実行系（Execution）
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を設定するユーティリティを呼び出し。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全分離して動作。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskConfig の既定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、initial_portfolio_value を broker.get_available_cash() で初期化。

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データの一貫性確保のため）。
    - プロセス優先度を起動時に設定し、SQLite / DuckDB を開いて SystemMonitor.check_once() を定期実行。
    - KeyboardInterrupt を捕捉してクリーンに終了、最後に DB 接続をクローズ。

- プロセス制御ユーティリティ
  - utils/process_priority.py を追加。
    - Windows (psutil の priority class) と POSIX（nice 値）を吸収して set_process_priority(level) を提供。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留め可能。
    - 対応外 OS や権限不足時は警告を出してフォールバック。

- ポートフォリオ構築
  - portfolio モジュールを追加（純粋関数群: DB 非依存、メモリ演算）。
    - portfolio_builder.py
      - select_candidates: スコア降順＋タイブレーク（signal_rank）で候補選択。
      - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を実装。全てのスコアが 0 の場合は等分配にフォールバック（警告）。
    - risk_adjustment.py
      - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター上限を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") による投下資金乗数を実装。未知レジームは 1.0 にフォールバック（警告）。
    - position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した株数算出を実装。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積り、残余キャッシュを使った端数処理ロジックを実装。

- リサーチ（Research）
  - research モジュールを追加（DuckDB を用いたファクター計算・解析）。
    - factor_research.py
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算。
      - calc_volatility: 20 日 ATR / 相対 ATR / 平均売買代金 / 出来高比率を計算。
      - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新報告を選択）。
      - 各関数はデータ不足時に None を返す等の堅牢な挙動を採用。
    - feature_exploration.py
      - calc_forward_returns: 将来リターン（horizons 指定可）を効率的に取得。
      - calc_ic / rank / factor_summary: Spearman ランク相関（IC）、ランク変換、ファクター統計サマリを実装。
    - research パッケージは zscore_normalize を data.stats から再エクスポート。

- AI ニュース NLP
  - ai/news_nlp.py を追加。
    - raw_news を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores に書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を明示的に行い、ルックアヘッドバイアスを回避。
    - バッチサイズ・最大文字数・最大記事数でトークン肥大化対策を実装（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 429 / ネットワークエラー / 5xx に対する指数バックオフのリトライ、レスポンス構造のバリデーション、スコアの ±1.0 クリップ、部分成功時に既存スコアを保護して部分更新する戦略を採用。
    - OpenAI API キー未設定時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading の検証レポートを標準出力に生成する CLI を提供（--from/--to/--db オプション対応）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を計算し、閾値（稼働率 >= 99% 等）で PASS/FAIL を判定。
    - DuckDB/SQLite のテーブル不存在やデータ不足に対して例外を捕捉してフォールバック表示。

Changed
- 初回リリースのため該当なし。

Fixed
- 各モジュールで想定される例外やデータ欠損に対する保護ロジックを追加（例: env 値の不正、DB のテーブル未作成時のフォールバック、API キー未設定検出、psutil による優先度設定失敗の警告など）。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- OpenAI API キーはパラメータ渡しまたは環境変数 OPENAI_API_KEY を要求し、未設定時は明示的にエラーとすることで無効な実行を防止。

注記（Breaking / 注意点）
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様になっています。監視データを分離したい場合は設定（環境変数 SQLITE_PATH 等）に注意してください。
- Settings.paper_fill_mode 等は厳密に検証を行い、無効な値で例外を投げます。デプロイ時の環境変数設定に注意してください。
- position_sizing の出力・ロジックは単元株（lot_size）を仮定しており、将来的に銘柄ごとの lot_size を取り扱う拡張の記載があります。

今後の予定（想定）
- stocks マスタに lot_size を追加して銘柄別単元対応を行う拡張。
- price 欠損時のフォールバック（前日終値や取得原価）を採用してエクスポージャー計算の精度向上。
- ai/news_nlp の実行結果をより堅牢に永続化するトランザクション処理や監査ログの導入。