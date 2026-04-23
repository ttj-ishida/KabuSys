CHANGELOG
=========

すべての変更は「Keep a Changelog」準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-23
--------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 実行/監視用エントリポイントスクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - BrokerClientFactory を介してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。data/stop_requested.flag による安全停止と data/execution.pid への PID 管理。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視 DB（monitoring）初期化（init_monitoring_db）と duckdb 接続。
    - 監視は環境に関わらず本番 sqlite_path を使用する（意図的に分離されている動作）。
- 設定関連 CLI/ユーティリティ
  - config_setup.py
    - .env の対話的作成・更新ウィザードを実装。既存 .env 読み込み、選択肢・デフォルト値・秘密値マスクに対応。
  - validate_config.py
    - .env と config/*.yaml の起動前検証ツールを実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実施。
    - --strict オプションで警告をエラー扱いにできる。
- 設定管理
  - config.py
    - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local をロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサは export プレフィックスやクォート、インラインコメント（スペース前の #）に対応。
    - Settings クラスを導入。各種設定プロパティを型付きで提供（パスは Path に展開、検証付き）。
    - Paper Trading 関連設定（paper_sqlite_path、paper_fill_mode 等）をサポート。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を提供。Console (stdout) と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決順を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 固定機能を実装。psutil の例外や権限不足は警告ログで扱う。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア正規化による重み計算（スコア合計が 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックと候補除外ロジック（"unknown" セクターは上限対象外）。
    - calc_regime_multiplier: レジーム (bull/neutral/bear) に応じた投下資金乗数の算出（未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく買付株数算出、単元株（lot_size）丸め、per-position 上限・aggregate cap によるスケールダウン処理、cost_buffer を考慮した保守的見積り、残差配分アルゴリズムを実装。
- リサーチ / ファクター計算（部分実装）
  - research/factor_research.py
    - モメンタム等ファクター計算モジュールを追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。計算定義・定数（1M/3M/6M、MA200、ATR 等）を含む（calc_momentum の実装開始）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し、定義済み閾値で PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ (--from/--to)、デフォルト DB パスの解決ロジックを実装。
- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし

Notes / 動作上の注意
- run_monitoring は「環境に関わらず本番 sqlite_path を使用する」設計になっているため、テスト目的で監視を分離したい場合は sqlite_path を明示的に環境変数で切り替えてください。
- config の自動 .env 読み込みはプロジェクトルート検出に依存するため、パッケージ配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境を管理することを検討してください。
- process_priority の設定はプラットフォーム依存・権限依存のため、失敗時は警告が出ますが起動継続します。
- paper_verification_report は DB スキーマに依存します。対象テーブルが存在しない場合は該当指標を N/A / 0 扱いで出力します。

Acknowledgements
- 初期実装に含まれる多くのコンポーネントは、実運用に向けた安全弁（stop flag、pid ファイル、ログローテーション、設定検証）を備えています。今後、テスト・監査を経て安定化を図ってください。