CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベースの内容から推測した変更点・追加機能を日本語で記載しています。

目次
-----
- [Unreleased](#unreleased)
- [0.1.0](#010)

Unreleased
----------
（現在の差分なし）

0.1.0
-----
初期リリース（機能実装の第一弾）。以下の主要機能・改善点を含みます。

Added
-----
- 全体
  - KabuSys 自動売買システムの初期実装を追加。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 起動スクリプト / ランタイム
  - run_execution.py: 実行エンジン起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御: data/execution.pid、data/stop_requested.flag による停止フラグ検出と安全なシャットダウン処理を実装。
  - run_monitoring.py: SystemMonitor をポーリング実行する監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視 (monitoring) は環境にかかわらず本番用 sqlite_path を使用する（監視データは本番 DB に記録）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - check_once() 実行時に例外が発生してもログ出力して次のポーリングに進む堅牢性を実装。

- 設定管理
  - config.py: .env 自動読み込み機能と堅牢なパーサーを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）により .env / .env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env の行パースで export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントの取り扱いをサポート。
    - Settings クラスを提供し、必要な設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）・パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）・各種閾値・フラグをプロパティとして取得可能。
    - PAPER_FILL_MODE の値検証（"instant"|"partial"|"never"|"reject" のみ許可）や KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
    - pid_file_path, kill_flag_path, kill_flag_clear_on_start 等の監視用設定を公開。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 既存 .env 読み込み、秘密値はマスク表示、選択肢とデフォルトのサポート、最終確認後に .env を書き出し。
    - 生成された .env に関する注意書き（Git にコミットしない）を含む。

- 設定検証ツール
  - validate_config.py: 起動前の設定検証スクリプトを追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・（PyYAML があれば）パース検証を実施。
    - --strict オプションを追加（警告を FAIL として扱う）。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - setup_logging 関数を追加。全起動スクリプトで共通のログ設定を提供。
    - stdout への StreamHandler（標準出力）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 既にハンドラがある場合は一度クリアしてから再設定し、二重出力を防止。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
  - utils/process_priority.py:
    - set_process_priority(level) を追加。Windows / POSIX（Linux/Mac/FreeBSD）を吸収して優先度を設定（psutil 使用）。
    - set_cpu_affinity(cpu_count) を追加してプロセスを最初 N コアにピン留め可能。
    - 権限不足や非対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選抜（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装（スコア合計が 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャを計算し、セクター上限を超える場合に新規候補を除外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: weights / candidates / 各種パラメータに基づき発注株数を決定するロジックを実装。
    - risk_based / equal / score 対応、単元株（lot_size）丸め、1 銘柄上限・全体キャップのスケーリング、cost_buffer（手数料・スリッページ見積り）考慮、残余キャッシュに基づく再配分ロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計し、PASS/FAIL 判定のレポートを標準出力に出力。
    - 日付フィルタ（--from/--to）、閾値（稼働率 99%、成立率 90% など）を組み込み。DB が存在しない場合はエラーメッセージを表示。

- 解析 / 研究用モジュール（着手）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum 等の計算方針を実装）。（ファイル中に計算ロジックのスケルトンを含む）

Changed
-------
- ロギング
  - 既存ハンドラの再初期化処理を行い、複数回 setup_logging を呼んでもログが二重出力にならないようにした。
  - コンソール出力は stderr ではなく stdout を使用（cron / Task Scheduler での扱いやすさを考慮）。

- .env 読み込み順序
  - OS 環境変数 > .env.local > .env の優先順位で環境変数を解決する仕組みを導入。OS 環境変数は保護され、.env.local で上書き可能。

Fixed
-----
- 起動スクリプトの堅牢性向上
  - run_monitoring のポーリングループで check_once() が例外を投げた場合にループ全体が停止しないように例外捕捉とログ出力を追加。
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時に、プロセスが致命的に停止しないようにフォールバック動作（コンソールのみ）を実装。

Deprecated
----------
- なし

Removed
-------
- なし

Security
--------
- 環境変数や .env の取り扱いに関して、秘密情報はウィザードでマスク表示するなど注意喚起を行う（.env を Git にコミットしない旨の注記を出力）。

Notes / 補足
------------
- 一部モジュール（例: research/factor_research.py）は実装途中（スケルトン・計算方針の記述）であり、今後の拡張（完全なファクター計算ロジックなど）が想定されます。
- validate_config は PyYAML の有無で挙動が変わり、PyYAML 未インストール時は YAML のパース検証をスキップして警告を出します。
- process_priority / CPU affinity の設定はプラットフォームや権限に依存するため、失敗した場合は警告を出してスキップします（安全設計）。

今後の TODO 想定
----------------
- factor_research の完成（Value, Volatility, Liquidity 等の実装）。
- execution / monitoring のテストカバレッジ拡充、エラー・再試行戦略の強化。
- per-stock lot_size の銘柄別対応（stocks マスタとの連携）。
- より詳細な監視アラート（LINE 通知連携など）の実装強化。