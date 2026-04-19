# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
リリース方針: 重要な機能追加・変更・修正を日本語で要約しています。

最新: 2026-04-19

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-19

Added
- 基本機能の初期実装を追加。
  - 実行・監視プロセス起動スクリプトを提供
    - run_execution: ExecutionEngine を起動するエントリポイント（src/kabusys/run_execution.py）。
      - KABUSYS_ENV=paper_trading のときは専用のペーパートレード用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全分離。
      - ブローカークライアントの抽象化（BrokerClientFactory）を導入し、テスト・ペーパーと本番の切り替えを容易に。
      - Engine を別スレッドで実行。data/stop_requested.flag による外部停止検知と PID ファイル記録（data/execution.pid）。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視用 DB は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計（監視データの一貫性確保）。
      - data/stop_requested.flag による停止検知。
  - 環境設定・読み込み関連
    - Settings クラス（src/kabusys/config.py）による環境変数のラップを提供。
      - デフォルト値、バリデーション（KABUSYS_ENV, LOG_LEVEL など）、パス解決（Path.expanduser）を実装。
      - PAPER_FILL_MODE の値検証、paper_sqlite_path / sqlite_path / duckdb_path 等のプロパティを公開。
      - is_live / is_paper / is_dev の便利プロパティを提供。
    - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。ロード順は OS 環境 > .env.local > .env。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサを強化（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメント処理など）。
    - config_setup 対話ウィザード（src/kabusys/config_setup.py）を追加。対話式に .env を作成・更新でき、シークレットはマスク表示。
    - 設定検証 CLI（src/kabusys/validate_config.py）を追加:
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証。
      - --strict モードで警告をエラー扱いにできる。
  - ロギング・プロセス管理ユーティリティ
    - 統一ロギングセットアップ関数 setup_logging を追加（src/kabusys/utils/logging_setup.py）。
      - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日分保持）をルートロガーに設定。
      - LOG_DIR 環境変数や引数でログディレクトリを制御。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - プロセス優先度・CPU affinity を抽象化するユーティリティを追加（src/kabusys/utils/process_priority.py）。
      - Windows / POSIX（Linux, Darwin, FreeBSD）に対応。psutil を利用し、優先度や CPU ピン留め設定を試みる。権限不足等は警告ログで安全にスキップ。
  - ポートフォリオ構築ライブラリ（pure function）
    - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
      - select_candidates, calc_equal_weights, calc_score_weights を実装。score が全て 0 の場合は等金額配分へフォールバックし警告ログを出力。
    - セクター上限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
      - apply_sector_cap: 既存保有を基にセクター集中度を算出し、上限超過セクターの新規候補を除外。unknown セクターは除外対象外。
      - calc_regime_multiplier: レジームラベル（bull/neutral/bear）に応じた乗数を返す（未知ラベルは 1.0 にフォールバックし警告）。
    - 発注株数計算（src/kabusys/portfolio/position_sizing.py）
      - calc_position_sizes: allocation_method = "risk_based" / "equal" / "score" をサポート。lot_size（単元）で丸め、ポートフォリオ上限・単銘柄上限・集約上限（available_cash）を考慮したスケーリングロジックを実装。cost_buffer（手数料等）を考慮した保守的計算を実装。
  - 研究用ファクター計算の骨組みを追加（src/kabusys/research/factor_research.py）。
    - モメンタム・移動平均・ATR・流動性などの指標計算方針と定数を定義。DuckDB 接続を通じて prices_daily / raw_financials を参照する設計を示す。
  - ユーティリティツール
    - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
      - 稼働率・注文成功率・送信率・API レイテンシ（P95） を算出し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）に基づき PASS/FAIL を出力。
      - --from / --to / --db オプションで期間・DB を指定可能。P95 計算や日付フィルタ組み立てを実装。

Changed
- 実行スクリプトの起動時にプロセス優先度を "high" に設定するように統一（run_execution, run_monitoring）。これによりリアルタイム性の確保を意図。
- 監視（monitoring）用 DB 初期化処理を冪等に実行（init_monitoring_db を呼んでテーブルの存在を保証）。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用することで、本番データと明確に分離する設計に変更。

Fixed
- .env の読み込み実装において、export プレフィックス・引用符付き値のエスケープ・インラインコメントの取り扱いを改善し、現実の .env ファイルに対する互換性を向上。
- logging_setup: ログディレクトリ作成失敗時でもプロセスがクラッシュしないようにフォールバック処理を追加。

Security
- .env 設定ウィザードで出力される .env ファイルに対して「絶対に Git にコミットしないこと」と明示的に指示（config_setup.py のヘッダ）。

Notes
- Settings._find_project_root() は __file__ を起点に .git や pyproject.toml を探索してプロジェクトルートを特定するため、パッケージ化後も CWD に依存せず動作する設計。ただし配布形態によっては検出できないケースがあり、その場合は自動 .env ロードをスキップします。
- 一部モジュール（研究用ファクター計算など）は設計方針と骨組みを提供しており、実装の拡張や追加のデータ品質チェックが今後の作業対象になります。

---

参考:
- 主要 CLI:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数の主なデフォルト:
  - KABUSYS_ENV: development
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_DIR: logs/
  - LOG_LEVEL: INFO

以上。