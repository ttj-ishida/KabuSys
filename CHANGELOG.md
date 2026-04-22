# Changelog

このファイルは Keep a Changelog の形式に準拠しています。  
すべての変更はセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-22

初回公開リリース。日本株自動売買システム KabuSys の基礎機能を実装しました。主な追加項目は以下の通りです。

### Added
- 基本パッケージ情報
  - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
- 環境設定管理
  - src/kabusys/config.py
    - プロジェクトルート探索（.git / pyproject.toml を基準）による .env 自動読み込み。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）。
    - _parse_env_line による堅牢な .env パーサ（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート）。
    - _load_env_file の override/protected 機構により OS 環境変数の保護を実現。
    - Settings クラス: 型付きプロパティによる設定取得（パスは Path 型で取得、値検証を含む）。
    - 環境変数検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の値検査とエラー通知）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化対応（テスト向け）。
- .env 設定ウィザード
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI。
    - 各設定項目の定義（選択肢、デフォルト、シークレット表示、説明文）。
    - 既存 .env の読み込み・再利用、入力キャンセル処理、最終確認とファイル書き出し機能。
    - 書き出しテンプレートには Git にコミットしない旨の注記を付与。
- 設定検証ツール
  - src/kabusys/validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI（--strict フラグで警告を FAIL 扱いにできる）。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認。
    - PyYAML 未インストール時には YAML 内容検証をスキップして警告出力。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）。
- 実行用エントリスクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - プロセス優先度設定、PID/stop フラグ管理、paper_trading 時の専用 SQLite を使用する分離設計。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨の仕様。
- 注文・状態管理
  - src/kabusys/execution/order_record.py
    - OrderRecord データモデルと状態遷移ロジックを実装（状態列挙・許容遷移定義・更新タイムスタンプ自動更新）。
    - 不正遷移時に InvalidStateTransitionError を送出。
  - src/kabusys/execution/order_manager.py
    - OrderRecord と OrderRepository を組み合わせた外向け API。
    - create/send/sync/cancel の振る舞いを定義。
      - create_order は signal_id の重複防止（DB の部分ユニーク制約違反を DuplicateOrderError に変換）。
      - send_order はクラッシュ耐性を意識した 2 段階永続化（OrderSent を先に保存 → broker 呼び出し → broker_order_id を保存 → OrderAccepted に遷移）。
      - OrderSentPendingError（注文番号は発行されたが約定しないケース）を適切に扱い DB に broker_order_id を残す。
      - sync_order は broker のステータス取得により状態同期（部分約定の進行はフィールド更新で対応）。
      - cancel_order はキャンセル不可能な状態の判定と例外送出、broker 呼び出し後に Cancelled に遷移。
- 発注エンジン
  - src/kabusys/execution/execution_engine.py
    - ExecutionEngine 本体（シグナルの読み込み、Gate1/2/3 によるリスクチェック、発注フロー、push ドレイン、kill_switch の実装）。
    - シグナル処理（8:50-9:10）と push ドレイン（9:10-15:30）を実装。
    - Gate 1: シグナルレベル検査、Gate 2: 実行レベル（レート制限・サーキットブレーカー）、Gate 3: ドローダウン監視（NG の場合に kill_switch 発動）。
    - WebSocket 用ワーカースレッドからの push を内部キューへ投入し処理する仕組み（stream_push 未対応の場合はスキップして警告）。
    - PID ファイル管理、kill.flag の起動時挙動（KILL_FLAG_CLEAR_ON_START による自動クリア選択肢）。
    - 発注成功/保留/失敗時に監視 DB へイベント記録（可能な場合）。
- ブローカークライアント（kabu station）
  - src/kabusys/execution/kabu_client.py
    - KabuStationClient 実装（同期 httpx クライアントを使用）。
    - トークン管理（遅延初期化、401 時の再取得とリトライ）、HTTP エラー→独自例外への変換（BrokerAPIError / RateLimitError 等）。
    - kabu station の注文状態コードを内部ステータスにマップするロジック。
- 監視関連
  - src/kabusys/monitoring/*（モジュール参照箇所を利用）
    - init_monitoring_db 等を使用した監視 DB 初期化・イベント記録の統合（run_monitoring / run_execution で使用）。
- ユーティリティ
  - プロセス優先度設定ユーティリティ（set_process_priority を呼び出し High 優先度に設定する処理を起動時に実行）。
  - ロギングセットアップユーティリティ（setup_logging を利用して各プロセスのログ初期化）。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Notes / Usage
- .env の自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利です）。
- 設定ウィザード:
  - 実行: python -m kabusys.config_setup
  - 生成後は python -m kabusys.validate_config で検証してください。
- 設定検証ツール:
  - 実行: python -m kabusys.validate_config [--strict]
  - --strict を付けると警告も失敗扱い（exit code 1）になります。
- 実行スクリプト:
  - 実行エンジン: python -m kabusys.run_execution
  - 監視プロセス: python -m kabusys.run_monitoring
- PAPER_TRADING モードでは paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番監視 DB と分離します。
- Monitoring は設計上、環境にかかわらず本番 sqlite_path を使用します（監視は本番データに対して行う想定のため）。

今後の課題（例）
- async 対応: KabuStationClient を httpx.AsyncClient に置き換えて非同期処理を検討する。
- より詳細な YAML 設定スキーマ検証（PyYAML が存在する場合の強化）。
- 単体テスト・統合テストの追加（特にクラッシュ時の再起動/リコンシリエーション動作の網羅）。

---

（注）この CHANGELOG は現在のコードベースからの推測に基づいて作成しています。実際の開発履歴やコミットログと差分がある場合は、適宜更新してください。