CHANGELOG
=========

すべての出演は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。

バージョン
---------

### 0.1.0 — 2026-04-18

Added
-----
- 初回公開リリース。
- 実行用スクリプト / デーモン類を追加。
  - run_execution.py — ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB 接続、BrokerClient の生成、ExecutionEngine の起動／停止監視（data/execution.pid, data/stop_requested.flag を使用）。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite (data/paper_trading.db) を利用するよう分離。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能。監視は環境に関わらず本番 sqlite_path を使用（監視テーブルの初期化、duckdb 接続を行う）。
- 設定管理・セットアップ・検証 CLI を追加。
  - config_setup.py — 対話式ウィザードで .env を作成／更新。シークレット項目はマスク表示。作成された .env は Git にコミットしない旨の注記を出力。
  - validate_config.py — .env と config/*.yaml の起動前検証 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 等の値チェック、DB パスや YAML ファイルの存在・パース検証、KABUSYS_ENV=live の追加ガードを実装。--strict モードで警告を FAIL 扱いにできる。
- 設定読み込み／Settings 実装（config.py）。
  - プロジェクトルート自動検出（.git または pyproject.toml による）。自動で .env/.env.local を読み込む仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env のパースは export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント扱い等に対応。
  - Settings クラスで多くの設定プロパティを提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、paper_trading 用パス、監視しきい値、env/log_level バリデーションなど）。
  - PAPER_FILL_MODE の入力検証（"instant"|"partial"|"never"|"reject" のみ許容）。
- ログ／プロセス管理ユーティリティを追加（utils）。
  - logging_setup.py — ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティ。ログディレクトリ作成に失敗した場合はファイル出力を自動でフォールバックしてコンソールのみで継続。
  - process_priority.py — Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS の安全ハンドリングあり。
- ポートフォリオ構築モジュール（portfolio/*）。
  - portfolio_builder.py — 候補選定 (select_candidates)、等配分 / スコア加重配分 (calc_equal_weights, calc_score_weights) を実装。スコア合計が 0 の場合は等配分にフォールバック。
  - risk_adjustment.py — セクター集中制限 apply_sector_cap と市場レジーム乗数 calc_regime_multiplier を実装。セクター上限超過銘柄の除外ロジック、未知レジームでのフォールバックと警告。
  - position_sizing.py — position size 計算（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash に合わせたスケールダウン）、cost_buffer（スリッページ・手数料見積り）対応、残差処理で lot 単位の追加配分を安全に行う。
- Paper Trading 検証ツールを追加（tools/paper_verification_report.py）。
  - ペーパートレード用 SQLite を解析して稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を行う CLI。期間フィルタ、DB パス引数／環境変数対応、各種閾値を定義。
- 研究用ファクター計算の骨組み（research/factor_research.py）を追加。
  - モメンタム、MA200 乖離、ATR、出来高等のファクター算出方針・定数を定義。DuckDB 接続を受けて prices_daily/raw_financials を参照する設計（関数の実装は一部スケルトン）。

Changed
-------
- ロギングの挙動を標準化: 全起動スクリプトは setup_logging を呼び出して stdout と日次ローテーションログを統一的に扱うようになった。
- .env 自動読み込みの挙動:
  - OS 環境変数を保護して .env.local の override を行う（OS 環境変数が優先）。
  - プロジェクトルートが検出できない場合は自動ロードをスキップ。

Fixed
-----
- .env パーサの堅牢化:
  - export プレフィックス対応、シングル／ダブルクォート内のエスケープ処理、インラインコメントの扱い（クォート有無での違い）を正しく処理するよう改善。
- process_priority / CPU affinity の失敗時に例外により起動が止まらないように警告ログでフォールバックする実装を追加。
- run_monitoring / run_execution における停止フラグ（data/stop_requested.flag）検知を標準化し、既にフラグが立っている場合の安全な起動停止を実装。

Security
--------
- config_setup の表示ではシークレット項目をマスクして表示（保存前の確認画面でもマスク）。
- .env ファイル生成テンプレートに「.env は絶対に Git にコミットしないこと」の注記を明示。

Notes / Migration
-----------------
- 起動前に validate_config.py で設定検証を行うことを推奨します（必須環境変数未設定だと Settings からの呼び出し時に ValueError が発生します）。
- 自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で使用）。
- MONITOR_POLL_INTERVAL は run_monitoring のポーリング間隔（秒）を上書きします。不正な値（整数変換不可・0 以下）はデフォルト 60 秒にフォールバックします。
- PAPER_FILL_MODE は許容値が限られています（instant/partial/never/reject）。不正な値を設定すると起動時に例外となります。
- run_monitoring は監視 DB に対して常に Settings.sqlite_path（本番向け）を使用します。監視 DB を分離したい場合は環境変数で SQLITE_PATH を適切に設定してください。
- run_execution は paper_trading 環境で paper_sqlite_path を使用して本番 DB とデータを分離します。

Acknowledgements
----------------
- 本リリースで導入した各モジュールは、今後ユニットテスト・ドキュメント・追加のエラーハンドリング・性能最適化を順次進めます。ご利用・フィードバックを歓迎します。