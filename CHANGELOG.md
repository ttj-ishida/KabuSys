# Changelog

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/) の形式に準拠します。

## [0.1.0] - 2026-04-23

初回リリース。

### 追加 (Added)
- パッケージ初期リリース (kabusys v0.1.0) を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境・設定管理機能 (src/kabusys/config.py)
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に探索する _find_project_root() を実装。
  - .env ファイルの自動読み込みロジックを追加（OS 環境変数 > .env.local > .env）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグに対応。
  - .env のパース機能を強化:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォートとバックスラッシュエスケープ対応。
    - インラインコメントの扱いを改善。
  - 環境変数取得ヘルパー _require() を追加して必須設定の欠如時に ValueError を投げるように。
  - Settings クラスを実装し、主要な設定値（J-Quants, kabu API, DB パス, PID/KILL フラグパス, 閾値, 環境/ログレベルなど）をプロパティとして提供。
  - PAPER_FILL_MODE の検証および paper_trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH）を追加。

- 対話式設定ウィザード CLI (src/kabusys/config_setup.py)
  - .env の初期作成・更新を支援する対話式ウィザードを追加（python -m kabusys.config_setup）。
  - 入力項目定義、シークレットのマスク表示、選択肢サポート、既存 .env 読み込み、キャンセル時の挙動を実装。
  - .env を安全なヘッダコメント付きで出力する _write_env() を実装。
  - デフォルト項目群（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* など）を用意。

- 設定検証 CLI (src/kabusys/validate_config.py)
  - .env および config/*.yaml の起動前チェックを行う CLI を追加（python -m kabusys.validate_config）。
  - 必須/任意の環境変数リスト、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリ存在チェックを実装。
  - config/*.yaml の存在確認および PyYAML が存在する場合は YAML パース検証を実施。PyYAML 未インストール時は警告でスキップ。
  - KABUSYS_ENV=live の際の追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の危険値チェック）を実装。
  - --strict オプションで警告を FAIL として扱うモードを追加。CLI はエラー時に exit(1)。

- 実行スクリプト: ExecutionEngine 起動 (src/kabusys/run_execution.py)
  - ExecutionEngine を起動するエントリポイントを追加（プロセス優先度設定、PID/STOP フラグ管理、DB 接続）。
  - paper_trading 環境では paper_trading 専用 SQLite を使用し、本番 DB と分離。
  - stop_requested.flag 検出で起動中断/停止を行う仕組みを導入。

- 実行スクリプト: SystemMonitor 起動 (src/kabusys/run_monitoring.py)
  - 監視プロセス起動スクリプトを追加（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可、デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する仕様。
  - 監視ループは stop_requested.flag を監視して安全に終了。

- 発注エンジンコア (src/kabusys/execution/*.py)
  - OrderRecord (src/kabusys/execution/order_record.py)
    - 注文状態列挙 OrderState と許容遷移表を実装。
    - transition_to() による遷移検証と更新（更新時刻を UTC で自動更新）。
    - InvalidStateTransitionError を追加。
  - OrderManager (src/kabusys/execution/order_manager.py)
    - signal_id ベースの重複検出と DuplicateOrderError を実装。
    - create_order(): DB に OrderCreated を保存（UUID を client_order_id に採番）。
    - send_order(): 2 段階の永続化（OrderSent を先に保存→broker 呼び出し→broker_order_id を保存→OrderAccepted を保存）によるクラッシュ耐性設計。
    - OrderRejectedError / OrderSentPendingError の取り扱いを実装。
    - sync_order(): broker 側ステータスを照合して DB を更新する同期処理を実装（部分約定更新の差分反映含む）。
    - cancel_order(): 終端状態のキャンセル禁止チェック、broker API 呼び出し、Cancelled への遷移を実装。
  - ExecutionEngine (src/kabusys/execution/execution_engine.py)
    - Signal Queue Pull 型の発注フローを実装。シグナル処理フェーズ（8:50–9:10）と push ドレインフェーズ（9:10–15:30）を明確化。
    - Gate 1（シグナルレベル）、Gate 2（エグゼキューションレベル・レート制限）、Gate 3（ドローダウン監視）を導入し、リスク統制連携を実現。
    - kill_switch(): 全 active 注文のキャンセルとループ停止処理を実装。
    - WebSocket スレッドを用いた push 処理（broker が stream_push を持つ場合）を追加。push ペイロードから注文同期と Gate 3 評価を行う。
    - position_entries テーブルへの entry/sell 日付記録（発注成功時）を実装。
    - Reconciliation の起動時実行（オプション）や PID ファイルの扱いを実装。
  - 実行補助: broker_factory, order_repository, reconciler, risk_manager（これらは呼び出し/利用される形で統合）

- kabu station REST クライアント (src/kabusys/execution/kabu_client.py)
  - KabuStationClient を実装（同期 httpx クライアントを使用）。
  - トークン取得の遅延初期化と 401 リトライ処理を実装（_get_token, _request）。
  - HTTP エラー（タイムアウト・ネットワーク・429 レート制限・5xx）を明確な例外に変換。
  - WebSocket push 用の stream_push 連携を想定した設計（push 用ハンドラ登録を想定）。
  - kabu ステータスコード→内部ステータスマップを定義。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。

### 修正 (Fixed)
- なし（初回リリースのため該当なし）。

### 既知の注意点 (Notes)
- config/*.yaml のパース検証には PyYAML が必要。未インストール時は validate_config が YAML 内容の検証をスキップして警告を出します。
- 自動 .env ロードでは OS 環境変数が優先され、.env.local が .env を上書きします。テストや特別な状況では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化できます。
- ExecutionEngine の一部機能（broker の stream_push、Reconciler、RiskManager の詳細実装）は外部コンポーネントに依存します。実稼働時は各バックエンド（kabu station, DB 等）の準備が必要です。

---

(本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時はリリースの意図・既知の問題・互換性情報を補完してください。)