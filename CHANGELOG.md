# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog 準拠の形式を採用しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のパッケージバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

初回公開リリース。日本株自動売買フレームワーク「KabuSys」の基幹機能を実装しました。

### 追加 (Added)
- 基本設定・起動補助ツール
  - config モジュールを追加し、.env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、配布後も動作するように実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
    - .env のパースは引用符、エスケープ、コメント（インライン含む）を考慮した堅牢な実装。
  - config_setup CLI（python -m kabusys.config_setup）を追加。
    - 対話式ウィザードで .env の初期作成・更新が可能。
    - J-Quants / kabu API など主要設定項目を網羅するプロンプトとデフォルト値、説明を提供。
    - 生成される .env に注意書きを追加（Git にコミットしないよう注意喚起）。
  - validate_config CLI（python -m kabusys.validate_config）を追加。
    - 必須環境変数の存在確認、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・YAML パース検証（PyYAML がインストールされている場合）などの事前点検を行う。
    - --strict オプションで警告も失敗扱い（exit 1）にできる。

- 実行系スクリプト
  - run_execution（python -m kabusys.run_execution）を追加。ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用 SQLite を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出に対応。
  - run_monitoring（python -m kabusys.run_monitoring）を追加。SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグを検出して安全に終了。

- 実行エンジン/発注ロジック
  - ExecutionEngine を実装
    - シグナル処理（デフォルト 8:50–9:10）と WebSocket push ドレイン（9:10–15:30）を想定したセッションモデル。
    - Gate 1（シグナルレベル）・Gate 2（エグゼキューションレベル／レート制限）・Gate 3（ドローダウン監視）の 3 段階リスクチェックを導入。Gate 2 のレート制限はリトライロジックを実装。
    - kill_switch による全 active 注文のキャンセル機能と外部停止フラグとの連携。
    - WebSocket push を受け取るワーカースレッド（broker が stream_push を持つ場合）と内部キューへの取り込み実装。
    - DuckDB からシグナルを読み込むロジック（signals と portfolio_targets の JOIN）。

  - OrderRecord（状態遷移モデル）を実装
    - 発注状態を列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）し、許可される遷移テーブルを定義。
    - 不正な遷移時に InvalidStateTransitionError を投出。

  - OrderManager（外向き API）を実装
    - create_order: 同一 signal_id の重複アクティブ注文検出（DuplicateOrderError）。
    - send_order: クラッシュ耐性を考慮した 2 相永続化戦略を採用。
      - OrderSent に永続化してから broker API 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移 といった流れ。
      - OrderRejectedError は Rejected に遷移して保存。
      - OrderSentPendingError（注文番号は発行されたが約定しないケース）は broker_order_id を保存した上で例外を伝搬（Reconciliation 対象）。
    - sync_order: broker 側の状態を取得してローカル状態に同期（部分約定の進行による数量／平均価格更新も考慮）。
    - cancel_order: キャンセル不可状態は InvalidStateTransitionError を返し、可能な場合は broker API にキャンセルを依頼して Cancelled に遷移。

  - Reconciler / RiskManager / OrderRepository 等（実装を前提とした統合）に対応する依存関係を組み合わせる設計。

- ブローカー API クライアント（kabu station 向け）
  - KabuStationClient を実装（同期 httpx と websocket）。
    - トークン取得の遅延初期化と 401 時の自動再取得・1 回リトライ処理。
    - HTTP ステータス 429 を RateLimitError として判別、500 系を BrokerAPIError として扱う。
    - send_order: API へのペイロード整形（成行は Price=0 を強制）と発注拒否時の OrderRejectedError ハンドリング。
    - cancel_order / get_order_status の基本的な実装（orders の全件取得 → ID フィルタ方式での照会、kabu station の挙動を考慮）。

- 監視（Monitoring）
  - 監視 DB（SQLite）初期化関数を用意し、run_monitoring / run_execution 起動時に冪等にテーブルを保証してから利用する設計。
  - ExecutionEngine の発注フローで監視 DB へトレードイベント（Sent 等）のログを出力するフックを追加可能。

- 設定項目・デフォルト
  - 環境変数のセット（必須/任意/デフォルト）と説明を config_setup の項目定義にて明示。
  - Settings クラスでプロパティアクセスを提供（必須変数取得時に未設定なら ValueError を投げる _require を採用）。
  - PAPER_FILL_MODE 等の値検証（有効値チェック）を実装。

### 変更 (Changed)
- なし（初回公開）

### 修正 (Fixed)
- なし（初回公開）

### 注記 / 制限事項 (Notes)
- config/*.yaml の内容検証は PyYAML がインストールされている場合にのみ有効。未インストール時は検証がスキップされ、警告が出ます。
- KabuStationClient の get_order_status 実装は外部 API の挙動（全件取得してフィルタする）を想定しているため、kabu station 側の仕様変更があると調整が必要です。
- 一部のモジュール（Reconciler 等）は外部コンポーネントに依存した設計になっており、実運用時は BrokerClientFactory やストレージなどの実装を提供する必要があります。

### セキュリティ (Security)
- 重要なトークン/パスワードは .env に記述する想定で、config_setup は .env を生成する際に「Git にコミットしないこと」を強調しています。今後、シークレット管理（Vault、KMS など）連携を検討してください。

---

今後の予定（例）
- async 対応の HTTP client（httpx.AsyncClient）や WebSocket の改善
- Reconciler の堅牢化と起動時の自動リカバリ強化
- より細かな監視メトリクスの拡充と Prometheus/exporter 連携

---