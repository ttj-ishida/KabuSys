# CHANGELOG

すべての注目すべき変更履歴を記録します。  
このファイルは Keep a Changelog のガイドラインに準拠しています。

フォーマット：
- 未リリースの変更は [Unreleased] に記載します。
- 既リリースはバージョンと日付で記載します。

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-04-23
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。

### 追加 (Added)
- パッケージ全体
  - パッケージ初期化とバージョン定義を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 環境設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml で探索）。
  - 読み込み順序: OS環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env のパースを強化：
    - export KEY=val 形式のサポート
    - クォート（シングル/ダブル）内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォートなしの場合は直前が空白/タブの # をコメントと認識）
  - Settings クラスを追加し、環境変数から各種設定を取得（例: jquants_refresh_token, kabu_api_password, duckdb/sqlite パス、paper_trading 切替等）。
  - PAPER_FILL_MODE 等の検証ロジックと有効値チェックを実装。
- 設定ウィザード CLI (src/kabusys/config_setup.py)
  - .env の作成・更新を対話式で行うウィザードを実装。
  - 秘匿項目のマスク表示、選択肢・デフォルト表示、既存 .env の読み込みをサポート。
  - .env のテンプレート出力（コミットしない旨の注意含む）。
- 設定検証 CLI (src/kabusys/validate_config.py)
  - .env と config/*.yaml の事前検証を行う CLI を実装。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース検証（PyYAML 未インストール時はスキップ）を実装。
  - --strict オプションで警告をエラー扱いにする機能。
  - KABUSYS_ENV=live のときの追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）。
- 実行エントリスクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - プロセス優先度設定、PID/停止フラグの扱い、本番/ペーパーでの DB 分離（paper_trading 用 SQLite）を実装。
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
- 発注エンジン・実行ロジック (src/kabusys/execution/*.py)
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナル処理（8:50–9:10）、push ドレインループ（9:10–15:30）を実装。
    - kill.flag の扱い、KILL_FLAG_CLEAR_ON_START による起動時自動クリア、PID ファイル書き込み、WebSocket push の取り込み (push_queue)。
    - Gate1（シグナルレベル）、Gate2（エグゼキューションレベル：レート制限とサーキットブレーカー）、Gate3（ドローダウン監視）を実装。NG 時は適切に kill_switch を発動。
    - DuckDB からのシグナル読み取り、position_entries の更新（約定日計算に next_trading_day を使用）。
    - 監視 DB への発注イベントログ出力フック（MonitoringDB が渡された場合）。
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態機械（OrderState）と許可遷移表を実装。状態遷移検証と更新（更新時刻自動セット）。
    - InvalidStateTransitionError を定義。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - シグナルからの注文作成、重複チェック（signal_id の active 注文禁止）、送信フロー（2相永続化）を実装。
    - send_order の挙動:
      - OrderSent に DB 保存後に broker API 呼び出し（クラッシュ安全性確保のため）。
      - broker_order_id を先に永続化 → OrderAccepted に遷移の流れ。
      - OrderRejectedError / OrderSentPendingError のハンドリング。
    - sync_order（broker 側状態との同期）、cancel_order（キャンセル可否判定と API 呼び出し）を実装。
    - DuplicateOrderError を定義。
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - kabuステーション REST API クライアントを実装（httpx を使用）。
    - トークンの遅延取得と 401 時の再取得・1 回リトライ。
    - レスポンス JSON パースエラーやネットワーク/タイムアウトを BrokerAPIError に変換。
    - 429 を RateLimitError に変換、500 以上はサーバーエラーとして扱う。
    - WebSocket push（stream_push）をサポートするインターフェースを想定。
- 実行補助ユーティリティ
  - プロセス優先度設定ユーティリティ呼び出し（set_process_priority）。
  - ロギングセットアップ呼び出し（setup_logging）。
- 監視データベース初期化フック（init_monitoring_db）が実行前に呼び出されるようになりました。

### 変更 (Changed)
- なし（初回リリースのため）。

### 修正 (Fixed)
- なし（初回リリースのため）。

### 既知の注意点 / 移行メモ
- .env ファイルは絶対に Git にコミットしないでください（config_setup のヘッダにも注記あり）。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます（テスト等で利用）。
- 実行前に以下の必須環境変数が設定されていることを確認してください:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  validate_config CLI を使うことで実行前にチェックできます。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定と KILL_FLAG_CLEAR_ON_START の値に注意してください。
- PAPER_TRADING 用の DB（PAPER_TRADING_SQLITE_PATH）を指定しない場合はデフォルト data/paper_trading.db が使われます。本番 DB と分離されます。

---

（今後のリリースでは Unreleased セクションに変更を記載し、リリース時にバージョン／日付を移動してください。）