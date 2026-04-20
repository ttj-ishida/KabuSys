Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。  

[Unreleased]

[0.1.0] - 2026-04-20
--------------------

Added
- 基本機能の実装（初期リリース相当）
  - 環境設定 / 起動周り
    - .env ファイルの自動読み込み機構を実装（プロジェクトルートに基づく探索、.env と .env.local の読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 高度な .env パーサを実装（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理）。
    - Settings クラスを実装し環境変数を型付きで取得。必須項目の検査や値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を行う。
    - 対話式ウィザード（kabusys.config_setup）で .env の初期作成／更新を支援。
    - 設定検証 CLI（kabusys.validate_config）を実装し、必須環境変数やパス、config/*.yaml の存在・パース検証、"live" 環境でのガードチェックを提供。
  - 実行・監視スクリプト
    - run_execution: ExecutionEngine 起動用スクリプトを実装。プロセス優先度設定、paper_trading 環境時の専用 SQLite（data/paper_trading.db）利用、BrokerClientFactory によるブローカークライアント生成、エンジンを別スレッドで実行し停止フラグ検出で安全停止。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）、停止フラグファイル検出で終了、監視 DB の初期化を実行。
  - ロギング / プロセス制御ユーティリティ
    - 統一的なログ設定ユーティリティ（kabusys.utils.logging_setup）を提供。コンソール(stdout) と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はコンソールのみで継続。
    - プロセス優先度設定ユーティリティ（kabusys.utils.process_priority）を実装。Windows/Linux/macOS を吸収し high/normal/low の簡便 API を提供。CPU affinity 設定ユーティリティも追加。
  - ポートフォリオ構築モジュール（kabusys.portfolio）
    - 銘柄選定: select_candidates（スコア降順・タイブレークルール実装）。
    - 重み計算: calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
    - リスク調整: apply_sector_cap（セクター集中上限チェック、売却予定銘柄除外、"unknown" セクターは制限対象外）、calc_regime_multiplier（regime に応じた乗数: bull/neutral/bear）。
    - ポジションサイズ計算: calc_position_sizes（risk_based / equal / score の allocation_method をサポート、単元株（lot_size）丸め、aggregate cap によるスケールダウンと残差処理）。
  - 検証ツール
    - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を実装。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH で DB 指定可能。
  - 研究用モジュール（骨格）
    - ファクター計算モジュール（kabusys.research.factor_research）の骨格を追加（モメンタム等の計算を想定）。DuckDB を用いた prices_daily/raw_financials 参照設計。

Changed
- 初期リリースのため該当なし（今後のリリースで追記予定）。

Fixed
- .env 読み込みの堅牢化
  - export プレフィックス対応、クォート内バックスラッシュエスケープ処理、インラインコメントの扱い、空行／コメント行の無視などを実装して .env パーシングの精度を向上。
- ポートフォリオ・ポジションサイズ計算の端数処理とスケーリングロジックを実装し、利用可能現金を超えた場合の安全な調整を導入。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Notes / Known issues
- factor_research.calc_momentum 等、研究モジュールの一部は実装途中であり未完（ファイル末尾に途中断片あり）。今後実装を継続予定。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過小見積りされる可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価などのフォールバックを検討。
  - lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map を受け取る拡張を検討。
- ログディレクトリ作成やプロセス優先度設定が権限不足等で失敗した場合、フォールバック（コンソール出力のみ、優先度設定スキップ）する挙動になっているため、運用時は権限・パスの確認を推奨。
- run_execution/run_monitoring は停止フラグファイル（data/stop_requested.flag 等）によるプロセス終了制御を採用。運用時のフラグ管理に注意。
- validate_config による config/*.yaml の内容検証は PyYAML 未インストール時にスキップされる（警告表示）。

今後の予定（短期）
- research モジュールの完全実装（momentum, value, volatility, liquidity 等の計算）と DuckDB クエリ最適化。
- strategy / execution の統合テスト、paper_trading 向けの自動検証パイプライン整備。
- デプロイ環境向けの監視・アラート（LINE 通知）設定の強化。