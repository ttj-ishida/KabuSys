CHANGELOG
=========

すべての変更点はセマンティックバージョニングに従います。以下はリポジトリに含まれる機能・挙動をコードから推測して記載した初版の変更履歴です。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-23
------------------

Added
- 初期リリース: KabuSys のコア機能を実装
  - パッケージエントリポイントとバージョン情報を追加（__version__ = "0.1.0"）。
- 環境変数 / 設定管理
  - Settings クラスを追加し、環境変数から各種設定を取得する統一インターフェースを提供。
  - J-Quants / kabuステーション / LINE / DB /監視 /システム設定など多数のプロパティを実装。
  - PAPER_FILL_MODE 等の値検証（有効値チェック）を実装。
  - .env 自動読み込み機能を追加（プロジェクトルート探索: .git または pyproject.toml を基準）。
  - .env 読み込みの優先度: OS 環境 > .env.local > .env。OS 環境を保護する protected オプションを導入。
  - .env パーサを実装（export プレフィックス対応、クォート／バックスラッシュエスケープ対応、インラインコメント処理など）。
- 環境設定ウィザード CLI
  - config_setup.py に対話式ウィザードを追加。.env の初期作成・更新を支援。
  - シークレット項目は表示時にマスク、選択肢・デフォルト・説明をサポート。
  - .env の読み込み／確認／保存ロジックを実装。
- 設定検証 CLI
  - validate_config.py を追加。起動前に .env および config/*.yaml の設定不備を検出。
  - 必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DBパスの親ディレクトリ存在確認を実装。
  - PyYAML が存在する場合は config/*.yaml のパース検証を行い、未インストール時はスキップして警告を出力。
  - --strict オプションで警告を FAIL として扱う機能を実装。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。
- 実行系スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。paper_trading モードでは専用 SQLite を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。監視は常に本番 sqlite_path を使用。
  - PID ファイル／停止フラグ（stop_requested.flag / kill.flag）を用いた起動制御を実装。
  - プロセス優先度を設定するユーティリティ呼び出しを利用（set_process_priority）。
  - 起動時のログ設定（setup_logging）呼び出しを追加。
- 発注エンジンと注文管理
  - ExecutionEngine を実装（signal queue 型発注エンジン、シグナル処理時間帯管理、WebSocket push ドレインループ、セッション管理）。
  - シグナル処理と発注フローにおける Gate チェック（Gate1: signal、Gate2: execution/rate limit、Gate3: ドローダウン監視）を実装。NG 時には kill_switch を発動。
  - kill_switch により全 active 注文をキャンセルし、ループを停止する安全機構を実装。
  - OrderRecord: 注文状態（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）を列挙する状態機械と遷移検証を実装。InvalidStateTransitionError を定義。
  - OrderManager: create_order / send_order / sync_order / cancel_order を実装。2相永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）によりクラッシュ回復性を向上。
  - DuplicateOrderError の導入（同一 signal_id の active 注文の重複防止）。DB の部分ユニークインデックス違反からの変換処理を実装。
  - send_order における OrderRejectedError / OrderSentPendingError の取り扱いを実装（pending の場合は broker_order_id を保存して OrderSent のまま残す）。
  - sync_order は broker 側ステータスを元に状態同期し、部分約定の進行は個別フィールド更新で処理。
  - 発注成功時に position_entries へ約定予定日を書き込む処理（DuckDB を使用）。例外が発生しても発注フローは継続。
  - 発注時のモニタリング DB へのイベント記録機能を組み込み（存在する場合）。
- ブローカークライアント
  - KabuStationClient を実装（httpx を用いた同期 REST クライアント）。
  - トークンの遅延取得と自動再取得、401 リトライロジック、JSON パース検証、HTTP エラー種別の変換（RateLimitError / BrokerAPIError など）を実装。
  - WebSocket push 受信（stream_push）をサポートするインターフェースを想定。
- モニタリング
  - run_monitoring から SystemMonitor を用いたポーリングループを実行し、SQLite / DuckDB を用いて監視データを管理する仕組みを追加。
- ドキュメント／メッセージ
  - CLI ヘルプやログメッセージ、.env 生成ヘッダなどユーザー向けメッセージを充実。

Changed
- （初版につき該当なし）

Fixed
- 起動時の kill.flag による誤起動対策を導入。KILL_FLAG_CLEAR_ON_START 環境変数により起動時クリアを明示的に許可できるようにした（本番では 0 を推奨）。
- MONITOR_POLL_INTERVAL の不正値に対するフォールバック処理を実装（0 や負数、非整数入力でデフォルト 60 秒に戻す）。

Security
- .env ファイルについて明示的に "絶対に Git にコミットしないこと" を .env 生成ヘッダに記載。

Removed
- （初版につき該当なし）

Notes / 今後の想定改善点（コードから推測）
- async 対応: KabuStationClient を httpx.AsyncClient に置き換えることで非同期化が容易。
- テスト用フックやモックの整備: BrokerAPIProtocol を利用した単体テスト用のモック整備でテスト容易性を向上可能。
- config/*.yaml のスキーマ検証を追加（PyYAML に加え JSON Schema 等を使った内容検証）。
- 設定検証の出力をマシン可読（JSON）にするオプション追加。

以上。コードから推測して主要な追加機能と注意点をまとめました。必要であれば、各ファイルごとの変更点や開発履歴（コミット単位での想定差分）も作成します。