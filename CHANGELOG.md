CHANGELOG
=========

すべての注目すべき変更点を記録します。形式は「Keep a Changelog」に準拠しています。

目次
-----
- [Unreleased](#unreleased)
- [0.1.0 - 2026-04-11](#010---2026-04-11)

Unreleased
----------
(現時点での開発途中の小改善・ドキュメント補強等を想定しています)

Added
- 設定読み込みの堅牢化:
  - .env / .env.local の自動読み込みで、OS 環境変数を保護する protected オプションを導入。既存の OS 環境変数を上書きしない挙動を保証（src/kabusys/config.py）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env 読み込みを無効化できるようにした（テスト容易化）。
- 環境変数パーサの改善:
  - export 句のサポート、クォート内のバックスラッシュエスケープ、行内コメント処理などを強化（src/kabusys/config.py）。
- モニタリング周りの小改善:
  - MONITOR_POLL_INTERVAL の無効値に対する警告ログ出力とフォールバック挙動を明確化（src/kabusys/run_monitoring.py）。
- process priority ユーティリティの拡張:
  - set_cpu_affinity 関数を追加し、カレントプロセスの CPU affinity を最初の N コアに固定できるように（src/kabusys/utils/process_priority.py）。

Changed
- ログレベルの取り扱いを厳格化:
  - Settings.log_level の値チェックを追加し、不正な値で例外を投げるように（src/kabusys/config.py）。
- Paper Trading データ分離の明確化:
  - 実行スクリプトが paper_trading 環境時に専用 SQLite を使用する挙動を明示（src/kabusys/run_execution.py）。monitoring テーブルは冪等に初期化される（init_monitoring_db を常に呼出）。

Fixed
- 環境変数の不整合による起動障害防止:
  - 必須環境変数未設定時にわかりやすいエラーメッセージを出力（_require 関数）（src/kabusys/config.py）。

0.1.0 - 2026-04-11
------------------
初回リリース想定 — プロジェクトの主要機能を実装したバージョン。

Added
- 基本パッケージ情報:
  - パッケージメタ情報として __version__ = "0.1.0" を追加（src/kabusys/__init__.py）。
- 設定管理:
  - Settings クラスを導入し、各種環境変数（API トークン、DB パス、監視閾値、環境種別など）をプロパティとして提供（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出ロジックを含む）。
- 実行エントリ:
  - ExecutionEngine 起動スクリプトを実装。paper_trading 環境では MockBrokerClient を使用して専用 DB に記録する（src/kabusys/run_execution.py）。
  - SystemMonitor をポーリングする起動スクリプトを実装（MONITOR_POLL_INTERVAL による上書き対応）（src/kabusys/run_monitoring.py）。
- 監視 DB 初期化:
  - init_monitoring_db により監視用テーブルの存在を保証（冪等）するユーティリティを採用（参照実装より）。
- Execution コンポーネント群:
  - BrokerClientFactory / ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager（および RiskConfig / EngineConfig）といった実行系コンポーネントの組み立てを実装（src/kabusys/run_execution.py を経由）。
  - RiskManager のデフォルト構成（max_position_pct、max_utilization、rate_limit_per_sec など）を設定。
- ツール:
  - Paper Trading 検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL を判定（src/kabusys/tools/paper_verification_report.py）。
- ポートフォリオ構築:
  - 銘柄選定と重み計算 (select_candidates, calc_equal_weights, calc_score_weights) を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター制限とレジーム乗数 (apply_sector_cap, calc_regime_multiplier) を実装（src/kabusys/portfolio/risk_adjustment.py）。
  - ポジションサイズ算出ロジックを実装（risk_based / equal / score の各方式、単元株丸め、aggregate cap のスケーリング、cost_buffer を考慮）（src/kabusys/portfolio/position_sizing.py）。
  - 価格欠損や lot_size を考慮した堅牢な処理を導入。
- 研究／リサーチ機能:
  - ファクター計算モジュールを実装（モメンタム、ボラティリティ、バリュー。DuckDB を用いた SQL ベースの実装）（src/kabusys/research/factor_research.py）。
  - 将来リターン計算、IC（Spearman ρ）計算、統計サマリー、ランク関数を実装（src/kabusys/research/feature_exploration.py）。
  - research パッケージの公開 API を整備（src/kabusys/research/__init__.py）。
- AI ニューススコアリング:
  - raw_news から記事を集約して OpenAI API (gpt-4o-mini) で銘柄毎にセンチメントスコアを算出し ai_scores に書き込む機能を実装（バッチ処理、トークン肥大化対策、リトライ/バックオフ、レスポンス検証、スコアクリッピング等を含む）（src/kabusys/ai/news_nlp.py）。
- ユーティリティ:
  - プロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収、権限不足時の警告処理あり）（src/kabusys/utils/process_priority.py）。
  - CPU affinity 設定、エラーハンドリングを備える。
- パッケージエクスポート:
  - portfolio モジュールのトップレベルエクスポート（select_candidates 等）を提供（src/kabusys/portfolio/__init__.py）。

Changed
- DuckDB ベースのリサーチ機能は外部 API に依存せず、prices_daily / raw_financials テーブルのみ参照する設計として実装（安全性と再現性の確保）（src/kabusys/research/*）。
- ニュース NLP モジュールはルックアヘッドバイアスを避けるために datetime.today()/date.today() を直接参照しない方針を採用（score_news の引数に target_date を要求）（src/kabusys/ai/news_nlp.py）。
- ポジション決定ロジックは lot_size による丸めや単銘柄上限、aggregate cap のスケーリングロジックを導入して実運用での安全弁を実装した（src/kabusys/portfolio/position_sizing.py）。

Fixed
- レースコンディションや DB 存在なしでのクラッシュ防止:
  - Paper Trading 検証ツールで DB ファイル不存在時のエラーメッセージを改善（src/kabusys/tools/paper_verification_report.py）。
  - DuckDB executemany に関する実装上の注意（params が空の場合は実行しない）をコード設計に反映（src/kabusys/ai/news_nlp.py の設計方針）。
- ファクター／統計関数の安定化:
  - 欠損値・ゼロ除算・非有限値を排除する防御的実装（src/kabusys/research/*）。

Notes（備考）
- ここに記載の変更点は、提供されたソースコードから機能や設計意図を推測してまとめたものです。実際のコミット履歴やリリースノートが存在する場合はそれに従ってください。
- 日付はコード内のコメントや使用例から想定したものを使用しています。正式なリリース日付が必要な場合はソース管理のタグ／コミット日時を参照してください。