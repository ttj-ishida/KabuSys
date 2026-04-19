CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 基本アプリケーションと CLI を追加（初期リリース）。
  - src/kabusys/__init__.py にてバージョン 0.1.0 を設定。
- 実行（Execution）関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検出で優雅に停止。PID ファイルサポート。
    - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装。
- 監視（Monitoring）関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず production 用 sqlite_path を使用する設計（注記あり）。
    - 停止フラグ検出、例外捕捉、ログ出力を含む堅牢なループを実装。
    - duckdb と sqlite の接続を確立し、監視 DB 初期化を呼び出す。
- 設定・環境管理
  - config.py: 環境変数と設定管理クラス Settings を実装。
    - .env の自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の優先順位、オーバーライド制御、保護キー（OS 環境変数保護）に対応。
    - 各種プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID/KILL フラグパス, しきい値等）の取得とバリデーションを実装。
    - KABUSYS_ENV / LOG_LEVEL の検証を組み込み。
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 初期 .env の作成・更新を支援。シークレットはマスク表示。テンプレートでファイルを書き出し。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
    - --strict モードで警告を失敗扱いにできる。
    - production 向けのガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START 設定 など）を警告。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates（スコア降順・同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合のフォールバック警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター集中上限に基づく候補除外。unknown セクターは除外対象外）。
    - calc_regime_multiplier（market regime に基づく投下資金乗数; bull/neutral/bear マップ、未知はフォールバックして 1.0）。
  - portfolio/position_sizing.py:
    - calc_position_sizes（allocation_method: risk_based / equal / score を実装）。
    - 単元株（lot_size）で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap のスケーリングロジックを実装。
    - 価格欠損等のケースでのログ出力とスキップ挙動を実装。
- ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーの初期化ユーティリティを追加。
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 世代保持）を組み合わせて設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリは引数・環境変数で解決。
  - utils/process_priority.py:
    - set_process_priority(level)（Windows / POSIX の差を吸収）。
    - set_cpu_affinity(cpu_count)（指定数だけ最初のコアに固定）。
    - psutil の権限エラー等は警告してフォールバック。
- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード DB を分析して検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）を算出し、閾値に対する PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）および --db/環境変数で DB パスを指定可能。
- リサーチ
  - research/factor_research.py:
    - モメンタム / ボラティリティ / Value / Liquidity 等の定義と定数を導入。
    - calc_momentum の枠組みを追加（prices_daily テーブル参照前提）。※実装の一部は拡張の余地あり（現状での計算用定数・入力仕様は定義済み）。

Changed
- ログ運用の統一:
  - すべての起動スクリプトは setup_logging を呼び出し、出力が一貫するようにした。

Fixed
- （初期リリースのため特定のバグ修正履歴はなし。各モジュールは例外処理と失敗時のフォールバックを多めに実装して堅牢性を確保。）

Security
- シークレットの扱い:
  - config_setup の対話表示ではシークレット項目（トークン・パスワード）をマスク表示。
  - .env ファイル作成時に「.env を絶対に Git にコミットしないこと」を明記。

Notes / Breaking changes / Important details
- 監視（run_monitoring.py）はドキュメントに明示されている通り、KABUSYS_ENV にかかわらず settings.sqlite_path（production 想定の監視 DB）を使用します。異なる DB を使いたい場合は設定を上書きしてください。
- run_execution.py は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。
- 環境変数の自動ロードは既定で有効（.env / .env.local をロード）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のみ許容。無効値は ValueError を送出します。
- process_priority / cpu_affinity 設定は OS 権限に依存します。権限不足時は警告を出してスキップします。
- research/factor_research の calc_momentum は設計フレームを含みますが、実運用に使う場合はデータ範囲や欠損処理の追加検討が必要です。

Acknowledgements
- 本リリースはシステム監視、実行エンジン起動、環境設定ユーティリティ、ポートフォリオ構築ロジック、ペーパートレード検証ツール、ログ/プロセスユーティリティ等の基盤機能を提供します。運用や戦略の微調整、追加の安全弁（例: より厳密な入力検証や拡張テスト）は今後の課題です。