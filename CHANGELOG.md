# Changelog

すべての重大な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョンはパッケージ内の `__version__` に合わせて 0.1.0 としています。

## [Unreleased]

（今後の変更をここに記載します）

---

## [0.1.0] - 2026-04-18

初回リリース（コードベースから推測した主要機能・実装を記載）。

### Added
- パッケージの基盤機能を追加（kabusys）。
  - パッケージバージョン: `__version__ = "0.1.0"`。
- 設定管理
  - `kabusys.config`:
    - 環境変数読み込み機能（.env/.env.local の自動ロード）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` サポート。
    - 強化された .env パーサ（`export` プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等）。
    - 必須環境変数取得ヘルパ `_require()` と Settings クラス（各種パス、閾値、フラグ、環境判定プロパティ等）。
    - Paper Trading 用設定（`paper_sqlite_path`、`paper_fill_mode` の検証）。
- 設定ユーティリティ / CLI
  - `kabusys.config_setup`:
    - 対話式ウィザードで `.env` の初期作成・更新を支援。
    - 既存の `.env` 読み込み、シークレットマスク表示、保存機能。
  - `kabusys.validate_config`:
    - 起動前の設定検証 CLI（必須環境変数、KABUSYS_ENV、ログレベル、DBパス、config/*.yaml の存在やパース検証等）。
    - `--strict` オプション（警告を失敗扱いにする）。
    - PyYAML の有無に応じた挙動。  
- 実行系 / 監視
  - `run_execution.py`:
    - ExecutionEngine 起動スクリプト。
    - Paper Trading 環境では本番 DB と分離して専用 SQLite（`data/paper_trading.db`）を使用する仕組み。
    - BrokerClientFactory を介したブローカークライアント生成（paper/live 切替を想定）。
    - 実行中の停止フラグ（`data/stop_requested.flag`）検出、PID ファイル管理、デーモンスレッドでのエンジン実行と安全停止処理。
    - リスクマネージャ（`RiskManager`）の初期設定と初期ポートフォリオ取得（`broker.get_available_cash()` を利用）。
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 停止フラグ検知による優雅な終了。
    - 監視は実行環境に関わらず本番用の sqlite_path を使用する挙動（設計上の意図を明記）。
- ロギング / プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup`:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通セットアップ関数 `setup_logging()`。
    - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - ログレベルとログディレクトリの解決順を明示（引数 > 環境変数 > デフォルト）。
  - `kabusys.utils.process_priority`:
    - クロスプラットフォームでのプロセス優先度設定 `set_process_priority()`（Windows / POSIX(nice) 対応、未対応 OS はスキップ）。
    - CPU affinity 設定 `set_cpu_affinity()`（利用可能コアに基づくピンニング、権限不足時は警告でスキップ）。
- ポートフォリオ構築ライブラリ（純粋関数群・DB非依存）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates()`（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 `calc_equal_weights()`。
    - スコア加重配分 `calc_score_weights()`（全スコアが 0 の場合は等配分にフォールバックし Warning ログ出力）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap()`（既存保有のセクター比率を計算し上限超過セクターの候補を除外、"unknown" セクターは除外対象外）。
    - レジーム乗数 `calc_regime_multiplier()`（"bull"/"neutral"/"bear" マッピング、未知レジームはフォールバックで 1.0）。
  - `kabusys.portfolio.position_sizing`:
    - ポジションサイズ算出 `calc_position_sizes()`（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot）丸め、単銘柄上限・集約上限（aggregate cap）・コストバッファを考慮したスケーリングロジック、残差配分アルゴリズムを実装。
- 研究用 / データ処理
  - `kabusys.research.factor_research`（ファクター計算モジュールの骨格）:
    - モメンタム、移動平均乖離、ATR、流動性等の計算方針と定数を定義。DuckDB 接続経由で prices_daily / raw_financials を参照する設計。
    - （ファイル末尾で一部未完の箇所あり—作業途中の計算ロジック存在を示唆）
- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading の検証レポート生成 CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計と Pass/Fail 判定（閾値は定数で定義）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db または 環境変数 `PAPER_TRADING_SQLITE_PATH`）。
- 監視用 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db`（呼び出し箇所あり）を通じて監視テーブルの存在を保障する設計（冪等）。
- その他
  - 複数の起動スクリプトでプロセス優先度を最初に設定する（`set_process_priority("high")`）。
  - 実行・監視で DuckDB を分析向けに併用（`duckdb.connect()`）。

### Changed
-（初回リリースのため目立った「変更」はありません。設計上の挙動やデフォルト値は各モジュールの docstring / コメントで明示されています）

### Fixed
-（初回リリースのため既知のバグ修正履歴はなし。ただし実装コメントに将来的な改善点（価格欠損時のフォールバック、銘柄別 lot_size など）が記載されています） 

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注意事項（設計上のポイント）
- .env は絶対にリポジトリにコミットしないこと（`config_setup` のヘッダに注意書きあり）。
- Paper Trading と Live の DB を分離しており、paper 環境では実際の発注を行わない想定（MockBroker を利用）。
- `run_monitoring` は環境にかかわらず監視用の sqlite_path（本番想定）を使用する設計のため、本番データを操作する点に注意が必要です（運用ポリシーに合わせて変更可能）。
- 一部モジュール（factor_research 等）は計算ロジックが途中までの箇所が見られるため、完全な動作には追加実装が必要な場合があります。

もし望めば、上の記載をベースにリリースノートの和英翻訳、あるいは各変更点をファイル単位での詳細説明（影響範囲・使用例・環境変数一覧）として展開できます。どの形式で出力しますか？