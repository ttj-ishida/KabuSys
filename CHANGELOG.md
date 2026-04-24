CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
詳しい履歴はリリースノートをご覧ください。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ修正

Unreleased
----------

（次回リリース用のプレースホルダ）

0.1.0 - 2026-04-24
------------------

Added
- 初回公開リリース。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離する設計。
    - BrokerClientFactory を介してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境設定にかかわらず本番 sqlite_path を使用して監視 DB を更新（init_monitoring_db を呼ぶ）。
    - 停止フラグによりループを終了。
- 設定関連
  - config.py
    - 環境変数/.env の取り扱いを実装。プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を読み込む（読み込み順: OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - 各種設定プロパティを提供（API トークン、DB パス、Paper Trading 設定、監視しきい値等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を提供。
    - .env のテンプレート出力、既存値のマスク表示、保存確認を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の簡易検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML パース確認（PyYAML が存在する場合）、本番用ガードチェックを実装。--strict オプションで警告を FAIL 扱いにできる。
- ロギング/プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトから使える共通ロギング設定を実装。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数対応、既存ハンドラのクリーンアップ処理を実装。
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収するプロセス優先度設定。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS の場合は警告を出してスキップする堅牢さ。
- ポートフォリオ構築ライブラリ（純粋関数・DB非依存）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）とレジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターは上限除外、未知レジームはフォールバック。
  - portfolio/position_sizing.py
    - allocation_method に応じて個別銘柄の発注株数を計算（"risk_based" / "equal" / "score"）。
    - 単元（lot_size）丸め、1銘柄上限 max_position_pct、aggregate cap（available_cash）に基づくスケーリング、コストバッファ考慮、残差処理などを実装。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI。
    - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計し、パス/フェイル基準（デフォルトしきい値: 稼働率 99%、成功率 90% 等）で判定を行う。
    - PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB 指定可。
- リサーチ
  - research/factor_research.py
    - ファクター計算モジュールの枠組み（Momentum / Value / Volatility / Liquidity）を実装。DuckDB 接続を受け prices_daily / raw_financials を参照する設計。モメンタム係数計算（calc_momentum）の実装開始。
- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- n/a（初回リリースのため変更履歴は無し）。

Fixed
- n/a（初回リリースのため修正履歴は無し）。

Deprecated
- n/a

Removed
- n/a

Security
- n/a

注記 / マイグレーション
- Paper Trading と本番 DB は完全に分離されています。Paper Trading を使うには KABUSYS_ENV=paper_trading を設定してください。paper_trading 用 DB のデフォルトは data/paper_trading.db です。
- .env 自動読み込みはプロジェクトルートの検出に依存します（.git または pyproject.toml を基準）。テスト等で自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログディレクトリの作成に失敗した場合はコンソール出力のみとなりますが、アプリ自体は起動を継続します。
- 実行スクリプトは起動時にプロセス優先度を "high" に変更しようとしますが、権限不足やプラットフォーム制限で失敗することがあります（その場合は警告がログに残ります）。

今後の予定（例）
- research/factor_research のファクター完備、テストカバレッジ追加。
- SystemMonitor / monitoring_db / ExecutionEngine 周りの詳細な監視・リトライ実装強化。
- 銘柄ごとの lot_size 対応や手数料・スリッページモデルの洗練。
- YAML 設定ファイルの更なる検証・テンプレート生成。

--- 

（この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴や設計文書と差異がある可能性があります。）