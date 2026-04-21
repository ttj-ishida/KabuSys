# CHANGELOG

すべての公開変更は Keep a Changelog 準拠で記載しています。  
日付はリポジトリ内コードの実装状況から推測して付与しています。

フォーマット:
- Unreleased: 次リリース向けの未リリース変更（現状なし）
- 各バージョン: 主要追加・変更点をカテゴリ別に記載

---

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-21

初回公開リリース。以下の主要機能・ユーティリティを実装しています。

### Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てを行い、ExecutionEngine をスレッドで実行。
    - 停止制御: data/stop_requested.flag を監視し、検知時にエンジンを停止。
    - PID ファイル管理（data/execution.pid を想定）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバックして警告ログを出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する仕様。
    - 停止制御: プロジェクト直下の data/stop_requested.flag を検知してループを終了。
    - duckdb と sqlite3 の両方に接続して運用。

- 設定・環境管理
  - config.py
    - .env ファイル自動読み込み機能（プロジェクトルート（.git または pyproject.toml）を基準に探索）。
    - .env 読み込みの仕様: export プレフィックス対応、シングル/ダブルクォート内エスケープ処理、インラインコメント扱いの詳細実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
    - Settings クラスでアプリ設定をプロパティとして集約（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 環境判定等）。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path など paper_trading 用設定。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を実装。
    - デフォルト値、シークレットマスク表示、選択肢チェック、保存前の確認をサポート。
  - validate_config.py
    - .env と config/*.yaml の起動前検証ツールを実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML 未インストール時はスキップ）等を実施。
    - --strict オプションで警告をエラー扱いにできる。

- ロギング / プロセスユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを実装。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_DIR 環境変数/引数で出力先制御。ディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続。
  - utils/process_priority.py
    - プロセス優先度設定および CPU affinity 設定ユーティリティを実装。
    - Windows/Linux/macOS(一部) を抽象化して高優先度/通常/低優先度を設定。psutil を利用。
    - set_cpu_affinity によりカレントプロセスを先頭 N コアに固定可能（未指定なら全コア）。
    - 許可エラー（AccessDenied 等）は警告でスキップする安全設計。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights、全スコアが 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）。既存保有時価を計算して上限超過セクターの新規候補を除外。unknown セクターは上限対象外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。"bull"/"neutral"/"bear" にマップ、未知のレジームは警告とともに 1.0 フォールバック。
  - portfolio/position_sizing.py
    - 株数決定アルゴリズム（risk_based / equal / score）。
    - 単元株（lot_size）で丸め、1 銘柄上限、aggregate cap（available_cash）を超える場合のスケールダウンロジックと残差に基づく追加配分ロジックを実装。
    - cost_buffer により保守的なコスト見積りを行う。

- 研究 / ファクター計算
  - research/factor_research.py（骨格・モメンタム計算実装開始）
    - DuckDB 接続を受けて prices_daily などのテーブルからモメンタム / MA200 乖離 / ATR / 流動性等の計算を行う設計。
    - モメンタム関数（calc_momentum）の入力/出力仕様と定数定義を実装（計算範囲や欠損扱いの方針を含む）。（ファイル末尾で未完の実装の痕跡あり）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを実装。
    - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、リスク却下数、レイテンシ（avg / max / P95）。
    - P95 計算、期間フィルタ（--from/--to）、DB パス指定（環境変数 PAPER_TRADING_SQLITE_PATH または --db）。
    - 判定閾値を設定し、PASS/FAIL を出力する。

- パッケージメタ情報
  - __init__.py にてバージョンを "0.1.0" に設定。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / 実装に関する重要事項（ドキュメント的に明記）
- .env 自動読み込みはプロジェクトルートを基準に行うため、パッケージ配布後や CWD と異なる実行でも安定動作を目指す設計。ただしプロジェクトルートが特定できない場合は自動ロードをスキップする。
- run_monitoring は監視データ用の sqlite に常に production 用 sqlite_path を使う仕様（環境による切替なし）。paper_trading 実行は run_execution 側で paper_sqlite_path を使って完全に分離する設計。
- 多くの箇所で外部リソース（ファイル・DB・psutil）の権限や存在を想定しており、失敗時はログ出力して安全にフォールバックする実装方針。
- research/factor_research.py の一部処理は実装が継続中（ファイル末尾で未完の可能性あり）。DuckDB を用いた価格テーブル参照で設計されている。

### Removed / Deprecated / Security
- なし

---

翻訳・要約はコード実装とドキュメント文字列（docstring）から推測して作成しています。追加でリリース日や変更の粒度（小修正・ポイントリリース等）を確定したい場合は、コミット履歴や意図したリリースノート情報を提供してください。