CHANGELOG
=========

すべての注目すべき変更点を記録します。  
形式は「Keep a Changelog」に準拠します。

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-20
-----------------

初回リリース

Added
- 実行スクリプト / デーモン類を追加
  - run_execution.py: ExecutionEngine 起動用エントリポイントを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離する。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。バックグラウンドスレッドでエンジンを実行し、停止フラグで安全停止する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。停止フラグの検出と例外耐性を備えたループを実装。

- 設定管理とセットアップ
  - config.py: .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml基準）、export KEY=val 形式・クォートやエスケープを考慮した .env パーサ、環境変数の取得ラッパ（Settings クラス）を追加。PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、各種監視閾値や PID / KILL フラグのパス等をプロパティとして提供。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。機密値はマスク表示、確認プロンプト、.env の書き出し機能を持つ。

- 設定検証 CLI
  - validate_config.py: .env と config/*.yaml の整合性検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は YAML のパース検証、KABUSYS_ENV=live 時の追加ガード等を実装。--strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）/等重み（calc_equal_weights）/スコア加重（calc_score_weights。全スコア 0 の場合は等重にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限適用関数 apply_sector_cap（既存保有のセクター比率に基づく候補除外、売却予定銘柄を考慮）と、市場レジームに基づく資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py: position sizing 実装。allocation_method（risk_based / equal / score）に対応。リスクベース計算、単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金を超えた場合のスケールダウン）を備え、コストバッファ（手数料・スリッページ見積り）を考慮した調整ロジックを実装。aggregate スケーリング時に残差に基づく追加配分アルゴリズムを導入。

- 運用ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを追加。stdout 出力の StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）を設定。LOG_DIR/LOG_LEVEL の環境変数を尊重し、ディレクトリ作成失敗時はファイル出力をフォールバック（コンソールのみ）する。既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加（Windows / POSIX 対応）。set_process_priority(level) で high/normal/low を設定、set_cpu_affinity(cpu_count) で CPU affinity を固定。psutil 利用時のアクセス権限例外を安全にハンドリング。

- Paper Trading 用検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。system_status/trade_logs/risk_logs を参照して稼働率、注文成功率（fill_rate）、送信率、レイテンシ（平均/最大/P95）等を集計・判定（PASS/FAIL）。P95 計算、日付フィルタ、DB 存在チェック、欠損テーブルに対するフォールバックを備える。閾値はソース内定数で定義（稼働率 >=99%、fill_rate >=90% 等）。

- 研究モジュール（骨格）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（Momentum / Value / Volatility / Liquidity 計算方針と一部実装）を追加。prices_daily / raw_financials のみ参照する設計。

Changed
- パッケージ化とエクスポート
  - kabusys/__init__.py に __version__= "0.1.0" を設定し、主要サブパッケージを __all__ に追加。

Fixed
- .env パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いを改善。無効行の無視や未定義キーの扱い（override オプション、protected キー保護）を明確化。

- ロギングの堅牢化
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時に落ちないようにし、標準出力（stdout）へのフォールバックを明示的に行うよう修正。

Notes / Behavior
- 監視用ループ（run_monitoring）は MONITOR_POLL_INTERVAL 環境変数を読んでポーリング間隔を決定する。無効な値（非整数や 0 以下）の場合はデフォルト 60 秒にフォールバックして警告ログを出す。
- run_monitoring は監視 DB 初期化（init_monitoring_db）を行い、DuckDB も開く。SystemMonitor.check_once() の例外は捕捉してログ出力しループ継続する。
- Execution 側は RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を用意し、初期 available_cash を broker.get_available_cash() から取得する設計。
- PAPER_FILL_MODE は instant/partial/never/reject をサポートし、不正値は例外を発生させる。
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" 扱いし、unknown セクターはセクター上限の対象外（除外しない）。

Security
- 機密情報取り扱い: config_setup のウィザードは機密フィールドをマスク表示するが、.env は平文で保存するため、.env を絶対にリポジトリにコミットしない旨を注意書きとして出力する。

Acknowledgements / TODO
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_size を stocks マスタに持たせる拡張を想定（TODO コメントあり）。
- apply_sector_cap の価格欠損時の処理（price が 0.0 の場合のフォールバック）については注意書きと将来の拡張候補を残している。
- research/factor_research.py はモメンタム等の計算ロジックを実装中（ファイル末尾が未完の状態のため、追加実装・テストが必要）。

---

今後のリリースでは、テストカバレッジ、ドキュメント（API リファレンス・運用手順）、および研究モジュールの完成を優先予定です。