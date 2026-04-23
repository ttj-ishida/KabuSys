CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

テンプレートに沿って、コードベースから推測できる初期リリースの変更履歴を日本語でまとめています。

Unreleased
----------
（なし）

0.1.0 - 2026-04-23
-----------------

Added
- プロジェクト初期リリース: KabuSys 日本株自動売買システムの基本機能を実装。
- パッケージ初期化:
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。
- 設定管理:
  - src/kabusys/config.py
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサーは export KEY=val 形式、クォート値（エスケープ処理含む）、インラインコメントの扱いをサポート。
    - 必須環境変数取得用の _require() を実装（未設定時は ValueError）。
    - Settings クラスを提供し、各種設定（API トークン、DB パス、PID ファイル、キルフラグ、閾値、環境種別、ログレベル、paper_trading 用設定など）をプロパティで取得可能。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション。

- 環境設定ウィザード CLI:
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新。
    - シークレット項目は表示をマスク。
    - デフォルト値、選択肢、説明付き。
    - .env の読み書き（既存値を保持 / 上書き）と保存確認。
    - 推奨手順の案内（validate_config 実行の推奨）。

- 設定検証 CLI:
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の事前検証。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在チェックおよび PyYAML があればパース検証（PyYAML 未インストール時はスキップして警告）。
    - KABUSYS_ENV=live 時の本番向けガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict モードをサポート（警告を FAIL として exit(1)）。
    - 実行例: python -m kabusys.validate_config

- 実行スクリプト:
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプト。プロセス優先度設定、PID 管理、停止フラグに基づく挙動。
    - paper_trading 環境では専用の paper_trading DB を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）に基づく安全停止。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。

- 実行コンポーネント（コアロジック）:
  - src/kabusys/execution/execution_engine.py
    - Signal Queue ベースの発注エンジンを実装（シグナル処理窓: 8:50-9:10、push ドレイン: 9:10-15:30）。
    - Gate1/2/3 によるリスクチェックフロー（シグナル毎のチェック、実行時のレートリミット/サーキットブレーカー、ポートフォリオドローダウン監視）。
    - push（WebSocket）受信を _push_queue へ投入し、sync + Gate3 チェックを行う。
    - WebSocket 機能は broker の stream_push の有無に応じてスキップ可能。
    - position_entries への約定記録（次営業日を fill_date として扱う）を DuckDB に書き込み。
    - kill.flag の存在時の起動拒否と KILL_FLAG_CLEAR_ON_START による自動クリアオプション。

  - src/kabusys/execution/order_record.py
    - OrderRecord データモデルと状態遷移ロジック（状態列挙 OrderState, 許可される遷移マップ）。
    - transition_to による遷移検証と updated_at 自動更新。
    - 不正遷移時は InvalidStateTransitionError を送出。

  - src/kabusys/execution/order_manager.py
    - DB（OrderRepository）と OrderRecord を組み合わせた外向き API。
    - create_order で同一 signal_id の重複検出（DB の部分ユニークインデックスに基づく DuplicateOrderError を考慮）。
    - send_order の二相永続化パターン:
      1) OrderCreated -> OrderSent を先に永続化（クラッシュ安全性向上）
      2) broker API 呼び出し
      3a) 成功時は broker_order_id を永続化（state は Sent のまま）
      3b) OrderAccepted に遷移して永続化
      - OrderRejectedError を適切に Rejected に遷移して保存
      - OrderSentPendingError（注文番号は発行されるが約定しないケース）を扱い、broker_order_id を保存した上で OrderSent のまま残す（Reconciliation 対象）。
    - sync_order により broker 側の状態と同期。状態変化がない場合でも filled_qty/avg_fill_price の更新に対応。
    - cancel_order は終端状態のチェック後、broker API 呼び出しを行い Cancelled に遷移。

  - src/kabusys/execution/kabu_client.py
    - kabuステーション REST API クライアント実装（同期 httpx を使用）。
    - トークンの遅延取得と自動再取得（401 で再取得して1回リトライ）。
    - HTTP エラー（401、429、5xx）を専用エラーに変換（RateLimitError, BrokerAPIError 等）。
    - 将来的な async 対応を容易にする設計。

- 監視関連:
  - monitoring 用 DB 初期化（init_monitoring_db 呼び出し箇所を run_* で実行）。
  - ExecutionEngine から監視DBへの trade イベントログ書き込みを試みる（失敗しても発注フローは継続）。

- ユーティリティ:
  - process_priority 設定を呼び出してプロセス優先度を上げる（run scripts で最初に実行）。
  - setup_logging の呼び出しによりログ設定を行う想定。

Changed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- （該当なし。シークレット値は .env に置くこと、.env を Git にコミットしない旨を README/.env ヘッダに明記）

Known issues / Notes（既知の設計意図）
- config/*.yaml の検証は PyYAML が未インストールの場合スキップされる（警告を出力）。内容検証を行うには PyYAML をインストールしてください。
- send_order の二相永続化はクラッシュ耐性を高めるが、OrderSent のまま残るケースが発生する。これらはリコンシリエーション（Reconciler）で回復する設計。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバックする。
- WebSocket push 処理は broker 実装が stream_push を提供しない場合スキップされる設計。
- paper_trading は本番 DB と分離される（paper_trading 用 SQLite を使用）。

Usage highlights
- .env を作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行（例）:
  - 監視ループ: python -m kabusys.run_monitoring
  - 発注エンジン: python -m kabusys.run_execution

もし CHANGELOG に追記したい追加項目（例えば実際の修正履歴、細かいバグ修正や日付の差し替え等）があれば教えてください。コードの他ファイル（未提供の OrderRepository 等）を含めた詳細な変更点が必要なら、そのソースも提示してください。