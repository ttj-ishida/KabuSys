# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の慣例に従います。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-21

### 追加 (Added)
- プロジェクト初回リリース。以下の主要コンポーネントを実装。
  - 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視 DB は環境にかかわらず本番用 sqlite_path を使用。停止は data/stop_requested.flag を検知して行う。
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db）に記録。実行中は PID ファイル管理および停止フラグ監視を行う。
  - 設定管理
    - config.py: 環境変数および .env/.env.local の自動読み込み機能を提供。プロジェクトルート自動検出（.git または pyproject.toml）、.env のパースはクォート・エスケープ・コメント対応。Settings クラスで各種設定（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 設定等）をプロパティとして取得可能。
    - config_setup.py: 対話式 .env 作成・更新ウィザードを実装。秘匿項目のマスク表示、デフォルト値・選択肢サポート、保存確認などを提供。
    - validate_config.py: 起動前検証 CLI。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在、有無、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向けのガード等をチェック。--strict オプションで警告をエラー扱いにできる。
  - ロギング・プロセス制御ユーティリティ
    - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定する共通ユーティリティ。LOG_DIR / LOG_LEVEL / app_name による設定、ファイル出力失敗時はコンソール出力にフォールバック。
    - utils/process_priority.py: Windows/Linux/macOS 間の差分を吸収してプロセス優先度（high/normal/low）を設定する関数と、CPU affinity を設定する関数を提供。権限不足や未対応 OS では警告を出してスキップする安全設計。
  - ポートフォリオ構築ライブラリ (純粋関数群、DB 非依存)
    - portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルのスコア降順による選定（同点は signal_rank で破）を提供。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投資乗数を返す（未定義レジームはフォールバック 1.0）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。単元株（lot_size）丸め、1銘柄上限、利用可能現金による aggregate cap スケーリング、cost_buffer を用いた保守的見積り、残差処理による追加配分ロジックを実装。
  - 研究・分析ツール
    - research/factor_research.py: DuckDB 接続を受けてモメンタム等のファクターを算出する設計（prices_daily / raw_financials テーブルを参照）。（一部実装が進行中の旨の注記あり）
    - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を算出し、閾値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を行う。コマンドラインで期間指定や DB パス指定が可能。

### 変更 (Changed)
- 該当なし（初回リリース）

### 修正 (Fixed)
- 該当なし（初回リリース）

### セキュリティ (Security)
- 該当なし（初回リリース）

### 既知の注意点 / 動作上の挙動（実装から推測）
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされる。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。
- PAPER_TRADING 時は paper_trading 用 sqlite を利用することで本番 DB と完全分離される設計。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合はコンソール出力にフォールバックし、警告を出す。
- process_priority / cpu_affinity の設定は権限やプラットフォームに依存するため、失敗時は警告ログが出て処理は継続される。
- portfolio の位置決めロジックは単元株（lot_size）を前提としており、将来的に銘柄別単元サイズ対応の拡張がコメントで示されている。
- research モジュールの一部関数は実装途中（コメント・TODOあり）。利用時は挙動を確認のこと。

---

開発上の補足:
- パッケージバージョンは kabusys.__version__ = "0.1.0"。
- CLI 実行例:
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

（この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリース日付はプロジェクトのリリース管理に合わせて適宜更新してください。）