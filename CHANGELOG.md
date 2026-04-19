CHANGELOG
=========

すべての注目すべき変更を記録します。Semantic Versioning に準拠します。
（フォーマット: Keep a Changelog — https://keepachangelog.com/ja/）

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- 全体
  - 初回公開リリース。KabuSys（日本株自動売買システム）の基本的な実行・監視・設定・ポートフォリオ構成ユーティリティ群を追加。

- 起動スクリプト
  - run_execution.py を追加（ExecutionEngine 起動スクリプト）。
    - KABUSYS_ENV による paper_trading 切替をサポート。paper_trading の場合は専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで起動。
    - プロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）が検知されたらエンジン停止処理を行う。
    - 起動時に PID ファイル（data/execution.pid）を利用。

  - run_monitoring.py を追加（SystemMonitor ポーリングループ起動スクリプト）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値は警告を出してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）によりループを終了。check_once() の例外はキャッチしてログに出力し次のポーリングに継続。

- 設定管理
  - config.py を追加。
    - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env パーサは export プレフィックス、クォート（シングル／ダブル）、エスケープ、インラインコメントに対応した堅牢な実装。
    - 環境変数保護（既存 OS 環境変数を上書きしない等）と自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。
    - Settings クラスを通じて型付きの設定アクセスを提供（トークン、DB パス、紙トレード設定、監視しきい値、KABUSYS_ENV／LOG_LEVEL の検証など）。

  - config_setup.py を追加（対話式 .env ウィザード）。
    - 対話で .env の初期作成・更新が可能。シークレット項目はマスク表示、デフォルト・選択肢をサポート。
    - 生成テンプレートは .env に書き込まれ、保存前に確認を行う。

  - validate_config.py を追加（設定検証 CLI）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DUCKDB/SQLITE のパス親ディレクトリチェック、config/*.yaml の存在と YAML パースチェック（PyYAML がある場合）。
    - KABUSYS_ENV=live の場合の追加警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の警告等）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理
  - utils/logging_setup.py を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティ。
    - 既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / 引数での上書きをサポート。

  - utils/process_priority.py を追加。
    - psutil を利用して Windows / POSIX（Linux/Mac/FreeBSD）の差分を吸収したプロセス優先度設定（"high"/"normal"/"low"）と CPU affinity 設定ユーティリティを提供。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。

- ポートフォリオ構成（純粋関数群）
  - portfolio/portfolio_builder.py を追加。
    - 候補選定（スコア降順・タイブレークロジック）、等配分・スコア加重配分関数を提供（calc_score_weights は全スコア 0 の場合に等配分へフォールバック）。

  - portfolio/risk_adjustment.py を追加。
    - apply_sector_cap: セクター集中上限をチェックして当該セクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告後フォールバック 1.0）。

  - portfolio/position_sizing.py を追加。
    - リスクベース／等配分／スコアベースの発注株数計算を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超えた場合のスケールダウンと端数補正ロジック）を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる。

  - portfolio/__init__.py で上記 API を公開。

- ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH または --db）から検証指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など）を集計してレポート出力。
    - デフォルト閾値を定義し、PASS/FAIL 判定を表示。日付フィルタ（--from/--to）をサポート。
    - P95 計算、欠損データの扱い（N/A）の実装あり。

- リサーチ（開発中）
  - research/factor_research.py を追加（モメンタム等ファクター計算の骨組み）。
    - DuckDB の prices_daily / raw_financials を参照して各種ファクター（モメンタム、MA200乖離、ATR、流動性等）を算出する設計ノートと定数群を実装。関数の実装は継続中（ファイル末尾で未完の状態あり）。

Changed
- ロギング設計
  - コンソール出力は stdout を使用するよう明示（cron 等からのリダイレクトを想定）。
  - 既存ハンドラをクリーンに削除してから再設定することで二重出力を防止。

Fixed
- データベース初期化の冪等性
  - 起動スクリプト（実行／監視）で init_monitoring_db(sqlite_conn) を呼び、監視テーブルが存在することを保証（既存の場合は安全にスキップ）。

Notes
- 停止制御
  - 両スクリプトとも data/stop_requested.flag により外部から安全に停止できるよう設計（運用上の Kill Switch）。
  - KILL_FLAG_CLEAR_ON_START の設定は本番での危険性を validate_config が警告する。

- セキュリティ
  - .env は生成テンプレートで「絶対に Git にコミットしないこと」を明示。機密値はウィザードでマスク表示。

- 既知の未実装 / 今後の作業
  - research/factor_research.py の続き（calc_momentum 等の完全実装）。
  - ブローカークライアントや ExecutionEngine の外部依存（BrokerClientFactory, ExecutionEngine 本体など）は本リリースで参照されているが、詳細実装・統合テストの反映が必要。

Security
- なし（特記事項なし）

=========
変更点の説明や意図、運用上の注意点について詳しい説明が必要ならお知らせください。