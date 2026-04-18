# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
各リリースには主な追加・変更点、重要な挙動や環境変数の仕様を日本語で記載しています。

現在バージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
初回リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` としてリリース。

- 設定・環境読み込み
  - `kabusys.config.Settings` クラスを追加。環境変数を高レベル API として提供（例: `settings.env`, `settings.sqlite_path`, `settings.duckdb_path` など）。
  - 自動 `.env` ロード機能を実装：
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を読み込む。
    - OS 環境変数を保護して上書き制御を行う。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` のパースは `export KEY=val`、クォート文字列、インラインコメントの扱いなどをサポート。

- 対話型設定ウィザード
  - `kabusys.config_setup`：`.env` を対話的に作成/更新する CLI を追加。
  - デフォルト項目やシークレット表示・マスク、保存前の確認を実装。

- 設定検証 CLI
  - `kabusys.validate_config`：必須環境変数・KABUSYS_ENV の妥当性、DB パスの親ディレクトリ、config/*.yaml の存在と（PyYAML があれば）パース検証を行う。
  - `--strict` フラグで警告も失敗扱いにできる。

- 起動スクリプト
  - `kabusys.run_monitoring`：
    - SystemMonitor（監視ループ）を起動するスクリプト。
    - ポーリング間隔を `MONITOR_POLL_INTERVAL` 環境変数で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用する設計。
    - 停止フラグファイル (`data/stop_requested.flag`) の検出でループを終了。
  - `kabusys.run_execution`：
    - ExecutionEngine を起動するスクリプト。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper-trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / `settings.paper_sqlite_path`、デフォルト `data/paper_trading.db`）を使用し、本番 DB と物理的に分離。
    - 停止フラグおよび pid ファイル管理（`data/execution.pid`）に対応。
    - ブローカークライアントは `BrokerClientFactory.create(settings)` で取得し、paper/live を切り替え。

- 監視 DB 初期化
  - `init_monitoring_db` を呼び出して監視テーブルを冪等に初期化（監視・実行の両スクリプトで利用）。

- ロギング周り
  - `kabusys.utils.logging_setup.setup_logging` を追加：
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト `"INFO"`。
    - ログディレクトリ解決順: 引数 > 環境変数 `LOG_DIR` > デフォルト `logs/`。ディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - stdout を使うことで cron 等からの出力リダイレクト運用に適合。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority`：
    - `set_process_priority(level)`：Windows / POSIX を吸収して current process の priority (nice/HIGH_PRIORITY_CLASS 等) を設定。権限不足等は警告でスキップ。
    - `set_cpu_affinity(cpu_count)`：最初の N コアにプロセスをピン留め（未対応 OS や権限不足は警告でスキップ）。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio.portfolio_builder`：
    - `select_candidates`：スコア降順・タイブレークに signal_rank を用いる候補抽出。
    - `calc_equal_weights`, `calc_score_weights`：等金額配分 / スコア加重配分（全スコアが 0 の場合は等配分にフォールバックし WARNING）。
  - `kabusys.portfolio.risk_adjustment`：
    - `apply_sector_cap`：既存ポジションのセクター別エクスポージャを計算し、1 セクターあたりの上限比率（デフォルト 30%）を超えるセクターの新規候補を除外。`unknown` セクターは上限適用対象外。
    - `calc_regime_multiplier`：market regime に応じた投下資金乗数を返す（"bull"=1.0、"neutral"=0.7、"bear"=0.3）。未知のレジームは 1.0 にフォールバックして警告を出す。
  - `kabusys.portfolio.position_sizing`：
    - `calc_position_sizes`：allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。
      - risk_based: portfolio_value * risk_pct / (price * stop_loss_pct) に基づく算出と 1 銘柄上限・単元（lot_size）丸め。
      - equal/score: 各銘柄配分に基づく算出。
      - aggregate cap: 全銘柄合計投下金額が available_cash を超えた場合に保守的にスケールダウンし、lot_size 単位で端数調整を行う。
      - cost_buffer により手数料・スリッページ分を保守的に見積もる。

- 研究・ファクター計算の雛形
  - `kabusys.research.factor_research`：
    - Momentum、Value、Volatility、Liquidity 等を計算するための骨組みと定数を追加（DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計）。
    - モメンタム計算（mom_1m, mom_3m, mom_6m, ma200_dev）などを意図した実装方針が含まれる（ファイルは一部未完の箇所あり）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading の SQLite（デフォルト `data/paper_trading.db`）から集計レポートを出力する CLI。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算して PASS/FAIL を判定。
    - デフォルト判定閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from/--to）、DB パス指定（--db）をサポート。

- その他ユーティリティ
  - `kabusys.tools.__init__`、パッケージのエクスポート設定など。

### Changed
- （該当なし、初回リリース）

### Removed
- （該当なし、初回リリース）

### Fixed
- （該当なし、初回リリース）

### Notes / Important behavior
- run_monitoring は「環境にかかわらず」本番用の `settings.sqlite_path` を参照する設計です。監視データは環境分離されませんので運用時は注意してください。
- run_execution は `KABUSYS_ENV=paper_trading` のとき paper 専用 DB（デフォルト `data/paper_trading.db`）に書き込みます。本番 DB と完全分離される想定です。
- `.env` の自動読み込みはプロジェクトルートが特定できない（配布パッケージ化等）場合はスキップされます。その場合は明示的に環境変数を設定してください。
- process priority / cpu affinity の設定は OS 権限や環境に依存します。権限不足時は警告ログを出力してフォールバックします。
- ログ出力はデフォルトで stdout（コンソール）とファイル（日次ローテート）に行われますが、ログディレクトリの作成に失敗するとファイル出力を行わず stdout のみになります。

---

今後の改善候補（未実装・ TODO としてソース内に言及）
- position_sizing の lot_size を銘柄別に持てるようにする（stocks マスタ拡張）。
- apply_sector_cap の price 欠損時のフォールバック価格（前日終値や取得原価）を導入して過少見積もりを防ぐ。
- research.factor_research の一部未完実装を完成させる（ファイル末尾に未完の行が存在）。
- config/*.yaml の自動生成スクリプトや examples（scripts/generate_config.py の案内あり）。

（以降のリリースノートは本ファイルをアップデートして追加してください）