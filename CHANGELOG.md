# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

なお、本 CHANGELOG は与えられたソースコードの内容から推測して作成したもので、実際のコミット履歴に依存しない要約です。

## [0.1.0] - 初回リリース (推定)
リリース日: (未指定)

### 追加
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用して監視データを記録。
    - SQLite / DuckDB 接続の初期化、監視 DB スキーマの初期化（init_monitoring_db）を実施。
    - プロセス優先度（"high"）を起動時に設定。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用して実際のブローカークライアントまたはモックを生成。Engine を別スレッドで起動し、停止フラグを監視して安全に停止。
    - Execution 用 PID ファイル（data/execution.pid）を扱う。

- 設定管理・ヘルパー
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env と .env.local の読み込み順序（OS 環境変数 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複数の環境変数をプロパティとして提供（J-Quants、kabu API、LINE、DB パス、監視閾値、KABUSYS_ENV/LOG_LEVEL 判定等）。
    - .env パース機能を強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理等）。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）を追加。

  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。
    - 秘匿情報のマスク表示、デフォルト値・選択肢対応、.env ファイルテンプレート出力を実装。
    - 中断時の安全な取り扱い（入力中の Ctrl-C / EOF 等）をサポート。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が無い場合は警告）が可能。
    - --strict オプションにより警告を FAIL 扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギングセットアップ関数を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順序（引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ実行。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定ユーティリティを追加（psutil 利用）。
    - Windows / POSIX (Linux, macOS, FreeBSD) の差分を吸収。優先度設定の失敗時は警告でスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を追加。

- ポートフォリオ構築（メモリ内関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（select_candidates）、等金額・スコア重み計算（calc_equal_weights、calc_score_weights）を実装。スコアが全て 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有比率が閾値を超えるセクターの新規候補除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知レジームは警告とフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限・ポートフォリオ全体の aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング、余剰キャッシュを fractional remainder に基づき分配するアルゴリズムを導入。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。SQLite（PAPER_TRADING_SQLITE_PATH または引数 --db）からデータを集計して、稼働率、注文成功率、送信率、P95 レイテンシ等を算出。閾値に基づく PASS/FAIL 判定を行う。
    - CLI 引数 --from/--to/--db をサポート。

- 研究用（未完・部分実装）
  - research/factor_research.py
    - DuckDB を利用したファクター計算の骨子を追加（Momentum / Value / Volatility / Liquidity 等の計算方針と定数定義）。一部実装（モメンタム計算の開始）あり。設計上、prices_daily / raw_financials テーブルのみ参照し外部 API には依存しない。

- パッケージ情報
  - kabusys/__init__.py にて __version__ を "0.1.0" に設定。

### 変更
- 設定読み込みの振る舞いを明確化
  - 自動 .env ロードのルート検出は __file__ を起点に親ディレクトリへ探索する実装に変更（CWD に依存しない）。
  - .env の読み込みで OS 環境変数をプロテクトしつつ .env.local で上書き可能にした。

- ロギング
  - コンソールには stdout を使う（cron 等で stdout/stderr を一本化してリダイレクトする運用を想定）。

### 修正（バグフィックス / 安全性向上）
- run_execution/run_monitoring の両スクリプトでプロセス優先度設定に失敗した場合でも起動を継続するように例外を捕捉（警告出力）。
- run_execution の起動前に停止フラグが既に立っている場合は起動を中止する安全措置を追加。
- .env パーサーのクォート・エスケープ処理を強化し、文字列中のバックスラッシュなどを正しく解釈するよう改善。
- ポジション算出ロジックで価格欠損や不正値に対するガードを追加（価格 <= 0 の場合はスキップ）。

### 既知の制限 / 注意点
- research/factor_research.py は設計方針および定数が定義されているが、完全実装は未完（ファイル末尾で中断）。
- apply_sector_cap の現行実装では price_map に価格が欠損（0.0）がある場合にエクスポージャーが過小見積りされ、意図しないブロック回避につながる可能性がある（TODO コメントあり）。
- process_priority および set_cpu_affinity は psutil に依存しており、権限不足やサポート外 OS では警告が出て設定をスキップする。

### セキュリティ
- .env を生成する config_setup.py の出力にて「.env を絶対に Git にコミットしないこと」を明記。秘密情報はマスクして対話表示する。

---

今後のリリース候補（想定）
- research/factor_research の完全実装（Momentum/Value/Volatility/Liquidity ファクター算出の SQL/Python 実装完了）
- テストカバレッジの追加（ユニットテスト、統合テスト）
- order/execution 周りの耐障害性・リトライロジックの強化
- 銘柄ごとの lot_size 対応（stocks マスタ参照）や手数料・スリッページの詳細見積り
- DuckDB / SQLite スキーマバージョニングとマイグレーション機能

（以上）