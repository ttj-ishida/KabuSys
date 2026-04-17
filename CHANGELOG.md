CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠しています。

新しいプロジェクトの初回リリースとして、コードベースから推測される機能・振る舞いをまとめています。

リリースノート
-------------

### [0.1.0] - 2026-04-17

Added
- 全体
  - 初期リリース。日本株自動売買システム "KabuSys" のコアユーティリティ、実行・監視ランナー、ポートフォリオ構築、リスク調整、ポジションサイジング、リサーチ用ファクター計算などを追加。

- コマンドライン / 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB に記録）。
    - stop_requested.flag を検知してループを終了。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動ロジックを実装。
    - 実行中は data/execution.pid を使用して PID を管理し、stop_requested.flag により安全に停止可能。
    - リスク管理のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。

- 設定・ユーティリティ
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env, .env.local の読み込み順を実装（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 複雑な .env 行パースを実装（export プレフィックス、引用符、エスケープ、インラインコメント処理等）。
    - Settings クラスを通じた環境変数アクセスとバリデーションを提供（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。
  - config_setup.py
    - インタラクティブな .env 作成・更新ウィザードを追加。
    - 秘匿値はマスク表示、選択肢・デフォルト対応、保存前の確認プロンプトを実装。
    - .env のテンプレート出力（.env 書式）を提供。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、プレースホルダ値の警告、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの存在チェック（親ディレクトリ）、config/*.yaml の存在および PyYAML によるパース検証（PyYAML 未インストール時はスキップ）を実装。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。
  - utils/process_priority.py
    - プロセス優先度設定（Windows/Linux/macOS に対応するラッパー）と CPU affinity 設定関数を追加。
    - 権限不足や未対応 OS の場合は安全に警告を出してスキップするフェイルセーフを実装。

- ポートフォリオ構築・リスク・ポジション
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）を実装。既存ポジションのセクター時価を評価し、上限超過セクターの新規候補を除外。
    - 市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 複数の配分方式（risk_based, equal, score）に対応した株数計算ロジックを実装。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリングと残差調整ロジックを実装。
    - cost_buffer による保守的コスト見積りをサポート。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を用いたファクター計算モジュールを追加。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）およびボラティリティ／流動性（ATR20、avg_turnover、volume_ratio 等）を SQL で計算する関数を提供。
    - データ不足時の None ハンドリング、計算範囲に余裕を持たせる設計（スキャン日数バッファ）を実装。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（default: data/paper_trading.db）から運用検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計し、事前定義の閾値に基づく PASS/FAIL を出力。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

Changed
- 初回公開のため、過去互換性の変更は無し（初期導入）。

Fixed
- N/A（初回リリース）。

Notes / 備考
- 監視（run_monitoring）は明示的に本番 sqlite_path を使用する設計です。開発時の意図しない監視データ混入を避けるための設計判断と思われます。ペーパートレードは run_execution 側で専用 DB に分離されています。
- process_priority や CPU affinity の設定は権限やプラットフォームに依存するため、失敗した際は警告ログを出して処理を継続します。
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後は CWD に依存せずに動作する設計です。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- ExecutionEngine / SystemMonitor 等の具体的な実装（monitoring.monitoring_db, monitoring.system_monitor, execution.execution_engine 等）は本差分から参照されていますが当該ファイルの詳細実装は本リリース範囲外です（別ファイルで提供される想定）。

コミュニケーション
- 実行例:
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

今後の改善候補（観察に基づく推奨）
- apply_sector_cap の price 欠損時のフォールバック価格（前日終値や取得原価など）の導入。
- position_sizing の lot_size を銘柄別に持たせる（マスタ参照）。
- monitoring の DB 切り替えやテスト用フラグを明確化（監視データの分離オプション）。
- factor_research の計算における欠損データ処理の強化とユニットテスト追加。

以上。