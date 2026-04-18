CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  
日付はリリース日または変更日を記載しています。

0.1.0 - 2026-04-18
-----------------

Added
- 全体
  - 初期公開リリース。パッケージバージョンは __version__ = "0.1.0"。
  - プロジェクトの基本的な実行/設定ツール、ポートフォリオ構築、検証ツール、ユーティリティを提供。

- 実行・監視関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを生成し、OrderRepository, OrderManager, RiskManager, Reconciler 等の依存コンポーネントを組み立て、ExecutionEngine を別スレッドで実行。
    - 停止フラグ (data/stop_requested.flag) を監視し、検知時には安全に engine.stop() を呼び出してシャットダウンする。
    - 実行 PID を data/execution.pid に書く想定（pid_file を使用）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値はログ警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して接続（monitoring 用テーブルの初期化を実行）。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了、KeyboardInterrupt にも対応してクリーンに終了。
    - run_monitoring/run_execution ともに開始時に set_process_priority("high") を呼び出してプロセス優先度を上げる。

- 設定・CLI
  - config.py: 環境変数/設定管理モジュールを追加。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出して .env/.env.local を自動読み込み（OS 環境変数を保護）。
    - .env パーサは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント処理に対応する堅牢な実装。
    - Settings クラスにより各種設定値をプロパティ経由で取得。パスは Path オブジェクトで返す（expanduser を適用）。
    - Paper Trading 向け設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）や監視閾値、PID/KILL フラグのパス等を管理。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env ロード無効化をサポート。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 対話で主要設定を入力・既存値の再利用、シークレットは表示マスク、最終確認後に .env を安全に書き出し。
    - .env 作成時に注意書き（.env を Git にコミットしない等）を出力。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在確認、プレースホルダの検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がインストールされている場合）。
    - KABUSYS_ENV=live 時の注意喚起（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性等）。
    - --strict を指定すると警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順・タイブレーク処理で上位 N を選択。
    - calc_equal_weights: 等金額配分計算。
    - calc_score_weights: スコア比率で重みを計算（全スコアが 0 の場合は等配分にフォールバックして警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存保有比率を計算し、指定比率を超えるセクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金の乗数を返す（bull/neutral/bear 対応、未知レジームはフォールバックして警告）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の配分方式をサポートし、lot_size（単元株）で丸め、max_position_pct/per-position cap、aggregate cap（available_cash）を考慮したスケーリングと残余配分ロジックを実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮して保守的なコスト試算を行う。

- ツール類
  - tools.paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 指定期間（--from / --to）または DB 全体を対象に、稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計して PASS/FAIL 判定する。
    - デフォルト DB パスは data/paper_trading.db。--db で上書き可能。
    - P95 計算、各種 SQL クエリと N/A の扱い・OperationalError に対するフォールバックを実装。
    - 合格基準（閾値）をファイル冒頭に定義（稼働率 >= 99%、fill >= 90% 等）。

- ユーティリティ
  - utils.logging_setup: 統一的なロギング設定ユーティリティを追加。
    - ルートロガーに stdout 向け StreamHandler（stdout を使用）と TimedRotatingFileHandler（day rotation、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils.process_priority: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX 間の差分を吸収（nice 値 / Windows priority class を用いる）、set_process_priority("high"|"normal"|"low") と set_cpu_affinity を提供。
    - 権限不足や未実装のケースでは警告を出して安全にスキップ。

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Security
- .env ファイルは生成メッセージで Git へ絶対にコミットしない旨を明記。
- config_setup の対話でシークレット項目はマスク表示。

Notes / Breaking changes
- run_monitoring は「監視用 DB 接続」において KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。運用時に監視 DB を分離したい場合は Settings 側の設定（SQLITE_PATH）を注意して指定してください。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と厳格に分離する設計です。
- .env 自動ロードはプロジェクトルートの検出に依存します。配布後に自動ロードを行いたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

未完 / TODO（今後の改善候補としてコード内に記載）
- portfolio.position_sizing: 将来的に銘柄別 lot_size のサポート（マスタデータ参照）を予定。
- risk_adjustment.apply_sector_cap: price 欠損時のフォールバック（前日終値や取得原価）を導入することでエクスポージャー計算の信頼性向上が可能。
- research.factor_research: ファイルが途中で切れている（calc_momentum の実装途中）。DuckDB ベースのファクター計算は設計に沿って継続実装予定。

以上。今回のリリースでは「実行/監視のデーモン起動」「設定管理/検証」「ポートフォリオ構築の純粋関数群」「Paper Trading 検証レポート」「ロギング・プロセス優先度ユーティリティ」が主要な追加機能です。