# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
最新の変更が上に来ます。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-18

最初の公開リリース。自動売買システム KabuSys のコア機能・ユーティリティ・ツール群を追加しました。

### Added
- 基本パッケージ情報
  - __version__ を "0.1.0" に設定。

- 実行スクリプト / デーモン系
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクトの data/stop_requested.flag を用いる。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時はペーパートレード用 DB（data/paper_trading.db）と MockBrokerClient を利用し、本番 DB と完全分離。
    - 起動時に data/execution.pid を使用した PID 管理、stop フラグ検知で安全停止。

- 設定管理 / ウィザード / 検証
  - config.py: Settings クラスを導入。
    - .env の自動ロード（.env, .env.local）を実装（プロジェクトルートの検出は .git / pyproject.toml 基準）。
    - 複雑な .env パースに対応（export プレフィックス、引用符付き値、バックスラッシュエスケープ、インラインコメントの取り扱い等）。
    - Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）と各種閾値/パス等のプロパティを提供。
    - 環境種別（development/paper_trading/live）・ログレベル等の検証とユーティリティプロパティ（is_live / is_paper / is_dev）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - シークレット項目はマスク表示、デフォルト値・選択肢をサポート。
    - .env を安全に書き出すテンプレートを提供（.env を絶対にコミットしない旨の注意を出力）。
  - validate_config.py: 起動前に .env と config/*.yaml の整合性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェックを実装。
    - PyYAML が存在すれば config/*.yaml のパース検証を実施、存在しなければ警告。
    - --strict モードで警告を FAIL 扱い（exit(1)）にできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - 統一的ロギング設定関数 setup_logging を提供。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日分保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL 環境変数あるいは引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py:
    - psutil を利用したクロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定 set_process_priority を追加。
    - CPU affinity を設定する set_cpu_affinity を提供（指定コア数でプロセスを固定）。
    - 権限不足や未対応環境では安全にフォールバックして警告を出力。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順・タイブレークルールに基づく候補選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア0の場合に等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター別エクスポージャー計算、"unknown" セクターはチェック対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap のスケーリング処理、コストバッファ考慮、余剰キャッシュによる再配分ロジックを実装。

- 研究 / ファクター計算基盤
  - research/factor_research.py（ファクター計算モジュール）を追加。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 等の計算を行う設計（モジュールの冒頭設計コメントと一部計算ロジックが含まれる）。
    - ファクターは (date, code) ベースの dict リストで返す想定。

- 分析 / 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計して PASS/FAIL 判定を行う。
    - デフォルト DB は env/PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- DB / 分析
  - DuckDB（duckdb）と SQLite の両方を利用する運用を想定。run_* スクリプト内で各接続を確立し、起動時に monitoring 用テーブルの初期化（init_monitoring_db）を冪等に保証。

### Changed
- 設計方針（実装上の注意）
  - 監視コンポーネントは環境に依存せず本番の sqlite_path を参照する設計（運用上の決定）。
  - .env 自動読み込みは OS の環境変数を保護する（既存 OS 環境変数を上書きしないよう保護セットを採用）。
  - ログ出力は stdout を基準にし、ファイル出力はオプション（ディレクトリ作成失敗時にフォールバック）に。

### Fixed
- リスク制御 / 配分に関する実装上の堅牢化
  - score_weights の合計が 0 の場合のフォールバック実装（等金額配分）。
  - position_sizing の aggregate cap スケーリング時に端数対応（lot_size 単位での再配分）を実装し、過度の投下を防止。

### Security
- シークレット取扱いに注意
  - config_setup の説明・出力で .env を Git にコミットしない旨を明示。
  - シークレット入力はウィザードでマスク表示。

### Notes / その他
- validate_config による事前チェックで PyYAML が無ければ YAML 内容検証はスキップされるが警告が出るため、config/*.yaml の検証には PyYAML の導入を推奨。
- process_priority と CPU affinity の設定は権限が必要な場合があり、権限不足時は警告を吐いて安全にスキップする設計。
- run_execution は起動時に既に停止フラグがある場合は起動を行わず即時終了する安全ロジックを備える。

## 既知の制限 / TODO
- position_sizing の price 欠損時（price == 0.0）に対するフォールバック価格（前日終値・取得原価など）の取り扱いは TODO コメントあり。
- research/factor_research の一部関数は実装途中（ファイル末尾が途中で切れている箇所が見られる）ため、完全実装が必要。
- 将来的な拡張: 銘柄ごとの lot_size を持つ stocks マスタの導入により、銘柄別単元対応を行う想定。

---

参考: Keep a Changelog — https://keepachangelog.com/en/1.0.0/