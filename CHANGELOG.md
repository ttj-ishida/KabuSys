CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを想定します。

Unreleased
----------

（現在のところ未リリースの変更はありません）

0.1.0 - 2026-04-19
-----------------

Added
- 初期リリース。KabuSys のコア機能群を実装。
  - 実行系 / 監視系起動スクリプト
    - run_execution: ExecutionEngine を起動するエントリポイントを提供。KABUSYS_ENV=paper_trading の際は paper_trading 用の SQLite を使用し MockBrokerClient 経由でペーパートレードを実行。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に依らず本番 sqlite_path を使用。
  - 設定関連
    - config: 環境変数/`.env` の読み込みと Settings クラスを実装。プロジェクトルート検出（.git または pyproject.toml 基準）、自動 `.env` ロード（.env → .env.local、OS環境変数の保護）、必須値取得ユーティリティを提供。
    - config_setup: 対話式ウィザードで `.env` を生成・更新する CLI を実装（python -m kabusys.config_setup）。
    - validate_config: 起動前の設定検証 CLI を実装。必須環境変数、KABUSYS_ENV やログレベル値、DB パス、config/*.yaml の存在・パースチェック、`--strict` オプション対応（python -m kabusys.validate_config）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio_builder: シグナル選定（select_candidates）、等配分/スコア重み（calc_equal_weights / calc_score_weights）。
    - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - position_sizing: 各銘柄の発注株数計算（calc_position_sizes）。allocation_method="risk_based" / "equal" / "score" をサポート、単元（lot_size）丸め、aggregate cap によるスケーリング、コストバッファ対応。
  - ロギング/プロセス制御ユーティリティ
    - utils.logging_setup: stdout ストリームハンドラと日次ローテートのファイルハンドラをルートロガーに設定する共通ユーティリティ。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
    - utils.process_priority: Windows/Linux/macOS 間の差を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。アクセス拒否等の例外は警告でスキップ。
  - 分析 / 検証ツール
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ等の指標を集計して PASS/FAIL 判定（閾値はソース内定義）。CLI から期間指定や DB パス指定が可能（python -m kabusys.tools.paper_verification_report）。
  - データアクセス
    - SQLite / DuckDB を用いる接続ロジックを整備。monitoring 用テーブル初期化ヘルパ（init_monitoring_db）呼び出しにより冪等に監視テーブルを保証。
  - パッケージ情報
    - パッケージメタ情報を __version__="0.1.0" として設定。

Changed
- （初期リリースのため変更履歴はなし）

Fixed
- レジリエンス・エラーハンドリング周りの考慮を追加（初期実装時点の設計上の記述に基づく）
  - .env パーサは export prefix、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを扱うように実装。OS 環境変数は保護され、.env.local は上書き（override）でロード。
  - logging_setup は既存ハンドラを適切に flush/close してから再設定し、ログディレクトリ作成失敗時にファイルハンドラ生成をスキップすることで起動継続を保証。
  - process_priority は psutil の権限エラーや未実装メソッドをキャッチして警告出力し、致命的失敗を避ける。
  - run_execution / run_monitoring は停止フラグ（data/stop_requested.flag）を監視して安全に停止できるよう実装。

Security
- センシティブ値（J-Quants トークン、kabu API パスワード等）は .env で管理し、config_setup の出力ではシークレット項目をマスク表示するように配慮。
- .env は絶対に Git にコミットしない旨をドキュメントに明記。

Notes / Implementation details
- Paper Trading と実環境の DB は分離（PAPER_TRADING_SQLITE_PATH / settings.paper_sqlite_path）。これによりペーパートレードデータは本番監視 DB と混在しない。
- run_monitoring は監視データ保存に settings.sqlite_path（本番 sqlite_path）を常に使用する設計になっているため、監視データ収集は環境に依存しない。
- position_sizing の aggregate cap のスケーリングは lot_size 単位で切り下げ／残余の再配分を行い、投下資金制限に収める工夫をしている。
- apply_sector_cap は sector_map にないコードを "unknown" 扱いし、unknown はセクター上限の対象外とする仕様。
- calc_regime_multiplier は未知のレジームに対して 1.0 でフォールバックし、警告を出力する。

Acknowledgements
- 本リリースは初期実装を想定した記録です。今後、ユニットテストの追加、エラー/例外パスの補強、外部モジュール（psutil, duckdb, yaml 等）未導入時のフォールバック強化、Strategy/Execution の詳細なバリデーションなどを予定しています。