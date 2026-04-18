# Changelog

すべての重要な変更をここに記載します。本ファイルは「Keep a Changelog」形式に準拠しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

なお、以下の記載はコードベースの内容から推測して作成しています（実装意図・振る舞いの説明を含む）。

## [Unreleased]
- （現時点での未リリース変更はありません）

## [0.1.0] - 2026-04-18
初回リリース。日本株自動売買システム KabuSys のコアユーティリティ、実行・監視スクリプト、ポートフォリオ構築ロジック、検証ツールなどを含む。

### Added
- 全体
  - パッケージ初期リリース。モジュール構成、CLI、ユーティリティ類を提供。
  - バージョン情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 実行・監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 時は専用の MockBrokerClient を使用する（BrokerClientFactory による抽象化）。
    - paper_trading の場合、専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 実行中の PID ファイル管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）によるプロセス制御。
    - スレッドで ExecutionEngine を起動し停止フラグ／タイムアウトを監視。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用（環境に依存しない）。
    - stop フラグ検出時の安全なシャットダウン処理。

- 設定管理
  - config.Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。
    - .env/.env.local の読み込み優先度（OS 環境変数を保護）。
    - 各種設定値（J-Quants / kabu API / DB パス / monitoring 閾値など）をプロパティとして提供。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証、PAPER_FILL_MODE の許容値チェックなど。
  - config_setup: 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 主要項目の説明、既存値の再利用、シークレット項目のマスク表示、保存機能付き。
    - .env のテンプレート書き出し（.env に書き込む際の注意文を含む）。

- 設定検証
  - validate_config CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの存在確認（親ディレクトリチェック）、
      config/*.yaml の存在・パース検証（PyYAML が無い場合はスキップ）等を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - setup_logging: 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler、デフォルト logs/、30 日保持）を設定。
    - ログレベル・ログディレクトリの解決ロジックを実装。既存ハンドラのクリア（重複防止）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして警告出力。
  - process_priority: クロスプラットフォームのプロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応した優先度設定。アクセス拒否等は警告ログでスキップ。
    - set_cpu_affinity によるコアピンニング機能を提供（未指定時は全コア）。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: シグナル選別・重み計算を追加（select_candidates, calc_equal_weights, calc_score_weights）。
    - スコア降順・タイブレークの扱い、スコア全体が 0 の場合のフォールバックを実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）・レジーム乗数（calc_regime_multiplier）を追加。
    - 既存保有をセクター別に集計し、max_sector_pct を超えるセクターを候補から除外する機能。
    - レジームに応じた投下資金乗数を返す（bull/neutral/bear）。
  - position_sizing: 発注株数計算ロジックを追加（calc_position_sizes）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer（手数料・スリッページ想定）を実装。
    - 価格欠損時のスキップや、スケールダウン時の残差配分ロジックを採用。

- 研究・指標計算
  - research/factor_research: ファクター計算モジュール（モメンタム等）を追加（設計・一部実装）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する方針。
    - モメンタム、MA200 乖離、ATR、流動性指標などを計画（関数 calc_momentum の骨組みあり、詳細実装の続きが示唆される）。

- ツール
  - tools/paper_verification_report: ペーパートレード検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB から集計。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ等。
    - 判断基準（閾値）を定義し、PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）対応、DB テーブル欠損時のフォールバック処理。

- DB 関連
  - 監視用 DB の初期化呼び出しを各スクリプトで行う（init_monitoring_db を使用して冪等にテーブルを保証）。
  - DuckDB を分析用に統合（duckdb パスは Settings.duckdb_path で管理）。

### Changed
- （初回リリースのため変更履歴はなし。ただし内部実装の注意点・設計方針は各モジュール内ドキュメントに記載）

### Fixed
- （初回リリースにおける既知の問題は特にコードから明示されていないが、次版での改善候補を下記に列挙）
  - 一部の関数に TODO コメントや将来的拡張の注記あり（例: position_sizing の銘柄別 lot_size 拡張、risk_adjustment の価格フォールバック）。

### Security
- シークレット扱いの環境変数は対話ウィザードでマスク表示（.env の取り扱いについて README 等で Git へコミットしない旨を明示）。

### Notes / Known limitations (今後の改善候補)
- research/factor_research の一部実装が途中で終わっている（calc_momentum の実装継続が必要）。
- position_sizing の価格欠損時のフォールバック価格（前日終値等）未実装。
- config/*.yaml の詳細検証は PyYAML に依存するため、環境により検証がスキップされる可能性あり。
- ログディレクトリ作成失敗時はファイルログが無効化される（十分なアクセス権の確認が必要）。

---

参照:
- 各ファイルのドキュメンテーションストリング（src/kabusys/*.py）を元に要約・推測して作成しました。必要であれば、各機能についてより詳細なリリースノート（例: CLI 使用例、環境変数一覧、既知の問題の詳細）を追記します。