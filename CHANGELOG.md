Keep a Changelog に準拠した CHANGELOG.md（日本語）

このリポジトリの変更履歴を以下に示します。各エントリは Keep a Changelog の形式（Unreleased / バージョン / Added / Changed / Fixed / Deprecated / Removed / Security）に従っています。

注意: 以下の内容はソースコード（src/ 以下）から推測して作成した要約です。

Unreleased
---------

- なし

0.1.0 - 2026-04-13
-----------------

Added
- 基本アプリケーションパッケージを追加（kabusys）。
  - バージョン情報: __version__ = "0.1.0"
- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）。
  - .env パーサ実装（export KEY=val, クォート、エスケープ、インラインコメント処理対応）。
  - 必須環境変数取得ヘルパー _require()。
  - 各種設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須項目。
    - DB パス: DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）。
    - Paper Trading 用 DB: PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）。
    - Paper Trading の動作モード: PAPER_FILL_MODE（instant|partial|never|reject）。
    - 監視関連: PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / 各種閾値(CPU/MEM/DISK)。
    - 実行環境: KABUSYS_ENV（development|paper_trading|live）、LOG_LEVEL。
- プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) — Windows / POSIX を吸収して優先度設定（"high"|"normal"|"low"）。
  - set_cpu_affinity(cpu_count) — 指定コア数に固定。
  - アクセス拒否や未対応環境は警告でスキップするフェイルセーフ。
- 実行エントリスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する挙動。
    - プロセス優先度を最初に "high" に設定。
    - sqlite3 / duckdb 接続を確立し、終了時にクローズ。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用（分離された）paper_trading DB を使用（PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時に MockBrokerClient を利用する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - プロセス優先度を最初に "high" に設定。
- モニタリング DB 初期化ユーティリティ（init_monitoring_db の利用箇所あり）
  - monitoring テーブルの存在を保証する処理（冪等性を考慮）。
- Portfolio 構築関数群（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順に並べ上位 N を選定（signal_rank をタイブレークに使用）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化（全スコア 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を抑えるための候補除外ロジック（sell_codes を除外して既存エクスポージャーを計算、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じた投下資金乗数。未知の値は 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算、lot_size（単元）丸め、per-position と aggregate の上限処理、available_cash に対するスケーリング（残差を lot 単位で再配分）。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: PER（EPS が 0/欠損の場合は None）、ROE（raw_financials の最新レコードを使用）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターン取得（horizons のバリデーションあり）。
    - calc_ic: スピアマン順位相関（IC）計算。3 銘柄未満なら None。
    - factor_summary / rank: 基本統計量とランク計算（同順位は平均ランク）。
  - research/__init__.py に zscore_normalize の再エクスポート（kabusys.data.stats 依存）。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）で銘柄ごとにセンチメントスコアを算出し ai_scores に書き込む処理を実装。
  - バッチ処理（最大 20 銘柄/コール）、記事・文字数のトリム、429/5xx/接続問題への指数バックオフリトライ、レスポンス検証、スコアクリップ（±1.0）。
  - score_news() は API キー未指定時に環境変数 OPENAI_API_KEY を要求し、未設定時は ValueError を送出。
  - ニュースウィンドウは JST ベース（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して扱う（calc_news_window）。
  - 部分失敗時に既存スコアを保護するため、更新は該当コードに限定して置換（DELETE → INSERT の戦略）。
- ツール
  - paper_verification_report:
    - Paper Trading の SQLite DB（デフォルト data/paper_trading.db）から検証レポートを生成。
    - 指標: 稼働率（uptime）, 注文成功率（fill rate）, 送信率（send rate）, P95 レイテンシ など。
    - PASS/FAIL 閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ（--from / --to）と --db オプション対応。
    - DB のテーブル欠如に対するフォールバック処理（OperationalError を捕捉して N/A 相当を出力）。
- パッケージのエクスポート整理
  - kabusys.portfolio と kabusys.research の __init__ による公開 API 整備。

Changed
- なし（本リリースは機能の追加が主体と推定）

Fixed
- 不正な MONITOR_POLL_INTERVAL 値（0 以下や非整数）に対して警告を出しデフォルトにフォールバックする処理を採用（run_monitoring）。
- .env 読み込みに失敗した場合に警告（warnings.warn）で失敗を通知するように変更（config）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API の使用に関する注記:
  - score_news() は明示的に API キーを要求（引数または OPENAI_API_KEY 環境変数）。キーが未設定だと ValueError を送出して処理を停止するため、秘匿情報の管理に注意が必要。
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化可能（テスト環境向けの配慮）。

Migration notes / 運用上の注意
- 監視（run_monitoring）は常に settings.sqlite_path（本番用）を利用します。開発や paper_trading と監視 DB を分離したい場合は sqlite_path を変更してください。
- 実行エンジン（run_execution）は paper_trading 環境では settings.paper_sqlite_path を使用して DB を完全に分離します（PAPER_TRADING_SQLITE_PATH で上書き可能）。
- MONITOR_POLL_INTERVAL は環境変数で秒数を指定。1 未満や不正値は無効として 60 秒にフォールバックします。
- PAPER_FILL_MODE の有効値: instant, partial, never, reject。無効な値は ValueError を送出します。
- KABUSYS_ENV の有効値: development, paper_trading, live。無効な値は ValueError。
- LOG_LEVEL の有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL。無効な値は ValueError。
- process_priority の変更には OS 権限が必要な場合があり、権限不足時は警告でスキップされます。

既知の制限 / TODO（コード内コメントより）
- position_sizing.calc_position_sizes:
  - price_map に価格が欠損（0.0）がある場合、エクスポージャーが過小評価される可能性があるためフォールバック価格の導入を検討。
  - lot_size は現状全銘柄共通。将来的に銘柄別単元情報を導入する予定。
- news_nlp:
  - API レスポンスの堅牢性向上や部分失敗時のリトライ戦略のさらなる強化など運用改善余地あり。
- research モジュール:
  - pandas 等の外部依存を避けた実装であるが、大規模データ処理性能・可読性向上のため将来の見直し余地あり。

補足
- 本 CHANGELOG はソースコード（コメント・実装・デフォルト値）から推測して作成したものです。実際のリリースノートとして使用する場合は、追加の検証・編集を行ってください。