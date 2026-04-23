# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

- リリースノートはコードベースから推測して作成しています。実際のコミット履歴とは差異がある可能性があります。

## [Unreleased]

### Added
- ドキュメント／運用支援用 CLI を追加
  - python -m kabusys.config_setup: 対話式ウィザードで .env を生成 / 更新可能（シークレットのマスク表示、選択肢／デフォルト対応、保存確認）。
  - python -m kabusys.validate_config: .env と config/*.yaml の起動前検証を行う CLI を追加（--strict で警告を失敗扱い）。
- 環境設定管理モジュールを追加
  - 自動 .env ロード（プロジェクトルートを .git / pyproject.toml で探索）、.env と .env.local の優先度制御、OS 環境変数保護機能（protected）。
  - .env 解析ロジック強化（export プレフィックス、シングル/ダブルクォート中のエスケープ、インラインコメント処理）。
  - Settings クラス導入：J-Quants / kabu API / LINE / DB パス / Kill Switch /閾値 等のプロパティを提供。値のバリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実施。
- Execution 系の主要コンポーネントを追加
  - ExecutionEngine: シグナル処理（8:50-9:10）、push ドレイン（9:10-15:30）、kill switch、PID 管理、WebSocket push の受信と処理を実装。
  - OrderRecord: 注文状態モデルと状態遷移ロジック（遷移の検証、更新時刻自動更新）を追加。InvalidStateTransitionError を導入。
  - OrderManager: シグナル→DB 登録→broker 送信→同期（sync）→キャンセルまでの外向き API を実装。DuplicateOrderError の導入。
  - Two-phase 永続化の設計を採用し、クラッシュ時の不整合に対するリコンシリエーションを考慮（OrderSent 前後の処理や broker_order_id の先行永続化等）。
  - Reconciler / RiskManager / OrderRepository 等（組み立て・呼び出し例を実装）。
- Broker / kabu station クライアント実装
  - KabuStationClient: httpx を使った同期 REST クライアントを実装。トークンの遅延取得および 401 の際の再取得とリトライをサポート。429（レート制限）/ 5xx の取り扱いを実装。
  - WebSocket push（stream_push）に対応する設計（存在しないブローカーの場合はスキップされる）。
- Monitoring 周り
  - run_monitoring スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60秒）。監視は環境に関係なく本番 sqlite_path を使用して DB を初期化。
  - 監視 DB 初期化用 init_monitoring_db 呼び出しを利用。
- 実行用スクリプト
  - run_execution: 実行用エントリポイント。プロセス優先度の設定、paper_trading の場合は paper_trading 専用 SQLite を使用する分離設計、停止フラグ検知による起動抑止を実装。
- ロギング・プロセス管理ユーティリティとの統合ポイントを用意（setup_logging、set_process_priority の呼び出し）。
- DuckDB と SQLite の併用を明示（DuckDB は分析、SQLite は監視／履歴保存に使用）。paper_trading 用 DB のパス設定を分離。

### Changed
- 監視 / 実行の挙動設計の明確化
  - 監視は常に本番用 sqlite_path を使用する仕様と明示。
  - ExecutionEngine はシグナル処理中や push 処理中に発生した例外をロギングしつつ耐障害性を保つように設計（例外でセッションが完全に停止しないように保護）。
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能に。

### Fixed
- Order の状態遷移制御を明確化（OrderSent → Filled などの直接遷移を避けるため、OrderAccepted 経由の遷移や同一状態での filled_qty / avg_fill_price の更新ロジックを実装）。
- send_order の例外ハンドリングを整理し、OrderSentPendingError（注文番号はあるが未約定）を呼び出し元へ伝播させて保留処理を扱えるように。

### Security
- .env ファイルは絶対に Git にコミットしない旨を config_setup の出力に明記。

---

## [0.1.0] - 2026-04-23

初回公開想定リリース — 基本機能の導入

### Added
- パッケージメタ情報
  - __version__ = "0.1.0"
- 基本構成
  - 環境設定読み込み（.env 自動読み込み、.env.local 上書き）
  - 設定取得用 Settings オブジェクト（各種 env に対する検証付きプロパティ）
- 実行エンジン一式
  - ExecutionEngine（セッション管理、シグナル処理、push ドレイン、kill switch、PID 管理）
  - run_execution スクリプト
- 注文管理
  - OrderRecord（状態遷移検証）
  - OrderManager（create/send/sync/cancel の実装、DuplicateOrderError）
  - OrderRepository 呼び出し例の統合
- Broker クライアント
  - KabuStationClient（REST API 操作、トークン管理、エラー変換）
- 監視
  - run_monitoring スクリプト（監視ループ、DB 初期化、ポーリング間隔設定）
- 開発運用ツール
  - config_setup（.env 生成ウィザード）
  - validate_config（環境変数や config/*.yaml の起動前検証）
- DuckDB / SQLite の利用を前提としたデータ入出力インタフェースを整備

### Fixed / Notes
- 主要な操作フロー（発注→永続化→broker 呼び出し→同期）のクラッシュ安全性を考慮した二相的な永続化戦略を採用。
- .env パーサは複雑なケース（クォート内のエスケープ、export プレフィックス、コメント）に対応。
- PAPER_TRADING 用の DB 分離（paper_trading 実行時は paper_sqlite_path を使用）を実装。

---

注: 本 CHANGELOG は与えられたソースコードから推測して作成したものであり、実際の変更履歴（コミットメッセージやタグ）とは異なる場合があります。必要であれば、実際の VCS 履歴ベースで調整した CHANGELOG を生成します。