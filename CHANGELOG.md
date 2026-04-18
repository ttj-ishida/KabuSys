# Changelog

すべての重要な変更履歴をここに記載します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Removed, Deprecated, Security）に記載します。
- バージョンは逆順（最新を先頭）で記載します。

## [Unreleased]

（開発中の変更・TODO をここに記載してください）

---

## [0.1.0] - 2026-04-18

初回公開リリース。

### Added
- 基本アプリケーション情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離する挙動を実装。
    - ブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンド実行と停止フラグ管理を実装。
    - プロセス優先度を高く設定して起動する仕組みを導入。
    - 起動時に停止フラグ（data/stop_requested.flag）を検出した場合は起動を中止する安全措置を実装。
    - 実行中は PID ファイル（data/execution.pid）を利用。

  - run_monitoring.py
    - SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）を実装。0 以下や不正な値はデフォルトにフォールバック。
    - 監視 DB（SQLite）は Monitoring が環境にかかわらず本番の sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検出時にループを終了する処理を実装。

- 設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を実装し、.env/.env.local の自動ロード（OS 環境変数優先）を実装。
    - .env のパース機能を実装（export プレフィックス対応、シングル/ダブルクォート・エスケープ、インラインコメント処理など）。
    - 環境変数を扱う Settings クラスを実装（DB パス、API トークン、ペーパートレード設定、閾値、ログレベル等）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` のサポート。

  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。
    - 多数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, LINE_* など）を対話的に入力・確認して .env を書き出す機能を提供。

  - validate_config.py
    - 設定検証 CLI を追加。
    - 必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）などを実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティを追加。
    - ログディレクトリの自動作成。作成失敗時はファイルハンドラをスキップしてコンソール出力のみで安全に継続する挙動を実装。
    - ログレベルは引数 > 環境変数 > デフォルト の優先度で解決。

  - utils/process_priority.py
    - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX 系（Linux, Darwin, FreeBSD）を吸収する実装。権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順、スコア同値は signal_rank の昇順でタイブレーク）。
    - 等比重 calc_equal_weights、スコア重み calc_score_weights（全スコア=0 の場合は等配分にフォールバック）を追加。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有を基にセクター比率を計算し上限超過セクターの新規候補を除外）。
    - "unknown" セクターは上限適用対象外とする挙動を採用。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知のレジームは 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - 銘柄ごとの発注株数算出 calc_position_sizes を実装。
    - allocation_method（"risk_based", "equal", "score"）に対応。
    - 日次単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的なコスト見積り、スケールダウン後の端数処理（lot 単位で再配分）などを実装。
    - price 欠損時のスキップやログ出力、将来の拡張（銘柄別 lot_size）への注釈を含む。

- 研究・解析ユーティリティ
  - research/factor_research.py
    - ファクター計算モジュールを追加（モメンタム、MA200乖離、ATR、流動性等を想定）。
    - DuckDB 接続を受けて prices_daily / raw_financials テーブルから計算する設計（関数スケルトンと定数群を実装）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL 判定を行う。
    - CLI で期間フィルタ（--from, --to）と DB パス指定（--db / 環境変数）に対応。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して起動時に監視テーブルの存在を保証（冪等）。

### Changed
- ログ出力のデフォルトストリームを stderr ではなく stdout に変更（cron/スケジューラからのリダイレクトを想定）。
- .env 自動ロードの優先順位を明確化（OS 環境変数 > .env.local > .env）。OS 環境変数は保護され .env.local / .env により上書きされない。
- process_priority 実装で OS 毎の適切な定数・nice 値を使用するように抽象化。

### Fixed
- 起動スクリプトでの DB 接続後にリソースを必ずクローズするように finally ブロックで処理を追加。
- 無効な MONITOR_POLL_INTERVAL 値（非数値や 0 以下）を検出して警告を出しデフォルト値にフォールバックする処理を追加。

### Security
- .env の生成時に注意書きを追加（.env を絶対に Git にコミットしない旨）。
- 対話式ウィザードでシークレット項目はマスク表示（確認時に **** 表示）。

---

今後の予定（TODO）
- research/factor_research の各ファクター関数の完全実装（現在はモジュール・定義を追加済み、一部実装中）。
- ExecutionEngine / SystemMonitor の詳細なテストカバレッジと E2E テスト。
- 銘柄別 lot_size のサポート（stocks マスタ拡張）。
- 監視・アラートの LINE 通知連携（LINE トークン利用）強化。

---

参照
- リリースに含まれる主要スクリプト:
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/config.py
  - src/kabusys/config_setup.py
  - src/kabusys/validate_config.py
  - src/kabusys/utils/logging_setup.py
  - src/kabusys/utils/process_priority.py
  - src/kabusys/portfolio/*
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/research/factor_research.py

（必要であれば各ファイルの詳細な変更点や設計意図を追記します。）