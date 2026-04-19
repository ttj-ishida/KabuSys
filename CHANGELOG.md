# CHANGELOG

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

- リリース日付はコミット時点のソースから推測しています。  

## [Unreleased]

## [0.1.0] - 2026-04-19
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ情報とエクスポート定義を追加（kabusys.__init__、バージョン "0.1.0"）。
- 実行 / デーモン起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）にデータを記録して本番 DB と分離。
    - プロセス優先度を最初に "high" に設定。
    - init_monitoring_db により監視用テーブルの存在を保証（冪等）。
    - 停止フラグ (data/stop_requested.flag) を検知して安全に停止する仕組みを実装。
    - 実行用 pid ファイルを管理（data/execution.pid）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB を常に本番向けに確保）。
    - duckdb 接続を併用してデータ処理を行う。
    - 停止フラグの検知、例外時のログ出力、KeyboardInterrupt のハンドリング等を実装。
- 設定管理 / 初期化
  - config.py: Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルート判定に .git または pyproject.toml を使用）。
    - .env / .env.local の読み込み順序（OS 環境変数を保護）。
    - 環境変数パーサは export プレフィックス、クォート文字列、インラインコメント等に対応。
    - 各種設定プロパティ（DB パス、PID/kill フラグパス、閾値、PAPER_FILL_MODE バリデーションなど）を提供。
    - 環境判定ユーティリティ（is_live / is_paper / is_dev）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - よく使う設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン等）を対話的に入力可能。
    - 既存 .env の読み込みと既存値の再利用、シークレット値のマスク表示、保存確認を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がない場合はスキップ）等。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション、既定 logs/ ディレクトリ、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順を明示。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度 / CPU affinity 設定機能を追加。
    - Windows と POSIX（Linux / macOS / FreeBSD）を吸収。
    - set_process_priority(level) — "high" | "normal" | "low"。アクセス権限不足や未実装 API は警告でスキップ。
    - set_cpu_affinity(cpu_count) — 指定コア数にピンニング（例外ハンドリング付き）。
- ポートフォリオ構築ロジック
  - portfolio/portfolio_builder.py: 候補選定と重み計算を追加。
    - select_candidates: スコア降順・タイブレークに signal_rank を使用して上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重（スコア合計が 0 の場合は等金額にフォールバックして警告）。
  - portfolio/risk_adjustment.py: セクター集中制限とレジーム乗数を実装。
    - apply_sector_cap: 既存保有のセクター別時価から上限超過セクターを除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market_regime に基づく投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py: 株数決定ロジックを実装。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）でスケールダウンする補正ロジック。
    - cost_buffer を加味した保守的なコスト見積もりおよび残差処理による追加配分の実装。
- 研究・シグナル補助
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum、Value、Volatility、Liquidity を想定）。
    - DuckDB を用いた prices_daily / raw_financials 参照ベースの計算設計。
    - モメンタム計算 calc_momentum の実装（営業日ベースの複数ハラizon 計算、MA200 乖離率等）を含む設計（ソース一部に続きあり）。
- ツール類
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db オプション）で指定した SQLite から指標を抽出し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを計算。
    - 定義済み閾値に基づく PASS/FAIL 判定（稼働率 >= 99%、注文成功率 >= 90% 等）。
    - P95 計算、期間フィルタリング（ISO8601 UTC タイムスタンプ）対応。
- DB 初期化ユーティリティ
  - monitoring/monitoring_db.py への参照により、監視用テーブルの初期化を行う機能を起動フローに組み込み（冪等）。

### 変更 (Changed)
- なし（初回リリース）。

### 修正 (Fixed)
- なし（初回リリース）。

### 注意事項 / 補足
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のみ有効。無効な値は ValueError を送出。
- ログは標準で logs/<app_name>.log に日次ローテーションで出力するが、ディレクトリ作成に失敗するとコンソール出力のみとなる。
- run_monitoring は監視 DB に常に Settings.sqlite_path（本番）を使用する点に注意。実行エンジンは paper_trading 環境時に DB を分離する。
- process_priority や CPU affinity の設定は環境によって権限エラーや未実装 API によりスキップされることがあります（警告ログ出力）。
- research/factor_research.py は DuckDB ベースでのファクター計算を設計しており、関数が継続実装される想定。

<!--
フォーマット参考:
https://keepachangelog.com/ja/1.0.0/
-->
