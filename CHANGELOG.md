# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

全般的な注意
- 実装内容はコードベースから推測して記載しています。実際の挙動や意図と差異がある可能性があります。

## [Unreleased]

### 追加
- ドキュメント化／ユーティリティ
  - ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - コンソール出力（stdout）用 StreamHandler と、日次ローテーション（TimedRotatingFileHandler）を組み合わせてルートロガーを設定。
    - ログディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルは関数引数 > 環境変数 LOG_LEVEL > デフォルトの順で解決。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX 系の差分を吸収し、"high" / "normal" / "low" の抽象レベルで優先度を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - 権限不足や未対応環境では警告を出して処理をスキップ。

- 設定管理
  - Settings クラスを導入（kabusys.config）。
    - .env ファイルおよび環境変数から設定を読み込み。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env ファイルのパースにおいてシングル/ダブルクォートやエスケープ、インラインコメントなどに対応。
    - 必須値取得用の _require()、各種パス・閾値・フラグのプロパティを提供（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_* / CPU/MEMORY/DISK 閾値 等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）を実装。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。

- 設定補助 CLI
  - 対話式 .env 作成／更新ウィザードを追加（kabusys.config_setup）。
    - 質問に応じて .env を生成・保存する helper。
    - シークレット項目は表示時マスク、既存 .env の読み込み・再利用に対応。
    - 保存前に内容確認・キャンセル可能。
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数や KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース（PyYAML がインストールされている場合）をチェック。
    - KABUSYS_ENV=live のときに追加のガードチェック（LINE 設定、KILL_FLAG_CLEAR_ON_START 等）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行／監視エントリポイント
  - Execution エンジン起動スクリプトを追加（kabusys.run_execution）。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境に応じて本番用またはペーパートレード用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用。paper_trading 環境では MockBrokerClient を使用して本番 DB と完全分離する想定。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) と pid ファイル (data/execution.pid) を利用した起動・停止制御。
    - RiskManager 初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker, max_drawdown など）を設定。

  - SystemMonitor 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定、stop フラグでループ終了、例外時のログ出力・次ポーリングまで継続。

- 監視 DB ユーティリティ
  - 監視用 DB 初期化ヘルパ（init_monitoring_db）呼び出しが各起動スクリプトで利用され、監視テーブルの冪等的作成を保証。

- ポートフォリオ構築（Pure functions）
  - 銘柄選定と重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順（同点は signal_rank 昇順）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額とスコア正規化による重み計算。全スコアが 0 の場合は等金額にフォールバックして警告。

  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有を基にセクターごとの時価割合を計算し、上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。sell_codes（当日売却予定）の除外に対応。
    - calc_regime_multiplier: market regime（'bull'|'neutral'|'bear'）に基づく投下資金乗数を提供。未知のレジームは警告して 1.0 でフォールバック。

  - 株数計算・リスク制約・単元丸め（kabusys.portfolio.position_sizing）
    - calc_position_sizes: allocation_method（"risk_based"|"equal"|"score"）に応じて各銘柄の発注株数を計算。
    - lot_size 単位で切り捨て、max_position_pct（1 銘柄上限）、max_utilization（投下資金上限）、cost_buffer（スリッページ・手数料見積）を考慮した aggregate cap のスケーリング処理を実装。
    - risk_based では stop_loss_pct / risk_pct を用いた逆算でポジションサイズを決定。

- リサーチ
  - ファクター計算モジュール（kabusys.research.factor_research）を追加。
    - Momentum 等のファクター（1M/3M/6M リターン、MA200 乖離など）を DuckDB 上の prices_daily テーブルから計算する方針を実装開始。関数雛形（calc_momentum）を実装（途中までの実装あり）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - SQLite（PAPER_TRADING_SQLITE_PATH または --db 指定）からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計してレポート出力。
    - PASS/FAIL 基準を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms）し、判定理由を出力。
    - P95 計算、SQL クエリの期間フィルタ（ISO8601 UTC 文字列）対応、データがない場合の N/A 取り扱いを実装。

### 変更
- パッケージ初期化
  - パッケージのバージョンを __version__ = "0.1.0" として定義（kabusys.__init__）。

### 修正
- なし（新規コードベースに相当）

### 既知の注意点
- run_monitoring は説明どおり「監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」します。テストや開発環境での取り扱いに注意してください。
- config の自動ロードはプロジェクトルートの判定ロジックに依存するため、配布後やインストール環境で .git／pyproject.toml が存在しない場合は自動ロードがスキップされます。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御してください。
- factor_research の calc_momentum 等は実装が途中の箇所があり、完全な計算ロジックやエッジケース処理が未完成の可能性があります。

---

## [0.1.0] - 2026-04-18

初回リリース。上記 Unreleased に記載の機能群を含むリリース。

- 初回公開: 設定管理、ログ/プロセスユーティリティ、Execution/Monitoring 起動スクリプト、ポートフォリオ構成ロジック（選定・重み・リスク・ポジションサイズ）、ファクター計算の雛形、Paper Trading 検証ツール、設定ウィザード／検証ツールなどを提供。

---

記載に不足や誤りがありましたら、差分（どのファイルがどのように変更されたか）を教えてください。それに基づいて CHANGELOG を更新します。