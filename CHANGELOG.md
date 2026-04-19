# CHANGELOG

すべての重要な変更点を記録します。本ドキュメントは "Keep a Changelog" の慣習に準拠しています。

※初期リリース: バージョン番号はパッケージ内の __version__ に合わせて 0.1.0 としています。

## [0.1.0] - 2026-04-19

### 追加
- 基本パッケージとバージョニング
  - パッケージ初期版を追加。__version__ = "0.1.0"。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし、警告を出力。
    - 停止制御: プロジェクトの data/stop_requested.flag ファイルを検知して安全にループを終了。
    - 監視は環境変数 `KABUSYS_ENV` にかかわらず本番用の sqlite_path を使用して DB に接続。
    - 起動時にプロセス優先度を "high" に設定。
    - sqlite3 および DuckDB 接続を確立して監視 DB の初期化を実行。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 専用の SQLite（data/paper_trading.db）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID 管理 (data/execution.pid) をサポート。停止フラグを検知すると ExecutionEngine の停止を要求。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててバックグラウンドスレッドで実行。

- 設定管理と初期化ツール
  - config.py
    - Settings クラスを追加し、環境変数をプロパティ経由で安全に取得するユーティリティを提供。
    - .env 自動ロード: プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読み込み。OS 環境変数が優先され、.env.local は .env を上書き可能。
    - .env のパースはクォート、export プレフィックス、インラインコメント、エスケープを考慮。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DuckDB/SQLite パス / PID/kill-flag 閾値 / PAPER_FILL_MODE の検証など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

  - config_setup.py
    - .env 作成・更新の対話式ウィザードを追加。
    - いくつかの設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）の対話入力をサポート。
    - 秘密情報はマスク表示、既存値の再利用、.env ファイルの書き出し機能を提供。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV 値チェック、LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検証（PyYAML が未インストールの場合はスキップして警告）。
    - KABUSYS_ENV=live の場合に追加のガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起など）。
    - --strict オプションで警告をエラー扱いにできる。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテート（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログファイルは logs/<app_name>.log、日次ローテーション、30日分保持。
    - ログレベル解決順: 関数引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。

  - utils/process_priority.py
    - プロセス優先度（nice / Windows 優先度クラス）と CPU affinity 設定ユーティリティを追加。
    - クロスプラットフォーム対応（Windows / Linux / macOS 等）。権限不足や未対応環境では安全にスキップして警告ログを出力。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定と配分重み計算機能を追加。
    - select_candidates: score 降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等額配分およびスコア加重配分（スコア合計が 0 の場合は等配分にフォールバックして警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づく新規候補の除外ロジック。既存保有のエクスポージャー（当日売却予定の銘柄を除外）を計算し、上限を超えるセクターの候補をフィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 にフォールバックして警告。

  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数算出ロジックを実装（allocation_method: "risk_based"|"equal"|"score"）。
    - リスクベース配分（risk_pct / stop_loss_pct に基づく）および重みベース配分をサポート。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、総投下上限（available_cash による aggregate cap）を実装。総コストが available_cash を超える場合はスケールダウンして再配分（小数端数は fractional 残差に基づいて lot 単位で追加配分）。
    - cost_buffer により手数料/スリッページ分を保守的に見積もる。

- マーケット調査 / リサーチ
  - research/factor_research.py（骨格）
    - Momentum / Value / Volatility / Liquidity 等のファクター計算設計を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計。
    - calc_momentum の定数や関数骨格を追加（実装は継続予定、スキャン範囲等の設計定数を定義）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計ロジックと閾値（デフォルト: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）を実装。
    - 日付フィルタ（--from / --to）や DB 指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - DB のテーブル欠如に対する耐性（OperationalError をキャッチして N/A 表示）を実装。

- その他
  - monitoring.monitoring_db の初期化呼び出しを各起動スクリプトから行い（冪等）、監視テーブルの存在を保証。
  - パッケージエクスポートを整理（kabusys.portfolio の __all__ 等）。

### 変更
- なし（初期リリース）

### 修正
- なし（初期リリース）

### 既知の注意点 / TODO
- research/factor_research.calc_momentum の実装が途中（ファイル末尾で切れている）。ファクター計算ロジックの完成が必要。
- position_sizing の _max_per_stock は price が 0 または欠損のとき 0 を返すため、price の欠損があると配分が不利に働く可能性あり（コメントでフォールバック価格の検討を指摘）。
- apply_sector_cap は sector_map に存在しないコードを "unknown" 扱いし、"unknown" セクターには上限を適用しない旨の設計。マスタデータ品質に依存。
- process_priority / cpu_affinity の適用は権限に依存し、失敗時はログ警告を出して安全にスキップする。

---

今後のリリースでは、ファクター計算の完成、ExecutionEngine / Monitoring の詳細実装テスト、broker モックと本番の整合性検証、単体テストの追加などを予定しています。ユーザー向けの運用ガイドや設定例（.env.example）も別途整備する計画です。