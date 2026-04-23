CHANGELOG
=========

すべての変更は「Keep a Changelog」準拠で記載しています。日付はリリース日です。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-23
--------------------

Added
- 初回リリース。KabuSys の基本ユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定関連 CLI、解析ツールなどを追加しました。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB を使用し、本番 DB と完全分離。
    - ブローカークライアントは BrokerClientFactory から生成（paper_trading 時は MockBrokerClient を想定）。
    - エンジンは別スレッドで実行し、data/stop_requested.flag を検知すると停止処理を実行。
    - 実行中の PID を data/execution.pid に書き込む（Engine 側で pid_file を利用）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照して監視データを記録。
    - 停止フラグ data/stop_requested.flag を検知してループを終了。
    - check_once() 呼び出し中の例外はログに記録して次回ポーリングへ継続。
- 設定管理
  - Settings クラスを実装: 環境変数から各種設定（DB パス、API トークン、KABUSYS_ENV、ログレベル、監視閾値など）を取得。
  - 自動 .env ロード機能を追加: プロジェクトルート（.git または pyproject.toml）を検出して .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 環境変数パースはシングル/ダブルクォート、export プレフィックス、インラインコメント等に対応。
  - PAPER_FILL_MODE（paper_trading 用の約定挙動）を追加（有効値: instant|partial|never|reject）。
- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加。主要な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を対話で編集可能。
  - validate_config: .env および config/*.yaml の検証ツールを追加。
    - 必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース確認（PyYAML がインストールされている場合）。
    - --strict オプションで警告も失敗扱いにできる。
- ログ・プロセス管理ユーティリティ
  - logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。ログディレクトリ作成失敗時はコンソール出力のみでフォールバック。
  - process_priority: Windows/Linux/macOS でプロセス優先度（high/normal/low）を抽象化して設定するユーティリティを追加。CPU affinity を設定する set_cpu_affinity も実装（権限不足時は警告でスキップ）。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み計算（スコア全0 の場合は等分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター別集中を制限し、過剰セクターの候補を除外するロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数決定ロジックを実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）でのスケーリング、cost_buffer（手数料・スリッページ見積り）考慮等の挙動を備える。
- データ解析ツール
  - tools/paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）など。
    - レポート期間フィルタ (--from / --to) と --db オプションをサポート。
    - PASS/FAIL の閾値をコード内に定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
- research
  - factor_research: DuckDB を使ったファクター計算モジュールを追加。モメンタム等の計算関数を実装する設計（prices_daily/raw_financials を参照）。（実装途中の関数あり）

Changed
- n/a（初版）

Fixed
- n/a（初版）

Notes / Usage
- 起動・停止
  - 監視や実行の停止はプロジェクトルート/data/stop_requested.flag を作成して行います。run_execution は起動時に停止フラグが既に存在する場合は起動を中止します。
  - run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で調整可能（単位: 秒、1秒以上の正整数。無効な値はデフォルト 60 秒にフォールバック）。
- データベース
  - DuckDB は分析用（デフォルト: data/kabusys.duckdb）。
  - 監視データ（monitoring）はデフォルトで data/monitoring.db（Settings.sqlite_path）に保存。paper_trading 実行時は data/paper_trading.db（Settings.paper_sqlite_path）を使用。
- 設定管理
  - .env の自動読み込みはプロジェクトルートが検出できる場合にのみ行われます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - Settings は環境変数の妥当性チェックを行います（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の値検証）。
- ログ
  - デフォルトでは logs/<app_name>.log に日次ローテーションでログを出力します。LOG_DIR 環境変数で場所を変更可能。ファイル出力に失敗した場合はコンソール出力のみで継続します。

Breaking Changes
- なし（初回リリース）

Security
- 秘密情報（API トークン等）は .env に保存します。.env をリポジトリにコミットしないでください（config_setup でも注意書きを出力します）。

Acknowledgements / TODO
- factor_research の一部関数は実装途中です（ファイル末尾の calc_momentum が途中で切れている箇所あり）。今後のリリースでファクター計算の完成、ユニットテスト、さらに細かなエラーハンドリング強化を予定しています。
- position_sizing の lot_size は全銘柄共通で扱っています。将来的に銘柄別 lot_size をサポートする設計拡張を検討しています。
- apply_sector_cap の価格欠損時の挙動（price が 0 の場合に過少見積りされる点）について改善の余地がある旨コメントを残しています。

--- 

（この CHANGELOG は提供されたコードベースの内容に基づいて推測して作成しています。実際の変更履歴やリリースノートが必要な場合は、コミット履歴やリリースノート元を参照してください。）