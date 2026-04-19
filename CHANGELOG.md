# CHANGELOG

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。  
日付はリリース日 (YYYY-MM-DD) を示します。

## [0.1.0] - 2026-04-19

初回リリース — KabuSys の基本ユーティリティ群・実行/監視スクリプト・ポートフォリオ構築ロジック・開発用ツールを導入。

### 追加 (Added)
- 実行 / 監視エントリポイント
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するランナーを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御用フラグファイル (data/stop_requested.flag) と PID ファイル (data/execution.pid) を使用。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用するように設計。
    - DuckDB と SQLite の両方に接続して監視情報を初期化・利用。

- 設定管理 / .env 自動読み込み
  - src/kabusys/config.py
    - Settings クラスを導入し、環境変数を型安全に取得する API を提供。
    - プロジェクトルート (.git または pyproject.toml) を基準に .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path、各種監視閾値やファイルパスなどのプロパティを追加。
    - env 判定 (development/paper_trading/live) とログレベル検証を実装。

- 設定ユーティリティ / CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - シークレット入力はマスク表示。既存 .env の読み込み・Enter による再利用に対応。
    - .env 書き込み用フォーマットを提供。
  - src/kabusys/validate_config.py
    - 起動前に設定を検証する CLI を追加。
    - 必須/任意環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在確認（PyYAML が存在する場合はパース検証）を実行。
    - --strict オプションにより警告を FAIL 扱いにできる。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。

- ロギング / プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - setup_logging() を追加。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次, 保持30日）を設定。
    - LOG_DIR 指定・作成時のフォールバック、LOG_LEVEL 解決ロジックを実装。
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) を追加。Windows と POSIX の差分を吸収してプロセス優先度を設定（失敗時は警告）。
    - set_cpu_affinity(cpu_count) を追加。第一引数 N コアへピン留め可能（未対応 OS/権限不足時はスキップ）。

- ポートフォリオ構築ロジック（純粋関数群・DB 非依存）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定 select_candidates（スコア降順、signal_rank でタイブレーク）。
    - 重み計算 calc_equal_weights（等分配）、calc_score_weights（スコア比例、スコア全て 0 の場合は等分配にフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap：既存保有のセクターエクスポージャーに基づき、新規候補をフィルタ。unknown セクターは適用対象外。
    - calc_regime_multiplier：market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 でフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes：allocation_method（"risk_based" / "equal" / "score"）に対応した株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap のスケーリング、cost_buffer による保守的見積り、残差配分アルゴリズムを実装。

- 検証用ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - P95 計算、期間フィルタ (--from / --to / --db オプション) に対応。
    - デフォルトの閾値を設定（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）とし、PASS/FAIL 判定を出力。

- リサーチ基盤
  - src/kabusys/research/factor_research.py
    - ファクター計算の基盤実装を追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 接続を受け取り prices_daily 等のテーブルを参照して計算する設計。
    - モメンタム計算のための定数・calc_momentum の骨子を実装（データ不足ハンドリング含む）。

- パッケージメタ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### 変更 (Changed)
- 監視 / 実行の DB 接続ポリシーを明確化
  - 監視(run_monitoring) は環境にかかわらず本番 sqlite_path を使用する設計。
  - 実行(run_execution) は paper_trading 環境時に paper_sqlite_path を使用し DB を分離。

### 修正 (Fixed)
- 環境ファイル読み込みの堅牢化（config._parse_env_line / _load_env_file）
  - export 形式、クォート付き値（バックスラッシュエスケープ対応）、行内コメントの取り扱い、既存 OS 環境変数保護（protected set）などに対応。
  - .env 読み込み失敗時に警告を出すように変更。

### 注意事項 (Notes)
- 一部モジュールは外部パッケージ依存性により機能が制限される場合があります（例: PyYAML がない場合は config/*.yaml の内容検証をスキップ）。
- process_priority や set_cpu_affinity は権限やプラットフォームによっては動作しない（その場合は警告を出して安全にスキップ）。
- Paper Trading と本番 DB はデータ分離される設計ですが、運用時は環境変数（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等）を適切に確認してください。
- ロギング設定はデフォルトで logs/<app_name>.log に日次ローテーションで出力します。ファイル出力に失敗した場合はコンソールのみで継続します。
- research/factor_research.py はファクター計算の基盤を提供しますが、外部データやテーブル構成に応じた追加実装・テストが必要です。

今後の予定（例）
- factor_research の完全実装とユニットテスト追加
- ExecutionEngine / SystemMonitor 周りの統合テスト
- 銘柄ごとの lot_size マスタ対応、手数料/スリッページモデルの拡充
- モニタリング通知（LINE 等）とアラートの強化

---

この CHANGELOG はコードベースの内容から推測して作成しています。詳細な変更履歴や過去のコミット履歴がある場合は、適宜追記・修正してください。