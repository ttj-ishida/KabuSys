CHANGELOG
=========

すべての注目に値する変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
初回リリース以降の差分は本ファイルに順次追記してください。

Unreleased
----------

（なし）

0.1.0 - 2026-04-13
------------------

Added
- 基本情報
  - パッケージバージョンを追加: kabusys.__version__ = "0.1.0"。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値（0 以下や非整数）ではデフォルトにフォールバックし、警告を出力。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用して DB に接続。
    - プロセス優先度を最初に "high" に設定してから起動。
    - SQLite（監視テーブル初期化）および DuckDB へ接続し、例外はログに記録してポーリングを継続するフェイルセーフ実装。
  - run_execution.py
    - 実行エンジン（ExecutionEngine）起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - プロセス優先度を最初に "high" に設定してから起動。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。読み込み優先度は OS 環境変数 > .env.local > .env。
    - .env パーサは export プレフィックス、クォート内バックスラッシュエスケープ、コメント扱い（クォート外かつ '#' の直前が空白/タブ）、空行・コメント行スキップ等に対応。
    - Settings クラスを提供し、各種環境変数をプロパティ化:
      - J-Quants / kabu API / LINE / DB（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）/ PID/KILL フラグ /しきい値等。
      - PAPER_FILL_MODE のバリデーション（有効値: "instant","partial","never","reject"）を実装。
      - KABUSYS_ENV のバリデーション（"development","paper_trading","live"）と log level の検査を追加。
      - デフォルト値を多数設定（例: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PID_FILE_PATH=data/execution.pid など）。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを実装。
    - Windows 用の HIGH_PRIORITY_CLASS 等と POSIX 用 nice 値のマッピングを用意し、set_process_priority(level) で "high"/"normal"/"low" をサポート。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定する機能を追加（None の場合は無効）。
    - 権限不足や未対応環境では警告ログを出して安全にスキップする実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順でタイブレーク）でソートし上位 N を返す。
    - calc_equal_weights: 等金額配分（1/N）を計算。
    - calc_score_weights: スコア比率で重みを計算。全スコアが 0.0 の場合は等金額配分にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を計算して超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: weight / candidates / portfolio_value / available_cash 等を基に発注株数を計算。allocation_method に "risk_based"（リスクベース）と "equal"/"score" をサポート。
    - 単元株（lot_size, デフォルト 100）に丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）を尊重。資金超過時には保守的にスケーリングして端数は lot 単位で再配分するロジックを実装。
    - cost_buffer によりスリッページ等を保守的に見積もる挙動を追加。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m および ma200 乖離率を prices_daily から計算（MA200 が揃っていない銘柄は None）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。真の True Range 計算で NULL 伝播を制御。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得して PER/ROE を計算（EPS が 0 または NULL の場合は None）。
    - DuckDB を直接使用する SQL ベースの実装で、性能と再現性を重視。
  - research/feature_exploration.py
    - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト [1,5,21] 営業日）先のリターンを一括で計算。horizons の入力検証あり（正の整数かつ <=252）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。データ不足（有効レコード < 3）なら None。
    - rank / factor_summary: ランク変換（同順位は平均ランク）とファクター列の基礎統計量（count/mean/std/min/max/median）を提供。外部ライブラリに依存しない標準ライブラリ実装。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）に対して銘柄単位のセンチメントスコア（-1.0 ～ 1.0）を取得し ai_scores テーブルへ書き込む処理を実装。
    - 処理の要点:
      - ニュース収集ウィンドウは JST ベースで「前日 15:00 JST ～ 当日 08:30 JST」を UTC に変換して比較（calc_news_window 実装）。
      - 1 回の API コールで最大 _BATCH_SIZE=20 銘柄を処理。1 銘柄あたりの記事は最大 10 件、かつ文字数上限 3000 文字でトリム。
      - OpenAI クライアント（OpenAI API）を使用。429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（上限 _MAX_RETRIES=3）。
      - レスポンスのバリデーション、スコアの ±1.0 でクリップ、部分成功時は対象コードのみを DELETE→INSERT で置換して既存データを保護（部分失敗フェイルセーフ）。
      - API キーは引数 api_key または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
      - JSON Mode を前提としたシステムプロンプトと出力検証を行う。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 検証指標:
      - 稼働率（uptime_pct）閾値 99.0%
      - 注文成功率（fill_rate）閾値 90.0%
      - 送信率（send_rate）閾値 95.0%
      - P95 レイテンシ閾値 200 ms
    - trade_logs / system_status / risk_logs などから集計を行い、PASS/FAIL 判定と詳細サマリを標準出力に出力。
    - コマンドライン引数で期間（--from/--to）と DB パス（--db）を指定可能。デフォルト DB は data/paper_trading.db。
    - P95 計算および各種 NULL 安全処理を実装。対象テーブル未存在時は sqlite3.OperationalError を捕捉して N/A 表示にフォールバック。

- DB 関連
  - 監視テーブル初期化ユーティリティ（monitoring.monitoring_db.init_monitoring_db）を run スクリプトから呼び、監視テーブルの存在を冪等に保証するように設計。

Changed
- （初回リリースにつき該当なし）

Fixed
- .env 読み込みでの I/O エラーを warnings.warn で通知して処理を継続するようにし、起動失敗のリスクを軽減。
- process_priority / cpu_affinity は権限不足や未対応プラットフォームで例外が伝播しないように捕捉して警告ログに留める安全設計。

Notes / Implementation details
- 多くのアルゴリズムは「純粋関数」として設計され、DB を参照しないモジュール（portfolio.* 等）は副作用を持たないように実装されています。
- DuckDB はリサーチ系の大規模集計に用いられる前提で組み込まれており、SQL 内でウィンドウ関数や ROW_NUMBER を積極的に利用しています。
- 実行時のプロセス優先度設定や DB パスの切り替え（paper_trading 用 DB 分離）など、運用を想定した安全策が散りばめられています。
- OpenAI 連携はフェイルセーフ（失敗時はログを残してスキップ）を重視し、部分成功時のデータ保護（該当 code のみ更新）を行います。

Acknowledgements
- 初回リリース（0.1.0）はコア機能（実行・監視・ポートフォリオ構築・リサーチ・AI ニュース・運用ツール）を一通り揃えた状態です。今後のリリースでテスト補強、エラーケースの詳細整備、性能改善、拡張（銘柄別 lot_size、さらなるファクター、可観測化など）を予定しています。