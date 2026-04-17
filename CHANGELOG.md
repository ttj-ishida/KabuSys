# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム KabuSys のコアユーティリティ群、CLI、ポートフォリオ構築ロジック、モニタリング・実行エントリポイント、およびいくつかの補助ツールを追加しました。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- エントリポイント / 実行関連
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV による paper_trading モードをサポート。paper_trading 時は MockBrokerClient を使用し、Paper Trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - 停止フラグ（data/stop_requested.flag）を監視して安全にエンジンを停止。
    - エンジン実行はデーモンスレッドで行い、PID ファイル（data/execution.pid デフォルト）への出力をサポート。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization 等）を組み込み。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（監視データの一元管理）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。

- 設定管理 / CLI
  - config.py
    - .env の自動読込機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
    - .env 読み込みの優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 各種設定プロパティを提供: J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム環境判定（is_live / is_paper / is_dev）。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject" のみ許容）。
    - PATH 系（duckdb/sqlite/paper_sqlite/pid 等）は Path 型で取得。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - J-Quants トークンや kabu API パスワードなどの必須項目を対話でセット可能。既存 .env の読み込み・再利用に対応。
    - 保存前に確認を促す。保存時は .env テンプレートヘッダを付与して書き出す。

  - validate_config.py
    - 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在チェックおよび PyYAML があればパース検証、KABUSYS_ENV=live 時の追加警告（LINE 通知等）。
    - --strict オプションで警告を FAIL 扱いにできる。

- モニタリング / ツール
  - monitoring 側の DB 初期化呼び出し init_monitoring_db を各エントリポイントで呼ぶ（冪等）。
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成ツールを追加。
    - システム稼働率、注文成功率（Fill率）、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を行う。
    - デフォルトの合格基準を定義（稼働率 >=99%、Fill >=90%、Send >=95%、P95 <=200ms）。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）をサポート。

- ポートフォリオ構築（純関数モジュール）
  - portfolio/portfolio_builder.py
    - select_candidates：BUY シグナルをスコア降順で上位 N を選択（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights：等金額配分。
    - calc_score_weights：スコア重み付け（全銘柄スコアが 0 の場合は等金額にフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap：セクター集中制限（max_sector_pct）に基づき候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数（未知レジームは警告の上 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes：allocation_method ("risk_based", "equal", "score") に基づき発注株数を計算。
    - 単元株丸め（lot_size、デフォルト 100）、1銘柄上限・aggregate cap（available_cash）へのスケーリング、cost_buffer による保守的見積り、端数配分ロジックを実装。
    - price 欠損や price<=0 の銘柄はスキップし、ログにデバッグ情報を出力。

- リサーチ（DuckDB ベース）
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum / Volatility（ATR 等）等のファクターを計算する関数を追加。
    - calc_momentum：1M/3M/6M リターン、MA200 乖離を計算。データ不足時は None を返す。
    - calc_volatility：ATR20、相対 ATR、20日平均売買代金、出来高比率等を計算。ウィンドウ不足時は None を返す。
    - 全て SQL（DuckDB）ベースで prices_daily 等のテーブルを参照し、結果は dict のリストで返却。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（nice / Windows priority class）設定ユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low")：Windows / POSIX を吸収して設定。AccessDenied 等は警告でスキップ。
    - set_cpu_affinity(cpu_count: int | None)：プロセスの CPU affinity を最初の N コアに固定する。実行環境を問わず安全に扱う。

### Changed
- .env 読み込みの挙動
  - auto-load の優先順位を明確化（OS 環境変数を保護しつつ .env の上書き制御を実装）。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line にてシングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、export KEY=val 形式への対応を追加。これにより .env 内の複雑な値が正しく読み込まれるようになった。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - 0 以下や非整数の値が設定された場合は警告を出してデフォルト（60 秒）にフォールバックするよう修正。

### Notes / Known issues
- 一部機能は外部モジュール（psutil や PyYAML）に依存する。これらが利用できない場合は該当チェックや設定操作は警告を出してスキップされる。
- position_sizing の価格欠損時の挙動（price が 0.0 の場合にエクスポージャーが過少見積りとなる可能性）については TODO コメントを残しており、将来的にフォールバック価格の導入を検討。
- run_execution / run_monitoring はそれぞれ SQLite / DuckDB への接続を行うため、実運用では適切な DB ファイルパスと権限を事前に確認してください。

-- 
この CHANGELOG はコードベースから推測して作成した要約です。実際のリリースノート作成時は差分に基づく確認を推奨します。