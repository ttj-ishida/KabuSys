CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。  
各リリースは「Added / Changed / Fixed / Deprecated / Removed / Security」セクションを持ちます。

0.1.0 - 2026-04-19
-----------------

### Added
- 初期リリースを公開。
- 実行用スクリプトを追加。
  - run_execution: ExecutionEngine を起動するエントリポイントを実装。プロセス優先度を "high" に設定し、スレッドでエンジンを実行して停止フラグ検出で安全に終了するロジックを備える（`src/kabusys/run_execution.py`）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能、停止フラグでループを抜ける（`src/kabusys/run_monitoring.py`）。
- 設定管理を実装。
  - Settings クラスを追加し、.env / 環境変数から設定を取得するユーティリティを提供（`src/kabusys/config.py`）。
  - プロジェクトルート自動検出（.git または pyproject.toml）と .env 自動読み込みを実装（自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - .env パーサは `export ` プレフィックス、クォート、エスケープ、インラインコメントなどを扱えるよう実装。
  - Paper Trading 用の分離された SQLite パス（`PAPER_TRADING_SQLITE_PATH`）と fill モード (`PAPER_FILL_MODE`) サポート。
- 設定関連 CLI を追加。
  - config_setup: 対話式ウィザードで `.env` を生成/更新するツールを追加（`src/kabusys/config_setup.py`）。
  - validate_config: 起動前に .env と config/*.yaml のチェックを行う検証ツールを追加。`--strict` オプションで警告を失敗扱いにできる（`src/kabusys/validate_config.py`）。
- ロギング基盤を追加。
  - setup_logging ユーティリティを実装。コンソール (stdout) と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定、ログディレクトリ自動作成・30日保持（`src/kabusys/utils/logging_setup.py`）。
- プロセス制御ユーティリティを追加。
  - set_process_priority: Windows / POSIX を吸収してプロセス優先度を設定（`high|normal|low`）。失敗時は警告を出してスキップ。
  - set_cpu_affinity: 指定コア数で CPU affinity を設定（権限不足時は警告を出してスキップ）（`src/kabusys/utils/process_priority.py`）。
- Portfolio 構築モジュールを追加（純粋関数群、DB参照なし）。
  - 候補選定・重み計算（select_candidates / calc_equal_weights / calc_score_weights）（`src/kabusys/portfolio/portfolio_builder.py`）。
  - セクター集中制限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）（`src/kabusys/portfolio/risk_adjustment.py`）。
  - ポジションサイジング（calc_position_sizes）: risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケーリング、コストバッファ考慮（`src/kabusys/portfolio/position_sizing.py`）。
  - これらをまとめてエクスポートするパッケージ `kabusys.portfolio` を追加。
- Paper Trading 検証レポート生成ツールを追加。
  - paper_verification_report: ペーパートレードの SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95）などを集計・評価するレポートを標準出力に出力（`src/kabusys/tools/paper_verification_report.py`）。
  - デフォルト閾値（稼働率 >= 99% など）を定義し、PASS/FAIL 判定を行う。
- 研究用ファクター計算モジュール雛形を追加。
  - factor_research: DuckDB 接続を使ったモメンタム等のファクター計算実装の骨子（部分実装／コメントあり）（`src/kabusys/research/factor_research.py`）。
- パッケージ初期化ファイルにバージョンを設定（`__version__ = "0.1.0"`）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Notes / Implementation details
- run_monitoring は「監視用 DB」（settings.sqlite_path）を KABUSYS_ENV に関わらず本番パスとして使用する設計（監視データは環境に依存しない想定）。
- run_execution は paper_trading 環境時に paper_trading 用の専用 SQLite DB を使用し、本番データと完全分離する。
- .env の自動読み込みは OS 環境変数を保護しつつ `.env`（優先度低） → `.env.local`（優先上書き）を読み込む挙動。
- 設計上、Portfolio モジュールの関数は純粋関数（副作用なし）でテスト容易性を重視。将来的に銘柄ごとの lot_size や価格フォールバックの拡張を想定する TODO コメントあり。
- logging_setup はログディレクトリ作成に失敗した際ファイル出力をスキップしてコンソールのみで継続する耐障害性を備える。
- process_priority / set_cpu_affinity は権限不足や未対応 OS に対して安全にフォールバックする。

今後の予定（非包括的）
- factor_research の完全実装（各ファクターの SQL / 計算ロジックの完成）。
- 銘柄別単元株情報（lot_size）の導入と position_sizing の拡張。
- 監視・実行のユニットテスト強化と CI 統合。
- Paper Trading レポートの自動アラート化（LINE など）と可視化出力（CSV/JSON）。

以上。