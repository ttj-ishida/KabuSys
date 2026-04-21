CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ を基準にしています。

[Unreleased]
-------------

（現在のコードベースが初期リリース相当のため、主な内容は以下 0.1.0 にまとめています）

0.1.0 - 2026-04-21
------------------

Added
- 全体
  - 初回公開相当の機能群を追加。自動売買システム "KabuSys" のコアモジュールを提供。
  - duckdb/SQLite を併用したデータ管理、実行エンジン、監視、ポートフォリオ構築、ユーティリティ群を実装。

- 起動スクリプト
  - run_execution.py:
    - ExecutionEngine を起動する CLI スクリプトを追加。BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせてエンジンを起動。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）が検知されたら安全に停止する仕組みを追加。
    - 実行中の PID を data/execution.pid に記録する設計（pid_file を受け渡し）。
    - プロセス優先度を高（"high"）に設定する処理を起動時に実行。

  - run_monitoring.py:
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず production 用 sqlite_path を使用する（監視は常に本番 DB を参照する設計）。
    - 停止フラグ検知でループを終了、KeyboardInterrupt をハンドリングしてクリーンに終了。

- 設定 / CLI
  - config.py:
    - 環境変数読み込み機能を実装（.env/.env.local 自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスで各種設定値（DB パス、KABUSYS_ENV、PAPER_FILL_MODE 等）をプロパティで提供し、値検証を行う。
  - config_setup.py:
    - 対話式ウィザードで .env を生成/更新する CLI を追加。秘密値のマスク表示、選択肢サポート、既存 .env の読み込みを行う。
  - validate_config.py:
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。必須環境変数チェック、パス存在チェック、YAML のパース検証（PyYAML がなくても実行）をサポート。--strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナル選択（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター比率が閾値を超える場合に新規候補を除外する。unknown セクターは上限適用対象外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。既知レジームはマッピング（bull/neutral/bear）、未知は 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py:
    - 発注株数計算（calc_position_sizes）を実装。allocation_method ("risk_based" / "equal" / "score") をサポート。単元株（lot_size）で丸め、ポジション上限や aggregate cap、cost_buffer（手数料・スリッページ緩和）を考慮したスケーリングを実装。

- ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定する共通セットアップを追加。ログディレクトリ自動作成、LOG_DIR / LOG_LEVEL による上書き、ファイルハンドラ障害時のフォールバックを実装。
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティを追加。set_cpu_affinity も提供。psutil の権限不足等は警告でスキップ。

- モニタリング / 検証ツール
  - monitoring.monitoring_db (初期化呼び出し):
    - run_* スクリプトから監視テーブル初期化を呼ぶことで冪等にテーブルを確保。
  - tools/paper_verification_report.py:
    - ペーパートレードの検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを報告し、閾値に基づく PASS/FAIL 判定を出力。P95 の計算、テーブルが存在しない場合の耐障害性（OperationalError を捕捉）を実装。

Changed
- ロギング挙動
  - StreamHandler を stdout に統一（cron/Task Scheduler の出力リダイレクトを考慮）。
  - 日次ローテーション（30日保持）を標準化。

- .env 自動ロード
  - プロジェクトルート検出は __file__ から親ディレクトリを遡り .git または pyproject.toml を基準とするよう変更。パッケージ配布後も CWD に依存せず動作する設計。

Fixed
- 環境変数の堅牢性向上
  - .env のクォート/エスケープ/コメント処理の改善により、特殊文字を含むトークン等の読み込み信頼性を向上。
- ポートフォリオ算出の丸め・スケーリング
  - 単元株（lot_size）での丸めと aggregate cap 超過時のスケーリングを実装して、発注額が available_cash を超えないように調整。

Notes / Migration
- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能。無効値（0 以下や非整数）を指定した場合はデフォルト 60 秒にフォールバックして警告が出力されます。

- 監視 DB の参照:
  - run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（監視用の本番 sqlite path）を使用します。監視目的で環境ごとに DB を切り替えたい場合は設定を見直してください。

- Paper Trading の分離:
  - 実行エンジンは paper_trading 環境で paper_sqlite_path（PAPER_TRADING_SQLITE_PATH 環境変数）を使用して本番データと完全に分離します。

- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN および KABU_API_PASSWORD は必須。validate_config で未設定やプレースホルダ値の検出が可能です。

- 依存:
  - process_priority, set_cpu_affinity 等は psutil に依存。権限不足や未インストール時は警告を出してスキップする設計です。
  - YAML の内容検証は PyYAML がある場合のみ実施されます。PyYAML がない場合は検証がスキップされ、警告が出ます。

Security
- なし（この差分からはセキュリティ修正は検出されていません）。

その他
- research/factor_research.py はファクター計算の設計方針と一部定数/関数のスケルトンを含むが、実装は一部未完（切り出し途中）。今後の実装で DuckDB を用いたファクター計算を完成させる予定。

参考
- 主要ファイル:
  - src/kabusys/run_execution.py, run_monitoring.py
  - src/kabusys/config.py, config_setup.py, validate_config.py
  - src/kabusys/portfolio/*.py
  - src/kabusys/utils/logging_setup.py, process_priority.py
  - src/kabusys/tools/paper_verification_report.py

もしリリース日やバージョン付けをファイルの作成日／別日付に合わせたい場合は日付を調整します。追加で「変更箇所ごとの詳細な説明」や「既知の制限事項」を追記することも可能です。どの形式で出力するか（Markdown ファイル、プレーンテキスト等）も指定してください。