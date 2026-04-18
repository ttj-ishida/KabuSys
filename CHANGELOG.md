# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトの初期リリースに相当する変更点は、ソースコードの実装内容から推測して記載しています。

フォーマット:
- Unreleased: 今後の変更予定
- 各バージョン: 日付付き（YYYY-MM-DD）

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初回リリース想定。システム全体の基盤機能（設定管理、ログ、プロセス管理、実行エンジン、監視、ポートフォリオ構築、検証ツールなど）を実装。

### Added
- 全体
  - パッケージ初期化とバージョン定義を追加（kabusys/__init__.py: __version__ = "0.1.0"）。
- 設定管理
  - 環境変数読み込み・管理モジュールを追加（kabusys.config）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env の行解析で export 形式、クォート文字列、エスケープ、インラインコメント等に対応する堅牢なパーサを実装。
    - Settings クラスでアプリ設定をプロパティとして提供（DB パス、API トークン、Paper Trading 設定、監視しきい値、環境種別判定など）。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH のサポートを追加。
- 設定ユーティリティ
  - 対話式 .env 作成ウィザードを追加（kabusys.config_setup）。
    - 秘密値はマスク表示、既存値の再利用、デフォルト値提示、保存前の確認などを実装。
    - .env 書き出しテンプレートを提供（Git にコミットしない旨の注意含む）。
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict モードで警告を失敗扱いにできる。
- 実行・監視エントリポイント
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading 時に専用の paper_trading DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせて ExecutionEngine を起動。
    - PID ファイル、停止フラグ（data/stop_requested.flag）の検出・処理、スレッド監視と安全停止処理を実装。
  - SystemMonitor ポーリングループ起動スクリプト（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は設定にかかわらず本番 sqlite_path を使用して監視テーブルを操作。
    - 停止フラグの検出、例外発生時のログ出力と次ポーリングへの復帰、KeyboardInterrupt のハンドリング。
- ログ・プロセス管理ユーティリティ
  - ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でのファイル出力（logs/<app_name>.log）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順（関数引数 > LOG_LEVEL 環境変数 > デフォルト）。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX の差分を吸収して priority（high/normal/low）を設定。CPU affinity を最初の N コアに固定する機能も提供。
    - 設定に失敗した場合は警告を出力して安全にスキップ。
- ポートフォリオ構築
  - 銘柄選定と重み計算（kabusys.portfolio.portfolio_builder）。
    - select_candidates（スコア降順・タイブレーク処理）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等分にフォールバック）を実装。
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）。
    - apply_sector_cap: 既存保有のセクター別エクスポージャ計算に基づき、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは 1.0 でフォールバックして警告。
  - 株数決定・リスク制限・単元丸め（kabusys.portfolio.position_sizing）。
    - allocation_method="risk_based" / "equal" / "score" をサポート。lot_size（単元）で丸め、1銘柄上限や aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - スケーリング時に残差の大きい銘柄から lot 単位で追加配分するロジックを実装。
    - cost_buffer による保守的なコスト見積りを考慮。
- 研究・指標計算（部分実装）
  - ファクター計算モジュール（kabusys.research.factor_research）を追加（モメンタム、移動平均、ATR、流動性等を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - paper_trading DB（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ、欠損テーブル・操作時の安全フォールバックを実装。

### Changed
- 設計上の決定（実装に基づく挙動）
  - 監視プロセスは環境に関係なく本番用 sqlite_path を使用して監視データを記録する（運用観点で常に本番監視を参照する設計）。
  - 実行エンジンは paper_trading モード時に paper_trading 用の SQLite DB を使用して本番データと完全分離する（テスト/検証を容易にするため）。
  - ログはデフォルトで logs/ 以下に日次ローテーションで保存され、30 日分保持するように設定。
  - .env 自動ロードの優先順位は OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。既存の OS 環境変数は保護され上書きされない。
  - プロセス起動時に優先度を "high" に設定する呼び出しを実行スクリプトで行う（run_execution / run_monitoring）。

### Fixed / Improved
- .env パーサの堅牢化
  - export 付き行、シングル/ダブルクォート内のエスケープ、コメントの解釈などに対応して .env の読み込みを堅牢化。
- エラー耐性
  - run_monitoring のポーリングループで check_once() が例外を投げてもループ継続するように例外捕捉とログ出力を追加。
  - DB 接続やファイルハンドラ作成に失敗した場合は適切にフォールバック（コンソールログのみ等）してプロセスを継続する設計に改善。

### Security
- .env に関する注意
  - config_setup で生成される .env は絶対に Git にコミットしない旨のヘッダを付与。
  - Settings._require により必須環境変数が未設定の場合は ValueError を投げて早期検出する。
- 実運用ガード
  - validate_config は KABUSYS_ENV=live の場合に LINE の通知設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告する。

### Known limitations / TODO
- position_sizing: 銘柄ごとの lot_size を将来的にサポートする旨の TODO コメントあり（現状は全銘柄共通の lot_size を想定）。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャが過少見積もりされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨のコメントあり。
- research.factor_research: ファイルが途中で未完の箇所（トランケーション）あり。DuckDB 経由のファクター算出ロジックは実装を継続する必要あり。
- 一部の外部依存（psutil, duckdb, PyYAML 等）が存在し、環境によってはインストールが必要。validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出す。

---

（注）本 CHANGELOG は与えられたソースコードの実装内容から推測してまとめたものであり、実際のコミット履歴やリリースノートを完全に反映するものではありません。必要に応じて日付・カテゴリの調整や詳細な差分（コミット単位）への展開を行ってください。