# CHANGELOG

すべての重要な変更は Keep a Changelog 準拠で記載します。  

リンクや互換性ポリシーの詳細はリポジトリの README を参照してください。

## [0.1.0] - 2026-04-23

### 追加 (Added)
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- 環境設定 / 管理
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検索）。
  - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱い）。
  - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - 設定ウィザード CLI を追加（python -m kabusys.config_setup）。対話式で .env を作成/更新可能。`--env-file` でファイル指定可。
  - Settings クラスを導入し、環境変数を型安全に取得するプロパティ（トークン・DBパス・PIDパス・閾値など）を提供。
  - `PAPER_FILL_MODE` の検証を実装（有効値: instant/partial/never/reject）。

- 設定検証
  - validate_config CLI を追加（python -m kabusys.validate_config）。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - `--strict` オプションにより警告も失敗扱い（exit code=1）にできる。

- 実行エントリ / プロセス管理
  - run_execution スクリプトを追加（python -m kabusys.run_execution）。ExecutionEngine を起動し、paper_trading 時は専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用。
  - run_monitoring スクリプトを追加（python -m kabusys.run_monitoring）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用。
  - PID / stop フラグに基づく起動・停止制御、停止フラグ検出での安全な終了を実装。
  - プロセス優先度設定フック（set_process_priority）およびロギング初期化（setup_logging）を導入。

- 発注エンジン / 注文管理
  - ExecutionEngine 実装（シグナル取得→Gate1/2 による検査→発注、WebSocket プッシュのドレイン、Gate3 のドローダウン監視）。
  - OrderRecord: 注文状態を表す State Machine（定義済み状態と許容遷移、transition_to による遷移検証）。
  - OrderManager: create/send/sync/cancel の外向き API を実装。DuplicateOrder チェック、クラッシュ安全性を考慮した 2 相永続化パターンを採用。
  - Reconciler（起動時の照合）呼び出しの統合（ExecutionEngine 側）。
  - ブローカークライアント抽象（BrokerAPIProtocol）に基づく BrokerClientFactory を利用。

- ブローカー接続
  - KabuStationClient を実装（httpx 同期クライアント）。トークンの遅延取得・自動再取得、401 リトライ、429 / 5xx のエラー変換を実装。WebSocket プッシュ受信（stream_push）との連携を想定。

- 監視 / DB
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を利用した監視データ収集の土台を追加。
  - ExecutionEngine / OrderManager と連携して監視イベント（例: Sent）を監視 DB に記録する仕組み（監視 DB が指定された場合）。

### 変更 (Changed)
- .env 読み込み挙動:
  - 読み込み優先順位を OS 環境 > .env.local > .env に設定。OS 環境を protected として .env.local の override から保護。
  - 読み込み失敗時は警告を出力して処理を継続する。
- DB パスの扱い:
  - デフォルトの DUCKDB/SQLite のパスを明示（data/kabusys.duckdb, data/monitoring.db）。
  - run_monitoring は常に本番 sqlite_path を使用（監視は本番データを扱う設計）。
- ExecutionEngine の挙動:
  - 起動時に kill.flag を検査。`KILL_FLAG_CLEAR_ON_START=1` のときは kill.flag を自動クリアして起動可能（デフォルトは拒否）。
  - セッションタイミング（signal_send_start/end, market_close）に基づく処理ループ実装。
  - WebSocket push による同期処理と Gate3 のドローダウン判定を明確化。
- OrderManager の挙動:
  - send_order の手順を明文化し、ブローカから注文番号取得→DB 保存→状態遷移の順で永続化（クラッシュ耐性向上）。
  - OrderSentPendingError を特別扱い（order_id を永続化して OrderSent のまま例外を伝搬）し、リコンシリエーションの回復性を向上。

### 修正 (Fixed)
- 並行・クラッシュ耐性
  - send_order の二相永続化により、途中クラッシュ時でも broker_order_id などから復旧できるように改善（Reconciliation 対応）。
- 重複注文検出
  - create_order で DB の部分ユニーク制約違反を DuplicateOrderError に変換し、重複検出のロジック欠落による異常を修正。
- .env パーサ
  - クォート内のバックスラッシュエスケープとインラインコメントの処理を改善。export プレフィックスに対応。

### 互換性に関する注意 (Compatibility)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD が必須。これらが未設定の場合、Settings プロパティや validate_config によりエラー/警告が発生します。
- 新しい/変更された環境変数:
  - KABUSYS_ENV: 有効値は development / paper_trading / live（設定値の検証あり）。
  - LOG_LEVEL: 有効値は DEBUG / INFO / WARNING / ERROR / CRITICAL（検証あり）。
  - KILL_FLAG_CLEAR_ON_START: 起動時の kill.flag 自動クリア（0/1）。本番では 0 を推奨。
  - PAPER_TRADING_SQLITE_PATH: paper_trading モード用の SQLite（デフォルト: data/paper_trading.db）。
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する（テスト用途）。
- PyYAML:
  - validate_config は PyYAML がインストールされていない場合、YAML 内容検証をスキップして警告を出します。YAML のパース検証を行うには PyYAML をインストールしてください。

### 既知の制限 / 注意点 (Known issues / Notes)
- KabuStationClient は同期 httpx.Client を使用しており、将来的な async 化は httpx.AsyncClient へ切り替えることで対応可能。
- 一部 API/クラス（BrokerAPIProtocol, Reconciler 等）は外部実装（ファクトリや依存注入）に依存しており、環境に応じた実装を提供する必要があります。
- config/*.yaml の雛形は scripts/generate_config.py で生成する想定。存在しない場合は validate_config で警告を出します。

### セキュリティ (Security)
- .env ファイルは絶対に Git にコミットしないよう README / ウィザード内ドキュメントで注意喚起を追加。

---

今後のリリースでは、ドキュメント強化、テストカバレッジの拡充、非同期クライアント対応、より細かな監視／メトリクス機能の追加を予定しています。