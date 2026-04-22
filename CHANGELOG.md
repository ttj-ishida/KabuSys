CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
- なし

[0.1.0] - 2026-04-22
--------------------

Added
- 初期リリースを公開。
- 環境・設定管理
  - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env ファイルのパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応（src/kabusys/config.py）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、環境変数に基づくアプリケーション設定を型付きプロパティで取得可能（J-Quants / kabu API / DB パス / PID/Kill Flag 等）。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の検証ロジックを実装（無効値は例外を投げる）。
- 環境設定ウィザード CLI
  - 対話形式で .env を作成・更新するツールを追加（src/kabusys/config_setup.py）。
  - デフォルト値、選択肢、シークレットマスク表示、既存 .env 読み込み、保存確認などをサポート。
- 設定検証 CLI
  - .env および config/*.yaml の存在・基本整合性を起動前に検証する CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数の未設定検出、プレースホルダ値検出、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、PyYAML 未インストール時のスキップを実装。
  - KABUSYS_ENV=live 時の追加ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の警告）を実装。
  - --strict オプションで警告も失敗（exit 1）として扱うモードをサポート。
- 実行スクリプト
  - ExecutionEngine 起動スクリプト（run_execution.py）を追加。paper_trading 環境なら専用 SQLite（paper_trading.db）を使用して本番 DB と分離。
  - SystemMonitor 用のポーリングループ起動スクリプト（run_monitoring.py）を追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用。
  - 起動時にプロセス優先度を設定し、PID ファイル管理、停止フラグ（stop_requested.flag）検出に対応。
- 発注エンジン・注文管理
  - ExecutionEngine を追加（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（8:50–9:10）と push ドレイン（9:10–15:30）を想定したセッションループ。
    - kill.flag の検査、KILL_FLAG_CLEAR_ON_START による自動クリア挙動、PID ファイル書き込み処理を実装。
    - Gate1（シグナルレベル）、Gate2（エグゼキューションレベル、レート制限/Circuit Breaker）、Gate3（ドローダウン監視 kill 判定）を呼び出す設計。
    - size_multiplier 適用時の発注数量丸め（100株単位）と 0 のスキップ。
    - 発注成功/保留/失敗の監視ログ記録を監視 DB（MonitoringDB）へ書き込むフックを持つ。
    - push (kabu push) を受けて _push_queue を処理し、sync_order → Gate3 評価を行う。
  - OrderRecord（状態マシン）を追加（src/kabusys/execution/order_record.py）。
    - 明確な OrderState 列挙、許可される遷移テーブル、transition_to() による更新（updated_at 自動更新、関連フィールド更新）。
    - 不正遷移時に InvalidStateTransitionError を送出。
  - OrderManager（OrderState マシンの外側 API）を追加（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id の重複検出（DB の部分ユニーク制約違反を DuplicateOrderError に変換）。
    - send_order: クラッシュ安全性を考慮した 2 段階永続化シーケンス（OrderSent 永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）。
    - OrderRejectedError、OrderSentPendingError に対する適切な処理（pending は broker_order_id を保存して例外伝播）。
    - sync_order: broker 側ステータス照合による状態同期と部分約定情報の更新。
    - cancel_order: 終端状態のキャンセル防止・broker 側 cancel 呼び出しと状態遷移。
- ブローカークライアント（kabu）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を利用した同期 REST クライアント。
    - トークン取得の遅延初期化と、自動再取得（401 時に1回リトライ）を実装。
    - レスポンス JSON パース失敗やネットワーク/タイムアウトを BrokerAPIError として変換。
    - 429 応答は RateLimitError にマップ。
    - kabu 注文状態コード → 内部ステータス変換マップを実装。
    - WebSocket push (stream_push) を利用したイベント取り込み（ExecutionEngine の websocket ワーカーと連携可能）。
- DB / データ
  - DuckDB（分析用）と SQLite（監視 / 発注履歴）を併用する設計を採用。
  - monitoring DB 初期化ユーティリティを参照するフローを追加（init_monitoring_db を利用）。

Changed
- n/a（初期リリース）

Fixed
- 初期リリースのため、各種例外処理とクラッシュ安全性に配慮した実装を含む（Order の 2 段階永続化、OrderSentPending の扱い、sync による回復経路など）。

Security
- 環境変数のうちシークレット値はウィザードでマスク表示するようにした（config_setup）。
- .env の内容は絶対に Git にコミットしない旨をウィザード出力に明記。

Notes / Implementation details
- YAML のパースチェックは PyYAML がインストールされている場合のみ行い、未インストール時は警告を出してスキップする（validate_config）。
- Settings のプロパティで不正な環境値の場合は ValueError を送出し、安全側で失敗させる設計。
- run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視プロセスは共通の監視 DB を参照する想定）。
- ExecutionEngine の run_session は Reconciler が与えられれば起動時に Reconciliation を実行し、継続可能な例外を捕捉してログに記録する。

開発者向け TODO / 欲しい改善点（今後の候補）
- kabu_client の非同期版（httpx.AsyncClient）への移行で WebSocket/IO を効率化。
- validate_config に YAML スキーマ検証を追加（現在はパースのみ）。
- より詳細な監視イベント（API レイテンシ分布、失敗理由別カウント）の監視 DB ロギング強化。
- ExecutionEngine のテスト用フックの追加（時刻制御・push エミュレーション強化）。

---

注: 上記は提供されたソースコードの内容から推測して作成した CHANGELOG です。ファイルやリリース日などはコード断片の時点情報に基づくため、実際のリポジトリ運用時は適宜調整してください。