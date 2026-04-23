CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。
全ての変更はセマンティックバージョニングに従います。

0.1.0 - 2026-04-23
------------------

Added
- 初回公開: KabuSys の基本モジュール群を追加。
- 環境設定 / 読み込み
  - Settings クラスを追加し、環境変数から設定を取得可能に。
  - 自動 .env ロード機能を追加（プロジェクトルートを .git / pyproject.toml で検出）。
  - OS 環境変数を保護した上で .env / .env.local を読み込む実装を追加。
  - .env パース機能を強化（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントの扱いの改善）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションをサポート。

- 設定支援ツール
  - 対話式ウィザード `kabusys.config_setup` を追加。.env の初期作成・更新を補助。
  - ウィザードは項目定義（必須・任意・シークレット・選択肢）を持ち、既存 .env の読み込み・確認・保存を行う。
  - .env を保存する際に Git にコミットしないよう注意書きを出力。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。
  - 必須環境変数の存在確認、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml ファイルの存在と YAML パース（PyYAML があれば）検証、KABUSYS_ENV=live 時の追加ガードを実装。
  - --strict オプションで警告もエラー扱いにできる。

- 実行スクリプト
  - `run_execution` を追加。ExecutionEngine を起動するためのスクリプト（プロセス優先度設定、PID 管理、stop フラグ検知、paper_trading の DB 分離を含む）。
  - `run_monitoring` を追加。SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL 環境変数で間隔上書き可）。Monitoring は環境に関わらず本番 sqlite_path を使用する仕様。

- 実行ロジック・発注系
  - ExecutionEngine（Signal Queue Pull 型）を追加。シグナル処理窓（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）のフローを実装。
  - EngineConfig で target_date 等を指定可能。
  - 発注フローに Gate1/2/3 のリスク検査を導入（signal-level / execution-level / portfolio-level）。
  - kill_switch により全 active 注文のキャンセルとループ停止を行う実装を追加。
  - WebSocket ワーカースレッド（broker が stream_push を提供する場合）で push を受けて処理する仕組みを追加。

- 注文データモデルと管理
  - OrderRecord（状態遷移ロジックを含む純粋ビジネスロジック）を追加。OrderState（created, sent, accepted, partial, filled, closed, cancelled, rejected）と遷移許可マトリクスを実装。InvalidStateTransitionError を導入。
  - OrderRepository と組み合わせる OrderManager を追加。create/send/sync/cancel の外向き API を提供。
    - create_order は signal_id 重複検査（DB 制約も考慮）を行い、DuplicateOrderError を定義。
    - send_order はクラッシュ耐性を考慮した 2 相的な永続化戦略を実装（OrderSent 先コミット、broker_order_id 先コミット、次に OrderAccepted に遷移）。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order で broker からの状態を取り込み、部分約定の更新や OrderSent→Filled の直接遷移を防いで OrderAccepted を経由する調整を実装。
    - cancel_order は取消不可状態の検出と例外処理を実装。

- broker クライアント
  - KabuStationClient を追加（httpx 同期クライアント利用）。トークン取得の遅延初期化、自動再取得（401 時にリトライ）、HTTP タイムアウト・ネットワーク例外の BrokerAPIError への変換を実装。
  - レスポンス json パース失敗を BrokerAPIError に変換、429/5xx のハンドリングを追加。
  - WebSocket push（websocket ライブラリ）との連携ポイントを用意。

- 監視・DB 初期化
  - monitoring 側の DB 初期化関数 init_monitoring_db を組み込み、監視用テーブルの存在を保証する起動経路を追加。
  - ExecutionEngine / OrderManager から監視 DB へトレードイベントを書き込むフックを追加（監視書き込み失敗時は警告のみでフロー継続）。

Changed
- プロセス管理とファイルパス
  - PID ファイル／kill.flag の扱いを統一。起動時に kill.flag が存在する場合の挙動は KILL_FLAG_CLEAR_ON_START によって制御される（クリアするか起動拒否するか）。
  - paper_trading 環境では paper_sqlite_path を使用し、本番 DB と完全に分離する仕様を導入。

Fixed
- .env パースの不具合修正・改善
  - export プレフィックスに対応、クォート内のバックスラッシュエスケープを正しく処理、インラインコメントの誤検出を減らす処理を導入。
- MONITOR_POLL_INTERVAL の不正値（ゼロや負数）を検出してデフォルトにフォールバックする処理を追加（time.sleep に渡すと ValueError になる問題への対処）。
- send_order のクラッシュシナリオ（OrderSent と broker_order_id の永続化順序）を考慮した設計で、リコンシリエーションが状態を復旧できるように改善。

Security
- .env にパスワード等の機密情報が含まれるため .env は Git にコミットしないよう注意書きを追加（config_setup のヘッダに明記）。

Notes / Known limitations
- validate_config の YAML 内容検証は PyYAML がインストールされている場合にのみ行われる（未インストール時はスキップして警告を出力）。
- KabuStationClient は同期 httpx.Client ベース。将来的な非同期対応は httpx.AsyncClient への置き換えで対応可能。
- 本リリースは初回版のため、リコンシリエーションやブローカー固有のエラーケースに関する追加の堅牢化や運用テストを推奨。

Acknowledgements
- 初回リリース。今後の運用で検出された不具合や改善点は次バージョンで反映します。