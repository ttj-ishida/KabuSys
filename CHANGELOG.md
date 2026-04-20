# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
バージョン番号はパッケージの __version__ に合わせています。

リリースノートはソースコードから推測して作成しています。実装上の仕様や既知の注意点も併記しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-20

### Added
- 基本的なアプリケーション構成・起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するメインスクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応。停止フラグ検出でエンジン停止。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用（監視は本番 DB を参照する設計）。
    - 停止フラグ検出でループを終了。
- 環境設定関連
  - config.py
    - .env 自動読み込み（プロジェクトルートの検出: .git / pyproject.toml を基準）。読み込み順は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パースの頑健化（export プレフィックス、クォート内のエスケープ、インラインコメント判定など）。
    - Settings クラスで各種環境変数アクセスを提供（DuckDB/SQLite パス、Paper Trading パス、各種閾値、env/log レベル判定等）。
    - PAPER_FILL_MODE の検証、有効値制約。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を提供。
    - 複数の設定項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。
    - 既存 .env の読み込み / マスク表示 / 保存確認機能を提供。
- 設定検証 CLI
  - validate_config.py
    - .env と config/*.yaml の妥当性チェックを実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加警告等。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 一貫したログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name による設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラのクリーンアップを行い二重設定を防止。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定するユーティリティ。
    - Windows / POSIX (Linux/Mac/FreeBSD) に対応。psutil を使用し、失敗時は警告を出してスキップ。
    - CPU affinity 設定関数 set_cpu_affinity を提供。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソート（スコア降順、同点は signal_rank によるタイブレーク）、候補選定、等金額・スコア加重配分ロジックを提供。
    - スコア総和が 0 の場合は等配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存ポジションのセクター別エクスポージャを計算し、max_sector_pct を超えるセクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に基づく投下資金乗数。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based, equal, score）。lot_size 単位丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケーリングと端数処理を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる。
- 研究／分析関連
  - research/factor_research.py
    - DuckDB 接続を受け取り各種ファクター（Momentum, Value, Volatility, Liquidity）を計算するモジュール骨子を追加。モメンタム等の定義（1M/3M/6M、MA200、ATR 等）を記載。
    - （注）ファイル末尾が未完の箇所があり、実装が途中であることを示唆。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポートを生成する CLI。
    - デフォルト DB は `data/paper_trading.db`。--from/--to/--db オプションをサポート。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し、しきい値に基づく PASS/FAIL 判定を行う。
    - デフォルトの閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

### Changed
- 初期リリース（0.1.0）として上記機能をまとめて追加。

### Fixed
- 初版のため既知の不具合修正履歴なし（以降のイテレーションで追記予定）。

### Notes / Known issues
- research/factor_research.py の末尾が未完（ソース内で途中 `start_da` のような断片があり実装継続が必要）。ファクター計算の完全な実装は今後の作業。
- apply_sector_cap の価格欠損時の取り扱い（price が 0.0 の場合にエクスポージャが過少見積になる可能性）が TODO コメントとして残っている。将来的にフォールバック価格を導入することを推奨。
- run_monitoring は「監視は本番 sqlite_path を使用する」設計になっているため、テスト環境で監視を動かす場合は sqlite_path の指定に注意が必要。
- .env の自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布パッケージ等で自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すること。

---

参照:
- パッケージバージョン: __version__ = "0.1.0" (src/kabusys/__init__.py)