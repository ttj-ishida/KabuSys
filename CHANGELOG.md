# Changelog

すべての変更は Keep a Changelog 構文に従っています。  
現在のバージョンは src/kabusys/__init__.py に定義された __version__ に合わせて 0.1.0 としています（リリース日: 2026-04-18）。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 全体
  - 初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装。
  - パッケージエントリポイントとバージョン管理を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 設定関連
  - 環境変数 / .env ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を読み込む。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント（条件付き）等に対応。
    - Settings クラスで各種設定をプロパティとして取得。KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の値検証を実施。
    - データベース・ファイルパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）を Path 型で提供。

- 設定ユーティリティ CLI
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の読み書き、既存値の再利用、シークレット項目のマスク表示、保存確認などを実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検査（PyYAML がある場合）。
    - KABUSYS_ENV=live 時の追加注意チェック（LINE 通知設定や Kill Switch の設定等）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行・監視ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離（設定: PAPER_TRADING_SQLITE_PATH で上書き可）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading では MockBrokerClient を選択する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。エンジンはスレッドで実行し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を利用して安全終了する。
    - RiskManager のデフォルト設定（max_position_pct 等）を実装。初期ポートフォリオ値は broker.get_available_cash() を使用。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は本番 sqlite_path を常に使用（環境にかかわらず監視 DB は本番パスを参照）。
    - SystemMonitor を用いた単回チェック（monitor.check_once()）をループで実行し、例外発生時はログ記録して次回ループへ継続。

- ポートフォリオ構築
  - 銘柄選定・重み計算モジュールを追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順、同点時は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア加重（全スコアが 0 の場合は等分配にフォールバック）。
  - セクター制限とレジーム乗数を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存ポジションのセクター比率が上限を超える場合、同セクターの新規候補を除外。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数（1.0/0.7/0.3）。未知レジームは 1.0 でフォールバック（警告）。
  - ポジションサイズ算出を実装（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method として "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・集約上限（available_cash）によるスケーリング、cost_buffer を加味した保守見積り、端数調整ロジックを実装。
  - 上記を束ねるパッケージ化（src/kabusys/portfolio/__init__.py）。

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ/レベルの解決順を定義し、既存ハンドラはクリアして二重設定を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供。対応不可や権限不足時は警告してスキップ。
    - set_cpu_affinity(cpu_count) で先頭 N コアへピン留め（未対応 OS や権限問題は警告してスキップ）。

- 運用ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し、閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションで期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数に対応。

- リサーチ
  - ファクター計算モジュールのスケルトン（src/kabusys/research/factor_research.py）を追加。モメンタム系ファクター（1M/3M/6M、MA200乖離）計算の実装を開始（DuckDB 経由で prices_daily を参照する設計）。定数・方針を定義。

### 変更 (Changed)
- ログ出力
  - ログは stdout（StreamHandler）を優先する設計。cron / Task Scheduler でのリダイレクト運用を考慮して stderr ではなく stdout を使用。
- DB 初期化
  - 監視テーブルの初期化 (init_monitoring_db) は冪等に実行されるよう保証（run_execution/run_monitoring 内で呼び出し）。

### 修正 (Fixed) / 耐障害性の向上
- 環境パースの堅牢化
  - .env のパースでクォート・エスケープ・コメントをより正しく扱うように改善し、既存 OS 環境変数を保護するための protected 引数を導入。
- 起動時の失敗耐性
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合は警告を出してファイル出力を無効化し、プロセスはコンソールログのみで継続するようにした。
  - run_monitoring のループ内で monitor.check_once() が例外を投げてもループを継続して次回ポーリングへ移るよう例外を捕捉してログ出力する実装。
  - validate_config は PyYAML が未インストールでもパース検査をスキップして警告を出す（柔軟な環境での実行をサポート）。

### ドキュメント（コード内コメント）
- 各モジュールに詳細な docstring と設計注釈を追加。PortfolioConstruction.md / StrategyModel.md 等の仕様書への言及と実装方針がコード中に明記されている（将来の拡張ポイントや TODO も注記）。

## 既知の制限 / TODO
- research/factor_research.calc_momentum の実装は途中（ソースが途中で切れている箇所あり）。DuckDB SQL を用いた完全実装が必要。
- 一部の TODO（銘柄別 lot_size の扱い、価格欠損時のフォールバック処理など）がコード内に残っているため、追加の堅牢化・拡張が想定される。
- ExecutionEngine / BrokerClientFactory / SystemMonitor 等の内部実装は本変更ログで詳細化していないため、それらの振る舞い・API は別途ドキュメント化が必要。

---

注: 本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。