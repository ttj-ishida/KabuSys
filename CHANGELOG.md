# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースの内容から推測して作成しています。実際のコミット履歴に基づくものではありません。

全般:
- バージョニングは semantic versioning を想定しています。
- 日付は本ファイル作成日です。

## [0.1.0] - 2026-04-17
初期リリース — 基本的な自動売買フレームワーク、設定/検証ツール、ポートフォリオ構築、モニタリング/実行ランチャー、分析ツールを含む。

### 追加 (Added)
- 基本パッケージ初期導入
  - パッケージメタ情報: kabusys/__init__.py にバージョン 0.1.0 を追加。

- 実行・監視ランチャースクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合、paper trading 用の SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - ブローカークライアントのファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine.run_session() を別スレッドで実行。
    - 停止フラグ(data/stop_requested.flag) 検知時に安全に停止処理を実行。
    - プロセス優先度を起動時に "high" に設定（utils/process_priority を利用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視用 DB の一貫性を保持）。
    - 停止フラグ検知と例外ハンドリング、起動時にプロセス優先度を "high" に設定。

- 設定管理とウィザード
  - config.py
    - Settings クラスを実装し、環境変数から各種設定を取得。
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env の自動ロード優先度: OS 環境変数 > .env.local > .env。自動ロード無効フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パースの強化（export プレフィックス、クォート/エスケープ、インラインコメント処理など）。
    - Paper Trading / 本番の DB パス分離、PAPER_FILL_MODE の検証ロジック、閾値設定（CPU/Memory/Disk）などを提供。
  - config_setup.py
    - 対話式ウィザードで .env を初期生成・更新する CLI。
    - 多数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE トークン等）を対話的に入力し .env を書き出す。
    - 秘匿値はマスク表示、確認プロンプトあり。

- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の基本チェックを行う CLI。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース検証（PyYAML があれば実施）。
    - --strict オプションで警告を FAIL 扱いにできる。
    - live 環境時に追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の警告）を実行。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。
    - スコア合計が 0 の場合は等金額配分にフォールバックし警告をログ出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用(apply_sector_cap) — 既存ポジションに基づきセクター上限を超える場合に新規候補を除外。
    - レジームに応じた乗数(calc_regime_multiplier) — "bull"/"neutral"/"bear" をサポート、未知レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio/position_sizing.py
    - position size（発注株数）計算 calc_position_sizes を実装。
    - "risk_based", "equal", "score" の割当方式に対応。
    - 単元株ラウンド（lot_size）、1銘柄上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料・スリッページ）考慮、残差に基づく追加配分ロジックを実装。

- 研究・因子計算モジュール
  - research/factor_research.py
    - DuckDB 接続を受けて Momentum / Volatility 等のファクターを SQL で計算する実装（calc_momentum, calc_volatility 等）。
    - 各種期間の定義（1M/3M/6M、MA200、ATR20 など）を定数化して使用。
    - データ不足時に None を返すなど耐障害性を考慮。

- ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度を設定する set_process_priority を実装。
    - CPU affinity を最初 N コアにピン留めする set_cpu_affinity を追加。
    - 権限不足や未対応環境時は警告を出してフォールバック。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の結果を集計してレポートを出力する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う閾値を実装（稼働率 >= 99%、注文成功率 >= 90% など）。
    - DB が存在しない / テーブルが存在しない場合に例外を吸収して部分的なレポートを出力する耐障害性を実装。
    - P95 計算ユーティリティ、日付フィルタ対応、--from / --to / --db オプションをサポート。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- デフォルト値と検証の堅牢化
  - MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバックするログ処理を追加（run_monitoring.py）。
  - .env 読み込みでファイル読み込み失敗時に警告を出すように修正（config._load_env_file）。
  - process_priority の権限エラーやプラットフォーム非対応を適切にログに残してスキップするようハンドリング（utils/process_priority.py）。
  - paper_verification_report でテーブル未作成時の sqlite3.OperationalError を捕捉してレポート生成を継続するように実装。

### 注意事項 (Notes)
- 監視（run_monitoring.py）は「環境にかかわらず本番 sqlite_path を使用する」設計になっています。テスト環境で監視を行う場合は sqlite_path の指定に注意してください。
- .env の自動読み込みはデフォルトで有効です。テストや CI 等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL 等は厳密な値チェックが行われ、不正な値は例外を発生させます。設定ウィザードや validate_config を使って事前検証することを推奨します。
- CPU affinity / プロセス優先度の設定は環境依存であり、権限がない場合は安全にスキップされます。

### セキュリティ (Security)
- セキュリティ関連の修正・警告は現時点で報告なし。ただし .env に機密情報（API トークン等）を保存するため、必ず .gitignore に追加してリポジトリに含めないでください（config_setup の出力にもその旨を明記）。

-- End of changelog --