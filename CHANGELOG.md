KEEP A CHANGELOG 準拠 — CHANGELOG.md

All notable changes to this project will be documented in this file.

フォーマット:
- 変更は "Added", "Changed", "Fixed" などのセクションで分類しています。
- 日付は YYYY-MM-DD 形式。

Unreleased
---------
（現在なし）

[0.1.0] - 2026-04-17
-------------------
初回リリース。

Added
- 基本情報
  - パッケージバージョンを 0.1.0 として導入 (src/kabusys/__init__.py)。
  - コマンドライン実行可能モジュールやユーティリティ群を追加。

- 設定・環境変数管理
  - Settings クラスを追加して、環境変数経由のアプリ設定を集中管理（src/kabusys/config.py）。
    - J-Quants / kabuステーション / LINE / DB / 監視 / システム関連のプロパティを提供。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証を実装（有効値チェック）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE のバリデーションを実装。
  - 自動 .env ロード機能を追加:
    - プロジェクトルート（.git または pyproject.toml）を探索して .env を自動読み込み。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。

- .env パーサ／ウィザード
  - 高機能な .env パース実装を追加（引用符、export 形式、インラインコメントの取り扱いに対応）。
  - 対話式環境設定ウィザード (python -m kabusys.config_setup) を追加：
    - .env の初期作成／更新を支援。テンプレート出力と保存機能あり（src/kabusys/config_setup.py）。

- 設定検証 CLI
  - validate_config CLI を追加 (python -m kabusys.validate_config)：
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実行。
    - --strict オプションで警告を FAIL 扱いにできる（exit(1)）。

- 実行エンジン／監視の起動スクリプト
  - ExecutionEngine 起動スクリプトを追加 (src/kabusys/run_execution.py)：
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカクライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、Engine のスレッド起動と停止フラグ検知による安全停止処理を実装。
  - SystemMonitor ポーリングループ起動スクリプトを追加 (src/kabusys/run_monitoring.py)：
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（明示的な運用ポリシー）。

- 監視 DB 初期化 / duckdb 連携
  - monitoring_db 初期化呼び出しを組み込み（起動時に監視テーブルが存在することを保証）。
  - DuckDB 接続を必要とするモジュールを考慮して duckdb への接続処理を導入。

- プロセス制御ユーティリティ
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（psutil ベース、クロスプラットフォーム考慮）（src/kabusys/utils/process_priority.py）。
    - Windows/Linux(Mac 等) の差分を吸収。権限不足や未サポート環境では安全にスキップして警告を出力。
    - set_cpu_affinity により最初 N コアにピン留め可能（引数 None で無効）。

- ポートフォリオ構築モジュール
  - 銘柄選定・重み付け（portfolio_builder）を追加：
    - select_candidates（スコア降順、signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights（合計スコアが 0 の場合は等金額配分へフォールバック）。
  - セクター集中制限・レジーム乗数（risk_adjustment）を追加：
    - apply_sector_cap（既存保有を考慮してセクター上限を超える場合に候補を除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" のマッピングと未知値時のフォールバック）。
  - 株数決定・リスク制限・単元丸め（position_sizing）を追加：
    - calc_position_sizes：allocation_method に応じた発注株数計算 (risk_based / equal / score)。
    - lot_size 単位で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap のスケーリングと残余分配ロジックを実装。

- リサーチ（ファクター計算）
  - factor_research モジュールを追加（DuckDB 接続を受ける純粋関数群）：
    - calc_momentum：1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility：20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - 営業日ウィンドウとカレンダーバッファの取り扱い、欠損時の None 返却仕様を明示。

- ペーパートレード検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）を追加：
    - Paper Trading の検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定（デフォルト閾値をソース内で定義）。
    - --from / --to / --db オプションに対応、P95 計算ロジック実装。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- .env のパースにおける引用符内のエスケープ処理、export プレフィックス、インラインコメントの取り扱いなどを考慮する実装で堅牢化（src/kabusys/config.py）。
- process_priority / cpu_affinity は権限不足や未対応プラットフォームにおいて例外が飛ばないようログ警告に変換して安全化。

Notes / 運用上の注意
- 監視は明示的に本番 sqlite_path を使用する設計です（run_monitoring は KABUSYS_ENV に依存せず本番 DB を参照します）。ペーパートレードと監視 DB を分離したい場合は設定の調整が必要です。
- MONITOR_POLL_INTERVAL は環境変数で上書き可能（整数 1 以上）。0 以下や非整数は無効で、デフォルト 60 秒にフォールバックします。
- KILL_FLAG_CLEAR_ON_START が本番環境で 1 に設定されると危険（validate_config で警告が出ます）。
- .env ファイルは決してリポジトリにコミットしないでください（config_setup のヘッダにも注意書きを出力）。
- 一部機能は psutil (プロセス設定) や duckdb, sqlite3 を利用します。実行環境にこれらがインストールされていることを確認してください。

使用例（CLI）
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証:   python -m kabusys.validate_config [--strict]
- 監視開始:   python -m kabusys.run_monitoring
- エンジン起動: python -m kabusys.run_execution
- ペーパーレポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

今後の予定（例）
- 銘柄毎の lot_size 対応（stocks マスタからの読み取り）
- リスク算出時の価格フォールバック（price_map 欠損時の改善）
- ExecutionEngine / SystemMonitor のより詳細なログ・メトリクス出力

--------------------------------
この CHANGELOG はコードベースから推測して作成しています。必要に応じて日付・分類・記述をプロジェクト実情に合わせて編集してください。