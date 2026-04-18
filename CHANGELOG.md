# CHANGELOG

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in Japanese.
Release notes are organized by version and category.

デフォルトのバージョンは package の __version__ = 0.1.0 に合わせています。

## [Unreleased]
- なし（初回リリースに向けた状態）

## [0.1.0] - 初期リリース
初回リリース。システム監視・実行エンジン・ポートフォリオ構築・ユーティリティ類・各種 CLI を実装。

### Added
- 基本構成・バージョニング
  - パッケージ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は mock ブローカーを使用し、paper_trading 用 SQLite（data/paper_trading.db 等）を利用して本番 DB と完全分離。
    - 実行中の PID を data/execution.pid に記録する仕組みを想定（pid_file の取り扱い）。
    - data/stop_requested.flag による停止フラグ検知で安全に停止。
    - エンジンを別スレッドで起動し、停止フラグを監視して優雅に停止するループを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔の上書きが可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path（monitoring DB）を使用する設計。
    - data/stop_requested.flag を検知して監視ループを終了。
- 環境設定・検証・ウィザード
  - config.py: 環境変数読み込み・設定管理を実装。
    - プロジェクトルート (.git または pyproject.toml) を自動検出して .env / .env.local をロード（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 複雑な .env のパースを行うユーティリティ（クォート内のエスケープ、inline コメントの扱い等）。
    - 各種設定値（DB パス、KABUSYS_ENV 判定、PAPER_FILL_MODE のバリデーション等）をプロパティで取得する API を提供。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを実装。
    - 主要な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、Kill Switch など）に対する対話的入力と .env 書き出しをサポート。
  - validate_config.py: 起動前に .env および config/*.yaml の整合性を検証する CLI を実装。
    - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と PyYAML によるパースチェック（PyYAML 未インストール時はスキップ）、本番環境向けガード（LINE 設定・Kill Switch 設定の警告）などを提供。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ（銘柄選定・重み付け・ポジション決定・リスク調整）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で上位 N を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率に応じた配分。全スコアが 0 の場合は等金額配分にフォールバックし警告ログを出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用して候補銘柄を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返却。未知のレジームは 1.0 でフォールバックし警告を出力。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき銘柄ごとの発注株数を計算。
      - リスクベース計算、単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合はスケールダウン）および残余キャッシュを用いた再配分ロジックを実装。
      - cost_buffer によりスリッページ/手数料を保守的に見積もる。
- 研究用・ファクター計算
  - research/factor_research.py: ファクター計算モジュール（モメンタム、MA200乖離、ATR、出来高系などの算出方針を実装する設計）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計方針（外部 API 呼び出し無し）。
    - （注）ファイルに計算定数や calc_momentum の定義が含まれている。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - 指定期間の system_status, trade_logs, risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL を判定。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能。
    - 標準的な閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を用いた判定を実装。
- 監視 DB 初期化
  - monitoring/monitoring_db.py（参照されている）との連携で起動時に監視用テーブルを冪等に初期化する呼び出しを導入（run_monitoring, run_execution で init_monitoring_db 呼び出し）。
- ロギング関連ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを追加。
    - stdout への StreamHandler（sys.stdout）と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30 日分保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - LOG_LEVEL / LOG_DIR / 引数経由で設定可能。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続。
- プロセス優先度・CPU affinity ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows と POSIX（Linux/Mac 等）の差分を吸収してプロセス優先度を設定。権限不足や未対応 OS の場合は警告をログ出力してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスを固定する機能。権限不足や未対応環境では警告を出力してスキップ。
- DB ドライバ（duckdb / sqlite3）連携
  - run スクリプトや research, tools で DuckDB と SQLite の組み合わせを想定して接続を確立・クローズする実装。
- 設計方針・ドキュメント断片
  - 各モジュールに対して動作の注記や設計方針（PortfolioConstruction.md / StrategyModel.md 等参照）をコメントで記載。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数や入力値の堅牢化
  - MONITOR_POLL_INTERVAL のパースにおいて 0 以下や不正な値が指定された場合にデフォルトへフォールバックし警告をログ出力するように実装。
  - config._parse_env_line にてクォート・エスケープ・コメント処理を丁寧に扱うことで .env の誤読を防止。
  - process_priority 系はアクセス権限不足や未実装の属性に対して例外ではなく警告でフォールバックするよう変更。

### Security
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する想定だが、config_setup ウィザード内に「.env を絶対に Git にコミットしないこと」という注意書きを追加。

### Notes / Known limitations
- research/factor_research.py は設計と一部の実装（定数、calc_momentum のインターフェースなど）を含むが、完全実装の有無はファイル内の続きに依存します（本リリースではそのまま提供）。
- 各種 config/*.yaml の雛形は scripts/generate_config.py で生成可能だが、初期状態で存在しない場合は validate_config が警告を出します。
- paper_trading 用の MockBrokerClient 等は実装体（broker_factory, execution_engine, order_manager 等）に依存しており、本 CHANGELOG は公開 API と挙動を高レベルで記述しています。

---

今後のリリースでは詳細なバグ修正・性能改善・追加機能（例: 銘柄別 lot_size のサポート、前日終値を用いた価格フォールバック、より細かいログ出力制御など）を記載していきます。