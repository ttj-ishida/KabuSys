# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルは、コードベース（現時点のスナップショット）から推測した初回リリース向けの変更履歴です。

なお、バージョン番号はパッケージ定義 (src/kabusys/__init__.py) に合わせて 0.1.0 としています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19
初回リリース — 基本機能一式を追加。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py に __version__ = "0.1.0"）。
  - パッケージエクスポートを整理（portfolio / execution / monitoring などのサブモジュールを公開）。

- 設定・環境変数管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動読み込み機能（プロジェクトルートの .env / .env.local を読み込む）。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須/任意の環境変数取得メソッド（J-Quants トークン、kabu API パスワード、DB パス、ログ関連、Paper Trading 設定など）。
    - env 値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の妥当性チェック）。
  - .env パースの堅牢化:
    - 引用符（シングル/ダブル）やエスケープシーケンス、コメント（#）の扱いに対応するパーサを実装。

- 設定関連 CLI
  - 設定検証ツール（src/kabusys/validate_config.py）
    - .env と config/*.yaml の存在・基本妥当性をチェックする CLI を追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV のガード、YAML のパースチェック（PyYAML 未導入時はスキップして警告）。
    - --strict オプションで警告を失敗扱いにできる。
  - 環境設定ウィザード（src/kabusys/config_setup.py）
    - 対話式に .env を作成・更新するウィザードを提供。
    - シークレット入力のマスク表示、既存 .env の読み込み・再利用、ファイル書き出しロジックを実装。

- 実行用スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV に応じて本番/ペーパートレードの SQLite を切り替え（paper_trading の場合は paper_sqlite_path を使用）。
    - BrokerClientFactory を利用したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てと実行。
    - スレッドでエンジンを実行し、data/stop_requested.flag による安全停止、PID ファイル管理（data/execution.pid）をサポート。
    - RiskManager のデフォルト設定例をコード内に明記（max_position_pct 等）。
  - Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを実装。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視 DB の一貫性確保）。

- ログ・プロセス管理ユーティリティ
  - ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout 出力の StreamHandler と日次ローテーションする TimedRotatingFileHandler（デフォルト logs/<app>.log、30 日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - プロセス優先度 / CPU アフィニティ設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux/macOS の差を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限や未対応環境で失敗した場合は警告を出して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分（全スコアが 0 の場合は等分にフォールバックし警告）。
  - セクター集中・レジーム補正（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算して上限を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知のレジームは警告と共に 1.0 でフォールバック）。
    - 実装中の TODO をコード内に明記（価格欠損時のフォールバック戦略検討など）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、lot_size（単元）丸め、per-stock および aggregate の上限調整、cost_buffer を考慮したスケーリングロジックを実装。
    - aggregate cap の際のスケールダウンと残余キャッシュでの端数再配分ロジックを実装。
    - 将来的な拡張（銘柄別 lot_size マップ導入）を TODO として記載。

- データ解析・リサーチ
  - ファクター計算の下地モジュール（src/kabusys/research/factor_research.py）
    - Momentum / MA / ATR / Volume 周りの定数と.calc_momentum の実装方針を追加。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計（ファイルは途中まで実装）。
    - DuckDB を利用した分析を前提に設計。

- ツール
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
    - SQLite（Paper Trading 用 DB）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計してレポートを標準出力に出力。
    - デフォルトしきい値（稼働率 99%、成功率/送信率/レイテンシ基準）を定義し PASS/FAIL 判定を行う。
    - --from / --to / --db オプションに対応。P95 計算の実装あり。

- DB 周り
  - SQLite / DuckDB 接続の利用を全体で統一。
    - 監視用のテーブル初期化 init_monitoring_db が呼ばれる（monitoring 用テーブルの冪等な作成を保証）。

### Changed
- （初回リリースのため適用なし）

### Fixed
- （初回リリースのため適用なし）

### Notes / Known limitations
- run_monitoring は「監視 DB」として Settings.sqlite_path（本番用の SQLite）を環境にかかわらず使用するため、監視データと paper_trading の発注ログを分離したい場合は設定（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を適切に構成してください。
- process priority / cpu affinity の設定は OS 権限に依存し、権限不足や非対応プラットフォームでは警告を出してスキップします。
- risk_adjustment のエクスポージャー計算は price_map に 0.0 が含まれると過少見積りになる可能性があり、将来的にフォールバック価格（前日終値など）を導入する TODO が残っています。
- position_sizing は現状単元(lot_size)を全銘柄共通で扱う設計。将来的に銘柄別単元対応への拡張を想定しています。
- factor_research モジュールは設計方針・定数・一部関数の土台が含まれており、完全実装は一部未完（コードスナップショットの末尾が途中で切れているため）。

### Security
- .env は生成時に明示的に .env ファイルと注意文が出力され、Git へコミットしない旨の注意を明記。秘密情報（API トークン等）は .env に保管する前提。

---

もし CHANGELOG に追記したい追加の変更点や、リリース日付の調整、より詳細な「Fixed / Changed」項目の分類など希望があれば教えてください。コードの別ファイルやコミット履歴があれば、さらに正確な Changelog を作成します。