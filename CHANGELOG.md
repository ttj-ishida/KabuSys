# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、バージョンごとに Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリで記載します。

形式: YYYY-MM-DD を使う場合はリリース日を入れてください。ここでは初回リリースとして v0.1.0 を記載しています。

## [Unreleased]
- なし

## [0.1.0] - 初回リリース
初回公開。システム全体の起動スクリプト、設定管理、ログ・プロセスユーティリティ、ポートフォリオ構築ロジック、ペーパートレード検証ツール、検証・ウィザード系 CLI、研究用のファクター計算モジュール（開発中）などの主要機能を含む。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI。  
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と分離。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動。  
    - data/stop_requested.flag による外部停止フラグ検出、実行中のスレッド停止処理、execution.pid 管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視処理では monitoring 用 DB の初期化と duckdb 接続を行う。監視用 DB は環境に関係なく本番 sqlite_path を使用する実装。

- 設定・環境管理
  - config.py:
    - .env 自動読み込み機能（プロジェクトルートの検出: .git / pyproject.toml を基準）。  
    - 複数項目の Settings クラス経由で設定値を取得（J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視閾値 / 環境判定等）。  
    - PAPER_FILL_MODE 等の入力バリデーション実装。  
  - config_setup.py:
    - 対話式ウィザードで .env を作成・更新する CLI を追加。シークレット項目のマスク表示、既存 .env の読み込み、確認後にファイル保存。  
  - validate_config.py:
    - 起動前チェック用 CLI。必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検査（PyYAML がない場合はスキップ）や本番環境向けのガードチェックを実装。--strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（アプリ別ログファイル、日次ローテート、30日保持）を設定するユーティリティを追加。LOG_LEVEL / LOG_DIR の解決順を実装。ディレクトリ作成失敗時はファイル出力をスキップして警告を出す。
  - utils/process_priority.py:
    - psutil を利用したプロセス優先度設定を追加（Windows / POSIX を吸収）。set_process_priority(level) により high/normal/low を指定可能。set_cpu_affinity(cpu_count) で CPU アフィニティの設定をサポート（利用環境で未対応の場合は安全にスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights: スコア合計が 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を行う apply_sector_cap（既存保有比率が上限を超えるセクターの新規候補を除外）。unknown セクターは制限対象外。  
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知値はフォールバックと警告）。
  - portfolio/position_sizing.py:
    - 各銘柄の発注株数決定ロジック calc_position_sizes を実装（allocation_method: risk_based / equal / score）。  
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap（available_cash によるスケールダウン）、cost_buffer による保守的見積り、残差配分ロジック等を含む。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から指標を集計して人間向けレポートを出力する CLI。  
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を集計。P95 計算、期間フィルタリング、閾値による PASS/FAIL 判定を実装。

- 研究用ファクター計算（開発中）
  - research/factor_research.py:
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計。モメンタム計算の定数や関数の骨子を追加（実装途中）。

### Changed
- none（初回リリースのため変更履歴はありません）

### Fixed
- none（初回リリースのため修正履歴はありません）

### Deprecated
- none

### Removed
- none

### Security
- none

---

注記 / 実装上の注意点（ドキュメント的補足）
- run_monitoring は「監視用 DB を環境にかかわらず本番 sqlite_path を使用する」と明示しており、監視テーブルは init_monitoring_db で冪等的に初期化される。ペーパートレード時は run_execution 側で専用 DB を使用する設計によりデータの分離を確保している。  
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる。既存の OS 環境変数は保護され、.env.local は .env を上書きする（ただし OS 環境変数は保護）。
- process_priority / cpu_affinity は権限不足や未対応 OS の場合に例外を投げずに警告でスキップする安全設計。  
- Position sizing 周りは価格欠損（price <= 0）や lot_size 単位での丸めによる影響を考慮したログ出力・フォールバック処理を含むが、将来的に銘柄別 lot_size や価格フォールバックを導入する余地がある。

---
最終更新: v0.1.0（初回リリース）