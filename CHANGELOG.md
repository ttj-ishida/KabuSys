CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

[0.1.0] - 2026-04-23
--------------------

Added
- 初期リリースを追加。
- 環境/設定管理:
  - Settings クラスを実装し、環境変数経由で設定値を取得可能に。
  - 自動 .env ロード機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。.env と .env.local の読み込み順・保護設定に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env のパースロジックを強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応）。
- 設定ウィザード CLI:
  - python -m kabusys.config_setup による対話式ウィザードを実装。.env の初期生成・更新を支援し、秘密値のマスク表示・選択肢・既存値の再利用をサポート。
- 設定検証 CLI:
  - python -m kabusys.validate_config を実装。必須環境変数や config/*.yaml の存在・YAML パース（PyYAML があれば）を起動前に検出。--strict フラグで警告も失敗扱いにできる。
- 実行/監視用エントリポイント:
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。paper_trading 環境時は別 SQLite（paper_trading 用）へ記録して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート。監視は環境に関わらず本番 sqlite_path を使用する設計。
- 発注エンジンと関連コンポーネント:
  - ExecutionEngine 実装（シグナル処理・WebSocket push ドレイン・セッション管理・PID/kill.flag 処理等）。
  - OrderRecord: 注文状態（State Machine）モデルと厳格な遷移検証を実装。allowed transitions を明示。
  - OrderManager: OrderRecord と OrderRepository を組み合わせた外向き API を実装（create/send/sync/cancel）。DuplicateOrder 判定、送信時の安全な永続化フロー（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）を導入。
  - ExecutionEngine 側での Gate チェック（Gate1: シグナル、Gate2: エグゼキューション/レート制限、Gate3: ドローダウン）や kill_switch の統合。
  - Reconciler（起動時リコンシリエーション）呼び出しフックを用意。
  - 発注失敗・保留（OrderSentPendingError）の扱いを明確化し、保留時は broker_order_id を永続化して再照合対象とする。
- ブローカークライアント:
  - KabuStationClient 実装（同期 httpx ベース）。トークン管理（遅延取得・401 自動再取得）、HTTP エラー/タイムアウト/429（RateLimitError）ハンドリング、JSON パース例外の BrokerAPIError 変換を実装。
  - WebSocket push を受け取る stream_push を想定した設計（存在しない場合は警告してスキップ）。
- データベース:
  - DuckDB（分析用）および SQLite（監視・発注履歴用）の接続利用を導入。監視用 DB の初期化関数 init_monitoring_db 呼び出しを追加。
- ユーティリティ:
  - process_priority 設定、ロギング初期化のフックを導入（各 run_* スクリプトで使用）。
- 監視統合:
  - ExecutionEngine から監視 DB へ発注イベント（ログ/レイテンシ等）を書き込むための呼び出しを追加（監視 DB が提供される場合）。

Changed
- 環境値検証の強化:
  - validate_config と Settings で KABUSYS_ENV / LOG_LEVEL の有効値チェックを行うようにし、不正値を検出してエラー/警告を出す。
  - validate_config は必須環境変数のプレースホルダ検出（末尾が _here や your_value）を警告として報告。
- 起動時安全性向上:
  - run_execution / run_monitoring でプロセス優先度を最初に設定し、PID ファイルと stop_flag の扱いを明確化。
  - ExecutionEngine 起動時の kill.flag の既存検査と KILL_FLAG_CLEAR_ON_START による自動クリア動作を導入。

Fixed
- 発注フローのクラッシュ耐性改善:
  - send_order の実装を 2 相永続化（OrderSent の永続化を broker 呼び出し前、broker_order_id の永続化 → OrderAccepted の更新）にして、クラッシュ時でも再照合で回復可能に。
- .env 読み込み時の例外処理を追加（ファイルオープン失敗時に警告を出して継続）。
- YAML パースチェックは PyYAML 未インストール時にスキップし、その旨を警告するように変更。

Security
- 特になし（初期リリース）。

Notes / Implementation details
- .env の読み込み順と保護:
  - OS 環境変数 > .env.local > .env の優先度で読み込まれる。override の挙動と "protected"（OS 環境変数を上書きしない）オプションを組み合わせて実装。
- 本番/ペーパー分離:
  - paper_trading モードでは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番データと物理的に分離する。
- 設定検証 CLI:
  - config/*.yaml の存在チェックと（PyYAML が利用可能な場合は）パースチェックを行う。config ファイルが見つからない場合は generate_config.py で生成可能である旨を警告。
- Order state machine:
  - OrderRecord.transition_to で遷移許可を厳格に検査し、不正遷移は InvalidStateTransitionError を raise。
  - cancel の可否判定や、sync による部分約定進捗の更新処理を明確化。

開発者向け
- エントリポイント:
  - 実運用用: python -m kabusys.run_execution / python -m kabusys.run_monitoring
  - ユーティリティ: python -m kabusys.config_setup / python -m kabusys.validate_config
- パッケージバージョンは __version__ = "0.1.0" に設定。

今後の予定（想定）
- async 対応のための KabuStationClient の httpx.AsyncClient 置換対応
- より詳細な監視メトリクスの拡充と Web UI などの統合
- ユニットテストの充実（特にリコンシリエーション、order send のクラッシュシナリオ）

-----------
この CHANGELOG は、提供されたコードベースの実装内容から推測して作成しています。内部の実装意図や未公開の変更は反映されていない場合があります。