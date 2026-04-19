# Changelog

すべての変更は Keep a Changelog の慣例に従い記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-19

初回公開リリース。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 起動スクリプト / 実行系
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（`data/paper_trading.db`）を使用する仕組みを導入し、本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御のためのフラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py
    - SystemMonitor をポーリングする監視用スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番の sqlite_path を使用して監視テーブルを初期化する。

- 設定管理
  - config.py
    - .env ファイルおよび環境変数から設定をロードする `Settings` クラスを追加。
    - プロジェクトルート (.git または pyproject.toml) を基に自動で .env を探索・読み込みする自動ロードを実装（無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート）。
    - 各種設定プロパティを提供（DB パス、LINE トークン、閾値、環境種別判定など）。
    - PAPER_FILL_MODE のバリデーション（有効値: "instant", "partial", "never", "reject"）。
    - PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH、PID / kill flag 等のデフォルトパスを定義。
  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。既存 .env の読み込み、シークレット入力、デフォルト値提示、保存機能を提供。
    - 自動生成された .env のテンプレート書き出し機能を提供。

- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の不足や設定ミスを起動前にチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML 無しでも安全に動作）、`--strict` による警告の FAIL 扱いをサポート。
    - 本番 (live) のときの追加ガード（LINE 通知確認、KILL_FLAG_CLEAR_ON_START の危険性警告）。

- ロギング・ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを追加。
    - LOG_DIR / LOG_LEVEL の解決順、ファイルハンドラ作成失敗時のフォールバック（コンソールのみ）を実装。
    - 既存ハンドラをクリアして二重設定を防止。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定を追加（`set_process_priority("high"|"normal"|"low")`）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を追加。
    - 権限制約や未対応プラットフォームでの安全フォールバックを実装。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - スコアが全て 0 の場合の等金額フォールバックと警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中抑制 (apply_sector_cap) と市場レジームに基づく乗数 (calc_regime_multiplier) を実装。
    - unknown セクターの扱い、レジームマッピング（bull/neutral/bear）と既定値フォールバックを実装。
  - portfolio/position_sizing.py
    - position sizing（risk_based / equal / score）を実装。単元株（lot_size）で丸め、max_per_stock / aggregate cap のスケーリングロジック、cost_buffer による保守的見積りを実装。

- Research（分析）モジュール（着手）
  - research/factor_research.py
    - Momentum 等のファクター計算モジュールを追加（DuckDB 接続受け取り、prices_daily/raw_financials を参照する設計）。
    - 1M/3M/6M リターン、MA200 乖離、ATR、出来高系などを計画。関数雛形を追加（calc_momentum 等）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite のデータから検証レポートを生成する CLI を追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ等。
    - デフォルト閾値を定義（例: uptime >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）。期間フィルタ（--from/--to）と DB パス指定をサポート。
    - 出力は人間向けテキストレポートで Pass/Fail 判定を表示。

- DB 初期化ユーティリティ呼び出し
  - 起動スクリプトから monitoring テーブルの初期化を行う `init_monitoring_db` を呼び出すようにし、監視テーブルの冪等な存在保証を行う。

- パッケージエクスポート
  - portfolio モジュールをトップレベルから import しやすいように __all__ を経由してエクスポート。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の問題 / 注意事項 (Known issues / Notes)
- research/factor_research.py の実装は着手段階で、calc_momentum の実装が途中（ファイル末尾が切れている可能性あり）。本機能は今後のリリースで完成予定。
- position_sizing の注釈にある通り、銘柄ごとの lot_size を将来的にサポートする計画あり（現状はグローバル lot_size）。
- apply_sector_cap は price_map に価格が欠損（0.0）が含まれるとセクターエクスポージャーを過小見積りする可能性があるため、フォールバック価格の導入を将来的に検討。
- プロセス優先度 / CPU affinity の設定は権限不足や一部プラットフォームで例外になりうるが、安全に警告してスキップする実装になっている。

### セキュリティ (Security)
- なし（初回リリース）

---

開発者向けメモ:
- .env 自動読み込みはデフォルトで有効。テスト環境等で自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 設定検証は `python -m kabusys.validate_config`、設定ウィザードは `python -m kabusys.config_setup`、ペーパートレードレポートは `python -m kabusys.tools.paper_verification_report` を参照してください。