# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはコードベースから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-16

### Added
- 起動スクリプトを追加/整備
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する仕様。停止フラグ（data/stop_requested.flag）検知処理を実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 sqlite（data/paper_trading.db）を使用して本番 DB と完全分離。停止フラグと実行 PID ファイル管理（data/execution.pid）をサポートし、エンジンを別スレッドで実行・停止する制御を実装。

- 設定・環境読み込み
  - config.py: .env 自動読み込み（プロジェクトルート検出）を実装。export 形式やクォート・インラインコメントを考慮した堅牢な .env パーサを追加。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - Settings クラスを追加し、各種設定（J-Quants / kabu API / LINE / DB パス / PID/KILL フラグパス / 監視閾値 / 環境種別判定 等）をプロパティとして提供。paper_trading 用の PAPER_FILL_MODE と PAPER_TRADING_SQLITE_PATH の取り扱いを実装（値検証あり）。

- ポートフォリオ構築・リスク調整・ポジションサイジング
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）と等重・スコア加重の重み計算を実装。スコアが全て 0 の場合は等金額配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とマーケットレジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクター扱いの扱いも明記。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に対応した株数計算を実装。単元株（lot_size）丸め、per-position / aggregate cap、cost_buffer の考慮、スケールダウン時の残差配分ロジックなど詳細なアルゴリズムを提供。

- 監視/実行補助ユーティリティ
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティを追加（set_process_priority）。CPU affinity 設定関数 set_cpu_affinity を追加。

- 研究/リサーチ機能（DuckDB ベース）
  - research/factor_research.py: モメンタム / ボラティリティ / バリューのファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。DuckDB 接続を受け取り SQL で計算する設計。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（スピアマン・ランク相関）計算（calc_ic）、ファクターの統計サマリー（factor_summary）およびランク関数（rank）を追加。外部依存を使わずに実装。
  - research/__init__.py: 主要 API をエクスポート（zscore_normalize などを含む）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成 CLI を追加。システム稼働率・注文成功率・送信率・レイテンシ（P95）などを算出して PASS/FAIL 判定を出力。複数期間フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。DB/テーブル欠損時に安全に N/A を扱う処理を実装。

- ニュース NLP（AI）機能（設計・実装を追加）
  - ai/news_nlp.py: raw_news を OpenAI に送信して銘柄別センチメントスコアを ai_scores に書き込むモジュールを追加。タイムウィンドウ計算、記事集約、1 銘柄あたりの文字数上限・記事数上限、バッチ送信（最大 20 銘柄）、リトライ（指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗に備えた安全な DB 更新方針（対象コードのみ置換）などの設計方針を記載。※ソース末尾が一部切れている箇所あり（コード断片）。

### Changed
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" と基本 __all__ を定義。

- DB 初期化呼び出しの冪等化
  - run_monitoring/run_execution で監視テーブル初期化（init_monitoring_db）を確実に呼び出すことでテーブル存在を保証。

- 実行環境の分離
  - paper_trading 環境では専用 sqlite を使う設計を明確化（run_execution.py / Settings.paper_sqlite_path）、本番 DB と分離して安全に検証可能に。

### Fixed
- 環境変数・.env パーサの堅牢性向上
  - export プレフィックス対応、クォート内エスケープ、インラインコメントの扱いを改善。無効行のスキップや読み込み失敗時の警告出力を追加。

- MONITOR_POLL_INTERVAL の値検証
  - run_monitoring.py のポーリング間隔読み取りで 0 以下や非整数値を検出した場合にデフォルトへフォールバックし、警告を出すように修正（time.sleep に渡す不正値を防止）。

- PAPER_FILL_MODE の入力検証
  - Settings.paper_fill_mode で有効値をチェックし、無効な値は ValueError を送出するように修正。

- DuckDB/SQLite 参照時の障害耐性
  - 各種レポート/ツールで sqlite3.OperationalError を捕捉し、テーブル欠損などで処理中断しないように N/A やデフォルト値を返す処理を追加（paper_verification_report.py 等）。

- プロセス優先度/CPU アフィニティでの失敗許容
  - パーミッション不許可や未サポート環境で例外が発生した場合、ログに警告を出して処理を継続するように変更（utils/process_priority.py）。

### Documentation / Comments
- 各モジュールに設計方針・注意点・TODO を詳細に記載
  - ポートフォリオ/リサーチ/AI/実行系のモジュールに設計意図や動作境界、将来の拡張案（例: 銘柄別 lot_size 対応、価格欠損時のフォールバック）をコメントとして記載。

### Removed
- （初版のため該当なし）

### Security
- OpenAI API キーを環境変数か引数で受け取る仕様にし、未設定時は明示的にエラーで通知する実装を追加（ai/news_nlp.py）。外部秘匿情報の扱いに注意する旨をコメントで明示。

---

注記:
- 本 CHANGELOG は提供されたソースコードの内容から推測して作成した初期リリース向けの変更履歴です。実際のコミット履歴やリリースノートが存在する場合は、そちらを優先してください。