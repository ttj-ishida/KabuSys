CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。

Unreleased
----------

なし

0.1.0 - 2026-04-24
------------------

Added
- 基本パッケージ初期実装を追加。
  - src/kabusys/__init__.py にパッケージメタ（__version__ = "0.1.0"）を追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト data/stop_requested.flag ファイルで検知。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する実装。
    - monitoring 用 DB 初期化 (init_monitoring_db) と DuckDB 接続を実行。
    - プロセス優先度を "high" に設定して起動。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の依存コンポーネントを組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル管理、スレッドでの実行／停止制御を実装。

- 設定管理・検証・ウィザード
  - config.py
    - Settings クラスを実装し、環境変数から各種設定をラップ。バリデーションやデフォルト処理を提供。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml 基準）。.env → .env.local の順で読み込み（.env.local は上書き、既存 OS 環境変数は保護）。
    - .env パースは export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
    - PAPER_FILL_MODE の有効値検証や KABUSYS_ENV / LOG_LEVEL の検証など、詳細なプロパティを実装。
  - config_setup.py
    - .env 初期作成・更新の対話式ウィザードを追加（秘密項目のマスク表示、選択肢、デフォルト値サポート）。
    - 書き込みされる .env テンプレートと注意書きを自動生成。
  - validate_config.py
    - 起動前に環境変数および config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリの存在チェック、YAML ファイルの存在／パース検証（PyYAML があればパースまで実施）を提供。
    - --strict オプションで警告を FAIL 扱いにするモードを追加。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - すべての起動スクリプトで共通利用できるログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler、30日保持）のファイルハンドラをルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name による解決ロジックを実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）と CPU affinity 固定機能を追加。
    - Windows (psutil の priority constants) と POSIX 系 (nice 値) を吸収してクロスプラットフォームに対応。アクセス権限不足時は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有を考慮して特定セクターの新規候補を除外する挙動。
    - "unknown" セクターは上限チェックの対象外とする挙動を実装。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based", "equal", "score"）。
    - lot_size 単位での丸め、1銘柄上限・aggregate cap（利用可能現金によるスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮したスケーリングと余りの再配分ロジックを実装。

- 研究用モジュール
  - research/factor_research.py
    - ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 経由で prices_daily / raw_financials を参照する設計。モメンタム計算の骨子が実装されている（実装途中の場所あり）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB（PAPER_TRADING_SQLITE_PATH 指定可）から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数等を集計し PASS/FAIL を判定するしきい値を定義。
    - --from / --to / --db オプションで期間・DB 指定が可能。

- モジュールエクスポート
  - portfolio パッケージ __init__ に各関数をエクスポートし、上位から簡単に利用できるようにした。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Notes / Implementation details
- DB 初期化: run_monitoring/run_execution では監視用テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等）。
- .env 自動ロードはデフォルトで有効だが、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- ロギング設定は起動時に setup_logging(app_name=...) を呼ぶことで統一的に適用できる。
- process_priority.set_process_priority は権限不足や未サポート OS の場合に安全にスキップする（警告ログ）。

Security
- .env ファイルは生成スクリプトで注意喚起を出し、絶対に Git にコミットしないようドキュメントに記載。

Future / TODO（コード内コメントに基づく）
- position_sizing: 銘柄ごとの lot_size をサポートするための拡張（stocks マスタ参照）を検討中。
- risk_adjustment: price 欠損時のフォールバック価格（前日終値等）を用いる改善の検討。
- research/factor_research: 実装の続きを完了し、Value/Volatility/Liquidity 等のファクター算出ロジックを完成させる。

-----

注: 上記は提供されたコードの内容から推測して記載した CHANGELOG です。実際のコミット履歴やリリースノートと差異がある場合があります。必要に応じて日付・表現の調整や追記を行ってください。