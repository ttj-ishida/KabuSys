CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。バージョンはソース内の __version__（0.1.0）に基づく初期リリース向けの想定変更履歴です（ソースコードの内容から推測して作成）。

[Unreleased]
------------

v0.1.0 - 2026-04-24
-------------------

Added
- 基本アーキテクチャと起動スクリプトを追加
  - 実行エンジン起動スクリプト: run_execution.py
    - プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) を検知して安全に停止。
    - 実行時の PID を data/execution.pid に記録する仕組み（Engine 側で使用）。

  - 監視ポーリング起動スクリプト: run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視（Monitoring）は環境にかかわらず本番 sqlite_path を使用して監視用 DB を一元管理。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - check_once() 実行時の例外をハンドルして次ポーリングに継続。

- 設定・環境管理
  - config.py: 環境変数と .env 自動ロード機能を実装
    - プロジェクトルートを .git / pyproject.toml を起点に自動検出し、.env / .env.local を読み込む仕組み（OS 環境変数を保護するため protected な上書き処理あり）。
    - .env パーサは export プレフィックス、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - Settings クラスに多数のプロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、pid_file_path、kill_flag_path、閾値設定、KABUSYS_ENV/LOG_LEVEL のバリデーション、is_live/is_paper/is_dev 等）。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）を実装。

  - 対話式環境設定ウィザード: config_setup.py
    - .env の初期作成・更新を対話式で支援。シークレット項目はマスク表示。入力を確認して .env を書き出す。
    - デフォルト値・選択肢を提示し、既存 .env を読み込んで Enter で再利用可能。

  - 設定検証 CLI: validate_config.py
    - 必須/任意環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの存在確認、config/*.yaml の存在と PyYAML によるパース検証（PyYAML 未導入時は警告でスキップ）。
    - 本番環境（KABUSYS_ENV=live）向けの追加安全チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性に関する警告）。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - stdout に出す StreamHandler（stderr ではなく stdout を使用）と、日次ローテーション（TimedRotatingFileHandler）でログをファイルに保存する仕組みを実装。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
    - 既存ハンドラをクリアして二重設定を防止。ログレベル解決ルール（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - Windows/Linux/macOS を抽象化してプロセス優先度（high/normal/low）を設定。psutil を使用し、アクセス権限やプラットフォーム非対応時は警告してスキップ。
    - CPU affinity 設定用の set_cpu_affinity を実装（利用可能コア数の制約や権限例外をハンドル）。

- ポートフォリオ構築ライブラリ（純粋関数群、メモリ内計算）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存保有を考慮して特定セクターが上限（max_sector_pct）を超える場合、新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に対し 1.0/0.7/0.3 を返す。未知のレジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - position size 計算（calc_position_sizes）: allocation_method に "risk_based" / "equal" / "score" をサポート。ロット単位（lot_size）で丸め、1 銘柄上限・aggregate キャップ（available_cash）を考慮してスケーリング。cost_buffer による保守的見積りも対応。
    - リスクベース算出ロジック、aggregate cap のスケーリングと残余配分の実装（fractional 残差を用いた追加配分）。

- 研究用ファクター計算スケルトン
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity を想定したファクター計算モジュールの骨組みを追加（DuckDB 接続を受けて prices_daily / raw_financials を参照する方針、パラメータ定義や P95 等のユーティリティ実装あり）。（ファイルの末尾が途中で切れているため、モジュールは実装の続きが必要）

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポートを出力する CLI を実装。基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を行う。
    - 日付フィルタ (--from / --to)、--db オプションに対応。データ不足時は N/A を表示。

- パッケージ情報
  - パッケージの __version__ を 0.1.0 に設定。

Changed
- デフォルト挙動・安全策の導入
  - run_monitoring はどの環境でも監視用 DB として settings.sqlite_path（=data/monitoring.db デフォルト）を使用する仕様にして、監視データを環境ごとに混ぜないように設計。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用することで発注ログ等を本番 DB と分離。

Fixed
- 環境変数読み込みの堅牢化
  - .env の値読み取りでクォート内のバックスラッシュエスケープや export プレフィックス、インラインコメントの取り扱いを改善。これによりパスやトークンに特殊文字が入るケースでも正しく読み込めるようにした。

- ロギング設定の安全性強化
  - ログディレクトリ作成失敗時にもアプリが致命的に停止しないようにし、コンソールのみでログ出力を継続するフォールバックを追加。

- プロセス優先度設定の例外ハンドリング
  - 権限不足や非対応 OS での例外を捕捉し、警告を出して処理を継続するように改善。

Known issues / Notes
- research/factor_research.py は一部が未完成で、calc_momentum の実装が途中で停止しています。ファクター計算ロジックの完成が必要です。
- position_sizing の価格フォールバック未実装:
  - risk_adjustment.apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値や取得原価等でのフォールバック実装が今後の改善点です。
- 一部機能（例: Engine の内部実装、BrokerClientFactory の詳細、monitor.check_once の中身、init_monitoring_db の詳細）はこの差分に含まれていないため、動作の最終確認は統合テストで要検証。
- run_monitoring/run_execution は stop flag / pid file 周りの運用ルールに依存するため、デプロイ環境でのファイルパス（data ディレクトリ等）と権限設定の確認を推奨。

Security
- 機密情報 (.env のシークレット値等) は .env に保存される想定だが、config_setup で .env を生成する際に「.env は絶対に Git にコミットしないこと」と注意書きを出しています。運用時は適切なシークレット管理を行ってください。

---

以上。必要であれば特定ファイルごとの詳細な変更点や、今後追加すべきユニットテスト項目・統合試験のチェックリストを別途生成します。