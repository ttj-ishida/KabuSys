# Changelog

すべての注目すべき変更点をこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠します。

全般的な方針:
- semver を想定（このリリースは初期リリースとして 0.1.0）。
- ここに記載の内容は、コードベースから推測してまとめた変更点・機能説明です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
初期リリース。日本株自動売買システム「KabuSys」の基本的なランタイム、設定管理、ポートフォリオ構築、ユーティリティ群、および検証ツールを含む。

### Added
- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知してループ終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（BrokerClientFactory により生成）を使用し、paper_trading 用の SQLite（デフォルト data/paper_trading.db）に記録して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - ExecutionEngine をスレッドで実行し、停止フラグ検知時に安全に停止。

- 設定管理
  - src/kabusys/config.py
    - .env の自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込みロジック（OS 環境変数を保護する protected オプション）。
    - 複雑な .env 行パーサ（export プレフィックス、クォート文字内のバックスラッシュエスケープ、行内コメントの扱い）を実装。
    - Settings クラスを追加し、J-Quants や kabu API、DB パス、Paper Trading 関連、監視閾値、ログレベル等のプロパティを提供。
    - PAPER_FILL_MODE（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH 等の Paper Trading 向け設定をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。

- 設定関連 CLI / ツール
  - src/kabusys/config_setup.py
    - 対話式 .env ウィザードを実装。初期 .env の作成・更新を支援。
    - デフォルト項目、シークレット入力、保存前の確認、.env ファイルの書き込み（テンプレート）を提供。
    - 使用例: python -m kabusys.config_setup
  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在確認およびパース（PyYAML がインストールされている場合）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の警告など）。
    - --strict モードで警告を FAIL 扱いにできる。
    - 使用例: python -m kabusys.validate_config

- ロギング・プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログレベル・ログディレクトリ解決ロジック（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成に失敗した場合にファイル出力をスキップする安全策あり。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度（high/normal/low）を OS 間で吸収して設定するユーティリティを追加（psutil 利用）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を提供。
    - アクセス権限不足などの場合は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額ウェイト（calc_equal_weights）、スコア加重ウェイト（calc_score_weights）を追加。スコアが 0 の場合は等配分にフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄を除外可能、"unknown" セクターは制限を適用しない）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームは警告のうえ 1.0 にフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - 株数算出ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積もり、残差処理による追加配分ロジックなどを実装。

- 実行・監視用 DB 初期化フック
  - src/kabusys/monitoring/monitoring_db.py の init_monitoring_db 呼び出しに対応（各起動スクリプトから監視テーブルの存在を保証して冪等に初期化）。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
    - コマンド例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 研究用ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールを追加（DuckDB を用いて prices_daily / raw_financials を参照する設計）。
    - モメンタム計算（1M/3M/6M、MA200 乖離）、ATR、出来高等の定義と計算方針を含む（関数群を整備、計算窓とスキャン範囲の定義あり）。

- パッケージメタ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （現時点で特記すべきセキュリティ修正はなし）

### Notes / 運用上の注意
- 環境変数とデフォルト:
  - 主要な環境変数:
    - JQUANTS_REFRESH_TOKEN （必須）
    - KABU_API_PASSWORD （必須）
    - KABUSYS_ENV （development / paper_trading / live、デフォルト development）
    - LOG_LEVEL（デフォルト INFO）
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
    - PAPER_FILL_MODE（instant/partial/never/reject、デフォルト instant）
    - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD（1 で .env の自動読み込みを無効化）
  - .env 自動読み込みはプロジェクトルートが検出できた場合に有効（.git または pyproject.toml により判定）。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- ログ:
  - デフォルトで logs/ ディレクトリに日次ローテーションされたログを出力（ファイル出力に失敗すると stdout のみで継続）。
  - StreamHandler は stdout を使用（cron 等で stdout/stderr をリダイレクトしやすくするため）。
- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼び出す（権限不足の場合は警告を出してスキップ）。
- 停止制御:
  - 停止フラグファイル（data/stop_requested.flag）を用いた外部停止機構に対応。必要に応じてこのファイルを作成してプロセスに停止を促してください。
- Paper Trading と本番データの分離:
  - paper_trading 環境では paper_trading 用の SQLite を用いるように設計されており、本番監視 DB（SQLITE_PATH）と完全に分離されることを意図しています。

### Migration
- 既存環境から導入する際は、.env を作成して必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を設定し、python -m kabusys.validate_config で検証することを推奨します。
- 本番導入時は KABUSYS_ENV=live を設定することで、本番向けの追加ガード（LINE 設定の確認、KILL_FLAG_CLEAR_ON_START のチェック等）が動作します。

---

今後の改善案（実装候補・設計メモ）:
- position_sizing: 銘柄別 lot_size を stocks マスタ等から取得する拡張（現在は全銘柄共通 lot_size）。
- risk_adjustment.apply_sector_cap: price 欠損時のフォールバック価格（前日終値など）を導入して過小評価を防ぐ。
- factor_research: Value / Volatility / Liquidity の具体実装と単体テスト整備。
- 起動スクリプトのユニットテスト用フック（DB や BrokerClient のモック注入）や、systemd 等向け unit ファイルのテンプレート追加。

（以上）