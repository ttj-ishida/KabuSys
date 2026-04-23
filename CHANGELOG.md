CHANGELOG
=========

すべての注目すべき変更点をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- なし（現状は v0.1.0 が初期リリース）。


0.1.0 - 2026-04-23
------------------

Added
- 基本アーキテクチャとコア機能を実装した最初のリリース。
  - パッケージメタ情報:
    - バージョン: 0.1.0
    - パッケージ説明: KabuSys — 日本株自動売買システム
  - 環境/設定管理:
    - Settings クラスを実装し、環境変数から設定値を取得する API を提供。
    - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env パーサを実装（export 形式、クォート値（エスケープ対応）、インラインコメント扱い等をサポート）。
    - .env 読み込み順序: OS 環境 > .env > .env.local（.env.local は上書き）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数取得用の _require() を実装（未設定時は ValueError）。
  - 環境設定ウィザード:
    - python -m kabusys.config_setup による対話式ウィザードを実装。
    - .env の読み書き（テンプレートヘッダー、主要設定項目の初期項目群）。
    - シークレット項目のマスク表示、選択肢・デフォルト提示、保存確認。
  - 設定検証 CLI:
    - python -m kabusys.validate_config により .env と config/*.yaml の起動前チェックを実行。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを実装。
    - config/*.yaml の存在確認と、PyYAML が利用可能なら YAML のパース検証を行う（PyYAML 未インストール時はパース検証をスキップして警告）。
    - 警告をエラー扱いにする --strict オプションを追加。
  - 実行系起動スクリプト:
    - run_execution.py:
      - ExecutionEngine 起動スクリプトを提供。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（隔離）を使用。
      - 停止フラグ（data/stop_requested.flag）検知、PID ファイル管理、プロセス優先度設定を実装。
    - run_monitoring.py:
      - SystemMonitor ポーリングループ起動スクリプトを提供。
      - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
  - 実行エンジン:
    - ExecutionEngine 実装（signal queue ベースの発注フロー）。
    - EngineConfig によりターゲット日付や時間帯（発注開始/締切/市場クローズ）を設定可能。
    - シグナル処理（Gate1: シグナル検査、Gate2: 実行レート制御、Gate3: ドローダウン監視）を実装。
    - kill_switch によりセッション全体の停止と全 active 注文のキャンセルを行う。
    - WebSocket（kabu push）対応のスレッドを実装し、push を受け取って同期処理へ投入。
    - position_entries テーブルへの約定予定日の記録を行い、発注フローからの監視 DB へのログ書き込みをサポート（監視 DB オプション）。
  - 注文関連（Execution 層）:
    - OrderRecord: 注文状態遷移ロジックとデータモデルを純粋ロジックとして実装（DB 非依存）。
      - 状態列挙: created / sent / accepted / partial / filled / closed / cancelled / rejected
      - 許可遷移テーブルと transition_to による遷移検証（不正遷移で例外）。
    - OrderManager:
      - signal_id 単位での重複注文防止（DuplicateOrderError）。
      - create_order() で OrderCreated レコード生成 & 保存。DB の unique 制約違反を DuplicateOrderError に変換。
      - send_order() で安全な 2 相永続化戦略:
        1) OrderSent へ遷移してコミット（broker 呼び出し前）
        2) broker 呼び出し
        3a) broker_order_id を先にコミット（state は Sent のまま）
        3b) OrderAccepted へ遷移してコミット
        - OrderRejectedError／OrderSentPendingError の扱いに対応
      - sync_order() で broker 側のステータスと同期。状態が同じでも部分約定情報（filled_qty / avg_fill_price）の更新を反映。
      - cancel_order() はローカル状態を参照し、終端状態ではキャンセル不可（InvalidStateTransitionError）。
    - OrderRepository（呼び出し元として利用）との連携を想定。
  - ブローカークライアント:
    - KabuStationClient を実装（httpx を使用した同期 REST クライアント）。
      - トークン取得と自動再取得、401 リトライ、429（RateLimit）および >=500 のサーバエラーの取り扱い。
      - JSON パース失敗を BrokerAPIError に変換。
      - WebSocket push（stream_push）を想定した設計（stream_push が無ければ警告してスキップ）。
  - リスク管理 / リコンシリエーション / 監視:
    - ExecutionEngine から RiskManager / Reconciler / Monitoring DB を利用するフローを用意（各コンポーネントは呼び出し/連携）。
  - その他ユーティリティ:
    - process_priority 設定ユーティリティを使用して、起動時にプロセス優先度を高く設定。
    - ロギング設定ユーティリティを使用してプロセス別のログ初期化を実施。

Changed
- 新規リリースのための初期実装のみ。既存機能の変更はなし。

Fixed
- 初期実装リリースのための実装上の注意事項やエラーハンドリングを強化:
  - .env 読み込みでファイルオープン失敗時に警告を出す（warnings.warn）。
  - MONITOR_POLL_INTERVAL の不正値を検知してデフォルトへフォールバック（警告ログ）。
  - ExecutionEngine の起動時に kill.flag の存在判定と clear_on_start 設定の尊重。

Security
- .env ファイルは「Git にコミットしない」ことをドキュメント化（config_setup に注意書き追加）。
- シークレット値は UI 上でマスク表示（config_setup の確認画面等）。

Notes / Known limitations
- YAML のパース検証は PyYAML がインストールされている場合のみ実行され、未インストール時は警告を出してスキップする仕様。
- KabuStationClient は同期 httpx.Client を使用。将来的に非同期対応が必要な場合は AsyncClient への移行が見込まれる。
- 一部のコンポーネント（RiskManager, Reconciler, OrderRepository, MonitoringDB など）はこのリリースでの統合ポイントを提供するが、実際の実装・詳細は別モジュールで定義される（本 CHANGELOG はパッケージ全体のスナップショットに基づく要約）。

--- 

（本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。リリースノートや日付は状況に合わせて調整してください。）