# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。主にコードベースの最初の公開リリース相当の変更点を、ソースコードから推測して日本語でまとめています。

フォーマット:
- Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリで記載。

--------------------------------------------------------------------------

Unreleased
---------
- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-23
-------------------
Added
- パッケージ初期導入: KabuSys 全体の初期モジュール群を追加。
  - パッケージバージョン: __version__ = "0.1.0"

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env 自動読み込みを行う（無効化オプションあり）。
  - .env 行のパースロジックは quotes / export / インラインコメント等に対応。
  - 各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DuckDB / SQLite / Paper Trading 用 DB / 監視閾値 / 環境判定 等）。
  - 環境値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の妥当性チェック）を実装。

- 設定ウィザード CLI (src/kabusys/config_setup.py)
  - 対話式で .env を初期作成・更新するウィザードを追加。
  - デフォルト値、選択肢、シークレット入力の扱い、既存 .env の読み込み・再利用、保存の確認を実装。
  - .env 書き込みフォーマットを明示（ファイルは Git にコミットしない旨のヘッダを含む）。

- 設定検証 CLI (src/kabusys/validate_config.py)
  - 起動前に .env と config/*.yaml の基本的なチェックを実行する CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の警告、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML がない場合はスキップ）を実装。
  - --strict オプションで警告も失敗扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - プロセス優先度の設定、ログ設定、SQLite / DuckDB 接続の初期化。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite を使い、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine をデーモンスレッドで起動し、data/stop_requested.flag による停止制御、実行 PID ファイル指定に対応。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。初期ポートフォリオ値は broker.get_available_cash() を参照。
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor の初期化、ポーリングループ実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、負値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視テーブルの初期化を含む）。
    - data/stop_requested.flag によるループ停止検知、KeyboardInterrupt のハンドリング。

- ロギングユーティリティ (src/kabusys/utils/logging_setup.py)
  - 全起動スクリプトで共通利用できるログ初期化関数 setup_logging を追加。
  - stdout に出す StreamHandler と、日次ローテーション（TimedRotatingFileHandler）によるファイル出力を組み合わせる。
  - LOG_LEVEL / LOG_DIR の解決順を実装。既存ハンドラをクリアして二重出力を防止。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- プロセス優先度・CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
  - psutil を用いたプラットフォーム差分吸収の優先度設定（Windows の priority class / POSIX の nice 値）。
  - set_process_priority("high"|"normal"|"low") と set_cpu_affinity(n) を提供。
  - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築モジュール (src/kabusys/portfolio/)
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコアでソートして上位 N を選択（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバック。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用し、既存ポジションを参照して新規候補をフィルタリング（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知レジームは警告のうえ 1.0 にフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づいて発注株数を計算。
    - 損切り幅・リスク許容率に基づく risk_based 計算、単元株（lot_size）での丸め、1 銘柄上限・投下資金上限の考慮。
    - aggregate cap 超過時のスケーリングと remainder（端数）処理で lot 単位の追加配分を行う。
    - cost_buffer による保守的なコスト見積りをサポート。

- Paper Trading 検証レポートツール (src/kabusys/tools/paper_verification_report.py)
  - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）からログを集計して検証レポートを生成する CLI。
  - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数など。
  - PASS/FAIL 判定基準（デフォルト閾値）を設定: 稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 <= 200ms。
  - 日付レンジ指定 (--from / --to) と --db オプションをサポート。
  - P95 計算やデータ不足（テーブル欠如）への寛容なハンドリングを実装。

- 研究用ファクター計算（スケルトン） (src/kabusys/research/factor_research.py)
  - Momentum / Value / Volatility / Liquidity の計算方針を実装するモジュール骨子を追加。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計（関数 calc_momentum の実装開始を含む、詳細実装は継続予定）。

- DuckDB / SQLite 統合
  - アプリケーション全体で DuckDB（分析用）と SQLite（監視・履歴用）を併用する設計を採用。
  - 起動スクリプトやツールが両 DB への接続を確立し、適切にクローズする実装。

Changed
- 初回リリースのため該当なし（新規追加のみ）。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

--------------------------------------------------------------------------

注記 / 補足
- .env / シークレットは .git に絶対にコミットしない旨がドキュメント内に明示されています。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用する旨の仕様注記があるため、監視データの保護に注意が必要です。
- Paper Trading と本番 DB は意図的に分離される設計（PAPER_TRADING_SQLITE_PATH / Settings.is_paper）。
- 一部モジュール（例: research/factor_research.py）は実装が途中で切れている箇所が存在するため、今後の拡張・完成が想定されます。

もしリリースノートを英語版やより詳細（機能ごとの使用例・設定例）に展開したい場合は、その点を指定してください。