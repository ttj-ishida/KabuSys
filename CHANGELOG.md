CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

Unreleased
----------

- 今のところ未リリースの変更はありません。

[0.1.0] - 2026-04-25
-------------------

初回公開リリース。システムの基盤となる起動スクリプト、設定管理、監視・発注エンジンまわりのユーティリティ、ポートフォリオ構築ロジック、調査用ファクター計算、運用支援ツールをまとめて提供します。

Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_monitoring
    - `src/kabusys/run_monitoring.py`：SystemMonitor をポーリングするループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルートの `data/stop_requested.flag` ファイルを検知して行う。
    - 監視処理は環境にかかわらず本番用の `sqlite_path` を使用する（監視データは本番 DB に保存）。
    - 起動時にプロセス優先度を `high` に設定。

  - run_execution
    - `src/kabusys/run_execution.py`：ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の専用 SQLite（`data/paper_trading.db` デフォルト）を使用して本番と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い `ExecutionEngine.run_session` をバックグラウンドスレッドで実行。
    - 起動時にプロセス優先度を `high` に設定。停止フラグ `data/stop_requested.flag` により安全に停止可能。
    - PID ファイル管理用に `data/execution.pid` を使用。

- 設定管理
  - `src/kabusys/config.py`
    - 環境変数・.env ロード機能を提供。プロジェクトルート（`.git` または `pyproject.toml`）を基準に `.env` / `.env.local` を自動ロード（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - 安全に .env の行をパースする `_parse_env_line`（クォートやエスケープ、インラインコメント処理対応）。
    - `Settings` クラスを導入し、各種設定（DB パス、API トークン、ログレベル、監視閾値、paper_trading 用パス等）へプロパティ経由でアクセス可能。
    - `PAPER_FILL_MODE` の検証（"instant" | "partial" | "never" | "reject"）や `KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェックを内包。

  - 設定ウィザード / 検証 CLI
    - `src/kabusys/config_setup.py`
      - 対話式ウィザードで `.env` の初期作成・更新を支援。複数の設定項目（J-Quants トークン、kabu API パスワード、DB パス、ログレベル等）を対話的に設定して `.env` に書き出す。
    - `src/kabusys/validate_config.py`
      - 起動前の設定検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック（PyYAML 非インストール時は警告）および本番時のガード条件（LINE 通知設定や KILL_FLAG_CLEAR_ON_START）を検査。
      - `--strict` オプションで警告を要件違反（exit 1）として扱うことが可能。

- ロギング・プロセス制御ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - `setup_logging(app_name, log_dir, level)` を提供。ルートロガーに stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時にはファイル出力をスキップして標準出力のみで継続。
    - ログローテーションは日次・30世代保持。ログレベルは引数 / 環境変数 `LOG_LEVEL` / デフォルトの順で解決。
  - `src/kabusys/utils/process_priority.py`
    - `set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を追加。Windows/Linux/macOS の差分を吸収してプロセス優先度や CPU affinity を設定（psutil ベース、権限不足時は警告でスキップ）。

- 監視 DB ユーティリティ
  - `src/kabusys/monitoring/*`（参照のみ）との統合呼び出しを各起動スクリプトで実行（`init_monitoring_db` を呼び出して監視テーブルの存在を保証）。

- ポートフォリオ構築ロジック（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル候補選定 `select_candidates`（スコア降順、同点は signal_rank の小さい順）。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等金額にフォールバック）。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限を行う `apply_sector_cap`、市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear マップ）を実装。未知レジームは警告を出してフォールバック。
  - `src/kabusys/portfolio/position_sizing.py`
    - 各銘柄の発注株数を計算する `calc_position_sizes` を実装。`risk_based` と `equal`/`score` の割当方式をサポート。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）を考慮。cost_buffer を使って手数料・スリッページを保守的に見積もるロジックを含む。
  - `src/kabusys/portfolio/__init__.py` で上記機能をエクスポート。

- リサーチ（ファクター計算）
  - `src/kabusys/research/factor_research.py`（一部実装）
    - DuckDB の `prices_daily` / `raw_financials` を使ってモメンタム等のファクターを計算するための骨格を追加（モメンタム期間定義、PCT 計算方針、関数スタブ）。（注: ファイル末尾で実装が途中の箇所あり）

- 運用ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH`）から検証レポートを生成するスクリプトを追加。
    - システム安定性（稼働率 / エラー数）、注文成功率（fill / send）、リスク却下数、API レイテンシ（avg / max / P95）を算出し、定義済み閾値に基づいて PASS/FAIL を判定。P95 算出ユーティリティを実装。
    - CLI で期間（--from/--to）や DB パス（--db）を指定可能。

Changed
- なし（初回リリースのため新規追加のみ）。

Fixed
- なし（初回リリースのためバグ修正履歴なし）。

Notes / Known issues
- `src/kabusys/portfolio/position_sizing.py` と `risk_adjustment.py` にて、価格欠損時の取り扱いやフォールバック価格に関する TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する想定。
- `research/factor_research.py` はモメンタム計算等の骨格があるが、ファイル末尾に実装途中の箇所が確認される（今後の拡張対象）。
- `validate_config` は PyYAML が未インストールの場合に YAML 内容検証をスキップして警告を出す設計。環境によっては追加依存のインストールが必要。

License
-------
（ライセンス情報はここに記載してください。プロジェクトに応じて追記してください。）