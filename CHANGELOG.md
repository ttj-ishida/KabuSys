# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

※ 日付はリリース作成時点の推定日（2026-04-17）を使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョン 0.1.0 を設定。
  - DuckDB と SQLite を併用するデータ処理基盤を導入（設定経由でパス指定可能）。

- 実行 / 監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の DB を使用して本番 DB と分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory を介して環境に応じたブローカークライアントを生成（paper_trading 時は MockBrokerClient 想定）。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag により安全停止をサポート。
    - 起動時にプロセス優先度を "high" に設定する処理を呼び出す。
    - PID ファイル（data/execution.pid）を利用してプロセス管理を補助。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py を追加。
    - .env/.env.local 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先度: OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 形式、クォート、エスケープ、インラインコメント等に対応する堅牢な実装。
    - Settings クラスで環境変数をプロパティ経由で強く型付けして提供（検証とデフォルト値を含む）。
    - KABUSYS_ENV の有効値チェック（development/paper_trading/live）。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
    - 各種閾値・パス設定（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH 等）を統一的に管理。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全0 の場合は等金額配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用 (apply_sector_cap)、市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を実装。未知レジームはフォールバック挙動を明示。
  - portfolio/position_sizing.py
    - 単元株丸め、リスクベース / equal / score 方式の発注株数決定、ポートフォリオ全体での aggregate cap（利用可能現金でのスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮した丸めロジックを実装。
    - lot_size（単元）を考慮した残差配分ロジックを実装。

- 研究モジュール（DuckDB ベースのファクター計算）
  - research/factor_research.py
    - Momentum, Volatility, Value のファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL を用いたウィンドウ関数実装で、欠損やデータ不足時の None 処理を明示。
  - research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、ファクター統計要約 (factor_summary)、ランク変換 (rank) を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで計算。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加（CLI: python -m kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを計算して PASS/FAIL 判定を行う。閾値はソース内で定義（例: 稼働率 >= 99%）。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能。
    - P95 計算、日付フィルタの SQL 構築、テーブル欠如時のフェイルセーフ動作を実装。

- ニュース NLP スコアリング（AI 統合）
  - ai/news_nlp.py を追加（ニュース記事の OpenAI によるセンチメントスコアリング）。
    - タイムウィンドウ計算（JST 基準 → UTC）を提供（calc_news_window）。
    - OpenAI API（gpt-4o-mini）へのバッチ送信、最大トークン上限対策（記事数・文字数トリム）、リトライ（429/タイムアウト/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアクリッピングを設計。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
    - （注）ファイル末尾が途中で切れているため実装の一部は継続中・未完の可能性あり。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）を実装。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加。アクセス権限や未対応プラットフォーム時は警告を出してスキップ。

### 修正 (Fixed)
- 設定読み込み・パースの堅牢化
  - .env のクォート・エスケープ・コメント処理を改善し、誤ったパースによる環境変数設定ミスを低減。
- ポートフォリオ/ポジション計算
  - weight=0 や価格欠損時のスキップ、単元丸め、aggregate cap スケーリング時の端数配分ロジックを整理。
- 監視 / 実行スクリプトの堅牢性
  - 予期しない例外が発生した場合にログ出力して次のポーリングへ継続するフェイルセーフを導入（run_monitoring）。
  - 停止フラグを検知したら安全にエンジン停止・終了する挙動を明示（run_execution）。

### 既知の制約 / 注意事項 (Notes)
- run_monitoring は「監視専用」に設計されており、KABUSYS_ENV にかかわらず sqlite_path（本番監視 DB）を使用します。運用時は DB パスの扱いに注意してください。
- ai/news_nlp.py は API 呼び出し周りの記述が詳細にある一方、ファイル末尾が途中で切れているため本番稼働前に実装の完成・レビューが必要です。
- .env 自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。配布後や CWD が異なる場合にロードされないことがあります。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等は厳密な有効値チェックを行います。不正値を与えると起動時に例外が発生します。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に失敗する可能性があります。失敗時は警告を出して処理をスキップするため、必ずしも例外で停止しません。

### 将来検討事項 (Future)
- ai/news_nlp の完全実装とテスト、API コールのモック・リトライロジックの追加強化。
- position_sizing の lot_size を銘柄ごとに可変とするためのマスタ拡張（TODO コメントあり）。
- price 欠損時のフォールバック（前日終値や取得原価など）を実装してエクスポージャー計算の精度向上を検討。

---

生成元のコードから推測して作成しました。実際の変更履歴やリリースノートはリポジトリ運用ポリシーに従って調整してください。