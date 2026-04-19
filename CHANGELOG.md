# CHANGELOG

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-19

### Added
- 初回リリース。
- 実行エントリ / デーモン風スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（実運用 / モックの切替を想定）。
    - エンジンの PID ファイル管理、stop_requested.flag による安全な停止検出。
    - プロセス優先度を高（"high"）に設定してから実行。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバックし、警告出力。
    - 監視用 DB（sqlite）は環境にかかわらず本番 sqlite_path を使用。
    - stop_requested.flag によりループ終了。
    - プロセス優先度を高（"high"）に設定してから実行。

- 設定管理
  - config.py
    - Settings クラスで環境変数をラップし、各種設定をプロパティで提供（J-Quants、kabuAPI、DB パス、監視閾値、環境判定等）。
    - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を探索）。OS 環境変数は保護（上書き防止）。
    - .env の行パースで export プレフィックス・クォート・インラインコメント・エスケープをサポート。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の入力値検証（有効値チェック）。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加（各項目の説明・デフォルト・シークレット入力をサポート）。
    - .env 出力テンプレートを定義。

- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の起動前検証ツールを追加。
    - 必須環境変数の未設定チェック、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がなければ警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR が作成できない場合はファイル出力をスキップして stdout のみで継続。
    - ログレベル解決順、ログディレクトリ解決順の仕様を文書化。
  - utils/process_priority.py
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度 / CPU affinity を設定。psutil を利用し、権限不足や未対応 OS は警告を出して安全にスキップする。
    - 無効な引数に対する ValueError の送出やアクセス権限エラー時の警告処理を実装。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額にフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）を実装。sell_codes を除外して既存保有のセクターエクスポージャを算出し、上限超過セクターの候補除外を行う。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score の allocation_method）を実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下資金合計の aggregate cap、手数料・スリッページ見積もり用 cost_buffer による保守的見積り、スケールダウン時の残差配分ロジックを実装。
    - 価格欠損時のスキップ、0 価格チェック、ログ出力でのデバッグ情報を実装。

- 運用ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計し、閾値に基づいて PASS/FAIL を判定。
    - コマンドライン引数 --from / --to / --db をサポート、PAPER_TRADING_SQLITE_PATH 環境変数の利用を想定。
    - デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms。

- 研究用モジュール（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算するための骨組みを追加（価格テーブル参照前提）。モメンタム計算等の実装を開始（処理設計・定数定義を含む）。

- パッケージ情報
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- 初回公開のため該当なし。

### Fixed
- 初回公開のため該当なし。

### Security
- 初回公開のため該当なし。

### Notes / 備考
- .env 自動読み込みはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等で使用）。
- config.py の Settings は実行時に未設定の必須環境変数があると ValueError を送出します。validate_config.py で事前に検査することを推奨します。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化します。運用環境では適切な権限とディスクパスの確保を推奨します。