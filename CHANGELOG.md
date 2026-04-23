# CHANGELOG

すべての notable な変更点を記載します。形式は「Keep a Changelog」に準拠しています。

なお、本CHANGELOGは与えられたコードベースの内容から推測して作成しています。実際のリリース日や細かい履歴はソース管理の履歴に従って補完してください。

## [Unreleased]

- ドキュメントやビルド/公開に関する未リリースのメタ情報はありません（初期リリースとして以下の v0.1.0 を含む）。

---

## [0.1.0] - 初回リリース（推定）

初期公開バージョン。自動売買システム KabuSys の基盤となる設定管理、実行エンジン、発注ロジック、監視処理、kabuステーション用クライアント等のコア機能を実装。

### 追加 (Added)

- 全体
  - パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - 実行・監視用スクリプトを提供:
    - python -m kabusys.run_execution: ExecutionEngine の起動スクリプト（PID / stop flag 管理、paper_trading 時の DB 分離）。
    - python -m kabusys.run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL による間隔制御）。
  - 環境変数・設定管理を実装:
    - kabusys.config.Settings クラスにより環境変数から設定を取得（必須値チェック・型変換を含む）。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を検出し、.env と .env.local を OS 環境変数を保護しつつ読み込む。
    - .env のロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォートとエスケープ、コメントの扱い（ルールに基づく）に対応。
  - 対話式設定ウィザードを追加:
    - kabusys.config_setup: .env の初期作成・更新を対話式で支援する CLI（シークレット入力扱い・既存値の再利用・デフォルト値表示・保存確認）。
  - 設定検証ツールを追加:
    - kabusys.validate_config: .env と config/*.yaml の起動前チェック。--strict を指定すると警告も失敗扱い（exit 1）。
    - 検証内容: 必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在可否、config/*.yaml の存在と（PyYAML があれば）パース検証、本番時の追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START 等）。
  - ExecutionEngine（発注エンジン）を実装:
    - シグナル処理（デイリーフロー: signal_send_start/ end）と WebSocket push ドレインループ（market_close まで）。
    - run_session にて Reconciliation 実行、kill.flag チェック（KILL_FLAG_CLEAR_ON_START による挙動差異）、PID ファイル管理、WebSocket スレッド起動。
    - signals の DuckDB からの読み出し（portfolio_targets との JOIN）。
    - Gate 1/2/3 による多段リスクチェック（signal レベル、実行レート制限、ポートフォリオ指標によるドローダウン監視）。
    - push ドレイン時に broker.get_positions() を参照して Gate3 を評価。
    - 発注成功・保留・失敗でのモニタリングDB記録（存在する場合）と position_entries への書き込み（発注の BUY/SELL に応じた処理）。
  - Order 管理/発注ロジック:
    - OrderRecord: 注文状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と状態遷移検証ロジック（Allowed transitions と transition_to 実装）。
    - OrderManager: DB（OrderRepository）と組み合わせた外向き API。create_order（signal ごとの重複防止）、send_order（2相永続化を意識した手順）、sync_order（broker の状態照合）、cancel_order（終端状態の検査・キャンセル）、例外クラス（DuplicateOrderError, InvalidStateTransitionError）を定義。
      - send_order はクラッシュ安全性に配慮したシーケンスを実装（OrderSent 状態の永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted への遷移等）。
      - OrderSentPendingError を考慮し、pending 状態は DB に broker_order_id を残して上位へ伝播する設計。
  - KabuStation API クライアント:
    - KabuStationClient を実装（同期 httpx クライアント使用）。トークン取得、認証リトライ（401 時トークン再取得後1回リトライ）、タイムアウト / ネットワークエラーを BrokerAPIError に変換。
    - レスポンスステータスに基づくエラー処理（429 → RateLimitError、5xx → BrokerAPIError 等）。
    - kabu ステーションのステータスコード→内部ステータス変換マッピングを実装。
    - WebSocket push 受信（websocket / stream_push 呼び出しを期待する broker 実装向け）に対応。
  - 監視（Monitoring）起動:
    - run_monitoring は Monitoring 用 DB 初期化（init_monitoring_db）、SystemMonitor の check ループ、stop flag 検出、SQLite/duckdb の接続管理を行う。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
  - 設定 / 監視に関するユーティリティ:
    - Settings で paper_trading 用 DB 切替、PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）、閾値関連（CPU/MEM/DISK）等を提供。
    - kill_flag_path / pid_file_path の取り扱いを提供。
  - その他ユーティリティ参照:
    - logging_setup、process_priority、monitoring_db、system_monitor などのユーティリティ/モジュールを利用する設計（実装ファイルの存在を前提）。

### 変更 (Changed)

- （このバージョンは初回公開のため既存機能の「変更」はありません。設計上の注意点をドキュメントや CLI のヘルプに反映。）

### 修正 (Fixed)

- （初期実装のため既知のバグ修正履歴は無し。パーサやクラッシュ安全性の考慮など再現性の高い運用性に配慮した実装が含まれる。）

### セキュリティ (Security)

- 本リリースでは .env を絶対に Git にコミットしないように README/ウィザード内メッセージで注意喚起。
- 本番環境（KABUSYS_ENV=live）時には LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START=1 の危険を警告するチェックを追加。

---

開発者向けのメモ（実装上の意図・設計ポイントの要約）
- send_order の実装はクラッシュ耐性（2相に相当する永続化の順序）とリコンサイル容易性を重視。OrderSent 状態が残るケースや broker_order_id が先に永続化されるケースを想定して reconcile（sync）で回復できる設計。
- ExecutionEngine はシグナル処理（バッチ）と push イベント処理（ドレイン）を明確に分離しているため、テスト時に個別に呼び出しやすい。
- .env パーサはシングル/ダブルクォート内のエスケープや inline コメントの扱いを考慮しているため、現実的な .env の記述に耐える。
- Monitoring は環境に依らず「本番 sqlite_path」を使用する仕様。監視は実行環境の妥当性を保証するため常に本番 DB を参照する方針。

---

注記
- 上記はソースコードから推測してまとめた CHANGELOG です。細かい修正履歴（コミット単位）やリリース日、パッチ番号等は実際の Git 履歴に基づいて補完してください。