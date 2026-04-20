CHANGELOG.md
=============

すべての注目すべき変更はここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-20
--------------------

Added
- 初回リリースを追加。
- パッケージのバージョンを `kabusys.__version__ = "0.1.0"` に設定。

- 環境設定・ロード
  - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env パーサとローダーを実装し、`export KEY=val`、クォート、インラインコメント等に対応。
  - 環境変数の優先順位: OS 環境変数 > .env.local > .env（`KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可）。
  - Settings クラスを実装してアプリケーション設定を集中管理（J-Quants、kabuAPI、DBパス、Paper Trading 設定、監視閾値、KABUSYS_ENV 検証など）。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を作成 / 更新する `kabusys.config_setup` を追加。
    - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DBパス、LINE トークン等）。
    - 既存 .env の読み取り・マスク表示・保存テンプレート生成機能。
  - validate_config: 起動前の設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認。
    - config/*.yaml の存在確認および PyYAML が利用可能な場合はパース検査。
    - 本番 (live) 向けの追加ガード（LINE 設定確認、KILL_FLAG_CLEAR_ON_START 警告）。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行・監視エントリポイント
  - run_execution: `run_execution.py` により ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine をデーモンスレッドで実行し、data/stop_requested.flag により安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行 PID を data/execution.pid に出力（Engine 側の PID ファイルパス対応）。
  - run_monitoring: `run_monitoring.py` により SystemMonitor のポーリングループを追加。
    - 環境にかかわらず（paper / development / live いずれでも）本番用 sqlite_path を使用して監視 DB を扱う仕様。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化・DuckDB 統合
  - 監視テーブルの初期化を担う init_monitoring_db 呼び出しを run_* で行い冪等にテーブル存在を保証。
  - DuckDB 接続を受けて分析用に利用する設計を導入（duckdb_path 設定）。

- ロギング・プロセス管理ユーティリティ
  - logging_setup: ルートロガーに StreamHandler(stdout) と日次ローテートの TimedRotatingFileHandler を設定するユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。
    - stdout を利用することで cron 等からのリダイレクトを容易に。
  - process_priority: psutil を用いたクロスプラットフォームのプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を追加。
    - Windows / POSIX の差分を吸収し、アクセス権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソート（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等配分 / スコア重み配分（全スコア 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限適用（既存保有のセクター比率に基づき新規候補を除外）。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームはフォールバック 1.0。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく株数計算実装。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、投下資金の aggregate cap、cost_buffer を使った保守的見積り、スケールダウンと端数配分ロジックを実装。
    - 不足データ（価格欠損等）ではログとともにスキップ。

- Paper Trading 検証ツール
  - tools/paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、レイテンシ（avg, max, P95）を集計してレポート出力。
    - PASS/FAIL 判定の閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）。
    - 日付範囲フィルタ（--from / --to）と --db オプションをサポート。

- 研究用ファクター計算（DuckDB）
  - research/factor_research: ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算の基盤（定数、calc_momentum の冒頭実装）を追加（実装は継続中、DuckDB 統合を前提）。

Security / Privacy
- config_setup にてシークレット項目はマスク表示。
- .env テンプレート生成時に「.env を Git にコミットしないこと」を明示。

Notes / Implementation details
- run_monitoring は MONITOR_POLL_INTERVAL の不正値に対して警告しデフォルト値にフォールバックする健全性処理を実装。
- run_execution は停止フラグ検出時に ExecutionEngine.stop() を呼んで安全停止を試み、スレッドの join を行う設計。
- logging_setup は既存ハンドラを flush/close してから再設定することで二重ハンドラ登録を防止。
- process_priority は権限不足や未対応 OS の場合に警告して処理を継続（例: コンテナや一部環境での graceful フォールバック）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Authors
- KabuSys コードベース（初期実装一式）

---

注: この CHANGELOG は提供されたソースコードから推測して作成したものです。各項目の文言は実装の意図やコメントを基にまとめています。実際のリリースノート作成時は変更差分（git のコミット履歴）やリリース管理方針に合わせて調整してください。