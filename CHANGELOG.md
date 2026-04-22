# CHANGELOG

すべての注目すべき変更をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

全般:
- バージョニングは SemVer を想定しています。
- このリリースはパッケージの最初の公開相当の内容をまとめたものです（__version__ = 0.1.0）。

## [0.1.0] - 2026-04-22

### 追加
- 基本アプリケーションパッケージを追加（kabusys）。
  - src/kabusys/__init__.py にバージョン情報と公開モジュール一覧を追加（__version__ = "0.1.0"）。
- 環境・設定管理
  - Settings クラスを追加して環境変数から設定を一元管理（src/kabusys/config.py）。
    - 必須/任意の設定（J-Quants トークン、kabu API パスワード、DB パス、LINE 通知など）。
    - 環境（development / paper_trading / live）およびログレベルの検証。
    - paper_trading 用の専用 SQLite パス（PAPER_TRADING_SQLITE_PATH）のサポート。
    - 各種しきい値（CPU/MEM/DISK など）や kill flag の設定を提供。
  - .env 自動読み込み機能を追加（プロジェクトルート（.git または pyproject.toml）から .env/.env.local を読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env ファイルパース機能の実装:
    - export KEY=val 形式や、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
- 対話式設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
  - .env 初期作成 / 更新を支援するウィザード。
  - デフォルト値、選択肢、シークレット入力、既存 .env の読み込み／再利用機能。
  - .env 出力フォーマットと注意コメントを生成。
  - 実行例: python -m kabusys.config_setup
- 設定検証 CLI を追加（src/kabusys/validate_config.py）。
  - .env と config/*.yaml の事前検証を行うツール。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パス親ディレクトリ存在確認、YAML パーサー（PyYAML）有無に応じた処理、KABUSYS_ENV=live の追加ガード（LINE 通知や KILL_FLAG_CLEAR_ON_START の警告）。
  - --strict オプションにより警告を失敗扱いにできる。
  - 実行例: python -m kabusys.validate_config
- 実行用スクリプトを追加
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - ExecutionEngine を使ったセッション起動処理。paper_trading 環境では専用の paper_trading DB を使用して本番 DB と分離。
    - stop flag / pid ファイル制御、プロセス優先度設定、DB 初期化処理を含む。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可（デフォルト 60 秒）。
    - 監視は常に sqlite_path（本番相当）を使用する。
- 発注エンジンと関連コンポーネント
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナル読み込み（DuckDB）、Gate1/Gate2 のリスクチェック、発注フロー、push ドレイン、Gate3（ドローダウン）判定、kill_switch の発動などのセッションロジックを実装。
    - WebSocket push 用スレッド（broker が stream_push を提供する場合）を起動して受信を内部キューへ投入。
    - PID ファイル管理、kill.flag の起動時挙動（KILL_FLAG_CLEAR_ON_START のサポート）。
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態（OrderState）列挙と状態遷移ロジックを持つ純粋なデータモデルを実装。
    - 許可される遷移テーブルと不正遷移時の例外（InvalidStateTransitionError）を定義。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - signal_id による重複注文防止（DuplicateOrderError）。
    - create_order / send_order / sync_order / cancel_order の外向き API を実装。
    - send_order はクラッシュ耐性を考慮した二相永続化（OrderSent への遷移を先にコミットし、broker_order_id を保存→OrderAccepted に遷移）を行う設計。
    - OrderSentPendingError（ブローカーが注文番号を発行したが約定しないケース）を適切に扱う。
    - sync_order によるブローカー状態同期と部分約定の取り扱い（filled_qty/avg_fill_price の更新）。
    - cancel_order は終端状態のチェックおよび broker への cancel 呼び出しを行う。
  - 発注関連の補助設定（RiskManager / Reconciler 等の利用箇所を統合する構造を実装）。
- Broker クライアント実装（kabu station）
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx を使った同期 REST クライアント実装とトークン管理（遅延取得と 401 時の再取得 → 1 回再試行）。
    - レスポンス JSON パース例外の変換、タイムアウト / ネットワークエラーのハンドリング。
    - HTTP 429 を RateLimitError、5xx を BrokerAPIError に変換。
    - kabu station の状態コードを内部ステータス（open/partial/filled/...）にマップ。
    - WebSocket(push) の受信連携（websocket ライブラリ利用想定）。
- DB / 監視関連
  - duckdb と sqlite を利用した接続処理を含む。monitoring の初期化関数呼び出しを各起動スクリプトで実施。
  - 監視用イベントの記録（latency / trade event）を ExecutionEngine 内で監視 DB に書き込む箇所を用意（監視DBが与えられた場合）。
- ユーティリティ
  - .env 読み込みの堅牢化（ファイル読み込み失敗時の warnings.warn）。
  - ファイルパスの親ディレクトリ存在チェックと警告メッセージ。

### 変更
- なし（初期リリース）。

### 修正
- なし（初期リリース）。

### 既知の注意点
- config/*.yaml の中身検証は PyYAML がインストールされている場合のみ行われます。未インストール時は YAML のパースチェックはスキップされ、警告が出ます。
- ExecutionEngine の一部挙動（WebSocket push の有無や broker 側の API 実装など）は、Broker の実装に依存します。
- .env は絶対に Git にコミットしないよう README 等で注意する必要があります（config_setup がその旨のヘッダを出力します）。

---

（将来のリリースでは Unreleased セクションを用意して変更を積み重ねてください）