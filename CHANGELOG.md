# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

<!-- NOTE: 日付はソースコード読み取り時点の推測日を使用しています。 -->

## [Unreleased]

- ドキュメント／マイナー改善など、次回リリースに含める可能性のある変更を記載。

## [0.1.0] - 2026-04-23

### Added
- 初期リリースを追加（KabuSys 日本株自動売買システムの基本機能群）
- 設定・環境周り
  - .env 自動読み込み機能を追加（プロジェクトルート（.git / pyproject.toml）基準で探索）。環境変数は OS > .env.local > .env の優先順位で適用。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。（src/kabusys/config.py）
  - 高度な .env パーサ実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの処理に対応。無効行（コメント等）は無視。（src/kabusys/config.py）
  - .env ファイル読み書きユーティリティと対話式ウィザードを追加（python -m kabusys.config_setup）。シークレット値はマスク表示、既存値の再利用、選択肢/デフォルトのサポートあり。（src/kabusys/config_setup.py）
  - Settings クラスを追加し、環境変数を型付きアクセサ（Path/float/bool/str）で取得。PAPER_FILL_MODE 等の値検証を実施。（src/kabusys/config.py）
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数の未設定/プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の検証、DB パスや config/*.yaml の存在・パースチェック、KABUSYS_ENV=live 時の追加ガードを実装。--strict オプションで警告を FAIL 扱いに可能。（src/kabusys/validate_config.py）
- 実行/監視スクリプト
  - ExecutionEngine 起動スクリプトを追加（python -m kabusys.run_execution）。プロセス優先度設定、PID ファイル管理、stop フラグ検出、paper_trading の DB 分離などを実装。（src/kabusys/run_execution.py）
  - Monitoring ポーリングスクリプトを追加（python -m kabusys.run_monitoring）。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、停止フラグ検出、SQLite/DuckDB の接続初期化を実装。（src/kabusys/run_monitoring.py）
- 発注・状態管理
  - OrderRecord：注文状態を表す State Machine を純粋ロジックとして実装（遷移検証、更新時刻自動更新、オプションフィールド更新）。InvalidStateTransitionError を定義。（src/kabusys/execution/order_record.py）
  - OrderManager：signal からの注文生成、送信、同期（sync）、キャンセルの外向き API を実装。DuplicateOrder 検出、クラッシュ耐性を考慮した 2 段階永続化（OrderSent と broker_order_id の扱い）、OrderSentPending の扱い、sync_order によるブローカー照合を実装。（src/kabusys/execution/order_manager.py）
  - ExecutionEngine：シグナル処理ループ、WebSocket push ドレインループ、Gate1/2/3 によるリスクチェック、kill_switch による全注文キャンセル、position_entries へ約定記録などの発注フローを実装。実行時のリコンシリエーション呼び出しや PID ファイル管理も含む。（src/kabusys/execution/execution_engine.py）
  - Reconciler / RiskManager 等との連携を想定した設計（モジュール間インタフェース利用）。
- ブローカークライアント
  - KabuStationClient（kabu station REST API クライアント）を実装。httpx を用いた同期クライアント、トークン自動取得／再取得（401 時のリトライ）、レスポンス JSON パース例外の BrokerAPIError 変換、429/5xx の処理を実装。stream_push を利用した WebSocket push 処理に対応する設計。（src/kabusys/execution/kabu_client.py）
- データベース
  - DuckDB と SQLite を併用するアーキテクチャを導入（分析用 DuckDB / 監視・履歴用 SQLite）。monitoring 用 DB 初期化ユーティリティを追加。（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py, 監視モジュール）
- 監視（Monitoring）
  - 発注遅延・イベントを監視 DB に記録する仕組みを組み込み（ExecutionEngine からのログ書き込み呼び出し箇所あり）。（src/kabusys/execution/execution_engine.py）

### Changed
- ロギング＆運用
  - 起動時にプロセス優先度を "high" に設定するユーティリティを呼び出すように（monitoring/execution）。PID ファイルや停止フラグの扱いを統一。  
  - 実行環境（KABUSYS_ENV）に応じた動作差分を明確化（paper_trading では paper_sqlite_path を使用して本番 DB と分離）。（src/kabusys/config.py, run_execution.py）
- .env の読み書き挙動を明確化：既存 OS 環境変数は protected として書き換えを制御。config_setup による .env 生成テンプレートを追加し、コミット禁止の注意書き含む。（src/kabusys/config.py, src/kabusys/config_setup.py）

### Fixed
- 発注フローのクラッシュ耐性を強化
  - send_order において「OrderSent を DB に残してから broker 呼び出し」「broker_order_id を先に永続化してから Accepted に遷移」する手順により、クラッシュ時でも Reconciliation による復旧が可能となる設計を導入。（src/kabusys/execution/order_manager.py）
- .env パースの不正解釈を改善
  - クォート内のバックスラッシュエスケープ処理やインラインコメント判定を改善し、複雑な .env の値取り扱いの誤動作を修正。（src/kabusys/config.py）

### Security
- シークレット値の取り扱い改善
  - config_setup の対話でシークレットをマスク表示し、.env のサンプルや生成方法でシークレット漏えいに関する注意書きを追加。（src/kabusys/config_setup.py）

### Notes / Migration
- 環境変数の読み込み順序が導入されています。既存運用で .env.local を使う場合や OS 環境変数に依存する場合は、優先順位（OS > .env.local > .env）に注意してください。
- Settings クラスは環境値の検証を行い、不正な値では ValueError を送出します（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）。自動起動環境では設定の事前検証（python -m kabusys.validate_config）を推奨します。
- 本番運用時は KABUSYS_ENV=live の設定により追加の警告とガードが働きます。特に KILL_FLAG_CLEAR_ON_START=1 は本番では推奨されません。
- paper_trading モードでは paper_trading 専用の SQLite DB が使用され、本番 DB と分離されます。

---

（この CHANGELOG はリポジトリ内のソースコード構成・コメントから推測して作成しています。実際のリリース履歴や日付はプロジェクトの運用に合わせて更新してください。）