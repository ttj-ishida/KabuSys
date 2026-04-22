# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog のスタイルに準拠しています。  

## [0.1.0] - 2026-04-22

### Added
- 初回リリース: KabuSys 基本モジュール群を追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - 設定管理
    - src/kabusys/config.py
      - .env の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - .env/.env.local の読み込み順序（OS 環境変数を保護）。
      - 複数フォーマット対応の .env パーサ（export プレフィックス、クォート、エスケープ、インラインコメントの取り扱い等）。
      - 環境変数必須チェック用の _require()、Settings クラスによるプロパティアクセス（J-Quants / kabu API / DB パス / LINE / PID / kill flag / thresholds 等）。
      - PAPER_FILL_MODE 等の値検証（不正値で ValueError を送出）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env 設定ウィザード CLI
    - src/kabusys/config_setup.py
      - インタラクティブな .env 作成/更新ウィザード（項目定義、既存値の読み取り、シークレットマスク、選択肢サポート）。
      - .env ファイル書き込みテンプレート（コメント付き）と --env-file オプション。
      - 実行後の次ステップ案内（validate_config の推奨）。
  - 設定検証 CLI
    - src/kabusys/validate_config.py
      - .env と config/*.yaml の起動前検証用 CLI（--strict フラグで警告も失敗扱い）。
      - 必須/任意環境変数チェック、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性検査。
      - DB パスの親ディレクトリ存在チェック（存在しない場合は警告）。
      - PyYAML 未インストール時は YAML 内容検証をスキップして警告を出す挙動。
      - config/*.yaml ファイルの存在確認とパース検証（PyYAML 利用時）。
      - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
  - 実行スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine の起動スクリプト。プロセス優先度設定、PID 書き込み、stop フラグ検出、DB 接続（paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離）。
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視 DB は環境に関係なく本番 sqlite_path を使用。
  - 発注系コア
    - src/kabusys/execution/order_record.py
      - OrderState 列挙と状態遷移ロジック、Allowed transitions 定義、InvalidStateTransitionError、OrderRecord dataclass（状態遷移時に updated_at を UTC 自動更新）。
    - src/kabusys/execution/order_repository.py (参照されるが実ファイルはここに含まれていないコードベースに依存)
    - src/kabusys/execution/order_manager.py
      - OrderManager によりシグナル → 発注の外向き API を提供。
      - create_order: signal_id の重複検出（部分ユニーク制約 / DB 制約から DuplicateOrderError に変換）。
      - send_order: クラッシュ耐性を意識した二相的永続化手順（OrderSent を先に永続化 → broker 呼出し → broker_order_id 永続化 → OrderAccepted に遷移）。
      - OrderSentPendingError の扱い（broker_order_id を永続化したまま例外を伝播し Reconciliation 対象にする）。
      - sync_order: broker 側状態取得による同期ロジック（status→内部状態マッピング、部分約定の更新処理、OrderSent→Filled などの不整合時に OrderAccepted を経由して遷移）。
      - cancel_order: 終端状態のキャンセル禁止判定、broker cancel 呼び出し、Cancelled への遷移。
    - src/kabusys/execution/execution_engine.py
      - Signal Queue Pull 型の発注エンジンの実装。
      - EngineConfig（target_date / 時間窓）。
      - シグナル読み込み（DuckDB）、Gate 1/2（シグナルレベル・実行レベルのリスクチェック）、Gate 3（ドローダウン監視）を実装。
      - size_multiplier の適用、BUY の数量切り捨てロジック（100単位）。
      - リトライ / レート制限処理、API 成功/失敗の記録、監視 DB へのイベントログ。
      - WebSocket push ドレイン処理（_push_queue）、push による sync_order 呼出しと Gate 3 評価。
      - kill_switch による全 active 注文のキャンセル処理。
      - 起動時の Reconciliation 実行と kill.flag の扱い（KILL_FLAG_CLEAR_ON_START が有効な場合はクリアして起動、そうでなければ起動拒否）。
  - broker クライアント
    - src/kabusys/execution/kabu_client.py
      - KabuStationClient: kabu station REST API クライアント（同期 httpx.Client を使用）。
      - トークン管理（遅延取得、401 時に再取得してリトライ）。
      - レスポンス JSON パース時の例外変換、httpx のタイムアウト/ネットワーク例外を BrokerAPIError に変換。
      - 429（Rate Limit）と 5xx の判定と例外化。
  - ユーティリティ（参照）
    - ロギングセットアップ、プロセス優先度設定、monitoring DB 初期化などを利用する実行フローを統合。

### Changed
- （初回公開に伴う設計上の注記）
  - Paper trading の DB を本番 DB と完全分離（settings.paper_sqlite_path を使用）。
  - Monitoring は環境に依存せず本番 sqlite_path を使用する設計に変更。
  - .env の読み込みで OS 環境変数を保護するため protected セットを導入（.env.local は override=True でも OS 環境変数を上書きしない）。
  - validate_config の --strict オプションにより警告を fail 扱いにできるようにした。

### Fixed / Reliability improvements
- 発注の耐障害性強化
  - send_order の二相永続化により、クラッシュ時でも broker_order_id が DB に残り、Reconciliation で状態を回復できるように設計（Issue 想定: Reconciliation の補助）。
  - OrderSentPendingError の取り扱いを明確化し、pending 状態を DB に残した上で呼び出し元に伝播することで上位での再試行や観測が可能。
- HTTP API のエラー処理強化
  - KabuStationClient でタイムアウト・ネットワークエラーを BrokerAPIError にラップし、401 の際はトークン再取得と 1 回のリトライを行う。
- .env パーサの堅牢化
  - クォート内でのバックスラッシュエスケープ対応、コメントの取り扱い改善など。

### Notes
- PyYAML がインストールされていない環境では validate_config による config/*.yaml の中身検証がスキップされ、警告が出ます。Parser を有効にするには PyYAML をインストールしてください。
- MONITOR_POLL_INTERVAL は 1 以上の整数であることを期待します。無効値はデフォルト（60 秒）にフォールバックします。
- kill.flag の既存検出挙動:
  - ExecutionEngine は起動時に kill.flag が存在すると、KILL_FLAG_CLEAR_ON_START が 1 でなければ起動を拒否して SystemExit(1)。
  - KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に kill.flag をクリアして起動を許可する（本番では 0 推奨）。
- ExecutionEngine はセッションの最後に PID ファイルを削除します。PID ファイルの場所は Settings で設定可能（PID_FILE_PATH）。
- これらは初期実装としての挙動記述です。実運用前に validate_config や config_setup により設定の検証・初期化を行ってください。

--- 

今後のリリースでは、テストカバレッジの向上、非同期対応（httpx.AsyncClient への移行）、より詳細なモニタリング・メトリクス収集、追加ブローカー実装を予定しています。