# Changelog

すべての変更は「Keep a Changelog」フォーマットに準拠して記載します。  
バージョニングは package の __version__ = "0.1.0" に合わせ、初回リリースとしてまとめています（リリース日: 2026-04-17）。

### 0.1.0 - 2026-04-17

概要: KabuSys のコア機能群を初回公開。自動売買エンジンの実行/監視スクリプト、環境設定管理、ポートフォリオ構築・ポジションサイズ計算、リサーチ用ファクター計算、Paper Trading 検証ツール、ニュースNLP スコアリング（OpenAI）等を実装。DuckDB/SQLite を用いたデータ連携を想定したモジュール構成です。

Added
- 実行および監視エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading 時は paper 用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでの engine.run_session 起動と停止フラグ対応を実装。
    - プロセス優先度を起動時に "high" に設定する処理を追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックし警告を出す。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは環境に依存しない設計）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - DuckDB 接続も作成し SystemMonitor に渡す。

- 環境設定 / .env ローダー
  - config.py
    - プロジェクトルート (.git または pyproject.toml) を探索して .env / .env.local を自動ロード（OS 環境変数が優先、.env.local は上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - export KEY=val 形式やクォート、エスケープ、インラインコメント等に強い .env パーサを実装。
    - Settings クラスを導入し、各種設定プロパティを環境変数から取得（検証付き）。
      - データベースパス: SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH
      - Paper Trading 用挙動: PAPER_FILL_MODE (instant|partial|never|reject) の検証
      - システム関連: KABUSYS_ENV 検証（development/paper_trading/live）
      - 監視閾値や PID ファイル等のプロパティを提供
    - settings インスタンスをモジュールでエクスポート。

- ポートフォリオ構築系（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で上位 N 件を選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコア合計が 0 の場合は等分へフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジションをもとにセクター別エクスポージャ算出し、上限超過セクターの候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知のレジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく銘柄ごとの発注株数決定、単元株丸め、per-position 上限・aggregate cap（利用可能現金）適用、cost_buffer（手数料・スリッページ見積）の考慮、スケールダウン時の端数配分ロジックを実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20、相対 ATR、20 日平均売買代金・出来高比率を計算（NULL 値の取り扱いに注意）。
    - calc_value: raw_financials と prices_daily を結合して PER・ROE を計算（最新の財務レコードを銘柄毎に取得）。
    - DuckDB を用いたウィンドウ関数中心の実装で、大量銘柄に対する一括計算を想定。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。入力検証（ホライズンは 1..252）あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。レコード不足や定数系列は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク処理）や基本統計サマリー（count/mean/std/min/max/median）を実装。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX（Linux/Mac/FreeBSD）に対応したプロセス優先度設定（psutil ベース）。権限や未対応プラットフォーム時は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を固定する機能。入力検証と権限エラーの安全ハンドリングあり。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、リスク却下件数、レイテンシ（平均/最大/P95）を集計して標準出力に整形出力。
    - 判定用閾値（稼働率 99% etc.）を定義し PASS/FAIL を出力。
    - コマンドライン引数 (--from, --to, --db) に対応。

- ニュース NLP（OpenAI 連携）
  - ai/news_nlp.py
    - raw_news と news_symbols をまとめ、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores に書き込む処理を実装。
    - 実装方針（抜粋）:
      - ニュース時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供（UTC での比較に使用）。
      - 銘柄単位で記事を集約し、1回の API 呼び出しで最大 20 銘柄程度をバッチ送信。
      - 429 / ネットワークエラー / タイムアウト / 5xx に対して指数バックオフでリトライ（上限あり）。
      - レスポンスのバリデーションとスコアの ±1.0 クリップ、成功分のみ ai_scores に置換（部分更新で他銘柄のスコア保護）。
    - API キー未指定時は ValueError を送出する検証を実装。
    - 設計上、datetime.today()/date.today() へ直接依存しない（ルックアヘッドバイアスを防止）。

Changed
- データベースハンドリングの設計
  - 監視プロセスは環境にかかわらず本番の sqlite_path を使用する仕様を明記（run_monitoring）。
  - 実行プロセスは paper_trading 環境時に paper_sqlite_path を使用し、本番 DB とロジック的に分離（run_execution）。
  - monitoring DB テーブルの初期化（init_monitoring_db）を起動時に冪等的に呼び出すことでテーブル存在を保証。

- 環境変数ローディングの優先順位
  - OS 環境変数 > .env.local > .env の順で読み込む挙動を採用し、OS 側の既存キーは保護する設計に更新（config.py）。

Fixed / Robustness improvements
- 環境値・入力検証の強化
  - MONITOR_POLL_INTERVAL が不正（非整数や 0 以下）の場合は警告を出してデフォルト値（60 秒）にフォールバック（run_monitoring）。
  - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL の有効値チェックを追加（Settings）。
  - calc_forward_returns の horizons 引数検証（正整数かつ <=252）を追加。
  - position_sizing 等で価格欠損や 0 値の扱いに注意するログ出力を追加し、不正データ時のスキップを明示。
  - process_priority / set_cpu_affinity は権限不足や未実装環境で安全にスキップする設計。

- Error handling / Fail-safe
  - Monitoring の check_once() 実行で例外発生した場合はループを継続し、例外ログを出力する安全策を実装（run_monitoring）。
  - OpenAI API 呼び出し時の部分失敗を他銘柄に影響させない（部分置換戦略）方針を採用（ai/news_nlp）。
  - Paper verification レポート生成でテーブルが存在しない場合の sqlite3.OperationalError を捕捉して安全に N/A を扱う実装。

Notes / Known limitations
- ai/news_nlp.py は大枠の処理（ウィンドウ計算、バッチ処理、リトライ、レスポンス検証、書き込み方針など）を実装していますが、SDK 呼び出しの細部や DB クエリの一部は実装状況に応じて追加・調整が必要です（提供コードは途中までのスニペットを含みます）。
- position_sizing の単元丸めは現在 global lot_size（デフォルト 100）に依存。将来的に銘柄別単元導入の余地あり（TODO コメントあり）。
- apply_sector_cap のエクスポージャ算出では price_map に欠損（0.0）を渡すと見積りが過少となる可能性あり。フォールバック価格（前日終値等）を用いる拡張を検討。

Developers
- パッケージのエクスポートを整理（kabusys/__init__.py, portfolio/__init__.py, research/__init__.py）。
- ロガーを各モジュールで利用し、デバッグ・警告メッセージを適切に出力する設計。

----- 

将来的なリリースでは、テストカバレッジ、ドキュメント（API 仕様・実運用手順）や、ニュースNLP のフルワークフロー（OpenAI レスポンス処理の完全実装）を整備することを推奨します。必要であれば、CHANGELOG をより細かく分割（minor/patch 単位）して作成します。