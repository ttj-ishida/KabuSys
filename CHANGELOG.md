CHANGELOG
=========

このCHANGELOGは「Keep a Changelog」規約に準拠しています。  
このファイルは、コードベースから読み取れる実装内容を元に推測して作成しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-17
-----------------

Added
- プロジェクト初期実装を追加。
  - パッケージメタ情報
    - kabusys.__version__ を "0.1.0" として定義。
  - 環境設定 / 設定管理
    - kabusys.config: .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
      - 読み込み順序: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - .env パーサは export プレフィックス対応、クォート文字列とエスケープ、行末コメントの処理をサポート。
      - Settings クラスを提供し、各種環境変数の取得・バリデーションを行う（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD の必須チェック、KABUSYS_ENV / LOG_LEVEL の許容値チェックなど）。
      - Paper Trading 用設定（PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE 等）をサポート。
  - 設定ユーティリティ CLI
    - kabusys.config_setup: 対話式ウィザードで .env を生成・更新する CLI を提供。
      - 各設定項目の説明・デフォルト・選択肢を提示し、.env を安全に書き出す（.env を Git にコミットしないよう注意喚起を出力）。
    - kabusys.validate_config: 起動前の設定検証 CLI を追加。
      - 必須 / 任意環境変数チェック、KABUSYS_ENV のガード、DB パスや config/*.yaml の存在チェック（PyYAML がない場合は YAML チェックをスキップして警告）。
      - --strict オプションで警告も FAIL 扱いにできる。
  - 実行エンジン / 監視の起動スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と完全分離。
      - BrokerClientFactory を使ってブローククライアントを生成（Mock を含む想定）。
      - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとスレッド実行制御を実装。
      - 停止フラグ (data/stop_requested.flag) を検知して安全に停止。
      - 実行用 PID ファイルを data/execution.pid に作成する挙動を想定。
      - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors, circuit_breaker_window_sec, max_drawdown）を利用。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効な値はデフォルトにフォールバックして警告。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録。
      - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
  - 監視用 DB 初期化
    - monitoring.monitoring_db による監視テーブル初期化処理（init_monitoring_db）を起動スクリプトで呼び出し、冪等的に監視テーブルの存在を保証。
  - ユーティリティ
    - kabusys.utils.process_priority:
      - set_process_priority(level): Windows / POSIX 差分を吸収してプロセス優先度を設定（"high" / "normal" / "low"）。
      - set_cpu_affinity(cpu_count): 指定したコア数にプロセスを固定する機能（未指定時は全コア）。
      - 権限不足や未対応 OS 時は警告を出して安全にスキップする実装。
  - ポートフォリオ構築ロジック（純粋関数群）
    - kabusys.portfolio.portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順で選定（タイブレークは signal_rank）。
      - calc_equal_weights / calc_score_weights: 等配分 / スコア加重の重み計算（スコア合計が 0 の場合は等配分にフォールバックして警告）。
    - kabusys.portfolio.risk_adjustment:
      - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、セクター上限超過時に候補を除外（"unknown" セクターは無視）。
      - calc_regime_multiplier: レジーム文字列 (bull/neutral/bear) に基づく投下資金乗数を返す（未知のレジームは警告のうえ 1.0 フォールバック）。
      - セクター評価で価格欠損時の挙動や TODO コメントを含む（将来的なフォールバック価格の検討）。
    - kabusys.portfolio.position_sizing:
      - calc_position_sizes: risk_based / equal / score の各方式で発注株数を算出。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash によるスケールダウン）を実装。
      - cost_buffer による手数料・スリッページ保守見積りを考慮したスケーリングと余剰配分ロジックを実装。
      - 将来的な銘柄別 lot_size サポートについて TODO を記載。
  - リサーチ（ファクター計算）
    - kabusys.research.factor_research:
      - calc_momentum: mom_1m/mom_3m/mom_6m / ma200_dev を DuckDB の prices_daily テーブルから計算。
      - calc_volatility: ATR/avg_turnover/volume_ratio 等のボラティリティ・流動性指標を計算する SQL ベースの実装（大きめのウィンドウと欠損制御を考慮）。
      - DuckDB 接続を受け取り SQL で高速に計算する設計。
  - ツール
    - kabusys.tools.paper_verification_report:
      - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI。
      - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、閾値に基づく PASS/FAIL 判定を出力（デフォルト閾値はソース内定数で指定）。
      - 日付フィルタ（--from / --to）と --db オプションをサポート。
      - P95 算出・NULL 安全性に配慮した実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- .env は絶対にリポジトリにコミットしない旨の注意が config_setup に明記されている。
- 環境変数に必須値が未設定の場合は明示的なエラーを投げる設計（Settings._require）。

Notes / Known limitations
- セクターエクスポージャー計算で price が欠損（0.0）だとエクスポージャーが過少評価され除外が解除される可能性があり、ソース内にフォールバック価格導入の TODO がある。
- position_sizing の lot_size は現在全銘柄共通の単一値であり、銘柄別の単元サポートは将来的な拡張（TODO）。
- process_priority / set_cpu_affinity は OS の権限や psutil の機能制約に依存するため、十分な権限がない環境では警告のうえ処理をスキップする。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップする（警告）。
- run_monitoring は監視 DB に常に sqlite_path を使用する（KABUSYS_ENV に依存せず本番 DB へ書き込む設計になっているため、テスト時は注意が必要）。

参考
- 各 CLI はモジュール単体で実行可能（python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.tools.paper_verification_report, 等）。
- デフォルトの DB/ファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - stop フラグ / PID 等: data/stop_requested.flag, data/execution.pid

もしこのCHANGELOGで触れてほしい追加の観点（例: 各関数の公開 API の詳細やユースケース別の注意点）があれば指示してください。