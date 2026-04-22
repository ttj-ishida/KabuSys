CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はこのリリースノート作成日です。

Unreleased
----------
（なし）

0.1.0 - 2026-04-22
-----------------

Added
- パッケージ初期リリース。
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 設定・環境変数関連
  - src/kabusys/config.py
    - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出（.git または pyproject.toml）を行い、.env / .env.local を読み込む（OS 環境変数を保護して上書き制御）。
    - .env のパース機能を強化:
      - export KEY=val 形式のサポート。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
      - インラインコメントの扱い（クォート有無で挙動を区別）。
    - _require() で必須環境変数未設定時に ValueError を送出する仕組み。
    - Settings クラスを導入し、アプリケーション内で型付きプロパティ経由で設定を参照可能に。
      - J-Quants / kabu API / LINE / DB パス / PID / kill flag / リソース閾値など多数のプロパティを提供。
      - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL の入力検証を実装（不正値で ValueError を送出）。
    - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。

  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 入力項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）。
    - シークレット値のマスク表示、選択肢チェック、既存 .env 読み込みサポート。
    - .env ファイルのフォーマット書き出し機能を実装（.env を絶対に Git にコミットしない旨をヘッダに記載）。

  - src/kabusys/validate_config.py
    - 起動前検証 CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証を実施。
    - KABUSYS_ENV=live の追加安全チェック（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を失敗扱いにして exit(1) を返すモードを実装。
    - 出力に INFO/WARNING/ERROR を使った見やすいログ表示。

- 実行スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイントスクリプトを追加。
    - paper_trading 環境では paper_trading 用 SQLite を使い、本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（stop_requested.flag）検出ロジックを実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する仕様。

- 発注 / 実行エンジン
  - src/kabusys/execution/execution_engine.py
    - Signal Queue Pull 型の ExecutionEngine を実装（シグナル処理窓口と WebSocket push ドレインを含む）。
    - セッションスケジュール（signal_send_start/end, market_close）でシグナル処理（8:50-9:10）→ push ドレイン（9:10-15:30）を実行。
    - kill.flag の存在チェック、KILL_FLAG_CLEAR_ON_START による起動時の挙動制御、PID ファイル書き込み/削除をサポート。
    - WebSocket スレッド経由で受信した push ペイロードをキューに入れ、_drain_push_queue で処理。
    - Gate 1/2/3 の概念を導入し、RiskManager による信号・実行・資産監視（ドローダウン）チェックで kill_switch 発動を行う。
    - 発注時のレート制限リトライ、pending（OrderSentPendingError）ハンドリング、監視DBへのトレードイベント記録の統合ポイントを実装。
    - position_entries テーブルへの約定予定日の追記（fill_date: 翌営業日）を実装。

  - src/kabusys/execution/order_record.py
    - OrderRecord データモデルを導入（状態遷移ロジックを含む純粋なビジネスロジック）。
    - OrderState 列挙と許可トランジション (_ALLOWED_TRANSITIONS) を実装。
    - transition_to() による遷移検証（不正遷移は InvalidStateTransitionError）とタイムスタンプ更新、関連フィールド更新を実装。

  - src/kabusys/execution/order_manager.py
    - OrderRecord と OrderRepository を組み合わせた外向き API を実装（create_order, send_order, sync_order, cancel_order）。
    - 同一 signal_id の active 注文重複検出と DuplicateOrderError を導入。
    - send_order のクラッシュ耐性を考慮した 2 相的永続化戦略を実装（OrderSent 永続化→ broker 呼び出し→ broker_order_id 永続化→ OrderAccepted 更新）。
    - OrderRejectedError / OrderSentPendingError の取り扱いを実装。
    - sync_order で broker 側の状態照合・同期を行い、部分約定時のフィールド更新処理をサポート。
    - cancel_order は現在状態を確認し、キャンセル不可状態では InvalidStateTransitionError を送出。broker_order_id があれば broker 側の cancel API を呼ぶ。

  - src/kabusys/execution/kabu_client.py
    - kabu station REST API クライアント実装（同期 httpx ベース）。
    - トークン管理（遅延取得、401 時の再取得とリトライ）を実装。
    - レスポンス JSON パースでのエラーを BrokerAPIError に変換。
    - 429 レスポンスを RateLimitError として扱う、500 系をサーバーエラーとして扱うなどの HTTP ステータス処理。
    - 将来の非同期対応を見据えた設計（httpx.AsyncClient への置換で対応可能）。
    - WebSocket push（stream_push）を利用した通知受信を想定した設計。

- 監視 / DB 初期化
  - src/kabusys/monitoring/*（実装ファイルを参照）
    - 監視用 SQLite 初期化関数 init_monitoring_db を提供（run_monitoring / run_execution で利用）。
    - 監視DBへの書き込みを行う MonitoringDB との統合点を提供。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py, process_priority.py（実行スクリプトから利用）
    - ロギングセットアップ、プロセス優先度設定のユーティリティ関数を提供。

Notes / その他
- .env の取り扱いに関する注意:
  - config_setup により生成される .env は絶対に Git にコミットしないことをファイルヘッダで強調しています。
  - 自動ロードでは OS 環境変数が保護され、.env.local による上書きが可能です。
- validate_config CLI は PyYAML が未インストールの場合、YAML の内容検証をスキップして警告を出力します。
- ExecutionEngine / OrderManager 周りはクラッシュ耐性（OrderSent の途中クラッシュや broker_order_id の永続化）や再照合（Reconciliation）を考慮した設計になっています。
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB を参照する設計）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Security
- 初版のため該当なし。

References / Usage
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行（Production / PaperTrading 用スクリプト）:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

今後の予定
- テスト補完（単体テスト・統合テスト）。
- 非同期（async）対応の検討（httpx.AsyncClient 等）。
- Reconciliation 機能の拡張と詳細なドキュメント追記。