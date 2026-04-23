CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

(なし)

0.1.0 - 2026-04-23
------------------

Added
- 初回リリース。KabuSys 自動売買フレームワークの基本機能を追加。
- 設定管理
  - Settings クラスを導入。環境変数から各種設定（API トークン、DB パス、LINE トークン、ログレベルなど）を取得。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。OS 環境変数が優先され、.env.local による上書きをサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションあり。
  - .env パースの堅牢化: export プレフィックス、シングル/ダブルクォート内のエスケープ、行内コメントの扱いなどを正しく処理。
  - Settings のプロパティで値の検証を行い、不正値は例外で通知（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- 対話式セットアップ
  - config_setup.py による .env 作成／更新ウィザードを追加。対話的プロンプト、選択肢、シークレットマスク表示、.env の書き出しを提供。
- 設定検証 CLI
  - validate_config.py を追加。起動前に .env と config/*.yaml の不足や不整合を検出（必須環境変数確認、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パス／親ディレクトリ確認、YAML パースチェック（PyYAML が未インストールの場合は警告））。
  - --strict モードを追加。警告を FAIL として exit(1) を返す。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。paper_trading 環境用に本番 DB と分離した SQLite（paper_trading DB）を使用。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL によるポーリング間隔上書きに対応。
  - 両スクリプトともプロセス優先度設定、ログ設定、DB 初期化のフローを備える。
- 発注エンジン（Execution）
  - ExecutionEngine 実装を追加。シグナル読み込み（DuckDB）、Gate1/Gate2（シグナル・エグゼキューション検査）、発注処理、WebSocket push ドレインループ（push を受けての同期・Gate3 チェック）を含むセッション制御（8:50→9:10→15:30 の流れ）。
  - セッション開始時のリコンシリエーション呼び出し、kill.flag の扱い（KILL_FLAG_CLEAR_ON_START による自動クリアオプション）、PID ファイル出力・削除を実装。
  - position_entries への書き込み（発注成功時にエントリー/クローズ日を記録）をサポート。
- 注文状態管理（OrderRecord / OrderManager）
  - OrderRecord: 純粋な状態遷移ロジックを持つデータモデルを追加。明示的な状態列挙（created/sent/accepted/partial/filled/closed/cancelled/rejected）と許可遷移を定義。遷移検証で InvalidStateTransitionError を投げる。
  - OrderManager: DB（OrderRepository）と Broker API を組み合わせた外向き API を実装。create/send/sync/cancel の一連の処理フローを定義。DuplicateOrderError による重複検出を実装。
  - send_order のクラッシュ安全設計：OrderSent を永続化→broker 呼び出し→broker_order_id を先に永続化→OrderAccepted へ遷移、という 2 相永続化でリコンシリエーション耐性を考慮。
  - OrderSentPendingError の取り扱い（broker が order_id を返して pending となるケース）を実装し、DB に broker_order_id を残して再送/再照合可能に。
  - sync_order により broker 側の状態を照合して部分約定や全約定を反映。状態遷移制約に基づく補正（OrderSent→Filled 等の場合は OrderAccepted を経由）に対応。
  - cancel_order はキャンセル不可能な状態を弾くロジックを追加（Filled を含む）。
- ブローカークライアント（kabu station）
  - KabuStationClient を追加（httpx を利用した同期 REST クライアント）。トークン取得・自動再取得、HTTP レスポンスの JSON パース、401 リトライ、429 (rate limit) と 5xx のハンドリング、タイムアウト/ネットワーク例外の BrokerAPIError 変換を実装。
  - WebSocket push の受け口（stream_push）を想定した設計で、ExecutionEngine の WS スレッドと連携可能。
- モニタリング
  - run_monitoring と監視 DB 初期化（init_monitoring_db）を使った監視ループを追加。監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
  - 発注時の監視ログ（latency 等）を MonitoringDB に記録するフックを提供（監視 DB が設定されている場合）。
- リスク管理 / ガード
  - ExecutionEngine と RiskManager 間の Gate1/Gate2/Gate3 による多段防御を実装（シグナルレベル検査、エグゼキューションレベルのレート制御・サーキットブレーカー、ポートフォリオドローダウン監視によるキルスイッチ）。
  - キルスイッチ（kill_switch）により全 active 注文のキャンセルとループ停止を行うロジックを提供。
- その他ユーティリティ
  - .env ファイルの読み書きヘルパー（config_setup.py 内）と、.env の既存値読み込み機能。
  - ロギングセットアップ、プロセス優先度設定ユーティリティとの統合呼び出しを各起動スクリプトで実行。
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として追加。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 機密値（API トークン等）は対話式ウィザードでマスク表示。.env 生成時に Git へのコミットを行わない旨の注意を .env ヘッダに明記。

Notes / Known limitations
- YAML 検証は PyYAML に依存。未インストール時は YAML 内容検証をスキップ（警告）。
- KabuStationClient の一部レスポンス処理や API パスは実際の kabu station の挙動に依存するため、実運用前に接続先での動作確認を推奨。
- 一部モジュール（OrderRepository、BrokerAPI の具象実装、MonitoringDB 実装等）はこの変更履歴の対象コード外に依存するため、統合テストでの確認が必要。

---- 

今後のリリースでは、テストカバレッジの拡充、async 対応（httpx.AsyncClient）、さらに細かな監視メトリクスや UI/ドキュメントの追加を予定しています。