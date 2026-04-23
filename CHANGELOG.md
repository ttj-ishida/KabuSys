CHANGELOG
=========

すべての重要な変更をここに記載します。フォーマットは "Keep a Changelog" に準拠しています。

注: バージョンや日付はソースコードの状態から推測して記載しています。

Unreleased
----------

追加（Added）
- 設定検証 CLI を追加
  - python -m kabusys.validate_config により .env と config/*.yaml の存在・基本構文を起動前に検証可能。
  - --strict オプションで警告も失敗扱いにできる。
  - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在確認、PyYAML が無い場合のスキップなどを実装。

- 対話式設定ウィザードを追加
  - python -m kabusys.config_setup で .env の初期作成・更新を対話式に実行可能。
  - シークレット入力のマスク、選択肢・デフォルト提示、既存 .env の読み取りと再利用、保存時のテンプレート出力に対応。

- 設定管理モジュールを追加
  - kabusys.config: .env ファイル（.env / .env.local）をプロジェクトルート（.git / pyproject.toml を探索）から自動読み込み（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD あり）。
  - .env のパースは export 対応、クォート内バックスラッシュエスケープ、コメントの扱い（クォートなしでの # 扱い）など堅牢に実装。
  - Settings クラスを提供し、型付きプロパティ経由で設定値を取得。必須値は未設定時に ValueError を送出。

- 実行スクリプトを追加 / 改良
  - run_execution: ExecutionEngine を起動するエントリポイントを実装。
    - paper_trading 環境では専用の paper_trading DB を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検知、停止時の整序処理を実装。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。

- 発注周りコアロジックの追加
  - OrderRecord: 注文状態列挙（OrderState）と状態遷移の検証ロジックを実装（不正遷移で例外）。
  - OrderManager: DB（OrderRepository）と OrderRecord を組み合わせた外向け API を実装。
    - create_order: 同一 signal_id の重複防止（部分ユニークインデックス / アプリレベル検査）。
    - send_order: 二相永続化の設計（OrderSent を DB に残す→broker 呼び出し→broker_order_id を保存→OrderAccepted に遷移）によりクラッシュ耐性を確保。
    - sync_order: broker 側ステータス取得による同期ロジック（部分約定の更新含む）。
    - cancel_order: キャンセル不可状態の判定・実行。
    - OrderSentPendingError を考慮した処理（注文番号は得られたが約定しないケースを pending として扱う）。
  - ExecutionEngine: 信号プル型発注ループを実装。
    - シグナル処理（8:50–9:10）と push ドレイン（9:10–15:30）を分離。
    - Gate1/2/3 による多段リスクチェック（signal レベル、実行レベル（レート制限・サーキットブレーカー）、ドローダウン監視）。
    - kill_switch により全 active 注文をキャンセルしループ停止。
    - WebSocket push の受信・同期・Gate3 評価を行うプッシュ処理。
    - 発注成功/失敗時に監視 DB（MonitoringDB）があればトレードイベントを記録。

- ブローカークライアントの実装（kabu station REST API）
  - KabuStationClient を実装（httpx 使用、同期クライアント）。
  - トークンの遅延初期化と 401 時の再取得・リトライ処理を実装。
  - レスポンス JSON パースエラー・タイムアウト・ネットワークエラーを BrokerAPIError 等に変換。
  - 429 応答は RateLimitError として扱う。

変更（Changed）
- DB / ファイル取り扱いに関する方針を明確化
  - monitoring は環境にかかわらず本番 sqlite_path を用いる（監視は本番観点で一貫性を担保）。
  - paper_trading は paper_sqlite_path により本番 DB と分離。

- 環境変数読み込み順序
  - OS 環境 > .env.local > .env の優先順で読み込む実装に変更（._load_env_file の override/ protected により OS 変数は保護）。

修正（Fixed）
- .env パーサーの堅牢化
  - export キーワード対応、クォート内エスケープ処理、コメント切り取りの改善により複雑な .env を正しく解釈。

セキュリティ（Security）
- .env の生成テンプレートに対し「絶対に Git にコミットしないこと」を注記。

互換性（Compatibility）
- Settings のプロパティは ValueError を投げることで不正値を早期に検出する設計。既存コードは例外ハンドリングに注意が必要。

[0.1.0] - 2026-04-23
--------------------
初回リリース（推測） — 基本機能の実装一覧

追加（Added）
- パッケージ初期構成を追加:
  - kabusys パッケージ本体 (__version__ = 0.1.0)
  - データ/戦略/エグゼキューション/監視関連のモジュール群（モジュール一覧は __all__ に記載）
- 設定周り:
  - .env 自動読み込み（プロジェクトルート探索）
  - Settings クラスによる型付きアクセス
- ユーティリティ / 起動スクリプト:
  - 環境設定ウィザード (config_setup)
  - 設定検証ツール (validate_config)
  - 実行エンジン起動スクリプト (run_execution)
  - 監視起動スクリプト (run_monitoring)
- 発注エンジン:
  - ExecutionEngine（シグナルプル + WebSocket ドレイン構造）
  - OrderRecord（状態遷移モデル）
  - OrderManager（発注フロー、再送・同期・キャンセル等）
  - Broker クライアント（KabuStationClient）と抽象 API 定義
  - Reconciler / MonitoringDB フック（リコンシリエーション・監視連携の想定）
- リスク管理:
  - RiskManager / Gate1-3 による信号・実行・ドローダウンチェック（インターフェースを利用）

変更（Changed）
- 発注フローの永続化戦略を設計（OrderSent を DB に残すことでクラッシュ後の復旧を容易にする）。
- paper_trading 環境の DB 分離。

修正（Fixed）
- 各種例外ケース（HTTP 401/429/タイムアウト等）を BrokerAPIError / RateLimitError 等へマッピング。
- .env のパースに関するバグ修正（引用符内エスケープ、コメント認識）。

脚注
- 本 CHANGELOG はソースコードを解析して推測に基づき作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。