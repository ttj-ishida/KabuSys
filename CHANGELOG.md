CHANGELOG
=========

すべての注目すべき変更点を記録します。形式は "Keep a Changelog" に準拠しています。

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-04-22
-----------------
Added
- 初期リリース（0.1.0）。
- 環境・設定管理
  - kabusys.config: .env ファイルおよび環境変数からの設定読み込み機能を追加。
    - プロジェクトルート自動検出（.git / pyproject.toml を基準）。
    - .env / .env.local の順で自動読み込み（OS 環境変数は保護され、.env.local は上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
    - .env のパースを堅牢化：export プレフィックス対応、クォートとバックスラッシュエスケープ、インラインコメントの取り扱い。
  - Settings クラスによるアプリ設定取得 API を提供（J-Quants token、kabu API、DB パス、PID/Kill フラグパス、閾値、環境/ログレベル検証など）。
  - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等、ペーパートレード向け設定をサポート（設定値検証を実施）。
- 対話式設定ウィザード
  - kabusys.config_setup: .env の初期作成・更新を対話式で行う CLI を追加。
  - デフォルトや選択肢の提示、シークレット値のマスク表示、既存 .env の読み込み/再利用、生成される .env のテンプレートを実装。
  - .env ファイル生成時に Git へコミットしない旨の注記を出力。
- 設定検証ツール
  - kabusys.validate_config: .env および config/*.yaml の起動前検証 CLI を追加。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在確認と YAML パース検証（PyYAML が未インストールの場合はスキップして警告）。
  - --strict オプションで警告も失敗扱いにするモードを提供。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告など）。
- 実行スクリプト / エンジン
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - プロセス優先度の設定（高優先）とログセットアップを行う。
    - paper_trading モードでは専用の SQLite（paper_trading.db）を使用して本番 DB と分離。
    - PID ファイル書き込み、stop フラグ検出、スレッドでのエンジン実行/監視を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
- 発注・状態管理
  - execution.order_record: OrderRecord データモデルと明確な状態遷移（OrderState enum）・遷移検証（InvalidStateTransitionError）を実装。
  - execution.order_manager: OrderManager による外向き API（create_order, send_order, sync_order, cancel_order）を追加。
    - create_order は signal_id ごとの重複検出（DuplicateOrderError）を行い、DB のユニーク制約違反も DuplicateOrderError に変換可能。
    - send_order はクラッシュに対する耐性を考慮した 2 相的永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）を実装。OrderRejectedError/OrderSentPendingError 等のハンドリングを行う。
    - sync_order は broker 側の状態を照合してローカル状態を同期、部分約定の進行に対する差分更新対応。
    - cancel_order は状態を検査してから broker のキャンセルを呼び出し、終端状態のキャンセル禁止を明示。
- ExecutionEngine（発注フロー）
  - Signal Queue からのシグナル処理（_process_signals）、8:50〜9:10 のシグナル処理と 9:10〜15:30 の push ドレインループを実装。
  - Gate 検査（Gate1: シグナルレベル、Gate2: エグゼキューション/レート制限、Gate3: ドローダウン監視）を組み込み、NG 時の挙動（スキップ／kill_switch 発動）を実装。
  - kill_switch 実装：全 active 注文のキャンセル（例外や API エラーはログ処理して継続）と全ループ停止。
  - WebSocket push を受けて _push_queue に投入するワーカー（broker 側で stream_push を持つ場合のみ稼働）。
  - 発注後の position_entries 書き込み（DuckDB への挿入／更新）と監視 DB へのトレードイベント記録を実装（監視書き込み失敗時は発注フロー継続）。
- ブローカークライアント
  - execution.kabu_client: KabuStationClient を追加（httpx 同期クライアント）。
    - トークン取得と内部トークンキャッシュ、401 発生時の自動再取得＋1回リトライを実装。
    - レスポンス JSON パース失敗、タイムアウト、ネットワークエラー、429（RateLimitError）や 5xx（BrokerAPIError）などの例外分類を実装。
    - kabu ステータスコード → 内部ステータス文字列のマッピングを定義。
- 監視周り
  - monitoring モジュール関連（init_monitoring_db, SystemMonitor 参照）を run_monitoring/run_execution で利用可能に。
- その他ユーティリティ
  - ロギングセットアップ、プロセス優先度設定ユーティリティを利用するように各起動スクリプトを構成。

Changed
- なし（初期リリースのため "Added" が中心）。

Fixed
- .env パーサの堅牢化により、次のケースを正しく処理:
  - export プレフィックス付き行
  - シングル/ダブルクォート内のバックスラッシュエスケープ
  - クォート無しの値におけるインラインコメントの判定（直前の空白に依存する仕様）
- Execution / Order フローにおけるクラッシュ耐性を向上（send_order の 2 段階永続化、broker_order_id が残ることでリコンシリエーションが状態回復可能）。

Security
- .env を絶対に Git にコミットしないようウィザードの出力に注意書きを追加。
- KILL_FLAG_CLEAR_ON_START のデフォルトを安全側（0）に設定。KABUSYS_ENV=live の場合は設定値に対して警告を出す仕様で誤設定の注意喚起を行う。

Notes / Implementation details
- 設計の意図として、DB（SQLite）は実際の注文ライフサイクルの永続化とリコンシリエーションを重視し、クラッシュ後の復旧経路（OrderSent のまま残るケース、broker_order_id が先に書き込まれるケースなど）を考慮して実装している点を明記。
- Monitoring は KABUSYS_ENV に依存せず常に本番 sqlite_path を用いる（運用上の設計判断）。
- 一部モジュールは外部ライブラリ（PyYAML, httpx, websocket, duckdb 等）に依存。PyYAML 未インストール時は validate_config が YAML 内容検証をスキップして警告する。

未対応 / 既知の制約
- 非同期（async）クライアントは未実装（将来 httpx.AsyncClient に置換可能とする設計コメントあり）。
- 一部のエラー分類やリトライポリシーは簡易化されている箇所があり、運用で調整が必要な場合がある。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）を参照するロジックは存在するが、そのスクリプト自体は本リリースに含まれない場合がある。

参考
- パッケージバージョン: __version__ = "0.1.0" (src/kabusys/__init__.py)