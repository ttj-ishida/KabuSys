# CHANGELOG

すべての注目すべき変更点をここに記録します。  
フォーマットは Keep a Changelog に準拠します。

- リリース方針: 重要な機能追加・変更・修正をカテゴリ別に記載します。
- 日付表記: YYYY-MM-DD

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 初回公開: KabuSys v0.1.0 を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite DB（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と完全に分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - 起動前に stop flag (data/stop_requested.flag) をチェックし、停止フラグがある場合は起動せず終了。
    - 実行中は停止フラグ検知で安全に engine.stop() を呼び出して終了処理。
    - 実行 PID を data/execution.pid に記録する想定（pid_file の扱いをサポート）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視 DB を初期化（init_monitoring_db）。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
- 設定管理
  - config.py: .env 自動読み込み機能と Settings クラスを追加。
    - プロジェクトルートは .git または pyproject.toml を起点に自動検出（CWD 非依存）。
    - .env / .env.local の読み込み優先度 (OS 環境 > .env.local > .env) を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別 等）。無効値検出時は明示的に例外を送出。
    - paper_trading 用の PAPER_FILL_MODE と PAPER_TRADING_SQLITE_PATH をサポート。
- 設定補助 CLI
  - config_setup.py: 対話式 .env ウィザードを追加。
    - シークレット項目はマスク表示、既存 .env の読み込みと Enter での既存値再利用、保存前の確認を実装。
    - .env を安全に書き出すテンプレートを提供（.env を Git にコミットしない旨のヘッダ付き）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須/任意環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング & プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的ロギング設定関数 setup_logging を追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - LOG_DIR 指定・作成処理と作成失敗時のフォールバック（コンソールのみ）を実装。
    - LOG_LEVEL 解決順を明記（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py: set_process_priority / set_cpu_affinity を追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収して優先度や CPU affinity を設定。権限不足等の失敗は警告によりスキップ。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコア総和が 0 の場合は等金額にフォールバックし警告。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）を追加。
    - apply_sector_cap は既存保有のセクター時価を計算して上限超過セクターの新規候補を除外（"unknown" は除外しない）。
    - calc_regime_multiplier は 'bull'/'neutral'/'bear' をマップし、未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py: 株数決定ロジックを追加（risk_based / equal / score 対応）。
    - 単元株（lot_size）丸め、ポジション上限（max_position_pct）、総投下資金上限（max_utilization）を考慮。
    - aggregate cap 超過時のスケーリングアルゴリズムと残差処理（lot 単位での追加配分）を実装。
    - price 欠損時のスキップやデバッグログを出力。
- paper_verification_report ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均, 最大, P95）を算出。
    - 基準値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）を定義し PASS/FAIL 判定を出力。
    - --from / --to / --db オプションで期間と DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数も使用。
- research モジュール
  - research/factor_research.py: DuckDB を使ったファクター計算の骨組みを追加（モメンタム / MA / ATR / 流動性 等の設計記述、calc_momentum のインターフェースを導入）。※実装は継続作業を要する箇所あり（ファイル終端が未完の可能性を示唆）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 削除 (Removed)
- なし

### 非推奨 (Deprecated)
- なし

### セキュリティ (Security)
- なし

---

メモ:
- 本リポジトリは「本番/ペーパートレードの DB 分離」「.env の堅牢なパース」「起動時の設定検証」「運用に配慮したログ・プロセス制御」「ポートフォリオ構築の純粋関数群」など運用・安全性を意識した設計が中心です。
- 今後の予定: research モジュールの詳細実装、Strategy/Execution の内製コンポーネント実装拡張、テストカバレッジ強化やドキュメント整備。