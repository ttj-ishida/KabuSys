CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

- (なし)

[0.1.0] - 2026-04-28
--------------------

Added
- 複数の CLI エントリポイントを追加／整理
  - run_execution: ExecutionEngine の起動スクリプト（起動時リコンシリエーション、ExecutionEngine のスレッド起動、PID/停止フラグ管理、Execution Startup Summary 出力）
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、監視用 PID ファイル出力、停止フラグ検知）
  - run_intraday_monitor: ザラ場中監視 CLI（単発実行 / watch モード、状態判定と CLI 用フォーマット）
  - run_pre_market_report: Pre-Market Report の生成エントリーポイント（DuckDB / SQLite からのデータ収集、JSON/保存オプション）
  - run_market_close_report: Market Close Summary の生成エントリーポイント（JSON/保存オプション、BLOCKED 判定で非ゼロ終了）
  - run_performance_report: 運用成績サマリ（daily/weekly/monthly）用 CLI（期間指定、env 指定、保存オプション）
  - run_position_reconciliation_report: Position Reconciliation View（watch モード対応、保存/JSON オプション、差分がある場合は非ゼロ終了）
  - run_signal_queue_report: Signal Queue Confirmation View（対象日指定、JSON/保存オプション）
  - validate_config: 起動前の設定検証 CLI（.env と config/*.yaml の存在・簡易パース検証、--strict オプション）
  - config_setup: 対話式 .env 作成／更新ウィザード（既存 .env の読み込み、対話入力、.env 書き出し）
  - tools/paper_verification_report: Paper Trading 検証レポート生成スクリプト（稼働率 / 注文成功率 / 送信率 / レイテンシ P95 など）

- 設定管理（config モジュール）
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を基準）
  - .env 自動ロード機能を追加（優先順位: OS 環境 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env パーサーを強化（export プレフィックス対応、クォート文字とバックスラッシュエスケープ、インラインコメント処理など）
  - Settings クラスを実装し、アプリケーション設定（各種 API トークン、DB パス、PID/フラグパス、監視閾値、環境判定など）を明確化
  - paper_trading 用の paper_sqlite_path / PAPER_FILL_MODE などペーパートレード向け設定を追加（PAPER_FILL_MODE 値の検証あり）

- 監視／実行の運用面
  - init_monitoring_db 呼び出しにより監視用テーブルの存在を保証（冪等）
  - プロセス優先度を設定するフック（set_process_priority("high") を起動時に呼び出し）
  - PID ファイルと停止フラグの取り扱いを統一（data/*.pid および data/stop_requested.flag など）

Changed
- DB の取り扱い
  - run_execution: KABUSYS_ENV が paper_trading の場合、SQLite の接続先を paper_sqlite_path（デフォルト data/paper_trading.db）に切り替え、ペーパートレード用 DB と本番 DB を完全分離
  - run_monitoring: Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視データは本番 DB に保存）
  - 多くのレポート系 CLI は DuckDB を読み取り専用で接続するように変更（read_only フラグ利用）

- 設定検証とエラー報告
  - validate_config において必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在有無チェックを追加
  - 本番環境（KABUSYS_ENV=live）向けのガードチェックを追加（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定に関する警告）

- risk_config.yaml の読み込みと検証（run_execution 内）
  - YAML のパース失敗・キー欠如・値レンジ等で明確なエラーを投げる（例: max_position_pct / max_utilization / max_drawdown は (0,1]、rate_limit 等は >=1）
  - 読み込み完了時にログ出力で主要パラメータを表示

- CLI 出力／保存の挙動
  - JSON 出力と保存オプションの取り扱いを統一（--json 時は JSON を stdout に出力し、保存先メッセージは stderr に出す等、ストリーム汚染を回避）
  - watch モードでは最低 1 秒のスリープを強制しスピンループを抑止

Fixed
- .env 読み込みでのファイルアクセスエラーを警告に変換して処理継続
- run_execution の起動フローで起動時リコンシリエーションの失敗があっても起動を継続するように例外ハンドリングを追加（Startup Summary 生成失敗は警告扱い）
- run_monitoring のポーリング間隔取得ロジックを堅牢化（MONITOR_POLL_INTERVAL が不正（0 以下や非数）な場合にデフォルトへフォールバックし、警告ログを出力）

Security
- デバッグ情報・シークレット表示について配慮
  - config_setup の確認画面でシークレット項目はマスク表示するようにした

Documentation / Developer experience
- 各 CLI に使用例を docstring に追加（モジュールトップ）
- config_setup による .env 生成テンプレートを整備（コメント付きファイルヘッダ、コミット禁止注意喚起）

Other
- パッケージ初期バージョンを __version__ = "0.1.0" に設定

Notes / Breaking changes
- run_monitoring が常に本番用 sqlite_path を使用するようになったため、監視データの保存先が環境に依存しなくなりました。テストや開発で監視データを分離したい場合は sqlite_path を環境に応じて明示的に切り替えてください。
- PAPER_TRADING 環境では run_execution が paper_trading 用 DB を使うため、本番 DB とデータが混在しません。既存運用で DB パスを期待しているスクリプトがある場合は確認してください。

もし CHANGELOG に追加してほしい詳細（たとえば各 CLI の具体的なオプション一覧やログ出力例、エラーメッセージの完全コピー等）があれば教えてください。コードの別ファイル（monitoring_db や execution_engine 等）にも変更点がある場合は、そのファイル群を提供いただければさらに詳細な変更点を反映します。