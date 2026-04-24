CHANGELOG
=========

すべての重要な変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）準拠で記載しています。

フォーマット:
- 変更カテゴリ: Added / Changed / Fixed / Removed / Security
- バージョンと日付（YYYY-MM-DD）

Unreleased
----------

- （なし）

0.1.0 - 2026-04-24
------------------

Added
- 初期リリース。KabuSys のコア機能群を追加。
- CLI 起動スクリプト:
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV が paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を利用する設計をサポート。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を参照する挙動をとる。
  - validate_config.py: .env および config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや YAML パースチェック、ライブ環境用ガードを実装。--strict オプションで警告を失敗扱いにできる。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。既存 .env の読み込み・編集・保存に対応し、秘密値のマスク表示や選択肢サポートなどを備える。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、API レイテンシ（P95）などを算出して PASS/FAIL 判定を出力。期間指定と DB パス指定オプションをサポート。
- 設定・環境管理:
  - config.py: 自動 .env 読み込み機能（.env/.env.local、OS 環境変数優先）を実装。プロジェクトルート検出（.git または pyproject.toml 基準）を行い、テスト向けに自動ロード無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。Settings クラスに J-Quants / kabu API / DB / 監視閾値 / 実行環境判定プロパティを追加し、入力検証（有効な列挙値・型チェック）を実装。
  - .env パース強化: export プレフィックス、クォート内のエスケープ、インラインコメント処理などを考慮したパーサを実装。
- データベース・分析:
  - DuckDB 対応: duckdb 接続を受け取る設計（ExecutionEngine / 各種コンポーネントで使用）。デフォルトパスは data/kabusys.duckdb。
  - 監視 DB 初期化ユーティリティ（monitoring_db.init_monitoring_db）呼び出しを追加し、監視テーブルが存在することを保証。
- ポートフォリオ構築（純粋関数群）:
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順、同点は signal_rank でタイブレークして候補選定。
    - calc_equal_weights / calc_score_weights: 等重配分とスコア加重配分（全スコアが 0 の場合は等重にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、セクター上限超過銘柄を候補から除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた乗数を実装（デフォルトフォールバックと警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の割当方式をサポート。損切り率・リスク許容率・単元株対応・max_position_pct/max_utilization に基づく計算、合計投下資金が available_cash を超える場合のスケーリングと残差処理を実装。
- 研究モジュール（骨格）:
  - research/factor_research.py: DuckDB の prices_daily/raw_financials を参照して Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計（calc_momentum の冒頭実装、定数定義と設計方針を追加）。（注: ファイルは計算ロジックの続きが未完の箇所あり）
- ユーティリティ:
  - utils/logging_setup.py: ルートロガーに対して StreamHandler(stdout) と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを実装。LOG_DIR/LOG_LEVEL の解決順、既存ハンドラのクリア、ディレクトリ作成失敗時のフォールバックを考慮。
  - utils/process_priority.py: プラットフォーム差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装（Windows のプロセスクラス / POSIX の nice 値を考慮）。CPU affinity 設定関数も提供。権限不足や未対応環境では警告ログでスキップ。
- パッケージ初期化:
  - __init__.py に __version__ = "0.1.0" を設定し、主要サブパッケージをエクスポート。

Changed
- なし（初期リリースのため変更履歴なし）

Fixed
- なし（初期リリースのため修正履歴なし）

Removed
- なし

Security
- なし（現時点で特記すべきセキュリティ修正はなし）

Notes / 備考
- run_execution/run_monitoring 等の起動スクリプトは停止フラグや PID ファイルを使ったオペレーション制御を想定しており、運用時は data ディレクトリやフラグ設定の運用手順を整備してください。
- .env ファイルは機密情報を含むため絶対にリポジトリへコミットしないでください（config_setup.py の出力にも注意書きを追加）。
- research/factor_research.py の一部関数は実装が途中または外部依存（DuckDB スキーマ）に依存するため、実運用前の追加実装・検証を推奨します。