# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づいています。

## [0.1.0] - 2026-04-21

### 追加
- 基本アプリケーション構成
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで実行され、 data/stop_requested.flag により安全に停止可能（デフォルトの PID ファイル path: data/execution.pid）。
    - RiskConfig のデフォルト値を設定し、RiskManager に初期資金を broker.get_available_cash() で渡す。
  - run_monitoring: SystemMonitor ポーリングループ起動用スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を監視し、検知時にループを終了。
    - 監視用 DB 初期化と DuckDB 接続を行い、SystemMonitor.check_once() を定期実行。
    - 監視コンポーネントは KABUSYS_ENV に関わらず production の sqlite_path を使用する挙動（意図的なデザイン）。
- 設定管理・読み込み
  - .env 自動読み込み機構を実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml）。
    - .env を読み込み、.env.local で上書き（OS 環境変数は保護）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
    - .env パーサーは export KEY=val 形式、引用符付き値、バックスラッシュエスケープ、インラインコメントなどに対応。
  - Settings クラスを追加（src/kabusys/config.py）:
    - J-Quants / kabuAPI / LINE / DB パス / Paper Trading の挙動 / 監視・しきい値 / 環境（development/paper_trading/live）/ログレベル等のプロパティを提供。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH のプロパティ、各種閾値のデフォルト等を実装。
- 設定検証 CLI
  - validate_config CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML 未インストール時はスキップ）を実施。
    - KABUSYS_ENV=live 時の追加ガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
- 設定ウィザード CLI
  - config_setup インタラクティブウィザードを追加（src/kabusys/config_setup.py）。
    - 対話式に .env を作成/更新。シークレット項目はマスク表示、選択肢やデフォルト値をサポート。
    - 生成される .env のテンプレートと書き込みロジックを提供。保存前に確認プロンプトあり。
- ロギング・プロセス制御ユーティリティ
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ファイル出力用ディレクトリ作成に失敗した場合はコンソール出力のみでフォールバック。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収して set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - psutil 不可や権限不足の場合は警告ログを出してフォールバック（スキップ）する。
- ポートフォリオ構築関係（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights を実装。score が全て 0 の場合は等金額にフォールバック。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中制限ロジックを実装（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは警告の上 1.0 にフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes を実装。allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）での丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer（手数料・スリッページ見積）を考慮した安全な配分ロジックを実装。
    - スケーリング後に残余キャッシュで fractional 残差が大きい順に lot_size 単位で再配分するアルゴリズムを実装。
- Paper Trading 検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）を追加。
    - Paper Trading DB（PAPER_TRADING_SQLITE_PATH / --db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など）を集計してレポートを出力。
    - PASS/FAIL の閾値を定義（稼働率 99% など）し、詳細な出力フォーマットを提供。
    - P95 計算、期間フィルタリング、テーブル存在なしの耐性（OperationalError を捕捉）を備える。
- research/factor_research
  - ファクター計算モジュールの骨組みを追加（src/kabusys/research/factor_research.py）。
    - momentum, volatility, value, liquidity 等の設計方針と定数を定義。DuckDB 接続を受け取る方式を採用。
    - calc_momentum の実装を開始（ファイル末尾で未完部分あり）。

### 変更
- なし（初期リリース）

### 既知の問題 / 注意事項
- 監視用スクリプト（run_monitoring）は KABUSYS_ENV に関わらず Settings.sqlite_path（本番用 sqlite_path）を使用する挙動になっています。開発環境で別 DB を使いたい場合は設定の上書きやコード調整が必要です。
- position_sizing / apply_sector_cap における価格欠損の扱い:
  - risk_adjustment.apply_sector_cap は price_map で価格が得られない場合に 0.0 を使い、過少評価につながる可能性をコード内で指摘（TODO）。前日終値等のフォールバック実装は未実装。
- position_sizing の lot_size は現状全銘柄共通のまま。将来的に銘柄別 lot_size を持たせる拡張が予定されている（TODO コメントあり）。
- research/factor_research.calc_momentum は実装途上でファイル末尾が未完（start_da... で途切れ）。本格運用前に残りの実装とテストが必要。
- .env 読み込みは自動で行われる（.env → .env.local の順）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップして stdout のみで継続します。ログの永続化が必要な環境では LOG_DIR の書き込み権限を確認してください。

### セキュリティ
- なし

### 開発メモ / 次期改善案
- broker / engine 周りの統合テスト（paper_trading と live の振る舞いを含む）を拡充すること。
- factor_research の完全実装（ファクター計算の SQL / 正規化）と単体テスト追加。
- .env パーサーの更なる堅牢化（稀なエッジケースの追加テスト）。
- position_sizing の銘柄別 lot_size サポート、価格フォールバック実装（前日終値や取得原価の利用）。

----------------------------------------------------------------------------
(初回リリース)