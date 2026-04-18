# Changelog

すべての重要な変更はここに記録します。本ファイルは「Keep a Changelog」規約に従います。  
既往のリリースや変更点は日本語で記載しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除

---

## [0.1.0] - 2026-04-18
初回公開リリース。

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）
  - パッケージバージョン: `__version__ = "0.1.0"`

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - ブローカークライアントを `BrokerClientFactory` 経由で生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、`ExecutionEngine.run_session` を別スレッドで実行。
    - 停止制御: `data/stop_requested.flag` を監視し、検知時にエンジン停止。PID ファイル書き込み機能あり（`data/execution.pid`）。
    - RiskManager のデフォルト設定（max_position_pct等）を組み込み。初期ポートフォリオ値は broker.get_available_cash() を利用。

  - run_monitoring.py
    - SystemMonitor ポーリングループ用起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト60秒）。不正値はデフォルトへフォールバックし警告を出力。
    - 監視データベースは環境に依らず本番の sqlite_path を使用（監視は本番 DB を参照）。
    - 停止フラグ（`data/stop_requested.flag`）が立っているとループを終了。
    - 例外発生時はログ出力し、次回ポーリングまで待機する堅牢化。

- 設定管理・CLI
  - config.py
    - 環境変数 / .env の読み込みを自動化（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env の読み込み優先順位: OS 環境 > .env.local > .env。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 各種設定プロパティを提供（DB パス、API トークン、ログレベル、しきい値等）。
    - `Settings` クラスで値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の検証など）。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START, 等）を扱う。
    - シークレット項目は表示をマスクし、保存時のテンプレートヘッダを付与。
  - validate_config.py
    - 起動前に .env と config/*.yaml（存在する場合）の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML ファイルのパースチェック（PyYAML があれば内容検証）等を実施。
    - `--strict` オプションで警告をエラー扱いにできる。

- ポートフォリオ構築モジュール（純粋関数）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates)
    - 等重み計算 (calc_equal_weights)
    - スコア加重計算 (calc_score_weights) — 全銘柄のスコアが 0 の場合は等重みへフォールバックし警告を出力
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（売却予定銘柄を除外して既存エクスポージャを計算）
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート。未知レジームは 1.0 でフォールバック）
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes
    - allocation_method: "risk_based" | "equal" | "score" をサポート
    - lot_size（現状100株単位）、cost_buffer（手数料・スリッページ見積）を考慮
    - aggregate cap（利用可能現金を超える場合のスケーリング）と残差処理によるロット単位での再配分を実装

- 研究・分析ユーティリティ
  - research/factor_research.py（ファクター計算基盤）
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計に基づくモジュールを追加（モメンタム計算等の関数群を実装）。
    - 設計方針として prices_daily / raw_financials テーブルのみを参照し、外部 API にはアクセスしない純粋な分析処理を想定。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）＋ TimedRotatingFileHandler（日次ローテート、30 日保持）をルートロガーへ設定。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト("INFO")。
    - ログディレクトリの自動作成を試み、失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収）。
    - set_process_priority("high"|"normal"|"low") と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS の場合は警告を出してスキップ。

- 監視・検証ツール
  - monitoring_db 初期化呼び出しを各スクリプトから実行（監視用テーブルの存在保証、冪等）。
  - tools/paper_verification_report.py
    - ペーパー取引ログ（SQLite）から検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計し、閾値比較で PASS/FAIL を判定。
    - 日付範囲指定（--from / --to）と DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - P95 計算、欠損データ時の N/A 表示、テーブルが存在しない場合の耐性（OperationalError をキャッチ）を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / その他の実装上のポイント
- .env のパースはシェル風のシンタックスをサポート（export プレフィックス、シングル/ダブルクォートとエスケープ、行内コメントの一定ルール）。不正行は無視。
- Settings の一部プロパティは値チェックを行い、不正値は例外を投げる（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- run_monitoring/run_execution 等のスクリプトは起動時にプロセス優先度を "high" に設定しようとする（権限不足時は警告を出力して継続）。
- Paper Trading に関する分離（DB とブローカー挙動）は設計上強く意識されており、本番環境と追試環境の混同を避けるようになっている。
- ロギングは stdout を使う設計（タスクスケジューラや cron での一元化リダイレクトを想定）。

---

今後の予定（例）
- モジュールのユニットテスト追加
- factor_research の完全実装と最適化
- Strategy / Execution の実運用検証に基づくパラメータ調整
- 銘柄別 lot_size サポート（stocks マスタの導入）

--- 

（注）本 CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴・リリースノートと差異がある場合があります。