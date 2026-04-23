# Changelog

すべての重要な変更点をここに記載します。本ファイルは Keep a Changelog の形式に準拠しています。  

注: 日付はこのリリース時点の日付です。

## [Unreleased]

## [0.1.0] - 2026-04-23

### 追加
- 初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。
- パッケージ情報
  - バージョン: 0.1.0（src/kabusys/__init__.py）
- 設定・環境管理
  - Settings クラスによる環境変数/設定の集中管理を導入（src/kabusys/config.py）
    - J-Quants / kabu API / LINE / DB パス /監視・システム設定などのプロパティを提供
    - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。不正な値は ValueError を発生
    - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
    - .env のパースはシングル/ダブルクォートやエスケープ、インラインコメント等に対応
- 対話式設定ウィザード
  - config_setup CLI を追加（src/kabusys/config_setup.py）
    - python -m kabusys.config_setup で .env の初期作成・更新を対話形式で行える
    - デフォルト値、選択肢、シークレット項目のマスク表示、保存確認機能を実装
    - .env を生成・上書きする際にテンプレートヘッダを付与（Git にコミットしないよう注意喚起）
- 設定検証ツール
  - validate_config CLI を追加（src/kabusys/validate_config.py）
    - .env と config/*.yaml の内容を起動前に検証
    - 必須環境変数の未設定チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DBパスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 未インストール時はスキップ）
    - --strict オプションで警告を FAIL として扱う（終了コード1）
    - 実行例: python -m kabusys.validate_config
- 実行用スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度設定、PID ファイル書き出し、stop flag / kill flag の監視、paper_trading と本番 DB の分離（paper_trading は paper_sqlite_path を使用）
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き、監視用 DB (SQLite) と DuckDB 接続の初期化
- Execution / Order 管理
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナル処理（8:50-9:10）→ push ドレイン（9:10-15:30）というセッション実行フローを実装
    - WebSocket push の受信スレッド（broker が stream_push を提供する場合）と内部キューによる同期処理
    - kill_switch による全 active 注文キャンセル機構と Gate チェック（Gate1: シグナル検査、Gate2: エグゼキューション検査、Gate3: ドローダウン監視）
    - position_entries への約定情報記録（DuckDB を利用）
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態（OrderState）の列挙と許可遷移を定義する状態遷移ロジック
    - 不正遷移は InvalidStateTransitionError を送出
  - OrderManager（src/kabusys/execution/order_manager.py）
    - OrderRecord と OrderRepository を組み合わせた外向き API（作成・送信・同期・取消）
    - send_order におけるクラッシュ耐性を意識した二相永続化のフローを実装（OrderSent を永続化してから broker 呼び出し → broker_order_id を保存 → OrderAccepted に遷移）
    - OrderSentPendingError, OrderRejectedError 等を適切に扱う（pending の永続化等）
    - DuplicateOrderError を導入（同一 signal_id の active 注文重複を検知）
  - Execution 側でのモニタリング連携: 発注イベントの監視DBへのログ記録（監視DBが渡された場合）
- broker / kabu client
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx による同期 REST クライアント実装
    - トークン取得の遅延初期化と 401 時のトークン再取得・リトライ
    - レート制限(429) とサーバーエラーのハンドリング、タイムアウト/ネットワークエラーを BrokerAPIError に変換
    - WebSocket push (websocket ライブラリ) を用いた通知受信の枠組み（stream_push を想定）
- リスク／リコンシリエーション／監視の連携ポイント（各モジュールから利用）
  - RiskManager, Reconciler, MonitoringDB 等の統合ポイントを ExecutionEngine と OrderManager が利用する設計（実装の呼び出し箇所を追加）

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 削除
- なし（初回リリース）

### セキュリティと運用上の注意
- .env は絶対に Git にコミットしないことを README/生成テンプレートで明示
- validate_config や config_setup によるチェックを起動前に実行することを推奨
- KABUSYS_ENV=live の場合は追加の警告や動作差異（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の値チェック）が入るため本番稼働前に十分に確認すること
- PID ファイル / kill.flag の存在により起動や動作が左右されるため、運用手順に沿ったフラグ管理を行ってください

### 互換性 / 移行
- Settings が環境変数を直接参照し、不正な値で例外を送出するため、既存の環境変数設定を validate_config で事前検査することを推奨します。
- paper_trading 環境では SQLite のパスが切り替わる（本番 DB と完全分離）。運用時に設定確認を怠らないでください。

---

メンテナンス上の問い合わせや不具合報告は issue にてお願いします。