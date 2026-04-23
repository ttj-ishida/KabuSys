# Changelog

すべての重要な変更を記載します。フォーマットは「Keep a Changelog」に準拠します。

20xx-xx-xx: 日付はリリース日に合わせて適宜更新してください。

## [Unreleased]

- （今後の変更をここに記載）

---

## [0.1.0] - 2026-04-23

最初の公開バージョン。日本株自動売買システム「KabuSys」の基本機能を実装しました。主要な追加点は以下のとおりです。

### 追加 (Added)

- 全体
  - パッケージ初期リリース（__version__ = 0.1.0）。
  - アプリケーション設定・環境変数管理を提供する Settings クラスを追加（kabusys.config）。
    - 環境変数から各種設定値（トークン、API パスワード、DB パス、各種フラグなど）を安全に取得。
    - KABUSYS_ENV / LOG_LEVEL の値検証、PAPER_FILL_MODE の妥当性チェックを実装。
    - Path 型を返すプロパティや閾値（CPU/Memory/Disk）などを提供。
  - .env 自動読み込み機能を追加
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を自動で読み込み。
    - OS 環境変数を保護するための保護キー（protected）を導入。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。

- CLI / ユーティリティ
  - 設定ウィザード（kabusys.config_setup）
    - 対話式に .env を作成/更新するウィザードを実装。
    - シークレット項目のマスク表示、選択肢やデフォルトのサポート、保存キャンセル機能を実装。
    - 保存時にはテンプレートヘッダを付与し、.env をコミットしないよう注意を表示。
  - 設定検証ツール（kabusys.validate_config）
    - .env と config/*.yaml の設定不備を起動前に検出する CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）や KABUSYS_ENV/LOG_LEVEL の妥当性検査を実行。
    - DB パスの親ディレクトリ存在確認、PyYAML があれば YAML のパースチェックを実施。
    - KABUSYS_ENV=live の追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告も失敗と扱い exit(1) を返す実行モードを提供。

- 実行スクリプト
  - run_execution（kabusys.run_execution）
    - ExecutionEngine を用いた本番/ペーパートレード起動スクリプトを追加。
    - Paper Trading 時は専用 SQLite（paper_trading.db）を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（stop_requested.flag）監視を実装。
  - run_monitoring（kabusys.run_monitoring）
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動を明示。

- 発注・実行エンジン（execution）
  - ExecutionEngine（kabusys.execution.execution_engine）
    - シグナルプル型の発注エンジンを実装。シグナル処理（8:50–9:10）と push ドレイン（9:10–15:30）を扱う。
    - セッション開始時のリコンシリエーション、kill.flag の扱い（起動時の自動クリアは KILL_FLAG_CLEAR_ON_START に従う）を実装。
    - WebSocket push を受けて内部キューに入れ同期処理するワーカを実装（stream_push 未実装ブローカに対する警告あり）。
    - PID ファイルの書き込み/削除、スレッド管理を実装。
    - position_entries（DuckDB）への約定記録処理を組み込み（BUY/Sell に応じた扱い）。
    - 発注遅延計測・監視DB へのログ出力フックを追加。
  - OrderManager（kabusys.execution.order_manager）
    - OrderRecord（状態マシン）と OrderRepository（SQLite）を組み合わせた外向け API を実装。
    - create_order: signal_id 単位での重複検知（DB の部分ユニーク制約違反を DuplicateOrderError に変換）。
    - send_order: クラッシュ耐性を考慮した 2 相永続化戦略（OrderSent のコミット → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted へ遷移）。
    - OrderRejectedError / OrderSentPendingError の適切な扱いを実装。
    - sync_order: broker 側状態照合による同期（同一状態でも部分約定量や平均価格の更新を行う）。
    - cancel_order: キャンセル不可能状態のチェックと broker 呼び出し、状態遷移の適切な管理。
  - OrderRecord（kabusys.execution.order_record）
    - 注文状態を enum で定義し、許可される遷移テーブルを実装。
    - transition_to による遷移検証（不正遷移は InvalidStateTransitionError を発生）とメタデータ更新（broker_order_id, filled_qty, avg_fill_price, error_message, updated_at）を実装。
  - KabuStationClient（kabusys.execution.kabu_client）
    - kabu ステーション REST API の同期クライアント実装（httpx 使用）。
    - トークン取得の遅延初期化、自動再取得（401 時のリトライ）、エラーの変換（タイムアウト/ネットワーク/認証/レート制限/サーバエラー）を実装。
    - kabu のステータスコードから内部ステータス（open/partial/filled/cancelled/rejected）へのマッピングを保持。

- リスク管理・リコンシリエーション（参照実装）
  - ExecutionEngine 側で利用する RiskManager / Reconciler 用の組み立てポイントを用意（具体的な実装は別モジュールで提供）。
  - Gate1/Gate2/Gate3 のフロー（シグナル検査・実行レート制限・ドローダウン監視）を実装し、Gate3 NG 時は kill_switch を発動する設計。

- 監視DB
  - init_monitoring_db を用いて監視テーブルの初期化（冪等）を実施するフローを追加。
  - 監視プロセスは環境にかかわらず本番 sqlite_path を使用する旨を明記。

- ユーティリティ
  - .env パーサーの改善
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、非クォート時のインラインコメント判定（前が空白/タブの場合）が可能。
  - DB パスチェック、親ディレクトリの存在確認に関する警告出力を追加。
  - MONITOR_POLL_INTERVAL の不正値回避（1 未満はデフォルトにフォールバック）を実装。

### 変更 (Changed)

- （初回リリースのため該当なし）

### 修正 (Fixed)

- （初回リリースのため該当なし）

### 注意事項 / 既知の挙動

- .env は絶対に Git にコミットしないでください（config_setup の出力でも同様の注意を表示します）。
- Settings._load_env_file は OS 環境変数を既定で保護しますが、テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- ExecutionEngine のセッション周り・ブローカー呼び出しは外部リソースに依存するため、本番稼働前に validate_config と十分な動作確認を推奨します。
- KabuStationClient は同期 API（httpx.Client）を使用します。将来的に非同期化する場合は httpx.AsyncClient へ移行可能な設計です。
- YAML の内容検証は PyYAML がインストールされている場合のみ行われます（未導入時はスキップして警告）。

---

今後のリリースでは以下を予定しています（例）:
- 監視・ロギング機能の強化（アラート配信履歴、LINE 通知のリトライ等）
- Broker API のテストモック拡充と外部化された設定（タイムアウト/リトライ方針）
- 非同期対応（WebSocket / API 呼び出しの async 化）
- ドキュメント・運用ガイドの充実

（必要に応じて日付や項目を調整してください）