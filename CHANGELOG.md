# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成した変更履歴です。

全般の前提:
- 初版リリースとしての機能群をコードから抽出し記載しています。
- 日付は本ファイル作成日 (2026-04-19) を使用しています。

## [Unreleased]
- 開発中の変更点はありません（初回リリースにて主要機能を導入）。

## [0.1.0] - 2026-04-19

### Added
- 起動スクリプト / 実行環境
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止。
    - 常に本番用 sqlite_path を使用して監視データを記録。
    - duckdb 接続の利用、監視用 DB の初期化処理を呼び出し。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient 相当のファクトリ経由でブローカーを分離（本番 DB と完全分離）。
    - Engine の実行はデーモンスレッドで起動し、停止フラグ検知で安全停止。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理・検証・セットアップ
  - config.py
    - .env 自動読み込み機構を追加（.env /.env.local をプロジェクトルートから読み込み、OS 環境変数を保護）。
    - .env パーサーは export 形式、クォートされた値、インラインコメント、エスケープシーケンスに対応。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス /監視閾値 / 環境種別などのプロパティを提供。値チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
  - validate_config.py
    - 起動前に環境変数と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML がない場合はスキップ）を実装。
    - KABUSYS_ENV=live に対する追加のガード（LINE 関連や Kill-flag の注意喚起）。
    - --strict フラグで警告を FAIL 扱いにできる。
  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを実装。
    - 秘密値はマスク表示、選択肢やデフォルト値の提示、最終確認後に .env を生成する機能を提供。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガー向けの統一ロギング設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリ作成に失敗した場合はファイル出力を無効化して継続。
    - LOG_LEVEL / LOG_DIR / 引数でのオーバーライド対応、既存ハンドラの二重設定防止。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定を提供（psutil を利用）。
    - Windows と POSIX（Linux, macOS 等）の差分を吸収し、失敗時は警告ログでスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、タイブレークロジック）とウェイト計算（等金額・スコア加重）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中リスク制限（apply_sector_cap）を実装。既存保有を基にセクター別エクスポージャーを計算し、閾値超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - 株数決定ロジックを実装。allocation_method に応じて risk_based / equal / score の計算を行う。
    - 単元株（lot_size）での丸め、per-stock 上限や aggregate cap（available_cash）に基づくスケーリング、cost_buffer に基づく保守的見積りを実装。
    - スケーリング後の残額分を fractional remainder に基づき再配分するロジックを備える。

- 研究用 / ツール
  - research/factor_research.py（モジュールの骨組み）
    - DuckDB 接続を用いたファクター計算（Momentum / Value / Volatility / Liquidity）を想定した設計。prices_daily / raw_financials テーブルを参照する方針を明記。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出し、閾値比較により PASS/FAIL を判定。
    - 日付フィルタ、--from/--to/--db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数の利用をサポート。

- パッケージ情報
  - __init__.py にてパッケージバージョンを "0.1.0" として設定。

### Changed
- （初回リリースのため特別な変更履歴はなし）

### Fixed
- （初回リリースのため特別な修正履歴はなし）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注記:
- 実装はコードから推測したものであり、実際の挙動や細かな仕様はソースコード/ドキュメントを参照してください。必要であれば各モジュールごとにより詳細な変更点や利用方法を追記できます。