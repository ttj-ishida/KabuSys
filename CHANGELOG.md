CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

Unreleased
----------

- （現時点で未リリースの変更はありません）

0.1.0 - 2026-04-19
-----------------

初期リリース。以下の主要機能・ユーティリティを実装しています。

Added（追加）
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル処理をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知、例外発生時のログ出力と次ポーリングへの継続処理を実装。

- 設定管理 / 初期化
  - config.py
    - 環境変数 / .env 自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env / .env.local の読み込み順序と既存 OS 環境変数保護の実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 各種設定値をプロパティとして提供（DB パス、PID パス、監視閾値、PAPER_FILL_MODE のバリデーションなど）。
  - config_setup.py
    - 対話式の .env 作成ウィザード。既存 .env 読込、シークレットマスク表示、保存時の確認を実装。
  - validate_config.py
    - 起動前の設定検証 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番向けガードチェックを提供。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定するユーティリティ。
    - LOG_LEVEL / LOG_DIR / 引数での上書きをサポート。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows/Linux/macOS でのプロセス優先度設定ラッパー（"high" / "normal" / "low"）。
    - CPU affinity 設定用 set_cpu_affinity を提供（指定が None の場合は無処理）。
    - 権限不足や未サポート環境では警告を出し安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコア全0 の場合は等配分へフォールバックし警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer による保守的見積もり、残差分の追加配分ロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH を参照）から、システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポート出力。
    - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。
    - DB が存在しない・テーブルが欠けている場合は適切に N/A やデフォールトを出力。

- research/factor_research.py（作業中）
  - DuckDB を用いたファクター計算基盤（モメンタム・MA200・ATR 等）の骨組みを実装開始。（ファイル末尾で未完の段階）

Changed（変更）
- なし（初期リリース）

Fixed（修正）
- ロバストネス向上
  - 環境変数パーサ（config._parse_env_line）でシングル/ダブルクォート内のバックスラッシュエスケープやインラインコメント処理を実装し、.env 読み込みの堅牢性を強化。
  - logging_setup: ログディレクトリ作成失敗時に例外を投げず、コンソールログのみで継続するように変更。
  - process_priority: サポート外 OS や権限不足時に警告を出してスキップすることで起動失敗を回避。

Security（セキュリティ）
- .env の扱いに関する注意書きを config_setup に追加（.env を絶対に Git にコミットしない旨）。

Notes / 個別注意事項
- Monitoring の挙動
  - run_monitoring は「環境にかかわらず」Settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計になっています。本番/ペーパートレードで監視 DB を分けたい場合は設定・設計の見直しが必要です。
- PAPER_FILL_MODE の検証
  - Settings.paper_fill_mode は有効値（instant/partial/never/reject）の検証を行い、無効値は ValueError を発生させます。
- validate_config の YAML 検証は PyYAML の有無に依存します。インストールされていない場合は YAML 内容チェックをスキップして警告を出します。
- research/factor_research.py は未完（calc_momentum の途中で切れている）。本格運用前に実装完了・テストが必要です。

Acknowledgements
- このリポジトリは自動売買システムの基礎機能（設定管理、起動スクリプト、監視、ポートフォリオ構築、ペーパートレード検証、ユーティリティ）を含む初期実装です。今後、テスト・ドキュメント・エラーハンドリング強化・モジュール分離・型注釈の厳格化などを進めることが想定されます。