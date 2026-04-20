CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。  

既知の慣例:
- リリース日には本リポジトリのスナップショット作成日（ここでは現行コードベースの作成日）を使用しています。

Unreleased
----------

（現時点の作業ツリーと同一内容のため空）

0.1.0 - 2026-04-20
-----------------

Added
- 基本アプリケーションとユーティリティ群を追加。
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
- 実行用スクリプトを追加。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモン実行と停止フラグ監視を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（監視データは本番 DB に記録）。
    - 停止フラグファイル（data/stop_requested.flag）を検出してループを終了。
- 環境設定関連 CLI を追加。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新するツール。
    - J-Quants・kabu API 等の必須項目やデフォルト値・説明を提示し、.env を安全に書き出す。書き出し時に .env を絶対にコミットしない旨の注意コメントを挿入。
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出力。
- ツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite から稼働率 / 注文成功率 / 送信率 / レイテンシ等を集計して検証レポートを生成する CLI。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）し、Pass/Fail 判定を行う。
    - --from / --to / --db オプションで期間・DB を指定可能。
- ポートフォリオ構築モジュールを追加。
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全体が 0 の場合は等配分にフォールバック（警告出力）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
    - レジーム乗数は "bull"/"neutral"/"bear" に対応（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数算出ロジック（risk_based / equal / score）を実装。単元株丸め、1銘柄上限、aggregate cap によるスケーリング、cost_buffer の考慮などを行う。
- 設定管理を充実化（config.py）。
  - .env の自動読み込み機構を追加（プロジェクトルートは .git または pyproject.toml から検出）。
  - .env と .env.local の読み込み順（OS 環境変数 > .env.local > .env）を実装。OS 環境変数は保護され上書きされない。
  - .env パーサを強化:
    - export KEY=val 形式に対応。
    - クォートあり／なし両方の値と、バックスラッシュエスケープ、行内コメントの扱いを適切に処理。
  - Settings クラスに各種プロパティを実装：
    - パス系（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）。
    - 環境 (KABUSYS_ENV) とログレベルのバリデーション。
    - PAPER_FILL_MODE の列挙バリデーション（instant/partial/never/reject）。
    - 各監視閾値（CPU/MEM/MEMORY/DISK）や kill flag 関連設定の取得。
- ログ設定ユーティリティを追加（utils/logging_setup.py）。
  - StreamHandler（stdout）＋ TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーへ設定。
  - 既存ハンドラをクリアして重複設定を防止。
  - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - stdout を利用することでタスクスケジューラや cron でのリダイレクト運用を配慮。
- プロセス優先度・CPU アフィニティユーティリティを追加（utils/process_priority.py）。
  - Windows / POSIX の差分を吸収した set_process_priority(level) を提供（high/normal/low）。
  - set_cpu_affinity(cpu_count) でプロセスを先頭 N コアにピンニングする機能を追加（権限不足や未対応 OS は警告してスキップ）。
  - 権限不足や未対応 API 呼び出し時でも安全にフォールバック。
- DuckDB / SQLite を利用する初期化機能を統合（monitoring.monitoring_db の init_monitoring_db を起動時に呼び出す実装等）。
- research/factor_research.py を追加（ファクター計算基盤）。
  - Momentum 等のファクター（1M/3M/6M リターン、MA200乖離等）を DuckDB の prices_daily を参照して計算するための骨組みを実装（設計方針と定数を含む）。※ファイル末尾は途中まで実装。

Changed
- ログ出力の標準化:
  - 全起動スクリプトは setup_logging(app_name=...) を呼び出しコンソール出力とローテートファイルを統一的に設定するように変更。
- モニタリングの DB 使用方針:
  - run_monitoring は環境にかかわらず監視用に Settings.sqlite_path（本番監視 DB）を使用する方針をドキュメント化。

Fixed
- .env 読み込みの堅牢性向上:
  - 読み取り失敗時に警告を出すようにし、例外でプロセスがクラッシュしないように安全化。

Security / Safety
- config_setup にて .env を生成する際に「.env を絶対に Git にコミットしないこと」と明記。
- validate_config により、本番（KABUSYS_ENV=live）設定時に LINE 通知設定や Kill Switch の設定の確認を促す警告を追加。

Notes / Behavior details
- MONITOR_POLL_INTERVAL:
  - 環境変数でポーリング間隔を指定可能。整数で 1 以上を期待し、0 以下や非整数の場合はデフォルト（60 秒）にフォールバックして警告。
- 停止フラグ / PID ファイル:
  - 停止はプロジェクトルート/data/stop_requested.flag を置くことで各スクリプトが検出して終了する方式を採用。
  - Execution 用に data/execution.pid を利用する設計。
- Paper Trading 分離:
  - paper_trading 環境では Mock ブローカー（BrokerClientFactory 経由）と paper_trading 用 SQLite を使い、本番データとの混ざりを防止。
- DuckDB:
  - 分析用途の DuckDB を各スクリプトで接続（Settings.duckdb_path）。ファイル IO は user が設定可能。

今後の予定（例）
- research/factor_research のファクター実装完了（Value / Volatility / Liquidity 等）。
- ExecutionEngine / SystemMonitor のさらなるテストカバレッジ拡充と例外ハンドリングの強化。
- 単体テスト・CI 設定の追加。

---
参考: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/