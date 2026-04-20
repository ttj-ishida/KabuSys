# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

なお、本リポジトリの初期バージョンは 0.1.0 です。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-20
初回リリース。以下の主要機能・ユーティリティを追加しました。

### 追加 (Added)
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録することで本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) による安全な停止処理を実装。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用して監視データを記録。
    - 停止フラグ検知でループを終了する処理を実装。

- 設定・環境関連
  - config.py
    - 環境変数と設定を一元化する Settings クラスを追加。
    - .env 自動読み込み機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）を実装。
    - 各種パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等）、動作モード判定（is_live / is_paper / is_dev）や閾値設定をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーションや KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 入力補助、既存 .env の読み込み、シークレット値のマスク表示、保存前の確認を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- Portfolio 構築関連（純粋関数群、DB を参照しない）
  - portfolio/portfolio_builder.py
    - 銘柄選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコアが全て 0 の場合に等金額配分にフォールバックする挙動を持つ。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes を追加（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer、aggregate cap（資金が不足する場合のスケールダウン）などを考慮した実装。
    - 小数処理や残余配分ロジック（残差に基づく lot 単位の追加分配）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガー向けの統一ロギング設定ユーティリティを追加。
    - stdout に StreamHandler を出力することで cron 等での一本化に対応。
    - 日次ローテーションの TimedRotatingFileHandler を追加（デフォルト logs/<app_name>.log、30 日分保持）。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル・ログディレクトリ解決の優先順位を明示。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定を行うユーティリティを追加（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応環境でのフォールバック処理を含む堅牢な実装。

- tools
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled / Created）、送信率（Sent / Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計し PASS/FAIL を判定。
    - CLI オプション: --from / --to / --db、環境変数 PAPER_TRADING_SQLITE_PATH から DB パス指定可。
    - P95 計算、閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms）を採用。

- research
  - research/factor_research.py（ファクター計算基盤）
    - Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールの骨子を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算 calc_momentum の仕様（1M/3M/6M リターン、MA200乖離等）を記載（実装の続きあり）。

- パッケージメタ
  - __init__.py にバージョン情報を追加: __version__ = "0.1.0"

### 変更 (Changed)
- .env のパース処理を強化（config._parse_env_line）
  - export プレフィックスへの対応、クォート内のバックスラッシュエスケープ、インラインコメント処理、クォートなしのコメント判定などを実装し、より現実的な .env 文法に耐性を追加。
- .env 自動読み込みの挙動
  - プロジェクトルート探索を __file__ ベースで行うため、CWD に依存せずパッケージ配布後も動作するようにした。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化を実装（テスト時等に使用可能）。
- ログ出力の設計
  - 既にハンドラが設定されている場合は一旦 flush/close してから再設定することで二重設定を防止。

### 修正 (Fixed)
- 環境変数 MONITOR_POLL_INTERVAL の不正値処理
  - run_monitoring._get_poll_interval で負値や非整数を受け取った場合、自動的にデフォルト（60 秒）へフォールバックし警告を出すように修正。
- データベース初期化の冪等性
  - run_execution と run_monitoring 起動時に監視テーブルの初期化（init_monitoring_db）を呼び出してテーブル存在を保証するようにした（冪等性を意識）。
- process_priority / cpu_affinity の例外ハンドリング
  - 権限不足や未サポート環境での例外を捕捉して警告にフォールバックするように改善。

### ドキュメント・メタ
- 各モジュールに詳細な docstring を追加。
- config_setup 実行手順・validate_config の使い方・tools の CLI 例など、開発者向けの操作説明を各スクリプト冒頭に記載。

### 注意点 / 既知の制約
- research/factor_research.py は計算ロジックの一部（calc_momentum の実装開始）が含まれていますが、ファイル末尾で実装が途中で切れている箇所があります。実装の継続が必要です。
- position_sizing 等は単元株数 lot_size を全銘柄共通とする実装になっており、将来的に銘柄別 lot_map を受け取る拡張が予定されています（TODO コメントあり）。
- apply_sector_cap はセクター不明（"unknown"）の銘柄に対しては上限を適用しない挙動です。必要に応じてポリシーを変更してください。

---

もしこの CHANGELOG に追記したい変更点（リリース日や追加された細かなバグ修正）があれば教えてください。ログの粒度やフォーマット（日本語／英語、より詳細なコミット参照など）も調整可能です。