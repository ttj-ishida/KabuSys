CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
リリース日はパッケージ内のバージョンに合わせて付与しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーション構成を実装（初期公開）。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。
- 環境設定・読み込み
  - .env ファイルの自動読み込み機能を実装。読み込み順は OS 環境変数 > .env.local > .env。
  - 読み込みロジックは、`export KEY=val` 形式、シングル/ダブルクォート、エスケープ、インラインコメントなどの実用的なパースに対応。
  - 自動読み込みを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `Settings` クラスを追加し、各種設定プロパティ（J-Quants トークン、kabu API、DB パス、Paper Trading 設定、監視閾値、実行環境判定など）を環境変数から取得・検証。
  - `PAPER_FILL_MODE` の有効値チェック（"instant" | "partial" | "never" | "reject"）を実装。
  - `KABUSYS_ENV` は "development" / "paper_trading" / "live" のみ許容。

- 環境設定支援ツール
  - 対話式ウィザード `kabusys.config_setup` を追加。`.env` の初期作成・更新を支援。
  - シークレット項目はマスク表示、デフォルト・選択肢、保存前の確認画面を提供。
  - `.env` ファイルの読み書きユーティリティを含む。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。必須環境変数の未設定、`KABUSYS_ENV` / `LOG_LEVEL` の不正値、DB パスの親ディレクトリ存在確認、`config/*.yaml` の存在確認と（PyYAML があれば）パース検証を行う。
  - `--strict` オプションで警告を失敗として扱う。

- 実行系スクリプト
  - `run_execution.py` を追加（ExecutionEngine 起動スクリプト）。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用して paper_trading 専用 SQLite（`PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）に記録し、本番 DB と分離。
    - 起動時にプロセス優先度を高く設定（`set_process_priority("high")`）。
    - BrokerClientFactory 経由で broker を生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて `ExecutionEngine` をスレッドで起動。
    - 停止フラグ（`data/stop_requested.flag`）検知で安全に停止。
    - PID ファイルの取り扱い（`data/execution.pid` を渡す）。

- 監視系スクリプト
  - `run_monitoring.py` を追加（SystemMonitor ポーリングループ起動スクリプト）。
    - 環境に関わらず monitoring は設定の sqlite_path（本番用パス）を使用して監視 DB を初期化。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告ログを出力。
    - 停止フラグ検知でループを終了。KeyboardInterrupt をハンドリングしてクリーンアップ。

- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup` を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ファイルハンドラ作成失敗時はコンソール出力のみで継続。
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX の差分を吸収してプロセス優先度を設定する `set_process_priority`。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity`。
    - 権限不足や未対応 OS の場合は警告ログを出し安全にスキップ。

- ポートフォリオ構築モジュール
  - `kabusys.portfolio` 以下を追加（純粋関数群、DB参照なし）。
    - portfolio_builder:
      - `select_candidates`: スコア降順・同点は signal_rank でタイブレークして上位 N を選定。
      - `calc_equal_weights` / `calc_score_weights`: 等金額・スコア加重配分。スコア合計が 0 の場合は等配分へフォールバック（警告）。
    - risk_adjustment:
      - `apply_sector_cap`: 既存保有のセクター比率が閾値を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
      - `calc_regime_multiplier`: 市場レジームに基づく投下資金倍率（bull/neutral/bear -> 1.0/0.7/0.3）。未知レジームは 1.0 にフォールバック（警告）。
    - position_sizing:
      - `calc_position_sizes`: allocation_method に応じた発注株数決定（"risk_based" / "equal" / "score"）。
      - 単元（lot_size）丸め、1 銘柄上限、利用可能現金に基づく aggregate cap スケーリング、スケーリング後の残余配分ロジックを実装。
      - cost_buffer（手数料・スリッページ見積り）を使った保守的コスト見積り。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - ペーパートレード用 SQLite（環境変数または CLI --db）からメトリクスを集計。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出して PASS/FAIL 判定（しきい値はソース内に定義）。
    - P95 の算出、期間フィルタ、DB 存在チェック、SQL の例外をハンドリングして堅牢に動作。

- 研究用ファクター計算スケルトン
  - `kabusys.research.factor_research` を追加。Momentum / Value / Volatility / Liquidity 等のファクター設計方針と計算用ユーティリティ（DuckDB 接続想定）の骨組みを実装。momentum 計算関数の実装開始（ファイル末尾は途中）。

Changed
- （このリリースは初期公開のため該当なし）

Fixed
- （このリリースは初期公開のため該当なし）

Deprecated
- （なし）

Removed
- （なし）

Security
- 環境変数やシークレットの扱いに注意して設計。`.env` は絶対に Git にコミットしない旨を config_setup のヘッダに明記。

Notes / 補足
- DB 周り
  - DuckDB は分析用（prices_daily 等のクエリ想定）、SQLite は監視・発注履歴用に使用する設計。
  - `run_execution` は paper_trading モードで paper 専用 SQLite を使い、本番データと完全分離する。
  - `init_monitoring_db` を各起動経路で呼び出して監視テーブルの存在を保証（冪等）。

- 停止制御
  - 各種スクリプトはプロジェクトルートの `data/stop_requested.flag` を監視して安全に停止する仕組みを採用。

- ログ
  - コンソールは stdout に出力することで外部ランナー（cron 等）でのログ集約を想定。

今後の予定（例）
- research.factor_research の各ファクターの完全実装。
- ExecutionEngine / SystemMonitor の詳細なユニットテストと負荷試験。
- 銘柄毎の lot_size をマスタで管理する拡張（現在は全銘柄共通の lot_size 想定）。
- 発注・約定ロジック（BrokerClient）の追加実装とテストカバレッジ拡充。