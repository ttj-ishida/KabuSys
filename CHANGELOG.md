# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
日付は 2026-04-18 にリリースされた v0.1.0 を示します。

## [0.1.0] - 2026-04-18

### Added
- 初回公開: KabuSys ベースライブラリと複数の起動スクリプト / ユーティリティを追加。
- 実行スクリプト
  - run_execution.py: 実注文処理を起動する ExecutionEngine 用エントリポイントを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）へ記録して本番 DB と完全分離する。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル (data/execution.pid) を管理。
    - 停止フラグ (data/stop_requested.flag) を監視して安全に停止。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。  
    - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計（監視データは本番 DB を参照/記録）。
    - ポーズ/停止フラグ検知・例外ハンドリングを備えたループ。
- 設定管理
  - config.py: 環境変数読み込み・管理クラス `Settings` を実装。
    - 自動 .env ロード機構: プロジェクトルートを検出して `.env` / `.env.local` を読み込む（OS 環境変数を保護）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 各種設定プロパティ（J-Quants トークン、kabu API、DB パス、PID/kill flag パス、モニタ閾値、環境種別など）を提供。値検証（例: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE）を実装。
    - `settings` のインスタンスをエクスポート。
- 設定補助ツール
  - config_setup.py: 対話型ウィザードで `.env` を初期作成・更新する CLI を追加。
    - シークレット入力、選択肢、既存値再利用、保存確認機能などを提供。
  - validate_config.py: 起動前に .env および config/*.yaml の設定不備を検出する検証 CLI を追加。`--strict` オプションで警告を失敗扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML ファイルの存在とパース検証、`live` モード向けの追加ガードを実装。
- Paper Trading ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成ツールを追加。  
    - 稼働率、注文成功率（fill/send）、リスク却下数、API レイテンシ（平均・最大・P95）を算出して PASS/FAIL を判定する。  
    - デフォルト DB: data/paper_trading.db。コマンドラインで期間指定や DB パス上書きが可能。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルから候補を選定する `select_candidates`（スコア降順、同点時は signal_rank によるタイブレーク）。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap`（売却予定銘柄を除外して既存エクスポージャを評価、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear をマッピング、未知の値は 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 複数の配分方式（risk_based / equal / score）に対応した株数決定ロジック `calc_position_sizes` を実装。
    - 単元株（lot_size）丸め、銘柄/総計の上限（max_position_pct, max_utilization）、手数料・スリッページのための cost_buffer、投資合計が利用可能現金を超えた場合のスケールダウン・端数分配ロジックを備える。
  - portfolio/__init__.py でエクスポートを整理。
- ユーティリティ
  - utils/logging_setup.py: 全アプリで共通のログ設定ユーティリティを追加。  
    - stdout（StreamHandler）と日次ローテーションファイル出力（TimedRotatingFileHandler、30日保持）をルートロガーに設定。`LOG_DIR`/`LOG_LEVEL` で上書き可。既存ハンドラの再設定処理あり。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。  
    - Windows/Linux/macOS 対応（psutil を使用）。`set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供。権限不足時は警告を出して安全にスキップ。
- monitoring/monitoring_db.py などモニタリング周りの初期化呼び出しを各スクリプトで行う（監視テーブルの冪等初期化）。
- research/factor_research.py: ファクター計算モジュールの骨組みを追加（DuckDB を用いた価格・財務データに基づくモメンタム/ボラティリティ/流動性等の計算を想定）。  
  - （ファイルは実装途中の箇所あり）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- 停止制御はファイルベース（data/stop_requested.flag, data/kill.flag）で実装され、運用上の簡易な Kill Switch を提供。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値に対してログ警告を出しデフォルト値にフォールバックする（0 や負の値は無効）。
- config の .env パーサはクォート、エスケープ、`export KEY=val` 形式、行末コメントの扱いなどを考慮した堅牢な実装になっている。
- logging_setup はログディレクトリ作成失敗時はファイル出力を諦めて stdout のみで継続する安全設計。
- process_priority / CPU affinity の設定は権限やプラットフォームに依存するため失敗時はログ警告に留める。

---

今後の予定（アイデア）
- research/factor_research の完全実装とユニットテスト追加。
- ExecutionEngine / BrokerClient 等のモジュールのドキュメント整備と統合テスト。
- 監視・レポートの自動メール/LINE 通知連携。
- 単体テスト・CI の追加。

もし CHANGELOG に特定の項目（例: 追加の修正や日付の調整）を反映したい場合は知らせてください。