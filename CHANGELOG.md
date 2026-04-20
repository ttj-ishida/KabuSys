# CHANGELOG

すべての注目すべき変更点を時系列で記録します。  
このファイルは "Keep a Changelog" の書式に準拠しています。  

※ 以下はコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-20
初回公開リリース。以下の主要機能／モジュールを導入しました。

### 追加
- 基本アプリケーション情報
  - パッケージ初期化: kabusys.__version = "0.1.0" を設定。

- 環境設定・管理
  - Settings クラス（kabusys.config）を実装。
    - .env ファイル／環境変数から各種設定値を取得するプロパティを提供（J-Quants、kabu API、LINE、DBパス、監視閾値、実行環境フラグ等）。
    - 自動 .env ロード機構（プロジェクトルート判定、.env / .env.local の順で読み込み）。OS の既存環境変数を保護する挙動を持つ。
    - 必須値チェック（_require）や設定値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
  - 環境設定ウィザード CLI（kabusys.config_setup）を追加。
    - 対話式で .env を初期作成・更新するユーティリティ。シークレット項目はマスクして入力可能。
    - デフォルト値、選択肢、説明文を用意し、.env を安全に書き出す。
  - 設定検証 CLI（kabusys.validate_config）を追加。
    - 必須環境変数や DB パス、config/*.yaml の存在・パース（PyYAML があれば実行）を検査。
    - --strict オプションで警告を FAIL 扱いにできる。実行結果を errors/warnings/infos として出力。

- 実行／監視ランナー
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
    - KABUSYS_ENV に応じて paper_trading と本番 DB を分離（paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使用）。
    - BrokerClientFactory でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行する。
    - data/stop_requested.flag を参照して安全に停止する仕組み（PID ファイル出力、最大 join タイムアウト）。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告後デフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計。
    - SQLite/duckdb への接続初期化、init_monitoring_db 呼び出し、SystemMonitor.check_once() の例外保護とループ継続処理を実装。
    - 停止フラグファイル検出および KeyboardInterrupt 捕捉で安全に終了。

- ポートフォリオ構築ロジック（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコアでソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（全スコア 0.0 の場合は等分にフォールバックし警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中リスクを評価し、上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知レジームはフォールバックで 1.0）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based/equal/score）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を考慮した保守的見積り、残差に応じた追加配分ロジックを実装。

- ユーティリティ
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の解決順、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバックを実装。
    - ログファイル作成失敗やディレクトリ作成失敗時はコンソール出力にフォールバック。
  - プロセス優先度／CPU affinity ユーティリティ（kabusys.utils.process_priority）:
    - psutil を使って Windows/Linux/Mac の差分を吸収して優先度（high/normal/low）を設定。
    - set_cpu_affinity による最初 N コアへのピニング機能（例外／権限不足は警告してスキップ）。
    - 設定失敗時に AccessDenied 等を捕捉して警告出力。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を追加。
    - paper_trading の SQLite（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - P95（パーセンタイル）計算、期間フィルタ（--from / --to）対応、基準閾値を満たすかで PASS/FAIL を判定（稼働率・成功率・送信率・P95 レイテンシの閾値を定義）。
    - DB 存在チェックや SQL の OperationalError をキャッチして堅牢に動作。

- リサーチ（骨格）
  - factor_research モジュール（kabusys.research.factor_research）を追加。
    - Momentum/Value/Volatility/Liquidity の設計方針と定数を定義。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する計算方針を採用。momentum 関数の実装開始（コードベース内に未完の位置あり）。

### 変更（設計上の重要点）
- 監視（monitoring）は運用上の理由から KABUSYS_ENV に依存せず常に本番用 sqlite_path を使用する設計になっています。
- run_execution は paper_trading モード時に paper 用 DB を使用して本番 DB と完全に分離することで、ペーパートレードと本番環境の混同を防止。
- ログは標準エラーではなく標準出力（stdout）に出力するように統一（外部スケジューラからのリダイレクト運用を考慮）。

### 修正（バグフィックス等）
- .env パーサー（kabusys.config._parse_env_line）:
  - export 文、クォート（シングル／ダブル）、バックスラッシュエスケープ、行内コメントの扱いなど多彩なケースに対応するよう堅牢化。
- MONITOR_POLL_INTERVAL の値検証:
  - 0 以下や不正文字列が渡された場合に警告してデフォルトにフォールバックするよう安全化。

### 既知の制約・注意事項
- factor_research の一部関数は実装途中（momentum 関数の先頭で途切れ）であり、完全実装は今後の課題。
- 一部の機能（YAML 検証等）は外部依存（PyYAML）が存在しない場合、検証をスキップして警告を出す設計。
- process_priority / set_cpu_affinity は権限や OS に依存するため、失敗時は警告を出してスキップする仕様。

---

（今後）
- 追加ユニットテスト、factor_research の完成、ExecutionEngine/Monitoring の詳細実装・運用ドキュメント整備を予定しています。