CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。  

リリース日付はコードベースから推測した日付を使用しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-13
------------------

Added
- 初回公開リリース。KabuSys の基本コンポーネントを追加。
- 実行 / 監視ランナー
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - 環境変数 KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine を起動。
    - RiskManager の初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を実装。initial_portfolio_value は broker.get_available_cash() から取得。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。値が不正（0 以下や非数）の場合はデフォルトにフォールバックし警告を出力。
    - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
- 設定 / 環境変数管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートの .git または pyproject.toml を検出して .env/.env.local をロード）。
    - .env パーサを実装（`export KEY=val`、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメント処理を考慮）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 各種設定プロパティを提供（J-Quants、kabuAPI、LINE、DB パス、PID/kill フラグ、閾値、環境判定など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- 監視 DB 初期化ユーティリティ
  - monitoring_db.init_monitoring_db を呼び出して監視テーブルが存在することを保証（冪等）。
- ユーティリティ
  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac/FreeBSD）でプロセス優先度（nice/HIGH_PRIORITY_CLASS 等）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応環境で安全にスキップし、適切に警告を出すフォールバック実装。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重（calc_score_weights）を追加。スコア合計が 0 の場合は等金額にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を追加。未知のレジームはログ警告後にフォールバック 1.0。
    - セクターが "unknown" の場合は制限対象外とする挙動を明示。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based", "equal", "score"）に対応した株数決定ロジックを実装。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash）が超過する場合のスケールダウンと端数配分ロジックを実装。
    - cost_buffer による手数料・スリッページ見積りを考慮。
- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB を用いたファクター計算を実装（prices_daily / raw_financials を参照）。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（ATR20、相対 ATR、出来高関連）、バリュー（PER, ROE）を計算する関数を追加。
    - データ不足時の None 処理やウィンドウサイズの安全マージンを考慮した実装。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を追加。外部ライブラリに依存しない実装。
- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）で銘柄ごとにセンチメント（-1.0〜1.0）を付与し、ai_scores テーブルへ書き込むロジックを追加。
    - タイムウィンドウ計算（JST → UTC 変換）を実装（前日 15:00 JST ～ 当日 08:30 JST）。
    - 1回の API 呼び出しで最大 20 銘柄をバッチ送信。1銘柄あたりの最大記事数・文字数制限を実装（トークン肥大対策）。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフのリトライ処理を実装（上限回数あり）。
    - API レスポンス検証（JSON 構造、既知コード、スコア型）とスコアクリップ（±1.0）。
    - 成功した銘柄のみを部分的に置換する安全な DB 更新戦略（DELETE WHERE date=? AND code=ANY(codes) → INSERT）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加（CLI）。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを算出し PASS/FAIL を判定する閾値を定義。
    - P95 計算ユーティリティ、日付フィルタ、各種クエリ（system_status / trade_logs / risk_logs）を実装。
    - --from / --to / --db オプションをサポート。
- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの未設定時は明示的に ValueError を発生させ、キーの漏洩リスクを減らすため外部にキーを出力しない設計。

Notes / 備考
- DuckDB / SQLite をデータ層に採用しており、リサーチ系関数は外部 API に依存しない設計になっています。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後やテスト時に動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 実行環境によってはプロセス優先度や CPU affinity の設定に管理者権限が必要な場合があります。不許可時は警告を出してスキップします。

-----------------------------------------------------------------------------