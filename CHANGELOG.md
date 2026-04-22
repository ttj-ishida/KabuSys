CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
（現在なし）

[0.1.0] - 2026-04-22
-------------------
初回公開リリース。以下の主要機能と実装を含みます。

Added
- 環境設定・読み込み
  - .env ファイルの自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。  
    OS 環境変数を保護しつつ .env と .env.local の読み込み順序をサポート（.env → .env.local、.env.local は上書き）。
  - .env パーサーの実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のエスケープ処理を考慮した値抽出。
    - クォート無し行におけるインラインコメント（'#'）の取り扱いをサポート。
  - Settings クラスを追加し、環境変数を型付きプロパティとして提供（トークン・DBパス・各種設定の取得を集中管理）。

- 設定ウィザード / 検証 CLI
  - 対話式 .env 作成・更新ツールを追加（python -m kabusys.config_setup）。必須/任意項目やデフォルトを提示し、シークレットはマスク表示。
  - 設定検証ツールを追加（python -m kabusys.validate_config）。必須環境変数の存在チェック、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL 等の妥当性チェック、DBパスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードなどを実施。--strict オプションで警告を失敗扱いにできる。

- 実行用スクリプト
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）を追加。paper_trading モード時は paper_trading 用 SQLite を使用して本番 DB と分離。
  - Monitoring ポーリングスクリプト（python -m kabusys.run_monitoring）を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能。Monitoring は環境にかかわらず本番 sqlite_path を使用。

- 発注・状態管理ロジック
  - OrderRecord（状態機械）を追加。OrderState 列挙型と明示的な遷移許可表（_ALLOWED_TRANSITIONS）を定義。transition_to により遷移検証と関連フィールド更新を行う。
  - OrderManager を追加。create/send/sync/cancel の外向き API を提供し、DuplicateOrder の検出や DB 整合性を考慮した実装を含む。
    - create_order は signal_id に対する部分ユニーク制約や既存 active 注文を検査し、DuplicateOrderError を投げる。
    - send_order はクラッシュ耐性を考慮した 2 相的な永続化手順（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted へ遷移）を実装。OrderRejectedError と OrderSentPendingError を適切に扱う。
    - sync_order は broker 側の状態を照合してローカル状態を更新。部分約定の進行は差分更新で扱う。
    - cancel_order はキャンセル不可能な状態を検査して適切に振る舞う（終端状態では InvalidStateTransitionError を送出）。

- リコンシリエーション / リスク管理連携
  - ExecutionEngine は起動時に Reconciler を実行可能（存在する場合）。クラッシュ後に残る OrderSent レコードや broker_order_id の痕跡から状態回復できる設計を採用。
  - ExecutionEngine 内のシグナル処理に Gate1/2/3（シグナルレベル・エグゼキューションレベル・ドローダウン監視）を組み込み。Gate2 のレート制限や回路遮断（circuit breaker）処理、Gate3 のドローダウン検出時の kill_switch 発動を実装。
  - 発注成功/失敗や pending 状態の監視イベントを Monitoring DB に記録するフックを追加（オプショナル）。

- broker / kabu client
  - KabuStationClient を追加（httpx ベースの同期 REST クライアント）。
    - API トークンの遅延取得とキャッシュ、401 発生時の自動トークン再取得とリトライを実装。
    - HTTP ステータスに基づく例外変換（429 → RateLimitError、5xx → BrokerAPIError 等）。
    - WebSocket（push）受信用の stream_push をサポートする設計（存在しない場合はスキップ）。

- DB / 監視
  - Monitoring DB 初期化ユーティリティ（init_monitoring_db）を提供し、監視用テーブル作成を保証。
  - DuckDB を用いたシグナル取得 / portfolio_targets 結合ロジックを ExecutionEngine に組み込み。

Changed
- 設定読み込みのデフォルト挙動
  - OS 環境変数が優先され、.env で未定義のキーのみ上書きされるデフォルト動作を採用。テスト等で自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- Settings のバリデーション
  - env や log_level、PAPER_FILL_MODE 等は不正値の場合に ValueError を送出して早期検知するように変更。
- データベースパスの扱い
  - 設定は expanduser() を利用して ~ を展開。run_monitoring は環境にかかわらず本番用 sqlite_path を使用する旨を明確化。
- ExecutionEngine
  - 起動時の kill.flag 挙動を改善（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアのオプションを提供）。PID ファイルの書き込み/削除を追加。
  - WebSocket push 処理は push payload から OrderID を取り出して該当注文を同期し、見つからない場合でもポートフォリオ評価（Gate3）を行う設計。

Fixed
- 発注のクラッシュ安全性
  - send_order の実装を見直し、broker_order_id の先行永続化や OrderSent の取り扱いにより Reconciliation での回復を容易にした。
- .env 読み込みエラーの通知
  - ファイル読み込み失敗時に warnings.warn で警告を出すようにし、読み込み失敗でプロセスが停止しないようにした。
- config YAML 検証
  - PyYAML が存在しない場合は YAML 内容検証をスキップして警告する（依存が無くても起動可能）。

Security
- .env の注意喚起を追加
  - config_setup にて生成する .env のヘッダに「.env を絶対に Git にコミットしないこと」を明記。

Notes
- 本リリースは初期実装に相当し、主要なコンポーネント（設定周り、発注エンジン、ブローカークライアント、監視、対話式設定ウィザード、検証ツール）を含みます。今後のリリースでテスト整備、エラーハンドリング強化、非同期対応（httpx.AsyncClient 等）、およびより詳細な運用ドキュメントの追加を予定しています。