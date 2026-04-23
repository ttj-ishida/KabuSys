# Changelog

すべての notable な変更を記録します。  
このファイルは Keep a Changelog の形式に従います。  
<https://keepachangelog.com/ja/1.0.0/>

## [Unreleased]

## [0.1.0] - 2026-04-23

初期リリース

### 追加
- 基本アプリケーション情報
  - パッケージメタ情報を `src/kabusys/__init__.py` に追加（__version__ = 0.1.0）。
- 環境/設定管理
  - .env ファイルの自動ロード（プロジェクトルートを .git / pyproject.toml で探索）を実装。
    - OS 環境変数を保護する仕組み（protected keys）を持つ読み込み順序: OS 環境 > .env.local > .env。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env 行パーサーを実装（クォート、エスケープ、インラインコメント、export 形式対応）。
  - `Settings` クラスを実装し、アプリケーション設定を環境変数から取得するプロパティ群を提供（トークン、API パスワード、DB パス、監視閾値、環境判定等）。
  - `config_setup` CLI（対話式ウィザード）を追加:
    - `.env` の初期作成・更新を対話形式で支援。
    - セクション分けされたテンプレート出力とシークレットマスク表示、保存確認。
- 設定検証ツール
  - `validate_config` CLI を追加:
    - 必須環境変数の存在チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性検査。
    - DB パス（DuckDB / SQLite）の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML がある場合）パース検証。
    - `--strict` フラグで警告も失敗扱いにできる。
    - 本番（KABUSYS_ENV=live）向けガード（LINE 通知設定や Kill Flag の自動クリア設定の警告）。
- 実行スクリプト
  - `run_execution` スクリプトを追加:
    - `ExecutionEngine` の起動処理（プロセス優先度設定、DB 接続、PID 書き出し、停止フラグ検出）。
    - paper_trading 環境では専用の SQLite DB を使用して本番 DB と分離。
    - スレッドによる実行と停止フラグ検出のループ管理。
  - `run_monitoring` スクリプトを追加:
    - `SystemMonitor` のポーリングループ（デフォルト 60 秒、環境変数 `MONITOR_POLL_INTERVAL` により上書き可能）。
    - 監視プロセスは環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検出とリソースクリーンアップ（DB クローズ）を実装。
- 発注（Execution）サブシステム
  - `ExecutionEngine` を実装:
    - シグナル処理フェーズ（8:50-9:10）と push ドレイン（9:10-15:30）をサポート。
    - kill.flag の扱い（起動時の拒否または自動クリア）と PID ファイル管理。
    - WebSocket push を受けて内部キューへ投入するワーカーを実装（broker が stream_push を持つ場合）。
    - Gate 1/2/3 によるリスクチェック（シグナル・実行・ドローダウン）を統合し、NG 時にはログ出力や kill_switch を発動。
    - 発注時のレート制限リトライ、pending（OrderSentPendingError）ハンドリング、発注レイテンシの監視 DB ログ記録。
    - DuckDB を使った position_entries の記録（約定日扱いのロジック）。
  - `OrderManager` を実装:
    - signal_id 重複検査（DB の部分ユニーク制約と整合）と DuplicateOrderError の導入。
    - 発注の二相永続化（OrderSent に遷移してコミット → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）によるクラッシュ耐性の向上。
    - send_order / sync_order / cancel_order の各操作の実装（Broker API 例外ハンドリング含む）。
  - `OrderRecord`（状態遷移モデル）を実装:
    - 明確な状態列挙と遷移可能性を定義（InvalidStateTransitionError を送出）。
    - updated_at の自動更新、オプションフィールド更新（broker_order_id, filled_qty, avg_fill_price, error_message）。
  - Reconciler / RiskManager 等と連携するためのフックを用意（ExecutionEngine のコンストラクタ引数で注入可能）。
- ブローカークライアント
  - `KabuStationClient` を実装（httpx を利用した同期クライアント）:
    - トークン取得の遅延初期化と 401 に対するトークン再取得の自動リトライ。
    - レスポンス JSON パース失敗を BrokerAPIError に変換、429 を RateLimitError として扱う。
    - WebSocket push 用に `stream_push` を持つ実装を想定。
- 監視関連
  - monitoring 初期化ロジック（`init_monitoring_db`）や `SystemMonitor` の起動に対応。
- ユーティリティ
  - 簡易なプロセス優先度設定やログセットアップ（各ランナーで利用）。

### 変更
- 設定のバリデーションと Settings の整合性強化:
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを Settings プロパティと validate_config の両方で実装し、一貫性を確保。
  - PAPER_FILL_MODE の検証（有効値チェック）を Settings に実装し、不正値時は ValueError を raise。

### 修正
- .env の柔軟なパース実装により以下に対応:
  - export 付き行、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いを改善。
- 発注フローのクラッシュ耐性を向上:
  - OrderSent 状態の永続化タイミングと broker_order_id の先にコミットする設計で、再照合（Reconciliation）からの回復を容易に。
- run_monitoring / run_execution の終了処理で DB 接続を確実にクローズするように修正。
- モニタリング DB への書き込み失敗はエラーにせずログ警告に留め、発注フローを継続するようにハンドリング。

### 既知の制限（注意点）
- PyYAML がインストールされていない場合、`validate_config` は config/*.yaml の内容検証をスキップし、警告を出します。
- `KabuStationClient` の WebSocket や一部 Broker API の挙動は実環境の kabu station アプリに依存します。
- `Settings` の自動ロードはプロジェクトルートの検出に依存するため、配布後や特殊な配置では自動ロードがスキップされる可能性があります（その場合は手動で環境変数を設定してください）。
- 一部のエラーは設計上ビルド・運用時に明示的に投げられる（ValueError / RuntimeError など）。ユニットテストや運用オペレーションで適切にハンドルしてください。

---

もし特定の変更点について詳細（実装上の意図、使い方、設定例、既知バグの再現手順など）を追記希望があれば教えてください。