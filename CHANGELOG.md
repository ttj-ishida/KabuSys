CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベース（バージョン 0.1.0）の機能追加・変更点をソースコードから推測して日本語で記載しています。

注記
-----
- 日付は本 CHANGELOG 作成日です: 2026-04-24
- 実装の解釈に基づく記載が含まれます（コメントや docstring から推測）。

[0.1.0] - 2026-04-24
-------------------

### Added
- 全体
  - 初期リリース相当の機能群を追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を導入。

- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。以下をサポート:
    - BrokerClientFactory によるブローカークライアント生成。
    - paper_trading 環境では専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による外部停止フラグ検知で安全に停止可能。
    - PID ファイル (/data/execution.pid) をサポート。
    - RiskManager, OrderManager, Reconciler, OrderRepository の組み立てロジックを統合。
    - RiskConfig のデフォルトパラメータをコードに明示（max_position_pct, max_utilization, rate_limit_per_sec など）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。以下をサポート:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する旨を明示。
    - 外部停止フラグ（data/stop_requested.flag）検知、例外発生時のログ出力とループ継続処理。
    - 起動時にプロセス優先度を high に設定。

- 設定管理
  - config.py: 環境変数読み込み・設定管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード（.env → .env.local の順、OS 環境変数は保護）。
    - _parse_env_line によりシングル/ダブルクォート、エスケープ、export プレフィックス、インラインコメント等を考慮した .env パーサを実装。
    - Settings クラスで各種設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, PID/KILL フラグパス, 監視閾値等）をプロパティとして提供。
    - PAPER_FILL_MODE（paper trading の fill 動作）や PAPER_TRADING_SQLITE_PATH 等の設定を追加・検証。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。

  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 各設定項目の説明・デフォルト・選択肢を提示し .env を生成/更新可能。
    - 秘匿項目はマスク表示。
    - 保存前の確認を実施。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の有無と YAML パース検証（PyYAML が存在する場合）。
    - KABUSYS_ENV=live に対する追加警告（LINE 通知設定や Kill Switch 設定等）。
    - --strict モードで警告を FAIL 扱い可能。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーの統一セットアップ関数 setup_logging を追加。
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - LOG_DIR / LOG_LEVEL の優先順位解決を実装。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
  - utils/process_priority.py:
    - set_process_priority(level) による Windows/Linux/macOS 向けの優先度設定を追加（psutil 利用）。
    - set_cpu_affinity(cpu_count) による CPU アフィニティ固定をサポート。
    - 権限不足や未対応 OS では警告を出してスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - シグナルのソーティング（score 降順、signal_rank でタイブレーク）、候補選定（max_positions）。
    - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - セクター別上限チェック apply_sector_cap（既存保有のセクターエクスポージャを計算し超過セクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマップと未知レジームのフォールバック）。
  - portfolio/position_sizing.py:
    - allocation_method（risk_based / equal / score）に応じた株数決定ロジックを実装。
    - 単元株（lot_size）処理、1 銘柄上限や aggregate cap、cost_buffer（手数料・スリッページ見積）を考慮したスケールダウンと端数処理（残余キャッシュでの lot 単位追加配分）。

- 研究・ツール
  - research/factor_research.py: DuckDB 接続を受け取るファクター計算モジュール（モメンタム・MA200・ATR 等）を追加。コメントに仕様とスキャン範囲が明記（実装途中の箇所あり）。
  - tools/paper_verification_report.py:
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）等の指標を算出し PASS/FAIL 判定を実施。
    - デフォルト DB: data/paper_trading.db、閾値はファイル内で定義（稼働率 99%、fill_rate 90% 等）。
    - --from/--to/--db オプション対応。

### Changed
- ロギングとファイル出力
  - デフォルトで stdout を利用する StreamHandler を設定し、ファイルハンドラはログディレクトリ作成成功時のみ追加するように設計（ログ出力の堅牢性向上）。

- .env 自動ロードの動作
  - 自動ロード時に OS 環境変数を保護（.env.local の override 時も OS 環境変数は上書きされない）する実装を導入。

- run_monitoring / run_execution の共通挙動
  - 起動時にプロセス優先度を High に設定する呼び出しを追加（set_process_priority("high")）。

### Fixed
- .env パーサの堅牢化
  - 引用符付き値中のバックスラッシュエスケープ、対応する閉じクォートの検索、インラインコメント無視などに対応して .env の解析精度を向上。
  - export プレフィックスの取り扱いをサポート。

- 停止フラグ検知の一貫化
  - run_execution.py と run_monitoring.py で data/stop_requested.flag による外部停止処理を実装し、強制終了時の安全な後片付けを改善。

### Security
- 機密情報の扱い
  - config_setup の対話でシークレットは表示をマスクし、.env 生成時に .env をコミットしない旨を README 風のヘッダで強調。
  - Settings で必須トークンを取得する際に未設定なら明示的に例外を送出し、誤設定で起動しないようにした。

### Deprecated
- なし（初期リリース相当のため該当なし）。

### Removed
- なし。

互換性 / デプロイに関する注意点
------------------------------
- 監視（run_monitoring）は「環境にかかわらず」本番用の sqlite_path を参照するように設計されているため、開発環境で監視を動かす際は sqlite_path の上書きに注意してください。
- Paper Trading 用 DB は paper_trading 環境で分離（PAPER_TRADING_SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 環境変数）されています。運用時に本番 DB と混同しないよう設定を確認してください。
- 起動時にプロセス優先度を変更します。権限不足で設定に失敗した場合は警告が出力されますが、動作自体は継続します。
- ログディレクトリ作成に失敗した場合はコンソールログのみで継続します。必要に応じて LOG_DIR 環境変数を設定してください。
- .env 自動ロードはデフォルトで有効です。テスト等で自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

今後の改善候補（ソースコードからの提案）
---------------------------------------
- research/factor_research.py の実装継続（ファクター計算の完成・単体テスト整備）。
- position_sizing の lot_size を銘柄別に扱うための拡張（stocks マスタ参照）。
- apply_sector_cap の price 欠損時フォールバック（前日終値や取得原価の使用）実装。
- ロギングのテスト容易化のため、setup_logging にハンドラの注入ポイント（外部テスト用）を追加。
- PyYAML 非インストール環境でも config/*.yaml のフォーマット検証を行える代替手段の検討。

以上。必要であれば、リリースノートの英語版やセクション別に詳細なデプロイ手順・環境変数一覧を作成します。