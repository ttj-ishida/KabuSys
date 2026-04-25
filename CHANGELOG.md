# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。
このプロジェクトではセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-25

初期リリース。システム監視・実行エンジン・設定管理・ポートフォリオ構築・ユーティリティ等の基本機能を実装しました。

### 追加
- 全体
  - パッケージ初期公開。バージョンは `__version__ = "0.1.0"` に設定。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルートの `data/stop_requested.flag` を検知して行う。
    - Monitoring は環境に依らず本番用の `sqlite_path` を使用して DB に接続し、DuckDB と併用する。
    - 起動時にプロセス優先度を "high" に設定（`set_process_priority` を利用）。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper_trading SQLite DB（既定 `data/paper_trading.db`）を使用し、本番 DB と分離（docstring に明記：MockBrokerClient を使用する想定）。
    - 停止フラグや PID ファイル管理を行い、エンジンは別スレッドで実行。停止フラグ検出で安全に停止する。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py: 環境変数・設定管理クラス `Settings` を追加。
    - .env 自動読み込み機能（プロジェクトルート検出: `.git` または `pyproject.toml` を起点）。
    - 読み込み順: OS 環境変数 > .env.local > .env（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - 複数の設定プロパティを提供（J-Quants / kabu API / LINE / DuckDB/SQLite パス / ペーパートレード用パス / 監視閾値 / ログレベル等）。
    - `paper_fill_mode`（PAPER_FILL_MODE）のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - `env` のバリデーション（development, paper_trading, live）。
  - config_setup: 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。
    - 各設定項目のラベル・説明・デフォルト値を提示し、シークレット値はマスク表示。
    - `.env` 保存用のフォーマットを生成（Git にコミットしない旨を明記）。

- 設定検証
  - validate_config: 起動前に環境変数と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML が未インストールの場合は警告を出す）。
    - `--strict` オプションで警告も FAIL 扱いにできる。

- ツール
  - tools/paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（平均/最大/P95）等を集計して判定（PASS/FAIL）を出力。
    - P95 算出、日付フィルタ（--from / --to）、DB パスの引数／環境変数対応。
    - デフォルト閾値を定義（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms）。

- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py:
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を追加。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を追加。
    - レジームに応じた資金乗数（bull/neutral/bear）を提供。未知レジームは警告を出してフォールバック。
  - portfolio/position_sizing.py:
    - 発注株数計算 calc_position_sizes を追加。allocation_method に応じて "risk_based"/"equal"/"score" をサポート。
    - 単元株（lot）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer（手数料・スリッページ見積り）を実装。
    - 不足価格データや 0 価格はスキップする安全処理を実装。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル/ログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py:
    - プラットフォーム差分を吸収したプロセス優先度設定と CPU affinity 設定機能を追加（psutil を利用）。
    - Windows と POSIX（Linux, macOS, FreeBSD）対応。権限不足等は警告でスキップ。
    - set_cpu_affinity で最初の N コアに固定する機能も提供。

- research
  - research/factor_research.py: ファクター計算モジュール（モメンタム、ボラティリティ、流動性、バリュー等）の土台を追加。DuckDB を使用して prices_daily / raw_financials から計算する設計。
    - calc_momentum の実装を開始（関数の定義と定数群を追加）。（実装途中の箇所あり）

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 非推奨
- なし

### 削除
- なし

### セキュリティ
- なし

注記:
- run_monitoring/run_execution は init_monitoring_db など監視・実行周りの初期化呼び出しを行います。これらは冪等に設計されており、既存テーブルがあっても問題なく起動できる想定です。
- research/factor_research.calc_momentum はファイル末尾で途中（関数実装が続く）になっており、今後の実装・テストが必要です。