CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーションおよびユーティリティ群を追加（初期リリース）。
  - パッケージ情報
    - パッケージバージョンを設定: __version__ = "0.1.0"。
  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き機能（デフォルト: 60秒）。
      - 停止フラグファイル（data/stop_requested.flag）検知による安全終了。
      - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）と MockBrokerClient を使用し、本番 DB と分離。
      - 停止フラグ（data/stop_requested.flag）および PID 管理（data/execution.pid）に対応。
      - デーモンスレッドでエンジンを実行し、フラグ検知で安全停止。
  - 設定管理
    - config.py
      - .env の自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パースの堅牢化（export 形式、クォート、インラインコメント処理など）。
      - Settings クラスで各種環境変数をラップ（J-Quants、kabuステーション、DB パス、監視閾値、環境種別フラグなど）。
      - Paper Trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）と検証。
    - config_setup.py
      - 対話式 .env 作成・更新ウィザードを追加。既存 .env 読み込み、シークレットマスク表示、保存確認、.env の書き出し機能を提供。
    - validate_config.py
      - 起動前の設定検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスや config/*.yaml の存在・パース確認、live 環境向け追加ガードを実装。
      - --strict オプションで警告を失敗扱いにできる。
  - ログ / プロセス管理ユーティリティ
    - utils/logging_setup.py
      - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通セットアップを提供。
      - ログディレクトリ自動作成（失敗時はファイル出力をスキップして stdout のみで継続）。
      - ログレベル / ログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
    - utils/process_priority.py
      - プラットフォーム差分を吸収したプロセス優先度設定（Windows の優先度クラス / POSIX の nice 値）。
      - CPU affinity を最初の N コアに固定する機能（設定可、未サポート環境では警告を出してスキップ）。
      - 権限不足や未対応環境で安全にフォールバックする設計。
  - ポートフォリオ構築関連（純粋関数群）
    - portfolio/portfolio_builder.py
      - 銘柄候補選定（select_candidates: スコア降順、タイブレークに signal_rank）。
      - 等分配（calc_equal_weights）／スコア加重（calc_score_weights、全スコアが 0 の場合は等分配にフォールバック）を提供。
    - portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap: 既存保有のセクター時価比で上限を判定し、新規候補を除外）。
      - 市場レジームによる乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知は警告とともに 1.0 フォールバック）。
    - portfolio/position_sizing.py
      - 発注株数決定ロジック（allocation_method: "risk_based" / "equal" / "score" をサポート）。
      - 単元株（lot_size）丸め、1銘柄上限・総投下資金上限（max_position_pct, max_utilization）、コストバッファを考慮した aggregate cap のスケーリングと端数処理。
      - price 欠損時のスキップ、利用可能現金を超える場合のスケールダウンと残差配分を実装。
    - portfolio/__init__.py
      - 主要関数をパッケージレベルでエクスポート。
  - 研究／ツール
    - research/factor_research.py（実装開始）
      - DuckDB 経由で定量ファクター（Momentum, Value, Volatility, Liquidity）を計算するモジュールを追加（モメンタム関数のインターフェースと定数群を実装中。ファイル末尾で実装未完の箇所あり）。
    - tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成スクリプトを追加。
      - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計し、閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を出力。
      - DB パスの引数／環境変数オーバーライド対応（--db、PAPER_TRADING_SQLITE_PATH）。
  - データベース周り
    - run_* スクリプトから監視テーブルの初期化（init_monitoring_db）を呼び出して起動時の冪等な整備を行う設計（監視用 SQLite と分析用 DuckDB の併用）。
  - その他
    - 停止フラグ（data/stop_requested.flag）や kill/ pid ファイルの扱いを統一して、安全運用を支援。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 限界・今後の改善点（コードから推測）
- research/factor_research.py は実装途中に見える箇所があり、完全なファクター計算は追加実装が必要。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価など）は TODO コメントあり。将来の拡張候補。
- apply_sector_cap は "unknown" セクターを上限チェックから除外する仕様。必要に応じて扱いを見直す可能性あり。
- ログディレクトリ作成やプロセス優先度設定は権限や環境に依存するため、運用時に動作確認が必要。

ライセンスや互換性、デプロイ手順等は別途ドキュメントを参照してください。