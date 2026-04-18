CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__ を基にしています。

Unreleased
----------

- なし

0.1.0 - 2026-04-18
------------------

Added
- 基本アプリケーション構成を初期リリースとして追加。
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - stop_requested.flag による外部停止フラグ監視。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading SQLite DB を使用（本番 DB と完全分離）。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て、エンジンのデーモン起動。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env/.env.local の読み込みロジック（OS 環境変数の保護、上書きルール）。
    - .env 行パーサを実装（export プレフィックス、クォート文字列、インラインコメント処理に対応）。
    - Settings クラスを追加し、環境変数を型付プロパティとして提供（J-Quants、kabu API、DB パス、監視閾値、環境モード判定など）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 環境値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。

- 設定ユーティリティ / CLI
  - config_setup.py:
    - 対話式 .env 作成・更新ウィザードを追加。
    - デフォルト値とシークレット入力、選択肢、既存 .env の読み込み・再利用に対応。
    - 書き込みテンプレート: DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START 等を出力。
  - validate_config.py:
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）や config/*.yaml の存在確認（PyYAML があればパース検証）。
    - KABUSYS_ENV=live の際の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict モードで警告も失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py:
    - 統一ログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py:
    - プラットフォーム差分を吸収したプロセス優先度設定を実装（Windows, POSIX 対応）。
    - CPU affinity 設定ユーティリティ set_cpu_affinity を追加。
    - 権限不足など失敗時は警告ログを出してスキップ。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）: スコア降順・タイブレークに signal_rank を使用。
    - 重み計算: 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア合計が 0 の場合は等分にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）: 既存保有のセクター別エクスポージャーを計算して上限超過セクターの候補を除外。
    - レジーム乗数（calc_regime_multiplier）: market レジームに応じて投下資金乗数を返す（bull/neutral/bear）。
  - portfolio/position_sizing.py:
    - ポジションサイズ計算（calc_position_sizes）: risk_based / equal / score の各方式に対応。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate cap（available_cash）を考慮したスケーリング、コストバッファを考慮。
    - スケールダウン時に残差ロジックで再配分する実装を追加。

- 分析ツール / レポート
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを算出。
    - CLI オプション: --from / --to（期間指定）、--db（DB パス上書き）。PAPER_TRADING_SQLITE_PATH 環境変数でデフォルト DB を指定可能。
    - 基準値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200 ms）で PASS/FAIL 判定。

- リサーチ / ファクター計算（着手）
  - research/factor_research.py:
    - モメンタム等のファクター計算モジュールの骨格を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照して各種ファクターを算出する設計（モジュールは途中まで実装）。

Changed
- 既存の DB 初期化処理（監視テーブル確保）の呼び出しを実装場所に追加（init_monitoring_db を使用し冪等に保証）。

Fixed
- （初期リリース）.env パーサと読み込みによりクォートや export、インラインコメント周りの扱いを明確化し、環境変数の誤読を軽減。

Notes / Internal
- run_monitoring と run_execution はそれぞれ起動直後にプロセス優先度を "high" に設定しますが、権限不足や対応しない OS 環境では警告を出してスキップします。
- Logging は stdout を利用する設計（cron 等からのリダイレクト運用を想定）。
- config.py の自動ロードはテスト用途などで KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
- position_sizing のロジックは単元株共通（lot_size 固定）を前提としているため、将来的に銘柄別 lot_size を導入する余地あり（TODO コメントあり）。
- research/factor_research.py はファイル末尾で途中（start_da... で切れている）ため、完全実装は今後の作業対象。

Security
- .env ファイルは生成時にコミット禁止を明示（config_setup のヘッダに注意書き）。機密トークンは .env に保存する設計のため、取り扱いに注意してください。

Acknowledgements
- この CHANGELOG はリポジトリに含まれるソースコードから推測して作成しています。実際のコミット履歴やリリース計画がある場合はそちらに合わせて更新してください。