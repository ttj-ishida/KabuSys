CHANGELOG
=========

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ と整合しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - 実行スクリプト
    - python -m kabusys.run_execution: ExecutionEngine を起動するスクリプトを追加。
      - シグナル処理（8:50-9:10）と push ドレイン（9:10-15:30）を実装。
      - PID ファイル管理、停止フラグ（data/stop_requested.flag）検出、kill_switch による全注文キャンセル機能を実装。
      - paper_trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH／data/paper_trading.db）を使用して本番 DB と分離。
    - python -m kabusys.run_monitoring: SystemMonitor ポーリングループの起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
  - 環境設定関連
    - python -m kabusys.config_setup: 対話式 .env 作成/更新ウィザードを追加。
      - J-Quants トークン、kabu API パスワード、DB パス、LINE 通知設定等の項目を対話的に設定可能。
      - シークレット項目は表示時にマスク。保存時は .env を生成。
    - python -m kabusys.validate_config: 起動前に .env と config/*.yaml を検証する CLI を追加。
      - --strict モードで警告を失敗扱いにできる。
      - PyYAML が未インストールでも存在チェックは行い、パースはスキップする旨を警告。
  - 設定管理
    - kabusys.config: 自動 .env 読み込み（OS 環境変数 > .env.local > .env）、.env パーサー、Settings クラスを追加。
      - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮して扱う。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - Settings に各種プロパティ（トークン、パスワード、DB パス、PID/KILL フラグ設定、閾値、env/log_level の検証等）を実装。
  - 発注/実行系
    - OrderRecord: 注文状態のデータモデルと状態遷移ロジックを実装（純粋なビジネスロジック、DB 不依存）。
      - 状態列挙 OrderState と許可遷移テーブルを定義。InvalidStateTransitionError を定義。
    - OrderManager: OrderRecord と OrderRepository を組み合わせた外向き API を実装。
      - create_order: signal_id の重複チェック（部分ユニーク制約／DB 制約を考慮）。
      - send_order: broker 呼び出し前に OrderSent を永続化し、broker_order_id を先に保存する 2 段階永続化パターンを採用してリカバリを容易に。
        - OrderRejectedError、OrderSentPendingError の扱いを区別。
      - sync_order: broker 側の状態を照合してローカル状態を同期。部分約定の進行に対しては差分更新を行う。
      - cancel_order: キャンセル不能状態の判定、必要に応じて broker API を呼んで Cancelled に遷移。
    - ExecutionEngine: Signal Queue Pull 型発注エンジンを実装。
      - Gate 1（シグナルレベル）/ Gate 2（発注レベル・レート制御）/ Gate 3（ドローダウン監視）により多段リスク検査を実施。
      - size_multiplier 適用（BUY のみ）や qty の 100 株刻み切捨て処理を実装。
      - 発注レイテンシ測定、監視 DB へのトレードイベント記録（MonitoringDB が提供されている場合）。
      - WebSocket push 受信を別スレッドで行い、push を _push_queue に入れてドレイン処理で同期処理を実行。
      - 再調整（Reconciler）を起動時に実行できるオプションをサポートし、結果をログ出力。
  - Broker / kabu クライアント
    - KabuStationClient: kabu ステーション REST API クライアントを実装（httpx 同期 client）。
      - トークン取得の遅延初期化、自動再取得（401 発生時のリトライ）を実装。
      - レスポンス JSON パース失敗やタイムアウト／ネットワークエラーを BrokerAPIError 等に変換。
      - 429 を RateLimitError にマッピング。
      - 将来的な非同期対応を見据えた実装（httpx.AsyncClient への切替が可能な設計）。
  - 監視・DB 初期化
    - monitoring_db.init_monitoring_db を使用して SQLite の監視テーブルを冪等に初期化する処理を追加。
  - ユーティリティ
    - logging_setup と process_priority のユーティリティを各スクリプトで利用（起動時にログ設定・プロセス優先度設定を実行）。

Changed
- なし（初期リリース）

Fixed
- .env パーサーの堅牢化:
  - export プレフィックス、クォート内のバックスラッシュエスケープ処理、クォートなしのインラインコメントルール（直前が空白/タブのみコメントとみなす）に対応。
- send_order の永続化シーケンスを設計し、クラッシュ時に OrderSent や broker_order_id が残るケースでも Reconciliation で復元可能に改善。
- run_monitoring: MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルトにフォールバックし、time.sleep の ValueError 回避。

Security
- なし

Notes
- config/*.yaml の検証は PyYAML がインストールされている場合にパースチェックを行う。未インストール時はパースチェックをスキップして警告を出す設計。
- 設定ウィザードは生成した .env を Git 管理下に絶対にコミットしないように注意喚起するヘッダを出力する。
- ExecutionEngine の一部挙動（時間判定・push ドレイン・kill.flag の扱い等）はテストしやすさを考慮して設計されている（ユニットテスト時は内部メソッドを直接呼べる）。

今後の改善案（参考）
- 非同期化（httpx.AsyncClient / asyncio）対応による WebSocket / API 呼び出しの最適化。
- Reconciler の更なる堅牢化と監視メトリクスの拡充。
- 設定検証の強化（YAML スキーマ検証、環境変数の型チェック、自動修正提案）。
- テスト用に KabuStationClient のモック/ベンチマークを提供。