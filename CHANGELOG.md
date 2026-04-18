# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従います。  
このプロジェクトの初期リリース履歴を記載しています。

なお、日付は本リポジトリのスナップショット作成日です（2026-04-18）。

## [0.1.0] - 2026-04-18

### 追加
- 基本パッケージの初期実装を追加。
  - src/kabusys/__init__.py にパッケージ情報（__version__ = "0.1.0"）を追加。
- 実行用スクリプトを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager に対するデフォルト設定（max_position_pct 等）を実装し、初期ポートフォリオ値を broker.get_available_cash() から取得。
    - ExecutionEngine をバックグラウンドスレッドで実行し、data/stop_requested.flag による停止フラグ検知・グレースフル停止、実行 PID ファイル (data/execution.pid) の取り扱いを行う。
  - src/kabusys/run_monitoring.py
    - SystemMonitor 起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（デフォルト: data/monitoring.db）を使用して監視データを確実に記録。
    - 起動時にプロセス優先度を "high" に設定。
    - data/stop_requested.flag を検知して監視ループを終了。
- 設定・環境変数管理を追加。
  - src/kabusys/config.py
    - .env 自動読み込み機能（プロジェクトルートに .git または pyproject.toml がある場合）。
    - .env/.env.local の読み込み順序、OS 環境変数の保護（上書き禁止）を実装。
    - 値のパース機能（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い）を実装。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス / 監視閾値 / 環境種別 等の取得メソッドを定義。PAPER_FILL_MODE の検証、paper_sqlite_path、is_live/is_paper/is_dev プロパティ等を含む。
- 設定関連 CLI を追加。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を作成・更新する機能を提供。
    - 入力補助（デフォルト値、選択肢、シークレットマスク表示）と .env の読み書きを実装。
  - src/kabusys/validate_config.py
    - 起動前チェック CLI。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在確認（PyYAML があればパース検証）を実施。
    - --strict オプションで警告を失敗扱いにできる。
- ログ・プロセスユーティリティを追加。
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定。
    - ログディレクトリ自動作成、環境変数 LOG_LEVEL / LOG_DIR による設定、既存ハンドラのクリアなどを実装。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを実装。psutil を利用し、権限不足時は警告を出してスキップ。
- ポートフォリオ構築関連の純関数群を追加（DB 参照なし）。
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数計算、単元株丸め、aggregate cap によるスケーリング、コストバッファ考慮などを実装。
  - src/kabusys/portfolio/__init__.py から上記 API をエクスポート。
- Paper Trading 検証レポートツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - SQLite（paper_trading DB）からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポート出力。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定し PASS/FAIL 判定を出力。
    - コマンドライン引数 --from/--to/--db をサポート。
- 監視 DB 初期化ヘルパー参照
  - run_* スクリプトで monitoring_db.init_monitoring_db を呼び出し、監視テーブルの存在を保証（冪等）。

### 変更（設計/挙動）
- DB パスと運用分離に関する挙動を明確化。
  - run_monitoring は KABUSYS_ENV にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用する仕様。
  - run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離する仕様。
- ロギングの標準出力は stderr ではなく stdout を使用するように統一（cron / タスクスケジューラ等との相性を考慮）。
- .env ファイル自動読み込みのポリシー:
  - OS 環境変数を優先し、.env と .env.local を順次読み込み（.env.local は上書きを許可）する挙動を採用。自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。

### 修正（バグ修正等）
- 環境変数解析の堅牢化:
  - export プレフィックス、クォート内のエスケープ、インラインコメントの扱いを正しくパースするよう改善。
- process_priority / set_cpu_affinity で許可エラーや未実装環境において例外が伝播しないよう警告にフォールバックする実装へ変更。

### 既知の注意点 / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される旨を TODO コメントで記載。将来的に前日終値等のフォールバックを検討する必要あり。
- position_sizing:
  - lot_size を全銘柄で共通とする設計。将来的に銘柄別 lot_map の受け入れを想定する旨をコメントで記載。
- research/factor_research.py の一部（calc_momentum の実装途中）に未完了コードがある（スニペット末尾が途中で切れている）。ファクター計算モジュールは設計方針と定数が整備されているが、完全実装は追加作業が必要。

### セキュリティ
- 初期リリースでは機密情報（API トークン等）を .env に格納する想定。README 等で .env の Git 管理禁止を強調することを推奨（config_setup のヘッダにも注意書きを追加済み）。

---

以上がこのリポジトリの初期リリース（v0.1.0）に含まれる主な変更点です。必要であれば各ファイルごとの詳細な変更説明（関数単位の動作やパラメータの説明）を追記できます。