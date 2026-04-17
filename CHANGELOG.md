CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

（現時点のコミットがリリース済みでない場合に使用します。今回の提出コードは初期リリース相当の内容を含むため、主要変更は 0.1.0 にまとめています。）

0.1.0 - 2026-04-17
------------------

初期公開リリース。

Added
- 全体
  - パッケージ初期構成を追加。パッケージバージョンは kabusys.__version__ = "0.1.0" として設定。
  - DuckDB と SQLite を併用するデータ処理基盤を導入（データ分析や監視用に両方の接続を使用）。

- 実行 / 監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、エンジン起動と停止フラグ処理を実装。
    - 実行中の PID を data/execution.pid に記録する機構を想定。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境変数に関わらず本番 sqlite_path を使用して監視テーブルを参照。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定 / 環境変数管理
  - config.Settings クラスを追加し、アプリケーション設定を環境変数から取得する統一 API を提供。
  - .env 自動読み込み機能を実装:
    - プロジェクトルート判定（.git または pyproject.toml を探索）に基づいて .env / .env.local を読み込む。
    - export KEY=val 形式やクォート・インラインコメントを解釈する独自パーサーを実装。
    - OS 環境変数の保護（protected）や上書き制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 各種設定プロパティを追加（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）。
  - PAPER_FILL_MODE の検証ロジック（有効値チェック）を実装。

- ポートフォリオ構築
  - portfolio モジュールを追加:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N 件を選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分を実装（全銘柄スコアが 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存保有を考慮し上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投入資金乗数を提供（bull/neutral/bear のマッピング、未知レジームは警告とともにフォールバック）。
  - position_sizing:
    - calc_position_sizes: 各銘柄の発注株数決定ロジックを実装（risk_based / equal / score の割当方式、lot_size による丸め、aggregate cap によるスケールダウンと残差処理）。

- リサーチ / ファクター
  - research モジュールを追加:
    - factor_research:
      - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を用いたファクター計算（モメンタム、ATR ベースのボラティリティ、PER/ROE 等）。
    - feature_exploration:
      - calc_forward_returns: 将来リターンの一括計算（可変ホライズン対応）。
      - calc_ic / rank / factor_summary: IC（スピアマン）計算、ランク化、統計サマリー等の分析ユーティリティ。
  - いずれも DuckDB 接続を受け取り、外部 API に依存しない純粋なデータ処理実装。

- AI / ニュース NLP
  - ai.news_nlp モジュールを追加（OpenAI を用いたニュースセンチメントスコアリング）。
    - ターゲット日の前日 15:00 JST ～ 当日 08:30 JST のウィンドウでニュース記事を集約。
    - 銘柄ごとに記事をトリム（最大記事数／最大文字数）してバッチ（最大 20 銘柄）で OpenAI（gpt-4o-mini, JSON Mode）へ送信。
    - 429 / ネットワーク断 / 5xx 等に対する指数バックオフによるリトライ、レスポンスのバリデーション、スコアの ±1.0 クリップ、部分更新（既存スコア保護）等を設計方針に含む。
    - OpenAI API キーを引数または OPENAI_API_KEY 環境変数から取得し、未設定時は例外を送出。

- ユーティリティ
  - utils.process_priority を追加:
    - set_process_priority: Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。対応外 OS や権限不足時は警告を出してスキップ。
    - set_cpu_affinity: カレントプロセスを最初の N コアに固定するユーティリティ（引数検証と権限例外処理あり）。

- ツール
  - tools.paper_verification_report スクリプトを追加:
    - Paper Trading 用の SQLite（デフォルト data/paper_trading.db）を読み取り、稼働率・注文成功率・送信率・P95 レイテンシ等の指標を集計して標準出力へレポート出力。
    - CLI オプション --from/--to/--db をサポート。データ不足時やテーブルが存在しない場合の頑健性処理を実装。
    - 合格基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定義し PASS/FAIL 判定を出力。

Changed
- DB/環境分離方針
  - 監視コンポーネントは KABUSYS_ENV に依らず本番の sqlite_path を参照する設計（run_monitoring）。
  - 実行コンポーネントは paper_trading 環境時に paper_trading 専用 DB を使用し、本番と完全分離（run_execution）。

- 設定ロードの優先順位
  - OS 環境変数 > .env.local > .env の優先順位で自動ロードする仕組みを導入。既存 OS 環境を上書きしない安全な読み込みを実現。

Fixed / Robustness
- 各モジュールで入力不足やデータ欠損に対するガードを追加:
  - ファクター計算、ボラティリティ計算、forward returns などはデータ不足時に None を返す、または空結果を返す設計。
  - position_sizing のスケールダウン処理は lot_size 単位の丸めと残差処理を行い、コミット可能な追加配分を安全に行うアルゴリズムを実装。
  - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックし、警告ログを出す。
  - utils.process_priority / set_cpu_affinity は権限不足や未対応 OS に対して警告を出し処理を継続。
  - tools.paper_verification_report はテーブルが存在しない・DB ファイルがない場合に適切にメッセージを出力して終了。

- CLI / 実行時の停止制御
  - run_execution / run_monitoring はプロジェクト内の data/stop_requested.flag を監視して安全に停止する仕組みを採用。run_execution は既に停止フラグが立っている場合は起動をスキップ。

Notes / Known limitations
- ai.news_nlp の実装は堅牢性・部分失敗時のデータ保護を考慮しているが、API 呼び出し部分や DB 書き込みの細部（例: executemany のパラメータ空チェックなど）は OpenAI の利用ポリシーや実運用での検証が必要。
- position_sizing の価格欠損時（price_map に価格が無い / 0 の場合）は将来的に前日終値や原価でのフォールバックを検討する旨の TODO コメントが残っている。
- Project root の自動検出は .git / pyproject.toml を基準とするため、特殊な配布形態では自動 .env ロードが働かない場合がある（その場合 KABUSYS_DISABLE_AUTO_ENV_LOAD による制御が利用可能）。

Acknowledgments
- 本リリースは DuckDB / SQLite / psutil / OpenAI クライアント等のライブラリを前提に実装されています。運用環境に応じた設定（環境変数、DB ファイルパス、API キー等）の準備を行ってください。

-----