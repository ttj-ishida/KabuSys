# CHANGELOG

すべての重要な変更は「Keep a Changelog」準拠で記録します。  
このファイルは、リリースごとの機能追加・変更・修正の要点を日本語でまとめたものです。

フォーマット:
- ヘッダはバージョンと日付（YYYY-MM-DD）
- 各バージョンは主に Added / Changed / Fixed に分類しています

## [Unreleased]
- 現時点で未リリースの変更はありません。

---

## [0.1.0] - 2026-04-17
初期リリース。以下の主要機能群とユーティリティを実装・公開しました。

### Added
- 基本パッケージ設定
  - kabusys.__version__ を 0.1.0 に設定。
  - 環境変数 / .env 管理モジュール (kabusys.config.Settings)
    - .env / .env.local の自動読み込み（OS 環境変数を保護する仕組み付き）
    - export プレフィックス、クォート、インラインコメントなどに対応する堅牢な .env パーサを実装
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能
    - 各種環境設定プロパティ（DB パス、API トークン、監視閾値、ペーパートレード用設定 等）

- 実行・監視エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading 時は paper_trading.db を使用して本番 DB と分離
    - BrokerClientFactory を用いたブローカークライアント生成
    - OrderManager / OrderRepository / RiskManager / Reconciler の組み立てと実行スレッド化
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理のサポート
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
    - 監視は環境に関わらず本番用 sqlite_path を使用する設計

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選択
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア合計ゼロ時のフォールバックあり）
  - portfolio.position_sizing
    - calc_position_sizes: 等配分 / スコア配分 / リスクベース配分に対応
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap のスケールダウン、cost_buffer を考慮した保守的見積り
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を超える候補の除外（unknown セクターは上限除外）
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB で計算
    - calc_volatility: ATR20、相対 ATR、平均売買代金、出来高比率を計算
    - calc_value: EPS/ROE を用いた PER / ROE 計算（raw_financials 結合）
    - DuckDB を利用したウィンドウ関数中心の実装（パフォーマンス配慮のスキャン範囲制限）
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（任意ホライズン）をまとめて取得
    - calc_ic: スピアマンのランク相関（IC）計算（結合・欠損除外・有効レコード判定）
    - factor_summary / rank: 基本統計量・ランク化ユーティリティ

- AI ニュース NLP（OpenAI 統合）
  - ai.news_nlp
    - raw_news を銘柄別に集約して OpenAI API（デフォルト: gpt-4o-mini）でセンチメント（-1.0〜1.0）を算出
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大対策（記事数・文字数トリム）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ
    - レスポンスの厳密な JSON バリデーションとスコアクリッピング（±1.0）
    - ai_scores テーブルへの部分置換操作（部分失敗時に既存スコアを保護する設計）
    - API キーは引数または環境変数 OPENAI_API_KEY を参照

- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成 CLI（--from/--to/--db）
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算・表示
    - 指標に基づく PASS/FAIL 判定（閾値はファイル内定義）
    - DB テーブル未存在時の安全な扱い（OperationalError を補足して N/A を返す）

- ユーティリティ
  - utils.process_priority
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows/HIGH_PRIORITY_CLASS、POSIX nice 値）
    - set_cpu_affinity による CPU ピン留め（利用可否の検出と安全ハンドリング）
    - 権限不足や未対応環境では警告ログを出してスキップする堅牢さ

- DB 関連
  - DuckDB 接続を利用した分析ワークフロー対応（research / ai / その他）
  - monitoring_db.init_monitoring_db を用いた監視テーブルの冪等初期化（run_execution/run_monitoring で利用）

### Changed
- ログレベルやデフォルト値の明確化（各スクリプトで logging.basicConfig(level=logging.INFO) を使用）
- .env 読み込み順序の明確化: OS 環境 > .env.local > .env（OS 環境は protected として上書き防止）
- run_monitoring のポーリング仕様
  - MONITOR_POLL_INTERVAL を環境変数で上書き可能にし、0 以下や不正値はデフォルトにフォールバックする挙動を追加
  - 監視は常に本番 sqlite_path を参照する（環境に依存しない設計）

### Fixed
- .env パーサの改善
  - export プレフィックスやシングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを修正して堅牢化
- position_sizing / aggregate cap の挙動
  - 可利用資金を超える場合のスケーリングと lot_size 単位での再配分を実装し、端数処理の再現性を確保
- research/feature_exploration
  - horizons 引数のバリデーション強化（正の整数かつ 252 以下）
  - DuckDB クエリでのホライズン重複除去とスキャン範囲の制限によりパフォーマンスを安定化
- paper_verification_report
  - データ不足・テーブル未存在時に安全に N/A を返す例外処理を追加
  - P95 計算で空リスト時に None を返す実装（レポート出力で N/A 表示）
- utils.process_priority
  - 未対応 OS や権限不足で安全にスキップし、警告ログを出すように修正

### Security
- OpenAI API キーは明示的に引数または環境変数（OPENAI_API_KEY）でのみ使用し、未設定時は ValueError を送出して処理を中断する設計としました（誤ったキー使用や未設定の誤動作を防止）。

---

注記:
- 本 CHANGELOG は、ソースコードから推測できる実装内容をもとに作成しています。実際のリリースノートはコミット履歴・変更履歴に基づいて適宜更新してください。
- 以降のリリースでは Unreleased セクションを運用し、Semantic Versioning に沿ってバージョンを更新してください。