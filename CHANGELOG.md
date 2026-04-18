# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成した初期リリース向けの変更履歴です。

フォーマット:
- Unreleased: 今後の変更（現時点は空）
- 各リリース: 追加(Added)、変更(Changed)、修正(Fixed)、注意点(Notes) 等

※ バージョン番号は src/kabusys/__init__.py の __version__ を参照しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成を実装
  - パッケージ名: kabusys（src/kabusys）
  - バージョン: 0.1.0

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止用フラグファイル data/stop_requested.flag による終了検知。
    - 監視用途の SQLite は環境に関係なく settings.sqlite_path（本番パス）を使用。
    - SQLite / DuckDB 接続の初期化処理を含む（監視 DB の初期化関数 init_monitoring_db を呼び出し）。

  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（settings.paper_sqlite_path）を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成（テスト/Mock に対応する想定）。
    - ExecutionEngine を別スレッドで起動し、停止フラグ（data/stop_requested.flag）を検知して安全に停止。
    - 実行用 PID ファイルのパス管理（data/execution.pid を利用）。

- 設定管理
  - config.py
    - .env ファイルの自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env / .env.local の読み込み順（OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 複雑な .env パース実装: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなど。
    - Settings クラスで各種設定（J-Quants / kabuAPI / データベースパス / 監視しきい値 / 環境判定等）をプロパティとして提供。
    - PAPER_FILL_MODE（paper_trading 用 fill モード）などの妥当性検査を実施。

- 設定ユーティリティ CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツール。
    - 入力のマスク（シークレット）、選択肢、デフォルト提示、既存 .env の読み込み再利用に対応。
    - 保存前確認・キャンセル処理あり。

  - validate_config.py
    - .env および config/*.yaml の基本検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パス存在チェック、YAML のパースチェック（PyYAML が無ければ警告）。
    - --strict オプションで警告も失敗扱いにできる。
    - exit コードで成功/失敗を表現。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - setup_logging() により、ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（デイリーローテーション、30 日保持）を設定。
    - ログレベル・ログディレクトリの解決優先順をサポート（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を提供。
    - Windows / POSIX（Linux/macOS/FreeBSD）の差分を吸収し、権限不足や未対応環境では警告ログを出して安全にスキップするよう実装。

- ポートフォリオ構築モジュール（純粋関数、DB非依存）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコア全ゼロ時に等金額へフォールバックの警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）
      - 既存保有のセクター別時価計算、上限超過セクターの候補除外、"unknown" セクターは上限適用しない挙動。
      - sell_codes（当日売却予定）を評価から除外可能。
    - レジーム乗数（calc_regime_multiplier）
      - bull/neutral/bear に基づく乗数（1.0 / 0.7 / 0.3）。未知レジームは警告の上 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出（calc_position_sizes）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、総投下上限のスケーリング、cost_buffer（手数料・スリッページ見積）を考慮した安全なスケーリングロジックを実装。
    - price 欠損や 0 値の扱いはログ出力してスキップ。

- 研究系（ファクター計算）
  - research/factor_research.py (初期実装)
    - Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計。DuckDB 接続を受け取り prices_daily / raw_financials を参照する想定。
    - 一連の定数（期間定義など）を定義。
    - （注）ファイル末尾で実装が途中で切れている箇所あり（開発継続が必要）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト（SQLite DB 参照）。
    - 稼働率、注文成功率（fill_rate）、送信率、API レイテンシ（P95）などを集計し PASS/FAIL 判定を出力。
    - 環境変数 PAPER_TRADING_SQLITE_PATH / コマンドライン --db オプション対応。
    - デフォルトしきい値（稼働率 99% 等）を定義。

- モジュールエクスポート
  - portfolio パッケージで主要関数を __all__ によって公開。

### Changed
- （初回リリースのため、過去からの変更はなし。コード内に設計選択の注記あり）
  - run_monitoring: 監視は環境変数 KABUSYS_ENV に関係なく「本番用の sqlite_path」を参照する設計。
  - config: .env の自動読み込みは OS 環境変数を保護しつつ .env.local が .env を上書きする仕様を採用。

### Fixed
- （初回リリースにおける既知の安全対策）
  - logging_setup: ログディレクトリ作成失敗時にプロセスが失敗しないようファイルハンドラ作成をスキップするフォールバックを実装。
  - process_priority: 権限不足や未実装 API に対して例外を握り潰さず警告ログでスキップする挙動を実装。

### Notes / Known issues / TODO
- research/factor_research.py の実装が途中で切れている（ファイル末尾が不完全）。ファクター計算ロジックの継続実装が必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合のエクスポージャー算出に関する注記あり（将来的に前日終値や取得原価でフォールバックする検討）。
- .env ファイルの取り扱い:
  - .env は絶対にリポジトリにコミットしない運用が README 等で推奨される設計（config_setup.py のヘッダ内容参照）。
- 監視・実行フローはファイルベースの stop/kill フラグに依存する。コンテナ/プロセスマネージャでの利用時は運用ルールに注意が必要。
- 一部の依存モジュール（PyYAML、psutil、duckdb、sqlite3 等）が必要。validate_config は PyYAML が無ければ YAML 検証をスキップして警告を出す。

### セキュリティ
- 環境変数の取り扱いに注意:
  - JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD 等のシークレットは .env に保存しても環境保護が必要。
  - config_setup.py は .env を生成するが、ファイル管理（パーミッション、バックアップ、Git からの除外）は運用上重要。

---

以上がコードベース（src/kabusys）から推測して作成した CHANGELOG.md です。必要であれば、各項目をさらに詳細化したりリリース日を調整したりできます。どの程度の粒度で出力するか指示をください。