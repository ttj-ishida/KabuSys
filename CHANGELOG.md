# Changelog

すべての注目すべき変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用しています。

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-22

初回リリース。KabuSys のコア設定・起動・発注監視に関するモジュール群を追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを定義: `kabusys.__version__ = "0.1.0"`。

- 環境設定・読み込み
  - settings モジュール (`src/kabusys/config.py`) を追加:
    - .env 自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml` を起点）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパースはクォートやエスケープ、コメント処理に対応（`export KEY=...` 形式もサポート）。
    - Settings クラスを提供し、主要な設定値（J-Quants / kabu API / DB パス / LINE / PID/KillSwitch 関連 / スレッショルド / 環境判定 等）をプロパティ経由で取得可能。
    - 環境変数の必須チェック（`_require`）・列挙型の妥当性検証（`KABUSYS_ENV` / `LOG_LEVEL` / `PAPER_FILL_MODE` など）。
    - デフォルト値: DUCKDB/SQLite のファイルパスや KABU_API_BASE_URL 等。

- .env ウィザード CLI
  - `src/kabusys/config_setup.py` を追加:
    - 対話式ウィザードで `.env` を生成・更新。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
    - 既存 .env の読み込み、シークレット値のマスク表示、選択肢チェック、保存確認。
    - `.env` を上書きする `_write_env` を実装。リポジトリへのコミット禁止を明記するヘッダを出力。

- 設定検証 CLI
  - `src/kabusys/validate_config.py` を追加:
    - 起動前に .env と config/*.yaml の不備を検出する CLI（`--strict` オプションで警告を失敗扱いに）。
    - 必須/任意の環境変数リストを定義し未設定・プレースホルダ値の検出、KABUSYS_ENV や LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在確認を実装。
    - config/*.yaml の存在チェックと、PyYAML が利用可能な場合はパース検証（PyYAML が未インストールなら警告を出してスキップ）。
    - 本番環境 (KABUSYS_ENV=live) に対する追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険な設定等）を実装。

- 実行系スクリプト
  - 実行エンジン起動スクリプト `src/kabusys/run_execution.py` を追加:
    - ExecutionEngine を起動するためのセットアップ（ロギング、プロセス優先度設定、DB 接続）。
    - 環境が `paper_trading` の場合は paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - 停止フラグファイルの検出およびスレッドベースでのエンジン実行／停止ハンドリング。
  - 監視ループ起動スクリプト `src/kabusys/run_monitoring.py` を追加:
    - SystemMonitor のポーリングループ（デフォルト 60 秒、`MONITOR_POLL_INTERVAL` で上書き可）。
    - 監視用 DB 初期化（SQLite）と DuckDB 接続、停止フラグ検出、例外ハンドリングを実装。

- Execution コア
  - ExecutionEngine (`src/kabusys/execution/execution_engine.py`) を追加:
    - シグナル処理と push ドレインの二相構成（シグナル処理 8:50-9:10、ドレイン 9:10-15:30）。
    - Gate ベースのリスク検査（Gate1: シグナル、Gate2: 発注時の実行制御 / レート制御、Gate3: ドローダウン監視）。
    - kill_switch による全 active 注文キャンセル機構、PID / kill.flag の取り扱い、WebSocket push を別スレッドで受け取りキュー処理。
    - DuckDB を用いたシグナル読み込みと position_entries への記録（発注結果に応じ分岐）。
    - 監視DB（MonitoringDB）へ発注イベントのログを書き込むフック。

- Order 管理
  - OrderRecord (`src/kabusys/execution/order_record.py`):
    - 注文状態を Enum で定義し、許可された状態遷移テーブルを定義。
    - 不正遷移時に `InvalidStateTransitionError` を発生させる transition_to メソッド。
    - DB に触れない純粋ビジネスロジックとして設計。
  - OrderManager (`src/kabusys/execution/order_manager.py`):
    - create/send/sync/cancel の公開 API。
    - create: 同一 signal_id の active 注文重複検出（Repository 側のユニーク制約違反を DuplicateOrderError に変換）。
    - send_order: クラッシュ安全性を考慮した二相的な永続化シーケンスを実装（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 保存 → OrderAccepted へ遷移等）。OrderSent のまま残るケースを Reconciliation 対象とする設計。
    - sync_order: broker 側状態取得に基づく同期（部分約定の更新処理含む）。
    - cancel_order: キャンセル不可状態の判定と broker cancel 呼び出し、状態遷移処理。
    - OrderSentPendingError 等の特殊ケース（注文が番号を受け取ったが約定しない等）をハンドリング。

- kabu station クライアント
  - KabuStationClient (`src/kabusys/execution/kabu_client.py`) を追加:
    - httpx を用いた同期 REST クライアント。
    - トークン取得の遅延初期化と 401 リトライ処理（トークン再取得して 1 回再試行）。
    - レスポンス JSON パースのエラー変換、429 レート制限判定、500 以上のサーバエラー判定、タイムアウトやネットワーク例外の BrokerAPIError 変換。
    - push 用 WebSocket 受信（別スレッド）に対応するための stream_push フック想定。

- 監視 DB 初期化
  - monitoring_db 初期化ヘルパーを import して利用（run_monitoring/run_execution で使用）。

- ユーティリティ
  - ロギングセットアップとプロセス優先度設定ユーティリティを利用（run_* スクリプトで呼び出し）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known limitations / Notes
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行われます。未インストール時はパース検証をスキップして警告を出します。
- .env 自動読み込みはプロジェクトルートの検出に依存します。プロジェクトルートが見つからない場合は自動ロードをスキップします。
- Settings の一部プロパティ（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）は不正値で ValueError を送出します。これにより起動時に早期に不整合を検出できます。
- ExecutionEngine は kill.flag による起動拒否/自動クリアの挙動をサポート（`KILL_FLAG_CLEAR_ON_START`）。本番利用時は自動クリアを無効化することを推奨します（デフォルト: 0）。
- Paper trading は本番 DB と分離された SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用する設計。

### Security
- 機密情報（J-Quants トークン、kabu API パスワード等）は .env に保存される設計のため、`.env` をリポジトリにコミットしないよう README / ウィザードにも注意書きを出力しています。

---

今後のリリースでは、テストカバレッジの追加、async 化（httpx.AsyncClient を用いた非同期処理）、さらに細かな監視メトリクスや運用用コマンドの追加を予定しています。