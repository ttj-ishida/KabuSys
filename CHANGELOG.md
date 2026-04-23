CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 初回リリース: KabuSys のコア機能を実装。
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。
- 設定管理:
  - .env ファイルおよび環境変数を扱う設定モジュールを追加（src/kabusys/config.py）。
    - .git または pyproject.toml を基準にプロジェクトルートを探索して自動的に .env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
    - .env のパース実装: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなどをサポート。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB / 監視 / システム関連の設定値をプロパティ経由で取得。値の妥当性チェック（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行い、不正値の場合は明示的に例外を投げる。
- 設定ウィザード CLI:
  - .env の初期作成・更新を対話式で支援するウィザードを追加（src/kabusys/config_setup.py）。
    - 項目定義（実行環境、API トークン、DB パス、LINE トークン、ログレベル、Kill Flag 動作など）。
    - 既存 .env 読み込み、シークレットのマスク表示、選択肢の入力チェック、保存の確認。保存フォーマットに注意書きを付与。
- 設定検証 CLI:
  - 起動前に環境変数・config/*.yaml の不備を検出するツールを追加（src/kabusys/validate_config.py）。
    - 必須/任意環境変数チェック、プレースホルダ値検出、KABUSYS_ENV の妥当性確認、LOG_LEVEL 検証、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース検証（PyYAML 未インストール時はスキップ）。
    - 本番（live）環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告など）。
    - --strict オプションで警告を FAIL 扱いにする機能と exit コード制御を実装。
- 実行スクリプト:
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き、監視 DB（SQLite）と分析 DB（DuckDB）への接続、停止フラグ検出、例外発生時のログ出力および後続ポーリング継続。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する挙動。
  - 発注エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し本番 DB と分離。
    - プロセス優先度設定、PID/stop フラグの扱い、スレッドでのエンジン起動と停止処理。
- ExecutionEngine（発注エンジンコア）:
  - Signal Queue Pull 型の発注エンジンを実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理ウィンドウ（デフォルト 8:50-9:10）と WebSocket push ドレインループ（9:10-15:30）を実装。
    - kill.flag による起動拒否・キルスイッチ動作、PID ファイル管理、WS スレッド（broker が stream_push を提供する場合のみ起動）。
    - シグナル毎に Gate1（シグナルレベル） / Gate2（エグゼキューションレベル、レート制限・サーキットブレーカー） / Gate3（ドローダウン監視）を順に評価し、NG の場合はスキップまたは kill_switch 発動。
    - 発注後の position_entries への書き込み（buy/sell の扱い）と監視 DB への trade event ログ記録（監視 DB が提供されている場合）。
- 注文管理（OrderRecord / OrderManager / OrderRepository 連携）:
  - 注文状態モデルと遷移ロジックを実装（src/kabusys/execution/order_record.py）。
    - 明確な状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許可遷移テーブル、遷移時のメタデータ更新、InvalidStateTransitionError を定義。
  - 外向き API と永続化戦略（src/kabusys/execution/order_manager.py）。
    - create_order で重複 signal_id を検出して DuplicateOrderError を投げる（DB の部分ユニーク制約違反を適切に変換）。
    - send_order はクラッシュ安全性を考慮した 2 相永続化戦略を採用（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を先にコミット → OrderAccepted に遷移してコミット）。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order で broker 側の状態を取得してローカルを同期。部分約定の進行のみでフィールド更新する最適化。
    - cancel_order は終端状態のキャンセル不可判定と broker API 呼び出し、Cancelled への遷移を実行。
- ブローカークライアント実装:
  - kabu station REST API クライアントを追加（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期クライアント、トークン管理（遅延初期化・401 時の再取得とリトライ）、応答 JSON パースのエラーハンドリング、429 レート制限と >=500 のサーバエラー検出を実装。
    - WebSocket push（websocket ライブラリ経由）と同期的な stream_push 想定（ExecutionEngine の WS スレッドと連携可能）。
- その他ユーティリティ・統合点:
  - Process priority 設定、ログ設定呼び出し箇所を run_monitoring/run_execution に組み込み（優先度向上 & 初期ログ設定）。
  - DuckDB（分析）と SQLite（監視/履歴）を併用するアーキテクチャを採用。paper_trading 用に DB 分離機能あり。
  - Reconciler / RiskManager / BrokerClientFactory 等との連携ポイントを用意（実装は別モジュールで提供）。

Changed
- なし（初回リリースのため該当なし）。

Fixed
- なし（初回リリースのため該当なし）。

注記
- config/*.yaml のパース検証は PyYAML インストール有無に依存。PyYAML が無い場合は検証をスキップして警告を出す設計（環境により YAML 検証を有効化可能）。
- 実行にあたっては各種外部依存（httpx, websocket, duckdb, sqlite3 など）および適切な .env 設定が必要です。validate_config と config_setup を利用して初期設定と検証を行うことを推奨します。