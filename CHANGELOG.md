# Changelog

すべての注目すべき変更点を記録します。これは Keep a Changelog 準拠の CHANGELOG.md 形式です。

フォーマット:
- 変更はセクション（Added / Changed / Fixed / Security / …）に分類しています。
- 日付はリリース日を示します。

## [0.1.0] - 2026-04-22

初回公開リリース。

### Added
- 基本パッケージ構成とバージョン情報を追加
  - src/kabusys/__init__.py にパッケージ名とバージョン `0.1.0` を定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルや環境変数から設定を自動ロードする仕組みを導入。
    - プロジェクトルートを .git または pyproject.toml を基準に探索するため、CWD に依存しない自動ロードを実現。
    - .env パーサーを実装:
      - `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント（クォートなしの場合の挙動）をサポート。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効にする環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で利用可能）。
    - _require() による必須環境変数取得と未設定時の ValueError 発生。
    - Settings クラスを提供し、各種設定（J-Quants トークン、kabu API パスワード、DB パス、PID/KILL フラグ、しきい値など）をプロパティ経由で取得可能に。

- 設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新できる CLI を実装。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 通知設定など）。
    - シークレット項目はマスク表示、選択肢/デフォルト対応、既存 .env の読み込みと再利用機能。
    - 保存時に .env を適切なテンプレート形式で書き出す `_write_env` を実装。
    - `python -m kabusys.config_setup` で実行可能。`--env-file` オプションで出力先指定可。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の設定不備を起動前に検出する CLI を実装。
    - 必須/任意環境変数リストを定義し、プレースホルダ値の検出や未設定の検出をレポート。
    - `KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェックと許可値リストを導入。
    - DUCKDB/SQLite のパスの親ディレクトリ存在チェック（なければ警告）。
    - config/*.yaml の存在確認と（PyYAML がインストールされていれば）パース検証を実施。PyYAML 未インストール時は YAML 内容検証をスキップして警告。
    - `KABUSYS_ENV=live` の場合に本番向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定検出）を追加。
    - CLI オプション `--strict` を追加（警告を FAIL として exit(1)）。

- 実行スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - paper_trading モード時は paper 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - プロセス優先度設定、監視 DB 初期化、DuckDB 接続、ExecutionEngine 実行ループの起動/停止ハンドリングを実装。
    - 停止フラグファイル（data/stop_requested.flag）検出によるシャットダウン処理を追加。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検出による安全終了を実装。

- 発注 / 実行エンジン関連
  - src/kabusys/execution/execution_engine.py
    - ExecutionEngine を実装。Signal Queue Pull 型の発注エンジン。
    - セッション制御（signal_send_start/End、market_close）を持ち、run_session により一日のワークフローを実行。
    - WebSocket push の受信とドレイン処理（_websocket_worker / _drain_push_queue）を組み込み、push に基づく同期処理を実行。
    - シグナル処理フローを実装（_process_signals）:
      - size_multiplier 適用（BUY のみ）、qty の丸め（100 株単位）等。
      - Gate 1（シグナルレベル）・Gate 2（実行レベル：レート制限等）を通す設計。Gate 2 は最大 3 回リトライ、CIRCUIT_BREAKER 発生時はシグナルループを停止。
      - 発注成功/保留/失敗のハンドリング、latency 計測、監視 DB へのイベント記録。
      - position_entries テーブルへの書き込み（発注成功時にエントリ記録。BUY pending は記録、SELL pending は記録しない等）。
    - Gate 3（ポートフォリオ指標: ドローダウン等）検査で NG の場合は kill_switch を発動。
    - kill_switch 実装: 全 active 注文をキャンセルしループを停止。
    - PID ファイル書き出しと kill.flag の扱い（KILL_FLAG_CLEAR_ON_START に依存）を実装。

  - src/kabusys/execution/order_record.py
    - OrderRecord データモデル（dataclass）と OrderState 列挙型を実装。
    - 許可される状態遷移マップを定義し、transition_to による遷移検証と更新（updated_at 自動更新）を実装。
    - InvalidStateTransitionError を導入し、不正遷移時に例外を送出。

  - src/kabusys/execution/order_manager.py
    - OrderManager を実装。OrderRecord（純粋ロジック）と OrderRepository（SQLite）を組み合わせて外向き API を提供。
    - create_order: signal_id ごとに active 注文の重複を防止。client_order_id に uuid4 を採番。DB 側の部分ユニーク制約違反は DuplicateOrderError に変換。
    - send_order: クラッシュ安全性を考慮した二相的永続化手順を実装（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted に遷移）。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order: broker 側のステータス取得によりローカル状態を同期（部分約定/平均約定価格の更新を含む）。OrderSent → Filled 等の直接遷移が許可されない場合に OrderAccepted を挟む回復ロジックを実装。
    - cancel_order: 終端状態はキャンセル不可として InvalidStateTransitionError を発生させる。broker_order_id がある場合は broker 側キャンセル API を呼ぶ。

  - src/kabusys/execution/kabu_client.py
    - kabu station REST API クライアント実装（同期 httpx ベース）。
    - トークン管理: 遅延初期化、401 時のトークン再取得とリトライを実装。
    - レスポンスの JSON パース失敗や HTTP エラー（401/429/5xx 等）を BrokerAPIError / RateLimitError 等に変換して扱う。
    - websocket push のための stream_push インタフェースを想定（ExecutionEngine 側で存在チェックを行う設計）。
    - （注）実行時の詳細エラー処理と再試行の方針を盛り込む形で API クライアントの基盤を実装。

- 監視関連
  - src/kabusys/monitoring/*（ファイル一覧の一部が参照されている）
    - 監視用 DB 初期化関数 init_monitoring_db を提供し、run_monitoring / run_execution から利用。

- ユーティリティ
  - src/kabusys/utils/*（ログ設定・プロセス優先度設定など）
    - setup_logging, set_process_priority などを利用して、各プロセス開始時の共通初期化を実現。

### Fixed
- N/A（初回リリースのため該当なし）

### Changed
- N/A（初回リリースのため該当なし）

### Security
- .env ファイルは絶対に Git にコミットしない旨を .env テンプレートに明記（config_setup の出力に注意書きあり）。
- シークレットは UI 上でマスクして表示する等の配慮を実装。

### Notes / Usage
- CLI:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動: python -m kabusys.run_monitoring
- 主要な環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 任意/設定可能: KABUSYS_ENV (development|paper_trading|live), DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, KILL_FLAG_CLEAR_ON_START など
- Paper Trading:
  - KABUSYS_ENV=paper_trading 時は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db がデフォルト）を使用し、本番 DB と分離。
- 構成ファイル:
  - config/*.yaml の存在とパースを検証（PyYAML がインストールされている場合）。
  - サンプル生成スクリプト: python scripts/generate_config.py（validate_config の警告メッセージより参照可能）。

今後のリリースでは、テストの追加・API クライアントの強化（非同期対応等）、監視・リコンサイル機能の拡充、運用上の細かな改善を予定しています。