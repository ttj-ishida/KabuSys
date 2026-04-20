# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。メジャー/マイナー/パッチの運用方針に沿って、今回のリリースではコア機能の初期実装をまとめて追加しています。

## [0.1.0] - 2026-04-20

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。
主に以下の領域を実装・改善しています：実行エンジン起動スクリプト、監視（モニタリング）、設定管理ツール、ポートフォリオ構築ロジック、資金配分・株数計算、ユーティリティ、ペーパートレード検証ツール、ファクター計算の基盤など。

### 追加 (Added)
- 実行・監視ランナー
  - run_execution.py：
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV による挙動分岐を実装（paper_trading 時は専用 MockBrokerClient を利用し、paper_trading.db に記録）。
    - ストップフラグ（data/stop_requested.flag）、PID ファイル（data/execution.pid）によるプロセス制御を実装。
    - データベース接続（SQLite / DuckDB）初期化処理を組み込み。
  - run_monitoring.py：
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔のオーバーライド（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 停止フラグ検知でのループ終了、例外発生時のログ出力と継続動作を実装。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動を明示。

- 設定管理
  - config.py：
    - 環境変数 / .env 読み込みロジックを実装（プロジェクトルート検出: .git / pyproject.toml）。
    - 複数の設定プロパティを提供（DB パス、KABUSYS_ENV、ログレベル、paper_trading 用設定、監視閾値など）。
    - 自動ロード抑止フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加。
    - 必須環境変数未設定時に明示的にエラーを出す _require() を実装。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）を実装。
  - config_setup.py：
    - 対話式 .env ウィザードを追加（.env の初期作成 / 更新を支援）。
    - シークレットのマスク表示、選択肢・デフォルト値の扱い、保存前の確認を実装。
  - validate_config.py：
    - 起動前に .env および config/*.yaml の基本検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば）を実行。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、Kill Switch の自動クリア設定など）を実装。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py：
    - シグナル候補選定（select_candidates）を追加（スコア降順、signal_rank による tiebreak）。
    - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights、全スコアが 0 の場合は等金額にフォールバック）を追加。
  - portfolio/risk_adjustment.py：
    - セクター集中制限 apply_sector_cap を実装（既存保有比率が閾値を超えるセクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップとフォールバック挙動）。
  - portfolio/position_sizing.py：
    - 株数決定ロジック calc_position_sizes を実装（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer を考慮した保守的見積り、端数処理による追加配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py：
    - ルートロガーの統一設定ユーティリティを追加（StreamHandler: stdout、TimedRotatingFileHandler: 日次ローテーション、30 日保存）。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで動作。
  - utils/process_priority.py：
    - Windows / POSIX の差分を吸収したプロセス優先度設定（set_process_priority）を実装。
    - CPU affinity を固定する set_cpu_affinity を実装（利用可能コア数や権限不足のハンドリングを含む）。

- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py：
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から指標を集計しレポートを出力する CLI を追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg / max / P95）、リスク却下数等。
    - PASS/FAIL の閾値を定義（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200ms）。
    - 日付フィルタ（--from/--to）と DB パス指定（--db）に対応。

- 研究・ファクター計算の基盤
  - research/factor_research.py：
    - Momentum 等のファクター計算仕様（1M/3M/6M リターン、MA200 乖離、ATR、出来高指標等）の枠組みを実装（DuckDB 接続を想定）。
    - 設定定数や計算方針（スキャンウィンドウ、欠損値扱い等）を定義。

### 変更 (Changed)
- ログ出力の一貫化：
  - すべての起動スクリプトは setup_logging を呼び出すスタイルに統一され、stdout 優先での出力および日次ファイルローテーションを行うように変更。
- DB の扱い：
  - run_monitoring は環境に関係なく本番 sqlite_path を使用する仕様を明示（監視データの一意化を意図）。
  - run_execution は paper_trading 時に専用の PAPER_TRADING_SQLITE_PATH を使用し、本番 DB と分離。

### 修正 (Fixed)
- 環境変数の堅牢化：
  - config._parse_env_line と _load_env_file により .env の多様な書式（export プレフィックス、クォート内エスケープ、インラインコメント）を正しくパースするよう改善。
  - MONITOR_POLL_INTERVAL の不正値に対し警告を出してデフォルトにフォールバックする挙動を実装（time.sleep に与える負の値を回避）。
  - PAPER_FILL_MODE の不正値検出時に ValueError を送出して早期検知できるように。
- プロセス優先度・CPU 固定の権限不足ハンドリング：
  - psutil による操作で AccessDenied 等が発生した場合に警告ログを出してスキップするよう対応。
- ポジション算出ロジックの安定化：
  - lot_size による丸めと aggregate cap スケーリング時の端数処理を実装し、投下資金を超過しないよう安全弁を実装。

### 既知の制限 / 注意事項 (Notes)
- run_monitoring は監視用 DB に常に settings.sqlite_path（本番想定のパス）を使用します。テスト目的で監視を分離したい場合は適宜設定を変更してください。
- config 自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。パッケージ化後や特殊な配置では自動ロードがスキップされる場合があります。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- research/factor_research.py はファクター計算の枠組みを整備していますが、実際の SQL クエリ実装や一部の関数実装が今後追加される予定です（現状は仕様・定数までを含む基盤）。
- ログファイル出力時にディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみの出力となります。運用環境では logs/ ディレクトリの書き込み権限を確認してください。

### セキュリティ (Security)
- .env は絶対にリポジトリにコミットしない旨を config_setup のヘッダに明記しています。シークレット値の取り扱いに注意してください。

---

今後の予定（例示）
- ファクター計算の完全実装（DuckDB SQL 実装の追加）
- ExecutionEngine / SystemMonitor のユニットテスト整備
- per-stock lot_size を銘柄ごとに指定できる拡張（stocks マスタ参照）
- 運用用のメトリクス出力（Prometheus 等）やアラート連携（LINE/外部）強化

---
（本 CHANGELOG はコードベースの内容から推測して作成しました。実際の変更履歴と差異がある場合は適宜調整してください。）