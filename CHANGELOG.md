CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の慣例に従っています。  
リリース番号はパッケージ内の __version__ に合わせています。

Unreleased
----------

- なし（次回リリースに向けた未確定の変更点を記載します）

0.1.0 - 2026-04-25
------------------

Added
- 基本アプリケーション初期リリース。
  - パッケージバージョン: 0.1.0
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いて実行環境に応じたブローカクライアントを生成。
    - Engine を別スレッドで起動し、 stop フラグ検知時に安全に停止する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず本番用の sqlite_path を参照して監視テーブルを初期化する設計。
    - 停止フラグ（data/stop_requested.flag）を監視して安全にループを終了。
- 設定・環境関連
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env/.env.local の読み込み順と上書きポリシー（OS 環境変数を保護）を実装。
    - 複数の設定プロパティを提供（DB パス、API トークン、ログレベル、監視閾値、環境判定など）。
    - PAPER_FILL_MODE のバリデーション、Paper Trading 用の SQLite パス分離などの便利なプロパティを追加。
  - config_setup.py
    - .env を対話式で作成・更新するウィザードを追加。
    - J-Quants / kabuAPI / DB パス / LINE / ログレベル / Kill Switch オプションなどを対話的に設定して .env を書き出す。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検査する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス（親ディレクトリの存在）、config YAML の存在とパース検証（PyYAML がインストールされている場合）を実施。
    - --strict オプションで警告をエラー扱いにできる。
- ログ & プロセス管理ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定する共通セットアップを提供。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する安全設計。
    - LOG_LEVEL / LOG_DIR / 引数で動的に振る舞いを制御可能。
  - utils/process_priority.py
    - set_process_priority(level) を提供し、Windows と POSIX の差分を吸収して優先度を設定。
    - set_cpu_affinity(cpu_count) を提供（利用可能な場合に CPU affinity を設定）。
    - 権限不足や未対応 OS の場合は警告を出して失敗を回避。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナルの選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額にフォールバックする安全処理あり。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定銘柄は除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知レジームは警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - 発注株数算出の calc_position_sizes を実装。
    - allocation_method に応じた "risk_based" / "equal" / "score" をサポート。
    - lot_size（単位株）に合わせた丸め、per-position 上限、aggregate cap（利用可能現金に基づくスケーリング）を実装。
    - cost_buffer を考慮した保守的なコスト見積りと残差に基づく追加配分ロジックを実装。
    - price 欠損時のスキップやログ出力など堅牢化を行っている。
- 解析・研究用モジュール（開発中）
  - research/factor_research.py
    - DuckDB を用いたファクター計算基盤を追加。
    - Momentum / Value / Volatility / Liquidity などの設計方針と定数を実装。calc_momentum の実装開始（ファイル末尾で未完の可能性あり）。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を解析して検証レポートを標準出力に出力するツールを追加。
    - 稼働率、注文成功率、送信率、リスク却下、レイテンシ（平均・最大・P95）などを集計し、閾値に基づく PASS/FAIL 判定を出力。
    - CLI 引数で期間指定（--from / --to）および DB パス指定（--db）に対応。
    - デフォルト DB パスは data/paper_trading.db。
- パッケージ初期化
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- -（本初回リリースのため該当なし）

Fixed
- -（本初回リリースのため該当なし）

Deprecated
- -（本初回リリースのため該当なし）

Removed
- -（本初回リリースのため該当なし）

Security
- -（本初回リリースのため該当なし）

Notes / Known issues
- research/factor_research.py の calc_momentum 実装が途中で終わっている可能性がある（ファイル末尾が不完全）。追加の実装・テストが必要。
- position_sizing.calc_position_sizes の注記にあるように、価格データの欠損時にエクスポージャーが過小評価されるケースがある（将来的に前日終値等でのフォールバックを検討）。
- run_monitoring は「監視は本番 sqlite_path を使用する」設計のため、開発環境でモニタリングを分離したい場合は注意が必要。
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされる。CI／特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。
- process_priority / cpu_affinity の設定は権限不足や未対応プラットフォームで失敗する可能性があり、その場合は警告を出して継続する設計。

開発者向けヒント
- .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- 設定検証は validate_config.py を活用してください。--strict を使うと警告も失敗として扱えます。
- ログはデフォルトで logs/ 配下に日次ローテーションで保管されます。ログ格納先を変更する場合は LOG_DIR 環境変数を設定してください。

-----END CHANGELOG-----