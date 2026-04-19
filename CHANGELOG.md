# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- リリース日はソースコードから推測した初期リリース日を付与しています（推測に基づくため実際の公開日とは異なる場合があります）。
- 各項目はコードベースの実装・コメントから推測した機能説明・注意点を記載しています。

## [Unreleased]

- 小さな改善・ドキュメント補足やテストの追加を予定。
- position_sizing の将来的な拡張候補:
  - 銘柄毎の lot_size を stocks マスタで持たせる設計への拡張（コメントにTODOあり）。
- risk_adjustment の価格欠損時のフォールバック実装（コメントで前日終値等を検討中）。
- factor_research モジュールの未完の実装箇所（ファクター計算の続き実装予定）。

---

## [0.1.0] - 2026-04-19

概要: 初期リリース。自動売買フレームワークのコアユーティリティ、ポートフォリオ構築ロジック、実行/監視の起動スクリプト、設定支援ツール、Paper Trading 向け検証レポート等を提供。

### Added
- 基本情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 実行 / 監視スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を利用して本番/モックブローカーを生成。
    - ストップフラグ（data/stop_requested.flag）を監視して安全に停止。
    - 実行 PID を data/execution.pid に保存（pid_file に渡す）。
    - プロセス優先度を High に設定（utils.process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知で安全にループ終了。

- 設定管理・検証・ウィザード
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順・上書きルールを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 複雑な .env パース処理（export 付き、クォート文字列、インラインコメント処理、エスケープ対応）。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、環境種別、ログレベル、Paper Trading 用設定など）をプロパティ経由で取得。値検証（enum チェックや PAPER_FILL_MODE のバリデーション）を実施。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI。必須項目や説明付きプロンプトを提供。
    - .env の読み書きロジックを実装（既存値の読み込み・シークレットマスク表示など）。
  - validate_config.py
    - .env および config/*.yaml の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告出力。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ロジック（純粋関数群）
  - kabusys.portfolio パッケージを追加:
    - portfolio_builder.py
      - select_candidates: BUY シグナルのスコア降順選定（同点は signal_rank でタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコア合計が 0 の場合は等配分にフォールバック（警告）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限をチェックし新規候補を除外（unknown セクターは除外対象外）。
      - calc_regime_multiplier: market regime に基づく投入資金乗数（bull/neutral/bear をマップ。未知値はフォールバック 1.0）。
    - position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算、単元株（lot_size）で丸め、aggregate cap（available_cash）超過時のスケーリングと再配分ロジックを実装。
      - 手数料/スリッページ見積りのための cost_buffer を考慮。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティ。
    - ログディレクトリ作成に失敗した場合でもコンソールログのみで継続するフェイルセーフ。
    - ログレベル / ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティ。
    - CPU affinity 設定機能（最初の N コアに固定）を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップする安全設計。

- Tools
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を出力。
    - デフォルト DB: data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH / コマンドライン --db で指定可能。
    - 判定基準（閾値）はスクリプト内定数で定義（稼働率 99% 等）。
    - P95 計算・日付フィルタリングを実装。

- Research
  - research/factor_research.py（部分実装）
    - DuckDB を用いたファクター計算（Momentum, Value, Volatility, Liquidity）を設計。モメンタム計算関数 calc_momentum の開始実装あり（未完部分あり）。

### Changed
- （初期リリースにつき該当なし）

### Fixed
- （初期リリースにつき該当なし）

### Deprecated
- （初期リリースにつき該当なし）

### Removed
- （初期リリースにつき該当なし）

### Security
- （特記事項なし）

---

補足（実装上の注意 / 将来対応方針）
- .env 読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後に環境変数から明示的に設定したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- position_sizing と risk_adjustment に TODO コメントあり。データ欠損時のフォールバックロジックや銘柄別単元対応は将来的な拡張対象です。
- ログディレクトリ作成やプロセス優先度の設定は OS/権限に依存するため、実運用環境では権限・ディレクトリ権限設定を確認してください。