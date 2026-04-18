# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  
各リリースはセクション（Added / Changed / Fixed / Deprecated / Removed / Security）で整理しています。

最新リリースはパッケージの __version__ に合わせて記載しています（src/kabusys/__init__.py: 0.1.0）。

## [0.1.0] - 2026-04-18

### Added
- 初期公開リリース。
- 実行系・監視系の起動スクリプトを追加：
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合、paper 用の SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) による安全停止、実行 PID を data/execution.pid に保存する仕組みを想定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを記録。
    - 停止フラグ検出でループを終了し、データベース接続をクローズする安全処理を実装。

- 設定管理・導入支援ツールを追加：
  - config.py
    - .env 自動読み込み機能（プロジェクトルートに .git または pyproject.toml がある場合）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 環境変数取得ラッパ(Settings クラス)を提供（env, is_live/is_paper/is_dev、DB パス、閾値等）。
    - PAPER_FILL_MODE のバリデーションとデフォルト（instant）。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI。
    - シークレット値はマスク表示、デフォルト値・選択肢のサポート、.env 書き出しのテンプレートを提供。
  - validate_config.py
    - .env と config/*.yaml の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML インストール有無で挙動変化）。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築・サイズ計算モジュールを追加（pure function 群、DB 非依存）：
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコア合計が 0 の場合は等金額にフォールバックして警告。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限の適用（当日売却予定は除外、"unknown" セクターは上限対象外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出。
    - 単元（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金）に基づくスケーリング、cost_buffer による保守的見積り。
    - スケーリング時の端数配分ロジックを実装。

- 研究用・ファクター計算基盤（DuckDB を想定）を追加（一部実装）：
  - kabusys.research.factor_research
    - Momentum / Value / Volatility / Liquidity を計算する方針と関数群の枠組みを実装。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算関数の骨組み（calc_momentum）を用意（実装途中）。

- ユーティリティを追加：
  - utils/logging_setup.py
    - 共通ロギング設定関数 setup_logging。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日分保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続。
  - utils/process_priority.py
    - プロセス優先度設定（Windows/Linux/Mac に対応するフォールバック処理）。
    - CPU affinity 固定ユーティリティ（最初の N コアに固定）。
    - 実行スクリプトで起動直後に高優先度設定を行う呼び出しを追加。

- ツールスクリプトを追加：
  - tools/paper_verification_report.py
    - ペーパートレード結果を検証するレポート生成ツール。
    - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を収集・表示し、閾値で PASS/FAIL を判定。
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- パッケージ基礎情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Deprecated
- （現時点ではなし）

### Removed
- （現時点ではなし）

### Security
- （現時点ではなし）

---

Notes / 実装上の注記（開発チーム向け）
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0 や非数）を検出するとデフォルト 60 秒にフォールバックして警告を出力します。
- 設定自動読み込みはプロジェクトルートを .git または pyproject.toml で検出して行います。パッケージ配布後などでルートが判定できない場合は自動ロードをスキップします。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップし警告を出します。
- position_sizing, risk_adjustment モジュールには将来的な拡張を示す TODO コメント（銘柄別 lot_size のサポート、価格フォールバック等）が残っています。
- research.factor_research モジュールの calc_momentum 関数は実装途中（ファイル末尾で途中終了の痕跡あり）です。研究用機能はまだ完成していないため、本番依存は避けてください。
- .env は機密情報を含むため絶対にリポジトリにコミットしない旨を config_setup の書き出しテンプレートに明記しています。

今後の予定（例）
- research モジュールの完成（ファクター集計の実装完了、正規化ユーティリティ連携）。
- ExecutionEngine/Monitoring の詳細なテストとエラー撃退（異常系カバレッジ強化）。
- 銘柄別単元（lot_size）対応、価格フォールバックロジックの導入。

もし CHANGELOG に追加したい重要な変更や、日付・バージョン表記の修正があれば教えてください。