# CHANGELOG

すべての重要な変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式で記載しています。  
この CHANGELOG は与えられたコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-04-16
初回リリース相当。システムの起動スクリプト、実行エンジン周り、監視・レポーティング、ポートフォリオ構築、リサーチ、ユーティリティ、AI ニュース NLP の基礎機能を実装。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用する。
    - 停止フラグ（data/stop_requested.flag）検出による安全な停止、実行時 PID ファイル管理（data/execution.pid）に対応。
    - ExecutionEngine の組み立て時に BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を統合。
    - RiskManager に RiskConfig を導入し各種リスクパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定可能にした。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明示。
    - 停止フラグでループを終了、例外発生時はログを残して次のポーリングへ継続。

- 設定/環境変数管理
  - config.py
    - .env / .env.local の自動読み込み機能を追加（プロジェクトルートの判定は .git / pyproject.toml を使用）。
    - エクスポート形式（export KEY=...）やクォート、インラインコメント等に対応した .env パーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - Settings クラスを導入し、各種設定（DB パス、OpenAI などのトークン、監視閾値、PID/kill フラグパス、環境種別判定など）をプロパティで取得可能にした。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の検証ロジックを導入。

- ポートフォリオ構築ライブラリ（pure functions）
  - kabusys.portfolio
    - portfolio_builder.py: 候補選定(select_candidates)、等金額/スコア重み(calc_equal_weights / calc_score_weights) を追加。スコア合計が 0 の場合のフォールバックを実装。
    - risk_adjustment.py: セクター集中上限適用 (apply_sector_cap)、市場レジームによる投下資金乗数 (calc_regime_multiplier) を実装。
    - position_sizing.py: position size の決定ロジックを実装（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケーリングと端数配分アルゴリズムを実装。

- リサーチ用モジュール
  - kabusys.research
    - factor_research.py: Momentum / Volatility / Value のファクター計算（DuckDB を利用した SQL 実装）を追加。
    - feature_exploration.py: forward returns 計算、IC（Spearman ランク相関）計算、ファクター統計要約、ランク変換ユーティリティを追加。
    - __init__.py により主要関数を公開（zscore_normalize を kabusys.data.stats から利用）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（もしくは --db）からデータを読み取り、稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）対応、DB が存在しない／テーブルがない場合のフォールトトレラントな処理を実装。

- AI ニュース NLP（下地）
  - ai/news_nlp.py
    - raw_news を集約して OpenAI (gpt-4o-mini) にバッチで問い合わせ、各銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理の骨組みを追加。
    - ウィンドウ計算（前日15:00 JST 〜 当日08:30 JST 相当の UTC 範囲）、バッチサイズ、文字数制限、リトライ（指数バックオフ）等の設計方針を導入。
    - API キー解決ロジックとエラーハンドリング方針を実装。
    - （注）ファイル末尾が途中で切れているが、全体設計と主要ロジックは導入済み。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定と CPU affinity 固定のユーティリティを追加（Windows / POSIX の差分を吸収）。権限不足や未対応 OS の場合は警告を出しフォールバック。

### 変更 (Changed)
- DB 初期化
  - run_execution.py / run_monitoring.py で起動時に監視テーブルの初期化（init_monitoring_db）を呼ぶようにして、監視テーブルの存在を冪等に保証。

- 実行時優先度
  - 起動スクリプトは開始時にプロセス優先度を "high" に設定するようになり、OS 毎の実装差分を utils/process_priority が吸収。

### 修正 (Fixed)
- ロバストネス向上
  - monitoring ループ内で monitor.check_once() が例外を投げた場合でもループを継続し、次のポーリングまで待機するようログ出力の上でハンドル。
  - .env パーサにおいて、クォート内のエスケープやインラインコメントの扱いを改善して誤読を低減。
  - paper_verification_report.py ではテーブル欠損時の sqlite3.OperationalError を捕捉し、レポート生成を続行するフォールトトレラントな挙動を実装。

### セキュリティ (Security)
- 環境変数の取り扱い
  - config._load_env_file に protected 引数（OS 環境変数保護）を導入し、.env ファイルによる既存 OS 環境の上書きを保護。
  - OpenAI API キーや各種トークンは Settings 経由で必須チェックを行い、未設定時は早期にエラーを出す設計。

### 注意点 / 破壊的変更 (Notes / Breaking Changes)
- 監視（run_monitoring.py）は KABUSYS_ENV にかかわらず settings.sqlite_path（本番 DB）を使用する設計になっています。テスト環境で監視を使う場合は sqlite_path を切り替えるか、本番 DB への書き込みを許容するかご注意ください。
- Process priority / CPU affinity は権限や OS に依存するため、実行環境によっては設定が無視される場合があります（権限不足時は警告を出してスキップ）。
- ai/news_nlp.py は設計方針と多くの実装が含まれていますが、ファイル末尾の処理が未完（スナップショット終了）です。実運用前に完全実装および API レスポンス検証ロジックの確認が必要です。

---

今後（Unreleased）に向けた改善案（推測）
- ai/news_nlp.py の完全実装（_fetch_articles, API 呼び出しループ、DB 書き込みトランザクション等）の完了。
- ユニットテストの追加（.env パーサ、position sizing の各アルゴリズム、IC 計算など）。
- ポートフォリオ構築ロジックのパラメータ外部化（設定ファイルまたは Settings 経由）。
- PDF/HTML 等のより見やすい検証レポート出力形式の追加。

（以上）