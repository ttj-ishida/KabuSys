CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 初回リリースを追加。
- 環境設定 / 起動補助 CLI を追加:
  - python -m kabusys.config_setup
    - 対話式ウィザードで .env を作成 / 更新。
    - J-Quants / kabuステーション / DB パス / LINE 通知など主要設定項目を用意。
    - シークレット項目は表示をマスク、デフォルトや既存値を利用可能。
    - .env のテンプレート出力機能を実装（.env をリポジトリにコミットしない旨を明記）。
  - python -m kabusys.validate_config
    - .env と config/*.yaml の起動前検証を実行。
    - 必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在確認、YAML パース検証（PyYAML がある場合）などを実施。
    - --strict オプションで警告も失敗扱いにできる。
- 設定管理モジュールを追加 (kabusys.config):
  - .env 自動ロード機構（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env / .env.local の読み込み順序と OS 環境変数保護（上書き制御）。
  - 複雑な .env 行パーサー（export プレフィックス、クォート内のエスケープ、インラインコメント扱い等）を実装。
  - Settings クラスで型付きプロパティを提供（トークン/パス/閾値/環境/ログレベル等）。バリデーションを含む。
- Execution 系コアを追加:
  - ExecutionEngine（kabusys.execution.execution_engine）
    - シグナル取得（DuckDB）→ Gate1/Gate2 による検査→ 発注フロー、push ドレインループ、WebSocket ワーカー、セッション時間帯管理（8:50-9:10 / 9:10-15:30）を実装。
    - PID ファイル書き出し・kill.flag の取り扱い・KILL_FLAG_CLEAR_ON_START のサポート。
    - 発注遅延や監視DBへの書き込みを記録可能。
  - OrderRecord（状態遷移ロジック）を追加
    - OrderState 列挙と許容遷移表、InvalidStateTransitionError を実装。
  - OrderManager（外向き API）
    - create_order / send_order / sync_order / cancel_order を実装。
    - send_order はクラッシュ耐性を考慮した 2 段階永続化（OrderSent の永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted への遷移）を採用。
    - OrderSentPendingError, OrderRejectedError の扱いを考慮。
    - DuplicateOrderError を導入（同一 signal_id のアクティブ注文重複検出）。
  - Reconciler / RiskManager 等の組み合わせでリコンシリエーション・レート制限・ドローダウン監視に対応（ExecutionEngine から利用）。
- Broker クライアント実装（kabusys.execution.kabu_client）:
  - KabuStationClient を実装。httpx を使用した同期 API。
  - トークン取得の遅延初期化と 401 に対する再取得リトライ、ステータスコードマッピング、429 の RateLimitError、ネットワーク/タイムアウト例外を BrokerAPIError に変換。
  - WebSocket push（stream_push）インターフェースを想定し、WebSocket スレッドで受信した payload を ExecutionEngine 側へ渡す仕組みをサポート。
- 実行 / 監視用スクリプトを追加:
  - run_execution.py
    - ExecutionEngine の起動スクリプト。paper_trading 時は専用 SQLite を使用して本番 DB と分離。
    - プロセス優先度設定（高優先度）・PID 管理・停止フラグ監視を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を調整可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用する設計。
- 監視 DB 初期化ユーティリティを追加 (monitoring_db.init_monitoring_db 呼び出し箇所を導入)。
- データストア:
  - DuckDB / SQLite を併用。DuckDB は分析・シグナル読み取り、SQLite は監視・注文履歴に利用。
  - paper_trading 用に専用 SQLite パスを Settings で提供。
- その他ユーティリティ:
  - ロギングセットアップとプロセス優先度設定ユーティリティを使用（kabusys.utils.*）。
  - ExecutionEngine 内で発注成功時に position_entries を更新（次営業日を entry_date として記録）。
- パッケージ情報:
  - パッケージバージョン __version__ = "0.1.0" を設定。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- .env をリポジトリへコミットしない旨をテンプレートに明記。
- 設定ウィザードではシークレット項目を表示マスク。

Notes / 想定動作
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config モジュールの自動 .env 読み込みを無効化できます（テスト用途など）。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップし、警告を出します。
- 実運用時は KABUSYS_ENV=live を設定すると validate_config が注意喚起（LINE 通知設定や Kill Switch 設定）を行います。
- ExecutionEngine は kill.flag による安全停止と、Gate による自動 kill_switch 発動（重大なドローダウン等）を備えています。

作者・貢献者
- コードベース内の実装に基づき自動生成された CHANGELOG です。詳細な変更点は該当ソースファイルのドキュメントとコメントを参照してください。