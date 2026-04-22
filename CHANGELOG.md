# CHANGELOG

すべての注目すべき変更を記載します。フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-22
初回リリース — KabuSys の基盤機能を導入しました。

### 追加
- プロジェクト初期版の実装を追加。
  - パッケージ情報
    - src/kabusys/__init__.py: バージョン情報を v0.1.0 として追加。
- 環境設定管理
  - src/kabusys/config.py
    - Settings クラスを実装し、環境変数から各種設定値を提供（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、KABUSYS_ENV 等）。
    - env 値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）で不正値は ValueError を送出。
    - .env 自動ロード機能を追加（優先順: OS 環境 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml を基準に探索。
    - .env の読み込みは既存 OS 環境変数を保護する仕組み（protected set）を持つ。
    - .env 行パーサーは export 形式、引用符付き値、バックスラッシュエスケープ、インラインコメント等に対応。
- 対話式設定ウィザード
  - src/kabusys/config_setup.py
    - .env の初期作成・更新を対話式に支援する CLI を実装（python -m kabusys.config_setup）。
    - 秘匿項目は表示時にマスク、デフォルト値や選択肢をサポート。
    - 保存時にテンプレ形式で .env を出力（コミットしない旨の注意書き含む）。
- 設定検証ツール
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の起動前チェック用 CLI（python -m kabusys.validate_config）。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの存在チェック等を行う。
    - config/*.yaml の存在チェックと（PyYAML がインストールされている場合の）パース検証を実施。PyYAML 未インストール時は警告を出してスキップ。
    - プレースホルダ値（末尾が "_here" または "your_value"）の警告検出。
    - --strict フラグを指定すると警告も FAIL（exit code 1）扱いに。
- 実行用スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を用いた実行エントリポイント。PID ファイル、停止フラグ(stop_requested.flag)の検出、プロセス優先度設定を含む起動処理。
    - paper_trading モード時は専用の paper_trading DB を使用して本番 DB と完全分離。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用。
- 注文関連コアロジック
  - src/kabusys/execution/order_record.py
    - OrderRecord データモデルと状態遷移（OrderState 列挙）を実装。許可される状態遷移を定義し、不正遷移時は InvalidStateTransitionError を送出。
  - src/kabusys/execution/order_manager.py
    - OrderManager: signal からの発注フロー、DB との併用ロジックを実装。
    - 同一 signal_id に対する重複注文検出用の DuplicateOrderError を導入。
    - send_order() はクラッシュ耐性を意識した 2 相永続化（OrderSent の永続化 → ブローカ API 呼び出し → broker_order_id を永続化 → OrderAccepted へ遷移）を実装。
    - OrderRejectedError / OrderSentPendingError の扱いを実装。OrderSentPendingError は broker_order_id を DB に残して再送出（Reconciliation 対象）。
    - sync_order() によるブローカー状態同期の実装（状態マッピング、部分約定の更新等）。
    - cancel_order() によるキャンセルロジック（キャンセル不可状態でのエラー、broker 側キャンセル呼び出し）。
- 発注エンジン
  - src/kabusys/execution/execution_engine.py
    - ExecutionEngine 実装（Signal Queue Pull 型）。
    - シグナル処理ロジック（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を想定したセッション運用。
    - Gate1/2/3 によるリスクチェック連携（RiskManager 使用）。Gate2 のレート制限はリトライと CB（回路遮断）判定をサポート。Gate3 で NG の場合は kill_switch を発動。
    - kill_switch(): 全 active 注文のキャンセル、エンジン停止フラグ設定を実装。
    - WebSocket ワーカースレッド（broker が stream_push を提供する場合に起動）と _push_queue による非同期処理。
    - 発注成功/保留/失敗時に position_entries へ約定予定日（翌営業日）を記録（DuckDB を利用）。監視DBへのトレードイベント記録にも対応（監視 DB が提供される場合）。
    - PID ファイル管理、起動時の Reconciliation 実行（reconciler が提供される場合）を実装。
- ブローカークライアント（kabu station 実装）
  - src/kabusys/execution/kabu_client.py
    - KabuStationClient: httpx を用いた REST クライアント実装。トークン取得の遅延初期化、401 発生時の自動再取得+リトライを実装。
    - レスポンス JSON パース失敗を BrokerAPIError に変換、429 を RateLimitError に変換、5xx を BrokerAPIError に変換。
    - kabu の注文状態コードを内部ステータス文字列にマッピング（open, partial, filled, cancelled, rejected）。
    - WebSocket push（stream_push）を想定した設計（WebSocket ライブラリ参照あり）。
- 監視・DB 初期化
  - src/kabusys/monitoring/* への参照を組み込み（init_monitoring_db 呼び出し）。監視用 SQLite の初期化・書き込み処理に対応（run_monitoring/run_execution で使用）。
- ユーティリティ
  - ロギング設定、プロセス優先度変更ユーティリティの呼び出しを実行スクリプトに統合。

### 変更
- （初版につき該当なし）

### 修正
- （初版につき該当なし）

### 既知の注意点 / 仕様
- Settings の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時に推奨）。
- validate_config の YAML 検証は PyYAML がインストールされていない環境ではスキップされ、警告のみ発生します。
- MONITOR_POLL_INTERVAL に 0 以下や不正値を与えるとデフォルト 60 秒にフォールバックします（time.sleep に負の値を渡さないための安全策）。
- PAPER_FILL_MODE は "instant"|"partial"|"never"|"reject" のみ許容。無効値はプログラム起動時に例外となります。
- ExecutionEngine のタイミング（8:50/9:10/15:30）は EngineConfig で上書き可能。
- .env ファイルは出力時に Git へコミットしない注意書きを含みます。

### セキュリティ
- .env はシークレットを含むため、生成した .env をリポジトリにコミットしない旨を強調。
- 認証トークンの扱いは Settings / KabuStationClient 内で直接環境変数を参照・保持します。トークンの取り扱いは運用方針に従ってください。

---

今後の予定（例）
- BrokerAPIProtocol の追加実装（モック / 本番クライアントの整備）。
- Reconciler の強化・ユニットテスト追加。
- WebSocket push の安定化・テストカバレッジ拡大。