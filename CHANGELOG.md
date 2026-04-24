# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルは人間が読める変更履歴を提供することを目的としています。

注意: コードベースから推測して作成しています。実際のコミット履歴・差分とは異なる場合があります。

## [Unreleased]

## [0.1.0] - 2026-04-24

初期リリース。主要な追加点・仕様は以下の通りです。

### Added
- 全体
  - パッケージバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - DuckDB / SQLite を組み合わせたローカル分析・監視基盤の基礎を追加。
- 実行・監視スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててデーモンスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) と実行 PID ファイル (data/execution.pid) を扱う。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - check_once() での例外をログに残してループ継続。
- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加。
    - .env ファイルの自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 複雑な .env 行のパースに対応（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント扱いなど）。
    - 各種プロパティを提供（J-Quants / kabu API / DuckDB/SQLite パス / PAPER_FILL_MODE / PID/KILLフラグ等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV の妥当性チェック（development/paper_trading/live）および is_live/is_paper/is_dev のユーティリティ。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能（テスト用途）。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を生成・更新する機能。
    - デフォルト値・選択肢表示、シークレット入力のマスク表示、保存確認を実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 起動前に必須環境変数・パス・YAML 設定ファイルなどを確認するツール。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML が無ければ YAML 検証をスキップして警告を出す実装。
- ロギング・プロセス制御ユーティリティ
  - 統一ロギングセットアップ関数を追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と、日次ローテーション (TimedRotatingFileHandler) の file ハンドラをルートロガーに設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップして stdout のみ）。
    - ローテーション保持数は 30 日。
    - LOG_LEVEL / LOG_DIR / 引数でカスタマイズ可能。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX を吸収して set_process_priority(level) を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定可能（未対応環境では警告でスキップ）。
    - アクセス権限不足や未実装機能に対する安全なエラーハンドリング。
- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates：スコア降順で上位 N を選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights（スコア和が 0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：既存保有のセクター比率が閾値を超える場合に新規候補を除外。
    - calc_regime_multiplier：market regime に応じた資金乗数（bull/neutral/bear）を返す（未知値は 1.0 にフォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：risk_based / equal / score の割当方式をサポート。
    - lot_size（単元株）対応、max_position_pct / max_utilization / cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap スケーリング実装。
    - 丸め・残差処理（lot_size 単位で端数を扱い、残余キャッシュで再配分）。
  - portfolio パッケージのエクスポート群を整理（src/kabusys/portfolio/__init__.py）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - デフォルト DB: env または data/paper_trading.db。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等。
    - P95 パーセンタイル計算、期間フィルタ（--from/--to）、閾値に基づく PASS/FAIL 判定を実装。
- リサーチ
  - ファクター計算モジュールの雛形を追加（src/kabusys/research/factor_research.py）。
    - Momentum/Value/Volatility/Liquidity 計算方針、DuckDB を使った価格・財務テーブル参照での実装方針を記載。
    - モメンタム計算 calc_momentum のインターフェイス・定数などを用意（実装途中）。

### Changed
- なし（初回リリースのため変更履歴はなし）

### Fixed
- なし（初回リリースのため修正履歴はなし）

### Security
- 環境変数ファイル (.env) について、config_setup にて「絶対に Git にコミットしないこと」を明記。
- Settings._require により未設定の必須機密情報に対して起動時に明確なエラーを出力するようにした。

### Notes / Behavioural details
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされるため、配布後の動作で CWD に依存しない設計になっている。
- Monitoring と Execution の DB 使用は意図的に分離されており、paper_trading 環境では発注系データが本番 DB と混ざらないように設計されている。
- run_monitoring は Monitoring 用テーブルが存在しない場合は init_monitoring_db() によって冪等的に初期化する。
- ロギングはデフォルトで stdout と logs/<app_name>.log の両方へ出力するが、ログディレクトリ作成に失敗した場合はファイル出力を安全にスキップする。

---

将来のリリースでは、以下の点を含めることが想定されます（未実装／改善候補）:
- factor_research の完全実装（duckdb クエリの最適化とテスト）
- ExecutionEngine / SystemMonitor の詳細なテスト・エラーハンドリング拡張
- 単体テスト・統合テストと CI 設定
- 銘柄別 lot_size 対応、手数料・スリッページモデルの拡張

（以上）