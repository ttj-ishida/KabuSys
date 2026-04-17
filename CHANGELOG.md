# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
タグ付けとリリース日付はソースコードの内容から推測したものです。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回公開

### Added
- 基本アプリケーション情報
  - パッケージバージョンを src/kabusys/__init__.py にて `0.1.0` として追加。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御用にプロジェクト配下の data/stop_requested.flag を監視。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する挙動を明示。
    - プロセス優先度を起動時に "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、paper_trading 専用 DB に記録して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）・PID 管理（data/execution.pid）をサポート。
    - スレッドで ExecutionEngine を実行し、停止フラグを検出したら安全に停止する制御。

- 設定管理・ウィザード・検証
  - config.py: 環境変数 / .env の読み込み・管理を実装。
    - プロジェクトルートを .git / pyproject.toml から自動検出し、その場所の .env/.env.local を自動ロード（無効化フラグあり: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env パーサは引用符・エスケープ・インラインコメントなどに堅牢に対応。
    - Settings クラスに各種設定プロパティを提供（DB パス、API トークン、監視閾値、環境判定など）。`PAPER_FILL_MODE` の有効値検査を含む。
  - config_setup.py: 対話式の .env 生成・更新ウィザードを追加。
    - 項目定義、既存 .env 読み取り、シークレットマスク、保存処理をサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パス親ディレクトリ存在チェック、config/*.yaml の存在チェックと（PyYAML 有りの場合の）パース検証、KABUSYS_ENV=live に対する追加警告を実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: シグナルのスコアでソートして上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア重み配分（全スコアが 0 の場合はフォールバックで等金額）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの集中を抑制するフィルタ（売却予定銘柄を除外可能）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算、単元株（lot_size）丸め、個別上限・aggregate cap、コストバッファ考慮、スケーリングと端数再配分ロジックを実装。

- 監視・実行関連ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定するユーティリティ（"high"|"normal"|"low"）。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアにピンニングする補助関数。
    - 権限不足や非対応プラットフォーム時には警告を出して安全にスキップする実装。

- 研究用ファクター計算
  - research/factor_research.py
    - DuckDB 接続を用いたファクター計算モジュールを追加（Momentum, Volatility 等）。
    - calc_momentum, calc_volatility 等の関数があり、prices_daily テーブルを参照して各種指標（mom_1m/3m/6m、MA200 乖離、ATR20、平均売買代金など）を算出。データ不足時の None ハンドリングを実施。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、しきい値（稼働率 >=99% 等）に基づく PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db、引数で期間・DB パスを指定可能。

- DB / ランタイム統合
  - run_* スクリプトや各コンポーネントで SQLite / DuckDB 接続を利用する実装を追加。monitoring DB 初期化用 init_monitoring_db 呼び出しは冪等で安全に実行される。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 機密値（例: API トークン、パスワード）は .env に保管する前提の扱いをドキュメント化（config_setup のヘッダに「.env を絶対に Git にコミットしないこと」と明記）。

---

注:
- 各モジュールの詳細実装はソース内の docstring / コメントに従います。  
- 本 CHANGELOG は提供されたコードベースから推測して作成しており、実際のリリース履歴やコミット履歴と差異がある可能性があります。