CHANGELOG
=========
すべての notable な変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリースを追加（バージョン: 0.1.0）。
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite DB（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を利用するよう想定。
    - 実行中の停止フラグ（data/stop_requested.flag）および実行 PID ファイル(data/execution.pid) の取り扱いを実装。
    - RiskManager、OrderManager、Reconciler 等のコンポーネント組み立てとスレッドベースのセッション制御を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視は環境（KABUSYS_ENV）に依らず本番 sqlite_path を使用する旨を明記。
    - 停止フラグ（data/stop_requested.flag）の検知による優雅な終了処理を実装。
- 設定管理
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml 基準）および .env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env パース機能（シングル/ダブルクォート、バックスラッシュエスケープ、export プレフィックス、インラインコメント処理対応）。
    - Settings クラスで各種設定プロパティを提供（DB パス、PID ファイル、Kill Switch 設定、閾値、PAPER_FILL_MODE の検証など）。
    - 必須環境変数の要求時に分かりやすいエラーを返す _require ユーティリティを提供。
- 設定ツール / 検証ツール
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。
    - 各設定項目の説明・デフォルト・選択肢を提示し .env を安全に生成。生成した .env はコメント付きテンプレートとして保存（Git にコミットしない旨を明記）。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML 未インストール時は警告）、および KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築（Pure functions）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限適用ロジック。既存保有のセクター比率が閾値を超える場合、当該セクターの新規候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知のレジームは警告して 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method に基づく株数算出（"risk_based", "equal", "score" をサポート）。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケールダウン）、cost_buffer（手数料・スリッページ見積り）の考慮、残差処理での優先配分などを実装。
- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority: Windows（psutil の優先度定数）および POSIX（nice 値）に対応したプロセス優先度設定。未対応 OS ではスキップ。アクセス権限不足等は警告で無視。
    - set_cpu_affinity: 指定コア数へ CPU affinity を固定する機能（None の場合は何もしない）。不正引数は ValueError。
- 解析 / レポート
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB を指定可能。
    - システム稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（avg/max/P95）を算出し、閾値に基づく PASS/FAIL 判定を出力（デフォルト閾値をソース中に定義）。
    - P95 計算、日付レンジ（--from/--to）のサポート、データ不足時の N/A 処理を実装。
- リサーチ
  - research/factor_research.py:
    - DuckDB を使用したファクター計算ユーティリティ（モメンタム、ボラティリティ／流動性等）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時に None を返す）。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率等を算出（NULL の扱いに注意して算出）。
- パッケージ化
  - kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - kabusys/portfolio/__init__.py などで関数の公開 API を整理。

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Security
- （該当なし）

Notes / 実装上の注意
- .env 自動読み込みはデフォルトで有効。テスト／CI 等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。
- PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の環境変数は既定の許容値チェックを行い、不正な値は例外を発生させます。運用時は .env の値に注意してください。
- run_monitoring は説明どおり監視用 DB に常に本番 sqlite_path を使用します（環境に依らず監視データを一元化する設計）。
- Process priority / CPU affinity の設定は権限に依存します。設定に失敗した場合は警告ログを出力して処理を継続します。

今後の予定（例）
- strategy / execution の各コンポーネントの詳細実装・単体テスト追加
- ファクター計算・ポートフォリオ構築パイプラインのベンチマークと最適化
- Windows / Linux でのデプロイ手順と運用ドキュメントの整備

-----