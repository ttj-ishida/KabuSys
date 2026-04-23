# Changelog

すべての重要な変更点を「Keep a Changelog」形式で日本語にて記録します。  
リリース日はコードベース内の実装内容から推測して付与しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- ドキュメント的変更や小さな改善・リファクタが随時発生する想定です。
- 既知の制限や TODO:
  - portfolio.position_sizing の lot_size は全銘柄共通で、将来的に銘柄別単元対応を予定。
  - risk_adjustment.apply_sector_cap で price が欠損（0.0）の場合のフォールバック価格未実装。
  - research.factor_research モジュールは実装途中でスニペットが含まれており、完全実装が必要。

---

## [0.1.0] - 2026-04-23

Added
- 基本機能の初期実装（初期リリース）。
  - 全体のパッケージバージョンを `__version__ = "0.1.0"` として設定。
- 起動スクリプト（プロセス管理 / デーモン系）
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。スレッド実行、停止フラグ（data/stop_requested.flag）の検出、PID ファイル管理（data/execution.pid）を実装。
    - 環境変数 `KABUSYS_ENV=paper_trading` 時に MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）へ完全分離して記録する挙動をサポート。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - RiskConfig にデフォルト値を設定（max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。環境変数 `MONITOR_POLL_INTERVAL` で間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視 DB は環境に関わらず本番 sqlite_path を使用する仕様。
    - 停止フラグの検出や例外時ログ出力を行い、安定して継続するよう設計。
- 設定管理と CLI
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）および .env / .env.local の自動読み込み機能を実装（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースロジックを堅牢化（export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント処理等に対応）。
    - Settings クラスで主要設定値をプロパティ経由で取得可能に（J-Quants / kabu / DB パス / Paper Trading 設定 / 監視閾値等）。
    - PAPER_FILL_MODE の妥当性チェック（instant, partial, never, reject）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を提供。シークレット項目はマスク表示、デフォルト値の提示、保存確認を実装。
    - .env の書式テンプレートを生成（.env を Git に含めない旨の注意を含む）。
  - validate_config.py
    - 起動前チェック CLI を実装。必須環境変数の存在確認、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスや config/*.yaml ファイルの存在チェックを行う。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。`--strict` で警告をエラー扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順・タイブレークを含めソートして上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全銘柄スコアが 0 の場合は等配分にフォールバック）を実装。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限により候補銘柄を除外するロジックを実装（売却予定銘柄除外や "unknown" セクターの扱いなどを定義）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に対する投下資金乗数を実装（未知レジームはフォールバックで 1.0）。
    - position_sizing.py
      - calc_position_sizes: risk_based / equal / score の各配分方式に従い発注株数を計算。単元株丸め、per-position 上限、aggregate cap のスケールダウン、cost_buffer の考慮、残差処理（lot 単位で追加配分）を実装。
- ユーティリティ
  - utils.logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーへ設定。ログディレクトリ/レベルの解決順を実装。
  - utils.process_priority.py
    - クロスプラットフォームでのプロセス優先度設定と CPU affinity 固定（psutil 使用）。Windows / POSIX の差分吸収と例外時のフォールバック処理を実装。
- 分析・検証ツール
  - tools.paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し、PASS/FAIL レポートを生成する CLI を実装。閾値はスクリプト内定数で定義。
- 研究用モジュール（DuckDB ベースのファクター計算）
  - research.factor_research.py
    - モメンタム・ボラティリティ等のファクター計算を行う設計を実装。DuckDB 接続で prices_daily / raw_financials を参照する方針。モジュールは設計・一部実装済み（計算範囲定義や定数を含む）。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db が使用され、必要な監視テーブルが存在することを保証（冪等に初期化）。

Changed
- ログの標準出力を stdout に統一（cron 等からのリダイレクト運用を想定）。
- run_* スクリプトで起動直後にプロセス優先度を high に設定するよう共通の方針を採用（set_process_priority を呼び出し）。

Fixed
- 環境変数パーサの強化:
  - export プレフィックス、クォート内エスケープ、インラインコメント判定などのエッジケースに対応。
- MONITOR_POLL_INTERVAL に 0 以下や不正文字列が指定された場合にデフォルトへフォールバックし、time.sleep による例外を防止。
- DB パス存在チェックと警告の改善（親ディレクトリが存在しない場合の注意喚起）。

Security
- config_setup.py で生成される .env に「.env を絶対に Git にコミットしない」旨のヘッダを明示。

Removed
- なし（初期リリース）。

Notes / Known limitations
- 一部の機能は外部ライブラリ（psutil, PyYAML）に依存し、権限不足や未インストール時にはフォールバック動作（警告）を行う。運用環境ではこれらのインストール・権限確認が必要。
- research.factor_research の完全実装、銘柄別 lot_size の導入、欠損価格時のフォールバックロジック等は将来的な課題として残す。
- Production 運用時の細かいチューニング（RiskConfig の値、閾値、ログローテーションポリシー等）は運用実績に合わせて調整推奨。

---

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0