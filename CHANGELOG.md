# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

全般:
- 日付形式: YYYY-MM-DD
- バージョン 0.1.0 は初回リリースとして、本コードベースで導入された主要機能を記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。以下の主要コンポーネントとユーティリティを追加しました。

### Added
- 起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient を利用する挙動を実装（本番 DB と分離）。
    - プロセス優先度を起動時に High に設定し、停止フラグ（data/stop_requested.flag）で安全に停止できる仕組みを追加。
    - 実行中の PID を data/execution.pid に書き出す仕組み（pid_file）をサポート。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。

- 設定管理 / ユーティリティ
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（.env, .env.local をプロジェクトルートから読み込み、OS 環境変数を保護）。
    - 複雑な .env パース（export プレフィックス、クォート、インラインコメント取り扱い）に対応。
    - 各種設定プロパティ（DB パス、API トークン、監視閾値、環境判定など）を提供する Settings クラスを追加。
  - src/kabusys/config_setup.py
    - 対話式の環境設定ウィザードを追加（.env の初期作成・更新を支援）。
    - デフォルト値、選択肢、秘匿表示（トークン等）のサポートと保存機能を備える。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスや config ファイルの存在/パースチェック、本番環境向けのガード（LINE 通知や KILL_FLAG_CLEAR_ON_START）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順 + tie-break）select_candidates を追加。
    - 等金額配分 calc_equal_weights と スコア加重配分 calc_score_weights を追加（スコア全0時は等金額へフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（既存ポジションからセクター露出を計算して新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを追加。allocation_method として "risk_based" / "equal" / "score" をサポート。
    - リスクベースの株数算出、単元取引（lot_size）での丸め、per-position 上限・aggregate cap（available_cash）でのスケーリング、cost_buffer（手数料・スリッページ想定）を実装。
    - 現在保有分を考慮した増減分算出を行う。

- ログ / プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーを統一的に設定する setup_logging を追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定、ログディレクトリ作成や失敗時のフォールバック動作を実装。
    - ログレベル / ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。30 日保持。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度の設定と CPU affinity のサポートを追加。
    - set_process_priority(level) で high/normal/low を指定可能、例外や権限不足時は警告してスキップ。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から指標を集計し、検証レポートを生成する CLI を追加。
    - 集計項目: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等。
    - 閾値を定義し PASS / FAIL 判定を出力。--from / --to / --db オプションをサポート。

- リサーチ（ファクター計算）基盤（部分実装）
  - src/kabusys/research/factor_research.py
    - モメンタム等ファクター計算の設計と定数を追加。DuckDB を使った prices_daily / raw_financials 参照による計算を想定。
    - （ファイル内に詳細設計と calc_momentum の実装開始が含まれるが、コードは部分的で続きがある形で導入）

- パッケージエントリ
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。
  - src/kabusys/portfolio/__init__.py エクスポートを整理。

### Changed
- n/a（初回リリースのため既存コードの変更はなし）

### Fixed
- n/a（初回リリースのためバグ修正履歴はなし）

### Notes / Implementation details
- 設定読み込み:
  - .env の自動ロードはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定する。
  - OS 環境変数は保護され、.env.local の override は OS 環境変数を上書きしない。
- run_monitoring と run_execution では起動直後に set_process_priority("high") を呼び、プロセス優先度を高めることで監視・実行の安定性を向上させる意図があります。
- run_monitoring は監視用 DB テーブルの初期化（init_monitoring_db）を行い、duckdb も利用します。例外発生時はログ出力して次ポーリングへ継続します。
- run_execution は paper_trading モードの際に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、実運用データと分離するよう設計されています。
- position_sizing の aggregate スケーリングでは lot_size 単位の再配分ロジックがあり、端数処理の安定化（再現性）を考慮しています。

---

（初回リリース。今後の変更はこのファイルに追記してください。）