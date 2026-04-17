CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- なし（初回リリースに向けた記録は下の 0.1.0 を参照してください）。

[0.1.0] - 2026-04-17
-------------------

Added
-----

- 基本アーキテクチャおよび主要コンポーネントを実装（初回公開）。
  - パッケージ: kabusys — 日本株自動売買システムの雛形を提供。
  - バージョン定義: __version__ = "0.1.0" を追加。

- 実行用スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と完全に分離する挙動をサポート。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、実行スレッドによるセッション起動と停止フラグ監視を実装。
    - 起動直後に process priority を "high" に設定する処理を追加（utils/process_priority 依存）。
    - 実行 PID 管理用の pid ファイルおよび stop フラグによる安全停止をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。デフォルトは 60 秒。無効な値は警告してデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは常に本番 DB へ記録する設計）。
    - stop フラグ検知・KeyboardInterrupt ハンドリング・例外時のロギング済み継続を実装。
    - 起動時に process priority を "high" に設定。

- 設定管理モジュールを実装。
  - config.py
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出し、.env/.env.local を自動ロード（OS 環境変数優先、.env.local は上書き可能）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサーは export プレフィックス・クォート（バックスラッシュエスケープ）・インラインコメント処理に対応。
    - Settings クラスで環境依存設定をプロパティ化（検証付き）。
      - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject" の検証）
      - KABUSYS_ENV 検証（development/paper_trading/live）
      - LOG_LEVEL 検証
      - 各種監視閾値（CPU/MEM/DISK）や PID / kill flag のパス等

- 監視・補助系ユーティリティを実装。
  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定ユーティリティ。
    - set_process_priority(level) で high/normal/low を設定。権限不足や未対応 OS は安全にスキップして警告。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定（権限や未実装環境では警告してスキップ）。

- ポートフォリオ構築関連の純粋関数群を実装（DB 非依存）。
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソート、同点のタイブレーク実装。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等配分へフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを計算し、セクター集中が上限を超えると候補銘柄を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）を実装。不明レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した発注株数算出ロジックを実装。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積）を考慮した aggregate cap スケーリングを実装。
    - price 欠損時や price <= 0 の銘柄をスキップする安全処理、スケールダウン後の残差を lot 単位で再配分するロジックも実装。

- リサーチ / ファクター計算モジュールを実装（DuckDB を使用、外部 API へはアクセスしない設計）。
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算（ウィンドウ不足時の None 処理）。
    - calc_volatility: ATR(20)・相対ATR・20日平均売買代金・出来高比等を計算（欠損値の正しい伝播を重視）。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE 計算（target_date 以前の最新財務レコードを取得）。
    - 全関数は DuckDB の SQL を利用した実装で、大量データに対しても比較的効率的に動作する想定。
  - research/feature_exploration.py
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を実装。有効サンプルが 3 未満の場合は None を返す。
    - rank / factor_summary: ランク計算（同順位は平均ランク）や基本統計量（count/mean/std/min/max/median）を算出。
  - research/__init__.py で主要関数を公開し、zscore_normalize を kabusys.data.stats から再エクスポートする設計（外部モジュールに依存）。

- AI ニュース NLP スコアリングを実装（OpenAI API と連携）。
  - ai/news_nlp.py（主要機能の実装）
    - 指定 target_date に対するニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して扱う）。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、トークン肥大化対策として記事数・文字数でトリム。
    - 最大 20 銘柄ずつバッチ送信（gpt-4o-mini + JSON モード）し、429/タイムアウト/5xx 等は指数バックオフで最大リトライ。
    - レスポンス検証（results キー、型、既知コード、スコア数値型）を行い、スコアを ±1.0 にクリップ。
    - 成功分のみ ai_scores テーブルへ置換（部分失敗時に既存スコアを保護するためコード絞り込みで DELETE→INSERT）。
    - API キーは引数で渡すか環境変数 OPENAI_API_KEY を参照。未設定なら ValueError を送出。
    - 設計方針としてルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない。

- ツールスクリプトを追加。
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）を解析し、システム稼働率・注文成功率・送信率・P95 レイテンシ等の指標を集計してレポート出力。
    - CLI オプション: --from / --to / --db に対応。
    - PASS/FAIL 基準（閾値）を定義（稼働率 99% / 成功率 90% / 送信率 95% / P95 latency 200ms）し、判定と詳細を出力。
    - DB のテーブル欠如時（OperationalError）は安全に N/A 等で扱う。

- モニタリング DB 初期化ユーティリティを追加（monitoring.monitoring_db から使用）。
  - init_monitoring_db(sqlite_conn) を使用してテーブルが存在することを保証（冪等処理）。

Changed
-------

- （初回リリース）特段の既存機能変更はなし。

Fixed
-----

- （初回リリース）特段のバグ修正履歴はなし。コード内にある TODO と注意点は将来的な改善項目として残す（例: price フォールバックの検討、銘柄別 lot_size の拡張など）。

Deprecated
----------

- なし。

Removed
-------

- なし。

Security
--------

- OpenAI API キーや各種シークレット（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）は環境変数経由で取得する設計。
- config の .env 自動ロードはデフォルトで有効だが、テスト等で無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを用意。
- API キー未設定時に早期にエラーとする箇所（news_nlp.score_news）を設け、誤操作によるサイレントな挙動を回避。

Notes / Known limitations
-------------------------

- ai/news_nlp.py のファイルは末尾が途中で切れている（fetch / 一部処理は省略されている可能性あり）。実環境での完全動作には残り実装の確認が必要。
- research モジュールは DuckDB を前提としており、prices_daily / raw_financials 等のスキーマ依存がある。これらテーブルの整備が前提。
- position_sizing の単元株（lot_size）は現在グローバル固定で処理。将来的に銘柄別単元対応（stocks マスタ）を想定する TODO が存在。
- apply_sector_cap は price_map の欠損（0.0）時に過少見積りとなる可能性がある点をコメントで指摘。フォールバック価格の導入が推奨される。
- process priority / cpu affinity は環境や権限に依存するため、権限不足時は警告ログを出して安全にスキップする実装。

開発者向け
-----------

- ローカルでの環境変数設定はプロジェクトルートの .env / .env.local を使用することを推奨。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading 検証は tools/paper_verification_report.py を利用。DB パスは --db または PAPER_TRADING_SQLITE_PATH で指定できます。
- 大量データ / 本番使用時は DuckDB と SQLite のファイル配置・バックアップ、OpenAI API のレート制限・コスト管理に注意してください。

--- 

（初回リリースのため、今後のリリースでは各モジュールの改善・バグ修正・機能追加を本ファイルに逐次追記します。）