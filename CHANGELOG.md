# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初期リリース。KabuSys のコア機能および運用用ユーティリティ群を追加。

### 追加
- アプリケーションメタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト / デーモン化支援
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト60秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全に終了。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用するよう設計。
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper DB を使用（data/paper_trading.db をデフォルト）。
    - 停止フラグ・PID ファイル管理、デーモン風スレッド起動、停止監視を実装。
    - ブローカークライアントのファクトリ利用、OrderRepository/OrderManager/RiskManager 等の組み立て。

- 設定管理 / CLI
  - config.py：.env 自動ロード（.env, .env.local）や環境変数ラッパー `Settings` を追加。
    - .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等の設定プロパティを提供。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。
  - config_setup.py：対話式ウィザードで .env を作成・更新する CLI を追加。
    - 各項目の説明、既存値の再利用、シークレットマスク表示、保存機能を提供。
  - validate_config.py：起動前に環境変数・config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、パスチェック、YAML パース（PyYAML が無い場合は検証スキップ）、本番環境向けの追加警告等。
    - --strict オプションで警告も失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup.py：統一的なロギング設定ユーティリティを追加。
    - コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler）を設定。
    - LOG_LEVEL / LOG_DIR / app_name による出力制御、既存ハンドラのクリア。
  - utils/process_priority.py：プロセス優先度／CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX(Linux/Mac/FreeBSD) を吸収する実装。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供（権限不足時は警告でスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py：
    - select_candidates、calc_equal_weights、calc_score_weights を追加（スコア基準による候補選定・重み計算）。
  - portfolio/risk_adjustment.py：
    - apply_sector_cap：セクター集中上限チェック（sell_codes で当日売却予定銘柄を除外可能）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を計算（未知レジームはフォールバック）。
  - portfolio/position_sizing.py：
    - calc_position_sizes：allocation_method("risk_based" / "equal" / "score") に基づく株数決定ロジックを実装。
    - 単元株（lot_size）で丸め、per-position 上限 / aggregate cap のスケーリング、cost_buffer の考慮を実装。

- データベース統合
  - DuckDB/SQLite の両方を利用する設計を導入（duckdb パッケージを利用）。
  - monitoring_db.init_monitoring_db を起動時に呼び出してテーブルの存在を保証する（冪等的）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成スクリプトを追加。
    - system_status、trade_logs、risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計。
    - 基準値（稼働率99%、成立率90%、送信率95%、P95 <= 200 ms）を定義し PASS/FAIL 判定を行う。
    - コマンドライン引数 --from / --to / --db をサポート。

- 研究用モジュール（下地）
  - research/factor_research.py：Momentum / Value / Volatility / Liquidity 等のファクター計算用モジュールの初期実装。
    - DuckDB の prices_daily / raw_financials を利用してファクターを計算する設計（未完部分あり、設計方針を明記）。

### 改良
- .env パーサ強化
  - export KEY=val 形式や引用符付き値、バックスラッシュエスケープ、インラインコメントの扱い等に対応する堅牢なパーサを実装。
  - _load_env_file は override と protected（OS 環境変数保護）をサポートし、.env.local の上書き動作を実現。

- ロギング
  - stdout に出力する StreamHandler を採用（cron 等で stdout/stderr を一本化する運用を想定）。
  - ローテートファイルは日次・30世代保持。ログディレクトリ作成失敗時はファイル出力をフォールバック。

- プロセス管理
  - 起動直後に優先度を "high" に設定する呼び出しを run_monitoring/run_execution の先頭で実行。
  - 権限不足や未対応 OS の場合は警告を出して安全に継続。

### 修正 / 安全対策
- 実行時の安全スイッチ
  - stop_requested.flag / execution.pid / kill.flag 等のファイルベースの制御により、安全にプロセスの停止や二重起動防止を実現。
  - validate_config による起動前チェックで本番環境（KABUSYS_ENV=live）に対する注意喚起を追加。

- エラー耐性
  - ポーリングループ中に monitor.check_once() が例外を投げてもログを出力して次のポーリングへ継続する仕組みを導入。
  - DB やファイルハンドルの確実なクローズ（finally ブロック）を実装。

### ドキュメント（コード内コメント）
- 各モジュールに利用方法・設計方針・注意事項を豊富な docstring / コメントで追加。
  - 例: run_execution.py/run_monitoring.py の使い方・挙動説明、portfolio モジュールの参照ドキュメント行、logging_setup の利用方法など。

### 既知の制限 / TODO
- factor_research.py は実装の一部が途中（ファイル末尾が切れている）。完全実装は今後の課題。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価）については TODO コメントあり。
- 単元株サイズの銘柄別対応（lot_map）や手数料詳細モデルなどは将来的な拡張対象。

### セキュリティ上の注意
- .env は絶対にリポジトリにコミットしないこと（config_setup.py のヘッダに注意書きあり）。
- 環境変数にシークレットを含める設計のため、運用時の権限/ファイルアクセス管理に注意すること。

---

（この CHANGELOG はコード内容から推測して作成しています。細かな実装差分や追加のコミット履歴がある場合は適宜更新してください。）