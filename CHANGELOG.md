CHANGELOG
=========

この変更履歴は「Keep a Changelog」形式に準拠しています。  
注: 以下はコードベース（src 以下）の内容から推測して作成したリリースノートです。

Unreleased
----------
### Added
- 監視・実行プロセスの起動スクリプトを整備
  - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数による間隔上書き、停止フラグファイルによる安全停止、起動時にプロセス優先度を High に設定。
  - run_execution.py: ExecutionEngine を起動するエントリポイント。paper_trading 環境時は専用の SQLite を使用する分離動作、停止フラグ検知による Graceful shutdown、エンジンを別スレッドで実行して監視する仕組みを導入。

- 環境・設定管理機能（config）
  - .env/.env.local の自動ロード（OS 環境変数の保護と上書きルールを実装）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - 環境変数のパースを堅牢化（export 形式、クォート内エスケープ、インラインコメントへの対応）。
  - Settings クラスに各種プロパティを定義（DB パス、paper_trading 用 DB、PID/kill フラグパス、CPU/MEM/DISK 閾値、env/log_level 検証など）。PAPER_FILL_MODE の値検証を追加。

- Execution 系インフラ
  - BrokerClientFactory を経由したブローカークライアント生成。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てロジック（リスク設定のデフォルト、初期資産の broker.get_available_cash() 参照など）。

- 監視 DB 初期化
  - init_monitoring_db(sqlite_conn) により監視用テーブル群の存在を冪等に保証。

- ポートフォリオ構築ライブラリ（portfolio）
  - 候補選定/重み付け: select_candidates, calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等分配へフォールバック）。
  - リスク調整: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジームに応じた投下資金乗数）。
  - ポジションサイジング: calc_position_sizes（risk_based / equal / score の複数方式、単元株丸め、aggregate cap によるスケーリングと残差処理）。

- 研究用モジュール（research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算）。
  - 特徴量探索: calc_forward_returns（柔軟なホライズン対応）、calc_ic（スピアマンランク相関）、factor_summary、rank。
  - DuckDB を用いた高速な時系列集計処理設計。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: paper_trading DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し、PASS/FAIL 判定を出力する CLI を提供。閾値は定数化されている。

- ニュース NLP（AI）スコアリング基盤
  - ai/news_nlp.py: raw_news を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む設計。バッチ処理、トークン肥大対策（記事数・文字数制限）、スコアクリップ、429/ネットワーク/5xx に対する指数バックオフ再試行、レスポンス検証などを想定した堅牢な処理フローを実装。
  - ニュース収集ウィンドウは JST ベースで定義され、ルックアヘッドバイアスを避けるために datetime.today() を参照しない設計を採用。

- ユーティリティ
  - utils/process_priority.py: Windows/Linux の差を吸収するプロセス優先度設定ユーティリティ（set_process_priority, set_cpu_affinity）。権限不足等の場合は警告を出してスキップ。
  - その他モジュールの __init__ による公開 API 整理。

### Changed
- DB 周りの取り扱いを明確化
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視の一貫性確保）。
  - Execution は paper_trading 環境であれば paper_sqlite_path を使用し、本番 DB と分離。

- チェックとフォールバックの強化
  - 環境変数や入力値の検証を追加（MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）。不正値時はログ警告およびデフォルトフォールバックを行う。

### Fixed
- NULL / データ不足時の安全な取り扱い
  - research / factor 計算・SQL での NULL 伝播に注意した実装（cnt による条件付き算出、true_range の NULL 扱いなど）。
  - paper_verification_report: データ欠損時に N/A を表示し、SQLite の OperationalError を捕捉して堅牢に動作するように改善。

- ポジション計算の丸め・キャップ処理の安定化
  - 単元株（lot_size）での丸め、aggregate cap 超過時のスケーリングと端数再配分ロジックを導入し、コミット金額計算で cost_buffer を考慮。

- Process 優先度設定失敗時のフォールバックと警告を追加。

0.1.0 - 2026-04-16
------------------
初回公開リリース。主要な機能セットを含む最初の安定版。

### Added
- コア機能
  - 自動売買システムの基本構成要素（execution / monitoring / portfolio / research / ai / utils / config）。
  - ExecutionEngine を中心とした発注パイプライン（OrderRepository, OrderManager, RiskManager, Reconciler）。
  - SystemMonitor と監視用 DB（monitoring.db）初期化ユーティリティ。
  - DuckDB を利用した履歴データ処理（prices_daily, raw_financials 等を前提）。

- ポートフォリオ構築・リスク管理
  - 候補選定、重み付け、ポジションサイズ決定、セクターキャップ、レジーム乗数など、PortfolioConstruction.md / StrategyModel.md に沿った実装。

- 分析・研究ツール
  - ファクター計算、特徴量解析、IC 計算、統計サマリー等を含む研究モジュール。

- Paper Trading サポート
  - paper_trading モードでのモックブローカ使用、専用 DB（data/paper_trading.db）への記録。
  - 紙上検証用レポートツール。

- AI（ニュース NLP）
  - ニュース記事を集約して OpenAI により銘柄別センチメントを算出する基盤を実装（API 呼び出し、バッチ処理、結果検証、DB 書込戦略）。

### Changed
- プロジェクトルート自動検出と .env の自動読み込みを導入し、配布後でも安定して動作するように改善。

### Fixed
- SQL クエリや集計処理における NULL / データ不足の取り扱いを改善し、例外発生時のフォールバックを追加。

Deprecated / Removed / Security
-------------------------------
- なし（初回リリース時点）

注記
----
- 上記はコードコメント・実装から推測して作成した変更履歴です。実際のコミット履歴ではなく、現行の機能・設計意図の要約となります。実際のリリース管理やバージョンポリシーに合わせて適宜編集してください。