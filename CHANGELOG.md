CHANGELOG
=========

すべての注目すべき変更点を時系列で記録します（Keep a Changelog 準拠）。

v0.1.0 - 2026-04-23
-------------------

Added
- 全体
  - 初回リリース (v0.1.0) — 日本株自動売買システム「KabuSys」のコア機能を追加。
  - パッケージバージョンは src/kabusys/__init__.py にて `__version__ = "0.1.0"` を設定。

- 設定・環境変数関連
  - 環境変数と .env ファイルを透過的に扱う Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動ロード (プロジェクトルートを .git または pyproject.toml で検出)。
    - 読み込み優先順位: OS 環境 > .env.local > .env。OS 環境を保護するため上書き不可キーを扱う実装。
    - .env 行パーサは export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメント等に対応。
    - 各種プロパティを提供: J-Quants トークン、kabu API パスワード、DB パス、ログレベル、PID/KILL フラグパス、閾値など。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）や KABUSYS_ENV / LOG_LEVEL の検証で不正値は ValueError。

  - 対話式 .env 設定ウィザードを追加（src/kabusys/config_setup.py）。
    - 質問項目定義と既存 .env 読み込み、シークレットのマスク表示、選択肢/デフォルト対応。
    - .env の書き込みヘッダおよび保存指示を実装。
    - 使用例: python -m kabusys.config_setup

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - .env と config/*.yaml の存在・基本検証を実行。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック。
    - PyYAML が存在すれば config/*.yaml をパースして検証。未インストール時はスキップして警告。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険値チェック等）。
    - コマンドライン引数 `--strict` を指定すると警告も失敗 (exit code 1) 扱いにできる。
    - 使用例: python -m kabusys.validate_config [--strict]

- 実行・監視用スクリプト
  - 実行エントリ run_execution を追加（src/kabusys/run_execution.py）。
    - ExecutionEngine を起動するためのスクリプト。プロセス優先度を "high" に設定。
    - paper_trading 環境では専用 SQLite (paper_trading.db) を使用し、本番 DB と分離。
    - 停止フラグ (data/stop_requested.flag) 検出により優雅に停止。
    - PID ファイルを書き込み、実行後に削除。

  - 監視ループ起動スクリプト run_monitoring を追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用。
    - プロセス優先度設定、DB 初期化、例外ハンドリングを実装。

- Execution エンジンと発注ワークフロー
  - ExecutionEngine を追加（src/kabusys/execution/execution_engine.py）。
    - Signal Queue Pull 型の発注エンジン。セッションの時間管理 (signal_send_start / signal_send_end / market_close)。
    - run_session():
      - 起動時のリコンサイル（Reconciler が与えられた場合）。
      - kill.flag の存在チェックと KILL_FLAG_CLEAR_ON_START による自動クリア挙動。
      - PID ファイル管理、WebSocket スレッド起動、シグナル処理ループ（8:50-9:10）、push ドレインループ（9:10-15:30）。
    - _process_signals(): Gate1/2 のリスクチェック、size_multiplier の適用、発注・レイテンシ測定、position_entries への記録 (DuckDB)、監視 DB へのログ出力。
    - WebSocket push を受け取り _push_queue に格納 → _drain_push_queue() で処理。push 受信での同期と Gate 3（ドローダウン監視）評価を実施。
    - kill_switch(): 全 active 注文のキャンセルと内部停止フラグ設定、外部停止用の stop() を公開。

  - OrderManager を追加（src/kabusys/execution/order_manager.py）。
    - create_order(): signal_id 単位での重複防止（DB/インメモリ両対応）と UUID での client_order_id 採番。
    - send_order(): クラッシュ安全性を考慮した 2 相永続化設計
      - (1) OrderCreated → OrderSent を永続化してから broker API を呼ぶ
      - (2) broker からの order_id を先に DB に保存（state は Sent のまま）
      - (3) OrderAccepted へ遷移して commit（成功時）
      - OrderRejectedError、OrderSentPendingError の扱い（pending は order_id を永続化したうえで例外を伝播）
    - sync_order(): broker 側の状態を取得してローカルレコードを同期。部分約定の進行のみの更新対応。
    - cancel_order(): 終端状態はキャンセル不可として例外を投げる。broker_order_id がある場合は API をコールしてから Cancelled に遷移。

  - OrderRecord（状態機械）を追加（src/kabusys/execution/order_record.py）。
    - OrderState 列挙、許容遷移マップ _ALLOWED_TRANSITIONS。
    - transition_to() による遷移検証、タイムスタンプ更新、オプションフィールド（broker_order_id/filled_qty/avg_fill_price/error_message）の反映。
    - InvalidStateTransitionError を追加。

  - Reconciliation / 安全性
    - send_order 中の二段階永続化により、クラッシュ後の状態復旧（Reconciliation）を考慮した実装。
    - sync_order による broker 照合で未確定状態の回復を想定。

- ブローカー（kabu）クライアント
  - KabuStationClient を追加（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 REST クライアント実装（将来の async 化を考慮して設計）。
    - トークン取得の遅延初期化、401 時の自動再取得 + リトライを実装。
    - HTTP ステータスに応じた例外変換（429 → RateLimitError, >=500 → BrokerAPIError 等）。
    - kabu の注文状態コードから内部ステータス文字列へのマッピングを実装。

- 監視関連
  - Monitoring DB 初期化呼び出しと SystemMonitor 利用箇所を追加（run_monitoring / run_execution）。
  - ExecutionEngine から監視 DB へ発注イベントの記録を行うオプションサポート（monitoring_db が与えられた場合）。

Changed
- （初版のため該当なし）

Fixed
- クラッシュ耐性の改善
  - send_order における broker_order_id の先行永続化と OrderSent の取り扱いにより、broker 側の注文番号が DB に残るケースを保証し、後続のリコンサイルでの状態回復を容易にした。

Security
- .env ファイルについて注意喚起を追加（config_setup のヘッダ）: ".env は絶対に Git にコミットしないこと"。

Notes / Migration
- 自動 .env 読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途など）。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使うため、監視用だけの別設定は Settings を通じて上書きする必要あり。
- paper_trading モード使用時は sqlite の保存先が paper_trading DB に分離されるため、本番 DB と混在しない設計。

既知の制約
- KabuStationClient は同期 httpx.Client を使用。将来的に非同期化することでより柔軟な設計が可能。
- 一部の詳細な broker API エラー（細かな原因解析）は BrokerAPIError 等でラップされるため、上位での詳細ハンドリングが必要になる場合あり。

--- 

今後の予定（例）
- async 対応のブローカークライアント追加
- unit/integration テストの整備（特にリコンサイル・クラッシュ復旧シナリオ）
- 監視ダッシュボード連携の強化

(何か補足・修正したい点があれば教えてください。)