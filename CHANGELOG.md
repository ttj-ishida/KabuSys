# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-12
初回リリース。以下の主要機能・モジュールを追加しました。

### 追加（Added）
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する挙動。
    - duckdb/SQLite の接続初期化と監視 DB テーブル初期化を実行。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority を使用）。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し MockBroker を選択して本番 DB と分離する仕様を実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine.run_session の起動を実装。
    - 起動時にプロセス優先度を設定。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env / .env.local の読み込み順序、OS 環境変数の保護（protected）に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env 行パーサーで export 形式、クォート文字列（バックスラッシュエスケープ対応）やインラインコメントの扱いを実装。
    - Settings クラスを提供し、J-Quants / kabu API トークンや DB パス、監視閾値、環境（development/paper_trading/live）検証、PAPER_FILL_MODE のバリデーションなどをプロパティとして取得可能に。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定 select_candidates と重み計算 calc_equal_weights / calc_score_weights を実装。
    - スコア合計が 0 の場合は等金額配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター比率に基づく候補除外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づく投下資金乗数の返却（未知のレジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した発注株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限や aggregate cap（available_cash）でのスケールダウン、cost_buffer による保守的見積り、残差処理による追加配分ロジックを実装。

- 実行時ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値）と CPU affinity 設定ユーティリティを追加。
    - 権限不足や未対応 OS の場合は警告してスキップする堅牢な実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily / raw_financials を使ってファクター（Momentum, Volatility, Value）を計算する関数 calc_momentum / calc_volatility / calc_value を追加。
    - 200 日移動平均や ATR、各種リターンなどを営業日ベースで計算する実装。
  - research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応）、スピアマン rank IC 計算 calc_ic、ランク変換 rank、列統計 factor_summary を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP（OpenAI 経由スコアリング）
  - ai/news_nlp.py
    - raw_news を銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ格納する処理を実装。
    - バッチサイズ、トークン肥大化対策（記事数・文字数上限）、JSON Mode を期待したレスポンス検証、スコアクリップ、エクスポネンシャルバックオフによるリトライ、部分成功時の既存スコア保護（対象コードのみ置換）などの設計方針を反映。
    - タイムウィンドウ計算（JST → UTC 変換）を提供する calc_news_window を実装。

- 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し、Pass/Fail 判定を行う。
    - P95 計算や日付フィルタ、DB 存在チェック、コマンドライン引数（--from/--to/--db）対応を実装。
  - tools/__init__.py を追加（パッケージ化）。

- パッケージ情報
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。
  - research パッケージのエクスポートを整理。

### 変更（Changed）
- なし（初回リリースのため新規実装中心）

### 修正（Fixed）
- なし（初回リリースのため新規実装中心）

### 既知の注意点（Notes / Known issues）
- .env パーサは多くのケース（クォート，エスケープ，inline コメント）に対応しますが、特殊なエッジケースが残る可能性があります。必要に応じて .env.example を参照して環境変数を設定してください。
- ai/news_nlp の外部 API 呼び出しはネットワーク依存のため、API キー未設定時は ValueError を送出します。失敗時はフェイルセーフ設計（部分失敗を避けるため対象コードのみ置換）になっていますが、運用時は API レートやコストに注意してください。
- position_sizing の lot_size は現状全銘柄共通想定（将来的に銘柄別拡張を想定）。

---

（将来のリリースでは、バグ修正、性能改善、API 呼び出しの冗長化、銘柄別単元対応、さらに詳細な監視/アラート機能などを予定してください。）