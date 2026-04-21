CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています（推測に基づく記載）。

[Unreleased]
------------

- なし（この CHANGELOG は現時点のコードベースから初版リリース向けに作成しています）。

[0.1.0] - 2026-04-21
--------------------

Added
- 初回リリースとして自動売買システム "KabuSys" の基本コンポーネントを追加。
  - 環境設定・管理
    - config.py: 環境変数/`.env` の自動ロード機能を実装。
      - プロジェクトルートの検出（`.git` または `pyproject.toml` を基準）により、カレントワーキングディレクトリに依存しない自動読み込みを実現。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
      - .env パーサは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - Settings クラス: アプリケーション設定をプロパティとして提供。J-Quants トークン、kabu API パスワード、DB パス、各種閾値、環境種別（development/paper_trading/live）等を管理。値の妥当性チェック（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）。
  - 設定支援ツール
    - config_setup.py: 対話式ウィザードで `.env` を初期作成/更新する CLI を追加。シークレット値は出力時にマスク。デフォルト値や選択肢表示をサポート。
  - 設定検証
    - validate_config.py: `.env` と `config/*.yaml` の起動前検証 CLI を追加。必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば実行、未インストール時はスキップ）など。`--strict` オプションで警告も失敗扱いに可能。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine の起動スクリプト。プロセス優先度設定、PID ファイル管理、停止フラグ検出、paper_trading 時の DB 分離（paper_trading 用 sqlite を使用）を実装。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。`MONITOR_POLL_INTERVAL` 環境変数で間隔上書き（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite を使用。
  - 実行ロジック（発注エンジン）
    - execution/execution_engine.py: Signal Queue からの発注ループ、WebSocket push ドレイン、3 段階の Gate によるリスクチェック（Gate1: シグナル、Gate2: 実行レート制御、Gate3: ドローダウン監視）を実装。kill_switch による全 active 注文キャンセル、PID ファイルおよび kill.flag の扱い、Reconciliation の起動フック、WebSocket スレッド処理を実装。
  - 注文管理
    - execution/order_record.py: OrderState 列挙・OrderRecord データモデルと状態遷移ロジックを実装。許容遷移表定義、遷移検証（InvalidStateTransitionError）、updated_at 自動更新などを提供。
    - execution/order_manager.py: OrderRecord（純粋なロジック）と OrderRepository（SQLite）を連携する外向き API を実装。create_order（重複検出）、send_order（クラッシュ耐性を考慮した 2 相永続化パターン）、sync_order（ブローカー状態同期）、cancel_order（キャンセル不可能状態の検査）を実装。DB の部分ユニーク制約違反を DuplicateOrderError に変換する処理を追加。
    - send_order は OrderSentPendingError を扱い、ブローカー注文番号を保存して OrderSent のまま残す等、Reconciliation を想定した安全設計。
  - ブローカークライアント
    - execution/kabu_client.py: kabuステーション REST API クライアントを実装（httpx 使用）。トークン取得の遅延初期化、401 時のトークン再取得とリトライ、429（レート制限）/5xx のハンドリング、send_order/cancel/get_order_status の基本実装、ステータスマッピングを実装。
  - 監視・データベース
    - Monitoring DB 初期化ユーティリティの呼び出しを run_monitoring/run_execution に統合。DuckDB と SQLite 両方を使用（分析用 DuckDB / 監視用 SQLite）。
  - ユーティリティ
    - ログ設定とプロセス優先度設定ユーティリティ（setup_logging, set_process_priority）を利用するスクリプトを用意。

Changed
- 初版につき過去からの変更なし（初期実装）。

Fixed
- .env パーサの強化により、引用符付き文字列内のバックスラッシュエスケープや、クォート無しでのコメント検出（直前が空白/タブの場合のみ）など、実運用で問題となりうるケースを考慮。
- send_order の永続化手順を明確化（OrderSent を先に DB に永続化 → ブローカ呼び出し → broker_order_id 保存 → OrderAccepted に遷移）してクラッシュ後の状態回復に配慮。
- validate_config: PyYAML 未インストール時の挙動を警告して YAML パースをスキップすることで依存関係がなくても検証を部分的に実行可能に。

Security
- config_setup の出力および設定確認画面ではシークレット値（J-Quants トークン、kabu API パスワード、LINE トークン等）を表示時にマスク。
- Settings._require は必須環境変数未設定時に明示的に例外を投げ、起動時の安全性を確保。

Notes
- 本リリースはコードベースからの推測に基づいて CHANGELOG を作成しています。実際のリリースノートはリポジトリ履歴やコミットメッセージに基づき調整してください。
- 利用手順の一例:
  - 初期設定: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 監視起動: python -m kabusys.run_monitoring
  - 実運用開始: python -m kabusys.run_execution

Deprecated
- なし

Removed
- なし

Security
- なし（公開すべきセキュリティ修正は本スナップショットからは見つかりませんでした）

-----