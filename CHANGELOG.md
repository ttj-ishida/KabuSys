# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
タグ付けは Semantic Versioning を想定しています。

## [Unreleased]

### Added
- 初期リリース (0.1.0 に含まれる機能を参照してください)。

### Known issues
- research.calc_momentum の実装が途中で終わっており、ファクター計算モジュールの一部が未完です（今後実装予定）。
- position_sizing モジュールにおいて銘柄ごとの単元情報（lot_size）の拡張が TODO コメントで残っています。
- risk_adjustment.apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価など）は未実装で、price が 0.0 の場合にエクスポージャーが過少見積りされる可能性があります。

---

## [0.1.0] - 2026-04-18

初回公開リリース。自動日本株売買システム「KabuSys」の基本機能群をまとめて追加。

### Added
- 全体
  - パッケージ初期バージョンを定義 (`__version__ = "0.1.0"`)。

- 起動スクリプト / 実行関連
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じた DB 分離:
      - `paper_trading` 環境では専用の paper_trading SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と完全分離。
      - BrokerClientFactory を用いて、paper_trading 時は MockBrokerClient を利用できる設計を想定。
    - 実行中の停止フラグ（`data/stop_requested.flag`）や PID ファイル管理に対応。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てロジックを実装。

  - run_monitoring.py
    - SystemMonitor ポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境に関係なく本番用の sqlite_path を使用して監視データを記録。
    - 停止フラグ（`data/stop_requested.flag`）の検出でループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数経由で各種設定（API トークン・DB パス・監視閾値・ログレベル等）を提供。
    - .env 自動読み込み機能を実装（プロジェクトルートを `.git` または `pyproject.toml` から検出）。`.env` と `.env.local` の優先順を実装し、OS 環境変数の保護（上書き禁止）に対応。
    - .env 行パーサで `export` 形式、クォート文字列とエスケープに対応。コメント取り扱いの細かい挙動も実装。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）を追加。
    - 環境種別 (`KABUSYS_ENV`) の検証と bool プロパティ（is_live, is_paper, is_dev）を提供。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 項目定義（環境種別、J-Quants トークン、kabu API パスワード、DB パス、LINE トークン等）を持ち、既存 .env の値を再利用可能。
    - 出力時にシークレットはマスク表示、.env 書き込みテンプレートには注意事項（絶対に Git にコミットしない等）を記載。

  - validate_config.py
    - 起動前に環境変数と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL のチェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在/パース検証（PyYAML 未インストール時はスキップ）などを行う。
    - `--strict` オプションにより警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - score が全て 0 の場合は等金額配分へフォールバックし警告ログを出力。

  - portfolio.risk_adjustment
    - セクター集中制限を適用して上限超過セクターの新規候補を除外する apply_sector_cap を実装。
    - 市場レジームに応じた投下資金乗数を返す calc_regime_multiplier を実装（bull/neutral/bear に対応。未知レジームは警告後 1.0 フォールバック）。

  - portfolio.position_sizing
    - allocation_method（"risk_based" / "equal" / "score"）に基づき、発注株数を決定する calc_position_sizes を実装。
    - 単元丸め（lot_size）、1銘柄上限、 aggregate cap（available_cash 超過時のスケーリング）、cost_buffer を考慮したスケーリングと端数処理を実装。
    - price 欠損や 0 値の取り扱いでスキップロジックを実装。

  - portfolio パッケージ __init__ にて主要関数をエクスポート。

- ユーティリティ
  - utils.logging_setup
    - 統一的なロギングセットアップ関数 setup_logging を追加。
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせ、既存ハンドラの二重登録を防止。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。

  - utils.process_priority
    - Windows / POSIX(Linux/Mac/FreeBSD) を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - CPU affinity 固定用の set_cpu_affinity 関数を提供。
    - アクセス権限不足や未対応 OS でのフォールバック処理と警告出力を実装。

- モニタリング / DB
  - monitoring モジュールの初期化処理呼び出しを run_execution, run_monitoring で実行（init_monitoring_db）。
  - duckdb, sqlite 接続の確立とクローズ処理を起動スクリプトで適切に管理。

- ツール
  - tools.paper_verification_report
    - ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）等を集計して判定（PASS/FAIL）を出力。
    - P95 計算、日付フィルタ（--from / --to）、DB 存在チェック、各 SQL のエラーハンドリングを実装。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。

- research
  - research.factor_research にモメンタム等のファクター計算の骨子を追加。DuckDB 接続を受け prices_daily / raw_financials を参照する設計。モメンタム計算（calc_momentum）のスタブを含むが、一部未完。

### Changed
- n/a（初期リリースのため既存からの変更はなし）

### Fixed
- .env パーサ周りで複雑なクォート・エスケープケースに対応（export 形式、バックスラッシュエスケープ、インラインコメント処理など）して堅牢性を向上。

### Security
- config_setup に .env を絶対に Git にコミットしてはいけない旨の注意文を出力。シークレット項目はウィザードでマスク表示。

### Notes / Implementation details
- stop/kill フラグや PID ファイルを利用した安全停止の仕組みを導入（`data/stop_requested.flag`, `data/execution.pid` 等）。
- run_monitoring は環境に関わらず本番 sqlite_path を監視 DB として使用する挙動を明確化（監視データは本番 DB に記録する想定）。
- Logger は stdout を用いることで cron/Task Scheduler 等でのリダイレクト運用に配慮。
- process_priority 系は権限不足や未対応プラットフォームで警告を出して安全にフォールバックする設計。

---

開発・運用にあたっての参考:
- .env 自動ロードはプロジェクトルート検出（.git / pyproject.toml）に依存します。パッケージ配布後に自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading と Live の DB 分離を徹底していますが、設定ミスや環境変数の誤設定は重大な影響を与えるため、`python -m kabusys.validate_config` による事前検証を推奨します。