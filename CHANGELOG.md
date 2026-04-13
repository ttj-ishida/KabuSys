# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、Semantic Versioning を想定しています。

現在の最新版: 0.1.0 - 初回リリース

## [Unreleased]

## [0.1.0] - 2026-04-13
初回リリース。自動売買システム KabuSys のコア機能群を実装しました。

### Added
- 全体
  - パッケージ初期版として、モニタリング、実行エンジン、ポートフォリオ構築、リサーチ、ユーティリティ、ツール類、AI ニューススコアリング等の主要コンポーネントを追加。
  - duckdb / sqlite を併用して時系列データ・ログ・監視情報等を扱うアーキテクチャを採用。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）でポーリング間隔を上書き可能。モニタリングは環境に依存せず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用し MockBrokerClient を利用する設計。

- 設定管理
  - config.py: .env 自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）を実装。読み込み優先度は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化に対応。
  - .env パーサを実装し、export 形式やシングル/ダブルクォート、エスケープ、インラインコメントの扱いをサポート。環境変数の保護（既存 OS 環境変数を上書きしない）機能を提供。
  - Settings クラスを実装し、各種環境変数（DB パス、PID/KILL フラグ、閾値、PAPER_FILL_MODE 等）をプロパティで提供。PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL のバリデーションを実装。

- モニタリング / 監視
  - monitoring_db 初期化呼び出しを導入（冪等）。ポーリング時に check_once() を呼び例外はログ化してループ継続する安全設計。

- 実行エンジン周り
  - ExecutionEngine の起動ロジックを追加。BrokerClientFactory 経由で環境に応じたブローカークライアントを生成。OrderRepository / OrderManager / Reconciler / RiskManager を組み合わせた構成を実装。
  - RiskConfig のデフォルト設定を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。RiskManager がブローカーの get_available_cash() を初期値として使用。

- ポートフォリオ構築
  - portfolio_builder: 候補選定（score 降順 + tie-breaker）、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights)（全スコアがゼロ時のフォールバック警告を含む）を実装。
  - risk_adjustment: セクター集中制限の適用(apply_sector_cap)、市場レジームに応じた投下資金乗数(calc_regime_multiplier)（未知レジームはログ警告の上で 1.0 にフォールバック）を実装。
  - position_sizing: 発注株数計算（risk_based / equal / score）を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金超過時のスケールダウン）および端数再配分アルゴリズムを実装。コストバッファ（手数料・スリッページ想定）にも対応。

- リサーチ
  - research.factor_research: モメンタム(calc_momentum)、ボラティリティ/流動性(calc_volatility)、バリュー(calc_value) のファクター計算を DuckDB SQL ベースで実装。MA・ATR 等の窓集計やデータ不足時の None ハンドリングを実装。
  - research.feature_exploration: 将来リターンの計算(calc_forward_returns)、スピアマンランク相関による IC 計算(calc_ic)、ファクター統計サマリ(factor_summary)、ランク関数(rank) を実装。外部ライブラリに依存しない実装。

- AI / ニュース
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメントスコアリングし、銘柄ごとに ai_scores テーブルへ保存するためのロジックを実装。タイムウィンドウ計算、記事トリム（記事数・文字数上限）、バッチ処理（最大 20 銘柄/回）、リトライ（429/ネットエラー/5xx に対する指数バックオフ）、レスポンス検証、スコアクリッピングを実装。API キー未設定時は明示的にエラーを返す。

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を追加。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し、閾値判定（PASS/FAIL）を行う。P95 計算や日付フィルタリング、DB 存在チェック・例外時フォールバックを実装。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームなプロセス優先度設定(set_process_priority) と CPU affinity 固定(set_cpu_affinity) を実装。Windows / POSIX（Linux/macOS/FreeBSD）に対応し、権限不足等は警告ログでスキップ。

### Changed
- パッケージメタ
  - __init__.py にてパッケージ version を "0.1.0" に設定。

### Fixed
- 環境変数関連
  - MONITOR_POLL_INTERVAL のパースにおいて不正な値（0 以下や非整数）を検出した場合、警告を出してデフォルト（60 秒）にフォールバックする処理を追加。time.sleep に渡す不正値によるクラッシュ防止。

- DB 初期化
  - run_execution/run_monitoring 起動時に監視テーブルの初期化（init_monitoring_db）を行い、存在しない場合でも安全に開始できるように調整（冪等）。

### Notes / Known limitations
- ai.news_nlp の OpenAI API 呼び出し周辺は外部接続に依存するため、API レートや料金、モデルの応答フォーマット変更に注意が必要。
- position_sizing の price 欠損時の挙動（price=0.0 によりエクスポージャー過少見積りになる可能性）については TODO コメントで将来的な改善（前日終値等のフォールバック）を残しています。
- research モジュールは DuckDB のテーブル（prices_daily, raw_financials 等）を前提としているため、データセットの整備が必要です。
- tools.paper_verification_report は SQLite DB のスキーマ（trade_logs, system_status, risk_logs 等）が存在することを前提とします。DB のスキーマ不整合時は一部指標が N/A になります。

---

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノート作成時は変更履歴・コミットログに基づく追記・修正を行ってください。）