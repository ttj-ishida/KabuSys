CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に準拠して記載しています。重要な変更点はセクションごとに分類しています。

[0.1.0] - 2026-04-18
-------------------

Added
- 基本機能の初期実装を追加（初回リリース相当）。
  - kabusys パッケージ本体（__version__ = 0.1.0）。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 環境変数 KABUSYS_ENV が `paper_trading` の場合は paper_trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler 等の依存コンポーネントを組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）対応。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を定義し、初期ポートフォリオ値を broker.get_available_cash() から取得。
  - run_monitoring.py
    - SystemMonitor をポーリングで定期実行する監視プロセス起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path（data/monitoring.db）を使用するよう設計。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理と CLI
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env / .env.local の読み込み順と保護された OS 環境変数の取り扱いを実装（.env.local は上書き可能、既存 OS 環境変数は保護）。
    - 複数の設定プロパティを定義（J-Quants、kabuAPI、LINE、DuckDB/SQLite パス、paper trading 用設定、監視閾値、KABUSYS_ENV 検証など）。
    - PAPER_FILL_MODE の検証と paper_sqlite_path の分離設定を追加。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。既存 .env の読み込み、入力補助、シークレットマスク、ファイル書き出しを実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（--strict オプションで警告を失敗扱いにできる）。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在/パースチェック（PyYAML がない場合は警告）、本番環境向け追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 共通ロギングセットアップ関数 setup_logging を追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決ルールと既存ハンドラの安全なクリア処理を実装。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows（HIGH_PRIORITY_CLASS 等を利用）と POSIX（nice 値）に対応、権限不足や未対応 OS の場合はフォールバックして警告を出力。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（psutil ベース、権限不足時は警告でスキップ）。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順・タイブレーク実装）。
    - 等分配 calc_equal_weights。
    - スコア加重 calc_score_weights（スコア合計が 0 の場合は等分配へフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap（既存保有のセクター別時価を計算して上限超過セクターの新規候補を除外）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear など、未知レジームは警告の上で 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を算出する calc_position_sizes を実装。
    - allocation_method に "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的コスト見積り、スケールダウン後の残余配分ロジックを実装。
- 研究用
  - research/factor_research.py（ファクター計算モジュールを追加）
    - Momentum / Value / Volatility / Liquidity を計算する設計を追加。DuckDB の prices_daily / raw_financials を参照して計算する方針。
    - calc_momentum の基本設計と定数を実装（ただしファイル末尾で途中終了しているため、calc_momentum の実装は未完/続きあり）。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）, 注文成功率（fill_rate）, 送信率（send_rate）, レイテンシ（avg/max/P95）等を集計し PASS/FAIL 判定を行う。
    - デフォルトしきい値を定義（例: 稼働率 >= 99%、fill_rate >= 90%、P95 レイテンシ <= 200 ms）。
    - --from / --to / --db オプション対応、PAPER_TRADING_SQLITE_PATH 環境変数の優先度処理。
- パッケージ構成
  - __all__ の整理と portfolio/pakg のエクスポートを追加。

Changed
- 環境変数ロードの振る舞いを明確化
  - プロジェクトルート探索 (.git / pyproject.toml) に基づく .env 自動ロードを追加。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できる。
  - .env.local を優先して .env を上書きする挙動を採用（ただし OS 環境変数は常に保護）。
- ログ出力の標準化
  - setup_logging により、全起動スクリプトで統一的に stdout とローテーティングファイルへの出力を行うように変更。
  - StreamHandler は stdout を使用（stderr ではない）ため cron 等でのリダイレクト運用に配慮。

Fixed
- MONITOR_POLL_INTERVAL の不正入力対策
  - 0 以下や非整数の値が設定された場合にデフォルトに戻し、警告を出力して time.sleep の例外を回避する処理を追加。
- .env パーサの堅牢化
  - export KEY=val 形式のサポート、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの扱い（クォートなしでは '#' 前の空白でコメント認識）を実装。

Security
- 環境変数 .env の取り扱いに関して注意喚起を追加（config_setup が .env を生成する際に Git コミットしないようドキュメント化）。

Notes / Known issues / TODO
- research/factor_research.py の calc_momentum 実装がファイル末尾で途中終了しており未完です。今後メソッド本体の完成および他ファクター（Value, Volatility, Liquidity）の具体実装を追加予定。
- position_sizing の価格欠損（price が 0.0 の場合）でエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値や取得原価等のフォールバック価格導入を検討。
- 一部の機能（BrokerClientFactory、ExecutionEngine、SystemMonitor など）は外部実装に依存します。実動作はそれらの実装により左右されます。
- Windows / POSIX ともにプロセス優先度や CPU affinity の設定は権限に依存するため、実行環境でのアクセス権限によっては設定できない場合があります（警告を出力してスキップ）。

終わり。

<!--
バージョン管理における将来の運用メモ:
- 次回リリースでは research モジュールの完成、Broker/Engine の統合テスト、監視・検証ツールの出力フォーマット（JSON/CSV）追加を目標とすることを推奨します。
-->