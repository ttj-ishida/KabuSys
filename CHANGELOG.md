CHANGELOG
=========
すべての重要な変更点を記載します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

-none-

0.1.0 - 2026-04-23
------------------

Added
- プロジェクト初版リリース。基本的な実行・監視・設定管理機能を実装。
- 環境設定・読み込み
  - src/kabusys/config.py
    - .env / .env.local を自動読み込み（OS 環境変数を優先、.env.local は上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を探索）。
    - .env のパース機能を実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
    - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能（J-Quants / kabu API / LINE / DB /監視 / システム設定など）。
    - 設定値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。不正な値は ValueError を送出。

- 設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話形式の .env 作成/更新ウィザードを追加（python -m kabusys.config_setup）。各項目の説明・デフォルト・シークレット表示をサポート。
    - 既存 .env の読み込み、確認画面、保存処理を実装。保存テンプレートには注意書き（.env を Git にコミットしない等）を含む。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する検証ツールを追加（python -m kabusys.validate_config）。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml 存在チェック・YAML パース（PyYAML が無ければスキップ）を実装。
    - --strict フラグで警告を FAIL（exit code 1）として扱える。

- 実行・監視エントリポイント
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するスクリプトを追加（PID ファイル管理、stop flag 検出、paper_trading 用の DB 分離）。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加（MONITOR_POLL_INTERVAL 環境変数で間隔上書き、デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。

- 注文・実行系コア
  - src/kabusys/execution/order_record.py
    - OrderState 列挙と OrderRecord データモデルを実装。状態遷移の検証ロジック（許可される遷移テーブル）と InvalidStateTransitionError を提供。
    - updated_at は UTC タイムスタンプで自動更新。
  - src/kabusys/execution/order_manager.py
    - OrderManager を実装（create/send/sync/cancel）。DB（OrderRepository）と純粋ロジック（OrderRecord）を組み合わせる。
    - DuplicateOrderError の扱い、create_order の DB 一意制約ハンドリング、send_order のクラッシュ耐性を考慮した 2 相永続化戦略（broker_order_id を先に永続化してから状態遷移）を採用。
    - OrderSentPendingError（注文は発行されたが約定しないケース）の扱いをサポート。
    - sync_order で broker の状態に同期し、部分約定の進展はフィールド差分更新で対応。
    - cancel_order は終端状態を拒否し、broker に対する cancel 呼び出しと状態遷移を行う。
  - src/kabusys/execution/execution_engine.py
    - Signal Queue Pull 型の ExecutionEngine を実装。シグナル処理（8:50-9:10）と push ドレインループ（9:10-15:30）を管理。
    - Gate 1/2/3 のリスク統制フローを導入（シグナルチェック、エグゼキューションレベルチェック、ドローダウン監視により kill_switch 発動）。
    - kill_switch 機能（全 active 注文のキャンセル、ループ停止）と stop エイリアスを提供。
    - WebSocket push の受信を別スレッドで扱い、_push_queue 経由で処理。
    - 発注成功・保留・失敗でのログ・監視DB書き込みフックを実装。
    - paper_trading 環境では paper_sqlite_path を使用して本番 DB と分離。

- broker/kabu クライアント
  - src/kabusys/execution/kabu_client.py
    - KabuStationClient を実装（同期 httpx Client を使用）。トークン取得（/token）、認証付きリクエスト、401 時のトークン再取得リトライ、429 のレート制限検出、ネットワーク/タイムアウト例外の BrokerAPIError 変換などを行う。
    - kabu ステータスコード → 内部ステータス文字列マッピングを保持。
    - 将来的な async 対応に向けて設計。

- 監視 DB / 初期化
  - src/kabusys/monitoring/*. (実装ファイル群参照)
    - monitoring 用の SQLite 初期化ユーティリティを提供（init_monitoring_db を利用）。

- ユーティリティ
  - process priority 設定や logging_setup の利用箇所を追加し、起動直後に優先度設定とログ初期化を行う。

Changed
- src/kabusys/__init__.py
  - パッケージのメタ情報を定義（__version__ = "0.1.0"、__all__ を設定）。

Fixed
- 一連のクラッシュ・再起動後の整合性問題に対処するため、OrderManager.send_order に 2 相永続化パターン（broker_order_id を先に保存）を導入。
- .env パースのエッジケース（引用符内のエスケープ、インラインコメント）に対応して堅牢化。

Notes / その他
- 設定ファイル（config/*.yaml）は存在を推奨。PyYAML がない環境では YAML 内容検証をスキップするが、その旨を警告する。
- kill.flag の取り扱い:
  - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=1 ならクリアして起動、そうでなければ起動を拒否する（ExecutionEngine）。
  - run_monitoring/run_execution はプロジェクト直下 data/stop_requested.flag による外部停止検出を行う。
- paper_trading（ペーパートレード）用の DB 分離により本番データと論理的に分離された環境運用が可能。

今後の TODO（想定）
- async HTTP クライアント対応（httpx.AsyncClient）への移行検討。
- config/*.yaml の詳細スキーマ検証（PyYAML + スキーマ定義）。
- より詳細な監視メトリクスの収集とダッシュボード連携。

--- 
このCHANGELOGは、リポジトリのソースコードから推定して作成したものであり、実際のコミット履歴と差異がある可能性があります。必要であれば差分の修正・補完を行います。