# CHANGELOG

すべての注目すべき変更を記載します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 初期リリース: KabuSys 基本モジュール群を追加。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）検出、プロセス優先度設定、監視 DB の初期化、duckdb 接続、例外耐性を持つループを実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し MockBroker を利用可能。OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、バックグラウンドスレッドでセッションを実行。停止フラグ／PID 管理をサポート。
- 設定管理
  - config.py: .env/.env.local の自動読み込み機能を実装（プロジェクトルート自動検出）。エクスポート形式・クォート・エスケープ・コメント処理に対応するパーサーを実装。Settings クラスで各種環境設定（DB パス、API トークン、Paper Trading 設定、監視閾値、ログレベル、環境判定など）をプロパティ化。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、signal_rank タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合はフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap（利用可能現金に基づくスケーリング）、手数料・スリッページ見積り（cost_buffer）を実装。
- 監視・ユーティリティ
  - utils/process_priority.py: プラットフォーム差を吸収するプロセス優先度設定ユーティリティを実装（Windows/POSIX 対応）。CPU アフィニティ固定機能を追加。
- 研究（Research）
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を DuckDB SQL ベースで実装（MA200、ATR20、リターン等）。
  - research/feature_exploration.py: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク変換ユーティリティを実装。外部ライブラリに依存しない純粋実装。
  - research/__init__.py: 主要関数の公開を整理。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から各種指標（稼働率・注文成功率・送信率・レイテンシ等）を集計し PASS/FAIL 判定を出力。CLI (--from / --to / --db) をサポート。
- AI ニューススコアリング（基礎実装）
  - ai/news_nlp.py: raw_news -> OpenAI（gpt-4o-mini）による銘柄別センチメントスコア生成機能を追加（バッチ処理、トークン肥大化対策、スコアクリッピング、リトライ/バックオフ戦略、ニュース収集ウィンドウ計算）。API キー解決やレスポンス検証の方針が含まれる（処理フローの実装途中での導入を想定）。

### 変更 (Changed)
- パッケージ情報
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ で公開。
- DB の取り扱い
  - 監視処理は KABUSYS_ENV に関係なく本番 sqlite_path を利用する旨を run_monitoring.py に明示（運用方針）。
  - run_execution.py は paper_trading の場合に専用の paper_sqlite_path を使うよう切り分け。

### 修正 (Fixed)
- .env パーサーの改善（config._parse_env_line）
  - export プレフィックス対応、シングル／ダブルクォート内部のバックスラッシュエスケープ処理、インラインコメントの扱いをより正確に実装。無効行の無視や保護付きオーバーライド処理を適切に適用するよう修正。
- 安全性／堅牢性の向上
  - run_monitoring.py / run_execution.py: 停止フラグの検出、例外発生時にログを残してポーリング/セッションを継続するフェイルセーフを実装。
  - tools/paper_verification_report.py: DB 存在チェックや sqlite3.OperationalError による欠損テーブルへの耐性を追加し、欠損時は N/A や 0 を扱うようにした。
  - process_priority の例外処理強化により、権限不足や未実装 API に対して警告ログを出してスキップするように変更。

### ドキュメント（コード内コメント）
- 各モジュールに設計方針、参照する仕様（PortfolioConstruction.md、StrategyModel.md 等）、注意点（例: bear レジームの扱いや価格欠損時の TODO）を詳細にコメントとして追加。

### 非互換・破壊的変更 (Deprecated / Removed)
- なし（初期リリース）。

### セキュリティ (Security)
- なし（公開コードから推測される範囲）。

---

注記:
- ai/news_nlp.py はファイル末尾が途中で切れているため、記事取得部分など一部機能が未完了の可能性があります。運用環境で利用する前に残り実装（_fetch_articles 等）と実際の OpenAI 統合のテストが必要です。
- 各コンポーネントは DuckDB/SQLite/外部 API（kabuステーション, J-Quants, OpenAI）に依存するため、実運用前に接続情報・権限・環境変数の設定（.env）を確認してください。