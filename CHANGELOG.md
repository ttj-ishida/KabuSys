# Changelog

すべての非互換性のある変更は明記します。  
このファイルは Keep a Changelog の形式に準拠しています。  

全体の変更は、コードベースから推測して記載しています（実装コメント・ドキュメント文字列等に基づく）。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-18

### Added
- プロジェクト初回公開相当の機能群を追加。
  - パッケージ情報
    - kabusys.__version__ = 0.1.0 を定義。
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite（既定: data/paper_trading.db）を使用し、本番 DB と分離して動作する。
      - BrokerClientFactory を用いて実際のブローカーまたはモック（paper trading）を生成。
      - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag を監視して安全に停止する処理を実装。
      - 実行時に PID ファイル（data/execution.pid 等）を扱う。
    - run_monitoring.py
      - SystemMonitor のポーリングループを起動するエントリポイント。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告の上デフォルトにフォールバック。
      - 監視（monitoring）は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計。
      - data/stop_requested.flag の検知でループ終了、KeyboardInterrupt のハンドリング、DB 接続のクリーンアップを実装。
  - 設定・環境管理
    - config.py
      - Settings クラスにより環境変数をプロパティ化。J-Quants / kabu API / DB パス / ログレベル / 各種監視閾値 などを一元管理。
      - .env の自動読み込み機能を提供（プロジェクトルート検出: .git または pyproject.toml が基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パースは export 形式やクォート・エスケープ、行内コメントを考慮した堅牢な実装。
      - PAPER_FILL_MODE 等の検証ロジック（有効値チェック）を実装。
    - config_setup.py
      - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
      - 秘密値（トークン・パスワード）をマスクして表示、デフォルト値・選択肢のサポート、保存前の確認を実装。
      - .env の書式・ヘッダテンプレートを作成。
    - validate_config.py
      - 起動前に .env や config/*.yaml の不備を検出する CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリチェック、YAML ファイルの存在とパースチェック（PyYAML がない場合は警告）を実装。
      - --strict オプションで警告を FAIL 扱いにするモードを提供。
  - ロギング・プロセス管理ユーティリティ
    - utils/logging_setup.py
      - 全起動スクリプトで共通に使えるロギング初期化を提供。
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
      - ログディレクトリの自動作成を試み、失敗した場合はファイル出力をスキップしてコンソールのみで継続。
      - ログレベル判定の優先順位（引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。
    - utils/process_priority.py
      - Windows/Linux/macOS の差分を吸収してカレントプロセスの優先度設定を行うユーティリティを追加。
      - set_process_priority(level) で "high" / "normal" / "low" を指定可能。権限不足や未対応 OS では警告を出してスキップ。
      - set_cpu_affinity(cpu_count) を用意（未指定では変更しない）。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順で選抜（タイブレークに signal_rank を使用）。
      - calc_equal_weights: 等金額配分（同一重み）を返す。
      - calc_score_weights: スコア正規化による重み計算。全スコアが 0 の場合は等配分にフォールバック（警告ログ）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: 同一セクターによる過度な集中を検出し、新規候補を除外するロジック（sell_codes による売却予定除外対応、"unknown" セクターは制限対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知値は 1.0 でフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数決定ロジックを実装。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、利用可能現金に対する aggregate cap、cost_buffer による保守的見積り、スケーリングと端数処理（fractional remainder を考慮して追加配分）を実装。
      - risk_based では risk_pct / stop_loss_pct に基づくポジションサイズ計算。
  - Paper Trading 向け検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を読み、システム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）などの指標を集計してレポート出力する CLI を追加。
      - デフォルトの Pass/Fail 基準を設定（稼働率 >= 99%、注文成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
      - 日付フィルタ（--from/--to）と --db オプションを提供。欠損テーブルに対しては安全に N/A を返すロバスト設計。
  - 研究用モジュール（下位のファクター計算）
    - research/factor_research.py（骨組み）
      - DuckDB 接続を受け、prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity ファクターを計算する方針を実装（モジュール設計と定数定義、calc_momentum のインターフェース開始）。結果は (date, code) をキーとする dict リストで返す設計。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数ファイル (.env) は生成時にコメントで「絶対に Git にコミットしないこと」を明記。秘密情報はウィザードでマスクして表示。

### Notes / 動作上の重要ポイント（実装からの推測）
- run_monitoring は KABUSYS_ENV に関わらず settings.sqlite_path を使用して監視データを保存する（監視データは本番用 DB を前提にしている設計）。
- run_execution は paper_trading 時に settings.paper_sqlite_path を使用して本番 DB と完全に分離するよう設計されている（ペーパートレードの記録は data/paper_trading.db 等へ）。
- .env のパースはシェル風の export 形式やクォート・エスケープに対応しており、行内コメントの扱いにも配慮している。
- ログはコンソール（stdout）とファイルの両方に出力、ファイルハンドラが利用できない環境でもフォールバックしてコンソールのみで動作する。
- プロセス優先度や CPU affinity の設定は権限やプラットフォームに依存するため、失敗時は警告ログを出して無害にスキップする実装。
- ポートフォリオ構築・サイズ決定は "純粋関数" として DB 参照を行わない設計（テスト容易性・再現性を優先）。
- Paper Verification レポートは欠損テーブルや空データに対しても安全に N/A を返してレポート可能。

---

参考: CLI 実行例
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

（以上はコードから推測される機能の一覧です。実際のリリースノートや仕様書がある場合はそちらを優先してください。）