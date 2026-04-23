# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの公開バージョンは __0.1.0__ です。

全般:
- 日付はリリース日を示します。  
- 重大な変更点や利用者が注意すべき挙動は該当箇所に明記しています。

## [0.1.0] - 2026-04-23

### 追加
- ベースパッケージの初期実装を追加。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。

- 環境/設定管理
  - Settings クラスを実装（`src/kabusys/config.py`）。
    - 環境変数から各種設定をプロパティで提供（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、PID/Kill flag パス、しきい値など）。
    - env 値（KABUSYS_ENV）や LOG_LEVEL、PAPER_FILL_MODE の値検証を実装し、不正値は ValueError を送出。
    - Paper Trading 用 SQLite パスを分離（`PAPER_TRADING_SQLITE_PATH` / `paper_sqlite_path`）。
    - 起動時に .env / .env.local を自動読み込みする仕組みを実装（OS 環境変数が優先され、`.env.local` は上書き可能）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサの強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープや、クォート内でのインラインコメントを正しく取り扱う。
    - クォートなしの場合は '#' の直前が空白/タブのときのみコメントとみなす（より現実的な .env コメント解釈）。
  - .env ファイル読み込み時に OS 環境変数を保護するための `protected` 機構を実装。

- 環境設定ウィザード CLI（`python -m kabusys.config_setup`）
  - `src/kabusys/config_setup.py` に対話式ウィザードを実装。
  - `.env` の既存値読み込み、シークレット値のマスク表示、選択肢の提示、確認プロンプト、ファイル書き出しをサポート。
  - デフォルト値や説明を含む複数の設定項目を用意（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定等）。
  - 書き出される `.env` に注意書きを付与（Git にコミットしない旨の警告）。

- 設定検証 CLI（`python -m kabusys.validate_config`）
  - `src/kabusys/validate_config.py` に設定検証ユーティリティを実装。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）を行う。
  - 出力を INFO/WARNING/ERROR に分類し、`--strict` オプションで警告を FAIL（exit code=1）として扱う。

- 実行用スクリプト
  - 実行エンジン起動スクリプト（`python -m kabusys.run_execution`）
    - `src/kabusys/run_execution.py` を追加。ExecutionEngine の起動手順を実装。
    - Paper Trading モード時は専用 SQLite（`paper_sqlite_path`）を使用して本番 DB と分離。
    - 停止フラグ確認、PID ファイル書き込み、プロセス優先度設定、DB 接続/クローズの流れを実装。
  - 監視ポーリングスクリプト（`python -m kabusys.run_monitoring`）
    - `src/kabusys/run_monitoring.py` を追加。SystemMonitor のポーリングループを実行。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を使用する挙動。

- 実行エンジン本体と周辺コンポーネント（execution パッケージ）
  - ExecutionEngine（`src/kabusys/execution/execution_engine.py`）を追加。
    - シグナル処理（8:50-9:10）と push drain（9:10-15:30）を含むセッション構成。
    - Reconciler による起動時リコンシリエーション実行（任意）。
    - kill.flag の検査と `KILL_FLAG_CLEAR_ON_START` による自動クリアの挙動。
    - PID ファイルの書き込み / 後始末。
    - WebSocket ワーカー（broker が stream_push を持つ場合）による push queue 採取とドレイン。
    - Signal 処理フロー: signals の読み出し（DuckDB）→ Gate 1（シグナルレベル）→ Gate 2（実行レベル、レート制限・サーキットブレーカー）→ 発注 → position_entries 更新 → 監視DB ログ記録。
    - Gate 3（ドローダウン監視）での kill_switch 発動。
    - `kill_switch()` により全 active 注文をキャンセルしてループ停止。

  - OrderRecord（`src/kabusys/execution/order_record.py`）
    - 注文状態を列挙する State Machine（OrderState）を実装。
    - 許容される状態遷移表を定義し、不正な遷移で `InvalidStateTransitionError` を投げる。
    - 状態遷移時に broker_order_id / filled_qty / avg_fill_price / error_message を安全に更新し、updated_at を UTC 現在時刻に更新。

  - OrderManager（`src/kabusys/execution/order_manager.py`）
    - signal_id の重複防止（同一 signal_id の active 注文が存在する場合は DuplicateOrderError）。
    - 発注時のクラッシュ耐性を意識した 2 相永続化パターン:
      1. DB 上で OrderCreated → OrderSent に遷移して commit（broker API 呼び出し前）
      2. broker へ送信、broker_order_id を先に永続化（state は Sent のまま）、その後 OrderAccepted へ遷移して commit
    - broker の拒否は Rejected として永続化、`OrderSentPendingError` を受けた場合は broker_order_id を保存して OrderSent のまま残し呼び出し元へ伝播（リコンシリエーション対象）。
    - `sync_order` により broker 側ステータス（open/partial/filled/cancelled/rejected）を内部状態へ同期待機。OrderSent→Filled/Partial の直接遷移は OrderAccepted を経由して扱う。
    - `cancel_order` は終端状態（Closed/Filled/Cancelled/Rejected）の場合にキャンセル不可とし、その他は broker API 呼び出しで取消→Cancelled。

  - Reconciler / RiskManager（インターフェースを利用する実装を組み合わせて動作する想定）との連携を想定した設計。

- kabu station クライアント（`src/kabusys/execution/kabu_client.py`）
  - `KabuStationClient` を実装（同期 httpx クライアント使用）。
    - トークン取得を遅延初期化し、401 発生時はトークン再取得して 1 回リトライする仕組みを実装。
    - レスポンス JSON パース失敗やネットワーク/タイムアウトエラーを `BrokerAPIError` 等に変換して上げる。
    - 429 を検出すると `RateLimitError` を送出。
    - kabu station の注文状態コードと内部状態のマッピングを保持。
    - WebSocket 系 push を処理するための stream_push を想定した設計（`stream_push` を持たない broker は WebSocket スレッドをスキップ）。

- 監視 DB 初期化ユーティリティ、SystemMonitor 等の呼び出しポイントを追加（実装は別モジュールに委譲）。

### 変更
- （初期リリースのため該当なし）

### 修正
- （初期リリースのため該当なし）

### 注意事項 / マイグレーション
- .env ファイルの自動読み込み
  - 起動時に自動でプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を読み込みます。CI やテストで読み込みを抑制するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - OS 環境変数は自動読み込み時に保護され、`.env.local` の上書きでも保護されます。

- 本番運用（KABUSYS_ENV=live）の留意点
  - `validate_config` を起動して警告・エラーを確認してください。`--strict` オプションで警告を FAIL として扱えます。
  - `KILL_FLAG_CLEAR_ON_START` が 1 に設定されていると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

- データベース分離
  - ペーパートレード (`KABUSYS_ENV=paper_trading`) 時は `paper_sqlite_path`（デフォルト: data/paper_trading.db）を使用して本番監視 DB と分離します。DuckDB は共有で使用されます（分析用途）。

### セキュリティ
- 機密情報（API トークン等）は .env に保存する設計です。.env は Git にコミットしないでください（config_setup のヘッダにも注意書きを記載）。

### 既知の制限 / TODO
- `PyYAML` が環境にインストールされていない場合、`validate_config` は YAML の内容検証をスキップします（警告）。
- `KabuStationClient` は同期 httpx ベースで実装。将来的に非同期化する場合は httpx.AsyncClient への差し替えを検討。
- 一部の外部モジュール（監視・Reconciler・RiskManager 等）の詳細実装はこのリリースの範囲外または別ファイルに委譲されているため、統合テストでの確認が必要です。

---------------------------------------
参考: 主な実行コマンド
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ポーリング起動: python -m kabusys.run_monitoring

（以上）