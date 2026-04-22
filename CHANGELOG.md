# Changelog

すべての注目すべき変更はここに記録します。
フォーマットは "Keep a Changelog" に準拠しています。

- リリース日は YYYY-MM-DD 形式で記載しています。
- これはコードベースの現在の状態から推測して作成した初期リリース履歴です。

## [Unreleased]

（現時点のスナップショットが初回リリースに相当するため、未リリース項目はありません。）

## [0.1.0] - 2026-04-22

初回公開リリース。本リリースでは自動売買システムのコア機能、運用用ユーティリティ、運用支援 CLI / ツール群、ポートフォリオ構築ロジックと基本的なリスク調整／ポジションサイジング機能などを実装しています。

### 追加 (Added)
- コアモジュール
  - kabusys パッケージの初期実装を追加。バージョンは __version__ = "0.1.0".
- 実行系 / エンジン
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離する挙動をサポート。
    - 停止フラグ (data/stop_requested.flag) の検知による安全停止処理を実装。
    - 実行中の PID を data/execution.pid に書き込む仕組み（ExecutionEngine 側の pid_file 引数を渡す）。
- 監視系
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) の検知でループを終了。
    - 監視は KABUSYS_ENV にかかわらず production 用 sqlite_path（デフォルト: data/monitoring.db）を使用する仕様。
- 環境設定 / 検証 CLI
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加（必須/任意項目、シークレット入力の扱い、保存処理）。
  - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML が無い場合はスキップ）、本番向けガードチェック等）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH / --db オプションで上書き可能）。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化配分（スコアが全て 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有エクスポージャー計算、売却予定銘柄の除外、"unknown" セクターは除外免除）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知のレジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算、単元株丸め、per-stock 上限・aggregate cap のスケーリング、cost_buffer（手数料・スリッページ想定）を考慮した計算ロジックを実装。
- データ・分析
  - duckdb を分析用 DB として統合（Settings.duckdb_path を経由）。
  - monitoring 用の SQLite 初期化関数 init_monitoring_db を呼び出して監視テーブルの存在を保証。
- 設定管理
  - config.py: Settings クラスを実装。
    - .env 自動ロード（プロジェクトルートを .git/.pyproject.toml から検出）。ロード順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 解析の堅牢化（export プレフィックス、引用符つき値のエスケープ、インラインコメント処理）。
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL 検証、監視閾値や kill/pid フラグのパス等）。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（アプリ別ログファイルを日次ローテーション、30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加（Windows/Linux/Mac の差分を吸収、set_process_priority/set_cpu_affinity を提供）。権限不足や未対応 OS の場合は警告を出してスキップ。
- 研究用モジュール（着手）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity を対象に設計）。DuckDB を使った計算を想定。注: ファイルの計算ロジックは着手中（スナップショットは未完）。

### 変更 (Changed)
- ロギング / 運用挙動
  - すべての起動スクリプトは setup_logging を呼び出すことで統一的なログ出力を行うよう変更。
  - 起動直後に set_process_priority("high") を呼んでプロセス優先度を上げる（monitoring / execution 起動スクリプト）。
- DB の扱い
  - 監視プロセスは環境にかかわらず本番の sqlite_path を使用する設計（監視データは運用実 DB を参照）。

### 修正 (Fixed)
- .env 読み込みの堅牢化（引用符付き値のバックスラッシュエスケープ、コメント扱いの改善など）により、実運用でのパラメータ読み込みエラーを軽減。
- calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックするように修正（警告ログ出力あり）。
- position_sizing の aggregate cap スケールダウンアルゴリズムで、lot_size 単位で再配分するロジックを実装し、残余キャッシュで配分を補正する機能を追加。

### ドキュメント（簡易） / ヘルプ
- 各 CLI スクリプトに簡易的な usage / help（コマンドライン引数説明）を追加。
  - validate_config.py: --strict オプションを追加（警告を FAIL とみなして exit(1)）。
  - config_setup.py: --env-file オプションで .env 保存先を指定可能。
  - tools/paper_verification_report.py: --from / --to / --db オプションを提供。

### 既知の制限 / TODO
- 一部機能や拡張点に TODO コメントあり:
  - position_sizing: 銘柄ごとの lot_size をサポートするため将来的に stocks マスタの導入を検討。
  - risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、前日終値や取得原価のフォールバックを検討中。
  - research/factor_research.py は未完（calc_momentum の実装開始部でスナップショットが途切れています）。
- 本番での kill/stop フラグの扱いには運用ルールの周知が必要（KILL_FLAG_CLEAR_ON_START の設定は本番で 1 にするのは危険と警告）。

---

開発チームや利用者向けメモ:
- デフォルトファイルパス（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）を使用する場合、起動前に親ディレクトリが存在するか、適切な権限で作成されることを確認してください。
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意喚起を記載）。
- 本リリースは初版のため、運用で発見された問題点や改善要望に基づき順次修正・機能拡張を行っていく予定です。

------
フィードバックや追加の変更履歴要望があれば教えてください。実際のコミット履歴や差分がある場合はそれを元により正確な CHANGELOG を作成できます。