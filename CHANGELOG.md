CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。
タグ付けやリリース日付はコードベースの状態から推測して記載しています。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-05-01
--------------------

Added
- コマンドライン／運用用エントリポイントを多数追加しました。各種レポート生成や実行コンポーネントの起動に対応します。
  - run_execution.py: ExecutionEngine 起動スクリプト（本番 / ペーパートレードの分離、起動時リコンシリエーション、Execution Startup Summary の生成、Engine のデーモンスレッド実行）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL によるポーリング間隔上書き、プロセス優先度設定、PID / stop flag 管理）。
  - run_intraday_monitor.py: ザラ場中監視 CLI（ワンショット / watch モード、CLI 表示フォーマット）。
  - run_position_reconciliation_report.py: Position Reconciliation レポート生成 CLI（watch モード、interval 指定、Broker 接続と OrderRepository 利用）。
  - run_pre_market_report.py: Pre-Market Report 生成 CLI（duckdb / sqlite からデータ収集、JSON出力／保存オプション）。
  - run_market_close_report.py: Market Close Summary 生成 CLI（duckdb / sqlite からデータ収集、JSON出力／保存オプション）。
  - run_performance_report.py: 運用成績サマリーレポート CLI（daily/weekly/monthly、期間指定、env 指定、保存オプション）。
  - run_signal_queue_report.py: Signal Queue 確認ビュー生成 CLI（date / save / json オプション）。
  - tools/paper_verification_report.py: ペーパートレード検証用レポート生成スクリプト（稼働率・注文成功率・送信率・レイテンシ(P95) 等を計算）。
  - validate_config.py: 起動前設定検証ツール（必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml の存在およびパース検証、--strict モード）。
  - config_setup.py: .env の対話式ウィザード（.env ファイルの初期作成・更新を支援）。
- 設定管理モジュールを追加しました（kabusys.config）。
  - Settings クラスでアプリケーション設定をプロパティとして取得可能（J-Quants / kabuステーション / LINE / DB / 監視 / システム関連）。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を起点）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーで export プレフィックス・クォート付き値・インラインコメント等に対応（既存 OS 環境変数を保護する仕組みあり）。
  - Paper Trading 用の分離: Settings.paper_sqlite_path と PAPER_TRADING_SQLITE_PATH 環境変数でペーパートレード専用 DB を指定可能。
  - paper_fill_mode（PAPER_FILL_MODE）の検証（有効値チェック）。
- 監視系の初期化・運用の改善
  - monitoring 起動時に本番 sqlite_path を使用して監視 DB を初期化（init_monitoring_db を呼び出し、監視テーブルの存在を保証）。
  - run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値は警告を出しデフォルトにフォールバック）。
  - PID ファイルと停止フラグ (data/*.pid, data/stop_requested.flag) を用いたプロセス管理を実装。
  - プロセス優先度を "high" に設定するユーティリティ呼び出しを追加（起動時に実行）。
- 実行エンジン（Execution）関係の改善
  - BrokerClientFactory により環境に応じたブローカクライアントを生成（paper_trading 時は MockBrokerClient を利用して DB 分離）。
  - 起動時に総資産（現金 + 保有評価額）を計算して RiskManager に渡す処理を追加。
  - risk_config.yaml の読み込みと詳細なバリデーションを実装（必須キー確認・型変換・範囲チェック・相互関係チェック）。
- レポート出力/保存の共通化
  - レポート生成モジュール群で CLI 表示、JSON 形式、レポートの artifacts への保存をサポート（--json / --save オプション）。
  - 一部 CLI では JSON 出力時に保存先メッセージを stderr に出力して JSON ストリームを汚染しない配慮を実装。
- 監視 / Intraday 表示改善
  - run_intraday_monitor のスナップショット収集と CLI フォーマットを整備（状態判定の閾値、絵文字による直感的表示）。
  - ステータス判定ロジックを明確化（Kill Switch / execution/monitoring PID チェック / ドローダウン / 注文エラー等）。
- データベース利用
  - DuckDB を分析向け DB として導入・利用（Settings.duckdb_path）。
  - 各 CLI で read_only 接続や URI 接続など実行時に適切な接続オプションを設定。
- パッケージメタ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

Changed
- .env 自動読み込みの順序を OS 環境 > .env.local（上書き）> .env（未設定時セット）に定義し、既存 OS 環境変数を上書きしない保護を実装。
- monitor/engine 起動時のログ初期化と例外ハンドリングを強化（check_once() 等での例外はログ出力してポーリング継続）。

Fixed
- .env のパースでクォート・エスケープ・コメント処理の不備に対応（export キーワードやクォート内のバックスラッシュエスケープ等を正しく扱うように改善）。

Security
- .env ファイル生成ウィザードでシークレット値をマスク表示し、.env を Git にコミットしない旨を明記。

Notes / Usage highlights
- run_execution は KABUSYS_ENV=paper_trading の場合、Settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離して動作します。
- run_monitoring は KABUSYS_ENV にかかわらず「監視用の本番 sqlite_path」を使用して監視データを一元管理します。
- validate_config により起動前に環境変数や config/*.yaml の基本的な整合性をチェックできます（--strict で警告も失敗扱い）。
- config_setup のウィザードで .env を生成した後、validate_config を実行して設定を確認することを推奨します。
- Paper Trading 検証スクリプト (tools/paper_verification_report.py) は稼働率やレイテンシの P95 などを計測し、閾値に基づく簡易判定を行います。デフォルトの閾値はファイル内に記載（稼働率 99% など）。

Acknowledgements / Limitations
- config/*.yaml の細かいスキーマ検証は PyYAML の有無に依存します。PyYAML がインストールされていない場合は YAML の内容検証はスキップされ、存在チェックのみ行います。
- 一部のユーティリティ（プロセス優先度設定、BrokerClient 実装等）は環境依存の実行振る舞いを持ちます。実際の運用環境での動作確認を行ってください。

---- 

以上がコードベースから推測した初期リリース 0.1.0 の変更点一覧です。追加でリリースノートの粒度変更（詳細なモジュール別の変更やコミット単位での分割）や英語版が必要であれば指示ください。