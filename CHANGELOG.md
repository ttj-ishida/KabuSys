# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠します。  
重大な互換性のある変更は MAJOR.MINOR.PATCH の増分に従います。本ファイルはコードベースの内容から推測して作成した初回リリースノートです。

## [0.1.0] - 初回リリース
（初期リリース。機能追加と基本的な実行フロー・運用補助ツールを提供）

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。
- 環境設定・管理
  - Settings クラスを導入し、環境変数からアプリ設定を取得する共通 API を提供（src/kabusys/config.py）。
  - .env 自動ロード機構を実装（プロジェクトルートの .env, .env.local 。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - .env ファイルのパース機能を強化（export プレフィックス対応、クォート／エスケープ、インラインコメントの扱い等）。
  - 環境変数必須チェック用の _require() 実装（未設定時は ValueError を送出）。
- 対話式設定ウィザード CLI
  - `python -m kabusys.config_setup` による .env 初期作成・更新ウィザードを追加（src/kabusys/config_setup.py）。
  - シークレット値のマスク表示、選択肢サポート、既存 .env の取り込み、確認後に .env を書き出すテンプレート機能を提供。
- 設定検証 CLI
  - `python -m kabusys.validate_config` による起動前チェックを追加（src/kabusys/validate_config.py）。
  - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・（PyYAML があれば）パース検証を実行。
  - `--strict` オプションで警告を失敗扱い（exit code 1）にする機能を提供。
- 実行・監視用エントリスクリプト
  - Execution エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - 環境に応じて paper_trading 用 DB を分離して使用（settings.paper_sqlite_path）。
    - stop フラグ / PID 管理、プロセス優先度設定、スレッドでのエンジン実行を実装。
  - Monitoring ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
- 注文・実行関連コア
  - OrderRecord（状態遷移を含む純粋なドメインモデル）を実装（src/kabusys/execution/order_record.py）。
    - 明示的な状態列挙 OrderState と許容遷移マップを持ち、不正遷移で InvalidStateTransitionError を送出。
  - OrderManager（外向き API）
    - create/send/sync/cancel フローを実装（src/kabusys/execution/order_manager.py）。
    - DuplicateOrder の検出（signal_id 重複）と例外変換、2 相永続化（OrderSent の永続化 → broker 呼出し → broker_order_id を先に永続化 → OrderAccepted へ更新）によるクラッシュ回復性強化。
    - OrderSentPendingError の扱い（broker が注文番号を返すが約定情報がないケース）をサポート。
  - ExecutionEngine（発注エンジン）
    - シグナル処理ループ（指定時刻でのシグナル読み込み・Gate1/Gate2 チェック・発注）と push ドレインループ（push 通知で同期・Gate3 チェック）を実装（src/kabusys/execution/execution_engine.py）。
    - kill_switch による全 active 注文のキャンセルとループ停止、PID ファイル管理、kill.flag の取り扱い（KILL_FLAG_CLEAR_ON_START による自動クリアオプション）を実装。
    - WebSocket push の受け取り（broker に stream_push がある場合）を別スレッドで処理する仕組みを提供。
    - 発注レイテンシや送信イベントを監視 DB にログするフック（MonitoringDB への書き込み）を追加。
    - position_entries の DuckDB 書き込み（BUY は挿入、SELL は sell_date 更新）を実装し、失敗時はログに留めて処理継続。
- ブローカークライアント
  - kabu station REST API クライアント（KabuStationClient）を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を使った同期クライアント、トークン取得の遅延初期化、401 時のトークン再取得とリトライ、タイムアウト/ネットワークエラーを専用例外に変換。
    - kabu station の状態コードを内部ステータスにマップ。
- モニタリング DB 初期化フック
  - run_monitoring/run_execution から監視 DB の初期化関数を呼ぶことでテーブルの冪等作成を保証。

### 変更
- 環境変数の扱い
  - .env 読み込みの優先順位を OS 環境変数 > .env.local > .env に明文化し、.env.local は override=True（ただし OS 環境変数は保護）で読み込むようにした。
- デフォルト設定
  - DB パスや API base URL、ログレベルなどのデフォルト値を明示（例: DUCKDB_PATH="data/kabusys.duckdb"、KABU_API_BASE_URL のデフォルト等）。
- リスク評価・レート制限
  - ExecutionEngine の Gate2（実行レベルのレート制限）で最大リトライ回数や Circuit Breaker の扱いを導入（リトライ最大3回、CB 発動時はシグナルループ停止）。

### 修正（バグ修正／堅牢化）
- Order のクラッシュ耐性強化
  - send_order の 2 段階コミット（broker_order_id を先に保存）により、クラッシュ時でも Reconciliation で状態回復できるようにした。
- .env ファイル読み込みでの IO エラーを warnings.warn に変換して処理継続可能にした。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルトへフォールバックする安全策を追加。
- 設定検証 CLI で PyYAML が未インストールの環境でも動作するよう YAML 未インストールを警告し、パース検証をスキップするフォールバックを追加。

### 既知の注意点 / 制約
- KabuStationClient は同期 httpx.Client を使用。将来的に非同期化（httpx.AsyncClient への切替）での対応が想定される。
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行う（インストールされていない場合は警告）。
- .env は絶対に Git にコミットしないよう .env 生成テンプレートに注記あり（config_setup が生成する .env に警告コメントを出力）。
- OrderRecord の状態遷移ルールは厳密であり、不正遷移で例外を投げるため、上位ロジックはそれを適切にハンドルする必要がある。

---

今後（Unreleased）に予定する改善案（推測）
- broker API のテスト用モック・インタフェースの整備と DI の強化。
- KabuStationClient の async 対応、接続再利用や接続プールの最適化。
- リコンシリエーション機能の強化（UI/監視への可視化、より詳細なログ）。
- 監視/メトリクスの外部送信（Prometheus 等）との統合。