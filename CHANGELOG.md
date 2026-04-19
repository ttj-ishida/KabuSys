# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

なお、以下の変更履歴はリポジトリ内のコード内容から推測して作成しています。実際のコミット履歴と差異がある場合があります。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初回リリース（推定）。日本株自動売買システム「KabuSys」の基本機能とユーティリティを実装。

### Added
- コア: KabuSys パッケージ初版を追加。
  - パッケージバージョン: 0.1.0
  - パッケージ説明: 日本株自動売買システムの基本モジュール群を提供。

- 起動スクリプト / デーモン類:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 専用の SQLite（既定: data/paper_trading.db）を使用し、本番 DB から分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - RiskConfig のデフォルトパラメータを設定（max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 監視ループは停止フラグ検知・例外捕捉・KeyboardInterrupt に対応。
    - duckdb 接続も初期化して使用。

- 設定管理 / CLI:
  - src/kabusys/config.py: 環境変数および .env 自動読み込み機構を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env / .env.local の自動読込（OS 環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env の各行パーサはクォート、エスケープ、インラインコメント等に対応。
    - Settings クラスを提供（J-Quants / kabu / DB パス / PAPER_FILL_MODE の検証など）。
    - 環境判定ユーティリティ（is_live / is_paper / is_dev）を提供。
  - src/kabusys/config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を実装。
    - デフォルト値・選択肢・シークレット入力に対応。生成後に .env を書き出す。
  - src/kabusys/validate_config.py: 設定検証 CLI を実装。
    - 必須環境変数の存在チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在/パースチェック（PyYAML が無い場合は柔軟に扱う）。
    - --strict フラグで警告をエラー扱いにできる。起動前チェック用。

- ポートフォリオ構築関連（純粋関数群、DB非依存）:
  - portfolio_builder.py:
    - select_candidates: BUY シグナルのスコアソートと上位選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア全0時は等金額にフォールバック）。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中制限（既存ポジションを基に新規候補をフィルタ）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マップ）。
  - position_sizing.py:
    - calc_position_sizes: weight / candidates / risk_based 等に応じた発注株数決定。単元株丸め、max_position / aggregate cap スケーリング、cost_buffer 考慮などを実装。
    - aggregate cap 超過時のスケーリングと残差処理（lot_size 単位での追加配分）を実装。

- ユーティリティ:
  - utils/logging_setup.py:
    - 統一的なロギング設定ユーティリティを提供（コンソール stdout と 日次ローテートファイル）。
    - LOG_LEVEL / LOG_DIR の解決順に対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py:
    - プラットフォーム差を吸収するプロセス優先度設定（Windows / POSIX に対応）と CPU affinity 設定。psutil を利用し失敗は警告でスキップ。

- ツール:
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成 CLI を追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）などの指標を集計・判定（PASS/FAIL）して標準出力へ出力。
    - フィルタ期間指定 (--from / --to)、DB 指定 (--db) をサポート。PAPER_TRADING_SQLITE_PATH 環境変数を使用可能。

- リサーチ:
  - research/factor_research.py（骨格実装）:
    - DuckDB 接続からモメンタム等のファクター計算を行う設計。モメンタム計算（1M/3M/6M、MA200乖離）などの仕様がある（実装途中の箇所あり）。

### Changed
- ログ出力:
  - logging_setup により、全起動スクリプトで一貫したログ構成（stdout + 日次ファイル）を採用。既存ハンドラをクリアして重複を防止する挙動を追加。

- DB 初期化:
  - run_execution/run_monitoring 共に init_monitoring_db を呼び出して、監視テーブルの存在を保証（冪等性を考慮）。

### Fixed
- .env パーサの堅牢化:
  - クォートされた値内のバックスラッシュエスケープや終端クォート処理、インラインコメント取り扱いを正しく処理することで .env 読み込みの不具合を低減。

- 監視ループの堅牢化:
  - monitor.check_once() 内で発生する例外を個別にキャッチしてループ継続するようにし、単発のエラーで監視が停止しないようにした。

- プロセス優先度設定のフォールバック:
  - 未対応 OS や権限不足時は警告出力でスキップする実装にして、起動失敗を防止。

### Security
- .env の取り扱いに関する注意文を config_setup のヘッダに明記（.env を絶対に Git にコミットしないよう明示）。

### Notes / TODO
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題を指摘する TODO を記載。前日終値や取得原価でのフォールバック検討が必要。
- position_sizing:
  - 将来的な拡張として、銘柄ごとの lot_size を stocks マスタから取得する設計への変更を検討中。
- research/factor_research.py は一部実装が途中（ファイル末尾で切れている）ため、残りの実装が必要。

### 互換性 / Breaking Changes
- なし（初回リリース想定のため既存互換性問題は特になし）。

---

（以上）