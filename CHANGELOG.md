# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

## [0.1.0] - 2026-04-23

### 追加 (Added)
- 初回公開リリース。日本株自動売買システム「KabuSys」の基本機能を実装。
- 環境/設定管理
  - Settings クラスを通じた環境変数ベースの設定取得を実装（src/kabusys/config.py）。
  - 自動 .env ロード機能を実装（プロジェクトルート検出、.env / .env.local の読み込み・優先度制御）。
  - .env ファイルパーサの強化:
    - export プレフィックス対応、クォート（'、"）内のエスケープ処理、行末コメント処理などに対応。
    - 上書き時に OS 環境変数を保護する protected 引数をサポート。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式に .env を生成・更新するウィザード、シークレット値のマスク表示、デフォルト／選択肢対応。
    - .env のテンプレート出力機能を実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML があれば中身も検証）、本番環境向けガードチェックを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- 発注/実行基盤
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）を実装:
    - シグナルプル型の発注ループ（シグナル処理時間帯/ドレインループ/セッション管理）を実装。
    - Gate1（シグナルレベル）、Gate2（エグゼキューションレート制御）、Gate3（ドローダウン監視）を組み込み、NG の場合は適切に処理（必要時 kill_switch 発動）。
    - WebSocket push を受け取って処理する push ドレイン機能を実装（ブローカの stream_push を使う場合）。
    - PID ファイル管理、kill.flag による起動ガードおよび起動時の自動クリアオプションをサポート。
    - 発注ごとの監視 DB ログ記録に対応（モニタリング DB が渡された場合）。
  - 実行スクリプト run_execution（src/kabusys/run_execution.py）を追加:
    - process priority セット、DB 接続（paper_trading の場合は専用 SQLite）、ExecutionEngine の起動・停止監視を実装。
  - 監視スクリプト run_monitoring（src/kabusys/run_monitoring.py）を追加:
    - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する挙動を採用。

- 注文管理（Order lifecycle）
  - OrderRecord（src/kabusys/execution/order_record.py）: 注文状態列挙（State Machine）と遷移検証ロジックを実装。無効遷移時は InvalidStateTransitionError を発生。
  - OrderManager（src/kabusys/execution/order_manager.py）を実装:
    - create_order: signal_id の重複検出（DB とメモリ両面）と OrderCreated レコードの永続化。
    - send_order: クラッシュ安全性を考慮した二相的永続化フロー（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 保存 → OrderAccepted へ遷移）、OrderRejected / pending（OrderSentPendingError）扱いを実装。
    - sync_order: broker 側の状態照合と適切な状態遷移（必要に応じて部分約定情報の更新）を実装。
    - cancel_order: 終端状態チェックの上で broker cancel を呼び Cancelled に遷移。
    - DuplicateOrderError を定義し、同一 signal の重複発注を防止。
    - 送信中や pending のケースを想定した堅牢な実装。

- ブローカ API 実装の基礎
  - KabuStationClient（src/kabusys/execution/kabu_client.py）を実装:
    - httpx を用いた同期 REST クライアント。トークン取得の遅延初期化と 401 に対する再取得リトライを実装。
    - レスポンス JSON パース失敗やネットワーク問題を BrokerAPIError 等の独自例外に変換。
    - レート制限（429）を RateLimitError として扱う。
    - websocket を用いた push 受信（stream_push を想定）との統合ポイントを用意。
  - ブローカ API と注文ステータスのマッピング／例外モデルを整備。

- リスク管理・再調整（Reconciliation）
  - RiskManager / Reconciler 等（参照箇所を実装想定）と ExecutionEngine の統合により、API 成功/失敗記録、レート制限やサーキットブレーカーによる挙動制御をサポート。
  - Reconciliation 実行フローを実装し、セッション開始時にリコンシリエーションを試みる（失敗してもセッション継続する設計）。

- データ層 / DB
  - duckdb と sqlite を併用するデータ設計を採用（分析用に DuckDB、監視/履歴に SQLite）。
  - paper_trading モード用に別 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
  - position_entries への書き込みロジック（BUY/SELL の扱い、約定日として翌営業日を記録）を ExecutionEngine に実装。

- ユーティリティ
  - ロギングセットアップ、プロセス優先度変更ユーティリティ（参照）との連携箇所を追加。
  - stop/kill フラグファイルによる外部制御を全体設計に反映。

### 変更 (Changed)
- 設定読み込み/検証に関する挙動の明確化:
  - .env 自動読み込みの順序を OS 環境 > .env.local > .env として明示し、テスト等で無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを用意。
  - validate_config における YAML 検証は PyYAML 未導入時はスキップする（警告を出力）。

### 修正 (Fixed)
- クラッシュ耐性の向上:
  - 発注フローで broker_order_id を早めに永続化することで、クラッシュ後の照合（Reconciliation）で状態回復可能に修正。
  - send_order 中の pending ケース（OrderSentPendingError）を明示的に扱い、DB に broker_order_id を残す設計にした。

### セキュリティ (Security)
- .env の取り扱いについて注意喚起を .env テンプレートに明記（絶対に Git にコミットしないこと）。

---

注記:
- この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はコミット履歴や PR 内容を基に調整してください。