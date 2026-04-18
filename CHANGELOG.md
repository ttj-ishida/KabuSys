CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（日本語訳）  
日付: 2026-04-18

Unreleased
----------

（現在なし）

[0.1.0] - 2026-04-18
--------------------

Added
- 全体
  - プロジェクト初期リリース（バージョン 0.1.0）。基本的な自動売買フレームワーク、設定/ユーティリティ群、監視・実行用スクリプト、ポートフォリオ構築ロジック、および検証ツールを提供。
- 設定関連
  - .env 自動読み込み機能を追加（.env, .env.local）。プロジェクトルートは .git または pyproject.toml を基準に探索（src/kabusys/config.py）。
  - 環境変数読み込みウィザードを追加：対話式で .env を作成/更新できる CLI（src/kabusys/config_setup.py）。
  - 設定検証 CLI を追加：.env や config/*.yaml の基本チェック、--strict モードで警告をエラー扱いにできる（src/kabusys/validate_config.py）。
  - Settings クラスを追加し、環境変数を型付きで取得可能に（src/kabusys/config.py）。
  - PAPER_FILL_MODE のバリデーション実装（有効値: instant/partial/never/reject）。
- 実行/監視
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の際には paper_trading 専用 SQLite を利用して本番 DB と分離。
    - BrokerClientFactory に基づくブローカークライアント選択、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - 実行用 PID ファイル管理、停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - SystemMonitor を用いたポーリングループ実装と停止フラグ検出を実装。
    - 監視は環境に関わらず本番 sqlite_path を使用する旨を明示。
- ポートフォリオ構築
  - 候補選定・重み計算ロジックを追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア順で上位 N 抽出）、等金額重み calc_equal_weights、スコア加重 calc_score_weights（スコア合計が 0 の場合は等配分へフォールバック）。
  - セクター制約とレジーム乗数を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap によるセクター集中抑制（売却予定銘柄の除外対応、"unknown" セクターは除外しない）。
    - calc_regime_multiplier によるレジーム別の投下資金乗数（bull/neutral/bear の値と未知レジームのフォールバック挙動）。
  - 株数決定ロジックを追加（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の割当方式対応、単元株（lot_size）丸め、per-position と aggregate の上限処理、コストバッファ考慮のスケーリング配分実装。
- ユーティリティ
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラの重複防止。
    - LOG_DIR 環境変数、アプリ名ベースのログファイル名（例: logs/execution.log）、ファイルハンドラ作成失敗時のフォールバック対応。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS の差分を吸収して優先度設定（high/normal/low）を行う。アクセス拒否や未対応 OS の場合は安全にスキップ。
    - CPU affinity 設定関数 set_cpu_affinity を追加（先頭 N コアに固定）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH を参照または --db で上書き。
- リサーチ
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - モメンタム/ボラティリティ/バリュー等の説明と calc_momentum の雛形（DuckDB 接続を受け取り prices_daily を参照する設計）。（実装は継続中）

Changed / Improved
- .env 読み込み
  - .env パーサーを強化：export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行内コメントの取り扱いを改善（src/kabusys/config.py）。
  - 自動ロード順序を明確化: OS 環境変数 > .env.local > .env。OS 環境変数は上書き保護される。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
- 実行/監視プロセス
  - 起動時にプロセス優先度を "high" に設定するフローを追加（run_execution.py, run_monitoring.py）。
  - DB 初期化関数 init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - run_execution は paper_trading 環境では paper_sqlite_path を使用するなど DB 分離を明確化。
- ロギング
  - setup_logging は既存ハンドラを安全に flush/close してからクリアし、二重出力を避けるよう改善。
- 安全性/運用性
  - 停止フラグ（data/stop_requested.flag）と PID ファイルの取り扱いを統一して安全停止をサポート（run_execution.py, run_monitoring.py）。
  - validate_config による起動前チェックを充実させ、YAML パースチェック（PyYAML があれば）や本番用ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定の警告）を追加。

Fixed
- .env 読み込み時の既存 OS 環境変数上書き問題を回避（protected セットにより保護） — config 自動読み込みの安全性向上（src/kabusys/config.py）。
- logging_setup: ログディレクトリ作成失敗時にクラッシュするのではなく、ファイル出力をスキップして stdout のみで継続するように修正。

Security
- 重要なシークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を .env で管理することを明記し、config_setup にてシークレット項目をマスクして表示するようにした（src/kabusys/config_setup.py）。

Notes / Breaking changes / Important behavior
- 監視プロセス（run_monitoring）は環境に関わらず Settings.sqlite_path（本番の sqlite_path）を使用します。複数環境で同一 DB を使いたくない場合は注意してください。
- PAPER_TRADING（paper_trading 環境）では専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）が使用されるため、本番 DB とデータは分離されます。
- set_process_priority / set_cpu_affinity は権限や OS に依存するため、失敗しても例外を上げず警告ログでスキップします。

Acknowledgements
- 本リリースは初期実装段階です。機能拡張や細かな挙動調整（ファクター計算の完成、Strategy/Execution の統合テスト、より詳細なエラーハンドリング等）は今後のリリースで行います。

-----