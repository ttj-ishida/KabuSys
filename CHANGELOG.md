# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に従います。
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース — KabuSys のコア設定・実行・監視・発注基盤を実装。

### 追加
- 基本メタ情報
  - パッケージバージョンを設定 (src/kabusys/__init__.py: __version__ = "0.1.0")。

- 設定管理
  - 環境変数/.env 読み込み機能を実装 (src/kabusys/config.py)。
    - .git または pyproject.toml を基準にプロジェクトルートを探索して .env / .env.local を自動読み込み。
    - OS 環境変数を保護するための上書きルール（.env.local は上書き、.env は未設定時のみセット）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト向け）。
    - .env 行のパースは export 形式、クォート（シングル／ダブル）、エスケープ、インラインコメント等に対応。
    - _require() による必須環境変数チェック。

  - Settings クラスを提供し、環境変数からアプリ設定を取得するプロパティを定義。
    - J-Quants / kabu API / LINE / DB パス / PID/Kill Flag /閾値 / 環境 (development/paper_trading/live) / ログレベル 等。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - paper_trading の場合に専用 SQLite パスを参照する paper_sqlite_path。

- 設定ウィザード CLI
  - 対話式 .env 生成/更新ツールを実装 (src/kabusys/config_setup.py)。
    - 対象項目の定義、既存 .env 読み込み、秘密値のマスク表示、選択肢サポート。
    - 保存前の確認と --env-file オプションによるファイル指定。
    - .env のテンプレート書き出し機能 (_write_env)。

- 設定検証 CLI
  - .env と config/*.yaml を起動前に検証する CLI を実装 (src/kabusys/validate_config.py)。
    - 必須/任意環境変数チェック、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL 値検証。
    - DB パスの親ディレクトリ存在チェック（存在しなければ警告）。
    - PyYAML の有無に応じた config/*.yaml の存在・パース検証。
    - KABUSYS_ENV=live の場合の追加ガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL として扱う。
    - 使い方: python -m kabusys.validate_config

- 実行/監視起動スクリプト
  - Execution 起動スクリプト (src/kabusys/run_execution.py)
    - プロセス優先度設定、設定読み込み、DB 接続（paper_trading は専用 SQLite を使用して本番 DB と分離）。
    - stop フラグ (data/stop_requested.flag) と PID ファイル管理。
    - スレッドで ExecutionEngine を起動・監視し、停止時にクリーンアップ。
  - Monitoring 起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。

- Execution エンジンと発注フロー
  - ExecutionEngine を実装 (src/kabusys/execution/execution_engine.py)
    - Session 実行フロー（シグナル処理 8:50-9:10、push ドレイン 9:10-15:30）。
    - 起動時リコンシリエーション呼び出し、kill.flag の挙動（KILL_FLAG_CLEAR_ON_START への対応）、PID ファイル管理。
    - WebSocket スレッドで kabu push を受信し内部キューへ投入。
    - シグナル読み込みは DuckDB から行い、size_multiplier による数量調整、100株刻み丸め。
    - Gate 1 (signal-level)、Gate 2 (execution-level, rate limit + circuit breaker)、Gate 3 (ドローダウン監視) による多段リスク管理。
    - 発注時の API レイテンシ計測と監視 DB への記録（MonitoringDB が渡された場合）。
    - kill_switch() 実装により全 active 注文のキャンセルを試みる。

  - OrderRecord（状態遷移モデル）を実装 (src/kabusys/execution/order_record.py)
    - 状態列挙 OrderState、許容遷移マップ、遷移検証と timestamp 更新。
    - InvalidStateTransitionError を定義。

  - OrderManager（外向き API）を実装 (src/kabusys/execution/order_manager.py)
    - create_order: signal_id の重複検出（DB 部分ユニーク制約違反を DuplicateOrderError に変換）。
    - send_order: 2相永続化戦略（OrderSent を DB に書き込んだ後 broker 呼び出し、broker_order_id の永続化 → OrderAccepted へ遷移）。
      - OrderRejectedError / OrderSentPendingError の扱い。
      - クラッシュ耐性を考慮した設計（送信途中での状態回復のための sync_order との連携）。
    - sync_order: broker 側ステータスを取得して状態同期（部分約定の進捗更新も考慮）。
    - cancel_order: キャンセル不可能な状態の判定、broker へのキャンセル呼び出し、Cancelled への遷移。

  - Broker 関連
    - KabuStationClient の実装を追加 (src/kabusys/execution/kabu_client.py)
      - httpx を用いた同期 REST クライアント。
      - Token 取得の遅延初期化、401 時の自動再取得とリトライ、429 による RateLimitError、500 系のサーバーエラー判定。
      - kabu ステーションの注文状態コードを内部ステータス（open/partial/filled/cancelled/rejected）へマッピング。
      - websocket 経路を用いた push 処理（stream_push）をサポートする設計（任意機能）。

- 監視 DB 初期化
  - init_monitoring_db（monitoring DB の初期化）呼び出しを run_execution / run_monitoring から行い、監視テーブルの存在を保証。

- ユーティリティ
  - process_priority 設定、logging setup の呼び出しなど共通ユーティリティを利用して起動時の環境整備を行う（run_* スクリプト）。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 削除
- なし（初回リリース）

---

注:
- 本リリースはコードベースから推測して記載した CHANGELOG です。実際の意図や将来の設計変更により差異が生じる可能性があります。
- .env ファイルは機密情報を含むため絶対にリポジトリへコミットしないでください（config_setup の出力にも注意喚起あり）。