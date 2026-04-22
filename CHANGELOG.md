# Changelog

すべての重要な変更をこのファイルに記録します。  
このファイルは Keep a Changelog の形式に従っています（日本語で要約）。

なお、リリース内容はコードベースから推測して記載しています。

## [Unreleased]

（現在のところ特定の未リリース変更はありません。将来の変更はここに記載してください。）

## [0.1.0] - 2026-04-22

初回公開リリース。以下の主要機能と設計要素を含みます。

### Added
- 環境/設定管理
  - Settings クラスを実装し、環境変数からアプリケーション設定を取得する API を提供。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式、クォート（シングル/ダブル）内のバックスラッシュエスケープ、行末コメントの扱いなどに対応。

- 対話式セットアップ
  - config_setup CLI を実装（python -m kabusys.config_setup）。
  - .env を対話的に作成/更新するウィザード。シークレット項目はマスク表示。
  - 標準的な設定項目テンプレート（J-Quants, kabu API, DB パス, LINE 通知, ログレベル, Kill Switch 等）を出力する _write_env。

- 設定検証ツール
  - validate_config CLI を実装（python -m kabusys.validate_config）。
  - 必須環境変数の存在確認、プレースホルダ値検出、KABUSYS_ENV / LOG_LEVEL の妥当性検査。
  - DB パス親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定等）を実装。
  - --strict オプションで警告を失敗扱いにするモードを提供。

- 実行スクリプト
  - run_execution.py:
    - ExecutionEngine の起動スクリプト。プロセス優先度設定、PID/stop フラグハンドリング、DB 接続（paper_trading の分離）を実装。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、stop フラグ検出等。

- Execution エンジンと発注フロー
  - ExecutionEngine:
    - シグナル読み取り（DuckDB）、Gate1（シグナルレベル）/ Gate2（実行レート制御）/ Gate3（ドローダウン監視）を組み合わせた発注フロー。
    - WebSocket（push）を受け取るための別スレッドとドレインキュー実装。
    - kill_switch による全 active 注文のキャンセルとループ停止処理。
    - セッション制御（発注開始/締切/市場クローズ）と PID ファイル管理。
  - Execution 用補助:
    - データベース（SQLite / DuckDB）への接続と初期化処理。
    - paper_trading 時に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使って本番 DB と分離。

- 注文管理と状態遷移
  - OrderRecord: 純粋な状態マシンデータモデルを実装（DB 非依存）。
    - OrderState 列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可される遷移テーブルと transition_to による検証／updated_at 自動更新。
    - 無効遷移で InvalidStateTransitionError を発生。
  - OrderManager:
    - create_order / send_order / sync_order / cancel_order の外向き API 実装。
    - create_order は signal_id の重複アクティブ注文を検出して DuplicateOrderError を投げる。
    - send_order はクラッシュ安全性を考慮した 2 相永続化（OrderSent を先に commit、broker_order_id を先に保存してから OrderAccepted に遷移）を実装。
    - OrderSentPendingError（注文番号はあるが約定待ち）や OrderRejectedError の扱いを実装。
    - sync_order は broker の状態を照合して部分約定情報（filled_qty / avg_fill_price）を反映。OrderSent→Filled のような直接遷移不可ケースでは OrderAccepted を経由する処理を実装。
    - cancel_order はキャンセル不適格状態を弾くチェックと broker 側取消し呼び出しを実装。

- ブローカークライアント（kabu）
  - KabuStationClient を実装（httpx 同期クライアントを利用）。
    - トークン取得の遅延初期化、401 発生時のトークン再取得→リトライ処理。
    - レスポンス JSON パースのエラーハンドリングを BrokerAPIError に変換。
    - HTTP ステータス 429 を RateLimitError に変換する扱いなど、エラー種別の判別処理を実装。
    - kabu station の状態コードから内部状態文字列へのマッピングを定義。
    - 将来の WebSocket 対応（stream_push）を想定した設計（_websocket_worker と連携）。

- 監視（Monitoring）
  - run_monitoring による監視ループ、monitoring DB 初期化、duckdb 利用。
  - 停止フラグ検出でループ終了、例外時のログ出力とリトライ継続を実装。

- ログ・プロセス制御・安全機構
  - プロセス優先度設定ユーティリティ呼び出し（set_process_priority）。
  - PID ファイル管理、kill.flag の検査と KILL_FLAG_CLEAR_ON_START によるオプション的自動クリア。
  - 設定値検証（PAPER_FILL_MODE の許容値チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック）。
  - 各所で例外の記録と安全なフォールバック動作（例: 監視 DB 書き込み失敗時は警告でフロー継続）を考慮。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数ファイル (.env) を Git にコミットしないよう README 注意書きが出力される書式で .env を生成する（config_setup の出力）。

Notes / Usage
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行系:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

詳細やマイナーな実装上の挙動はソースコード内の docstring とコメントを参照してください。