CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-12
-------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基礎機能を追加。
  - 実行・監視エントリポイント
    - run_execution.py
      - ExecutionEngine 起動スクリプトを提供。
      - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、本番 DB と完全分離。
      - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、エンジンのセッション実行を行う。
      - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority）。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを提供。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や非整数）はデフォルトにフォールバックして警告を出力。
      - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
      - check_once() 実行中の例外はログに記録してループ継続するフェイルセーフを実装。
  - 設定管理
    - config.Settings
      - .env 自動ロード機能（プロジェクトルートの .env / .env.local を読み込み、.env.local は上書き）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - .env パーサーは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント処理に対応。
      - 各種設定プロパティを提供（パス、閾値、PID/kill ファイル、PAPER_FILL_MODE バリデーションなど）。
  - ポートフォリオ構築（純関数群）
    - portfolio.portfolio_builder
      - select_candidates: スコア順で候補選定（signal_rank によるタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコアが全て 0 の場合は等配分にフォールバックして警告）。
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に対する縮小）、cost_buffer（手数料・スリッページ見積）を実装。スケーリング時の端数処理で再現性のある割当を実施。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクターごとの既存保有比率で新規候補を除外するロジック。unknown セクターは上限適用外。
      - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく投下資金乗数（未知レジームは警告後 1.0 でフォールバック）。
  - 研究用モジュール（DuckDB ベース）
    - research.factor_research
      - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials テーブルを参照してモメンタム、ボラティリティ、バリュー系ファクターを計算。ウィンドウ不足時は None を返す、安全な集計を実装。
    - research.feature_exploration
      - calc_forward_returns: 将来リターン（複数ホライズン）を計算。horizons のバリデーションあり。
      - calc_ic: スピアマンランク相関（IC）計算（tie を平均ランクで扱う）。有効レコード3未満で計算不能と判定。
      - factor_summary / rank: 基本統計量とランク変換ユーティリティ。
    - research.__init__ により主要関数と zscore_normalize をエクスポート。
  - ニュース NLP スコアリング
    - ai.news_nlp
      - calc_news_window: target_date に対するニュース収集ウィンドウ（JST→UTC 変換）を計算。
      - score_news: raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores に書き込む処理を実装。機能:
        - 1 銘柄あたり記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
        - 最大 _BATCH_SIZE（20）銘柄ずつのバッチ送信、JSON Mode を想定した厳密なレスポンスバリデーション。
        - 429 / ネットワーク断 / 5xx 等に対する指数バックオフによるリトライ制御。
        - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを保護するため、対象コードのみ置換する（DELETE→INSERT の典型的パターンを採用）。
        - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
      - 設計上の注意: datetime.today()/date.today() を直接参照しないなどルックアヘッドバイアス対策を考慮。
  - ユーティリティ
    - utils.process_priority
      - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度（high/normal/low）を設定。権限不足や未対応 OS の場合は警告してスキップ。
      - set_cpu_affinity: カレントプロセスを最初の N コアにピン留め。引数検証と権限例外の安全ハンドリングを実装。
  - ツール
    - tools.paper_verification_report
      - Paper Trading 用 SQLite データを解析して検証レポートを生成する CLI。出力指標:
        - システム稼働率（system_status）
        - 注文成功率（trade_logs の Created/Filled/Sent 集計）
        - リスク却下数（risk_logs）
        - レイテンシ（avg / max / P95）
      - 閾値（稼働率99%、fill 90%、send 95%、P95 200ms）を定義して PASS/FAIL 判定を行う。
      - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）に対応。DB が存在しない場合はユーザ向けメッセージを出力。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0"

Changed
- ログ・例外処理を強化
  - run_monitoring のループ内で monitor.check_once() の例外を捕捉してログ出力し、ループを継続することで監視の堅牢性を高めた。
  - process_priority / cpu_affinity の権限エラー・未実装例外を警告してスキップする実装に変更。

Fixed
- config の .env パーサーの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理を正しく扱うように改善。
  - .env.local の優先順位（上書き）と OS 環境変数保護（protected keys）を正しく適用。
- MONITOR_POLL_INTERVAL の取り扱い
  - 非正の値や非整数が指定された場合にデフォルト値へフォールバックして警告を出すように修正（time.sleep に渡せる安全な値を保証）。

Notes / Known limitations
- news_nlp.score_news は OpenAI API 呼び出しに依存するため、API キーとネットワークが必要。API 呼び出し失敗時は部分的にスコア取得が失敗する可能性があるが、既存データの破壊を避ける設計になっている。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄ごとの lot_size を受け取る拡張が想定されている（TODO コメントあり）。
- 一部 DuckDB クエリは prices_daily/raw_financials 等のテーブル構造に依存するため、期待するスキーマが揃っていることが前提。

ライセンス
- 各ファイルにライセンスヘッダは含まれていません。必要に応じてプロジェクトの LICENSE を参照してください。