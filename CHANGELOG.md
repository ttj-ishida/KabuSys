CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

0.1.0 - 2026-04-24
-----------------

Added
- 初回リリース。日本株自動売買フレームワーク KabuSys の基本コンポーネントを追加。
- 実行/監視スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度を高く設定し（set_process_priority）、KABUSYS_ENV によって paper_trading 用の専用 SQLite (data/paper_trading.db) を使用する分離を実装。停止フラグ (data/stop_requested.flag) と PID 管理をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用する設計。
- 設定関連
  - config.py: 環境変数 / .env の読み込みと Settings クラスを実装。プロジェクトルート自動検出（.git または pyproject.toml を基準）を行い、.env / .env.local の自動ロードをサポート。値検証（KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL 等）を実装。
  - config_setup.py: 対話式 .env ウィザードを追加。デフォルト値、選択肢、シークレット入力、既存 .env 読み込み・更新、保存機能を提供。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数チェック、パス存在確認、YAML ファイルの存在とパース検証（PyYAML がない場合は検証スキップ）、本番環境向けガードを実装。--strict オプションで警告をエラー扱いにできる。
- DB /分析
  - DuckDB/SQLite の接続パターンを統一（duckdb_path / sqlite_path / paper_sqlite_path）。monitoring テーブル初期化関数呼び出しを起動スクリプトに組み込み。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定(select_candidates) と重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）を追加。スコアが全て 0 の場合のフォールバック動作を実装。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知レジームのフォールバックとログ警告を実装。既存保有の評価に価格マップを使用（price 欠損に関する TODO コメントあり）。
  - portfolio/position_sizing.py: 発注株数計算(calc_position_sizes) を実装。risk_based / equal / score の配分方式、stop-loss・risk_pct・max_position_pct・max_utilization 等のパラメータ、単元株（lot_size）による丸め、aggregate cap（利用可能現金によるスケーリング）と端数配分ロジックを提供。手数料・スリッページ見積り用 cost_buffer を考慮。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリ自動作成と失敗時のフォールバック（コンソールのみ）対応。LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py: OS 間差分を吸収するプロセス優先度・CPU affinity のユーティリティを追加。Windows/Linux/macOS（POSIX）の nice 値や Windows 優先度を扱い、権限不足時に警告を出して処理をスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。system_status, trade_logs, risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出し、PASS/FAIL 判定（閾値はソース内定義）を行う。--from/--to/--db オプションをサポート。
- 研究用モジュール
  - research/factor_research.py: DuckDB の prices_daily/raw_financials を利用してモメンタム等のファクター計算を行う設計を追加（モジュール・定数と calc_momentum 等のインターフェースあり、一部実装は継続中）。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Known issues / Notes
- research/factor_research.py にて関数実装が途中で終わっている箇所があり、完全実装は今後のタスク。
- portfolio/risk_adjustment.py の apply_sector_cap は price_map に価格がない場合にエクスポージャーが過少評価される旨の TODO コメントが存在。前日終値等のフォールバックが未実装。
- position_sizing.py の lot_size は現状全銘柄共通の仮定。将来的に銘柄別 lot_size をサポートする予定（TODO コメント）。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や特殊環境では自動読み込みがスキップされる場合がある（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- process_priority / set_cpu_affinity は権限不足や未サポート環境で動作しない可能性があるが、安全に警告を出してスキップする実装。

Security
- 本リリース時点で特別なセキュリティ修正はありません。機密値（API トークン等）は .env に保存し、.env を Git にコミットしないよう README/ヘッダコメントで注意喚起あり。

Deprecated / Removed
- （初回リリースにつき該当なし）

---

今後の予定（参考）
- factor_research の完全実装（Momentum/Value/Volatility/Liquidity 等）
- 銘柄別 lot_size 対応、価格フォールバックロジックの追加
- 監視・実行コンポーネントのエンドツーエンドテスト拡充
- レポートの CSV/JSON 出力や Web ダッシュボード連携機能の追加

（以上）