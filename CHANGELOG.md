# CHANGELOG

すべての変更は「Keep a Changelog」準拠で記載しています。  
このリリースはコードベースから推測して作成した初回リリース用の変更履歴です。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 削除 (Removed)
- 備考 (Notes / Known issues)

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース — 基本機能群の実装。

### 追加
- 基本パッケージ情報
  - パッケージメタ: kabusys.__version__ = "0.1.0" を追加。

- 設定管理
  - Settings クラス (src/kabusys/config.py)
    - 環境変数から各種設定を取得する高レベル API を提供。
    - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env パースは export プレフィックス、シングル/ダブルクォート、インラインコメント等に対応。
    - 各種プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL, LINE_*（任意）
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - PID / KILL フラグ関連パス
      - CPU/MEM/DISK の閾値
      - KABUSYS_ENV (development / paper_trading / live) と判定ヘルパー（is_live / is_paper / is_dev）
      - PAPER_FILL_MODE（paper trading のフィルモード検証）

- CLI ツール
  - 設定ウィザード (src/kabusys/config_setup.py)
    - 対話式に .env を初期作成／更新するウィザード。
    - J-Quants, kabuステーション, DB パス, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等の項目をサポート。
  - 設定検証ツール (src/kabusys/validate_config.py)
    - .env や config/*.yaml の存在・基本構成を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パス親ディレクトリ確認、YAML のパース検査（PyYAML があれば実施）。
    - --strict モードで警告をエラー扱い可能。
  - Paper Trading 検証レポート (src/kabusys/tools/paper_verification_report.py)
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、レイテンシ等）を集計してレポート出力。
    - P95 計算、期間フィルタ (--from / --to)、閾値による PASS/FAIL 判定を実装。
    - デフォルト閾値 (稼働率 99%、成功率 90%、送信率 95%、P95レイテンシ 200ms) を採用。

- 実行 / 監視用エントリポイント
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine 起動フローを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用し本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組立て、Engine のデーモンスレッド実行、停止フラグによる安全停止機構を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループを起動する CLI。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - stop_requested.flag による停止実装、KeyboardInterrupt 対応。
    - 起動時にプロセス優先度を "high" に設定。

- ロギング / プロセス制御ユーティリティ
  - ログ設定ユーティリティ (src/kabusys/utils/logging_setup.py)
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保存）をルートロガーに設定。
    - ログレベルとログディレクトリの解決優先順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度/CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
    - Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - 権限不足や未対応 OS の場合は警告を出してフォールバック。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio_builder (src/kabusys/portfolio/portfolio_builder.py)
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N 件を抽出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を返す。
    - calc_score_weights: スコア加重配分を返す（全てスコアが 0 の場合は等分にフォールバックして警告）。
  - risk_adjustment (src/kabusys/portfolio/risk_adjustment.py)
    - apply_sector_cap: セクター集中を制限するフィルタ。既存保有のセクター比率が閾値を超える場合は当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック、警告あり）。
  - position_sizing (src/kabusys/portfolio/position_sizing.py)
    - calc_position_sizes: 複数の割当方式 ("risk_based", "equal", "score") に対応して銘柄ごとの発注株数を算出。
    - lot_size（単元株）に基づく丸め、1 銘柄上限（max_position_pct）、全体の投下上限（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的推定を実装。
    - 価格欠損時のスキップやログ出力、スケールダウン時の残差処理（端数の優先配分）を実装。

- 研究用ファクターモジュール（下地実装）
  - research/factor_research.py
    - モメンタム等ファクター計算のための骨組みを実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計）。
    - 定数や P95 等のユーティリティを含む。モメンタム計算 calc_momentum の実装が開始されている（ファイル末尾は途中の可能性あり）。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 削除
- （初回リリースのため該当なし）

### 備考 / 既知の制限
- research/factor_research.py の calc_momentum 実装はファイル末尾が途中に見えるため、完全実装が未完の可能性があります（将来のリリースで追記予定）。
- 一部の処理は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存します。実行環境にインストールされていない場合は機能が限定されます（validate_config は PyYAML がない場合に YAML 検証をスキップします）。
- .env の自動ロードはプロジェクトルートの検出に依存します。配布後や特殊な配置では自動ロードが行われない場合があります。その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を用いるか明示的に環境変数を設定してください。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用する設計のため、開発/ペーパートレード環境で監視データを分離したい場合は sqlite_path を適切に指定してください。
- run_execution は paper_trading 環境で paper_sqlite_path を使い本番 DB と分離する設計になっています。ペーパートレード運用時は PAPER_TRADING_SQLITE_PATH を設定してください。

--------------------------------
今後のリリースでは以下が想定されています:
- research モジュールのファクター完全実装とユニットテストの追加
- ExecutionEngine / SystemMonitor の詳細実装（ここでは起動フローのみが提示されている）
- テストカバレッジと CI 設定の追加
- ドキュメント（使用例、設定手順、運用手順）の整備

（この CHANGELOG はコード内容の構造およびコメントから推測して作成しています。実際のリリースノートは追加のコンテキストに基づいて補正してください。）