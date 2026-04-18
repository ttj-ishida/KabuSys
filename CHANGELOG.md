CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-18
--------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークのコア機能群を追加。
- 実行/監視ランナースクリプト:
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い、paper_trading 用 DB（data/paper_trading.db）を使用して本番 DB と完全に分離する実行フローを提供。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 両スクリプトで停止制御用フラグファイル（data/stop_requested.flag 等）と PID ファイルを使用する仕組みを実装。
- 設定管理:
  - config.py: .env 自動読み込み（.env → .env.local、OS 環境変数優先）、プロジェクトルート自動検出機構（.git または pyproject.toml 基準）、Settings クラスによる型付き取得とバリデーションを提供。
  - .env の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定を追加。
- 環境セットアップ・検証 CLI:
  - config_setup: インタラクティブな .env 設定ウィザードを追加（シークレットマスク表示・既存値読み込み・.env 生成）。
  - validate_config: .env および config/*.yaml の事前検証ツールを追加（--strict オプションで警告を FAIL 扱いにできる）。PyYAML があれば YAML パース検証も実施。
- 監視・モニタリング:
  - monitoring_db 初期化を行うユーティリティ（監視テーブル保証、冪等）。
  - SystemMonitor ポーリングループ内で例外発生時のログ捕捉と継続動作の実装。
- ポートフォリオ構築（純粋関数群）:
  - portfolio_builder: 候補選定（スコア順）、等金額/スコア加重配分の実装。
  - position_sizing: 発注株数決定ロジック（risk_based / equal / score、lot_size 単位丸め、aggregate cap スケーリング、コストバッファ対応）。
  - risk_adjustment: セクター集中制限の適用、レジームに応じた投下資金乗数 calc_regime_multiplier を実装。
- ツール:
  - tools/paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。閾値はスクリプト内で定義されている（稼働率 99%、填充率 90% 等）。
- 研究モジュール（骨格）:
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの雛形を追加（モメンタム・ボラティリティ等の計算設計・定数を含む）。
- ロギング・プロセス制御ユーティリティ:
  - utils/logging_setup: コンソール(stdout) と 日次ローテートファイルハンドラ（TimedRotatingFileHandler）を一貫して設定するユーティリティ。ログディレクトリ作成失敗時はファイル出力を安全にスキップ。
  - utils/process_priority: Windows / POSIX の差分を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定を提供。アクセス権限がない場合は警告ログを出してスキップ。
- パッケージメタ:
  - __init__.py にてバージョンを 0.1.0 に設定。

Changed
- DB 分離ポリシー明示化:
  - 監視（run_monitoring）は環境にかかわらず本番の sqlite_path を使用するように設計されている旨を明記（監視は本番データを参照する前提）。
  - 実行（run_execution）は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離。
- .env パース/ロードの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱いなどをサポートしてより現実的な .env のパースに対応。
  - .env.local を使った上書き処理と OS 環境変数保護（protected set）を実装。

Fixed
- CLI / スクリプトの堅牢性強化:
  - run_monitoring のポーリングループにおいて check_once() での例外を捕捉し、ループを継続することで単回の失敗でプロセス自体が停止しないように修正。
  - run_execution/run_monitoring で DB 接続を finally ブロックで閉じるようにしてリソースリークを防止。
- logging_setup:
  - StreamHandler を stdout に固定して、cron/タスクスケジューラ等での stdout/stderr の扱いを単純化。
  - 既存ハンドラがある場合は一旦 flush/close してから削除することで二重ハンドラ設定を回避。

Security
- config_setup で .env を作成する際、シークレット項目は対話中表示をマスク（****）することで秘匿性を向上。

Internal
- ドキュメント/コメントの充実:
  - 各モジュールにおいて設計意図・参照先（PortfolioConstruction.md 等）や注意点（例: price 欠損時の挙動、将来の拡張案）をコメントで明記。
- ログや挙動のデバッグ情報を適宜 logger.debug/ warning で出力する実装を追加し、運用時のトラブルシュートを容易化。

Notes / Migration
- 環境変数の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔（秒）を指定できます。1 未満や不正値はデフォルト 60 秒にフォールバックします。
- PAPER_FILL_MODE の有効値: "instant" | "partial" | "never" | "reject"。不正値設定時は起動時にエラーになります。
- 本番運用時は KABUSYS_ENV=live 設定下での LINE 通知周り（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）と KILL_FLAG_CLEAR_ON_START の値を特に注意してください。validate_config により起動前にこれらをチェックできます。
- paper_verification_report はデフォルトで data/paper_trading.db を参照します。別パスを使う場合は --db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数で指定してください。

Acknowledgements
- このリリースは初期機能セット（実行・監視・ポートフォリオ構築・運用ツール・設定管理）を提供します。今後、factor_research の完成、戦略実行パイプラインの追加テスト、手数料/スリッページモデルの改良などを予定しています。