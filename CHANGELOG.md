CHANGELOG.md

すべての変更は「Keep a Changelog」準拠の形式で記載しています。

[Unreleased]
- -

[0.1.0] - 2026-04-22
Added
- プロジェクト初回リリース (バージョン 0.1.0)
- 設定管理
  - 環境変数読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートの検出 (.git / pyproject.toml を探索) に基づく自動 .env ロード（.env → .env.local の順、OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント取り扱い等に対応。
    - Settings クラスで各種設定値へプロパティアクセスを提供（トークン、kabu API パスワード、DB パス、ログレベル、環境種別、監視閾値等）。
    - 環境変数のバリデーション（不正値は ValueError を送出）。
- 環境設定ウィザード
  - 対話式 .env 作成/更新ツールを追加（src/kabusys/config_setup.py）。
    - 各設定項目の説明、選択肢、デフォルト、秘密値のマスク表示機能を備えたウィザード。
    - 生成される .env のテンプレート出力機能（.env ファイルへ書き込み）。
    - 実行例: python -m kabusys.config_setup
- 設定検証 CLI
  - 起動前に .env と config/*.yaml を検証する CLI を追加（src/kabusys/validate_config.py）。
    - 必須/任意の環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DB パスの親ディレクトリ存在確認（起動時自動作成の注記）。
    - PyYAML の有無を考慮した config/*.yaml の存在確認と YAML パース検証（PyYAML 未導入時はスキップし警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict オプションで警告も異常扱いして exit(1)。
    - 実行例: python -m kabusys.validate_config
- 実行スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル・停止フラグ検出・スレッド管理を実装。
  - 監視用起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用。
    - 停止フラグ検出でループ終了、例外発生時はログ出力して次ポーリングへ継続。
- 注文処理・Execution コンポーネント
  - OrderRecord（状態マシンの純粋モデル）を追加（src/kabusys/execution/order_record.py）。
    - 明示的な OrderState 列挙、許可される状態遷移テーブル、transition_to による遷移検証（不正遷移は InvalidStateTransitionError）。
  - OrderRepository / OrderManager 周辺の発注ワークフローを実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id の重複防止（部分ユニークインデックス違反を DuplicateOrderError に変換）。
    - send_order: クラッシュ耐性を考慮した 2 段階永続化戦略（OrderSent を先に永続化 → ブローカー呼び出し → broker_order_id の永続化 → OrderAccepted への遷移）。
    - OrderSentPendingError の扱い（broker_order_id を残して OrderSent のままにする）をサポート。
    - sync_order: broker 側のステータス照会に基づく状態同期（部分約定の更新や OrderSent→Filled の回復ロジック含む）。
    - cancel_order: 終端状態チェック、broker_cancel 呼び出し、状態遷移処理。
  - ExecutionEngine（シグナルプル発注エンジン）を実装（src/kabusys/execution/execution_engine.py）。
    - セッション定義（発注ウィンドウ: 8:50-9:10、ドレイン: 9:10-15:30 など）。
    - Signal 読み込み（DuckDB 経由）、Gate1/2/3 によるリスクチェック、レート制限のリトライ処理、DuplicateOrder 回避、発注レイテンシ計測・監視DB ログ出力。
    - push ドレイン（WebSocket 経由の通知処理）と Gate 3（ドローダウン検査）による kill_switch 発動。
    - kill_switch 実装: 全 active 注文のキャンセル試行、ループ停止。
    - PID ファイル書き込み、kill.flag の存在チェックと KILL_FLAG_CLEAR_ON_START による挙動制御。
    - WebSocket ワーカ（broker が stream_push を提供する場合のみ利用）。
- ブローカークライアント（kabu station）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx 同期クライアントを使用した REST API 実装。
    - トークン管理（遅延取得・401 リトライ時の再取得）、JSON パース失敗時のエラーラップ。
    - 401（認証再取得後も 401）や 429（レートリミット）を相応の例外にマッピング。
    - WebSocket push（stream_push）を通す設計に対応（将来の async 化を見据えた作り）。
- 監視（Monitoring）
  - 監視 DB 初期化ヘルパー、SystemMonitor のポーリング起動ロジック（run_monitoring）を追加。
- ユーティリティ
  - ログ設定、プロセス優先度設定等のユーティリティ関数を利用（起動スクリプトで呼び出し）。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Security
- 特記事項なし。

Notes / 開発者向け補足
- 本リリースはアーキテクチャの基礎機能（設定管理・検証、発注フロー・状態管理、kabu station クライアント、監視ループなど）を広くカバーしています。詳細な BrokerAPI 実装や RiskManager/Repository の内部実装は別モジュールに分離されています（execution パッケージ内）。
- .env ファイルは絶対に Git にコミットしないこと（config_setup が警告を出力）。
- 本番環境起動時は python -m kabusys.validate_config で事前検証を推奨。--strict を使うと警告も失敗扱いになります。