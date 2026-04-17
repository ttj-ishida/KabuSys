CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-17
------------------

初回リリース。以下の主要機能・ユーティリティ・CLI を追加しました。

Added
- 全体
  - パッケージ初版を公開。バージョンは kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）。
  - モジュール構成: data, strategy, execution, monitoring 等のサブパッケージをエクスポート。

- 環境・設定管理
  - Settings クラスを導入し、環境変数からアプリ設定を取得する機能を追加（src/kabusys/config.py）。
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須/任意の設定項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など）。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_*、リソース閾値（CPU/MEM/DISK）等のプロパティ。
  - .env パースの堅牢化:
    - export KEY=val 形式に対応、クォート文字列内のバックスラッシュエスケープ処理、行内コメントの取り扱い、無効行スキップ等を実装。

- 設定支援 CLI / 検証ツール
  - インタラクティブな環境設定ウィザードを追加（python -m kabusys.config_setup）。
    - .env の初期作成・更新を対話式で行う（src/kabusys/config_setup.py）。
    - 主要設定項目の説明、シークレット入力のマスク、既存値の読み取りと保存機能を提供。
  - 設定検証コマンドを追加（python -m kabusys.validate_config）。
    - 必須環境変数の存在チェック、KABUSYS_ENV や LOG_LEVEL の妥当性検査、DB パスの親ディレクトリチェック、config/*.yaml の存在および YAML パース（PyYAML が利用可能な場合）を実行。
    - --strict フラグで警告も失敗扱いにできる（終了コード 1）。

- 実行用エントリポイント
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に分離して記録し、MockBrokerClient を使用する想定（BrokerClientFactory で実装）。
    - ExecutionEngine の依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立て、スレッドで engine.run_session() を実行。停止フラグ（data/stop_requested.flag）検出で安全に停止。
    - ExecutionEngine 起動前に monitoring テーブルの初期化（init_monitoring_db）を実行（冪等）。

  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 起動時にプロセス優先度を "high" に設定。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視情報を記録。
    - 停止フラグによるループ退出、例外発生時のログと継続挙動を実装。

- プロセス制御ユーティリティ
  - プロセス優先度および CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応プラットフォーム時に警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: score 降順、同点は signal_rank 昇順でタイブレーク。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合は等金額配分にフォールバック（警告ログ）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数マップを提供。未知のレジームは 1.0 にフォールバック（警告）。
  - 株数決定・リスク制約・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - risk_based: risk_pct / stop_loss_pct に基づくベース株数算出、1銘柄上限（max_position_pct）適用、lot_size 単位で丸め。
    - equal/score: weight に基づく割当。単元丸めや per-stock 上限を適用。
    - aggregate cap: 合計投資額が available_cash を超える場合はスケールダウンし、小数部の再配分を残差順に lot_size 単位で行う。cost_buffer による保守的コスト見積をサポート。

- ファクターリサーチ（DuckDB ベース）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。データ不足の銘柄は None を返す。
    - calc_volatility: ATR (20 日), 相対 ATR, 20 日平均売買代金, 出来高比率等を計算（DuckDB の SQL ウィンドウ関数を利用）。
    - DuckDB 接続を受け、prices_daily / raw_financials テーブルのみ参照する設計。外部 API へはアクセスしない。

- Paper Trading 検証ツール
  - paper_verification_report を追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）から期間集計してレポートを出力。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - デフォルト閾値を定義し、PASS/FAIL 判定を行う（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - CLI パラメータ --from / --to / --db をサポート。

Changed
- なし（初回公開のためすべて Added）

Fixed
- なし（初回公開のため）

Notes / 実装上の注意
- データベース
  - monitoring 用の SQLite は環境に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計。paper_trading 向け処理は paper_sqlite_path に分離しているため、本番データとペーパー取引データは分離される。
- .env パース
  - クォート内でのエスケープや行内コメントの扱いに注意。特殊な .env 構成がある場合は validate_config で検証することを推奨。
- 権限
  - set_process_priority や set_cpu_affinity は実行環境の権限によって失敗する可能性があり、その場合は警告を出して処理を継続します。
- 将来的な改善ポイント（TODO）
  - position_sizing の lot_size を銘柄別に対応する（stocks マスタに lot_size を持たせる等）。
  - apply_sector_cap の価格欠損時のフォールバック（前日終値やコストベース）を実装。
  - more comprehensive unit tests / CI の追加。

参考: 主なファイル一覧
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*
- src/kabusys/research/factor_research.py
- src/kabusys/tools/paper_verification_report.py

--- 

（この CHANGELOG は与えられたソースコードの内容から推測して作成しています。実際のリリースノートとして使用する場合は、差分やコミット履歴に基づく正確な確認を行ってください。）