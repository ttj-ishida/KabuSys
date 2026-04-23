# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム KabuSys の基礎的な構成・実行・発注・監視の実装を追加しました。

### Added
- パッケージメタ情報
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

- 設定管理
  - 環境変数 / .env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から検出して .env および .env.local を読み込む。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パースは引用符・エスケープ・コメントの扱いに対応。
    - _load_env_file の override / protected オプションで OS 環境変数の保護と上書き制御を実現。
  - Settings クラスを追加（src/kabusys/config.py）。環境変数から各種設定を取得する公開 API を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL, LINE_*、DB パス (DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH) 等
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）
    - KABUSYS_ENV / LOG_LEVEL の検証、is_live / is_paper / is_dev の補助プロパティ
    - kill_flag 関連や閾値（CPU/MEM/DISK/MEMORY）など監視用設定

- 対話式 .env 設定ウィザード
  - src/kabusys/config_setup.py を追加。
  - 対話的に .env を作成・更新するウィザード。秘密値のマスク表示、選択肢、デフォルト値、保存プレビューを提供。
  - CLI: python -m kabusys.config_setup（--env-file で出力先指定可能）。
  - .env ファイルテンプレート出力を実装（書式や注意書き含む）。

- 設定検証 CLI
  - src/kabusys/validate_config.py を追加。
  - .env と config/*.yaml の起動前検証を実行する CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・親ディレクトリ存在チェック、YAML ファイルの存在・パース検査（PyYAML 未導入時は警告）などを行う。
  - --strict オプションで警告を FAIL として exit(1) にする振る舞いを追加。
  - 検出結果を INFO/WARNING/ERROR に分類して出力。

- 実行 / 監視ランナー
  - run_execution: src/kabusys/run_execution.py を追加。
    - ExecutionEngine 起動用のエントリポイント。
    - paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と完全に分離。
    - プロセス優先度設定・PID ファイル管理・stop フラグによる制御を実装。
  - run_monitoring: src/kabusys/run_monitoring.py を追加。
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB の初期化処理を行う。

- 発注関連のコアロジック（Execution）
  - OrderRecord（状態マシン）: src/kabusys/execution/order_record.py
    - 注文状態 OrderState と許可遷移を定義し、状態遷移検証を行う OrderRecord を実装。
    - 不正遷移で InvalidStateTransitionError を送出。
  - OrderRepository（SQLite 経由の永続化）は既存想定（ファイル内参照）。
  - OrderManager: src/kabusys/execution/order_manager.py
    - create_order: signal_id の重複チェック（部分ユニーク制約と重複判定）と OrderCreated レコード生成。
    - send_order: "2 相永続化" の設計（OrderSent を先に永続化 → ブローカー呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）でクラッシュ耐性を高める。
      - OrderRejectedError / OrderSentPendingError の扱いを実装（pending は OrderSent のまま Broker order_id を保存して例外伝播）。
    - sync_order: broker の get_order_status を用いた状態同期。部分約定の進行は差分更新。
    - cancel_order: 終端状態の検出（キャンセル不可）と broker 呼び出し、Cancelled への遷移。
    - DuplicateOrderError を導入（同一 signal_id の active 注文存在時）。
    - 内部 status→OrderState マッピングとキャンセル不可能状態の定義を追加。
  - ExecutionEngine: src/kabusys/execution/execution_engine.py
    - Signal Queue Pull 型発注エンジンを実装。
    - シグナル処理フェーズ（例: 8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を想定したセッション管理。
    - Gate1（シグナルレベル）、Gate2（エグゼキューションレート制御／リトライ最大3回、回復不能な場合はドレインループ継続）、Gate3（ドローダウン監視）を実装。
    - kill_switch() により全 active 注文をキャンセルする安全停止機構を実装。
    - push_queue、_websocket_worker、_drain_push_queue により push 通知を非同期で処理。
    - 発注時の latency 計測や monitoring DB へのイベント記録フックを追加。
    - 発注後の position_entries 更新（DuckDB への書込み）と失敗時のフォールバックをサポート。
    - PID ファイル管理と KILL_FLAG_CLEAR_ON_START の挙動（存在時の起動拒否または自動クリア）を実装。

- ブローカークライアント（kabu station）
  - KabuStationClient: src/kabusys/execution/kabu_client.py を追加。
    - httpx を用いた同期 REST クライアント実装。
    - トークン取得を遅延初期化し、401 受信時にトークン再取得して 1 回リトライするロジックを実装。
    - レスポンス JSON パース時の例外を BrokerAPIError に変換。
    - 429 を RateLimitError として報告、サーバー 5xx を BrokerAPIError として扱う。
    - 注文状態コードから内部ステータス文字列へのマッピングを実装。
    - WebSocket（push）利用のため websocket を使用するための起動フローを想定（stream_push の有無を確認してスキップ可能）。

- 監視 DB 初期化フック
  - init_monitoring_db の呼び出しを run_* スクリプトで行い、監視テーブルの存在を保証（冪等的な初期化）。

- ユーティリティ
  - process_priority 設定や logging_setup フック呼び出しを run_* スクリプトで実施。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- .env を絶対に Git にコミットしない旨の警告をウィザードで出力。

### Notes / Migration
- 初回セットアップ手順:
  1. python -m kabusys.config_setup で .env を作成
  2. python -m kabusys.validate_config で設定を検証
  3. 実行: python -m kabusys.run_execution / python -m kabusys.run_monitoring 等
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を必ず設定してください。
- paper_trading モードでは監視・発注用 SQLite が本番データベースと分離されます（PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE を利用）。
- PyYAML をインストールしていない場合、config/*.yaml の内容検証はスキップされます（validate_config は警告を出力します）。
- KABUSYS_ENV に "live" を設定すると追加のチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告など）が実行されます。必要に応じて --strict モードで警告を失敗扱いにできます。

---

今後のリリースでは、ブローカー抽象の拡張、テスト向けフック、より詳細なモニタリング・メトリクスや UI/ダッシュボード連携等を予定しています。