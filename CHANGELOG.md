# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
フォーマット: 変更種別（Added / Changed / Fixed / Deprecated / Removed / Security）

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-21
初回リリース。本バージョンで導入された主要機能・CLI・ユーティリティおよび実装上の注意点を記載します。

### Added
- 基本アプリケーション情報
  - pakage メタ情報として `kabusys.__version__ = "0.1.0"` を追加。
  - パッケージ公開用のエクスポート (kabusys.__all__) を設定。

- 環境設定・管理
  - Settings クラス（`kabusys.config`）を実装。
    - .env ファイル自動読み込み（プロジェクトルートの検出: .git または pyproject.toml）。
    - 環境変数のパース／強制要求（必須 env の `_require`）。
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / paper trading 関連 / 監視閾値 / ログ等）。
    - `is_live` / `is_paper` / `is_dev` 判定プロパティを追加。
  - 対話式設定ウィザード CLI（`kabusys.config_setup`）
    - .env の初期作成・更新を支援するウィザード。
    - J-Quants / kabu / DB / LINE / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START 等の項目を対話的に編集・保存。
  - 設定検証 CLI（`kabusys.validate_config`）
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在およびパース検証（PyYAML が存在する場合）。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行系および監視プロセス起動スクリプト
  - `run_execution.py`
    - ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の paper DB（`PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と完全分離する挙動をサポート。
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て・起動フローを実装。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の取り扱い。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告記録。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計（監視データは本番 DB に集約）。
    - stop フラグ検出、例外を捕捉して次サイクルへ継続、KeyboardInterrupt 対応。

- ロギング・プロセス優先度ユーティリティ
  - `kabusys.utils.logging_setup`
    - 標準出力（stdout）への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソールのみで継続）。
    - ログレベル / ログディレクトリの解決順定義（引数 > 環境変数 > デフォルト）。
  - `kabusys.utils.process_priority`
    - Windows / POSIX 間の差分を吸収してプロセス優先度（nice / Windows priority class）を設定する関数 `set_process_priority`。
    - CPU affinity を固定する `set_cpu_affinity`（psutil を使用、権限不足等は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - シグナルのソート・候補選出（score 降順、同点は signal_rank でタイブレーク）。
    - 等分配（calc_equal_weights）とスコア加重（calc_score_weights）。スコア合計が 0 の場合は等分配にフォールバックして警告。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中上限を適用する apply_sector_cap（当日売却予定銘柄の除外、"unknown" セクターは上限無視）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 各銘柄の発注株数を算出する calc_position_sizes。
    - リスクベース（risk_based）と等配・スコア配分（equal/score）に対応。
    - 単元株（lot_size）で丸め、単銘柄上限（max_position_pct）、全体投下上限（max_utilization）、cost_buffer を考慮した aggregate cap（スケールダウン）ロジックを実装。
    - 残余キャッシュを使って端数分を lot 単位で再配分するアルゴリズム（安定性のため二次ソートに code を使用）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から集計し、稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）等の検証レポートを出力する CLI。
    - デフォルト閾値（稼働率 99% 等）による PASS/FAIL 判定を実装。
    - P95 の計算、日付フィルタ（--from, --to）、DB パス上書きオプションをサポート。

- リサーチ（ファクター計算）
  - `kabusys.research.factor_research` にモメンタム等ファクター計算の基礎（関数・定数設計）を追加（DuckDB を用いて prices_daily / raw_financials を参照して計算する設計）。（ファイル末尾が途中で切れているが、設計方針・定数・関数骨格を導入）

- DB 初期化
  - 監視用テーブル整備のための init_monitoring_db 呼び出し（冪等）を run_execution/run_monitoring で行う。

### Changed
- （このバージョンは新規追加が中心のため、後方互換性のための変更は特になし）

### Fixed
- .env パーサーの堅牢化（`kabusys.config._parse_env_line`）
  - export プレフィックス対応、クォート文字列のエスケープ対応、インラインコメントの扱いを実装。
  - クォートなし値でのコメント判定ルール（直前が空白またはタブの場合のみコメントとみなす）を明確化。

### Security
- 機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN 等）は .env 上で secret 扱い（config_setup の表示時はマスク表示）を行うよう UX を配慮。

### Notes / Implementation details / Known limitations
- run_monitoring は説明にある通り「KABUSYS_ENV にかかわらず本番 sqlite_path を使用」します。監視データの隔離が必要な場合は運用側で DB パスを分けてください。
- process_priority / CPU affinity の設定は権限不足やプラットフォーム非対応時に警告を出してスキップします（psutil に依存）。
- position_sizing の価格欠損（price が 0 または None）の取扱いに注意（現在は該当銘柄をスキップ）。将来的にフォールバック価格（前日終値等）を導入する余地あり。
- config/*.yaml のパース検証は PyYAML がインストールされている場合のみ実行されます。未インストール時は警告でスキップ。
- paper_verification_report の P95 は簡易実装（並べ替えインデックスでの抽出）。大規模データや精度要件が高い場合は最適化の余地あり。
- factor_research モジュールは機能の骨格を実装済みだが、実運用に用いる場合は更なる検証・テストが必要（ファイル末尾で実装が継続中の可能性あり）。

---
参考: 利用可能な主な環境変数
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等。

以上。今後のリリースでは各モジュールの詳細な変更（アルゴリズム改良、性能改善、バグ修正、API 変更等）を追記してください。