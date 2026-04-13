# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  
リンク: https://keepachangelog.com/ja/1.0.0/

なお、以下の変更点はリポジトリ内のソースコードから仕様・挙動を推測して作成しています。

## [Unreleased]
- 今後の変更を記載。

## [0.1.0] - 2026-04-13
初回リリース。

### Added
- 基本情報
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
- 設定・環境変数管理
  - Settings クラスによる環境変数ラッパーを実装。J-Quants / kabuステーション / LINE / DB /監視 /システム設定などをプロパティ経由で取得可能。
  - 自動 .env ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサは export PREFIX、クォート、エスケープ、インラインコメント等に対応。
  - 必須環境変数未設定時に ValueError を送出する _require() を提供。
  - PAPER_FILL_MODE の入力バリデーション（instant/partial/never/reject）。
  - KABUSYS_ENV の有効値チェック（development/paper_trading/live）。
- 実行関連スクリプト
  - run_execution.py：ExecutionEngine の起動スクリプトを追加。paper_trading 環境では専用の paper_trading DB を利用し MockBroker を利用する想定。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する挙動を明示。
- モニタリング
  - init_monitoring_db を呼び出して監視用テーブルを冪等的に初期化する仕組みを導入。
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバック（0 以下や非整数 → デフォルト 60 秒に警告して戻す）。
- 実行コンポーネント組立て
  - BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組立てを実装（run_execution 経路で利用）。RiskConfig や EngineConfig の初期設定を含む。
- プロセス制御ユーティリティ
  - set_process_priority(level) を追加。Windows と POSIX 系（Linux/macOS/FreeBSD）に対応し、権限不足や未実装関数は警告してスキップする。
  - set_cpu_affinity(cpu_count) を追加。利用可能コア数を超える入力に対するデバッグ出力や権限不足の扱いを実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等比重およびスコア正規化による重み計算（全スコア 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用、既存保有をもとに上限超過セクターの新規候補を除外（unknown セクターは無視）。
    - calc_regime_multiplier: market_regime に基づく投下資金乗数（bull/neutral/bear をサポート、未知レジームは警告して 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based, equal, score）に基づく株数決定、単元株丸め、per-stock 上限、aggregate cap（利用可能現金に応じたスケールダウン）を実装。cost_buffer による保守的見積りや lot 単位で端数処理を行う。
- 研究・ファクター計算
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を参照し、各種窓処理・NULL 安全処理を行う。
  - research.feature_exploration:
    - calc_forward_returns（任意ホライズン対応）、calc_ic（スピアマンランク相関）、rank（同順位は平均ランクで処理）、factor_summary（count/mean/std/min/max/median）を実装。外部ライブラリ非依存で実装。
  - research.__init__ で主要 API を公開（zscore_normalize を含む）。
- AI / ニュース NLP
  - ai.news_nlp:
    - raw_news / news_symbols を集約し OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメントスコアを生成して ai_scores に書き込む機能を実装。バッチ処理、最大記事数／文字数制限、スコア ±1.0 クリップ、リトライ（429/5xx/タイムアウト等の指数バックオフ）をサポート。
    - calc_news_window による JST ベースのタイムウィンドウ計算（前日 15:00 ～ 当日 08:30 JST を UTC に変換）。
    - API キー未設定時は ValueError を送出して明示的に失敗。
- ツール
  - tools.paper_verification_report:
    - Paper Trading 用の検証レポート生成ツールを追加。検証基準（稼働率、注文成功率、送信率、P95 レイテンシ）を定義し、SQLite DB（デフォルト data/paper_trading.db）から集計して標準出力にレポートを出力。コマンドライン引数で期間指定と DB パス上書き可能。
    - P95 計算、NULL 考慮、テーブル欠如時のフォールバックを実装。
- DB 接続
  - sqlite3／duckdb 接続を使用。DuckDB はリサーチ／AI モジュールで SQL を用いた高速集計に使用。

### Changed
- 設計上の明示（ドキュメント的変更）
  - Monitoring は KABUSYS_ENV によらず常に本番 sqlite_path を使用する（安全性の観点で監視用 DB を環境分離しない決定をコメント化）。
  - run_execution は paper_trading 環境で paper_sqlite_path を利用することで発注処理を本番 DB から分離。
  - .env のロード順序と protected オプションにより OS 環境変数が上書きされないよう保護。
  - research / ai モジュールはルックアヘッドバイアスを避けるため、date.today() 等を直接参照しない設計方針を注記。
  - process_priority の実行失敗（権限不足等）は警告にとどめ、プロセス継続を保証。

### Fixed
- 不正入力の安全対策
  - MONITOR_POLL_INTERVAL に 0 以下や非整数が設定された場合に警告を出してデフォルトにフォールバックするように修正。
  - PAPER_FILL_MODE の不正値を検出して ValueError を投げるバリデーションを追加。
  - research モジュールのウィンドウ処理や集計クエリで NULL 値やデータ不足を検出し、必要に応じて None を返すことで計算不能な状況に対処。
  - set_process_priority / set_cpu_affinity の実行で AccessDenied / NotImplementedError を捕捉して警告し、アプリケーションを継続するように修正。
  - ai.news_nlp の API キー解決で未設定時に明確な例外を投げるようにした（早期失敗で誤動作を防止）。

### Security
- OpenAI API キーを明示的に要求し、未設定時は ValueError を発生させることで不正な API 呼び出しを防止。

### Notes / Known limitations
- position_sizing, apply_sector_cap などは price_map の欠損（0.0）によりエクスポージャーが過少評価される可能性があり、将来的な価格フォールバック（前日終値や取得原価）の導入が検討されていることを注記。
- AI スコアリングは外部 API に依存するため、ネットワーク / レート制限に対する部分的失敗を許容し、得られたスコアのみを更新する安全対策を採用。
- tools.paper_verification_report は DuckDB を使用しないため大規模データではパフォーマンス評価が必要。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリース履歴や変更内容と差異がある場合は、差分に応じて編集してください。