CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

フォーマット:
- Added: 新規追加された機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて記載

Unreleased
---------
（無し）

[0.1.0] - 2026-04-16
-------------------

Added
- 初期公開: KabuSys パッケージ全体を追加。
  - パッケージバージョンは __version__ = "0.1.0"。

- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV による paper_trading モード対応（MockBrokerClient を使用、paper_trading 用 SQLite DB に記録して本番 DB と分離）。
    - 停止フラグ（data/stop_requested.flag）・PID ファイル管理（data/execution.pid）をサポート。
    - プロセス優先度を起動時に High に設定する処理を追加。
  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバックして警告を出す）。
    - 監視は環境に関わらず本番 sqlite_path を使用し、監視 DB の初期化処理を行う。
    - 停止フラグによるループ終了、check_once() の例外ハンドリング、リソースクローズを実装。

- 設定管理
  - config.py: 環境変数 / .env ファイルの読み込み・パース機能を実装。  
    - プロジェクトルート自動検出（.git または pyproject.toml 基準）を行い、.env / .env.local を自動ロード（OS 環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export プレフィックス・クォート付き値・インラインコメント等に対応した堅牢な .env パーサを実装。
    - 各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / システムフラグ等）。
    - 環境変数の値検証: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証と不正値時の例外。

- ポートフォリオ構築ユーティリティ（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。  
    - スコア全てが 0 の場合は等金額配分にフォールバックして警告を出す。
  - portfolio.risk_adjustment: セクター集中制限の適用 (apply_sector_cap) とレジーム乗数計算 (calc_regime_multiplier) を実装。  
    - 既存保有のエクスポージャー計算（当日売却予定銘柄除外）、unknown セクターは上限適用除外、未知レジームでのフォールバックと警告。
  - portfolio.position_sizing: 発注株数計算 (calc_position_sizes) を実装。  
    - risk_based / equal / score の複数配分方式、単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）によるスケーリング、cost_buffer（スリッページ・手数料見積り）対応、価格欠損時のスキップ。

- 研究（research）モジュール
  - research.factor_research: Momentum / Volatility / Value のファクター計算を DuckDB 経由で実装。
    - mom_1m/3m/6m, ma200_dev, atr_20/atr_pct, avg_turnover, volume_ratio, per, roe など。
    - ウィンドウ不足時の None 処理、性能を考慮したスキャン範囲（カレンダーバッファ）を採用。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク化ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - horizons 引数の入力検証、Spearman 相関（ランクの平均処理）を実装。
  - research パッケージ初期エクスポートに zscore_normalize（data.stats 経由）を含める。

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。  
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB 存在チェック、SQL の例外ハンドリングを実装。
    - コマンドライン引数（--from / --to / --db）対応。

- AI ニュース NLP（下流 API 統合）
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores に書き込む処理を実装（バッチ化、トークン肥大化対策、リトライ、レスポンス検証、スコアクリップ等）。
    - ニュース収集ウィンドウ（JST→UTC 変換）計算ユーティリティ calc_news_window を実装。
    - API キー解決、バッチ処理・最大記事数・文字数トリムなどの設計方針を実装。
    - （注）ソースの抜粋は途中で終わっており、完全実装はコード全体で確認が必要。

- ユーティリティ
  - utils.process_priority: プロセス優先度設定と CPU affinity 設定をクロスプラットフォームで実装（Windows と POSIX を吸収）。  
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足等は警告でスキップする安全設計。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db 呼び出しにより、監視用テーブルが存在することを起動時に保証（冪等）。

Changed
- なし（初回リリース）

Fixed
- 環境変数パースや各種値検証を強化して不正設定時の挙動を安定化（.env のパース、PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の検証、MONITOR_POLL_INTERVAL の不正値フォールバックなど）。
- プロセス優先度や CPU affinity の設定で発生し得るアクセス権限エラー等をキャッチして警告に留めるように改善。

Deprecated
- なし

Removed
- なし

Security
- 外部 API キー（OpenAI 等）は環境変数経由で取得する設計。未設定時は明示的にエラーを出すなど、キーの漏洩や未設定に対する明示的な扱いを実装。

Notes / その他
- Paper Trading と本番 DB は分離される設計（settings.paper_sqlite_path / settings.sqlite_path）。
- 多くの計算関数は「純粋関数」として実装され、DB 参照や副作用を最小化している（テスト容易性を意図）。
- 一部ファイル（例: ai.news_nlp）は抜粋で途中までの実装が見られるため、追加の実装・レビューが必要な箇所があり得る。

もしリリース日や対象バージョンの粒度を変更したい、あるいは抜粋ファイルの未完了部分（ai.news_nlp の続き等）を反映して追記したい場合は、その情報を提供してください。