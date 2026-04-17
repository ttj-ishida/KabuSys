# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog 形式に準拠しています。

## [0.1.0] - 2026-04-17

初期リリース。

### 追加
- 全体
  - パッケージ初期バージョンを 0.1.0 として公開。
  - Python パッケージ構成と各サブモジュールを追加（data, strategy, execution, monitoring 等を想定）。

- 実行エントリ / 常駐プロセス
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。停止フラグ検知で安全に停止。
  - run_monitoring.py: SystemMonitor をポーリングで起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）でポーリング間隔を上書き可能。
    - Monitoring は環境に関係なく本番用 sqlite_path を使用する仕様。
    - 停止フラグの検知、例外時のログ出力、リソースクローズ処理を実装。

- 設定・ユーティリティ
  - config.py: 環境変数読み込み・Settings 抽象化を追加。
    - .env/.env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 複数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、閾値設定など）。
    - KABUSYS_ENV の検証（development / paper_trading / live）とログレベル検証。
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 初期 .env 作成・更新を CLI でサポート。秘密項目はマスク表示。保存前確認あり。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検査、KABUSYS_ENV=live 時の追加ガード等を実装。
    - --strict オプションで警告も失敗扱いにできる。
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（P95 含む）等を算出し PASS/FAIL 判定（しきい値はファイル内定義）。
    - 日付範囲指定（--from, --to）と DB 指定（--db / 環境変数）をサポート。

- ポートフォリオ構築（純関数モジュール）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのソートと上位 N 件選抜。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分の計算（スコア合計が 0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限に基づく候補フィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポートし未知値はフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出、単元株丸め、per-stock/max aggregate 上限、スケールダウンロジック（available_cash 超過時の補正）を実装。

- 研究用ファクター計算
  - research/factor_research.py:
    - DuckDB を用いたモメンタム（1M/3M/6M、MA200乖離）およびボラティリティ/流動性（ATR、平均売買代金、出来高比）計算関数を追加。prices_daily テーブルのみ参照する設計。

- プロセス制御ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows / POSIX に対応したプロセス優先度設定（level: high/normal/low）。権限不足や未対応 OS は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 固定（対応状況により警告でスキップ）。

### 変更
- 環境読み込み挙動
  - .env の読み込み順序を OS 環境 > .env.local > .env として、OS 環境変数を保護（既存キーは上書きしない / protected set の導入）。
  - _parse_env_line にてクォートや export プレフィックス、インラインコメント、バックスラッシュエスケープ等のより堅牢なパースを実装。

- DB 周り
  - run_monitoring は monitoring 用テーブル初期化（init_monitoring_db）を行い、DuckDB への接続も行う（分析用 DB として）。
  - run_execution は paper_trading 環境で専用 SQLite を使用して本番データと分離する挙動を明示。

### 修正 / 安定化
- エラーハンドリング
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもループ継続し、例外は logger.exception で報告するように変更。
  - run_execution 実行ループで停止フラグ検知時に engine.stop() を呼ぶことで安全停止を試みる実装を追加。
  - paper_verification_report は対象テーブルが存在しない（OperationalError）場合にデフォルト値を返すなど、DB スキーマ欠落時にも堅牢に動作。

- 環境変数パース / 検証の堅牢化
  - Settings の各プロパティで不正値に対して明示的に ValueError を投げ、早期に設定ミスを検出可能に。
  - MONITOR_POLL_INTERVAL の不正入力（0 以下・数値以外）に対してデフォルトにフォールバックし警告を出力。

- レポート計算
  - paper_verification_report の P95 計算、平均/最大レイテンシ集約、各種割合計算でデータ不足時に None を返す設計にして、表示で N/A を出力するようにした。

### 注意 / 既知の制約
- process_priority, set_cpu_affinity は OS 権限やプラットフォームによっては動作しない場合があり、その場合はログで警告を出してスキップします。
- portfolio.position_sizing の lot_size は現状全銘柄共通の単純設計（将来的に銘柄別単元対応を検討）。
- apply_sector_cap の価格欠損（価格が 0 または未取得）によりエクスポージャーが過少見積もられる可能性がある旨を TODO コメントで示しています。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされます（配布後の挙動を考慮）。

---

今後のリリースでは、より詳細なテストカバレッジ、銘柄別単元対応、価格フォールバック処理、並列性やパフォーマンス改善（DuckDB クエリ最適化等）を計画しています。