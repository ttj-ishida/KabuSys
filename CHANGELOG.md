# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトではセマンティックバージョニングを採用しています。

最新の変更
------------

### [Unreleased]

- （なし）

過去のリリース
---------------

### [0.1.0] - 2026-04-19

初回リリース。以下の主要機能・モジュールを追加しました。

Added
- 基本アプリケーション情報
  - パッケージメタ情報: __version__ = "0.1.0" を導入。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし、警告出力。
    - 停止はプロジェクトルート/data/stop_requested.flag ファイルの存在で検知。
    - 監視は環境にかかわらず本番の sqlite_path を使用して DB に接続。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の MockBrokerClient を使用し、data/paper_trading.db（デフォルト）に記録して本番 DB と分離。
    - 停止フラグ・PID 管理・スレッド実行の仕組みを実装。

- 設定管理
  - config.py: 環境変数/​.env 読み込みと Settings クラスを実装。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の解析は export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントのルールに対応。
    - Settings に各種設定プロパティを定義（J-Quants / kabu API / LINE / DuckDB/SQLite パス / paper trading 設定 / 監視閾値等）。
    - PAPER_FILL_MODE の許容値チェック、KABUSYS_ENV/LOG_LEVEL の検証ロジックを含む。
    - デフォルトパス: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PAPER_TRADING_SQLITE_PATH=data/paper_trading.db。

- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env ウィザードを実装。既存 .env 読み込み、シークレットのマスク表示、.env テンプレート生成。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値確認、DB パスの親ディレクトリ存在チェック、PyYAML が有れば YAML のパース検証を実行。
    - KABUSYS_ENV=live の場合の追加注意チェック、--strict モード（警告を失敗扱い）をサポート。

- ロギング / プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログローテーションは日次、バックアップ 30 日。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応するマッピングを用意。set_process_priority("high"|"normal"|"low") で現在プロセスの優先度設定を試行。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアへ固定する機能を提供（権限や環境により失敗を許容して警告出力）。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: score 降順、同点は signal_rank 昇順で候補選定。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率配分（全スコアが 0 の場合は等配分へフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮し、上限超過セクターの候補を除外）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: market レジーム ("bull"/"neutral"/"bear") に応じた投下資金の乗数。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method=("risk_based"|"equal"|"score") をサポートした株数計算を実装。
      - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）や aggregate cap（available_cash） を適用。
      - cost_buffer により手数料・スリッページを保守的に見積もり、合計コストが available_cash を超える場合はスケールダウン＋端数処理（lot_size 単位で残余配分）。
      - risk_based モードは risk_pct / stop_loss_pct を用いたポジションサイズ計算。
      - 将来的な拡張（銘柄別 lot_size）の TODO を注記。

- 監視・モニタリング関連
  - monitoring モジュールへの初期連携（init_monitoring_db の呼び出し等）。
  - 監視ループ／実行エンジンはモニタリングテーブルが存在することを保証してから動作する実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。
    - SQLite（デフォルト data/paper_trading.db）からデータを集計し、稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（平均/最大/P95）等を算出。
    - P95 は独自実装で算出。日付フィルタ（--from/--to）と --db オプションをサポート。
    - 判定基準（デフォルト閾値）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

Changed
- （初回リリースのため過去変更なし）

Fixed
- （初回リリースのため過去修正なし）

Security
- （該当なし）

Notes / 実装上の注意
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされる（配布後の環境で安全）。
- Settings の一部プロパティは未設定時に ValueError を投げる（必須値の明示的検出を容易にする）。
- ログディレクトリ作成に失敗した場合でもアプリはコンソールログのみで継続可能（安全にフォールバック）。
- run_execution と run_monitoring は stop フラグ（data/stop_requested.flag）や PID ファイルを使用してプロセス制御を行う。運用時の停止フラグ設定により安全に終了可能。
- 一部モジュール（research/factor_research.py 等）はファクター計算の基礎を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。

既知の改善余地 / TODO
- position_sizing: 銘柄別の lot_size をサポートする設計への拡張を想定（コメントで TODO）。
- apply_sector_cap: price_map に価格欠損（0.0）がある場合のフォールバック戦略が未実装（コメントで注記）。
- research モジュールの実装はさらなるファクター整備・テストが必要。
- 本番運用時の Guard（kill flag, LINE 通知等）設定を validate_config で注意喚起するが、運用ドキュメントで詳細な運用手順を整備することを推奨。

付記
- この CHANGELOG はコードベース定義（ソースファイルの実装内容）から推測して作成しています。実際の変更履歴やリリースノートはプロジェクトの管理ポリシーに合わせて適宜調整してください。

[0.1.0]: v0.1.0 - 2026-04-19