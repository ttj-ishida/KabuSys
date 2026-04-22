Keep a Changelog 準拠の CHANGELOG（日本語）
======================================

変更履歴は Keep a Changelog の形式に従っています。  
各リリースの要点（追加・変更・修正・注記）を日本語でまとめています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-22
-------------------

Added
- パッケージ初版リリース (バージョン: 0.1.0)
- 環境・設定管理
  - .env ファイル読み込みロジックを実装（src/kabusys/config.py）
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）
    - .env / .env.local の自動ロード（OS 環境変数を保護）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応
    - 行パーサーは export プレフィックス、クォート（' / "）およびエスケープ、インラインコメントの扱いに対応
  - Settings クラスを追加（環境変数から安全に値を取得・検証）
    - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の取得
    - パス（DUCKDB_PATH, SQLITE_PATH 等）を Path として露出
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）
    - KABUSYS_ENV / LOG_LEVEL の妥当性検証
    - kill_flag 関連・閾値設定（CPU/MEM/DISK）などの取得

- 設定ウィザード CLI（src/kabusys/config_setup.py）
  - 対話式で .env を作成・更新するウィザードを実装
  - デフォルト値、選択肢、シークレットマスク表示、既存 .env 読み込みをサポート
  - 保存時にテンプレートヘッダと共に .env を書き出す（.env を Git に入れない旨を明記）

- 設定検証 CLI（src/kabusys/validate_config.py）
  - .env と config/*.yaml の起動前チェックを実装
  - 必須環境変数未設定はエラー、プレースホルダ値を検出して警告
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック
  - DB パスの親ディレクトリ存在チェック（存在しない場合は警告）
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告
  - KABUSYS_ENV=live の場合に本番用追加チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定など）
  - --strict オプションで警告も FAIL 扱い（exit 1）

- 実行エントリスクリプト
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine を起動するエントリポイント
    - paper_trading 時は paper 専用 SQLite を使用して本番 DB と分離
    - PID ファイル管理、stop フラグ検出、プロセス優先度設定を実装
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用

- 発注・実行基盤（Execution）
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナル読み取り→Gate 1/2（リスクチェック）→発注フロー（9:10 までの処理）→push ドレイン（WebSocket）ループ
    - kill.flag の検出と起動時の挙動（KILL_FLAG_CLEAR_ON_START に応じたクリア動作）
    - PID ファイルの書き込みと削除、WebSocket スレッド（broker が stream_push を持つ場合のみ）
    - position_entries の書き込み（-buy はエントリー記録、sell は売り確定で更新）
    - 監視DB への発注イベント記録（latentcy_ms など）
  - OrderManager（src/kabusys/execution/order_manager.py）
    - create_order: signal_id 単位での冪等チェック、UUID の client_order_id 採番、DB 保存
    - send_order: 送信前に OrderSent を永続化 → broker 呼び出し → broker_order_id を先にコミット（2相永続化）→ OrderAccepted へ遷移
      - OrderRejectedError の扱い、OrderSentPendingError の扱い（order_id を保存して OrderSent のまま復帰）を明確化
      - クラッシュ耐性を考慮した設計（Reconciliation を想定）
    - sync_order: broker 側ステータス取得と状態同期（部分約定更新の取り扱い、OrderSent→Filled 等の遷移補助）
    - cancel_order: 終端状態チェック、broker API 呼び出し、Cancelled への遷移
    - DuplicateOrderError / InvalidStateTransitionError の導入
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 状態遷移を管理する純粋ドメインモデル（DB には触れない）
    - OrderState 列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）
    - 許可される状態遷移テーブルを明示
    - transition_to による検証と更新（updated_at 自動更新、オプションフィールド更新）
  - Reconciler / BrokerFactory 等の連携点（エンジン起動時に組み立てて使用する設計）
  - RiskManager の利用（Gate 1/2/3）とデフォルト RiskConfig（Execution 起動時に設定例あり）

- ブローカークライアント実装
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx を使った同期 REST 実装
    - トークン取得の遅延初期化と 401 に対する再取得リトライ実装
    - レスポンスの JSON パース失敗 → BrokerAPIError 変換
    - 429 → RateLimitError を投げる
    - kabu ステーションの状態コードを内部ステータス（open/partial/filled/cancelled/rejected）にマッピング

- 監視関連
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を使用することで DB の準備を保証
  - SystemMonitor 用ポーリングループ（run_monitoring）を提供

- ユーティリティ
  - ロギング・プロセス優先度設定ユーティリティを利用（起動時に high 優先度へ設定）
  - stop_requested.flag / kill.flag / PID 管理の取り扱いを標準化

Changed
- 初版につき該当なし

Fixed
- 初版につき該当なし

Security, Notes & Migration
- .env は絶対にリポジトリにコミットしないこと（config_setup でもヘッダにその旨を記載）
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を確認すること。未設定時はアラートが届きません。
- KILL_FLAG_CLEAR_ON_START を本番で 1 にすることは危険（自動で kill flag がクリアされ、Kill Switch 保護が失われる）。本番は 0 を推奨。
- validate_config の --strict を CI に使うと、警告も失敗扱いにできるためデプロイ前チェックに利用可能。
- YAML の内容検証は PyYAML が必要。未インストール時は検証をスキップして警告のみ出力する。
- Paper Trading モードは本番 DB と完全に分離される（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）。実際の運用での誤接続に注意。

依存関係（主なもの）
- Python 標準ライブラリ: os, pathlib, sqlite3, threading, datetime など
- 必須外部: duckdb, httpx, websocket（利用する機能による）
- 任意: PyYAML（config/*.yaml の中身検証時に必要）

破壊的変更 (BREAKING CHANGES)
- 初版リリースのため該当なし

Authors
- KabuSys 開発チーム（コードヘッダ・モジュールに基づく推定）

=====

注: 上記はリポジトリ内のソースコードから推測してまとめた変更点です。実際のリリースノートを作成する際は、コミット履歴やリリース作業記録、テスト結果等を合わせて確認してください。