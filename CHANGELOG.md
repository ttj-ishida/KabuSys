# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
注: この CHANGELOG はソースコードから推測して作成しています。

## [0.1.0] - 2026-04-23

### Added
- 初期リリース: KabuSys 日本株自動売買システムのコア機能を追加。
- 設定・起動関連
  - 環境変数/設定の自動読み込み機能を追加（プロジェクトルートの .env / .env.local を読み込む）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - Settings クラスを追加し、環境変数からアプリケーション設定を一元取得可能に。
  - 対話式の環境設定ウィザード (kabusys.config_setup) を追加して .env の作成・更新を支援。対話入力、既存値の再利用、シークレットマスク表示、.env のテンプレート出力をサポート。
  - 設定検証 CLI (kabusys.validate_config) を追加。必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パース確認、KABUSYS_ENV=live 時の追加ガードを実行。--strict オプションで警告もエラー扱いに。
- 実行スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。paper_trading 時は専用の paper DB を使用して本番 DB と分離。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 実行エンジン / 発注フロー
  - ExecutionEngine を追加。シグナルの読み込み（DuckDB）→ Gate1/Gate2 による検査 → 発注 → push ドレインループの処理を実装。セッションタイミング（signal_send_start/ end、market_close）をサポート。
  - OrderRecord: 発注状態遷移を表す状態マシンと transition_to メソッドを追加（不正遷移は例外）。
  - OrderManager: 注文生成(create_order)、送信(send_order)、ブローカーとの同期(sync_order)、キャンセル(cancel_order) を実装。DuplicateOrder の検出、クラッシュ耐性を考慮した永続化順序を実装。
  - Broker クライアント抽象（broker_api を参照）と具体実装のファクトリを組み合わせて利用する設計を導入。
  - Reconciler（起動時リコンシリエーション呼び出し）を ExecutionEngine に統合。
- ブローカー実装
  - KabuStationClient を追加（httpx を利用した同期 REST クライアント）。トークン管理（遅延取得・401 時の再取得）・レスポンス JSON パースラップ・ステータスコード別例外（429=RateLimit）などを実装。WebSocket push の受信（stream_push）を受け入れる設計。
- モニタリング / DB
  - 監視用スクリプトは sqlite（監視 DB）と duckdb の両方に接続して監視を実行。init_monitoring_db によるテーブル初期化を行う。
- ユーティリティ
  - .env パーサーの実装（クォート・エスケープ・コメント処理対応）を追加。
  - PID/stop flag によるプロセスの起動制御、KILL_FLAG_CLEAR_ON_START オプションを追加。
  - process_priority の設定やログ設定（setup_logging）を起動時に実行するフローを追加。

### Changed
- 設定のデフォルトと挙動を整理
  - DB パス、ログレベル、kabu API のデフォルト URL などを Settings に明示化。
  - paper_trading モードでは paper_trading 用 SQLite を使用するように Execution/run logic を分離。
- 発注の耐障害性を改善
  - send_order にて broker_order_id を先に永続化し、その後状態遷移を行う「2相的」永続化手順を導入。これによりクラッシュ後のリコンシリエーションで状態復旧しやすくなった（Issue #32 に言及）。
- ExecutionEngine の挙動
  - kill.flag の検査と KILL_FLAG_CLEAR_ON_START の扱いを明確化。起動時に kill.flag が存在する場合の起動拒否や、自動クリアの挙動を導入。
  - push メッセージ処理で見つからない push でもポートフォリオ評価（Gate3）を行い、スプリアス push による検出漏れを減らす設計に変更。
- 設定検証の報告
  - validate_config の出力で INFO/WARNING/ERROR を整理。PyYAML がない場合は YAML 検証をスキップして警告する。

### Fixed
- 環境読み込みの堅牢性向上
  - .env 読み込み時にファイル読み込み失敗で警告を出すように変更（権限エラー等を隠さない）。
  - .env のパースでクォート内のバックスラッシュエスケープを正しく扱うように実装。
- 発注周りの不整合を防止
  - DuplicateOrder の検出を DB 制約違反（orders.signal_id のユニーク部分インデックス）から適切に変換して通知するよう修正。
  - sync_order において、OrderSent → Filled/PartialFill へ直接遷移できない場合は一旦 OrderAccepted を経由することで整合性を保つ処理を追加。
- 監視・DB 接続のクローズ漏れを防止
  - run_monitoring/run_execution で最終的に sqlite と duckdb の接続を必ずクローズするように finally ブロックを用いて保護。

### Security
- .env に関する注意喚起を config_setup のヘッダに追加（.env を Git にコミットしないよう明示）。

### Internal / Misc
- パッケージメタ情報としてバージョンを設定: __version__ = "0.1.0"
- ロギング・例外メッセージをわかりやすく調整（各モジュールで logger を活用）。
- 実行スクリプト・モジュールに CLI 用 main 関数を提供。モジュールを直接実行可能。

---

注記:
- この CHANGELOG はコードベースからの推測に基づいて作成されています。実際のコミット履歴や設計意図とは異なる可能性があります。必要があれば、改めて実コミットやリリースノートに合わせて調整してください。