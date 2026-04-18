# Changelog

すべての重要な変更を記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-18

### 追加
- 全体
  - 初期パブリックリリース。パッケージバージョンを `0.1.0` に設定。
  - パッケージ公開用の基本モジュール構成を追加（data / strategy / execution / monitoring などをエクスポート）。

- 実行系 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じた DB 分離:
      - `paper_trading` 環境では専用のペーパートレード DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient による仮想トレードを行う想定。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
    - 停止制御: data/stop_requested.flag を検出して安全に停止する仕組みを実装。
    - 実行時の PID 管理ファイルを使用（data/execution.pid）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）を検出してループを終了。

- 設定管理 / CLI
  - config.py: 環境変数 / .env 読み込みと Settings クラスを実装。
    - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で抑止可能）。
    - .env パーサの強化: `export KEY=val` 形式対応、シングル/ダブルクォート中のエスケープ処理、インラインコメント取り扱い等。
    - 各種プロパティを提供（J-Quants、kabuステーション、LINE、DuckDB/SQLite パス、ペーパートレード設定、監視閾値、環境判定等）。
    - `PAPER_FILL_MODE` の検証（有効値: "instant" / "partial" / "never" / "reject"）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の入力検証（許容値チェック）。
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。
    - シークレット入力の扱い、選択肢表示、既存値読み込み、最終確認後に .env を書き出し。
    - 書き込まれる .env は Git にコミットしない旨の注記を出力。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がある場合は）パース検証、本番環境向け追加ガードなど。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選別（同スコア時は signal_rank でブレーク）。
    - calc_equal_weights、calc_score_weights: 等配分・スコア加重配分を実装（スコア合計が 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのエクスポージャ計算、上限超過セクターの候補除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。
      - lot_size（単元）丸め、1 銘柄上限・aggregate cap（available_cash）超過時のスケーリング、cost_buffer（手数料・スリッページ見積）を考慮した保守的な計算ロジックを実装。
      - current_positions の差分計算で買い増し量を決定。

- ユーティリティ
  - utils/logging_setup.py:
    - 全起動スクリプトから共通で使えるロギング初期化関数 `setup_logging` を実装。
    - stdout（StreamHandler）と日次ローテートされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py:
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - Windows と POSIX（Linux/Darwin/FreeBSD）差分を吸収。権限不足や未対応 OS は警告してフォールバック。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 DB から各種指標（稼働率・注文成功率・送信率・リスク却下数・レイテンシ統計）を集計してレポートを出力するスクリプトを追加。
    - デフォルトの閾値を定義し、PASS/FAIL 判定を行う（期間指定オプションあり）。

- リサーチ
  - research/factor_research.py:
    - ファクター計算モジュールの骨格を追加（Momentum、Value、Volatility、Liquidity を想定）。DuckDB を利用して prices_daily / raw_financials を参照する設計。
    - モメンタム計算のための定数と calc_momentum の導入（日数設定や関数仕様は追加実装に向けて整備）。

### 変更
- logging の挙動
  - StreamHandler は stderr ではなく stdout を使用するようにした（cron / Task Scheduler 等で stdout/stderr を一本化して扱いやすくするため）。

### 修正
- .env 読み込みの堅牢化
  - .env の読み込み失敗時に警告を出しつつ処理継続するよう改善（読み込みエラーは警告で済ます）。

### 注意事項 / 既知の制約
- run_monitoring は「監視用 DB パスとして settings.sqlite_path（デフォルト: data/monitoring.db）を本番扱いで使用」する実装のため、本番・ペーパーで監視 DB を分けたい場合は環境変数を明示的に設定してください。
- process_priority や CPU affinity の設定は環境（権限・OS）に依存します。権限不足時は警告を出してスキップします。
- research/factor_research の一部関数は今後の実装継続が想定されています（初期骨格を含む）。
- .env に機密情報を含める場合は必ず Git 管理対象から除外してください（config_setup の出力ヘッダにも注意喚起あり）。

### 破壊的変更
- なし（初期リリース）

---

この CHANGELOG はコードベースの現状から生成した推測に基づき記述しています。実際の変更履歴やマージ履歴と差異がある可能性があります。必要であれば、個別ファイルやコミットに基づくより詳細なログを生成します。