# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースバージョンはパッケージの __version__ に従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。以下の主要コンポーネントと CLI / ユーティリティが含まれます。

### 追加 (Added)

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（ペーパートレード）を使用し、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用する。
    - 実行中の PID 管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）による安全停止をサポート。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。
    - 監視（monitoring）は環境にかかわらず本番の sqlite_path を使用して監査データを保持。

- 設定・環境管理
  - config.py
    - .env ファイル自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - クォートや export プレフィックスに対応した堅牢な .env パーサ実装。
    - 必須/オプションな環境変数のプロパティインタフェース（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - KABUSYS_ENV (= development / paper_trading / live) やログ設定の検証ロジック。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - シークレット項目のマスク表示、選択肢やデフォルトの提示、保存確認機能を提供。
  - validate_config.py
    - 起動前の構成検証 CLI（.env と config/*.yaml の存在と整合性チェック）。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等重み (calc_equal_weights)、スコア重み (calc_score_weights) 実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)。
    - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier)（bull/neutral/bear のマップ）。
  - portfolio/position_sizing.py
    - 株数決定ロジック (calc_position_sizes)：risk_based / equal / score の配分方式、単元（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap 処理など。

- 解析・研究ユーティリティ
  - research/factor_research.py（ファクター算出モジュール）
    - Momentum / Value / Volatility / Liquidity 等のファクターを DuckDB 上の prices_daily / raw_financials 参照で計算する設計。
    - （ファイルは本リリースに含まれるが、関数は段階的実装を想定）

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - 閾値は定数で定義（例: 稼働率 99.0%、Fill Rate 90.0%、P95 レイテンシ 200ms）。
    - --from / --to / --db オプションに対応。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティ。StreamHandler（stdout）＋ TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日分保存）。
    - LOG_LEVEL / LOG_DIR / app_name 引数で挙動をカスタマイズ可能。
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定（Windows/Linux/macOS 対応）と CPU affinity 設定ヘルパー。
    - set_process_priority("high" 等) を使用して起動直後に優先度を上げる設計。

- パッケージ初期化
  - __init__.py: バージョン 0.1.0、主要サブパッケージのエクスポート指定。

### 変更 (Changed)

- ロギング
  - すべての起動スクリプトで setup_logging(app_name=...) を呼び出すことでログ出力を標準化。
  - ファイルハンドラ作成失敗時はコンソール出力のみで継続するフォールバックを導入。

- DB 接続ポリシー
  - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使う設計（監査一元化）。
  - Execution は paper_trading 環境時に専用の paper_sqlite_path を使い本番 DB と分離。

### 修正 (Fixed)

- .env パーサの強化
  - export プレフィックスとシングル/ダブルクォート内のバックスラッシュエスケープに対応。
  - クォートなしの行でインラインコメント扱いのルールを改善（'#' の直前が空白/タブの場合のみコメントとして扱う）。

- ポートフォリオ重み計算のフォールバック
  - calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックし、警告ログを出力するように改善。

- position_sizing の aggregate cap
  - cost_buffer（スリッページ・手数料想定）を導入し、投資コスト見積りを保守的に計算するように改善。
  - スケールダウン後の再配分ロジックで残余キャッシュを利用し、lot_size 単位で追加配分する実装を導入。

### セキュリティ (Security)

- 秘密情報
  - config_setup の対話表示ではシークレット項目をマスク表示（表示・保存は .env に平文で保存されるため .env を絶対に Git にコミットしないよう警告を明示）。
  - validate_config で必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）が未設定のときエラーとして検出。

### 互換性（Breaking Changes）

- なし（初回リリースのため既存互換性の問題はありません）。ただし運用上の注意点があります（下記参照）。

### 運用上の注意 / マイグレーション

- 必須環境変数
  - JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD を必ず設定してください。未設定だと起動時にエラーになります（validate_config でも検出可能）。
- .env の自動ロード
  - デフォルトではプロジェクトルートの .env / .env.local を起動時に自動読み込みします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ
  - デフォルトログディレクトリは logs/。作成に失敗した場合はファイル出力が無効化され stdout のみになります。必要に応じて LOG_DIR を設定してください。
- ポーリング間隔
  - 監視プロセスのポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（秒単位）。0 以下や数値でない値は無視されデフォルト 60 秒が使用されます。
- Kill / Stop フラグ
  - 停止制御は data/stop_requested.flag（プロジェクトルート直下の data 配下）を参照する方式です。KILL フラグや自動クリアの動作は KILL_FLAG_CLEAR_ON_START で制御します。特に本番 (KABUSYS_ENV=live) では自動クリアを有効にしないことを推奨します（validate_config で警告）。
- Paper Trading 分離
  - paper_trading モードは paper_trading 用の SQLite を使用し本番 DB と完全分離します。運用時に誤って本番 DB を使わないよう環境変数を確認してください。

---

今後の予定（例）
- research/factor_research の完全実装とテスト
- ExecutionEngine / SystemMonitor の詳細テスト、モニタリングアラート（LINE 連携等）
- 戦略設定 YAML のサンプル生成スクリプトと CI での validate_config 自動チェック

もし追加でリリースノートの粒度（もっと詳細な関数別の変更点や既知の問題一覧など）を望まれる場合はお知らせください。