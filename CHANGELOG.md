# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。

## [0.1.0] - 2026-04-23

初回公開リリース。日本株自動売買システム「KabuSys」のコアモジュールとユーティリティを実装しました。

### 追加
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報と公開 API を追加（__version__ = "0.1.0"）。
- 環境設定・読み込み
  - src/kabusys/config.py
    - .env ファイル（.env / .env.local）および OS 環境変数から自動で設定を読み込む機能を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を導入し、配布後も動作するように設計。
    - .env のパース機能を強化（export 形式、引用符付き値、インラインコメント処理、エスケープシーケンスの考慮）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
    - Settings クラスを導入し、各種設定値（J-Quants トークン、kabu API パスワード、DB パス、PID/KILL フラグ等）をプロパティ経由で提供。
    - PAPER_FILL_MODE や paper_trading 用 SQLite パスなど、ペーパートレード用設定を実装。
    - env / log_level の妥当性チェックと値変換を行う（無効値は ValueError）。

- 対話式設定ウィザード
  - src/kabusys/config_setup.py
    - .env を対話式に作成・更新するウィザードを実装。
    - 設定項目一覧（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 通知設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を定義。
    - 既存の .env 読み込み、現在値の再利用、シークレット項目のマスク表示、選択肢制約、保存確認をサポート。
    - .env の書き出しフォーマットを定義（Git にコミットしない旨の警告を含む）。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI を実装。
    - 必須/任意環境変数チェック、プレースホルダ値の検出、KABUSYS_ENV／LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認（PyYAML があればパース検証を実行）を実装。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行用スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - 起動時にプロセス優先度を高く設定、Settings を読み込み、DB 接続（paper_trading 時は paper DB を使用）を行う。
    - ExecutionEngine をスレッドで起動し、停止フラグ（data/stop_requested.flag）検出により安全に停止する仕組みを実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する。

- 発注・状態管理コア
  - src/kabusys/execution/order_record.py
    - OrderRecord データモデル（状態遷移ロジックを含む）を実装。
    - OrderState enum と許可遷移テーブルを定義、transition_to による遷移検証と更新処理を実装。
  - src/kabusys/execution/order_manager.py
    - OrderManager を実装し、OrderRecord（純粋ロジック）と OrderRepository（SQLite）を組み合わせた外向き API を提供。
    - create_order: signal_id の重複防止（DuplicateOrderError）と DB 保存（UUID 発番）を実装。
    - send_order: 送信前に OrderSent へ永続化 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted へ遷移する 2 相永続化戦略を実装。OrderRejectedError / OrderSentPendingError の取り扱いを実装。
    - sync_order: broker 側状態照合と部分約定の反映ロジックを実装（ステータスマッピング含む）。
    - cancel_order: 終端状態判定および broker 取消 API 呼び出し後の Cancelled 遷移を実装。
    - cancel 不可状態定義（Filled を含む）を明示。

- 発注エンジン
  - src/kabusys/execution/execution_engine.py
    - Signal Queue Pull 型発注エンジン ExecutionEngine を実装。
    - セッションライフサイクル（8:50 のシグナル処理、9:10 以降の push ドレイン、15:30 セッション終了）を実装。
    - Gate 1/2/3 による多段リスクチェック、rate limit retry、Circuit Breaker 開時の処理、kill_switch の実装。
    - push 通知処理（broker_order_id → client_order_id を探し sync）、ポジション評価による Gate 3 判定と kill 発動を実装。
    - PID ファイル書き出し、kill.flag の扱い（KILL_FLAG_CLEAR_ON_START によるクリア動作）を実装。
    - WebSocket push を扱う broker の stream_push を利用する Worker スレッド実装を提供（存在しない場合はスキップ）。
    - 発注イベントを monitoring DB に記録するフックを実装（監視DBオブジェクトが渡された場合）。

- kabu station クライアント
  - src/kabusys/execution/kabu_client.py
    - KabuStationClient を実装（同期 httpx Client）。
    - トークン取得の遅延初期化と 401 時の再取得リトライを実装。
    - レスポンス JSON パース失敗やネットワーク/タイムアウトを BrokerAPIError に変換。
    - 429 応答を RateLimitError として扱う。
    - WebSocket（push）連携のための stream_push（ブローカー実装側に依存）を想定。

- 監視関連・ユーティリティ（参照）
  - Monitoring DB 初期化と SystemMonitor の初期化呼び出しを実装するフックを run_monitoring/run_execution で統合。
  - プロセス優先度設定、ログセットアップなどのユーティリティ呼び出しを各起動スクリプトに組み込み。

### 変更
- （初回リリースのため履歴なし）

### 修正
- （初回リリースのため履歴なし）

### 既知の制限 / 注意事項
- config/*.yaml の詳細な内容検証は PyYAML がインストールされている場合のみ行われます。未インストール時はパース検証をスキップして警告を出力します。
- KabuStationClient は同期実装（httpx.Client）です。将来の非同期対応は httpx.AsyncClient への差し替えで対応可能です。
- .env の自動ロードはプロジェクトルート検出に依存します。配布環境でルートが検出できない場合は自動ロードをスキップします（その場合は手動で環境変数を設定してください）。
- ExecutionEngine の時間窓はコード内のデフォルト値に依存（8:50 / 9:10 / 15:30）。必要に応じて EngineConfig でカスタマイズ可能です。

### セキュリティ
- （初回リリースのため該当なし）

----------

次のステップ:
- ドキュメント整備（ユーザー向けのセットアップ手順、デプロイ手順、監視/運用ガイド）。
- 単体テスト / 結合テストの追加（特に発注シーケンス、Reconciliation、リスクチェック、KabuStation のエラーケース）。
- 非同期クライアント対応や高可用化の検討。