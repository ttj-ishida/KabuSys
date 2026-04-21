CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在のスナップショットでは未リリースの変更はありません）

0.1.0 - 2026-04-21
-----------------

Added
- 初回リリースとして基本機能を実装しました。
  - CLI 起動スクリプト
    - run_execution: 実行エンジン (ExecutionEngine) の起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、ExecutionEngine の起動・停止監視を行います。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用（本番 DB から分離）します。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用します（環境に依存しない）。
    - validate_config: .env と config/*.yaml の事前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや YAML の存在・パース検証、追加の本番向けガードを実行。--strict オプションで警告を失敗扱いにできます。
    - config_setup: .env 作成・更新の対話式ウィザードを追加。複数の設定項目の入力補助・既存値読み込み・保存をサポート。
    - tools/paper_verification_report: ペーパートレード結果の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) などを集計し PASS/FAIL を判定します。
  - 設定管理
    - config.Settings クラスを実装。環境変数経由で設定を取得するためのプロパティ群（DB パス、API トークン、ログレベル、監視閾値など）を提供。
    - .env 自動ロード機構を実装（プロジェクトルートを .git または pyproject.toml で検出）。優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサは export KEY=val、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等をサポート。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等、ペーパートレード向け設定を追加。
  - ポートフォリオ構築（純関数群）
    - portfolio.portfolio_builder: BUY シグナルの候補選択 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
    - portfolio.risk_adjustment: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数計算 (calc_regime_multiplier)。
    - portfolio.position_sizing: 発注数量計算ロジック (calc_position_sizes)。allocation_method="risk_based" / "equal" / "score" をサポートし、単元株丸め、per-stock 上限、aggregate cap（利用可能現金でスケールダウン）、コストバッファ等に対応。
  - ユーティリティ
    - utils.logging_setup: 統一的なログ設定ユーティリティを提供。stdout へ StreamHandler、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーへ設定。LOG_DIR/LOG_LEVEL 優先解決の実装。
    - utils.process_priority: Windows / POSIX の差分を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を提供。アクセス権限エラー等は警告でスキップ。
  - DB/監視周り
    - monitoring 側で init_monitoring_db を呼び出して監視用テーブルを冪等に初期化。run_monitoring と run_execution の両方で起動時に監視テーブルの存在を保証。
  - その他
    - パッケージのバージョン設定: kabusys.__version__ = "0.1.0"。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する前提。config_setup ではシークレット項目をマスクして対話します。公開リポジトリへ .env をコミットしないよう注意喚起を追加。

Notes / Behavioural details
- run_execution の挙動
  - KABUSYS_ENV=paper_trading のときは settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視 DB と分離されます。MockBrokerClient の使用切り替えは BrokerClientFactory により行われます。
  - エンジンは別スレッドで run_session を実行し、data/stop_requested.flag の出現で安全に停止します。PID ファイルを data/execution.pid に書き出す想定。
- run_monitoring の挙動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（int、1 以上）。不正値は警告してデフォルト 60 秒にフォールバックします。停止は data/stop_requested.flag を置くことで行います。
  - 監視は環境（KABUSYS_ENV）に関係なく本番 sqlite_path を使用します（監視データの一元化）。
- ロギング
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソール出力のみで継続します。ログのデフォルト保存先は logs/、日次ローテーションで 30 日分を保持します。
- .env 自動ロード
  - プロジェクトルートが検出できない場合は自動ロードをスキップします。OS 環境変数で既に設定されているキーはデフォルトで上書きされません（.env.local は上書き可能）。
- Paper Trading レポート
  - tools/paper_verification_report は稼働率、注文の作成/成立/送信統計、リスク却下数、レイテンシ平均/最大/P95 を算出し、閾値に応じて PASS/FAIL を出力します。DB が存在しない場合はエラーメッセージを表示します。

Known limitations / TODO
- 一部モジュール（例: research.calc_momentum 等）の実装が継続中の可能性があります（コードベースの拡張余地あり）。
- position_sizing の lot_size 固定（現在は全銘柄共通の単元想定）や price 欠損時のフォールバック価格処理等、将来的な拡張をコメントで示しています。
- YAML 検証には PyYAML が必要。未インストール時は YAML 内容検証をスキップして警告を出します。

開発者向け
- コードベースは環境変数による設定に強く依存しています。ローカルで動かす際は config_setup を使って .env を作成し、validate_config で検証してください。
- 本番運用時は KABUSYS_ENV=live とし、KILL_FLAG_CLEAR_ON_START をデフォルトの 0（自動クリア無効）にすることを推奨します。

--- 
以上。質問やリリースノートの追加・修正が必要であれば教えてください。