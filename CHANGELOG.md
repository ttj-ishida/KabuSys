# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-23

### 追加
- プロジェクト初期リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。
- 環境/設定関連
  - Settings クラスを追加（src/kabusys/config.py）。環境変数から各種設定を取得・検証するプロパティを提供。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。OS 環境変数を保護して読み込み順序を管理（OS > .env.local > .env）。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（クォート、エスケープ、コメント処理対応）。キーの上書き制御（override/protected）をサポート。
  - 対話式の設定ウィザード CLI を追加（src/kabusys/config_setup.py）。.env の初期作成・更新を支援。保存テンプレートに注意書き（.env を Git にコミットしない）を記載。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース確認（PyYAMLがない場合は警告）、KABUSYS_ENV=live の追加ガードを実装。--strict オプションで警告を FAIL 扱いにできる。
- 実行・監視スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。プロセス優先度設定、DB 初期化、ExecutionEngine の起動および停止フラグ監視を実装。paper_trading 環境では専用 SQLite（paper_trading.db）を使用し、本番 DB と分離。
  - SystemMonitor をポーリングする監視スクリプトを追加（src/kabusys/run_monitoring.py）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境に関わらず本番 sqlite_path を使用。
- 発注関連コア
  - ExecutionEngine 実装（src/kabusys/execution/execution_engine.py）。シグナルループ（8:50–9:10）と push ドレインループ（9:10–15:30）を含むセッション制御、WebSocket push 処理、ポジション/position_entries 更新、監視DBへのトレードイベント記録フック等を実装。
  - OrderRecord（状態遷移モデル）を実装（src/kabusys/execution/order_record.py）。状態列挙 OrderState と許可遷移テーブル、遷移検証・タイムスタンプ更新を提供。InvalidStateTransitionError を定義。
  - OrderManager（外向き API）を実装（src/kabusys/execution/order_manager.py）。create/send/sync/cancel のワークフロー、重複注文検出（DuplicateOrderError）、send_order の「事前 OrderSent 永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 永続化」という二相永続化設計（クラッシュ耐性向上）を実装。OrderSentPendingError（保留）や OrderRejectedError の扱いを定義。
  - Execution 用の各種依存（OrderRepository / Reconciler / RiskManager 等）と連携する構成を実装（コード中で組み立て）。
- ブローカー（kabu station）クライアント
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。httpx を使った同期 REST クライアント。トークン取得・自動再取得、401 リトライ、429（レート制限）・500 系エラーの扱い、JSON パースエラー変換、WebSocket (push) の購読（stream_push）連携を想定。
- DB/監視/プロセス
  - DuckDB（分析用）と SQLite（監視/履歴）を組み合わせて使用。DuckDB はシグナル読み込みや position_entries 管理に使用。
  - PID ファイルの書き出し/削除、停止フラグ(stop_requested.flag / kill.flag)の検査・挙動（kill_switch）を実装。kill_switch は全 active 注文のキャンセルを試みる。
  - プロセス優先度設定とロギングセットアップフックを追加（utils 側参照）。
- リスク制御
  - RiskManager と Gate 構成（Gate1: シグナル、Gate2: 実行/レート制限、Gate3: ドローダウン監視）を実装し、必要に応じて kill_switch を発動する設計を反映。
- その他
  - パッケージの __version__ を "0.1.0" に設定。

### 変更
- （初期リリースのため変更履歴なし）

### 修正
- （初期リリースのため修正履歴なし）

### 既知の注意点 / セキュリティ
- .env ファイルには機密情報（API トークンやパスワード）が含まれるため、絶対に Git リポジトリにコミットしないでください（config_setup.py にも注意書きあり）。
- KABUSYS_ENV=live の場合は追加の警告チェックが入るが、本番運用前に必ず validate_config を実行して設定を確認してください。
- send_order の設計はクラッシュ耐性に配慮しているが、外部 broker の仕様に依存する部分があるため実環境での検証が必要です。

---

（この CHANGELOG はコードベースから推測して作成しました。細かな API 仕様や外部モジュールの実装状況に応じて内容を更新してください。）