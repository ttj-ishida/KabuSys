# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
この CHANGELOG は提供されたソースコードから機能・変更点を推測して作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （現時点の開発中の変更をここに列挙してください）

## [0.1.0] - 2026-04-22
初回公開推定バージョン。以下はコードベースから推測される主要な追加点・動作仕様です。

### Added
- 基本構成・環境管理
  - Settings クラスを導入し、環境変数からアプリケーション設定を取得する仕組みを実装。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env 自動読み込み機能を実装（.env, .env.local）および KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプション。
  - .env ファイルのパース機能を細かく実装（export プレフィックス対応、シングル/ダブルクォート、インラインコメント処理、エスケープ処理）。

- 環境設定ウィザード（CLI）
  - config_setup モジュールで対話式ウィザードを実装。
  - .env の読み込み・既存値の再利用・対話入力・バリデーション（選択肢チェック）・書き出し機能を提供。
  - デフォルト値・シークレット表示（マスク）・オプション項目対応。
  - 保存確認プロンプトと、保存後の次の手順案内を実装。

- 設定検証ツール（CLI）
  - validate_config モジュールで起動前に環境変数や config/*.yaml の不備を検出する CLI を実装。
  - 必須/任意の環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性検査、プレースホルダ値の検出（例: *_here / your_value）。
  - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック（警告）。
  - PyYAML が無い場合は YAML 検証をスキップする挙動と、ファイルのパースエラーを検出してエラー扱いにする機能。
  - --strict オプションで警告を失敗として扱うモードを追加。

- 実行エントリポイント
  - run_execution: ExecutionEngine 起動スクリプトを実装。paper_trading 時は専用 SQLite（paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数により間隔を上書き可能。

- Execution（発注）コア
  - ExecutionEngine を実装。シグナル読み込み（DuckDB）→ Gate チェック → 発注 → push ドレインの一連のセッション制御を提供。
  - EngineConfig で target_date / 発注時間帯 / セッション終了時刻などを設定可能に。
  - kill.flag / PID ファイルの取り扱い（起動拒否、起動時自動クリア設定）を実装。
  - WebSocket push の受信を別スレッドで行い、受信 payload をキュー経由で処理する仕組みを追加。
  - セッション起動時に Reconciler を呼び出してリコンシリエーションを実行する仕組みを実装（存在する場合）。

- Order 管理
  - OrderRecord: 注文状態遷移を表す状態マシン（OrderState）と遷移検証ロジックを実装。許可される遷移テーブルを定義。
  - OrderManager: OrderRecord と OrderRepository（SQLite）を組み合わせた外向け API を実装（create_order / send_order / sync_order / cancel_order）。
  - send_order の二相永続化（OrderSent を永続化 → broker 呼び出し → broker_order_id を先に保存してから OrderAccepted に遷移）によりクラッシュ時の回復性を向上。
  - OrderSentPendingError の扱い（注文番号は保存するが OrderSent のまま残す）に対応。
  - DuplicateOrderError を導入し、同一 signal_id の active 注文を防止。
  - sync_order による broker 側ステータスからの同期処理（部分約定の更新、状態遷移の安全化）を実装。
  - cancel_order はキャンセル不可状態をチェックして Broker API 呼び出し → Cancelled へ遷移。

- Risk / Gate / Monitoring 連携（エンジン側）
  - Gate1（シグナルレベル）/ Gate2（実行レート制限、サーキットブレーカー）/ Gate3（ドローダウン監視）を通す設計を実装。
  - レート制限でリトライを行い、Circuit Breaker 発動時は適切にループ停止。
  - 発注イベントを monitoring DB にロギングするフックを実装。

- Broker クライアント（kabu station）
  - KabuStationClient を実装（httpx Client を使用する同期版）。
  - API トークンの遅延初期化と 401 発生時のトークン再取得 + リトライを実装。
  - HTTP エラー（401/429/5xx）に応じた専用例外（RateLimitError, BrokerAPIError 等）を投げる。
  - WebSocket push（stream_push）を持つブローカーに対して WebSocket を利用する仕組みを想定（push のハンドリングを ExecutionEngine が行う）。

- DB / 初期化
  - monitoring 用 SQLite と分析用 DuckDB の接続をそれぞれ使用する設計。監視 DB の初期化関数 init_monitoring_db を呼ぶ実装を追加。
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する旨の仕様。

- ユーティリティ
  - プロセス優先度調整（set_process_priority）やログ初期化（setup_logging）を各起動スクリプトで利用。

### Changed
- N/A（初回リリースに相当するため、過去からの変更点はなしと推定）

### Fixed
- N/A（初回リリースに相当するため、バグ修正履歴はなしと推定）

### Security
- .env を絶対に Git にコミットしない旨を README/生成ファイルの注釈に記載（config_setup の書き出しヘッダに明記）。

### Notes / 実装上の重要点（運用上の注意）
- .env の自動ロードは OS 環境変数を保護する（protected set）。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すること。
- validate_config は PyYAML が無ければ YAML 内容検証をスキップするが、ファイルの存在は警告する。
- ExecutionEngine と OrderManager はクラッシュ安全性（2相永続化）やリコンシリエーションを意識した設計になっているため、運用時は定期的に reconcile を監視すること。
- KABUSYS_ENV=live の場合、validate_config と Settings は本番向けの注意喚起や追加チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START）を行う。

---

（注）この CHANGELOG は提供されたソースコードの内容から推測して作成しています。細かい挙動や実際の変更履歴はコミットログやリリースノートをご確認ください。