# Changelog

すべての変更は Keep a Changelog の方針に従い、セマンティックバージョニングを採用します。
リリース日: 2026-04-23

## [0.1.0] - 2026-04-23

最初のリリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、運用支援ツール群を追加しました。

### 追加 (Added)
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 環境・設定管理
  - 環境変数ローダ・設定管理モジュール `kabusys.config` を追加。
    - プロジェクトルート検出（.git / pyproject.toml 基準）により .env/.env.local を自動ロード（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可）。
    - .env パースロジック（クォート、export プレフィックス、インラインコメント処理）。
    - Settings クラスで各種設定値（DB パス、API トークン、閾値、環境種別など）をプロパティとして提供。
    - 環境種 `development` / `paper_trading` / `live` とログレベルの検証を実装。

- 起動スクリプト / デーモン類
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御ファイル（data/stop_requested.flag）検知でループを終了。
    - 監視（Monitoring）は環境にかかわらず本番用 sqlite_path を使用する仕様。
    - SQLite（監視 DB）と DuckDB 両方の接続確立、監視 DB の初期化処理呼び出しを行う。
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite DB を使用（data/paper_trading.db、環境変数で上書き可）し、MockBrokerClient を使用する想定。
    - 停止フラグ（data/stop_requested.flag）と実行 PID 管理（data/execution.pid）に対応。
    - ExecutionEngine をスレッドで起動し、停止フラグ検知で安全に停止を試みるループを実装。

- 設定支援 CLI
  - 対話式 .env 作成/更新ウィザード `kabusys.config_setup` を追加。
    - 入力ウィザード、既存 .env 読み込み、シークレット項目のマスク表示、保存確認を実装。
  - 設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml 存在チェック（PyYAML があればパース検証）、
      KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）などを行う。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup` を追加。
    - ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX(Linux, Darwin, FreeBSD) の差分を吸収してプロセス優先度（high/normal/low）を設定する `set_process_priority`。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity`（権限のない環境では警告を出してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を追加。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を追加。
    - レジームマップ: "bull"=1.0, "neutral"=0.7, "bear"=0.3（未知レジームは 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - position sizing ロジックを追加（allocation_method: "risk_based" / "equal" / "score" 対応）。
    - lot_size（単元）対応、max_position_pct、max_utilization、cost_buffer による保守的見積りと aggregate cap スケーリング、
      スケーリング後の端数処理（lot 単位で残差分を分配）を実装。
  - `kabusys.portfolio.__init__` にエクスポートをまとめる。

- ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading の SQLite（デフォルト data/paper_trading.db）を読み、システム稼働率・注文成功率・送信率・レイテンシ(P95 等)・リスク却下数 を算出しレポート出力。
    - デフォルトしきい値（PASS/FAIL 判定）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from / --to）、--db による DB 指定をサポート。
    - レポートは標準出力へ。

- 監視/実行関連の DB 初期化呼び出し
  - `monitoring.monitoring_db.init_monitoring_db` を利用して起動時に監視テーブルの存在を保証（冪等呼び出し）。

- 研究用ファクター計算（部分実装）
  - `kabusys.research.factor_research` を追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB を使って prices_daily / raw_financials を参照する設計。
  - モメンタム計算関数 calc_momentum の実装開始（設計・定数群・関数枠組みを追加）。※ファイル末尾に未完の箇所あり（実装継続予定）。

### 変更 (Changed)
- 該当なし（初回リリースのため既存コードの変更はありません）。

### 修正 (Fixed)
- 該当なし（初回リリースのためバグ修正履歴はありません）。

### 既知の問題 (Known issues)
- factor_research モジュールの calc_momentum 実装が途中で終わっている箇所があり、完全な計算実装は今後のコミットで補完予定です。
- 一部の機能は外部モジュール（psutil、PyYAML、duckdb、sqlite3 など）に依存しています。これらがインストールされていない環境では該当機能が警告・スキップされます（validate_config は PyYAML がない場合に YAML チェックをスキップする等）。
- process_priority / set_cpu_affinity は実行権限や OS によっては設定に失敗することがあり、その場合は警告を出してスキップします。

### マイグレーション / 運用メモ (Migration / Operational notes)
- .env の自動ロード:
  - デフォルトでプロジェクトルートを探し `.env` → `.env.local` の順に読み込みます。OS 環境変数は上書きされません。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 実行/監視の DB 分離:
  - `run_execution.py` は paper_trading モードの際に `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用し、本番監視 DB と分離します。
  - 監視プロセスは環境にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用します。
- ログ:
  - デフォルトログディレクトリは `logs/`。ファイル出力失敗時はコンソール出力のみで継続します。ログレベルは `LOG_LEVEL` 環境変数または setup_logging の引数で制御できます。
- 停止制御:
  - 実行・監視プロセスともにプロジェクトルート下の `data/stop_requested.flag`（パスはコード内で解決）を検知して正常停止します。kill/signal ベース運用ではこのファイル作成で遠隔停止できます。
- Paper Trading レポート:
  - `kabusys.tools.paper_verification_report` は運用後の検証に便利です。しきい値はソース内の定数で定義されていますが、必要なら CLI の外部化も検討してください。

### セキュリティ (Security)
- 現時点でセキュリティ関連の変更はありません。ただし .env は絶対にリポジトリにコミットしないでください（config_setup 生成時にもその旨を注記）。

---

今後の予定:
- research.calc_momentum 等の未完実装の完成・テスト追加。
- ExecutionEngine / BrokerClient のモック実装整備と E2E テスト。
- 設定検証・ウィザードの拡張（より詳細なチェックや非対話モード）。
- Paper Trading レポートの出力形式（JSON/CSV）追加検討。