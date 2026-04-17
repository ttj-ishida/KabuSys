CHANGELOG
=========

すべての重要な変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

0.1.0 - 2026-04-17
-----------------

Added
- 初期リリース: 基本的な自動売買フレームワークとユーティリティ群を追加。
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 に設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視用 DB 初期化（init_monitoring_db）を行い、duckdb へも接続。停止フラグファイル (data/stop_requested.flag) を監視して安全終了。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）して本番 DB と分離。MockBrokerClient の利用を想定。
    - BrokerClientFactory を通してブローカークライアントを生成。OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) と実行用 pid ファイルの取り扱い、停止時の安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境管理
  - src/kabusys/config.py
    - .env 自動ロード機能を追加（プロジェクトルートの探索: .git または pyproject.toml を起点）。
    - ロード順: OS環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export 形式・クォート・エスケープ・インラインコメントに対応。
    - Settings クラスを導入し、環境設定をプロパティ経由で取得。多くの既定値とバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を提供。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や監視しきい値（CPU/MEM/DISK）等の設定をプロパティで提供。

  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成または更新する CLI を追加（python -m kabusys.config_setup）。
    - デフォルト/既存値の再利用、シークレットマスク表示、保存確認、.env のテンプレート出力をサポート。

  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加（--strict オプションで警告を FAIL 扱いに可能）。
    - 必須環境変数のチェック、KABUSYS_ENV の検証、DB パスの親ディレクトリ検査、YAML ファイルの存在・パース検査（PyYAML がインストールされていない場合は警告）、本番環境向けの追加ガードを実装。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等重み calc_equal_weights、スコア重み calc_score_weights を実装。スコア全零時のフォールバックロジックを含む。

  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックにより候補を除外するロジックを実装。売却予定銘柄をエクスポージャー計算から除外できる。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームは警告とともに 1.0 にフォールバック。

  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 等配分・スコア・リスクベースの株数決定ロジックを実装。lot_size 単位丸め、per-stock 上限、aggregate cap（available_cash 超過時のスケーリングと端数調整）を含む。
    - cost_buffer による手数料/スリッページ考慮、価格欠損時のスキップなどの安全策を備える。

- 監視・実行ユーティリティ
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度および CPU affinity を設定するユーティリティを追加（psutil を利用）。
    - 権限不足や未対応 OS では警告を出してスキップする設計。

- 研究用ファクター計算
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算。
    - calc_volatility: ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算する土台を実装。
    - 「prices_daily」テーブルのみを参照し外部 API への依存を持たない設計。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite データベースから検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、リスク却下数、P95 レイテンシなどの指標を算出し、しきい値に基づく PASS/FAIL 判定を出力。
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH / data/paper_trading.db。期間指定オプション（--from / --to）あり。

Changed
- なし（初回公開のため、既存機能の変更履歴はありません）。

Fixed
- なし（初回公開のため、バグ修正の履歴はありません）。

Notes / 実装上の注意
- 監視ループ（run_monitoring）は KABUSYS_ENV にかかわらず monitoring 用の sqlite_path を使用する点に注意（設計的に本番監視 DB を参照する仕様）。
- Execution 起動時は is_paper 判定により paper_trading 用 DB・Mock ブローカーを利用し、本番データと分離する設計を採用。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後にプロジェクトルートが失われている環境では自動ロードをスキップします。
- process_priority / set_cpu_affinity は psutil に依存。環境により権限不足や未対応 OS の場合はログに警告を出して処理をスキップします。
- 一部関数（research の一部 SQL 等）は連結された DuckDB テーブル構造や外部データに依存します。実際の運用前に validate_config や config_setup で設定を確認してください。