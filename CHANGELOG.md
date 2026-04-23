CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠しています。ロードマップや互換性に関する情報は各リリースノートを参照してください。

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-23
-------------------

初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。
主な追加・改善点は以下の通りです。

Added
- 環境設定管理（src/kabusys/config.py）
  - .env および .env.local の自動読み込み機能（プロジェクトルート検出：.git / pyproject.toml 基準）。
  - OS 環境変数を保護する protected keys 機構。
  - .env の行パーサを実装。export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理をサポート。
  - Settings クラスを提供し、設定値を型（Path, float, bool 等）で取得可能に。
  - PAPER_FILL_MODE などの列挙的な検証ロジックを実装。

- 対話式設定ウィザード（src/kabusys/config_setup.py）
  - .env を対話式に作成/更新する CLI を追加。秘匿項目は表示をマスク。
  - 標準項目（J-Quants トークン、kabu API パスワード、DB パス等）のテンプレート生成機能を実装。

- 設定検証 CLI（src/kabusys/validate_config.py）
  - .env と config/*.yaml の存在および基本的妥当性を起動前に検査。
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定検出。
  - プレースホルダ値（例: *_here, "your_value"）の警告。
  - KABUSYS_ENV / LOG_LEVEL の値検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知、KILL_FLAG_CLEAR_ON_START の注意喚起）。
  - --strict オプションで警告を FAIL 扱いにする機能。
  - PyYAML がない場合は YAML 検証をスキップする旨の警告。

- 実行スクリプト（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）
  - ExecutionEngine / SystemMonitor の起動エントリを提供。
  - プロセス優先度設定、PID/停止フラグ処理、DB 初期化（SQLite / DuckDB）を実装。
  - 監視ループのポーリング間隔を MONITOR_POLL_INTERVAL で上書き可能とし、不正値はデフォルトにフォールバック。

- 発注エンジンコア（src/kabusys/execution/*）
  - OrderRecord（状態マシン）を実装。許容遷移テーブルと InvalidStateTransitionError を提供。
  - OrderManager による create/send/sync/cancel ワークフローを実装。DuplicateOrderError を導入。
  - send_order の 2 相永続化（OrderSent -> broker_order_id 永続化 -> OrderAccepted）でクラッシュ耐性を高め、Reconciliation をサポート。
  - sync_order で部分約定の差分更新に対応。
  - ExecutionEngine を実装し、シグナル処理（Gate1/Gate2）、push ドレイン（Gate3）、kill_switch、WebSocket ワーカ、PID 管理等を含むセッション制御を提供。
  - paper_trading モード時に paper_trading 用 SQLite を分離して利用する機能を実装。

- kabuステーション API クライアント（src/kabusys/execution/kabu_client.py）
  - KabuStationClient を追加。httpx を使った同期 API 呼び出し、トークンの遅延取得と 401 リトライ、429（レート制限）・5xx ハンドリングを実装。
  - kabu ステータスコード → 内部ステータスマッピングを追加。

- 監視 DB 連携
  - 発注イベント等を監視 DB に記録するための呼び出し箇所を ExecutionEngine に追加（監視 DB が与えられた場合）。

Changed
- .env パーサの仕様明確化（src/kabusys/config.py）
  - クォート内のバックスラッシュエスケープ、export キーワード対応、インラインコメントの扱いを改善。
- .env 自動ロードの優先度
  - OS 環境 > .env.local > .env の順序で読み込む仕様を導入。OS 環境は protected として上書き不可。
- kill.flag の扱い（src/kabusys/execution/execution_engine.py）
  - 起動時の kill.flag 検査を PID 書き込みより先に行い、KILL_FLAG_CLEAR_ON_START による自動クリア挙動を実装。
- ログレベル / 環境値の扱い
  - validate_config と Settings の両方で KABUSYS_ENV / LOG_LEVEL の検証ロジックを整合化。

Fixed
- send_order / sync_order のクラッシュ耐性向上（src/kabusys/execution/order_manager.py）
  - broker_order_id を先に永続化する手順を採用し、クラッシュ後の Reconciliation による復元を容易に。
- MONITOR_POLL_INTERVAL の不正値ハンドリング（src/kabusys/run_monitoring.py）
  - 0 以下や非整数が指定された場合は警告を出してデフォルトにフォールバック。
- YAML 依存性の取り扱い（src/kabusys/validate_config.py）
  - PyYAML が未インストールでも検証が致命的に停止しないようにし、存在しない場合は YAML 検証をスキップして警告を出すよう変更。

Security
- .env は絶対に Git にコミットしない旨を config_setup の生成ヘッダに明記。

注記（マイグレーション / ユーザ向け情報）
- 初回起動前に .env を作成し、python -m kabusys.validate_config で設定を検証してください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）および KILL_FLAG_CLEAR_ON_START の値に注意してください（デフォルトは 0）。
- paper_trading モードは本番 DB と監視 DB を分離します。Paper 用 DB パスは PAPER_TRADING_SQLITE_PATH で上書き可能です。

開発者向け
- バージョンは src/kabusys/__init__.py に定義されています（現在: 0.1.0）。
- 自動環境読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。

--- 

今後の予定（例）
- Broker API の詳細なエラーハンドリング強化および async 対応（httpx.AsyncClient への切替）検討。
- 監視メトリクスの拡充とダッシュボード連携。
- Reconciliation のさらなる堅牢化とテストカバレッジ拡大。