CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はリリース日を示します。

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーション構成
  - パッケージ初期バージョンを追加（__version__ = 0.1.0）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを生成。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag により安全に停止可能。
    - 実行時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - stop フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt による終了にも対応。
- 設定管理
  - config.py: Settings クラスを実装。
    - .env / .env.local の自動読み込み機能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 各種環境変数の取得ラッパー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - env 値/LOG_LEVEL のバリデーション（有効値チェック）。
    - paper_trading 用 DB パスの取得（paper_sqlite_path）。
- 設定ユーティリティ
  - config_setup.py: インタラクティブな .env 作成ウィザードを追加。
    - 対話形式で必須/任意の環境変数を設定し .env を生成。
    - 秘匿値は表示をマスクして取り扱い。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス存在チェック（親ディレクトリ）、config/*.yaml の存在・パース検証（PyYAML がある場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティ追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を根幹ロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル/ログディレクトリの解決順を明記。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度と CPU affinity 設定。
    - Windows / POSIX（Linux/macOS 等）での差分吸収。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。権限不足などの失敗は警告で扱う。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分の実装（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター単位の集中リスク制限を適用するフィルタを実装（"unknown" セクターは除外免除）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは 1.0 でフォールバックして警告を出力。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") による発注株数算出を実装。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer（手数料/スリッページ見積り）を考慮。
    - 価格欠損時のスキップ、再現性を保つ残差処理（fractional remainder）を導入。
- 解析/検証ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - データベース（PAPER_TRADING_SQLITE_PATH または --db）から統計（稼働率、注文成功率、送信率、レイテンシ等）を集計し、PASS/FAIL 判定を出力。
    - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- 研究用モジュール（骨格）
  - research/factor_research.py: DuckDB 接続を用いたファクター計算の骨組みを追加（モメンタム等の定義・定数を含む）。（ファイル末尾はスニペットの都合で一部切断）

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Notes / Usage / Important details
- 監視（run_monitoring.py）は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能。無効な値（非整数や 0 以下）の場合はデフォルト 60 秒にフォールバックし警告を出す。
- run_monitoring.py は監視用 DB に settings.sqlite_path（本番パス）を常に使用する設計になっています。環境に依存せず監視データを一元管理したい場合に有用です。
- run_execution.py は paper_trading 環境を明確に分離。ペーパートレード用の DB を使用するため、本番データと完全に分離できます。
- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）を見つけられない場合は自動ロードをスキップします。
  - OS 環境変数が優先され、.env.local は .env を上書きする動作（ただし既存の OS 環境変数は保護される）。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用等）。
- 本番運用注意事項
  - validate_config の live チェックでは LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を警告します。KILL_FLAG_CLEAR_ON_START=1 は本番では危険です（Kill Switch が自動クリアされるため）。
  - logging_setup はファイル出力に失敗した場合でもコンソール出力は継続します（可用性重視）。
- 依存・環境
  - psutil（プロセス優先度/CPU affinity）、duckdb、sqlite3 等を使用します。config_yaml の検証には PyYAML があると内部パースも行いますが、未インストールでも検証は続行します（警告）。

未実装 / TODO
- research/factor_research.py の一部（ファクター計算の完全実装）およびその他の戦略/実行細部は今後追加予定。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価など）は TODO コメントとして残しています。

ライセンス
- 本リポジトリにライセンス表記がある場合はそれに従ってください（CHANGELOG 自体はドキュメントのみ）。
