CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

未リリース
---------

- なし

0.1.0 - 2026-04-23
------------------

Added
- 初期リリース: KabuSys のコア機能を追加。
  - 実行エントリ/ユーティリティ
    - run_execution.py: ExecutionEngine 起動スクリプト（プロセス優先度設定、PID/停止フラグ管理、DB 初期化、スレッド管理）。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（監視用 DB を使用、ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能）。
  - 環境・設定管理
    - config.py: Settings クラスによる環境変数ラップ。.env 自動読み込み（.env / .env.local、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
    - config_setup.py: .env を対話式に作成・更新するウィザード CLI（シークレットマスク、選択肢・デフォルト、.env への書き出し処理）。
    - validate_config.py: 起動前の設定検証 CLI。必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード等を実行。--strict モードで警告も失敗として扱う。
  - 発注関連コア
    - execution/execution_engine.py: Signal Queue Pull 型発注エンジン（シグナル処理窓、push ドレインループ、kill switch、リコンシリエーション呼び出し、監視 DB へのイベント記録）。
    - execution/order_record.py: OrderState 列挙と OrderRecord（不変性・状態遷移検証を含む純粋ビジネスロジック）。
    - execution/order_manager.py: OrderRecord と OrderRepository を組み合わせた外向き API。create/send/sync/cancel のワークフロー（2 相永続化、OrderSentPending/Rejected の扱い、DuplicateOrder 防止）。
    - execution/kabu_client.py: kabuステーション REST API クライアント（httpx 使用、トークン取得と自動再取得、401 リトライ、429 レート制限検出、エラー変換）。
    - その他: BrokerClientFactory, Reconciler, RiskManager など発注フローに必要なコンポーネント群（実装ファイルは本リリース範囲に含まれる）。
  - データベース・監視
    - DuckDB / SQLite を使用したデータ永続化。paper_trading 環境では本番監視 DB と分離して paper_trading 用 SQLite を使用する設計。
    - monitoring_db の初期化 util（init_monitoring_db）を run_* スクリプトで呼び出す。
  - ロギング・プロセス管理
    - setup_logging, set_process_priority などのユーティリティと統合済み。

Changed
- 環境変数読み込み・パースの強化（config._parse_env_line）
  - export KEY=val 形式に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープを正しく解釈。
  - クォートなしの場合のインラインコメント取り扱いを改良（'#' の直前がスペース/タブの場合のみコメントとみなす）。
- .env 自動読み込みロジック
  - プロジェクトルート探索を __file__ を基準に親ディレクトリを上向きに検索し、.git または pyproject.toml を基準に判定。配布後も CWD に依存せず動作するように改善。
  - OS 環境変数を protected として .env.local の上書きを保護する挙動を明確化。
- Settings のバリデーション強化
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値検証を Settings のプロパティ内で行い、無効値時は ValueError を送出するようにした（検証を早期に行い誤設定の混入を防止）。
- Execution / Monitoring の挙動改善
  - run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定するように変更。
  - run_execution: paper_trading 時は settings.paper_sqlite_path を使用して本番 DB と完全分離。
  - ExecutionEngine は起動時に kill.flag を検査し、KILL_FLAG_CLEAR_ON_START=1 時の自動クリア挙動をサポート。
  - ExecutionEngine のセッション制御（signal_send_start/end, market_close）や WebSocket プッシュ処理を明確化。
- 発注ワークフロー（OrderManager）
  - send_order の永続化手順を明確にし、クラッシュ耐性（OrderSent の DB 残存、broker_order_id の先コミット等）を確保。
  - sync_order は broker のステータス差分（filled_qty / price）だけの更新を最適化して適切に更新する。

Fixed
- .env 読み込みで I/O エラー時に警告を出すように改修（読み込み失敗時に warnings.warn）。
- config/*.yaml のパース検証は PyYAML が未インストールの場合にスキップし、警告を出すようにした（validate_config）。
- run_monitoring の MONITOR_POLL_INTERVAL が不正値（0 以下や非整数）の場合にデフォルト値にフォールバックし、警告するようにした（time.sleep に渡すと ValueError になる旨の対策）。
- OrderRecord.transition_to は updated_at を UTC 時間で自動設定するよう修正。

Security
- 環境設定ファイル (.env) は絶対に Git にコミットしない旨のヘッダコメントを config_setup の出力ファイルに追加。

Notes / ヒント
- 設定検証:
  - 起動前に python -m kabusys.validate_config を実行して設定状況を確認してください。--strict オプションで警告を FAIL 扱いにできます。
- 初期設定:
  - python -m kabusys.config_setup で .env を対話式に生成・更新できます。
- 本番運用時の注意:
  - KABUSYS_ENV=live 時は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値を慎重に確認してください。validate_config は live 時に追加のガードチェックを行います。
- テスト:
  - 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用に有用）。

今後の予定 (提案)
- broker_client の非同期実装 (httpx.AsyncClient) の追加検討。
- 設定検証の拡張（YAML スキーマバリデーション等）。
- 監視イベントのメトリクス export（Prometheus 等）。

--- 

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートが別途存在する場合は、それらに合わせて調整してください。