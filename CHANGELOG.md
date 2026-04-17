# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このリポジトリの初回リリース履歴をコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース

### Added
- 全体
  - パッケージ初回公開。バージョンは `0.1.0` に設定。
  - コマンドライン / スクリプトとして利用可能なエントリポイントを複数提供。
  - デフォルトのデータファイル配置は project_root/data 以下（例: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）。

- 実行・監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の Mock ブローカを使用し、DB を本番と分離（デフォルト DB: data/paper_trading.db）。
    - 発注エンジンは OrderRepository, OrderManager, RiskManager, Reconciler 等のコンポーネントを組み立てて起動。
    - execution.pid を使用した PID 管理および data/stop_requested.flag による停止制御をサポート。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - stop フラグ（data/stop_requested.flag）検知で安全にループを終了。

- 設定管理
  - config: 環境変数読み込み・ラッパー実装。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数を保護しつつ .env / .env.local の読み込み順をサポート。
    - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DB パス、監視しきい値、環境判定など）。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等の環境変数をサポート。値チェックやデフォルト値を明示。
    - settings インスタンスをデフォルトエクスポート。

  - config_setup: 対話式ウィザードで .env を作成/更新する CLI を追加。
    - J-Quants トークン、kabu API パスワード、DB パス、ログレベル、KILL_FLAG_CLEAR_ON_START 等の設定項目を対話的に編集可能。
    - 既存 .env の読み込みと、シークレット項目のマスク表示、保存確認をサポート。

  - validate_config: 設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリの存在チェック、config/*.yaml の存在・パース検証（PyYAML 利用時）など。
    - --strict フラグで警告を失敗扱いにするモードを提供。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 小さい方優先）で上位 N を選択。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア比率による重み計算。全スコアが 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック。既存保有を基に上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバックし警告を出力。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を算出。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケールダウン、コストバッファの考慮、残差のロット単位での再配分ロジックを実装。
  - portfolio パッケージは上記関数群をエクスポート。

- 研究 / ファクター計算
  - research.factor_research:
    - DuckDB 接続を受け取り、prices_daily / raw_financials を用いて各種ファクターを計算する設計を導入。
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離率を算出（データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR（atr_pct）、20日平均売買代金、出来高比率などの算出を含む（関数設計と SQL を実装）。
    - DuckDB ベースのデータ取得により外部 API へアクセスせずにファクターを計算。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度（high/normal/low）を設定。権限不足や未対応環境では警告を出力してスキップ。
    - set_cpu_affinity: カレントプロセスの CPU affinity を最初の N コアに固定するユーティリティ（引数 None で何もしない）。入力チェックと例外ハンドリングあり。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成 CLI を追加。
    - 指標: 稼働率（uptime）, 注文成功率(fill_rate), 送信率(send_rate), P95 レイテンシ等を計算して PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 99.0%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms）。
    - --from/--to/--db オプションで期間・DB パスを指定可能。PAPER_TRADING_SQLITE_PATH 環境変数も参照。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の取り扱いについて、.env は Git にコミットしない旨を config_setup の出力で注意喚起。

### Notes / Implementation details
- 監視・実行スクリプトはいずれもプロセス優先度を最初に設定することで実行安定化を図る設計。
- モジュール設計は副作用を極力排除（portfolio の関数群などは DB 非依存の純粋関数）し、テスト容易性を考慮した構成。
- DuckDB と SQLite を併用する設計。DuckDB は分析用（prices_daily 等）、SQLite は監視・注文ログ用を想定。
- .env 自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。

今後の予定例（推測）
- 継続的なユニットテスト追加、CI 設定
- BrokerClient 実装の詳細化・外部 API 統合
- strategy / execution のさらなる実装とドキュメント整備

-----------------------------------------------------------------------------
参考: リポジトリ内の主要コマンド
- python -m kabusys.config_setup         # .env ウィザード
- python -m kabusys.validate_config      # 設定検証
- python -m kabusys.run_execution        # ExecutionEngine 起動スクリプト
- python -m kabusys.run_monitoring       # SystemMonitor 起動スクリプト
- python -m kabusys.tools.paper_verification_report  # ペーパートレード検証レポート生成

-----------------------------------------------------------------------------
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートは必要に応じて差し替えてください。）