CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠します。  

注: 日付はリリース日です。

Unreleased
----------

（なし）

0.1.0 - 2026-04-24
-----------------

Added
- 全体
  - 初回公開リリース。パッケージのバージョンは __version__ = "0.1.0"。

- 起動スクリプト
  - run_monitoring.py を追加
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag により検知。
    - 監視は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用して接続。
    - duckdb と sqlite の接続を初期化し、init_monitoring_db を呼ぶ。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py を追加
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient 等を用いペーパートレード用専用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB から分離。
    - 起動時にプロセス優先度を "high" に設定し、エンジンを別スレッドで実行。停止フラグで安全に停止。
    - 実行時 pid ファイル（data/execution.pid）を扱う。

- 設定/環境管理
  - config.py を追加
    - .env 自動読み込み機能（.env, .env.local）を提供（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パースは export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、行内コメント処理に対応。
    - Settings クラスを提供。J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム設定 等のプロパティを定義。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、各種デフォルト値を持つ。

  - config_setup.py を追加
    - 対話式ウィザードで .env を生成・更新する CLI。
    - シークレット入力のマスク表示、選択肢・デフォルトのサポート、保存前の確認を実装。
    - .env のテンプレート出力と書き込み機能を提供。

  - validate_config.py を追加
    - 起動前の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML があればパース検証）を実施。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict オプションで警告をエラー扱いにできる。

- ユーティリティ
  - utils/logging_setup.py を追加
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定する共通ユーティリティ。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソールのみで継続。

  - utils/process_priority.py を追加
    - Windows / POSIX (Linux, macOS, FreeBSD) の差分を吸収してプロセス優先度（nice / Windows priority class）を設定する関数 set_process_priority(level)。
    - カレントプロセスの CPU affinity を設定する set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応環境では警告を出してスキップする安全設計。

- ポートフォリオ構築（純粋関数群 / DB 参照なし）
  - portfolio/portfolio_builder.py を追加
    - select_candidates: BUY シグナルをスコア降順 + signal_rank のタイブレークで選別。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等配分にフォールバック（警告ログ）。

  - portfolio/risk_adjustment.py を追加
    - apply_sector_cap: セクターごとのエクスポージャーに基づき新規候補を除外するロジック。sell_codes を当日売却対象として計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す。未知レジームはフォールバック 1.0（警告）。

  - portfolio/position_sizing.py を追加
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて各銘柄の発注株数を計算。単元株（lot_size）で丸め、max_position_pct / max_utilization / cost_buffer を考慮する集約キャップ（スケールダウン）を実装。
    - risk_based 方式ではリスク許容率（risk_pct）とストップロス率（stop_loss_pct）からベース株数を算出。

  - portfolio/__init__.py を追加して上記 API を公開。

- ツール
  - tools/paper_verification_report.py を追加
    - ペーパートレーディング結果の検証レポート生成スクリプト。
    - system_status, trade_logs, risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を集計。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数（未指定時デフォルト data/paper_trading.db）。
    - 判定基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）を参照して PASS/FAIL を出力。
    - CLI で期間 or DB を指定可能。

- リサーチ
  - research/factor_research.py を追加（ファクター計算モジュール：モメンタム等の雛形・定数を実装）
    - モメンタム算出のための定数や calc_momentum の関数雛形を追加（duckdb 経由で prices_daily を参照する設計）。
    - 他ファクター（Value/Volatility/Liquidity）についての設計コメントあり。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

注意事項 / マイグレーション情報
- 環境変数とデフォルト
  - .env の自動読み込みを行うため、既存の環境へ導入する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか .env/.env.local の内容を事前に確認してください。
  - 重要な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABUSYS_ENV は development / paper_trading / live のいずれか（大文字小文字は問わない）。
  - ログ: デフォルトは logs/<app_name>.log（日次ローテーション）。LOG_DIR 環境変数または setup_logging の引数で変更可能。

- データベース
  - 監視（run_monitoring）は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
  - 実行（run_execution）は paper_trading 環境時に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離します。
  - DuckDB は分析用に settings.duckdb_path（デフォルト data/kabusys.duckdb）を使用。

- 停止制御
  - stop フラグ: data/stop_requested.flag を配置すると監視・実行プロセスが安全に停止します。
  - Kill Switch の扱い（KILL_FLAG_CLEAR_ON_START）に注意。live 環境では自動クリア設定（=1）は推奨されません。

- ログ / 権限
  - 起動時にプロセス優先度を "high" にするため、権限不足により警告が出る可能性があります（処理は継続されます）。

将来の予定（短期ロードマップ）
- research/factor_research のファクター実装を完成させ、DuckDB の SQL を用いたフル実装へ拡張する予定。
- Strategy / Execution の各モジュール（既存の Engine/OrderManager 等）との統合テストおよび E2E テスト強化。

---

この CHANGELOG はコードベース（src/ 配下）から推測して作成しました。実際のリリースノート作成時は実装者の意図やリリース日付を反映してください。