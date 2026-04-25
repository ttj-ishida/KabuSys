# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、Semantic Versioning を採用します。

全般:
- 初回公開リリース: バージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0。

---

## [0.1.0] - 2026-04-25

### Added
- 基本アーキテクチャとコアユーティリティを追加
  - パッケージのバージョン情報を設定 (kabusys.__version__ = 0.1.0)。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）で本番 DB と分離して動作。
    - 起動時にプロセス優先度を "high" に設定する仕組みを実装。
    - 停止制御: プロジェクトルートの data/stop_requested.flag を検出するとエンジンを停止。
    - 実行時の PID を data/execution.pid に記録する（pid_file 経路は設定から取得）。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて実行。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視データは環境にかかわらず本番 sqlite_path を使用して接続（monitoring 用 DB 初期化を実施）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - 例外発生時はログに例外を残して次のポーリングを継続（堅牢化）。

- 設定関連
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env/.env.local の読み込み優先度、既存 OS 環境変数の保護（protected）を考慮。
    - .env 行パーサは export プレフィックス、引用符、エスケープ、インラインコメントを正しく処理。
    - Settings クラスを提供し、環境変数読み出しをプロパティ経由で型付けして扱えるようにした（DB パス、PID ファイルパス、閾値、paper_trading 関連設定等）。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の値検証を実装。

  - config_setup.py
    - 対話式ウィザードで .env の初期生成・更新を行う CLI を追加。
    - デフォルト値、選択肢、シークレット入力（マスク表示）に対応し、.env を安全に書き出す。

  - validate_config.py
    - 起動前に必須環境変数や config/*.yaml の整合性を検証する CLI を追加。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML が無い場合は YAML 検証をスキップして警告を出す。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler(stdout) と TimedRotatingFileHandler（日次、30世代保持）を設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決ルールを実装。ログディレクトリ作成失敗時はファイルハンドラをスキップして標準出力のみで継続。
    - ストリームは stdout を使用（cron/Task Scheduler 等での取り扱いを考慮）。

  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定（Windows / POSIX の差分吸収）を追加。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity() を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築・ポジションサイジング
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等金額へフォールバック。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 同一セクターの既存保有比率が上限を超える場合に新規候補を除外するロジック（sell_codes により当日売却銘柄を除外可能）。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックして警告。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に従った株数決定を実装。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的なコスト見積り、残差を用いた追加配分ロジックを実装。
    - price 欠損や price <= 0 の場合は該当銘柄をスキップする防御的実装。

- 研究・ツール
  - research/factor_research.py
    - DuckDB の prices_daily/raw_financials テーブルを用いたファクター計算基盤を追加（Momentum, Value, Volatility, Liquidity を想定）。DuckDB 接続を受ける設計。
    - モメンタム計算関数 calc_momentum の骨格を実装（注: ファイル末尾で実装が途中の箇所あり。下記 Known issues を参照）。

  - tools/paper_verification_report.py
    - ペーパートレード DB を解析して稼働率・注文成功率・送信率・API レイテンシ（P95 等）を集計するレポートツールを追加。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を設定し、PASS/FAIL 判定を出力。

- パッケージエクスポート
  - portfolio モジュールの主要関数を top-level でエクスポート（select_candidates 等）。

### Changed
- 初版のため、既存コードとの互換性変更はなし（新規追加）。

### Fixed
- 初版のため、既存バグ修正はなし。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

## 既知の問題 (Known issues)
- research/factor_research.py の calc_momentum 実装がファイル末尾で途中になっている（truncated）。完全な計算ロジックはまだ未実装の箇所があります。ファクター計算を利用する前に該当関数の完成が必要です。
- apply_sector_cap 内の価格欠損処理について注意書きあり: price が 0.0 の場合、エクスポージャーが過少見積りされブロックが外れる可能性がある（将来的にフォールバック価格の導入を検討）。
- process_priority / set_cpu_affinity は権限不足や OS によっては実行できない場合がある（警告を出してスキップする実装）。

---

## マイグレーション・運用メモ
- 環境変数自動ロード
  - デフォルトではプロジェクトルートの .env と .env.local が自動読み込みされます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env の扱いには注意: .env は Git にコミットしないでください（config_setup.py のヘッダにも注意書きを追加）。

- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_sqlite_path（デフォルト: data/paper_trading.db）に接続します。本番用 monitoring.db とデータが混ざらないように注意してください。

- ログ
  - デフォルトのログ出力先は logs/<app_name>.log。LOG_DIR 環境変数や setup_logging の引数で上書き可能。ログディレクトリ作成に失敗した場合はコンソールのみで出力します。

- 停止/キル
  - run_* スクリプトはプロジェクトルートの data/stop_requested.flag を監視して起動中処理の停止を受け付けます。Kill Switch の自動クリアは KILL_FLAG_CLEAR_ON_START 環境変数で制御。

---

もし追加でリリース日やより詳細な部分（例: 各モジュールの public API サンプル、未実装箇所のチケット化など）を反映した CHANGELOG を望まれる場合は、対象箇所や優先度を指定して教えてください。