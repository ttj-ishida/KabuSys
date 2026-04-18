CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは "Keep a Changelog" の形式に従っています。  

フォーマット:
- Unreleased: 今後の変更予定
- 各リリースは日付を付与

[Unreleased]
-----------

- なし（次回リリースに向けた未確定の変更点があればここに記載します）

[0.1.0] - 2026-04-18
-------------------

最初の公開リリース。本リポジトリは日本株自動売買システム KabuSys の基礎機能群（実行/監視スクリプト、設定管理、ポートフォリオ構築ロジック、ユーティリティ群、ペーパートレード検証ツール、研究用ファクタ計算の骨子）を含みます。

Added
- 全体
  - 初期バージョン 0.1.0 を追加（src/kabusys/__init__.py にてバージョン管理）。
  - パッケージ公開に必要な主要モジュールと CLI スクリプトを追加。

- 実行・監視
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading の際は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成を組み込み。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てを行う。RiskManager 用のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec 等）を定義。
    - 停止フラグ（data/stop_requested.flag）検知で安全にエンジン停止。execution.pid を利用。
    - DB（SQLite / DuckDB）に接続し、起動後にクローズ。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は実行環境にかかわらず本番 sqlite_path を使用（監視用 DB 初期化を実施）。
    - 停止フラグ検知でループを抜け、DB をクローズ。

- 設定・検証
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序と override 挙動を実装。OS 環境変数は保護される（protected keys）。
    - .env ファイルの堅牢なパーサを実装（export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
    - Settings クラスを導入し、各種設定値（API トークン、DB パス、Paper Trading 設定、監視閾値、環境区分など）をプロパティで提供。入力検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を行う。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD フラグにより自動ロードを無効化可能（テスト向け）。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML が利用可能なら）パース検証を実施。
    - KABUSYS_ENV=live 時の追加安全チェック（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションを提供（警告を FAIL とみなす）。

  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを実装。
    - J-Quants / kabu API / DB パス / LINE トークン等の必須/任意項目を対話的に設定し .env を生成。
    - 既存 .env の読み込み・再利用、秘密項目のマスク表示、保存前確認を実装。

- ロギング・プロセス管理
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを提供。
    - ログディレクトリ自動作成。作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。

  - utils/process_priority.py
    - Windows/Linux/macOS を跨いだプロセス優先度設定ユーティリティを提供（psutil を利用）。
    - CPU affinity 設定関数も提供。権限不足や未対応プラットフォーム時は安全にスキップして警告を出す。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順、signal_rank のタイブレーク）、等金額配分・スコア配分（score-weighted）を提供。スコア全て 0 の場合は等金額配分へフォールバック。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）：既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）：market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは 1.0 にフォールバック。

  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap を考慮したスケーリング処理、手数料・スリッページ見積りを考慮する cost_buffer、残差分のロット追加配分などを実装。
    - price 欠損時のスキップやログ出力に対応。

  - portfolio/__init__.py
    - 主要関数のエクスポートを整理。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計してレポート化。
    - 判定基準（稼働率 99% 以上、注文成功率 90% 以上、送信率 95% 以上、P95 レイテンシ <= 200ms）を定義し PASS/FAIL を出力。
    - コマンドライン引数で期間指定（--from / --to）と DB パス指定（--db）に対応。

- 研究用
  - research/factor_research.py
    - ファクター計算モジュールの骨子を追加（モメンタム / MA200 / ATR / Volume 等の定数と calc_momentum の雛形を含む）。DuckDB を使った prices_daily 参照を想定した設計。注: 実装は一部（calc_momentum の続き）で未完。

- 監視 DB 初期化ユーティリティ
  - monitoring/monitoring_db.py（参照されているが本差分では実体は省略）と連携して起動時に監視テーブルの存在を保証する呼び出しを実装（init_monitoring_db を各起動スクリプトで使用）。

Changed
- なし（初回リリースのため）

Fixed
- なし（初回リリースのため）

Notes / 既知の制約
- SystemMonitor / ExecutionEngine / BrokerClient 等、外部依存（kabuステーション API, J-Quants, 実際の BrokerClient 実装など）に対する具体的な実装は別モジュールに依存しており、本リリースではそのインターフェースを前提に起動スクリプトや統合を実装しています。
- research/factor_research.py の calc_momentum 関数は途中で切れているため、完全なファクター計算は次版で完成予定です。
- apply_sector_cap の価格欠損（price == 0.0）時の挙動については TODO コメントあり（将来的にフォールバック価格を導入予定）。
- process_priority や set_cpu_affinity は権限不足やプラットフォーム差異でスキップする設計のため、設定が反映されない場合はログに警告が出力されます。
- .env は機密情報を含むため、絶対にリポジトリにコミットしないでください（config_setup.py のヘッダでも注意喚起あり）。

作者注
- 本 CHANGELOG は提示されたソースコードから機能・設計意図を推測して作成しました。実際の開発履歴（コミットログ等）が存在する場合はそちらを優先して正式な変更履歴を作成してください。