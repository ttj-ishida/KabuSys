CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記述しています。  
バージョン番号はパッケージ内の __version__（0.1.0）に基づいています。日付は推定（最終更新: 2026-04-25）です。

Unreleased
----------
（無し）

[0.1.0] - 2026-04-25
-------------------

Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。
- 起動スクリプト / デーモン系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - stop_requested.flag による停止検知、例外時のログ出力と再試行ロジック。
    - 監視用 DB は KABUSYS_ENV に関わらず本番 sqlite_path を使用する旨を明記。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、ExecutionEngine のスレッド起動、停止フラグ検知による安全停止処理。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
- 設定管理 / ユーティリティ
  - config.py: 環境変数 / .env 管理モジュールを追加。
    - プロジェクトルート自動検出 (.git または pyproject.toml) に基づく .env 自動読み込み（.env, .env.local）。
    - クォートやエスケープ、コメントを考慮した .env パース実装。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス /監視閾値 /実行環境などをプロパティ経由で取得可能。
    - PAPER_FILL_MODE の妥当性チェックや KABUSYS_ENV, LOG_LEVEL のバリデーションを実装。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パースチェック（PyYAML があれば内容検証）。
    - --strict オプションで警告を FAIL 扱いにできる。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加。
    - 既存値の読み込み、秘匿表示（シークレット）のサポート、ファイル書き込みテンプレートを提供。
    - .env を誤ってコミットしないよう注意喚起のヘッダを出力。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定関数 setup_logging を追加。
    - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数や引数からの解決ロジックを実装。
  - utils/process_priority.py: プラットフォーム差を吸収するプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows（HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）の両対応を意識した実装。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足などで安全にフォールバック。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコアでソートして上位 N を選択。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中度チェックに基づく候補除外ロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。単元株（lot_size）丸め、aggregate cap によるスケールダウンと端数配分ロジックを実装。
    - 投資コスト見積りのための cost_buffer オプションや max_position_pct/max_utilization 等のリスク制限をサポート。
- Research / Tools
  - research/factor_research.py（部分実装を含む）: DuckDB から価格・財務データを参照して Momentum / Value / Volatility / Liquidity 等ファクターを計算する設計を追加（calc_momentum 等の実装開始）。
  - tools/paper_verification_report.py:
    - ペーパートレード検証用レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し PASS/FAIL 判定（閾値はソース内定義）する CLI を提供。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。
- DB 関連
  - run スクリプトで sqlite3（監視 DB / ペーパートレード DB）と duckdb の両方を利用する実装を追加。
  - monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

Changed
- n/a（初期リリースのため該当なし）

Fixed
- n/a（初期リリースのため該当なし）

Deprecated
- n/a

Removed
- n/a

Security
- .env の管理に関する注意書き・対話ウィザードでの秘匿表示を導入し、.env の誤コミット防止を啓発。

Notes / Known limitations
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる点を TODO コメントで注記。将来的に前日終値等のフォールバックを検討。
- portfolio/position_sizing:
  - 今は全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_map への拡張を想定する TODO が存在。
- research/factor_research.py は設計に基づく実装を含むが、ファイル末尾で実装途中（スニペットが途中で終わっている）。完全実装は今後のタスク。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップするフェイルセーフを持つが、運用での権限問題やディスク容量には注意が必要。
- process_priority の実行には適切な権限が必要。権限不足時は警告を出してスキップする安全設計。

開発メモ / 使用例
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔変更
- Execution 起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading DB を使用
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- .env ウィザード:
  - python -m kabusys.config_setup
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

もし CHANGELOG に追加したい差分（実際のコミット履歴やリリース日など）があれば、それに合わせて日付や項目を調整します。