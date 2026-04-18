CHANGELOG
=========

すべての注目すべき変更点を記録します。形式は「Keep a Changelog」に準拠しています。
セマンティックバージョニングを採用しています。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの主要モジュールを追加しました。
  - 実行／監視エントリポイント
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（既定: data/paper_trading.db）を使用し MockBrokerClient を利用して本番 DB と分離。
      - Engine はスレッドで起動し、 data/execution.pid に PID を記録。 data/stop_requested.flag の存在で安全停止。
      - Execution に必要な依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立てる処理を実装。
      - RiskConfig の既定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、broker.get_available_cash() を初期ポートフォリオ値として参照。
    - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出しデフォルトにフォールバック。
      - 監視（monitoring）は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを初期化。
      - 停止フラグ（data/stop_requested.flag）検知でループを終了。
      - プロセス優先度を最初に "high" に設定。

  - 設定・起動支援ツール
    - config_setup.py: .env を対話式に作成/更新するウィザードを追加。
      - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を用意。
      - 生成される .env のテンプレートと注意書きを出力。
    - validate_config.py: 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。
      - 必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）。
      - KABUSYS_ENV=live 時の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）。
      - --strict オプションを提供（警告も失敗扱い）。
  - 環境設定読み込み
    - config.py: .env 自動読み込み機能を実装。
      - プロジェクトルート検出は .git または pyproject.toml を基準に上位ディレクトリを探索（CWD 非依存）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
      - .env パーサー（_parse_env_line）は export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントルールに対応。
    - Settings クラスを提供（settings インスタンスをモジュール末尾でエクスポート）。
      - 必須項目取得用の _require() 実装（未設定時は ValueError）。
      - 各種プロパティを提供: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, kill_flag_clear_on_start, CPU/メモリ/ディスク閾値、env/log_level/is_live/is_paper/is_dev、PAPER_FILL_MODE の妥当性検証（instant/partial/never/reject のみ許容）。
  - ロギングとプロセス制御ユーティリティ
    - utils.logging_setup.setup_logging: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定する統一 API を追加。LOG_DIR 環境変数や引数でログディレクトリを指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils.process_priority:
      - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定。psutil を利用し権限不足等の例外は警告でスキップ。
      - set_cpu_affinity(cpu_count): 指定コア数への固定をサポート（権限不足や未対応 OS は警告でスキップ）。
  - ポートフォリオ構築ライブラリ（pure functions）
    - portfolio.portfolio_builder:
      - select_candidates: スコア降順＋signal_rank によるタイブレークで候補選定。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
    - portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中上限による候補除外ロジック（"unknown" セクターは無視）。
      - calc_regime_multiplier: market regime に応じた乗数（bull/neutral/bear → 1.0/0.7/0.3、未知は 1.0 で警告）。
    - portfolio.position_sizing:
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算を実装。lot_size（単元）丸め、max_position_pct（per-stock cap）、max_utilization（aggregate）、cost_buffer（手数料・スリッページ見積り）を考慮。投資合計が available_cash を超える場合にスケーリングし、残差は lot 単位で再配分するアルゴリズムを実装。
  - ツール
    - tools.paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
      - PAPER_TRADING_SQLITE_PATH 環境変数/--db オプションで DB 指定可能。期間指定 --from/--to をサポート。
      - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、リスク却下数、API レイテンシ(P95 など) を集計。
      - デフォルト閾値: uptime >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 latency <= 200ms。判定 PASS/FAIL を出力。
  - 研究モジュール（着手）
    - research.factor_research.py: Momentum/Value/Volatility/Liquidity 等のファクター計算モジュールの骨格を追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。（ファイル末尾は途中のため詳細はこのリリースでは未完成）

Fixed
- .env パースの扱いを堅牢化:
  - export プレフィックス対応、クォート中のバックスラッシュエスケープ処理、行内コメントの取り扱いの不整合を解消。
- ログ設定: 既存ハンドラを安全に flush/close してから再設定するように修正（重複ハンドラの防止）。

Changed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes
- 監視（monitoring）と実行（execution）は DB を共有する設計だが、paper_trading モードでは実行側は paper_trading 専用 DB を使用して本番データと完全に分離するよう配慮しています。
- .env は機密情報（API トークン等）を含むため、生成される .env には「絶対に Git にコミットしないこと」と注記しています。
- factor_research.py は設計に基づく実装が進められているものの、このリリースで完全実装されていない部分があります（以降のリリースで追補予定）。

開発者向け補足
- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト実行時に便利です）。
- MONITOR_POLL_INTERVAL（秒）で監視ポーリング間隔を調整できます。不正な値（0 以下や非整数）はログ警告のうえデフォルト 60 秒にフォールバックします。

---