# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

最新: Unreleased / 0.1.0 を含む初期リリース記録を作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

初期リリース（ベースライン実装）。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### 追加 (Added)
- パッケージ基本情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 設定管理
  - Settings クラスを実装し、環境変数から各種設定（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、KABUSYS_ENV、LOG_LEVEL 等）を取得可能に。
  - .env 自動読み込み機構を実装（プロジェクトルートを .git / pyproject.toml で検出）。読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化できるオプションを追加。
  - .env のパースを強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォート無し行のインラインコメント処理（直前が空白/タブの場合のみコメントと見なす）。

- 設定ウィザード CLI
  - config_setup ウィザードを実装（python -m kabusys.config_setup）。
  - 対話形式で .env を作成・更新可能。必須・任意項目、シークレット項目のマスク表示、選択肢サポートを提供。
  - .env を生成する際のテンプレート書き込み（.env 内にコメント・注意書きを出力）。.env を Git にコミットしない旨を明記。

- 設定検証 CLI
  - validate_config CLI を実装（python -m kabusys.validate_config）。
  - .env と config/*.yaml の起動前検証を実行。必須環境変数未設定の検出、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config YAML ファイル存在・パース検証（PyYAML がインストールされている場合）を実施。
  - --strict オプションで警告を FAIL（exit code 1）扱いにできる。

- 実行スクリプト
  - run_execution（python -m kabusys.run_execution）を用意。ExecutionEngine の起動処理をまとめ、paper_trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用するよう分離。
  - run_monitoring（python -m kabusys.run_monitoring）を用意。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用し、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能。

- 実行エンジンと発注ロジック
  - ExecutionEngine を実装（シグナル処理 + push ドレイン）。シグナル処理時間帯（デフォルト 8:50-9:10）やセッション終了時刻を設定可能。
  - EngineConfig により target_date 等を指定可能。
  - WebSocket push 用ワーカー実装（broker が stream_push を持つ場合に起動）。
  - push 通知を受けて sync_order などを行う仕組みを追加。
  - PID ファイル / stop フラグ / kill.flag を使った起動制御を実装。KILL_FLAG_CLEAR_ON_START による起動時自動クリア挙動をサポート。

- 注文管理と状態機械
  - OrderRecord クラスを実装。OrderState 列挙と許可遷移テーブルを定義し、遷移検証（InvalidStateTransitionError）を行う。
  - OrderManager を実装。create_order / send_order / sync_order / cancel_order を提供し、DB（OrderRepository）と OrderRecord を組み合わせた外向き API を実現。
  - DuplicateOrderError による同一 signal_id の二重発注防止。
  - send_order に二相永続化（OrderSent 永続化 → ブローカー呼び出し → broker_order_id 永続化 → OrderAccepted 永続化）を導入し、クラッシュ後のリカバリ（reconciliation）を容易にする設計を採用。
  - OrderSentPendingError の取り扱いを実装（注文番号はあるが約定しない等の pending 状態を DB に保存し、呼び出し元へ伝播）。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（httpx を使用した同期 REST クライアント）。
  - トークン管理（遅延初期化、401 時の再取得とリトライ）、HTTP エラーを BrokerAPIError / RateLimitError 等に変換。
  - WebSocket（push）処理は別途 broker 側で stream_push を提供することで連携する設計。

- リスク管理 / レート制御 / Gate チェック
  - ExecutionEngine 側で Gate1（シグナルレベル）、Gate2（エグゼキューションレベル、レート制限、サーキットブレーカー）、Gate3（ポートフォリオ指標チェック → kill_switch）を実装/呼び出し。
  - RiskManager と連携し API 成功/失敗の統計を記録。

- 監視関連
  - MonitoringDB 用初期化と SystemMonitor のポーリングループを提供。
  - 発注イベントを監視DBへログするエントリ（log_trade_event）を ExecutionEngine の発注フローで利用できるよう追加（監視 DB が提供されている場合）。
  - run_monitoring にて stop flag 検出でループ終了。

- DB 関連
  - DuckDB（分析用）と SQLite（監視・注文履歴用）を併用。paper_trading 時に監視 DB を切り替えて本番 DB と分離する設計。
  - DuckDB へ position_entries を書き込むロジック（fill_date は翌営業日）を導入。

- ユーティリティ
  - .utils 配下に logging_setup, process_priority 等のヘルパーを利用する起動フローを採用（起動時にプロセス優先度を設定、ログ設定を初期化）。

### 変更 (Changed)
- （初版のためなし）

### 修正 (Fixed)
- （初版のためなし）

### 削除 (Removed)
- （初版のためなし）

### 廃止予定 (Deprecated)
- （初版のためなし）

### セキュリティ (Security)
- .env は絶対にリポジトリへコミットしないことを .env 生成テンプレートに明記（セキュリティ注意）。

---

## 既知の制約 / 注意点
- PyYAML がインストールされていないと config/*.yaml の内容検証はスキップされます（validate_config で警告）。
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布パッケージ等では KABUSYS_DISABLE_AUTO_ENV_LOAD を指定して挙動を制御してください。
- KabuStationClient は同期 httpx.Client を利用。将来的に非同期化する場合は httpx.AsyncClient へ置き換える方針を想定。
- kill.flag / PID ファイル操作はファイルシステムを使用するため、配置パスのパーミッション等に注意してください。
- ログレベル・KABUSYS_ENV 等の不正値は Settings のプロパティ参照時に ValueError を投げます。validate_config で事前チェックしてください。

---

（注）本 CHANGELOG は与えられたコードベースから実装内容を推定して作成しています。追加の変更履歴やリリースノートが存在する場合は適宜統合してください。