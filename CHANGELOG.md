CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

[Unreleased]
------------

- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-23
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎機能を実装。
- 設定管理:
  - 環境変数管理モジュールを追加（src/kabusys/config.py）。
  - .env/.env.local の自動読み込み機構を実装（プロジェクトルート検出: .git / pyproject.toml）。
  - .env の堅牢なパーサを実装: export プレフィックス対応、クォート内エスケープ、行コメント処理をサポート。
  - OS 環境変数の保護（既存値を上書きしない / 上書き可否制御）と自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を導入。
  - Settings クラスを実装し、各種設定（API トークン・DB パス・ログレベル・PID/KILL フラグ・しきい値等）をプロパティ経由で取得・検証。

- 環境設定ウィザード:
  - 対話式 .env 生成/更新スクリプトを追加（src/kabusys/config_setup.py）。
  - 標準項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、ログレベル、KILL フラグ等）をサポート。
  - シークレットはマスク表示、既存値の再利用、デフォルト値の提示、保存前の確認を実装。

- 設定検証 CLI:
  - 起動前に .env と config/*.yaml を検証する CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、プレースホルダ値検出（*_here や your_value に対する警告）、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在確認、PyYAML があれば YAML のパース検証を実施。
  - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の警告）。
  - --strict モードで警告を FAIL（exit 1）扱いにできる。

- 実行スクリプト:
  - Execution エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
  - Monitoring ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
  - 両スクリプトともプロセス優先度設定、PID ファイル・停止フラグの扱い、DB 初期化の処理を実装。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。

- 発注エンジン / 実行フロー:
  - ExecutionEngine を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（8:50-9:10）と push ドレインループ（9:10-15:30）をサポート。
    - kill.flag の検査と KILL_FLAG_CLEAR_ON_START に基づく起動挙動。
    - PID ファイルの書き出し・削除、WebSocket push の受信スレッド、position_entries への書き込み、監視DB へのログ出力対応。
    - Gate1/2/3 による多段リスク検査（シグナルレベル / 実行レベル（レート制限） / ポートフォリオ指標によるドローダウン監視）を組み込み、NG 時は適切な制御（スキップ・kill_switch 発動）を行う。
    - OrderSentPending ケースの扱い、API レイテンシ計測、監視DB へのイベント記録。

- 注文関連コンポーネント:
  - OrderRecord（状態マシン）を実装（src/kabusys/execution/order_record.py）。
    - 明示的な状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許容遷移定義。
    - transition_to による遷移検証とタイムスタンプ・オプションフィールド更新。
  - OrderManager を実装（src/kabusys/execution/order_manager.py）。
    - create_order（重複 signal_id の検出および DB 整合性考慮）、send_order（クラッシュ耐性を意識した2相的永続化: OrderSent の永続化→broker 呼び出し→broker_order_id 保存→OrderAccepted 更新）、
      sync_order（broker 状態の同期と部分約定反映）、cancel_order（キャンセル可否判定）を提供。
    - DuplicateOrderError, InvalidStateTransitionError 等を導入。

- ブローカークライアント:
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 REST クライアント、トークン取得（遅延初期化＋401 時再取得とリトライ）、レスポンスの JSON パースエラーハンドリング。
    - kabu ステーションの注文状態コード → 内部ステータスへのマッピング、429（レート制限）/5xx/401 などのエラー分類 (RateLimitError / BrokerAPIError / OrderRejectedError 等)。

- その他ユーティリティ:
  - Monitoring DB 初期化、Reconciler / RiskManager / BrokerFactory 等の連携を想定したインターフェース利用（ファイル内での import／組み立て）。
  - DuckDB と SQLite を併用したデータ保存設計（本番と paper_trading の DB 分離）。

Changed
- .env パース仕様を強化:
  - export KEY=val 形式を許可、クォート文字内のバックスラッシュエスケープ対応、クォートなしの行ではインラインコメント（#）の扱いを慎重に処理。
- 環境変数読み込み順序を明確化（OS 環境 > .env.local > .env）。
- Paper trading 時のデータ分離をデフォルト動作として明確化（paper_trading 用 SQLite パスを使用）。
- validate_config の挙動改善: プレースホルダ検出や PyYAML 未インストール時のスキップメッセージ。

Fixed
- send_order の永続化タイミング調整により、クラッシュ後の状態復旧（Reconciliation）に必要な broker_order_id の情報損失を防止する設計に改良。
- ExecutionEngine の kill.flag 起動時の競合を軽減（起動時チェックと設定 KILL_FLAG_CLEAR_ON_START の扱いを明確化）。
- run_monitoring の MONITOR_POLL_INTERVAL が不正な値の場合にデフォルトへフォールバックする安全処理を追加。

Security
- config_setup においてシークレット項目は出力時にマスク表示。
- .env ファイル生成時に「.env を Git にコミットしない」旨をファイルヘッダに明記。

Notes / Implementation details
- いくつかのコンポーネント（BrokerClientFactory、Reconciler、RiskManager、MonitoringDB など）はこのリリース内での連携インターフェースを提供しており、外部実装または別モジュールでの詳細実装を想定しています。
- YAML の内容検証は PyYAML がインストールされている場合のみ実行されます。未インストール時は警告表示してスキップします。
- 本ログはソースコードの内容から推測して作成しています。実際のリリースノートとは差分がある可能性があります。