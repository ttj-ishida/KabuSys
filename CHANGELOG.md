CHANGELOG
=========

このファイルは Keep a Changelog 準拠で記載しています。
リリースや変更の概要をコードベースから推測して日本語でまとめています。

Unreleased
----------
（今後の変更・修正をここに記載）

0.1.0 - 2026-04-23
-----------------
初回リリース（コードベースのスナップショットに基づく推測）

Added
- 環境設定 / 設定管理
  - Settings クラスを導入し、環境変数を型付きプロパティ経由で参照可能にした（J-Quants / kabu API / LINE / DB /監視 /システム設定など）。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションをサポート。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、コメント処理）。
  - PAPER_FILL_MODE や各種閾値（CPU/MEM/DISK など）を環境変数から取得するプロパティを追加し、妥当性チェックを行う。
  - paper_trading 用の専用 SQLite パス（PAPER_TRADING_SQLITE_PATH）と分離動作をサポート。

- CLI ツール
  - config_setup ウィザード（python -m kabusys.config_setup）を追加。対話式に .env を生成・更新可能。機密項目はマスク表示、選択肢・デフォルト提示あり。
  - validate_config（python -m kabusys.validate_config）を追加。環境変数や config/*.yaml、パス存在など起動前チェックを実行。--strict オプションで警告を FAIL 扱いにできる。
  - run_execution / run_monitoring 起動スクリプトを追加。ExecutionEngine / SystemMonitor のエントリポイントを提供。

- 発注エンジン / 実行ロジック
  - ExecutionEngine を実装。シグナル処理（8:50-9:10）→ push ドレイン（9:10-15:30）を実行するセッションループを提供。
  - EngineConfig により target_date や時間帯を設定可能。
  - ExecutionEngine が WebSocket push を別スレッドで受け取り、同期的に処理する仕組みを実装（broker.stream_push 経由）。
  - kill_switch の導入：異常時に全 active 注文をキャンセルしてループを停止する仕組み。

- 注文管理（Execution サブパッケージ）
  - OrderRecord（状態遷移モデル）を追加。OrderState 列挙型と許可遷移を明示し、不正遷移で InvalidStateTransitionError を投げる。
  - OrderManager を追加。create/send/sync/cancel の高レベル API を提供し、DB（OrderRepository）と組み合わせた状態管理を行う。
    - create_order は signal_id の重複検出（DuplicateOrderError）を実装。
    - send_order はクラッシュ安全性を考慮した 2 相的な永続化フローを採用（OrderSent を先に永続化→ broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）。
    - OrderSentPendingError（ブローカーが注文番号を返すが約定しないケース）を専用扱いし、pending を DB に残す。
    - sync_order はブローカーからの状態取得を元に部分約定や状態遷移を反映。filled_qty / avg_fill_price の差分更新にも対応。
    - cancel_order はキャンセル不可状態（Closed/Cancelled/Rejected/Filled など）をチェックして適切に動作。

- ブローカークライアント実装（kabu 専用）
  - KabuStationClient（同期 httpx ベース）を実装。トークン管理（遅延取得・401 リトライ）、エラー区別（429 レート制限 → RateLimitError、タイムアウト/ネットワーク → BrokerAPIError）を実装。
  - kabu ステーション状態コードの内部マッピングを定義。

- 監視（Monitoring）
  - run_monitoring スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は実行環境にかかわらず本番 sqlite_path を使用する挙動を明確化。
  - init_monitoring_db の呼び出しで監視用テーブル初期化を保証。

- DB / データ処理
  - DuckDB をデータ分析用 DB として利用（signals / portfolio_targets 参照）。ExecutionEngine は DuckDB 接続を受け取り signals を読み込む。
  - position_entries に対する発注後の書き込み（BUY の entry 登録、SELL の sell_date 更新）を実装（ON CONFLICT DO NOTHING を使用）。

- プロセス運用
  - PID ファイル書き出し、kill.flag チェック、起動時に KILL_FLAG_CLEAR_ON_START による自動クリアオプション（セーフティ）を実装。
  - プロセス優先度設定フック（set_process_priority）を run scripts の起動時に呼び出す。

Changed
- 設定検証の振る舞いを明確化
  - validate_config と Settings のバリデーションの役割を分離。validate_config は起動前チェック（警告/エラーを集約）を行い、Settings の一部プロパティはアクセス時に例外を投げて厳密に検証する設計。

Fixed
- クラッシュ耐性・再起復旧の強化
  - send_order の永続化順序変更などにより、クラッシュ後に OrderSent 状態や broker_order_id が残っても Reconciliation により回復可能にした。
  - sync_order の同一状態でも部分約定の進行を検知して更新することで状態差分更新漏れを防止。

Security
- .env の取り扱いに関する注意を config_setup に明記（.env を絶対に Git にコミットしない旨のヘッダを追加）。

Notes / その他
- validate_config では PyYAML 未インストール時に YAML 検証をスキップする旨の警告を出す。
- ログレベルや KABUSYS_ENV の不正値に対するメッセージと既定動作を整備（警告/例外の仕分け）。
- 一部外部コンポーネント（logging_setup / process_priority / monitoring_db / broker_factory 等）はモジュール境界で呼び出しているが、実装詳細は別ファイルに含まれる（このスナップショットでは参照のみ）。

今後の改善候補（コードから推測）
- KabuStationClient の非同期化（httpx.AsyncClient への移行）で WebSocket / 長時間処理の効率化。
- validate_config の YAML 内容チェックを強化（スキーマ検証）。
- リトライ・バックオフ戦略の体系化（API 呼び出し周りの一貫化）。
- テスト用のモックやインテグレーションテストスイートの整備（Reconciliation / send_order のクラッシュ耐性を自動検証）。

参考
- 実行方法のヒントは各スクリプトの docstring に記載（例: python -m kabusys.config_setup / validate_config / run_execution / run_monitoring ）。