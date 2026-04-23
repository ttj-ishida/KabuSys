# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。

## [0.1.0] - Unreleased
初回リリース。本リリースでは自動売買システム「KabuSys」の基礎となる設定管理、起動スクリプト、発注エンジン、注文状態管理、kabu station クライアント、監視用ループなどを実装しました。

### 追加
- 設定検証 CLI を追加（src/kabusys/validate_config.py）
  - .env と config/*.yaml の存在・基本的妥当性を起動前にチェック。
  - 必須/任意の環境変数チェック、プレースホルダ検出、LOG_LEVEL / KABUSYS_ENV の妥当性検査を実施。
  - --strict オプションで警告を失敗扱いにできる。
  - PyYAML が存在する場合は YAML ファイルのパース検証を行い、存在しない場合はスキップして警告を出す。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）を追加。

- 環境設定ウィザードを追加（src/kabusys/config_setup.py）
  - 対話式で .env を新規作成 / 更新する CLI。
  - シークレット値のマスク表示、選択肢・デフォルト表示、Enter による既存値再利用をサポート。
  - 保存前の確認表示、.env テンプレート書き込みを行う。

- 設定管理モジュールを追加（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能（OS 環境変数は保護し上書き回避）。
  - .env の高度なパース実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、コメント取り扱い）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスを導入し、各種設定値（トークン・パスワード・DB パス・PID/kill flag 等）をプロパティ化。
  - PAPER_FILL_MODE 等の値検証を実装（不正値は ValueError）。

- 実行/監視用エントリポイントを追加
  - run_execution: ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - paper_trading 時は専用 SQLite（paper_trading.db）を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル書き出し、停止フラグ検知、スレッド管理。
  - run_monitoring: SystemMonitor ポーリングループ（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。

- 注文状態モデル・状態遷移ロジックを追加（src/kabusys/execution/order_record.py）
  - OrderState enum と許可遷移テーブルを実装。
  - OrderRecord dataclass と transition_to() による遷移検証（不正遷移は例外）。
  - DB へ依存しない純粋ビジネスロジックとして実装。

- 注文管理 API を追加（src/kabusys/execution/order_manager.py）
  - create_order / send_order / sync_order / cancel_order を実装。
  - DuplicateOrderError による同一 signal_id の重複検知。
  - send_order での 2 相永続化戦略を導入（OrderSent の永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted）。
  - OrderSentPendingError の取り扱い（broker_order_id を保持して pending として残す）に対応。
  - sync_order で broker 側ステータスを反映、部分約定の進行に伴う個別フィールド更新を考慮。

- 発注エンジンを追加（src/kabusys/execution/execution_engine.py）
  - Signal Queue Pull 型発注フローを実装（シグナル処理窓 8:50-9:10、push ドレイン 9:10-15:30）。
  - Gate1/2/3 によるリスクチェックフローを組み込み（signal チェック、実行時レート制限、ポートフォリオ指標によるドローダウン監視）。
  - kill_switch により全 active 注文をキャンセルしエンジン停止。
  - WebSocket (push) を受けて _push_queue に入れ、sync_order と Gate3 評価を行う。
  - 発注後に position_entries へ約定予定日（翌営業日）を書き込む処理を実装（DuckDB 使用）。
  - 監視 DB への発注イベント記録（MonitoringDB が提供されている場合）。

- kabu station REST クライアントを追加（src/kabusys/execution/kabu_client.py）
  - KabuStationClient を実装（httpx を使用、将来の async 対応を想定）。
  - トークン取得の遅延初期化と 401 時の自動再取得・1回リトライを実装。
  - HTTP タイムアウト / ネットワーク例外の BrokerAPIError への変換、429（レート制限）を RateLimitError として扱う。
  - websocket による push 受信（stream_push）を想定した設計。

- 監視関連ユーティリティ追加
  - monitoring_db 初期化関数（init_monitoring_db）呼び出しを run_monitoring/run_execution で保証。
  - MonitoringDB 経由で発注イベントを記録するフックを ExecutionEngine に追加。

- ユーティリティ
  - process_priority 設定ユーティリティを利用してプロセス優先度を高める呼び出しを run_* スクリプトで行う。
  - ロギングセットアップ呼び出し（setup_logging）を各起動スクリプトで行う。

### 変更
- .env 読み込み順序の規定
  - 読み込み優先順位を OS 環境 > .env.local > .env と明示し、OS の既存キーは保護されるようにした（src/kabusys/config.py）。
- paper_trading モードの取り扱い
  - paper_trading 時は paper_trading 専用 SQLite を使い、本番データベースと分離（run_execution / Settings）。

### 修正（設計上の改善）
- 発注フローのクラッシュ耐性を向上
  - send_order において broker 呼び出し前に OrderSent を永続化し、broker_order_id の永続化を行うことでクラッシュ時の再同期性を改善（Reconciliation を想定）。
- .env パーサーの堅牢性を強化
  - export プレフィックス、クォート内のエスケープ、コメント認識などに対応（src/kabusys/config.py）。
- ExecutionEngine の再起動時の kill.flag 処理を強化
  - KILL_FLAG_CLEAR_ON_START により起動時に kill.flag を自動クリアする挙動をオプション化（Settings.kill_flag_clear_on_start）。

### 既知の問題 / 注意点
- 一部機能は外部ライブラリ（PyYAML, httpx, websocket, duckdb 等）に依存します。環境によってはインストールが必要です。
- Settings のプロパティは未設定の場合に ValueError を投げます。起動前に .env を正しく設定してください（config_setup と validate_config を推奨）。
- KabuStationClient は kabuステーション® アプリがローカルで稼働していることを前提としています。

---

今後の予定（例）
- テストカバレッジの強化（ユニットテスト / 統合テスト追加）
- 非同期対応や httpx.AsyncClient / asyncio ベースの push 処理の追加検討
- Reconciler の詳細実装と手動/定期リコンシリリエーションの UI
- 監視・アラートの強化（LINE 通知等の実装とテスト）

以上。