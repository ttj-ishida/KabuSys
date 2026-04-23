# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
予定されている将来変更は Unreleased に、リリース済みの変更はバージョン別に記載します。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-23
初回リリース — KabuSys の基本機能を実装しました。主な追加点と動作上の注意を以下にまとめます。

### Added
- パッケージ構成
  - kabusys パッケージを追加。サブパッケージ例: execution, monitoring, portfolio, research, utils, tools。
  - バージョン情報を `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` と設定。

- 実行 / 監視ランナー
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - Paper Trading（KABUSYS_ENV=paper_trading）では専用の SQLite（data/paper_trading.db デフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て、Engine のスレッド実行と停止フラグ（data/stop_requested.flag）対応。
    - 実行中は PID ファイル（data/execution.pid）を利用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視用 DB は環境に関わらず本番 `sqlite_path` を参照する実装。

- 設定関連
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）を実装。優先順位は OS 環境変数 > .env.local > .env。
    - `.env` の行を安全にパースするユーティリティ（export 形式、クォート・エスケープ、インラインコメント対応）。
    - Settings クラスを追加し、各種環境変数に対するプロパティとバリデーションを提供（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動読み込みを無効化可能（テスト用途など）。

  - config_setup.py
    - 対話式ウィザードで .env を作成／更新する CLI を追加。シークレットのマスク表示、選択肢・デフォルト値のサポート、.env 書き込みロジックを提供。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在とパース（PyYAML がある場合）を実施。
    - `--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap、レジームに応じた乗数 calc_regime_multiplier を実装（未知レジームはフォールバックと警告）。
  - portfolio/position_sizing.py
    - 発注株数算出ロジック calc_position_sizes を実装。allocation_method に `"risk_based"`, `"equal"`, `"score"` をサポート。lot_size（単元株）丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積もりを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - psutil を用いてクロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティを追加。また CPU affinity を最初の N コアに固定する関数も提供。権限不足や未対応 OS の場合は警告を出力してスキップする。

- 監視 / モニタリング DB 初期化
  - monitoring/monitoring_db.py （参照されている初期化関数を run_* スクリプトから呼び出し、監視テーブルの存在を保証する実装が組み込まれていることが想定される）

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出し、閾値（稼働率 99%、成功率 90% など）に基づき PASS/FAIL 判定を行う。CLI 引数で集計期間 (--from / --to) と DB パス (--db) を指定可能。
    - DB の存在チェック、テーブル未存在時のフォールバック処理を実装。

- 研究用ファクター計算（着手）
  - research/factor_research.py
    - Momentum（1M/3M/6M 等）、MA200乖離、ATR、ボリューム関連などを計算するための骨子と定数を追加。DuckDB 接続を受け prices_daily / raw_financials を参照する設計。モメンタム計算の関数化を開始（実装途中の箇所あり）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env の生成スクリプトで明示的に「.env を絶対に Git にコミットしないこと」を注意喚起。
- 設定検証で J-Quants / kabu API の必須トークンが未設定の場合はエラーとするため、秘密情報の未設定による誤動作を抑止。

### Notes / Known limitations
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化してコンソール出力のみで継続します（起動環境の書き込み権限に依存）。
- process_priority は psutil と OS 権限に依存します。権限不足の場合は警告を出力してスキップします。
- .env 自動ロードはプロジェクトルートを .git または pyproject.toml により検出します。配布後の環境でプロジェクトルートが特定できない場合は自動ロードをスキップします。
- research/factor_research.py はモメンタム計算部分の実装が途中で切れているファイルが含まれており、完全な計算フローは今後の実装作業が必要です。
- monitoring は常に本番用の sqlite_path を参照して監視データを記録するため、テストやペーパートレード環境では設定に注意してください（Execution 側は paper_trading で専用 DB を使用）。

---

開発・リリースに関する問い合わせや修正の要望があれば教えてください。必要に応じて Unreleased セクションに変更を追加して以降のリリースノート案を作成します。