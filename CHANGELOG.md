# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」準拠です。  
過去のリリース、重要な新機能、修正点、既知の制限などを日本語で記載しています。

最新更新日: 2026-04-16

## [Unreleased]
### 追加予定 / 注意事項
- news_nlp モジュールの処理部分がソースの途中で切れているため、OpenAI API 呼び出し以降の完全な書き込み・DB更新ロジックの確認・補完が必要です。
- portfolio.position_sizing における銘柄ごとの lot_size サポート拡張（現状は全銘柄共通の lot_size 固定）や、price 欠損時のフォールバック価格ロジックは TODO コメントとして残されています。実運用前に検討・実装してください。

---

## [0.1.0] - 2026-04-16
初回公開リリース。

### 追加
- 基本パッケージ情報
  - kabusys パッケージ初期化（`__version__ = "0.1.0"`）。
- 設定管理
  - `kabusys.config.Settings` クラスを導入し、環境変数および .env/.env.local からの自動読み込みをサポート。
  - 自動.envロードはプロジェクトルート（.git または pyproject.toml を基準）検出に基づく。テスト等で自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサ実装：コメント、`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などの細かいケースに対応。
  - 各種設定プロパティを提供（DBパス、paper_trading 切替、監視閾値、PID/フラグファイルパス、ログレベル検証等）。不正値時の検証・例外処理を実装。
- 実行 / 起動スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（paper_trading 環境は data/paper_trading.db を使用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド実行/停止処理および停止フラグ監視を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）、不正値はデフォルトへフォールバック。
    - 監視は常に本番 sqlite_path を使用する設計（環境に依存しない）。
    - stop フラグ検知でループ終了、例外・KeyboardInterrupt のハンドリングを実装。
- データベース / 分析ツール
  - `tools/paper_verification_report.py`：Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出して標準出力にレポート表示。
    - 日付フィルタ、DBパス指定（コマンドライン --db / 環境変数）対応。
    - 判定基準（閾値）を定義（稼働率 99%、注文成功率 90% など）。
- ポートフォリオ構築（純粋関数群）
  - `portfolio.portfolio_builder`：
    - select_candidates — BUY シグナルのスコア降順ソートと上位選定。
    - calc_equal_weights, calc_score_weights — 等金額配分とスコア加重配分の重み計算（スコア全0時のフォールバックとログ出力）。
  - `portfolio.position_sizing`：
    - calc_position_sizes — risk_based / equal / score の allocation_method に対応した発注株数計算、単元株（lot_size）丸め、aggregate cap によるスケールダウンロジックを実装。
    - コストバッファ(cost_buffer) を用いた保守的評価と、残余キャッシュを使った端数ロジック付きの比例配分を実装。
  - `portfolio.risk_adjustment`：
    - apply_sector_cap — セクター別エクスポージャーを計算し、上限超過セクターの候補銘柄を除外。
    - calc_regime_multiplier — market regime（bull/neutral/bear）に応じた投下資金乗数を定義。
  - `portfolio.__init__` で主要関数をエクスポート。
- 研究（Research）モジュール
  - `research.factor_research`：
    - calc_momentum — 1M/3M/6M リターン、MA200 乖離の計算（DuckDB 経由、prices_daily を参照）。
    - calc_volatility — ATR20、相対 ATR、20日平均売買代金、出来高比率の計算。
    - calc_value — raw_financials から EPS/ROE を取得し PER/ROE を計算。
  - `research.feature_exploration`：
    - calc_forward_returns — 将来リターン（複数ホライズン）計算。
    - calc_ic — ファクターと将来リターンのスピアマンランク相関（IC）計算。
    - factor_summary, rank — 基本統計量とランク付けユーティリティ。
  - `research.__init__` で z-score 正規化ユーティリティ（kabusys.data.stats から）と上記関数をエクスポート。
- AI / ニュース NLP（部分実装）
  - `ai.news_nlp`：
    - raw_news を銘柄別に集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む設計を追加。
    - バッチサイズ、トリム文字数、最大記事数、タイムウィンドウ計算（JST→UTC 変換）、スコアの ±1.0 クリップ、エラーハンドリング（リトライ・バックオフ）等の方針を実装。
    - API キーの取得と未設定時の例外処理を実装。
    - （注）ファイル末尾でソースが切れているため、完全な書き込み処理は要確認。
- ユーティリティ
  - `utils.process_priority`：
    - set_process_priority(level) — Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定、アクセス権限がない場合は警告でスキップ。
    - set_cpu_affinity(cpu_count) — 指定コア数へのピン留め（利用可能コアより多い場合の扱い、権限不足のフォールバック）を実装。
    - ログ出力・エラー抑制を考慮した堅牢な実装。

### 変更
- （初回リリースのため該当なし）

### 修正
- 環境変数/入力値の堅牢性向上（検証・フォールバック）
  - MONITOR_POLL_INTERVAL の不正値検出とデフォルトフォールバック（監視ループ）。
  - PAPER_FILL_MODE の有効値検証（paper_trading 動作設定）。
  - LOG_LEVEL / KABUSYS_ENV 等の列挙値検証で明示的なエラーを投げる実装。
  - .env 読み込み失敗時の警告発行。

### 既知の制限 / 注意点
- portfolio.position_sizing は現状で全銘柄共通の lot_size を前提としている。将来的に銘柄別 lot_size 対応を想定している（TODO コメントあり）。
- apply_sector_cap のエクスポージャー計算は price_map に依存し、price が 0.0 の場合に過少見積りとなるリスクがある（フォールバック価格の未実装を注記）。
- news_nlp のソースが途中で切れているため、OpenAI への送信・レスポンス処理・DB更新の最終ロジックを補完する必要あり。
- DuckDB を利用した分析処理は prices_daily / raw_financials 等のテーブル存在を前提としている。データが不足する場合、各関数は None を返す/適切に扱うように実装されているが、実運用前にデータ準備を確認してください。

### セキュリティ
- 機密情報（API キー等）は環境変数で管理する設計。OPENAI_API_KEY 未設定時は明示的な例外を投げる等の保護を実装。

---

開発・運用に関する補足や既知の TODO はソースコード内のコメント（TODO, FIXME）にも記載しています。必要に応じてチケット化して対応を進めてください。