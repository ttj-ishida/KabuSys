Keep a Changelog 準拠の CHANGELOG.md（日本語）を作成しました。プロジェクトの現状（src 以下のコードから推測）をもとに主な追加・変更点を整理しています。

CHANGELOG.md
=============
全ての重要な変更点をこのファイルに記載します。本ファイルは Keep a Changelog の形式に従います。

注: 下記のリリースは、ソース上の __version__ 等および実装内容から推測して作成しています。実際のリリース日やバージョン運用ポリシーに合わせて必要に応じて修正してください。

Unreleased
----------
- （現時点の未リリース変更はありません。ここは将来の変更用です。）

0.1.0 - 2026-04-23
------------------
追加
- CLI / ユーティリティ
  - 設定検証 CLI を追加: python -m kabusys.validate_config
    - .env および config/*.yaml の存在・基本整合性を起動前に検出。
    - --strict オプションで警告を FAIL（exit(1)）として扱う。
    - PyYAML が存在する場合は YAML のパースチェックを行い、未インストール時は警告でスキップ。
    - 必須環境変数のプレースホルダ（"_here" や "your_value"）を検出して警告。
    - KABUSYS_ENV の妥当性チェックや live 環境向けの追加ガードを実装。
  - 環境設定ウィザードを追加: python -m kabusys.config_setup
    - .env の対話的生成/更新を支援。シークレットのマスク表示、選択肢、デフォルト値、確認プロンプトを実装。
    - 生成される .env テンプレートにコメントヘッダーを付加（Git にコミットしないよう明記）。
- 設定管理
  - kabusys.config モジュールを追加
    - Settings クラスで全ての環境変数を集中管理（J-Quants／kabu／DBパス／監視設定等）。
    - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読込む。読み込み優先度は OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化が可能（テスト用）。
    - .env 行パーサーは export プレフィックス、引用文字列（クォート内でのエスケープ）、インラインコメント処理などに対応。
    - 必須項目が未設定の場合は _require() が ValueError を投げる。
- 実行・監視ランナー
  - run_execution.py を追加: ExecutionEngine を起動するエントリポイント
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite を分離して使用。
    - プロセス優先度設定、PID ファイル書込み、停止フラグ（stop_requested.flag）検出を実装。
  - run_monitoring.py を追加: SystemMonitor のポーリングループ実行スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
- 注文・発注関連コア
  - OrderRecord（dataclass）と OrderState（enum）を実装
    - 状態遷移ルールを明確化（許可される遷移セットを定義）。
    - transition_to() で遷移検証とタイムスタンプ更新、オプションフィールド更新を行う。
    - 不正遷移で InvalidStateTransitionError を送出。
  - OrderManager を実装
    - create_order(), send_order(), sync_order(), cancel_order() といった外向き API を提供。
    - 同一 signal_id の重複注文防止（DuplicateOrderError）。
    - send_order() はクラッシュ耐性を考慮した 2 相永続化（OrderSent 状態保存 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）を実装。
    - Broker の各種エラー（OrderRejectedError, OrderSentPendingError 等）に対するハンドリングを実装。
    - sync_order() で broker 側の状態を照合し、必要に応じて部分約定情報（filled_qty, avg_fill_price）を更新。
  - ExecutionEngine を実装
    - シグナル取得（DuckDB）→ Gate1/2（リスク検査）→ 発注フロー、推奨の発注ウィンドウ（8:50–9:10）とドレイン（9:10–15:30）をサポート。
    - size_multiplier の適用、ペーパートレード時の DB 分離、API レート制限のリトライ、API レイテンシ計測と監視DBへの記録（監視用 DB が渡された場合）。
    - WebSocket push のドレイン処理、push に基づいた sync_order 実行、Gate3（ドローダウン）チェックと kill_switch 発動機能。
    - kill.flag の存在検査、KILL_FLAG_CLEAR_ON_START による起動時自動クリア挙動、PID ファイル管理を実装。
- Broker クライアント
  - KabuStationClient を実装（httpx を使用した同期 REST クライアント）
    - トークン取得の遅延初期化と自動再取得（401 時リトライ）。
    - レスポンス JSON パースの失敗を BrokerAPIError に変換。
    - 429（Rate Limit）や 5xx に対する専用例外（RateLimitError, BrokerAPIError）を送出。
    - websocket push（stream_push）を持つクライアントに対して push 受信ループを容易に組み込める設計。

変更
- 設定・既定値の明確化
  - DUCKDB_PATH、SQLITE_PATH、KABU_API_BASE_URL、LOG_LEVEL 等のデフォルト値をコード中で明示。
  - Settings.paper_fill_mode にバリデーションを追加（instant/partial/never/reject）。
  - Settings.env/log_level で不正値は ValueError を送出するように変更（事前に検証できる設計）。
- モニタリング挙動
  - run_monitoring は環境に依らず「本番の sqlite_path」を使用する旨を明確化。
- .env 読み込み
  - .env の自動ロードでは OS の既存環境変数を protected として上書き禁止にする等、上書きロジックを整理。

修正（堅牢化・バグ回避）
- MONITOR_POLL_INTERVAL の検証を強化し、無効な値（0 以下や非数）の場合はデフォルトにフォールバックして警告。
- HTTP クライアント呼び出しでのタイムアウト/ネットワーク例外を BrokerAPIError にラップして明示的に扱うように変更。
- send_order フローでクラッシュや中断が起きても復旧可能なよう DB に broker_order_id を先に永続化する設計により Reconciliation が状態回復可能。
- ExecutionEngine の起動時に kill.flag が存在した場合の動作を明確化（clear_on_start により自動クリアまたは起動拒否）。
- .env パーサーを改善（引用符内のエスケープ処理、コメント判定ルール改善、export プレフィックス対応）して実環境の .env をより正確に扱うようにした。

注意事項 / 備考
- config/*.yaml の内容検証は PyYAML に依存。インストールされていない場合は検証をスキップし警告する挙動です。
- .env ファイルは生成スクリプトで作成できます（scripts/generate_config.py を参照する旨の警告を出す実装あり）。
- .env は秘密情報を含むため、生成時のヘッダに「絶対に Git にコミットしないこと」を明記しています。
- 実稼働（KABUSYS_ENV=live）時は LINE 通知設定が未設定だと警告するなどのガードを追加。

開発者向けメモ（実装からの推測）
- Reconciliation（reconciler）機能が ExecutionEngine 起動時に呼び出される設計があるため、運用中のクラッシュ後でも注文状態整合を取るしくみが組み込まれている。
- OrderRecord は DB 非依存の純粋ロジックに集約されているため、単体テストが容易に行える構造になっている。
- Broker API 周りは抽象プロトコル（BrokerAPIProtocol）を利用しているため、テスト用の MockBrokerClient の差し替えが想定されている。

以上。リリース日やバージョン名は必要に応じて調整してください。追加で「詳細な変更点を各ファイルごとに列挙」や「英語版 CHANGELOG」を作成することも可能です。必要があればお知らせください。