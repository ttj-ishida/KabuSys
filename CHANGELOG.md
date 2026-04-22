# Changelog

全ての変更は「Keep a Changelog」準拠で記載しています。日付・バージョンはコード内容から推測して付与しています。

## [0.1.0] - 2026-04-22

Added
- 初期リリースとして次の主要機能・モジュールを追加。
  - 実行・監視スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
      - KABUSYS_ENV が `paper_trading` の場合、専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）へ記録し、MockBrokerClient を使用して本番 DB と分離する設計。
      - 実行中の停止はプロジェクトルート配下の data/stop_requested.flag を確認して行う。実行 PID を data/execution.pid に保存（Engine が pid_file を使用）。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。プロセス優先度を "high" に設定。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出す。
      - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path（デフォルト: data/monitoring.db）を使用するよう明記。
      - 停止フラグ（data/stop_requested.flag）検知でループを終了。
  - 設定管理
    - config.py
      - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env の読み込み順は OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護される。
      - 複雑な .env 行のパースに対応（export 形式、クォート内のエスケープ、インラインコメントの扱いなど）。
      - Settings クラスにより各種環境変数をプロパティで提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、各種しきい値など）。
      - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）および LOG_LEVEL のバリデーション。
  - 設定支援・検証ツール
    - config_setup.py
      - 対話式ウィザードで .env の初期作成・更新を支援。既存値の読み込み、シークレット値のマスク表示、選択肢サポート、保存の確認など。
      - 生成される .env のテンプレートに主要設定項目を網羅（J-Quants、kabu API、DuckDB/SQLite パス、LINE 通知、ログレベル、Kill Switch の自動クリア設定等）。
    - validate_config.py
      - 起動前チェック用 CLI を追加。必須環境変数未設定やプレースホルダ値の検出、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在、config/*.yaml の存在・パースチェック（PyYAML がない場合はスキップして警告）などを出力。
      - --strict モードで警告を FAIL 扱いにできる。
  - ロギング・プロセス管理ユーティリティ
    - utils/logging_setup.py
      - 共通のロギング初期化関数 setup_logging を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
      - ログディレクトリは LOG_DIR 環境変数や引数で変更可能。ファイルハンドラ作成に失敗した場合はコンソール出力のみで継続。
      - stdout を使用する理由や既存ハンドラのクリーンアップ処理を実装。
    - utils/process_priority.py
      - psutil を用いてプラットフォーム非依存にプロセス優先度を設定するユーティリティを追加（"high"/"normal"/"low"）。Windows と POSIX（Linux/Mac/FreeBSD）を考慮した実装。
      - CPU affinity を設定する set_cpu_affinity 関数も提供（指定コア数が利用可能コア数を超える場合は全コア使用の扱い、エラー時は警告でスキップ）。
  - ポートフォリオ構築（純粋関数）
    - portfolio/portfolio_builder.py
      - 候補選定 select_candidates（スコア降順、同点は signal_rank 昇順）、等重み calc_equal_weights、スコア重み calc_score_weights（全スコア0時は等重みへフォールバック）を実装。
    - portfolio/risk_adjustment.py
      - apply_sector_cap：セクター集中が閾値（デフォルト 30%）を超える場合、新規候補を除外するロジック。unknown セクターは上限適用除外。
      - calc_regime_multiplier：market regime に応じた資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告の上 1.0 にフォールバック。
    - portfolio/position_sizing.py
      - calc_position_sizes：allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算。リスクベースの計算、単元株（lot_size）丸め、per-position 上限・aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残差に基づく追加配分ロジックを実装。
    - portfolio パッケージで上記関数をエクスポート。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から統計を集計し、稼働率・注文成功率（Filled/Created）・送信率（Sent/Created）・レイテンシ（avg/max/P95）・リスク却下数を算出してレポート出力する CLI を追加。
      - CLI オプション: --from / --to（YYYY-MM-DD）/ --db をサポート。
      - デフォルトの合格基準（しきい値）を定義：稼働率 >= 99.0%、注文成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。判定 PASS/FAIL を出力。
  - リサーチ（ファクター計算）
    - research/factor_research.py（骨子を実装）
      - モメンタム・ボラティリティ等のファクター計算方針を実装。DuckDB の prices_daily / raw_financials を利用し、純粋関数として (date, code) をキーとする結果を返す設計。
      - （ファイル末尾で途中切れあり：Momentum 計算関数の実装が始まっている段階）
  - パッケージ情報
    - __init__.py にバージョン __version__ = "0.1.0" と主要サブパッケージの __all__ を追加。

Changed
- なし（初回リリースのため既存機能からの変更はなし）。

Fixed
- なし（初回リリース）。

Known issues / Notes
- monitoring は意図的に KABUSYS_ENV に関わらず production 用 sqlite_path を使用する旨が明記されているため、運用時に期待と異なる DB を参照しないよう注意が必要。
- position_sizing の一部処理（価格が欠損時のフォールバック）は TODO コメントあり。price が 0.0 の場合にエクスポージャーが過少見積りされる可能性があるため将来的に前日終値や原価のフォールバックを検討する必要あり。
- research/factor_research.py の Momentum 関数はファイル末尾で途中（start_da…で切れている）ため、完全実装は次リリースで補完予定。
- ログディレクトリ作成やプロセス優先度設定は権限不足で失敗する可能性があるが、いずれも警告を出してフェールセーフでスキップする設計。

Security
- なし（現時点で明示的な脆弱性対応はなし）。シークレット情報（トークン・パスワード）は .env に保存する設計だが .env を Git にコミットしないよう README/生成テンプレートで注意喚起すること。

-- 
今後のリリース予定（例）
- research モジュールの完全実装（ファクター計算の完成）
- ExecutionEngine / SystemMonitor のユニットテスト追加およびエラーハンドリング強化
- 監視・発注のメトリクス収集とダッシュボード連携機能の追加