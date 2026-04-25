# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」準拠です。  
リリースの分類: Added, Changed, Fixed, Deprecated, Removed, Security。

## [Unreleased]
- ドキュメント化・次回リリースに向けた小変更のみ（現状なし）。

## [0.1.0] - 2026-04-25
初期公開リリース。本リポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ群（設定管理、起動スクリプト、ポートフォリオ構築、ログ設定、プロセス制御、ペーパートレード検証ツール、ファクター計算の骨組み等）を提供します。

### Added
- 基本パッケージ
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する挙動を明示。
    - 停止フラグファイル（data/stop_requested.flag）検出で安全にループを終了。
    - 例外発生時はログに例外を出し、次のポーリングまで待機して継続。

  - run_execution.py
    - 実際の ExecutionEngine 起動用スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を利用し paper_trading 用 DB（デフォルト: data/paper_trading.db）を使用して発注を本番 DB から完全分離。
    - 起動時にプロセス優先度を High に設定し、停止フラグ / PID 管理に対応。
    - エンジンを別スレッドで実行し、停止フラグ検出時に安全停止。

- 設定管理
  - config.py
    - .env の自動ロード機能（プロジェクトルートを .git / pyproject.toml で検出）を実装。`.env` → `.env.local` の優先順。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
    - .env パーサは quoted 値、export プレフィックス、インラインコメント等に対応（クォート内のエスケープ処理も考慮）。
    - Settings クラスを提供し、各種環境変数をプロパティとして整形・バリデーション付きで取得可能（例: PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証、パスの Path 化など）。
    - paper_trading 用 DB パス、監視閾値（CPU/MEM/DISK）、PID / kill flag の設定などをプロパティで提供。

- 設定ユーティリティ CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - 入力補助、デフォルト / 現在値表示、シークレットマスク、確認プロンプト、`.env` 書き出しロジックを含む。
    - .env 書式テンプレートを整えて出力。

  - validate_config.py
    - 起動前に必須環境変数・設定ファイルの存在や基本的な妥当性をチェックする CLI。
    - `--strict` オプションで警告を失敗扱いにできる。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証、KABUSYS_ENV やログレベル等の値チェック、DB パスの親ディレクトリ存在チェック、live 環境向けガードを実装。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次, 30 日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を回避。LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして安全に継続。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定機能を追加（Windows/Linux/macOS等に対応）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
    - 権限不足などで設定できない場合は警告ログでスキップする安全設計。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点時は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap：既存保有のセクターエクスポージャーに基づいて新規候補を除外するロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックし警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes：allocation_method（risk_based / equal / score）に基づいた注文株数決定ロジック。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap の実装、cost_buffer を考慮した保守的なコスト見積、スケーリングと残差に基づく追加配分アルゴリズムを含む。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を読み、期間指定で検証レポートを生成する CLI。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出。閾値ベースで PASS/FAIL 判定を行う（デフォルト閾値をソースに明記）。
    - P95 計算、日付フィルタ、DB 存在チェック、欠損テーブルに対する耐性（OperationalError のフォールバック）を実装。

- 研究用ファクター計算（骨組み）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等の計算方針と定数を定義。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - モメンタム計算（calc_momentum）の実装開始（コード断片あり、未完の箇所が含まれる）。

### Changed
- N/A（初期リリースのため履歴なし）。

### Fixed
- .env パーサと自動ロードにより、実行環境依存の設定ミス（クォート、export 形式、インラインコメント等）による読み込み失敗を軽減。
- run_monitoring のポーリング間隔取得で不正な値に対して警告を出しデフォルトにフォールバックする処理を追加（time.sleep への負の値渡しによる ValueError 回避）。

### Security
- config_setup に .env ヘッダコメントで「.env を絶対に Git にコミットしないこと」を明記。
- SECRET（J-Quants / KABU API パスワード）入力はシークレット扱いでマスク表示。

### Notes / Implementation details
- Monitoring と Execution はそれぞれ SQLite（監視用 / paper_trading 用切替）と DuckDB を併用する設計。Monitoring は環境に依存せず監視 DB を本番パスで扱う仕様（設計上の意図として監視データを一元化）。
- process_priority / logging_setup など OS 環境や権限に依存する操作は、失敗時に例外を上げずログで警告してフォールバックする堅牢設計。
- research/factor_research はまだ完成していない関数や実装断片が含まれるため、使用時は注意が必要。

---

今後の予定例（非包括的）
- factor_research の完成（momentum 等の実装完了、ユニットテスト追加）
- ExecutionEngine / Monitoring の詳細なユニットテストおよび統合テストの追加
- Strategy/Execution に関するドキュメントとサンプル設定の充実

--- 

（本 CHANGELOG はコードから推測して作成しています。実際のコミット履歴や変更差分からの自動生成ではありません。）