# Changelog

すべての注目すべき変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリース日は UTC ベースで付与しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

### 追加 (Added)
- プロジェクト初版リリース。
- 設定関連ツール
  - 対話式 .env 作成/更新ウィザードを追加（kabusys.config_setup）。
    - シークレット項目は表示時にマスク。既存 .env 読み込み・Enter で既存値再利用可能。
    - デフォルト値・選択肢・説明付きの項目定義を提供し、.env を生成する `_write_env` を実装。
    - コマンドラインから python -m kabusys.config_setup で実行可能。
  - 起動前に環境・設定を検証する CLI を追加（kabusys.validate_config）。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスや config/*.yaml の存在・パース検証（PyYAML があれば内容検証）など。
    - --strict オプションで警告も失敗扱いにできる。
- 環境・設定管理モジュール（kabusys.config）
  - .env ファイルの自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準、OS 環境変数を保護）。
  - .env パース処理を実装（export プレフィックス対応、クォート文字内のエスケープ処理、インラインコメント取扱いなど）。
  - Settings クラスを提供し、各種設定値（トークン、API パスワード、DB パス、PID/KILL フラグパス、閾値、環境判定フラグ等）をプロパティで取得可能。
  - PAPER_FILL_MODE、およびペーパートレード専用 SQLite パス（PAPER_TRADING_SQLITE_PATH）をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
- 実行/監視ランナー
  - ExecutionEngine を起動するランナーを追加（kabusys.run_execution）。
    - paper_trading モード時に専用 SQLite（paper_trading DB）を使用し、本番 DB と分離。
    - PID ファイル管理、停止フラグ（stop_requested.flag）検出、プロセス優先度設定を実装。
  - SystemMonitor をポーリングする監視用ランナーを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
- 注文処理基盤（execution パッケージ）
  - OrderRecord：状態遷移ロジックを持つ純粋なデータモデルを追加（状態遷移の検証、更新時刻自動更新、オプションフィールド更新）。
  - OrderManager：外向け API を提供。create/send/sync/cancel のフロー実装。
    - create_order で signal_id の重複チェックを行い、重複時は DuplicateOrderError を返す。
    - send_order はクラッシュ耐性を考慮した二相的永続化シーケンスを実装（OrderSent を先にコミット → broker 呼び出し → broker_order_id を保存 → OrderAccepted に遷移）。
    - OrderSentPendingError（注文番号はあるが確定しないケース）を扱い、pending 状態で DB を残す。
    - sync_order で broker 側の状態取得に基づく同期（部分約定の進行時は filled_qty/avg_fill_price の更新含む）。
    - cancel_order はキャンセル不可状態を判定して例外を出す等の安全化。
  - ExecutionEngine：シグナル駆動の発注エンジン実装（時間帯に応じた処理分割、WebSocket push ドレイン）。
    - Gate 1（シグナル水準）、Gate 2（エグゼキューション/レート制御、リトライ）、Gate 3（ドローダウン監視）を導入。Gate 3 NG で kill_switch を発動。
    - size_multiplier の適用（BUY のみ）、発注送信時の遅延計測・監視 DB へのイベント記録（監視 DB が提供されている場合）。
    - WebSocket push の受信を別スレッドで処理し、push 到着時に sync_order を実行して状態更新。
    - セッション起動時に Reconciler を実行する仕組みを用意（存在すれば起動時に照合を行う）。
    - kill_switch により全 active 注文をキャンセルし、ループを停止する API を提供。
- ブローカークライアント（kabu_client）
  - KabuStationClient を実装（httpx ベース、トークン取得/再取得の遅延初期化、401 リトライ、429/5xx のエラー分類）。
  - レスポンスの JSON パース失敗やネットワーク例外を BrokerAPIError に変換するハンドリングを追加。
  - WebSocket ストリーミング（stream_push）を持つ broker に対して push 受信コールバックを使える設計。
- モニタリング関連
  - monitoring_db 初期化呼び出しの追加（監視 DB テーブルを保証）。
  - 監視ループ・発注の経緯を監視 DB に記録するフックを追加。

### 変更 (Changed)
- 環境設定のデフォルト挙動
  - .env の自動読み込みは OS 環境変数を優先し、.env.local を .env より優先して上書きする挙動に統一。
- ログ出力レベルの取り扱い
  - LOG_LEVEL の値を許容する列挙を統一し不正値は Settings プロパティで ValueError を投げるように変更（validate_config は警告扱い）。
- ExecutionEngine の DB 接続
  - paper_trading 環境では paper_trade 用の SQLite を使用するよう挙動を明示化。

### 修正 (Fixed)
- 注文送信フローの信頼性向上
  - send_order の二相永続化設計により、クラッシュ/再起動時のリコンシリエーションで状態回復可能に（broker_order_id を確実に保存することで sync が復旧可能）。
- .env パーサーの堅牢性向上
  - クォート付き値内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いを改善。
- プロセス制御関連の安定化
  - PID ファイルの作成/削除、stop/kill フラグの検出とクリア（KILL_FLAG_CLEAR_ON_START のオプション化）を追加し、起動時の残留フラグによる誤起動を防止。

### セキュリティ (Security)
- .env 出力の注意書きを .env 作成ウィザードのヘッダに明記（.env を Git にコミットしないよう強調）。

### 既知の問題 / 注意点 (Known issues / Notes)
- config/*.yaml のパース検証は PyYAML がインストールされている場合にのみ実行される。未インストール時は警告を出してスキップする。
- KabuStationClient の実装は同期 httpx.Client ベース。将来的な非同期対応は httpx.AsyncClient に置き換えることで対応可能。
- 一部の外部モジュール（monitoring_db, SystemMonitor, Reconciler, BrokerClientFactory 等）はこのリリースでの外部依存として想定される（実装の整合性は併せて確認のこと）。

---

（今後のリリースでは各コンポーネントの詳細な変更履歴（リコンシリエーション改善、リスクマネージャー調整、ブローカードライバ拡張など）を個別に記載予定です。）