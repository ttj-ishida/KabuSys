CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは Keep a Changelog 準拠です。
日付はコミット状況から推測して付与しています。実際のリリース時は適宜更新してください。

[Unreleased]
-------------
- （なし）

[0.1.0] - 2026-04-16
--------------------
初回リリース（コードベースの初期導入）。以下の主要コンポーネントを実装・追加しました。

Added
- 実行系 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB から完全に分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行をサポート。
    - 停止制御用フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による安全停止処理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はログを出してデフォルトにフォールバック。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する仕様（意図的な設計）。
    - 停止フラグ検知によりループを安全に終了。

- 設定管理
  - config.py: .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出に .git / pyproject.toml を利用）。
    - 読み込みの優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 複雑な .env 行のパース実装（export プレフィックス、クォート・エスケープ、コメント処理など）。
    - Settings クラスで各種設定値をラップ（DB パス、API トークン、閾値、環境判定、paper trading 関連など）。入力検証を実装（有効値チェック、必須項目は例外）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など paper_trading 向け設定を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - シグナル選定（スコア降順、タイブレーク）、等金額・スコア加重配分を実装。スコア全0時は等配分にフォールバックし警告。
  - portfolio.position_sizing
    - risk_based / equal / score の allocation_method をサポート。損切り・リスク許容率・単元株（lot_size）・max_position_pct・max_utilization 等を考慮した株数計算を実装。
    - aggregate cap によるスケーリング、残差のロット単位での再配分ロジックを実装。
  - portfolio.risk_adjustment
    - セクター集中制限の適用（既存保有をセクター別に評価し上限超過セクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）。

- 研究 / ファクター計算
  - research.factor_research
    - Momentum / Volatility / Value ファクター計算を実装（DuckDB を用いた SQL ベースの実装、MA200、ATR20、リターン等）。
  - research.feature_exploration
    - 将来リターン計算（任意ホライズン）、IC（Spearman）計算、ランク付け、ファクター統計サマリを実装。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB のみで実装。
  - research.__init__ で必要関数を公開。

- AI / ニュース NLP（部分実装）
  - ai.news_nlp
    - raw_news からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを計算して ai_scores テーブルに書き込む処理の骨格を実装。
    - バッチサイズ、トークン肥大対策（記事数・文字上限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリップ等の設計方針を採用。
    - calc_news_window により JST 時間帯→UTC 変換ロジックを提供。
    - 注意: score_news の呼び出し先 _fetch_articles 等の実装が途中で切れている箇所があり、完全実装は未完（後述の Known issues 参照）。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証用レポート生成スクリプトを追加（コマンドライン実行可能）。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを算出し、閾値（稼働率 99%、成功率 90% 等）に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB 存在チェック、欠損テーブル時の耐障害処理を実装。

- ユーティリティ
  - utils.process_priority
    - プラットフォーム差分を吸収してプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（アクセス制限や未対応 API に対しては警告を出してスキップ）。
    - 呼び出し側はプラットフォームを意識せずに優先度設定を行える。

Changed
- パッケージ情報
  - kabusys.__init__ にバージョン 0.1.0 を設定。

Fixed
- 多数の箇所でフェイルセーフ / 入力バリデーションを追加
  - 環境変数の不正値に対して警告を出しデフォルトにフォールバック（例: MONITOR_POLL_INTERVAL）。
  - DuckDB/SQLite クエリでテーブル欠損時に sqlite3.OperationalError を捕捉して安全にレポート生成を継続（tools.paper_verification_report）。
  - Position sizing 等で無効な価格データを検知してスキップするログを追加。

Deprecated
- （なし）

Removed
- （なし）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で供給する設計。未設定時は score_news が ValueError を送出して処理を早期終了するため、キー漏洩リスクのあるログ出力は行わない方針。

Known issues / Notes
- ai.news_nlp.score_news はファイル中で途中 (fetch_articles 呼び出し直後) で切れており、記事取得・API 呼び出し後の結果反映ロジック（_fetch_articles の実装、レスポンス書き込み周り）が未実装／未完です。OpenAI 連携を本番稼働させるには追加実装が必要です。
- run_monitoring は設計上「監視は環境にかかわらず本番 sqlite_path を使用する」旨の挙動があります。意図的な仕様ですが、運用時に混乱しないよう注意してください（paper_trading 環境で監視を別 DB にしたい場合は設定変更が必要）。
- position_sizing の price フォールバックは未実装（TODO コメント）。price が欠損した場合、エクスポージャー過少見積りのリスクがあるため運用上の注意が必要です。
- process_priority の設定は権限不足や非対応プラットフォームでは警告を出してスキップします。期待どおり動作しない場合は実行環境の権限確認を推奨します。
- DuckDB / psutil / openai / sqlite3 等の外部依存が必要です。実行環境にこれらが整っていることを確認してください。

Migration notes
- paper_trading を使用する場合は PAPER_TRADING_SQLITE_PATH（または KABUSYS_ENV=paper_trading）で DB の分離を確認してください。
- .env / .env.local の自動ロードはデフォルトで有効。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

開発者向け
- ランタイム挙動や閾値は Settings クラスやツール内の定数で定義されています。運用調整や実験はこれらを変更してください。
- news_nlp の未実装部分は早急に完成させることを推奨します（バッチ化・リトライ・部分更新設計はすでに盛り込まれています）。

---
この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートはコミット履歴・変更の意図に合わせて適宜修正してください。