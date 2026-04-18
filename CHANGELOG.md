CHANGELOG
=========

すべての重要な変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

- (なし)

[0.1.0] - 2026-04-18
--------------------

Added
- 基本リリースを初版として追加。
- 環境・設定管理
  - Settings クラスを実装（kabusys.config）。環境変数経由で各種設定を取得。
  - 自動 .env 読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env パーサ実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理などを考慮。
- 環境セットアップ CLI
  - 対話式ウィザード（kabusys.config_setup）を実装。.env の初期作成・更新を支援。
  - プロンプト、既存値の読み込み、シークレットマスク表示、保存の確認機能を提供。
- 設定検証 CLI
  - kabusys.validate_config を実装。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML があれば）等を検証。
  - --strict オプションで警告を FAIL 扱いにできる。
- 実行用スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager 等の組み立て、スレッドでのエンジン実行と停止フラグ監視（data/stop_requested.flag）。
    - 起動時にプロセス優先度を high に設定（utils.process_priority を使用）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB を注意深く扱う方針）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - 起動時にプロセス優先度を high に設定。
- ロギング
  - kabusys.utils.logging_setup を実装。
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / app_name により挙動を制御。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
- プロセス優先度 / CPU アフィニティ
  - kabusys.utils.process_priority を実装。
    - psutil を用いて Windows / POSIX の差分を吸収し set_process_priority("high" | "normal" | "low") を提供。
    - set_cpu_affinity によりプロセスを最初の N コアにピン留め可能（アクセス権や未対応環境では安全にフォールバックして警告）。
- データベース接続
  - run_* スクリプトで sqlite3 / duckdb 接続を使用。監視テーブル初期化用に init_monitoring_db を呼び出して冪等に保証。
- Portfolio（ポートフォリオ構築）
  - 銘柄選定・配分:
    - select_candidates: スコア降順（同点は signal_rank 昇順）で候補選定。
    - calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
  - リスク調整:
    - apply_sector_cap: セクター集中制限のロジック。既存保有のセクター別時価を計算し上限超過セクターの新規候補を除外（unknown セクターは制限適用外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear -> 1.0/0.7/0.3）。未知レジームは 1.0 でフォールバック。
  - 株数計算 / 約定ロジック:
    - calc_position_sizes: allocation_method に応じた数量計算（risk_based / equal / score）。
    - 単元株（lot_size）単位で丸め、1銘柄上限・aggregate cap（available_cash）でスケールダウン。cost_buffer により保守的にコスト見積り。
    - スケーリング時に残差を考慮して lot_size 単位で追加配分するロジックを実装。
- ツール
  - kabusys.tools.paper_verification_report を実装。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH で指定可能）からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計しレポートを出力。
    - しきい値を用いた PASS/FAIL 判定（稼働率、成功率、送信率、P95 レイテンシ 等）。
- 研究用モジュール（research）
  - factor_research: DuckDB を用いたファクター計算の設計とモメンタム計算ロジックを実装（モメンタム指標: 1M/3M/6M リターン、MA200 乖離等）。（注: ファイルは途中まで実装）

Changed
- 初版のため過去バージョンからの変更は無し（初回リリース）。

Fixed
- ログハンドラやプロセス優先度設定で失敗した場合にプログラムを停止させず、警告ログを出してフォールバックするように実装（ファイル入出力や psutil の権限問題への耐性向上）。

Known issues / Notes
- research.factor_research はファイル末尾が途中で切れている（モメンタム関数の続き等、追加実装が必要）。
- apply_sector_cap 内で価格が欠損（0.0）だった場合のエクスポージャー過少見積りに関する TODO が残っている（前日終値等のフォールバック検討）。
- position_sizing の将来的拡張: 銘柄別の lot_size を stocks マスタで持たせることが想定されている（現状は全銘柄共通の lot_size）。
- run_monitoring は「監視は environment にかかわらず本番 sqlite_path を使用する」設計のため、運用時は設定の理解に注意が必要。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合、コンソール出力のみで継続する仕様（失敗を無視するのではなく警告してフォールバック）。

Authors
- KabuSys 開発チーム（コードコメント・実装から推測して作成）

References
- リポジトリ内ソース: src/kabusys 以下の各モジュール（config, config_setup, validate_config, utils, portfolio, execution, monitoring, tools, research 等）