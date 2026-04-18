# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

## [Unreleased]

（次のリリースに向けた変更点や予定をここに記載します）

---

## [0.1.0] - 2026-04-18

初回リリース。システム全体の起動スクリプト、設定管理、ポートフォリオ構築ロジック、実行エンジン補助、監視・検証ツール、ユーティリティ類を実装しました。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを提供。KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite（data/paper_trading.db を既定）を使用し、本番 DB と分離する動作をサポート。起動時にプロセス優先度を設定し、停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境設定にかかわらず本番 sqlite_path を使用する仕様。
- 設定管理
  - config.py: 環境変数読み込み・管理を提供。プロジェクトルート（.git または pyproject.toml）基準で .env/.env.local を自動ロード（OS 環境変数優先、.env.local は上書き）。環境変数の必須チェック用の _require、各種設定プロパティ（DB パス、PID/kill フラグ、閾値、ログレベル、環境判定など）を実装。PAPER_FILL_MODE の検証や paper_sqlite_path の分離等を実装。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。多数の設定項目を定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL など）。保存時にテンプレートヘッダを付与してファイル書き込み。
  - validate_config.py: 起動前の設定検証ツールを追加。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向けのガードチェック（LINE 通知設定や Kill Switch のクリア設定）を実施。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群、外部副作用なし）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（同点時は signal_rank 昇順）で選別。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で正規化した重みを計算。全スコアが 0 の場合は等金額配分にフォールバックして警告ログを出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限(max_sector_pct) に従い、特定セクターが既存保有で上限を超えている場合に新規候補銘柄を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（"bull" / "neutral" / "bear"）に応じた投下資金乗数を返す。未知レジームは警告ログを出して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: `risk_based` / `equal` / `score` の各 allocation_method に対応した発注株数計算を実装。単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、全体の aggregate cap（available_cash）超過時のスケーリング、cost_buffer による保守的コスト見積り、残余を fractional 残差に基づき再配分するロジックなどを実装。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティ。root ロガーに stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）のファイルハンドラを設定。既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: psutil を用いて Windows / POSIX（Linux/Mac/FreeBSD）間の差分を吸収したプロセス優先度（nice / Windows priority class）設定 API を提供。CPU affinity を最初の N コアに固定するユーティリティも実装。権限不足などで設定できない場合は警告ログにフォールバック。
- 実行・監視連携
  - monitoring/monitoring_db 初期化呼び出し（起動時に監視用テーブル存在を保証する init_monitoring_db の呼び出し）。
  - Execution 起動で pid_file と stop フラグ連携を実装（execution.pid の利用や stop flag の検出で安全停止）。
- ツール
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs テーブルからシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し、閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を出力。--from/--to/--db オプションで期間・DB 指定可能。PAPER_TRADING_SQLITE_PATH 環境変数に対応。
- 研究・計算
  - research/factor_research.py: ファクター計算基盤（DuckDB 接続を受け取り prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 等を計算する設計）。モメンタム計算用の定数と calc_momentum の骨格を追加（実装は継続）。

### 変更 (Changed)
- ログ動作
  - ログは stdout に出力する設計とし、ファイルハンドラはログディレクトリ作成に成功した場合のみ有効化することで、cron/task scheduler 等でのリダイレクト運用を容易化。
- .env ロード順
  - プロジェクトルート検出に基づいて自動で .env をロード（OS 環境変数 > .env.local > .env）。.env.local は .env の上書きとして扱い、既存の OS 環境変数は protected として上書き防止。

### 修正 (Fixed)
- なし（初回リリース）

### 既知の注意点 (Notes)
- run_monitoring は監視 DB として Settings.sqlite_path（デフォルト data/monitoring.db）を常に使用するため、Monitoring のテスト実行時は本番 DB を上書きしないよう注意が必要。ペーパートレード実行は run_execution 側で paper_sqlite_path を使用して分離しています。
- config_setup による .env ファイルはセキュリティ上 Git にコミットしないでください（ヘッダにもその旨を明記しています）。
- validate_config の YAML 検証は PyYAML が未インストールの場合スキップされます（警告出力）。
- research/factor_research.py は骨格を実装済みですが、いくつかの算出ロジック/最適化は今後の実装・テストが必要です（ファイル末尾が未完の可能性あり）。

### セキュリティ (Security)
- なし

---

過去の変更はありません（初回リリース）。今後のリリースではバグ修正や機能拡張、研究モジュールの完成、監視・レポートの強化などを予定しています。