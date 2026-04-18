# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」の形式に準拠します。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除
- Deprecated: 廃止予定
- Security: セキュリティ関連

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加しました。
主に CLI 起動スクリプト、設定管理、ロギング／プロセス管理ユーティリティ、ポートフォリオ構築・発注関連ロジック、検証ツール類を含みます。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py を追加。
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 停止はプロジェクト直下の data/stop_requested.flag によるフラグ検出。
    - Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定。
    - sqlite3 / DuckDB の接続管理と安全なクローズ処理を実装。
  - run_execution.py を追加。
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB（data/paper_trading.db を既定）を使用し、MockBrokerClient による完全分離が可能。
    - BrokerClientFactory を利用したブローカー抽象化、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンドスレッド実行。
    - 停止フラグ（data/stop_requested.flag）検知による安全シャットダウン、実行 PID 管理用ファイルの扱い。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py を追加。
    - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み順: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env の行パーサーは `export KEY=val`、クォート値（シングル/ダブル）のエスケープ、インラインコメントの扱いに対応。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス / 各種閾値 / 環境種別（development/paper_trading/live）などをプロパティ経由で取得。値の検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行う。
    - settings 単一インスタンスをエクスポート。

- 設定関連 CLI
  - validate_config.py を追加。
    - .env や config/*.yaml の設定不備を起動前に検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在とパース検証（PyYAML が無ければ検証をスキップ）などを実施。
    - --strict オプションで警告もエラー扱いにできる。
  - config_setup.py を追加。
    - 対話式ウィザードで .env を生成／更新する CLI。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START, 等）をサポート。シークレット項目はマスク表示。
    - 生成した .env をファイルに書き出すユーティリティを提供。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（アプリ別ログファイル、日次ローテーション、30日保持）を設定。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - StreamHandler は stdout を使う（cron/task scheduler での扱いを考慮）。
  - utils/process_priority.py を追加。
    - set_process_priority(level) で Windows / POSIX を吸収して優先度を設定（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定（未対応環境・権限不足は警告でスキップ）。
    - psutil ベースで実装し、権限不足等は安全に無視する設計。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを実装（起動スクリプトから冪等に監視テーブルを保証）。

- Portfolio 関連（純粋関数群）
  - portfolio/portfolio_builder.py を追加。
    - select_candidates: BUY シグナルをスコア降順・同点は signal_rank 昇順でソートして上位 N を返す。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等金額配分へフォールバックし警告を出す。
  - portfolio/risk_adjustment.py を追加。
    - apply_sector_cap: 既存ポジションのセクター別時価を計算し、1 セクターが指定上限（デフォルト 30%）を超過している場合は当該セクターの新規候補を除外。売却予定銘柄を計算から除外するオプションあり。unknown セクターは上限適用除外。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 でフォールバックし警告。
    - TODO コメント（価格欠損時のフォールバック等）を残す。
  - portfolio/position_sizing.py を追加。
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に基づく発注株数決定ロジック。
      - risk_based: risk_pct, stop_loss_pct を使った per-stock ベースのリスク計算。
      - equal/score: ウェイトに基づく割当。lot_size（単元）で丸め、_max_per_stock による上限考慮。
      - aggregate cap: 全銘柄合計が available_cash を超える場合はスケールダウンを行い、端数（lot 単位）の配分は残余キャッシュと fractional remainder を利用して再配分する（再現性のため安定ソート）。
      - cost_buffer によりスリッページ・手数料分を保守的に見積もる。
    - 発注数は lot_size 単位で丸められる。

- ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading (SQLite DB) から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95））を集計してレポートを生成。
    - P95 の計算、日付フィルタ（--from/--to）、DB パス解決ロジック（--db > 環境変数 > デフォルト）を実装。
    - デフォルトの合格基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定義し、PASS/FAIL 判定を出力。

- リサーチ（計算）基盤
  - research/factor_research.py を追加（モメンタム等ファクター計算の骨格実装）。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity の計算を行う設計方針。
    - モメンタム計算（1M/3M/6M、MA200 乖離）関数の雛形を追加。
    - （ファイル末尾が途中で切れているため実装は継続が必要）

### Notes / Known issues / TODO
- apply_sector_cap: 現状 price_map に価格が欠損した場合（0.0）にエクスポージャーが過少見積りされブロックが外れる可能性がある旨の TODO が残されています。前日終値等を使ったフォールバックの検討が必要です。
- position_sizing: 将来の拡張として銘柄別の lot_size をサポートする TODO が存在します（現状は全銘柄共通 lot_size を想定）。
- research/factor_research.py はファイル末尾が途中で切れています。完全実装・テストを行う必要があります。
- ロギング設定やプロセス優先度設定は権限や環境に依存するため、権限不足時は警告を出して処理をスキップする安全設計になっていますが、期待通り動作しない場合は環境（権限・psutil のバージョン等）を確認してください。

### Usage examples（代表的）
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=30 でポーリング間隔を 30 秒に設定可能
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）

---

今後の改善案（優先度順、計画候補）
- research/factor_research の完全実装とユニットテスト追加
- セクターエクスポージャー計算での価格フォールバック実装
- lot_size を銘柄別に扱うためのマスタ拡張
- 各モジュールの単体テスト充実（特に position sizing のスケーリングロジック、残差配分）
- ドキュメント（API 仕様、運用手順、設定例）の拡充

--- 

（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時には追加の運用上の注意や変更履歴を反映してください。）