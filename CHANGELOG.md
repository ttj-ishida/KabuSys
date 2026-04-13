CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 全体
  - 初回リリース。KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 実行関連
  - run_execution.py: 実行エンジン起動スクリプトを追加。
    - プロセス優先度を設定するユーティリティを起動時に呼び出し（high）。
    - 環境による DB 分離: KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離。DuckDB は共通で使用。
    - BrokerClientFactory を利用して適切なブローカークライアント（モック含む）を生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine を run_session() で起動。
    - RiskManager に初期化時のリスク設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックし警告をログ出力。
    - 監視は常に本番 sqlite_path を使用（環境に依存せず）。
    - プロセス優先度設定、SQLite/DuckDB 接続初期化、監視ループの例外保護と正常終了（KeyboardInterrupt）処理を実装。

- 設定・環境変数管理
  - config.py: 環境設定管理モジュールを追加。
    - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）を実装。OS 環境変数は上書きされないよう保護。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化サポート。
    - .env パース機能強化:
      - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント取り扱い、無効行スキップ。
    - Settings クラスで各種プロパティを提供（トークン、API ベース URL、DB パス、paper_fill_mode の検証、監視閾値、PID/KILL フラグ管理、環境名の検証など）。
    - paper_fill_mode の有効値チェック（instant/partial/never/reject）およびエラー報告。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。コマンドライン引数 --from/--to/--db をサポート。
    - システム稼働率・注文成功率・送信率・P95 レイテンシなどを集計し、閾値に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタの SQL パラメータ化、DB 存在チェック、テーブル欠損時のフォールバック（OperationalError のハンドリング）を実装。
    - デフォルト DB パスは data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH をサポート。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコア全てが 0 の場合は等金額配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する apply_sector_cap を追加（売却予定コードをエクスポージャー計算から除外可能）。
    - レジーム乗数 calc_regime_multiplier を追加（bull/neutral/bear に対する乗数、未知レジームは警告と共にフォールバック 1.0）。
  - portfolio/position_sizing.py:
    - 株数決定ロジック calc_position_sizes を追加。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap とスケールダウン処理、端数処理（lot 単位、残差に基づく追加配分）を実装。
    - 価格欠損時のスキップとデバッグログを実装。

- ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows と POSIX を吸収）。
    - set_process_priority("high"|"normal"|"low") と set_cpu_affinity(cpu_count) を提供。
    - psutil が利用できない・権限不足の場合は警告ログを出してスキップ。

- リサーチ
  - research/factor_research.py:
    - モメンタム、ボラティリティ、バリュー（calc_momentum, calc_volatility, calc_value）ファクター計算を DuckDB を用いて実装。
    - 各関数は prices_daily / raw_financials テーブルを参照し、データ不足時に None を扱う一貫した設計。
  - research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）を追加。
    - 外部ライブラリに依存せず、標準ライブラリのみで実装。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）へ送って銘柄ごとのセンチメントを計算し ai_scores テーブルへ書き込む score_news を追加。
    - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチ送信（最大 _BATCH_SIZE=20）、トークン肥大化対策（記事数・文字数制限）、JSON Mode を前提とした堅牢なレスポンス検証、スコアの ±1.0 クリップを実装。
    - リトライ（429/ネットワーク/5xx）に対する指数バックオフ、部分失敗時のテーブル保護（対象コード限定の DELETE→INSERT）などのフェイルセーフ設計。

Changed
- config.py / env ローダー
  - .env の読み込み順序と保護ポリシー（OS 環境変数を protected として上書きを制御）を明文化。
  - プロジェクトルート検出を __file__ を起点に行うことで作業ディレクトリ（CWD）依存を排除。

Fixed
- run_monitoring.py
  - MONITOR_POLL_INTERVAL の不正値（非整数・0 以下）ハンドリングを追加し、例外が発生する代わりにデフォルトへフォールバックして警告を出力。
- tools/paper_verification_report.py
  - DB 欠損やテーブル欠損時に例外で落ちないよう OperationalError を捕捉してフォールバックするように修正。
- position_sizing.py
  - aggregate cap スケーリング時に lot_size 単位で切り捨て・再配分することで端数処理の不整合を解消。

Security
- config.py
  - .env 自動ロードで OS 環境変数を保護する設計を採用（.env による意図せぬ上書きを回避）。
  - OpenAI API キーは明示的に引数または OPENAI_API_KEY 環境変数から読み取る。未設定時は ValueError を投げて明示的に対処させる。

Notes / Known limitations
- ai/news_nlp.score_news は OpenAI クライアント利用を前提としており、API 利用料・キー管理に注意が必要。
- position_sizing の lot_size は現状全銘柄共通としている。将来的に銘柄別 lot_size 対応を検討中（TODO コメントあり）。
- apply_sector_cap は price_map に欠損（0.0）がある場合にエクスポージャーを過少見積もる可能性がある旨の注記あり（フォールバック価格の導入検討）。
- duckdb を用いたリサーチ処理は prices_daily/raw_financials 等のテーブル存在を前提としているため、データ整備が必要。

Appendix: 主要な環境変数（デフォルトを含む）
- KABUSYS_ENV (development | paper_trading | live) — default: development
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- DUCKDB_PATH — default: data/kabusys.duckdb
- MONITOR_POLL_INTERVAL — default: 60
- PAPER_FILL_MODE — default: instant（instant | partial | never | reject）
- OPENAI_API_KEY — OpenAI 利用時に必要
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

--------------------------------------------------------------------------------
今後のリリースでは、単体テストの追加、ドキュメントの拡充、銘柄別 lot_size サポート、より詳細なエラーメトリクス出力などを予定しています。