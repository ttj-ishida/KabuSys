# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

最新の変更は上に記載します。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 基本アーキテクチャ・ランタイムスクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。  
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。  
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）で安全に停止可能。PID ファイルを書き込む仕組みあり。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番用の sqlite_path を使用する旨の明示。停止フラグでループを終了。DB 初期化（init_monitoring_db）と DuckDB 接続を行う。

- 設定管理と初期化ツール
  - config.py: 環境変数・設定管理モジュール。  
    - .env の自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。  
    - 複雑な .env パースロジック（export 形式、クォート、エスケープ、インラインコメント取り扱いなど）を実装。  
    - Settings クラスでアプリ設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID/KILL フラグ関連、閾値設定、環境種別検証など）。  
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の許容値チェック、paper_sqlite_path の提供等。

  - config_setup.py: 対話式 .env ウィザード。  
    - 初期 .env の作成・更新を支援（複数の項目定義、シークレットのマスク表示、既存値の再利用、保存前の確認など）。  
    - .env を書き出す際のテンプレートと注意書き（.env をコミットしない旨）を含む。

  - validate_config.py: 設定検証 CLI。  
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）など。  
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 一元的なロギング設定ユーティリティ。  
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。ローテーションは 30 日分保持。
  - utils/process_priority.py: プロセス優先度 / CPU affinity のユーティリティ。  
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収し、`set_process_priority("high"|"normal"|"low")` で優先度を設定。アクセス権や未対応環境では警告を出してスキップ。`set_cpu_affinity` で先頭 N コアに固定する機能あり。

- ポートフォリオ構築機能（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定・重み計算
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア正規化配分（全スコア 0 の場合は等配分にフォールバック）
  - portfolio/risk_adjustment.py: セクター上限の適用・レジーム乗数
    - apply_sector_cap: 既存保有に基づくセクター集中上限（max_sector_pct）を超えるセクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金の乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告を出す。
  - portfolio/position_sizing.py: 発注株数算出（risk_based / equal / score）
    - 単元株（lot_size）丸め、1銘柄上限や aggregate cap（利用可能現金に合わせたスケールダウン）、コストバッファの考慮、スケーリング後の端数処理（lot_size 単位で再配分）など、実務を考慮したアルゴリズムを実装。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成する CLI。  
    - 稼働率、注文成功率（fill_rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを算出し、閾値（稼働率 99% 等）で PASS/FAIL 判定を行う。P95 計算や日付フィルタ機能、DB 存在チェック、コマンドラインオプション --from/--to/--db をサポート。

- 研究用ファクター計算モジュール（骨格）
  - research/factor_research.py: DuckDB の prices_daily / raw_financials を用いたモメンタム / Value / Volatility / Liquidity 系ファクター算出モジュールの骨格を追加（詳細実装は継続）。モメンタム等の定数や計算方針の定義が含まれる。

- パッケージメタデータ
  - __init__.py にバージョン定義 __version__ = "0.1.0" を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- 機密情報（トークン・パスワード）は .env に格納し、config_setup のテンプレート・ README に「.env を Git にコミットしない」旨を明記（潜在的なベストプラクティスの提示）。

### Notes / 注意点
- run_monitoring は「監視用途の DB」として Settings.sqlite_path を環境にかかわらず使用する設計になっている点に注意してください（監視データは本番側のパスを参照する挙動）。
- .env 自動読み込みはデフォルトで有効だが、テスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで無効化できます。
- process_priority / cpu_affinity の設定は権限不足やプラットフォーム差分で失敗しうるため、失敗時は警告ログを出して安全にスキップします。
- research/factor_research.py はモジュールの骨格と計算方針を含みますが、一部実装（ファンクションの終端等）が未完の箇所があります。実行前に実装・テストが必要です。

もし CHANGELOG の記載粒度（例えばファイル単位での詳細な追加/修正一覧や、エンドユーザー向けの簡潔な要約）を変更したい場合は指示してください。