# Changelog

すべての互換性のある変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

### Added
- なし（現在の差分は次回リリースに含めてください）。

### Changed
- なし。

### Fixed
- なし。

---

## [0.1.0] - 2026-04-21

初回リリース — 基本的な自動売買プラットフォームのコアユーティリティとツール群を実装。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV による paper_trading モード判定を実装し、paper_trading の場合は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - ストップフラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）によるプロセス制御を実装。
    - ブローカークライアント生成（BrokerClientFactory）と依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組立て。
  - run_monitoring.py
    - SystemMonitor をポーリングで起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は起動環境にかかわらず production の sqlite_path を使用する仕様。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。
    - .env / .env.local の読み込み優先度（OS 環境変数 > .env.local > .env）を実装。
    - 環境変数パーサの強化: export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - 各種設定プロパティを提供（J-Quants、kabu API、LINE、DB パス、監視しきい値、環境種別判定等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）サポート。
  - config_setup.py
    - 対話式の .env 作成／更新ウィザードを追加。
    - 秘匿項目のマスク表示、選択肢・デフォルト値サポート、保存確認を実装。

- 設定検証ツール
  - validate_config.py
    - 起動前の環境検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- ログおよびプロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（既定 logs/ ディレクトリ）を設定。
    - LOG_LEVEL / LOG_DIR の解決順に対応、既存ハンドラの二重設定防止、日次ローテーション・30 日保持をサポート。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の優先度クラス、POSIX の nice 値）と CPU affinity 設定補助を追加。
    - アクセス権限不足や未対応 OS 時のフォールバック処理を実装。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順、同点時 tiebreaker）、等配分・スコア加重配分の実装。
    - スコア合計が 0 の場合は等金額配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存ポジションのセクター比率に基づき同一セクターの新規候補を除外するロジック。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）: bull/neutral/bear に対応、未知レジームはフォールバック（警告）。
  - portfolio/position_sizing.py
    - 複数の配分方式に対応した発注株数計算（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、利用可能現金に対する aggregate cap、cost_buffer（手数料・スリッページ見積）考慮、スケーリングと端数処理（残余キャッシュを用いた lot 単位での追加配分）を実装。

- 研究・ファクター計算
  - research/factor_research.py（実装開始）
    - DuckDB を用いたモメンタム / Value / Volatility / Liquidity 等のファクター計算の設計を追加。
    - モメンタム計算（calc_momentum）の仕様（1M/3M/6M リターン、MA200 乖離）を定義。※ファイル末尾で未完の箇所あり（続き実装予定）。

- 管理ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下件数、API レイテンシ（avg/max/P95）などを集計して人間可読なレポートを出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し、PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）と DB パスオーバーライド（--db / 環境変数）をサポート。

- パッケージ情報
  - __init__.py によるバージョン管理（__version__ = "0.1.0"）と public API エクスポート設定。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Documentation
- 各モジュールに docstring と使用例を追加してコードの意図と引数・戻り値の仕様を明記。

### Notes / Implementation details
- DB 関連
  - monitoring 用テーブルの初期化関数 init_monitoring_db を起動スクリプト側で呼び出し、監視テーブルの存在を保証（冪等）。
  - DuckDB と SQLite の両方を利用する設計。DuckDB は分析用途、SQLite は運用ログ・監視用に使用。
- 安全策
  - run_execution/run_monitoring は stop フラグファイル検知で安全に停止する仕組みを導入。
  - config.validate の live 向けチェック（LINE 通知設定と Kill Switch の安全設定）を追加。
- エラーハンドリング
  - 各所で例外を捕捉してログを残し、システムが単発の例外で停止しないよう耐障害性を意識した設計。

---

（将来のリリース案）
- research/factor_research の完全実装（残りの SQL/集計ロジック）。
- Strategy モジュール・シグナル生成とエンドツーエンドのシミュレーション。
- 単体テスト・CI の追加（現状はコード本体のみから推定）。