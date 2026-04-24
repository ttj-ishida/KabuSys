# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。コードベースの現状から実装内容を推測して作成しています。

全般的な注意
- 日付はコードから推測できる範囲で付与しています（リリース日はサンプル日付です）。必要に応じて実際のリリース日に置き換えてください。
- 各項目はソースファイルの実装内容に基づく要約です。細かな実装意図や未実装の TODO は適宜補足しています。

Unreleased
- ドキュメント化されているが未実装・未完成の機能や今後の改善案を記載（現状のコードに基づく注記）。
  - research/factor_research.py にてファクター計算（モメンタム等）の実装が開始されているが、ファイル末尾が途中で切れており未完成の可能性あり。継続実装・テストが必要。
  - position_sizing の将来的拡張点（銘柄ごとの lot_size マスタ化、価格フォールバック等）がコメントとして残されている。これらは次バージョンでの改善候補。
  - ログディレクトリ作成失敗時の挙動は StreamHandler のみで耐性を持つ実装になっているが、運用上の観点から監視・アラートを追加することを推奨。

[0.1.0] - 2026-04-24
Added
- 実行エントリ／プロセス管理
  - run_execution.py を追加。ExecutionEngine を起動するための CLI ランチャーを実装。
    - プロセス優先度を "high" に設定する処理を起動直後に実行。
    - KABUSYS_ENV が paper_trading の場合は paper 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離する。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動を行う。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う安全停止ロジックを実装。
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動するランチャーを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告を出してデフォルトにフォールバック。
    - Monitoring は環境に依存せず production 用 sqlite_path を使用する（監視は常に本番 DB を見る意図）。
    - stop flag による終了検知、check_once() の例外捕捉とログ出力を実装。

- 設定管理（.env / 環境変数）
  - config.py を追加。プロジェクトルート（.git または pyproject.toml）を自動検出して .env/.env.local を自動ロードする機能を提供（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化機能あり）。
  - Settings クラスを導入し、アプリ全体で使用する設定プロパティを集中管理。
    - J-Quants / kabuステーション / LINE / DB（DuckDB/SQLite）など主要設定をプロパティで提供。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH の分離、KABUSYS_ENV/LOG_LEVEL の検証ロジックを実装。
    - pid_file_path / kill_flag_path / kill_flag_clear_on_start / 各種閾値（CPU/MEM/DISK）など監視に必要な設定を提供。

- 設定ユーティリティ
  - config_setup.py を追加。対話式ウィザードで .env を初期生成・更新する CLI を実装。
    - .env の既存値読み込み、シークレットマスク表示、選択肢サポート、保存確認をサポート。
  - validate_config.py を追加。起動前に .env と config/*.yaml の妥当性を検証する CLI を実装。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML ファイルの存在チェックとパース（PyYAMLが存在する場合）を実施。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder を追加。
    - select_candidates（スコア降順で上位 N 選出）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等分配にフォールバック）を実装。
  - portfolio.risk_adjustment を追加。
    - apply_sector_cap によりセクター集中を制限（既存保有のセクター別エクスポージャを計算して候補を除外）。
    - calc_regime_multiplier により market regime（bull/neutral/bear）に応じた資金乗数を提供（未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing を追加。
    - calc_position_sizes を実装。allocation_method による分岐（risk_based / equal / score）で発注株数を計算。
    - 単元（lot_size）丸め、per-stock 上限・aggregate cap（available_cash 超過時の縮小）ロジック、cost_buffer（手数料・スリッページ想定）を実装。
    - aggregate cap のスケーリング実装は残差の取り扱い（fractional remainder に基づく lot-size 単位の再分配）まで考慮している。

- 監視・解析関連
  - monitoring_db の初期化呼び出しを複数箇所から行う（init_monitoring_db を起動時に呼出し、監視テーブルの存在を保証）。
  - tools.paper_verification_report を追加。Paper Trading 用の検証レポートを生成する CLI を実装。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg / max / P95）の集計と PASS/FAIL 判定ロジックを実装。
    - デフォルトの閾値（稼働率 99%、Fill 90%、Send 95%、P95 200ms）を定義。

- ユーティリティ
  - utils.logging_setup を追加。setup_logging 関数で共通のログ設定（stdout StreamHandler、日次ローテーションの TimedRotatingFileHandler）を提供。
    - LOG_LEVEL / LOG_DIR の解決順を実装、ログディレクトリ作成失敗時のフォールバックを用意。
  - utils.process_priority を追加。Windows/Linux の差分を吸収してプロセス優先度（high/normal/low）および CPU affinity の設定を提供（psutil を使用）。
    - アクセス権限不足時は警告ログを出してスキップ。

- パッケージ情報
  - __init__.py にてパッケージバージョン __version__ = "0.1.0" を設定。

Changed
- なし（本リリースは新規追加が中心と推測されるため、変更履歴は初版として記載）。

Fixed
- なし（同上）。

Security
- なし（特段のセキュリティ修正はコードからは検出できません。環境変数にシークレットを含むため .env の取り扱いと Git 応じた注意喚起が README 等で必要）。

Notes / 運用上のポイント
- 本番稼働時の注意
  - validate_config の警告（特に KABUSYS_ENV=live の場合の LINE 設定欠如、KILL_FLAG_CLEAR_ON_START 設定）は運用前に必ず確認してください。
  - run_monitoring は常に production sqlite_path を使う実装になっているため、テスト環境で監視データを書きたくない場合はコードまたは設定で適切に分離してください。
- テスト・拡張
  - research/factor_research の未完部分、position_sizing の銘柄別 lot_size 拡張、価格フォールバック実装などは今後の拡張候補です。
  - BrokerClientFactory や ExecutionEngine、SystemMonitor 等の実働ロジックは外部依存（ブローカー API、duckdb/prices テーブル等）を持つため、モックを用いた単体テストの整備を推奨します。

以上。必要であれば個々のファイル単位での変更要約や、実際のリリース日・バージョンの調整を行って CHANGELOG.md を更新します。