# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

最新のリリースはセマンティックバージョニングに従います。

## [Unreleased]

- ドキュメントやテストに関する変更は未記載。
- 将来的な改善案（ログのより細かい設定、価格フォールバックの拡張、DuckDB クエリの最適化など）を検討中。

## [0.1.0] - 2026-04-19

### Added
- 初回公開リリース。
- 全体構成
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。
  - モジュール群: execution, monitoring, portfolio, utils, research, tools, config 関連のユーティリティを提供。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動用エントリポイントを提供。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、別スレッドでの ExecutionEngine 実行と停止フラグ監視を実装。
    - 起動時にプロセス優先度を "high" に設定する仕組みを利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全にループを終了。
- 設定管理
  - config.py
    - .env ファイル自動読み込み（`.env` → `.env.local`、OS 環境変数優先）。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルートを `.git` または `pyproject.toml` により探索して決定（CWD に依存しない）。
    - .env のパースはクォート、エスケープ、コメント（インライン含む）に対応。
    - 各種設定プロパティを提供（J-Quants・kabu API トークン、DB パス、PID / Kill flag パス、監視閾値、環境判定など）。
    - Paper Trading 関連: `paper_fill_mode`, `paper_sqlite_path` 等。
  - config_setup.py
    - 対話式ウィザードで .env ファイルを初期作成 / 更新する CLI を提供（`python -m kabusys.config_setup`）。
    - シークレット値はマスク表示、デフォルト・選択肢対応、書き込みテンプレートを整備。
  - validate_config.py
    - 起動前の環境検証ツールを提供（`python -m kabusys.validate_config`）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック（PyYAML が無ければ YAML 検証をスキップ）、本番向けガードチェック等を実施。
    - `--strict` オプションで警告をエラー扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler (日次、30日保持) を設定する共通セットアップを提供。
    - ログレベルは引数 > 環境変数 LOG_LEVEL > デフォルト の順で解決。ログディレクトリも引数 > LOG_DIR > デフォルト `logs/` の順で解決。
    - ファイルハンドラの作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows/Linux/macOS の差異を吸収してプロセス優先度（high/normal/low）を設定可能。
    - CPU affinity 設定機能（最初の N コアへ固定）を提供。権限不足や未対応プラットフォームでは警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、タイブレークに signal_rank）と等金額・スコア重みの計算を提供。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（既存ポジションを考慮した除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づいた発注株数計算。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite データからシステム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - CLI で期間指定（--from / --to）や DB パス指定（--db）に対応。P95 計算、閾値による PASS/FAIL 判定を実装。
- 研究用ファクター計算（着手）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity を計算する設計方針を盛り込み、DuckDB 接続を受けて prices_daily / raw_financials を参照することを想定した実装骨子を追加（モメンタム計算などの実装開始）。

### Changed
- ログ出力
  - 標準出力には stdout を使用（stderr ではない）：cron 等のリダイレクト運用を考慮。
- .env 読み込み順序と保護
  - OS 環境変数を保護キーとして `.env.local` の上書きを管理。

### Fixed
- DB 初期化の冪等性
  - monitoring の初期化を起動時に保証（init_monitoring_db を呼び出し）してテーブル欠落による起動失敗を防止。

### Security
- シークレット取扱い
  - config_setup / .env ファイル生成時にシークレットはマスク表示。README 等で .env をコミットしない旨を明記（生成ヘッダに含む）。

### Notes / Known limitations
- research/factor_research.py は一部実装が途中（ファイル末尾が切れている）ため、完全実装が必要。
- price フォールバック: risk_adjustment.apply_sector_cap と position_sizing.calc_position_sizes の一部で price が欠損した場合の取り扱いが暫定的（TODO コメントあり）。将来的に前日終値や取得原価を使うフォールバックを検討。
- process_priority/set_cpu_affinity は権限やプラットフォーム依存のため失敗時は警告でスキップする設計。

---

（この CHANGELOG はコードベースから推測して作成しています。実際のリリース履歴や変更履歴を正確に反映するにはコミット履歴やリリースノートの確認を推奨します。）