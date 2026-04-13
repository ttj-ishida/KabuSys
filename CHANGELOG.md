CHANGELOG
=========

すべての重要な変更点を記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット: [Unreleased] → 最新、続いてリリース履歴（降順）。

[Unreleased]
------------

（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-13
-----------------

初回公開リリース。

Added
- 実行エントリ/デーモン
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して起動。
    - 起動時にプロセス優先度を "high" に設定。
    - sqlite3 / DuckDB 接続の確立、init_monitoring_db 呼び出し、PID ファイル指定対応。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に専用の Paper Trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由のブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組立て、ExecutionEngine 起動を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py: Settings クラスを追加／提供。
    - .env / .env.local の自動読み込み機能（プロジェクトルート自動探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 形式、クォート（シングル/ダブル）、インラインコメント等に対応。
    - 各種環境変数とデフォルト値をプロパティとして提供（DB パス、PID/KILL フラグ、しきい値、ログレベル、env 判定 等）。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証を実装。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH サポート。

- プロセスユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定 (set_process_priority) を追加。Windows / POSIX（Linux/ Darwin / FreeBSD）差分を吸収。
    - CPU affinity 設定 (set_cpu_affinity) を追加。
    - 権限不足や未対応 OS の場合は警告して安全にスキップする設計。

- Portfolio 構成関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順選別。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存ポジションのセクター別エクスポージャ計算、上限超過セクターの新規候補除外）。
      - unknown セクターは上限適用外。
      - sell_codes 引数で当日売却予定銘柄をエクスポージャ計算から除外可能。
      - 注意点: 価格欠損時の挙動や将来の価格フォールバックは TODO コメントあり。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数決定ロジック（allocation_method="risk_based" | "equal" | "score"）。
      - 単元株（lot_size）で丸め、1銘柄上限、aggregate cap（available_cash）でスケールダウン。
      - cost_buffer を用いた保守的コスト見積り（スリッページ・手数料）。
      - スケールダウン後の残余キャッシュを利用して、端数（lot 単位）を残差順に配分するアルゴリズムを実装。
      - 将来の拡張用に銘柄別 lot_size のサポートは TODO。

- Research（DuckDB ベース）
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の計算。
    - calc_volatility: ATR（20 日）、相対 ATR、20 日平均売買代金、出来高比等の計算。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE 計算（最新財務レコードの取得ロジックを含む）。
    - 全関数は DuckDB 接続を受け取り SQL で計算、結果を辞書のリストで返す設計。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（複数ホライズン）の一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。
    - rank: 同順位は平均ランクとするランク変換ユーティリティ。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - research/__init__.py に主要関数をエクスポート。

- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルに書き込む処理を実装。
    - バッチサイズ、最大記事数／最大文字数トリム、リトライ（429/ネットワーク/5xx）、指数バックオフを実装。
    - レスポンス検証、スコア ±1.0 のクリップ、部分失敗時に他コードの既存スコアを保護するための部分置換（DELETE→INSERT）戦略。
    - API キーが未指定の場合は ValueError を送出。
    - calc_news_window ユーティリティ（JST ウィンドウを UTC に変換）を提供。
    - 設計上、ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - デフォルト DB パス: data/paper_trading.db。--db オプション/環境変数で上書き可能。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、平均/最大/P95 レイテンシ等を集計。
    - 判定基準（しきい値）を定義（例: uptime >= 99% 等）し、PASS/FAIL 判定を行う。
    - P95 計算、SQL 範囲フィルタリング、データ欠損時の保守的フォールバック実装。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため過去変更なし）

Fixed
- （初回リリースのため過去修正なし）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY にて明示的に提供する必要あり。未設定時はエラー（ValueError）。

Notes / Known limitations
- apply_sector_cap: price が欠損（0.0）の場合、エクスポージャ計算が過少評価される可能性あり（TODO コメント）。
- position_sizing: 将来的に銘柄別 lot_size サポートを想定（現状はグローバル lot_size）。
- ai/news_nlp の挙動は OpenAI のレスポンス形式に依存。API レスポンス仕様変更時にフォールトトレランスが必要。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後にルートが検出できない場合は自動ロードをスキップする。

ライセンス、貢献、バグ報告等についてはリポジトリの README を参照してください。