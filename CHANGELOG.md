Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

0.1.0 — 2026-04-23
------------------

Added
- 初回リリース。KabuSys の基本的な設定管理・実行監視・発注エンジンのコア機能を追加。
- 環境設定／読み込み
  - Settings クラスを導入し、環境変数から各種設定を取得する API を提供（src/kabusys/config.py）。
  - .env 自動読み込み機構を実装（プロジェクトルートの検出: .git / pyproject.toml ベース）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントなどに対応（堅牢なパーサ実装）。
  - 必須値取得時に未設定なら ValueError を送出する _require() を提供。
- 環境設定ウィザード CLI
  - 対話式ウィザードで .env を作成・更新するツールを追加（python -m kabusys.config_setup）。秘密値のマスク表示や選択肢の扱い、.env の読み書きをサポート（src/kabusys/config_setup.py）。
- 設定検証 CLI
  - .env と config/*.yaml の整合性や必須環境変数の有無をチェックする CLI を追加（python -m kabusys.validate_config）。--strict オプションで警告を失敗扱いにできる（src/kabusys/validate_config.py）。
  - YAML が未インストールの場合はパース検証をスキップして警告を出す仕組みを持つ。
- 実行スクリプト
  - 実行エンジン起動スクリプトを追加（python -m kabusys.run_execution）。paper_trading 環境では専用の paper_trading DB を使用して本番 DB と分離する（src/kabusys/run_execution.py）。
  - 監視（SystemMonitor）用のポーリングループスクリプトを追加（python -m kabusys.run_monitoring）。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（src/kabusys/run_monitoring.py）。
- 発注エンジン / 実行ロジック
  - ExecutionEngine を実装。シグナル読み込み->Gate1/Gate2 チェック->発注->push ドレインというセッションフローを提供（src/kabusys/execution/execution_engine.py）。
  - セッション制御（start/end 時刻、PID ファイル生成、kill.flag の扱いなど）を実装。
  - WebSocket push（kabu push）を受け取り同期処理するワーカを組み込み。push は内部キューに入れてドレイン処理を行う。
- 注文状態管理
  - OrderRecord と OrderState（状態遷移表）を実装。状態遷移の検証と関連フィールド更新を行う純粋なビジネスロジックを提供（src/kabusys/execution/order_record.py）。
  - OrderManager を実装。create/send/sync/cancel の高レベル API を提供し、SQLite リポジトリと Broker API を連携（src/kabusys/execution/order_manager.py）。
  - 送信時の 2 相永続化（OrderSent に遷移して DB 更新 → broker 呼び出し → broker_order_id を保存 → OrderAccepted に遷移）によりクラッシュ耐性を考慮。
  - OrderSentPendingError / OrderRejectedError 等のエラー経路を考慮した処理。DuplicateOrderError を導入して同一 signal_id の重複を防止。
  - sync_order によりブローカー側の状態を DB に反映（部分約定の進捗や avg_fill_price の更新を考慮）。
- ブローカークライアント（kabu station）
  - KabuStationClient を実装（同期 httpx ベース）。トークンの遅延取得、401 時の自動トークン再取得とリトライ、HTTP エラーコード(429→RateLimitError, 5xx→BrokerAPIError など) のマッピングを実装（src/kabusys/execution/kabu_client.py）。
  - stream_push を持つブローカーに対して WebSocket 受信をサポート（push イベントを ExecutionEngine へ渡す）。
- リスク管理 / レート制御 / Gate
  - RiskManager（インタフェース）を組み込み、Gate1/Gate2/Gate3 によるシグナルレベル・エグゼキューションレベル・ドローダウン監視を想定したフローを実装（ExecutionEngine との連携）。
  - API 成功/失敗の記録や、Circuit Breaker 発動時の挙動（ループ停止など）を反映。
- 監視・DB
  - 監視用 SQLite（monitoring.db）と DuckDB を使用。init_monitoring_db による監視テーブル初期化を保証（src/kabusys/run_monitoring.py, run_execution.py）。
  - 発注時に監視 DB へイベントを記録するフックを追加（MonitoringDB を通じて）。また、position_entries の書き込みで約定予定日を記録する処理を実装。
- ユーティリティ
  - ロギング設定セットアップ・プロセス優先度設定ユーティリティと連携して起動シーケンス改善（高優先度設定を最初に実行）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Notes / 利用上の注意
- .env は決してリポジトリにコミットしないこと（config_setup のヘッダにも注意書きを追加）。
- 本番（KABUSYS_ENV=live）では LINE 通知や kill flag の扱い等を慎重に設定すること。validate_config に本番時の追加チェック/警告がある。
- ExecutionEngine の動作は時間帯（signal_send_start/ end / market_close）に依存するため、テスト時には直接メソッドを呼んで検証が可能。
- KabuStationClient は同期実装（httpx.Client）であり、将来的に async 実装に置き換え可能（httpx.AsyncClient）。

開発中 / 今後の改善予定（抜粋）
- async 対応の簡易化（httpx.AsyncClient への切替）
- Broker API のモック実装強化とテストカバレッジ拡充
- 監視・アラートの強化（LINE 以外の手段や詳細メトリクスの追加）
- config/*.yaml のスキーマ検証（現在は PyYAML の存在時にパースチェックを行うが、スキーマバリデーションは未実装）

---- 

この CHANGELOG はコードベースからの推測に基づいて作成しています。実際のコミット履歴やリリースの意図と差異がある場合は、修正してください。