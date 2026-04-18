Keep a Changelog
=================

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アプリケーションの初期実装を追加。
  - パッケージ情報:
    - バージョン: `kabusys.__version__ = "0.1.0"`
- 起動スクリプト / 実行系:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 停止制御にプロジェクト配下の `data/stop_requested.flag` を利用。
    - 監視は環境にかかわらず本番用の SQLite パス (`Settings.sqlite_path`) を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB (`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`) に記録して本番 DB と分離。
    - スレッドベースで ExecutionEngine をデーモン実行し、停止フラグで安全に停止可能。
    - 起動時に PID ファイルを管理（`data/execution.pid` など）。
- 設定管理:
  - config.py
    - .env 自動ロード機能を実装（優先順位: OS 環境 > .env.local > .env）。
    - `.env` の自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応（テスト用途）。
    - 強力な .env パーサ実装（`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い）。
    - Settings クラスで環境変数をラップ（各種パス、閾値、フラグ、Paper Trading モード等）。
    - 入力検証（`KABUSYS_ENV` / `LOG_LEVEL` / `PAPER_FILL_MODE` の妥当性チェック）。
- 設定ツール:
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を提供。
    - デフォルト値、選択肢、シークレット入力の扱い、既存 .env の読み込みと Enter による再利用をサポート。
    - .env のテンプレート書き出し機能を実装（書式と注意書きを含む）。
  - validate_config.py
    - 起動前チェック CLI を提供。必須環境変数やパス、config/*.yaml の存在・パース（PyYAML が利用可能な場合）を検証。
    - `--strict` オプションで警告をエラー扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や Kill Switch の設定確認）。
- ロギング / プロセス管理ユーティリティ:
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（デイリー、30世代保持）を設定するユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続する堅牢性を実装。
    - LOG_LEVEL / LOG_DIR / 引数で挙動を制御。
  - utils/process_priority.py
    - Windows と POSIX 系を透過的に扱うプロセス優先度設定と CPU affinity 設定を追加（psutil ベース）。
    - 対応外 OS や権限不足時には警告を出してスキップするフォールバック実装。
- データベース / 分析基盤:
  - duckdb を利用する統合を各スクリプトでサポート（Settings.duckdb_path）。
  - 監視用テーブル初期化ユーティリティ init_monitoring_db の呼び出しを組み込み（冪等）。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成約率 90%、送信率 95%、P95 レイテンシ 200 ms）で PASS/FAIL 判定。
    - 日付フィルタ（--from / --to）と DB パス指定オプションをサポート。
- ポートフォリオ構築 / リスク・ポジション計算:
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank によるタイブレーク）と等金額 / スコア加重の重み計算を実装。
    - 全スコアが 0 の場合のフォールバック（等金額）をログ警告付きで実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - セクター不明（"unknown"）は上限適用対象外にする挙動を採用。
  - portfolio/position_sizing.py
    - ポジションサイズ計算（risk_based / equal / score 対応）、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - 利用可能現金を超える場合はスケールダウンし、残差分は fractional 優先度でロット単位で再配分するアルゴリズムを実装。
- 研究モジュール（骨格実装）:
  - research/factor_research.py
    - DuckDB の prices_daily/raw_financials を参照して Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計（モジュール構成と定数、インターフェースの雛形を実装）。
    - モメンタム計算（mom_1m/3m/6m、MA200乖離）等の計算方針を定義（関数シグネチャを含む）。

Changed
- 初期実装につき、設計上の振る舞いやデフォルト値を明確化。
  - 監視プロセスは監視 DB として常に Settings.sqlite_path（本番パス）を使う旨をドキュメント化。
  - .env の自動ロード順序と上書き動作（.env.local が .env を上書き）を定義。

Fixed
- .env パースの堅牢化（引用符、エスケープ、インラインコメント、export プレフィックス対応）により誤った環境変数読み込みを軽減。
- ログ設定やファイルハンドラ作成に失敗した場合でもプロセスが継続するようにフォールバック処理を追加。

Security
- .env を生成する際にファイルに機密情報を含む旨の注意書きを追加（config_setup の書き出しテンプレート）。
- デフォルトで .env を Git にコミットしないよう開発者への注意を明記。

Internal / Notes
- 多くの箇所で外部依存（psutil, duckdb, PyYAML 等）をオプション扱いにして、未導入時は警告または代替経路（検証スキップ等）で安全に振る舞う実装を採用。
- stop/kill フラグや PID ファイルを用いたプロセス制御を統一的に採用。
- 将来的な拡張ポイントをコード内に注記（例: 銘柄ごとの lot_size 管理、価格フォールバック戦略の追加など）。

注記
- 本リリースは初期版のため API 安全性・運用性については十分な検証が必要です。特に KABUSYS_ENV=live を指定する場合は validate_config を利用して設定を事前に確認してください。