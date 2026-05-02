Keep a Changelog に準拠した変更履歴（日本語）
すべての注目すべき変更を記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
- （なし）

0.1.0 - 2026-05-02
Added
- パッケージ初期リリース（__version__ = "0.1.0"）。
- 多数の CLI エントリポイントを追加:
  - 実行系・監視・レポート系:
    - run_execution: ExecutionEngine 起動スクリプト（本番/ペーパートレードの DB 分離、起動時リコンシリエーション、ExecutionEngine のデーモンスレッド起動、停止フラグ監視、PID ファイル管理）。
    - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL 環境変数で間隔上書き、監視用 sqlite は環境に依らず本番パス使用、PID/停止フラグ管理）。
    - run_intraday_monitor: ザラ場中監視用 CLI（1回表示／ウォッチモード、JST 表示、ステータス判定ロジック）。
    - run_pre_market_report: Pre-Market Report 生成 CLI（duckdb / sqlite 取得、JSON/保存オプション、タスク・停止フラグの考慮）。
    - run_market_close_report: Market Close Summary 生成 CLI（duckdb / sqlite 取得、JSON/保存オプション、終了コード制御）。
    - run_performance_report: 運用成績サマリーレポート（daily/weekly/monthly、期間指定、env 指定、保存オプション）。
    - run_position_reconciliation_report: Position Reconciliation View（ウォッチモード対応、broker 接続、JSON/保存オプション）。
    - run_signal_queue_report: Signal Queue Confirmation View（日時指定、JSON/保存、退出ステータス）。
  - 運用支援ツール:
    - config_setup: 対話式 .env 作成ウィザード（既存読み込み、シークレットマスク、保存）。
    - validate_config: 設定検証 CLI（必須環境変数チェック、config/*.yaml 存在・パース検証、--strict モード）。
    - tools/paper_verification_report: ペーパートレード検証レポート生成スクリプト（稼働率、注文成功率・送信率、レイテンシ P95 などの計算）。
- 設定 / 環境読み込み周りの追加・改善:
  - config.Settings クラスを導入し、環境変数アクセスを整理（J-Quants / kabuAPI / LINE / DB パス / PID パス / Kill Switch 等）。
  - .env 自動読み込み機能を追加 (.env, .env.local)。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - プロジェクトルート判定ロジックを導入（.git または pyproject.toml を探索）。
  - .env パーサを強化: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、空行/コメント行の無視に対応。
  - .env 読み込み時の上書きルール: OS 環境変数は保護される（.env.local は既存 OS 環境を上書きしない）。
- 実行時振る舞い・堅牢化:
  - run_monitoring/run_execution でプロセス優先度を "high" に設定するユーティリティ呼び出しを追加。
  - run_monitoring: 監視ループで例外を捕捉してログ出力し、次回ポーリングへフォールバックするように変更。
  - run_execution: 起動時にブローカーから現金とポジションを取得して起動時総資産を算出し、RiskManager の初期値に使用。
  - run_execution: risk_config.yaml の読み込みロジックを実装し、必須キーの存在検査・型変換・範囲検証（max_position_pct, max_utilization, max_drawdown は (0,1]、rate_limit 等は >=1）を行う。
  - 各種レポート CLI に JSON 出力および artifacts への保存オプションを追加（保存時に保存先を出力）。
- DB / データベース連携:
  - duckdb および sqlite3 接続を各 CLI に導入（read_only モードや URI 指定を使用する箇所あり）。
  - 監視用 DB の初期化関数 init_monitoring_db を呼び出してテーブル存在を保証（冪等）。
- レポート / 収集ロジック:
  - intraday_collector, performance_collector, pre_market_collector, market_close_collector, position_reconciliation, signal_queue_report などを利用するエントリポイントを実装（各レポートのビルド・フォーマット・保存フローを統一）。
  - run_intraday_monitor の CLI 出力はステータス(OK/WARNING/CRITICAL) に応じた視認性の高い文字列（絵文字等）で表示。
- その他ユーティリティ:
  - .env 作成用ウィザードの出力テンプレートに注意書き（.env を絶対に Git にコミットしない）を追加。
  - 一部ファイル操作での安全処理（PID 書き込み、missing_ok=True での削除等）を導入。

Changed
- .env の自動読み込み順序を明確化: OS 環境変数 > .env.local > .env（OS 環境は保護）。
- run_execution における DB 接続先の分岐: KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用してペーパートレード DB と本番 DB を完全分離。
- run_monitoring は KABUSYS_ENV にかかわらず監視用 sqlite_path（本番パス）を使用するように明記。

Fixed
- 環境変数によるポーリング間隔設定の堅牢化:
  - MONITOR_POLL_INTERVAL の値が 0 や負の値、整数以外だった場合にデフォルト値へフォールバックして警告を出す処理を追加（time.sleep での ValueError 回避）。
- .env パースの不正ケースに対する耐性強化（空キーや不正行を無視）。
- run_pre_market_report / run_market_close_report 等の JSON 出力時に保存先メッセージが標準出力を汚染しないよう stderr を使う処理を適宜導入。

Security
- 特になし。

Removed
- 特になし。

Notes / Migration
- .env の自動読み込みに依存する挙動が導入されています。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番環境（KABUSYS_ENV=live）では .env の設定や KILL_FLAG_CLEAR_ON_START の値に注意してください（validate_config の live ガードが警告を出します）。
- risk_config.yaml の値に対して厳密な検証が追加されました。既存の設定ファイルが要件（型・範囲）を満たしているか確認してください。

---- End of changelog ----

必要であれば各リリースノート項目をより詳細（対象ファイル、関数名、エラーメッセージ例など）に拡張できます。どの程度の粒度で記載するか指示してください。