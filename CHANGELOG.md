CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-17
------------------

Added
- 初回リリース: KabuSys コードベースを追加。
- 実行スクリプト:
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用の sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB を使用し MockBrokerClient を用いる（本番 DB と完全分離）。停止フラグ／PID 管理とデーモンスレッドでのエンジン実行をサポート。
- 設定管理:
  - config.py: .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。.env/.env.local の読み込み順と保護（OS 環境変数の上書き防止）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを導入し、各種環境変数の取得とバリデーションを提供（DB パス、ログレベル、KABUSYS_ENV、PAPER_FILL_MODE 等）。
- 設定支援 CLI:
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装。デフォルト値、選択肢、シークレット入力サポート、.env 書き出しテンプレートを含む。
  - validate_config.py: 起動前チェック CLI を実装。.env と config/*.yaml の存在・簡易検証、必須環境変数チェック、KABUSYS_ENV の妥当性チェック、--strict オプション（警告を失敗扱い）を提供。PyYAML 未導入時は YAML 検証をスキップして警告を出す。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: 候補銘柄選定（スコア降順）と重み計算（等金額・スコア加重）を実装。スコアが全て 0 の場合のフォールバックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバック動作を定義。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）を実装。単元株（lot_size）丸め、銘柄ごとの上限、aggregate cap によるスケーリング、残差分配ロジックを含む。
  - portfolio/__init__.py: 主要関数をエクスポートするパッケージ API を提供。
- リサーチ / ファクター計算:
  - research/factor_research.py: DuckDB 接続を用いたモメンタム・ボラティリティ等のファクター計算を実装（prices_daily / raw_financials を参照）。P95 計算ユーティリティや各種移動平均・ATR 等を計算する関数を実装。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。期間指定（--from/--to）や DB 指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。稼働率・注文成功率・送信率・レイテンシ（P95）等の判定と閾値（デフォルト値）を提供。
- ユーティリティ:
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加。Windows（psutil の優先度定数）／POSIX（nice 値）差分を吸収。例外時に警告を出してフォールバック。CPU アフィニティ設定関数 set_cpu_affinity を実装。
- 監視用 DB 初期化: monitoring.monitoring_db.init_monitoring_db の利用による監視テーブルの冪等な初期化処理を導入（run_monitoring / run_execution で利用）。
- パッケージメタ: __version__ = "0.1.0" を設定。

Changed
- ログやメッセージ類は日本語の説明や詳しいログを追加し、運用者が状況把握しやすいメッセージに改善。
- .env のパース仕様を拡張:
  - export プレフィックス対応
  - シングル／ダブルクォート内のバックスラッシュエスケープ処理対応
  - クォートなし値のインラインコメント扱いルールの明確化（直前が空白またはタブの場合のみコメントと認識）
- .env ロードの挙動:
  - OS 環境変数は保護（protected）され、.env.local の override 时でも既存の OS 環境変数は上書きされないように実装。

Fixed
- process_priority.set_process_priority: 権限不足や未対応メソッドで失敗する可能性に対して例外キャッチと警告出力を追加し、起動停止につながらないように改善。
- run_execution: paper_trading モード時に paper 用 SQLite パスを使用して本番 DB と分離するように修正（Settings から paper_sqlite_path を使用）。
- run_monitoring: 停止フラグ（data/stop_requested.flag）検出時にループを安全に終了する動作を追加。check_once() 内の例外を捕捉して次回ポーリングまで待機する耐障害性を追加。

Security
- .env に機密情報が含まれる点を明示（config_setup にて .env を絶対に Git にコミットしない旨の注意書きを追加）。

Notes / Migration
- 自動 .env 読み込みはデフォルトで有効。テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading 用 DB はデフォルト data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）。本番と完全分離して運用してください。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能。0 以下や不正な値はデフォルト（60 秒）にフォールバックします。
- validate_config.py の --strict モードを使うと警告も失敗扱い（exit code 1）になります。本番環境導入前のチェックに利用してください。

Acknowledgements
- 初回実装にあたり、運用性向上のための CLI、堅牢な設定読み込み、ポートフォリオ構築・サイズ計算ロジック、検証レポート等を整備しました。今後はテスト、ドキュメント、追加の戦略ロジックや E2E の検証を進めていきます。