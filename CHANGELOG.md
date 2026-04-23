Keep a Changelog
================

すべての注目すべき変更点をこのファイルで記録します。  
このプロジェクトでは Keep a Changelog の形式に準拠します。

[Unreleased]: https://example.org/changelog/unreleased
[0.1.0]: https://example.org/changelog/0.1.0

0.1.0 - 2026-04-23
------------------

Added
- 初期リリース: KabuSys 自動売買システムの基本コンポーネントを追加。
- 設定管理
  - 環境変数/ .env ファイルを扱う Settings クラスを追加（src/kabusys/config.py）。
  - 自動 .env ロード機能を実装: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env、.env.local を読み込み。OS 環境変数優先、.env.local は上書き可。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーを強化: export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応、インラインコメントの扱い改善（src/kabusys/config.py）。
  - 必須取得ヘルパー _require() を提供し、未設定時に明確なエラーを出す。
  - PAPER_FILL_MODE 等の入力検証を実装（有効値チェック）。
- 環境設定ウィザード
  - 対話式 CLI で .env を作成/更新する config_setup（src/kabusys/config_setup.py）を追加。
  - シークレット項目は表示時にマスク、デフォルトや既存値の再利用をサポート。.env 書き込みテンプレートに注意書き（Git にコミットしないこと）を含む。
- 設定検証ツール
  - validate_config CLI（src/kabusys/validate_config.py）を追加。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在・YAML パース確認（PyYAML があればパースも実施）。--strict オプションで警告を FAIL 扱いにできる。
- 実行/監視スクリプト
  - ExecutionEngine 起動スクリプト run_execution（src/kabusys/run_execution.py）と SystemMonitor 用 run_monitoring（src/kabusys/run_monitoring.py）を追加。両方とも起動直後にプロセス優先度を設定し、logging を初期化して DB（SQLite/ DuckDB）へ接続する。
  - run_monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用する旨を明記。
- 実行エンジンと発注フロー
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）を実装。シグナル処理ループ（発注時間帯）と WebSocket push ドレインループを備える。reconciler による起動時リコンシリエーション、PID/kill.flag の取り扱い、kill_switch による全アクティブ注文キャンセル処理を実装。
  - OrderManager（src/kabusys/execution/order_manager.py）を実装。create/send/sync/cancel の高レベル API を提供し、DB 永続化と broker API 呼び出しの順序（クラッシュ耐性を考慮した 2 段階扱い）を設計。DuplicateOrderError を導入して同一 signal_id の重複発注を防止。
  - OrderRecord（src/kabusys/execution/order_record.py）で状態遷移を純粋ロジックとして管理。許容遷移テーブルと不正遷移時の InvalidStateTransitionError を提供。
  - send_order の実装は broker_order_id を先に保存してから OrderAccepted に遷移するなど、クラッシュ時の復旧（Reconciliation）を考慮した永続化順序を採用。OrderSentPendingError（送信済みだが未約定等）を適切に処理し、pending 状態を DB に残す。
  - sync_order で broker 側のステータスを取得してローカル状態を同期。部分約定の進行は状態変化なしでも filled_qty/avg_fill_price の差分更新を行う。
- ブローカークライアント
  - KabuStationClient（src/kabusys/execution/kabu_client.py）を実装。httpx を使った同期 REST クライアント、トークン取得の遅延初期化と 401 に対する再取得・リトライ、429（レート制限）や 5xx に対するエラー分類を実装。kabu ステータスコード→内部ステータスのマッピングを追加。
- リスク管理・監視統合
  - ExecutionEngine 内で RiskManager による Gate1/Gate2/Gate3 チェックを組み込み（レート制限、サーキットブレイカ、ドローダウン監視）。監視用 DB（MonitoringDB）が渡された場合は発注イベントのログを書き込むフックを追加。
- DB/環境分離
  - paper_trading 環境向けに paper_sqlite_path を用意し、paper_trading 時は監視/発注の本番 DB から分離して専用 DB を使用するように設計（run_execution と Settings.paper_sqlite_path）。

Changed
- ログ・プロセス管理
  - 起動スクリプトが最初にプロセス優先度を高く設定するように変更（set_process_priority 呼び出し）。
- kill.flag の扱い
  - ExecutionEngine 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START の値に応じて自動クリアするか起動を拒否する挙動を導入。run_execution/run_monitoring でも同様のチェックを行う。

Fixed
- .env の読み書きにおけるエッジケース対応
  - 値のクォート内でのバックスラッシュエスケープと閉じクォート検出を正しく扱うように改善。インラインコメントの判定ロジックを改善（src/kabusys/config.py）。
- DB 初期化
  - 監視 DB の初期化処理 init_monitoring_db を起動時に必ず呼び出すようにして、監視テーブルが存在しないケースに対処（冪等性を考慮）。

Security
- .env の取り扱い注意を明記（config_setup にて .env を絶対に Git にコミットしない旨をテンプレートに追加）。
- 設定ウィザードではシークレット項目を表示時にマスク。

Known issues / Notes
- validate_config は PyYAML が未インストールだと YAML のパース検証をスキップし、警告を出す（ユーザに PyYAML のインストールを推奨）。
- KabuStationClient は同期 API（httpx.Client）実装。将来的に非同期化する場合は httpx.AsyncClient への切り替えが容易にできる設計。
- ExecutionEngine の時間帯（8:50–9:10、9:10–15:30）は EngineConfig で上書き可能。テストでは内部メソッドを直接呼び出してセッションを短縮して検証することが想定されている。

未分類 / 内部
- パッケージバージョンを __version__ = "0.1.0" として設定（src/kabusys/__init__.py）。

(この CHANGELOG はコード内容から推測して作成しています。実際のコミットログやリリースノートと差異がある可能性があります。)