# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  

注: 以下は提供されたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-04-20

初回リリース。システム全体の起動スクリプト、設定管理、ポートフォリオ構築ロジック、ユーティリティ、ツール類、および一部のリサーチ機能を実装しました。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動／停止制御を実装。
    - 停止フラグ（data/stop_requested.flag）検知による安全な停止、実行時 PID ファイル出力の仕組みを追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト: 60秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
    - 停止フラグ検知でループを終了、エラー時にログを残して次ポーリングへフォールバック。

- 設定関連
  - config.py: 環境変数／.env 読み込みと Settings クラスを実装。
    - プロジェクトルート検知（.git または pyproject.toml）を起点に .env 自動ロード（.env → .env.local、OS 環境変数を保護）。
    - キー必須チェック用の _require()、各種設定プロパティ（DB パス、paper trading の設定、閾値等）を実装。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の入力検証を実装。
  - config_setup.py: 対話式 .env 作成／更新ウィザードを追加。
    - 複数項目のプロンプト、既存 .env の読み込み・表示、保存機能を備える。
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml ファイルの存在と YAML パース（PyYAML があれば）を検証。
    - --strict モードで警告もエラー扱いに可能。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder.py
    - select_candidates: BUY シグナルのソート・上位選定（score 降順、同点は signal_rank 昇順）。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重の重み算出（全スコアが 0 のときは等配分にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率が閾値を超える場合の候補除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知のレジームは警告の上でフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate 上限の適用、コストバッファ考慮、available_cash 超過時のスケーリング（端数処理の再配分）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を実装。
    - コンソール stdout 出力と日次ローテーション（TimedRotatingFileHandler、30日保持）のファイル出力を構成。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみでフォールバック。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py
    - set_process_priority / set_cpu_affinity を提供。Windows と POSIX の差分を吸収し、権限不足や未対応 OS の場合は警告を出して安全にスキップする。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs 等から稼働率・成功率・送信率・レイテンシ（avg/max/P95）を算出し、閾値 (稼働率 99%、成立率 90% 等) に基づき PASS/FAIL を判定。
    - CLI オプションで期間指定（--from / --to）と DB パス指定（--db）に対応。

- リサーチ（部分実装）
  - research/factor_research.py
    - Momentum, Value, Volatility, Liquidity 等のファクター計算方針とモメンタム系計算の骨組みを実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。（ファイルは途中まで提供）

- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。

### 変更 (Changed)
- N/A（初回リリースのため既存機能の変更履歴はなし）

### 修正 (Fixed)
- N/A（初回リリースのため過去バグ修正履歴はなし）

### 既知の制限 / 注意事項
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる設計。
- apply_sector_cap は "unknown" セクターを上限適用対象外とするため、マスタ未登録銘柄の扱いに注意が必要（TODO コメントあり）。
- position_sizing の lot_size は現状グローバル共通で 100 固定を想定。将来的に銘柄別単位への拡張を想定したコメントあり。
- process_priority / set_cpu_affinity は権限不足・未対応プラットフォームで動作しない場合があるが、安全にログ警告を出してスキップする実装。

---

発行日: 2026-04-20