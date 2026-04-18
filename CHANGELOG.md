# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
※このCHANGELOGは与えられたコードベースの内容から推測して作成しています。

All notable changes to this project will be documented in this file.

---

## [0.1.0] - 2026-04-18

### Added
- 初期リリースを追加。
- 実行・監視用起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、スレッドでエンジンを実行。停止フラグ (data/stop_requested.flag) を検知して安全に停止。
    - 実行用 PID ファイル (data/execution.pid) の扱いを想定。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の値はデフォルトにフォールバックして警告。
    - 停止フラグ (data/stop_requested.flag) の検知でループを終了。
    - Monitoring は環境に関係なく本番で想定する sqlite_path を使用する仕様。

- 設定管理・ウィザード・検証ツールを追加
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出を行い `.env` → `.env.local` の順で読み込み。OS 環境変数は保護され上書きされない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env の行パースで `export KEY=val`、引用符付き値、バックスラッシュエスケープ、インラインコメント処理等に対応する堅牢な実装。
    - Settings クラスにより各種環境変数をプロパティとして提供（J-Quants、kabuAPI、LINE、DB パス、監視閾値、環境判定など）。
    - `paper_fill_mode` の値検証（"instant", "partial", "never", "reject" のみ許可）。
  - config_setup.py
    - 対話式 `.env` ウィザードを提供。既存 .env の読み込み・表示、マスクされた秘密情報表示、保存時の確認、.env ファイルへの書き込みロジックを実装。
    - 項目例: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の不備を検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML があれば実施）など。
    - `--strict` オプションで警告を失敗と見なすモードを提供。
    - live 環境向けの追加ガードチェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性提示）。

- ロギング / プロセス制御ユーティリティを追加
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通ユーティリティ。
    - LOG_LEVEL / LOG_DIR / 引数での上書き、ログディレクトリ作成失敗時のフォールバック等に対応。
    - stdout を利用することで cron 等からのリダイレクト運用に配慮。
  - utils/process_priority.py
    - psutil を用いてクロスプラットフォーム（Windows / POSIX）でプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップする堅牢性を実装。

- ポートフォリオ構築用モジュールを追加
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順タイブレーク処理）select_candidates。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコア 0 の場合は等配分へフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（既存ポジション・当日売却予定を考慮）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear に対応、未知レジームはフォールバックして警告）。
  - portfolio/position_sizing.py
    - 各種配分方式（risk_based / equal / score）に基づく株数計算 calc_position_sizes。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、残余キャッシュ配分アルゴリズム（fractional remainder に基づく追加配分）を実装。

- 研究用ファクター計算モジュールを追加（部分実装）
  - research/factor_research.py
    - DuckDB 接続を受けて prices_daily / raw_financials 等から Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計。
    - モメンタム計算のための定数（1M/3M/6M、MA200 等）やスキャンバッファを定義。

- ツール:
  - tools/paper_verification_report.py
    - ペーパートレード結果の検証レポート生成ツール。
    - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）からデータを集計して稼働率、注文成功率、送信率、P95 レイテンシ等を算出。
    - 判定基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）を定義して PASS/FAIL を出力。
    - P95 計算、日付フィルタ、SQL の存在しないテーブルに対するフォールバックを備える。

### Changed
- なし（初回リリースのため変更履歴は特になし）。

### Fixed
- なし（初回リリースのため不具合修正履歴は特になし）。

### Security
- 環境変数・機密情報に対する注意喚起を `config_setup.py` のトップコメントと `.env` 書き出しテンプレートに明示（.env を Git にコミットしないことを強調）。

---

今後のリリースでは以下の点が検討対象:
- factor_research の完全実装（ファクター群の SQL 実装や Z スコア正規化の統合）。
- ブローカークライアントの詳細実装とモックの充実（paper_trading のシミュレーション精度向上）。
- 各種単体テスト・統合テストの追加（.env 自動ロード、プロセス優先度設定、position sizing のスケールダウンロジック等）。
- ドキュメント（API 仕様、運用手順、監視指標定義）の整備。

もし CHANGELOG に追加して欲しい点（改行や表現の変更、日付の調整、個別コミット/チケット参照の追加等）があれば教えてください。