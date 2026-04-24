CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。
https://keepachangelog.com/ja/1.0.0/

v0.1.0 - 2026-04-24
-------------------

Added
- 初回リリース。KabuSys の基本機能群を追加。
  - 実行/監視エントリポイント
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（既定: data/paper_trading.db）を使用し、MockBrokerClient 経由でペーパートレードを実行できる設計。
      - エンジンは別スレッドで実行され、 data/stop_requested.flag により安全停止できる。
      - 実行中は pid ファイルを data/execution.pid に書き込む（設定で上書き可能）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データ分離の意図）。
      - stop フラグ（data/stop_requested.flag）でループを終了。
  - 設定管理
    - config.py: .env の自動読み込み（プロジェクトルート検出）と Settings クラスを追加。
      - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - 環境変数のパースはシングル/ダブルクォート、エスケープ、コメント処理に対応。
      - 各種プロパティ（J-Quants / kabu API / DB パス / paper trading 設定 / 監視しきい値 等）を提供。
      - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や KABUSYS_ENV の値検証を実装。
    - config_setup.py: .env を対話式に作成・更新するウィザードを追加。
      - J-Quants トークンや kabu API パスワード等の必須項目に対応。シークレット入力の扱いと確認プロンプトを提供。
  - 設定検証ツール
    - validate_config.py: 起動前チェック CLI を追加。
      - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML がインストールされている場合）。
      - --strict オプションで警告を失敗扱いにできる。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定（スコア降順 + tie-break）select_candidates
      - 重み計算: 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア0 の際は等配分へフォールバック）
    - portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap（当日売却予定銘柄の除外、unknown セクターは除外しない）
      - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）
    - portfolio/position_sizing.py
      - 発注株数計算 calc_position_sizes（risk_based / equal / score）
      - 単元株丸め、1 銘柄上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）考慮、利用可能現金に基づくスケーリングロジックを実装
  - 解析・検証ツール
    - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定する（閾値はソース内で定義）。
      - --from/--to/--db オプションに対応。
  - utils（共通ユーティリティ）
    - utils/logging_setup.py
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次, 既定: logs/）を設定。既存ハンドラをクリアして二重設定を防止。
      - LOG_DIR / LOG_LEVEL による上書き、ファイルハンドラ作成失敗時はコンソールのみで継続。
    - utils/process_priority.py
      - psutil を使い Windows/Linux/Mac 向けにプロセス優先度（high/normal/low）および CPU affinity 設定を抽象化。権限不足時は警告してスキップ。
  - research/factor_research.py（ファクター計算の骨格を追加）
    - DuckDB の prices_daily/raw_financials を利用し、Momentum / Value / Volatility / Liquidity 等の計算設計を実装開始（モメンタム計算の関数骨格を含む）。
  - パッケージ定義
    - __init__.py にてバージョンを 0.1.0 に設定。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Notes / Implementation details
- データベース
  - DuckDB と SQLite 両方を併用する設計（分析用: DuckDB、監視/発注履歴: SQLite）。
  - 監視テーブルの初期化関数 init_monitoring_db が実行前に呼ばれることでテーブルの存在が保証される（冪等）。
- Paper Trading
  - 本番 DB とペーパートレード DB を明確に分離。PAPER_TRADING_SQLITE_PATH で上書き可能。
  - PAPER_FILL_MODE によりペーパートレードの約定動作を制御（instant/partial/never/reject）。
- ロギング
  - stdout を用いた StreamHandler を採用（cron 等で stdout/stderr を一本化している運用を想定）。
  - 日次ローテーションで 30 日分保持。
- 環境の自動読み込み
  - プロジェクトルートの判定は .git または pyproject.toml の存在で行うため、配布後の動作が安定する。
  - OS 環境変数は .env の自動上書きから保護される（protected 機能）。
- 監視ループ
  - 監視は例外を捕捉してログ出力し、次回ポーリングへ継続する設計（堅牢性向上）。
  - KeyboardInterrupt を適切に扱い、DB 接続を確実にクローズする。

Dependencies / Requirements
- Python 標準ライブラリに加え、以下が想定される外部依存:
  - duckdb
  - psutil
  - PyYAML（validate_config の config/*.yaml 検証に必要。未インストール時は警告して YAML 検証をスキップ）
- SQLite は標準ライブラリの sqlite3 を使用。

Security / Operational reminders
- .env は絶対に Git 等へコミットしないこと（config_setup のヘッダ・注意書きに明記）。
- KABUSYS_ENV=live の場合は LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定等を十分に確認すること（validate_config が警告を出す）。

Migration / Backwards compatibility
- 初回リリースのため互換性に関する変更点はなし。

Acknowledgements
- ドメインロジック（PortfolioConstruction.md / StrategyModel.md 等）に基づいた実装の骨格を提供しています。今後のリリースでファクター計算や ExecutionEngine 本体の詳細実装、テスト、ドキュメント強化を予定しています。