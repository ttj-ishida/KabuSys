# CHANGELOG

すべての注目すべき変更をここに記録します。 このプロジェクトは Keep a Changelog の形式に従います。

## [0.1.0] - 2026-04-22

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを追加。
  - 設定管理（src/kabusys/config.py）
    - .env ファイルの自動読み込み機能を追加。読み込み順は OS 環境変数 > .env.local > .env。
    - _find_project_root により __file__ を起点にプロジェクトルートを特定（.git / pyproject.toml を探索）。
    - .env の行パーサーを実装（export 形式対応、クォート文字のエスケープ処理、インラインコメントの限定解釈）。
    - _load_env_file で既存環境を保護する protected 引数を導入し、override オプションをサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
    - Settings クラスを追加し、環境変数から安全に設定値を取得するプロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、各種しきい値等）。
    - PAPER_FILL_MODE、paper_sqlite_path などペーパートレード用設定を追加。
  - 設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式に .env を作成・更新するウィザードを追加。主な項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を含む。
    - 既存 .env の読み込みと既存値の再利用、秘密項目のマスク表示、書き込みテンプレートの生成を実装。
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - .env / config/*.yaml の起動前チェックを提供（必須環境変数未設定、プレースホルダ検出、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML 未インストール時はスキップ）等）。
    - --strict オプションを追加（警告を FAIL 扱いして exit(1)）。
    - live 環境向けの追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の警告）。
  - 実行スクリプト
    - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
      - ExecutionEngine の起動シーケンス（プロセス優先度設定、DB 接続、PID/停止フラグ処理、スレッド管理）を実装。
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
      - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL で間隔上書き可能（デフォルト 60 秒）。
      - 監視は常に本番 sqlite_path を使用（環境に依らず）。
  - Execution コンポーネント（src/kabusys/execution/*）
    - ExecutionEngine（execution_engine.py）
      - シグナル処理（8:50–9:10）と WebSocket push ドレイン（9:10–15:30）を想定したセッション実行ロジックを実装。
      - Gate1（シグナルレベル）、Gate2（実行レベル・レート制限）、Gate3（ドローダウン監視）を組み込み、Gate3 NG で kill_switch を発動。
      - push 処理、position_entries への約定予定登録、監視DB へのトレードイベント記録を実装。
      - kill_switch / stop による全 active 注文のキャンセル処理を実装。
    - OrderRecord（order_record.py）
      - 注文状態遷移を表す OrderState 列挙型と許容遷移表、および状態遷移検証を行う OrderRecord クラスを追加。
      - 不正遷移時に InvalidStateTransitionError を送出。
    - OrderManager（order_manager.py）
      - signal_id 重複検知（DuplicateOrderError）、create/send/sync/cancel の高レベル API を実装。
      - send_order は二相永続化を考慮（OrderSent を永続化 → broker 呼び出し → broker_order_id 保存 → OrderAccepted へ遷移）し、OrderSentPendingError、OrderRejectedError に対応。
      - sync_order は broker 側の状態に基づく同期を行い、部分約定の進行はフィールド差分更新で対応。
      - cancel_order はキャンセル不可能な状態をチェックして broker API 呼び出し後に状態遷移。
    - KabuStationClient（kabu_client.py）
      - kabuステーション REST API クライアント（httpx）を実装。トークン取得、401 時の自動再取得とリトライ、429（Rate Limit）および 5xx エラーの扱いを実装。
      - kabu ステーションの状態コードを内部ステータスにマッピング。
      - 同期リクエストに加え WebSocket ベースの push 処理（websocket モジュール）を想定した stream_push フックに対応。
  - リスク管理・リコンシリエーション・リポジトリ等の基礎的連携コードを追加（リポジトリ / Reconciler / RiskManager などを使用する流れを実装）。

### Changed
- なし（初回公開のため変更履歴はありません）。

### Fixed
- なし（初回公開のためバグ修正履歴はありません）。

### Security
- 環境変数や .env の取り扱いについて注意喚起をドキュメントに記載（.env を絶対に Git にコミットしない旨、config_setup に注記）。

### Notes / Implementation details
- YAML パース検証は PyYAML がインストールされている場合のみ行う。未インストール時は警告を出してスキップする挙動。
- .env のパースはシェル互換の完全な実装ではないが、実用上必要な export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱いをサポート。
- ExecutionEngine はクラッシュや部分永続化（OrderSent のまま等）を考慮した設計になっており、Reconciliation により外部整合性を回復できることを想定。
- MONITOR_POLL_INTERVAL が不正（非正整数）の場合はデフォルトにフォールバックする。

---
今後の予定（例）
- BrokerAPI の抽象化強化と単体テスト整備
- WebSocket push の耐障害性強化（再接続・バックオフ）
- 監視 / メトリクスの充実化（Prometheus 等）

（必要であれば、各ファイルごとのより詳細な変更ポイントや設計意図、既知の問題点を追加します。）