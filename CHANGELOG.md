# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記録しています。  
このファイルはコードベースから推測して生成しています（自動生成ではなく手動での要約）。


## [0.1.0] - 2026-04-17

### Added
- 初回リリース。以下の主要機能・モジュールを追加。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルートの data/stop_requested.flag を検知して行う。
    - 監視機能は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは本番 DB を参照）。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用の SQLite（デフォルト data/paper_trading.db）に完全分離して記録。
    - 実行中は execution.pid を PID ファイルとして扱い、同じく data/stop_requested.flag により停止可能。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数からアプリ設定を提供。
    - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は既存 OS 環境変数を保護して上書き可）。
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / PID パス / 監視閾値 / PAPER_FILL_MODE の検証など）。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - シークレット項目は表示時にマスクし、既存値の読み込み・デフォルトの提示・入力検証を実施。
    - 出力される .env テンプレートは Git にコミットしない旨の注意を含む。
  - validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML 使用可の場合）などを実施。
    - --strict オプションで警告も FAIL 扱いにできる。
    - 本番（KABUSYS_ENV=live）時向けの追加ガード（LINE 設定や Kill Switch 関連の警告）を実装。
- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows / POSIX の違いを吸収）。
    - set_process_priority(level) で high/normal/low を指定可能。権限不足時は警告でスキップ。
    - set_cpu_affinity(cpu_count) によりプロセスの CPU affinity を設定する関数を追加。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 select_candidates（スコア降順、タイブレーク処理）を追加。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights を追加（スコア全てが 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を追加（既存ポジションを考慮して新規候補を除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を追加（bull/neutral/bear のマッピング、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数算出 calc_position_sizes を追加。
    - allocation_method に risk_based / equal / score をサポート。
    - lot_size（単元株）対応、max_position_pct / max_utilization / cost_buffer（手数料・スリッページ想定）考慮、aggregate cap のスケーリング（端数処理で残差配分ロジックあり）。
- 研究（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を受けてモメンタム・ボラティリティ等のファクターを計算する関数を実装（calc_momentum, calc_volatility 等）。
    - prices_daily / raw_financials テーブルのみ参照する設計。
    - 実装では、移動平均 (MA200)、各種モメンタム（1M/3M/6M）、ATR、出来高指標などを計算。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）などを算出し PASS/FAIL 判定を出力。
    - 期間フィルタ（--from / --to）、DB 指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - P95 の計算、無データ時の N/A ハンドリング、閾値（例: 稼働率 >= 99% など）を設定して判定。
- パッケージ初期化
  - __init__.py にバージョン __version__ = "0.1.0" を設定し、公開 API を定義。

### Changed
- （初回リリースのため該当なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （該当なし）

Notes / 実装上の補足（コードからの推測）
- .env パーサはクォート文字（' "）とバックスラッシュエスケープ、行末コメントの扱いに対応しており、実運用での柔軟な .env 設定を想定している。
- 設定値（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）は妥当性検証を行い、不正値では例外や警告を出す実装。
- 監視・実行プロセスはいずれも起動直後にプロセス優先度を上げる設計（set_process_priority("high")）、ただし権限不足ではフォールバックする。
- paper_trading 用 DB と本番監視 DB は明確に分離されるよう設計（監視のみ本番 DB を参照する点は意図的）。
- portfolio / position sizing 周りは "純関数" として副作用がなく、テストや再利用を想定した設計になっている。

もし追加でリリース日や変更履歴の細分化（例: minor/patch の分割、個々のコミットに基づく詳細化）をご希望であれば、コミットログや実際の変更差分を提供してください。こちらでより正確な CHANGELOG を作成します。