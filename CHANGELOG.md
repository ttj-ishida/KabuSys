# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。  

履歴
- 未リリース / Unreleased
- [0.1.0] - 2026-04-22

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-22

初回リリース。日本株自動売買システム KabuSys の基盤機能を実装しました。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ基本情報
  - パッケージ版番号を設定: `__version__ = "0.1.0"`。

- 環境変数／設定管理
  - Settings クラスを実装（kabusys.config）。
    - 環境変数から各種設定を取得するプロパティを提供（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン等）。
    - env/ログレベル値の検証（有効値チェック）。不正値は ValueError を投げる。
    - paper_trading 用の個別 SQLite パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE の検証をサポート。
    - 自動 .env 読み込み機構（プロジェクトルートを .git または pyproject.toml で検出）を実装。読み込み順は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - .env 読み込み時は OS 環境変数を保護（既存キーは protected として上書き抑止）。

  - .env パーサーの実装（引用符・エスケープ・export 形式・インラインコメント対応）。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - クォートなしの値でも # をインラインコメントとして扱う判定ロジックを実装。

- 環境設定ウィザード CLI
  - `kabusys.config_setup` モジュールを追加。
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 対話プロンプトは現在値やデフォルトを表示、シークレット項目はマスク表示。
    - 保存前の確認と .env ファイル書き込み処理を実装（.env を Git 管理しないよう注意書き付き）。
    - デフォルトで生成される設定項目一覧（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を備える。

- 設定検証 CLI
  - `kabusys.validate_config` モジュールを追加。
    - .env と config/*.yaml を起動前に検証。必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL 検証、DB パスの親ディレクトリ存在確認、YAML のパース検証（PyYAML がある場合）。
    - config/*.yaml が見つからない場合は警告。PyYAML 未インストール時は内容検証をスキップして警告を出す。
    - `--strict` オプションにより警告も失敗（exit 1）扱いにできる。
    - 出力に INFO / WARNING / ERROR を表示。

- 実行スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動する本番用スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）の検出、プロセス優先度設定を実装。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` により監視間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視専用挙動）。

- Execution エンジン本体
  - `ExecutionEngine`（kabusys.execution.execution_engine）を実装。
    - シグナル処理（8:50–9:10）および WebSocket push ドレイン（9:10–15:30）のセッション制御。
    - kill.flag の検査と起動時の動作（KILL_FLAG_CLEAR_ON_START による自動クリアの選択）を実装。
    - PID ファイルの書き出し/削除、WebSocket スレッド（push の受け取り）を実装。
    - シグナル読み込みは DuckDB から（signals と portfolio_targets を JOIN）。
    - position_entries の更新（BUY のエントリ登録、SELL のクローズ更新）を実装。
    - 発注に関する監視 DB ログ出力（latency, state 等）を統合可能。

- 注文管理（Order State Machine）
  - `OrderRecord`（kabusys.execution.order_record）
    - 注文状態を enum で定義（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可遷移テーブルと遷移検証ロジック。InvalidStateTransitionError を定義。
    - 状態遷移時に updated_at を UTC で自動更新。オプションフィールド（broker_order_id, filled_qty, avg_fill_price, error_message）更新対応。
  - `OrderManager`（kabusys.execution.order_manager）
    - 信号に基づく注文作成（create_order）で client_order_id を UUID4 で付与。
    - 重複注文検出（同一 signal_id の active 注文）で DuplicateOrderError を発生。
    - send_order におけるクラッシュ耐性を考慮した二相的永続化フローを実装:
      - OrderCreated → OrderSent を先に DB に永続化してから broker API を呼び出す。
      - broker_order_id を先に永続化してから OrderAccepted に遷移して永続化（クラッシュ後の復旧を容易にする）。
      - OrderRejected は Rejected に遷移して保存。
      - OrderSentPendingError（注文番号は発行されたが約定無し等）は broker_order_id を永続化して OrderSent のまま残し、例外を上位へ伝播（Reconciliation 対象）。
    - sync_order により broker の状態を照合して DB を更新。broker が返す状態に基づく遷移と、同一状態でも filled_qty / avg_price の更新に対応。
    - cancel_order はキャンセル不可能な状態（Closed / Filled / Cancelled / Rejected）を弾き、可能ならブローカーに cancel を送り Cancelled に遷移。

- ブローカークライアント（kabu station）
  - `KabuStationClient`（kabusys.execution.kabu_client）
    - kabuステーション REST API 向けクライアントを httpx（同期）で実装。
    - トークン取得（/token）とトークン遅延初期化、401 時の自動再取得・リトライを実装。
    - レスポンス JSON パース失敗やタイムアウト／ネットワークエラーを BrokerAPIError に変換して扱う。
    - 429 を RateLimitError として扱う。
    - kabu の注文状態コードを内部ステータス（open/partial/filled/cancelled/rejected）にマッピング。
    - WebSocket push（stream_push）を通じた push 受信に対応する設計（broker に stream_push がなければスキップ）。

- リスク管理・再整合（Reconciliation）などの統合点
  - ExecutionEngine が RiskManager / Reconciler / OrderRepository / OrderManager / BrokerClientFactory 等と連携して発注フローを構成。
  - Gate1（シグナルレベル）、Gate2（実行レート制御／サーキットブレーカー）、Gate3（ドローダウン監視）を通す設計。Gate2 のレート制限はリトライを行い、CB 発生時はシグナルループを停止。
  - kill_switch 発動時の挙動: 全 active 注文をキャンセルし、ループを停止。

- 監視関連
  - Monitoring 初期化関数 init_monitoring_db を利用して監視用テーブルを保証。
  - run_monitoring は SQLite/duckdb 接続を開き SystemMonitor を周期実行。

- ユーティリティ
  - process_priority 設定、logging セットアップの呼び出しポイントを実装（run_execution / run_monitoring）。
  - 各デフォルトパス（data/*.db, pid/flag ファイルパス）を一貫して使用。

### 変更 (Changed)
- 初回リリースのため履歴なし。

### 修正 (Fixed)
- 初回リリースのため履歴なし。

### 注意事項 / Migration
- .env ファイルは生成後に絶対に Git にコミットしないこと（config_setup の出力にも注記）。
- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml で検出します。配布環境やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化してください。
- Settings のプロパティは不正な値で ValueError を投げます。起動前に `python -m kabusys.validate_config` で検証することを推奨します。
- 本番運用時は KABUSYS_ENV=live の場合に特に注意：validate で live を検知すると警告が出ます。LINE 通知の設定や KILL_FLAG_CLEAR_ON_START の値を確認してください。

---

この CHANGELOG はコードベースの現状から推測して作成しています。実装の追加・修正に伴い適宜更新してください。