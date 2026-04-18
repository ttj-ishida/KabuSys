# CHANGELOG

すべての変更は「Keep a Changelog」準拠の形式で記載します。

## [0.1.0] - 2026-04-18
初回リリース

### 追加 (Added)
- 基本パッケージと主要コンポーネントを追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - パブリック API: portfolio モジュールの主要関数をエクスポート
    - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper trading SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - エンジンは別スレッドで実行され、`data/stop_requested.flag` により安全に停止可能。
    - 実行 PID を `data/execution.pid` に記録。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の `sqlite_path` を使用。
    - 停止フラグファイルによりループを終了、KeyboardInterrupt にも対応。
- 設定関連
  - config.py: 環境変数／.env 読み込み・ラッパー `Settings` クラスを実装。
    - 自動 .env ロード機能（プロジェクトルート検出: `.git` または `pyproject.toml` を起点）。
    - `.env` と `.env.local` の読み込み順と上書き（OS 環境変数を保護）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化。
    - 各種設定プロパティを提供（DB パス、API トークン、しきい値、環境モードなど）。
    - `PAPER_FILL_MODE` の検証（有効値: "instant" | "partial" | "never" | "reject"）。
  - config_setup.py: 対話式ウィザードで .env を作成 / 更新する CLI を追加。  
    - シークレット項目のマスク表示、デフォルト値、選択肢サポート。`.env` をテンプレ形式で書き出し。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML があればパース検証）。
    - `--strict` オプションで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）を設定するユーティリティを追加。  
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - utils/process_priority.py: プロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity を設定するユーティリティを追加。  
    - クロスプラットフォーム対応（Windows / Linux / macOS 等を吸収）。権限不足や未実装機能は警告でスキップ。
- ポートフォリオ構築・リスク制御
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。  
    - レジーム乗数: "bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは警告の上 1.0 にフォールバック。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（risk_based / equal / score）。  
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）を考慮。手数料・スリッページ想定用の cost_buffer を反映。
- 研究・指標計算
  - research/factor_research.py: モメンタム等ファクター計算モジュールを追加（DuckDB 接続を受け、prices_daily / raw_financials を使用する設計）。  
    - 1M/3M/6M リターン、MA200乖離、ATR 等の計算を行う設計（ファイル末尾は一部未完の箇所あり）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。  
    - 指標: 稼働率（uptime）、注文成功率、送信率、P95 レイテンシ 等。閾値を定義して PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）、DB パスの指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
    - P95 の計算、各種 NULL/データ欠損時の安全ハンドリングを実装。

### 変更 (Changed)
- .env 読み込みの挙動を明確化
  - OS 環境変数は保護され、`.env.local` は `.env` の後に上書き（override=True）される。
  - `.env` パースは以下をサポート:
    - `export KEY=val` 形式
    - シングル/ダブルクォート内のエスケープ処理
    - クォートなし値に対するインラインコメントの扱い（直前が空白/タブの場合にコメントと判定）
- ログの出力先扱い
  - コンソール出力は stdout に統一（cron/task scheduler からのリダイレクトを考慮）。
  - ファイルハンドラ作成に失敗しても起動を継続するフォールバックを追加。

### 修正 (Fixed)
- 環境変数読み込み時の脆弱なパース問題に対応（引用符・エスケープ・コメント処理の改善）。
- ExecutionEngine / Monitoring の起動フローでの DB 初期化（監視用テーブルの冪等な初期化）を保証。
- プロセス優先度設定での例外（権限不足など）を捕捉して警告を出すようにし、起動失敗を回避。

### 既知の問題 (Known Issues)
- research/factor_research.py の一部（ファイル末端）は未完（関数実装が途中で終わっている可能性あり）。実運用前に完全実装／テストが必要。
- position_sizing の価格欠測（price が 0.0 や欠損）の場合、現在はスキップしているが、将来的には前日終値や取得原価等のフォールバック処理を導入予定（TODO コメントあり）。
- apply_sector_cap は "unknown" セクターの取り扱いで上限制約を適用しない仕様。必要に応じてルールを厳格化すること。

### ドキュメント / CLI の使用メモ
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - オプション: --strict（警告を FAIL 扱い）
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 実行 / 監視:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

### 環境変数の主な追加点 / 既定値
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- KILL_FLAG_CLEAR_ON_START — デフォルト: 0（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）。デフォルト: 60
- PAPER_FILL_MODE — paper_trading の填補挙動（instant|partial|never|reject）。デフォルト: instant
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化

---

以上が初回リリース (0.1.0) の主な変更点・仕様です。運用時の注意点や未実装箇所は「既知の問題」を参照してください。