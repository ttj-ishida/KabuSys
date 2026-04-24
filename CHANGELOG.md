# CHANGELOG

すべての重要な変更点をこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠します。

最新: Unreleased
過去のリリースは日付順（降順）で記載しています。

---

## [Unreleased]

- 開発中の変更はここに記載します。

---

## [0.1.0] - 2026-04-24

初回リリース。主要機能・ユーティリティとコマンドラインツール一式を追加。

### 追加 (Added)

- 全体
  - パッケージ初期バージョンを追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、Engine 起動とデーモンスレッド管理、停止フラグ検知により安全終了。

- 設定管理
  - config.Settings クラスを追加（環境変数経由の設定アクセス）。
    - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（未設定時は例外を送出）。
    - データベースパス、PID/kill フラグパス、閾値（CPU/MEM/DISK）などをプロパティとして提供。
    - PAPER_FILL_MODE（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH のサポート。
    - KABUSYS_ENV の値検証（development/paper_trading/live）と helper プロパティ（is_live / is_paper / is_dev）。
  - .env 自動ロード機能を追加
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み。
    - export 文、クォート文字列、コメントの扱いに対応。OS 環境変数の保護機能あり。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

- 設定支援ツール
  - config_setup: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - 標準の設定項目一覧（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス等）を扱う。
    - シークレット入力のマスク表示、候補選択、既存値の読み込み・再利用をサポート。
  - validate_config: 起動前の構成検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検査（PyYAML がある場合）。
    - KABUSYS_ENV=live 用の追加警告（LINE トークン未設定や Kill フラグ自動クリア設定など）。
    - --strict モードで警告を失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging を追加。
    - ルートロガーに stdout 出力の StreamHandler と日次ローテート（TimedRotatingFileHandler）を設定。
    - ログディレクトリ（デフォルト logs/）自動作成、30 日分保持、LOG_LEVEL / LOG_DIR との統合。
    - ファイルハンドラ作成失敗時にコンソールログのみで継続する耐障害性を実装。
  - utils.process_priority を追加。
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足等の例外は警告ログで扱い処理をスキップする。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア重み配分を提供。全スコアが 0 の場合は等配分にフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中の最大比率 (max_sector_pct) を適用し、超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）を提供。未知のレジームは 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じた株数決定ロジックを追加（"risk_based", "equal", "score" をサポート）。
    - ロジックの要点:
      - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）を考慮。
      - リスクベースは risk_pct / stop_loss_pct に基づく算出。
      - aggregate cap により投下総額が利用可能現金を超える場合はスケールダウンし残余を lot 単位で配分。
      - cost_buffer による手数料/スリッページ保守見積りを考慮。

- Paper Trading 検証ツール
  - tools.paper_verification_report を追加。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）から集計しレポートを標準出力へ出力。
    - 指標: 稼働率、注文成功率(Filled/Created)、送信率(Sent/Created)、リスク却下数、API レイテンシ（avg/max/P95）。
    - 合格基準（デフォルト閾値）を設定:
      - 稼働率 >= 99.0%
      - 成立率(Fill) >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付レンジ指定 (--from / --to) と --db オプションをサポート。

- 研究モジュール（骨組み）
  - research.factor_research を追加（ファクター計算モジュールの実装開始）。
    - モメンタム等のファクター計算（モジュール定数、calc_momentum の開始実装）を含む設計。DuckDB 接続を受け prices_daily / raw_financials テーブルを参照する方針。

### 変更 (Changed)

- なし（初回リリースのため該当なし）

### 修正 (Fixed)

- なし（初回リリースのため該当なし）

### セキュリティ (Security)

- なし（初回リリースのため該当なし）

---

備考:
- 本 CHANGELOG はコードベース（src/ 以下）から推測して作成しています。動作の詳細は該当モジュールの docstring / コメントをご参照ください。