# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般的な注意: 以下の変更点は、提供されたコードベースの内容から推測して作成したリリースノートです。実際のコミット履歴や意図とは若干の差異がある可能性があります。

## [0.1.0] - 2026-04-24

### Added
- 初期リリース: KabuSys 自動売買システムのコアユーティリティ、実行/監視スクリプト、ポートフォリオ構築ロジック、ツール類を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 実行・監視関連スクリプトを追加
  - run_execution: ExecutionEngine を起動するスクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite データベース（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行用 PID ファイル出力（data/execution.pid）をサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や非数）の場合はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番用の sqlite_path（Settings.sqlite_path）を使用する設計。
    - 停止フラグファイルを検知してループを終了。
- 環境設定・読み込み周りの追加/改善
  - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順序: OS 環境 > .env.local > .env。OS 環境を保護するための上書き制御あり。
    - 自動読み込みを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別等）。
    - Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。PAPER_FILL_MODE のバリデーションあり。
  - .env 解析機能の強化
    - export KEY=val 形式を受け付ける。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - クォートなしの場合、インラインコメントの扱いを賢く処理。
- 設定支援 CLI を追加
  - config_setup: 対話式ウィザードで .env を初期作成/更新するスクリプト（src/kabusys/config_setup.py）。
    - デフォルト値、選択肢、シークレット入力の扱い、保存確認などの対話フローを実装。
    - .env 出力テンプレートを整形して保存。
  - validate_config: 起動前の設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証などを実施。
    - --strict モードで警告を失敗扱いにできる。
- ロギングとプロセス制御ユーティリティ
  - setup_logging: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ログレベルとログディレクトリの解決順をサポート（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみで継続。
  - process_priority: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応環境時は警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリを追加（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: スコア降順+タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア0 の場合は等金額へフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限をチェックし、上限超過セクターの候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームは警告と共に 1.0 をフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算。単元株（lot_size）、max_position_pct、max_utilization、cost_buffer に基づくスケーリング・端数処理を実装。aggregate cap 超過時のスケールダウンと残余配分ロジックを実装。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py:
    - 指定期間の paper_trading SQLite DB を解析してレポートを生成（稼働率・注文成功率・送信率・レイテンシ P95 等）。
    - デフォルト閾値を定め PASS/FAIL 判定を行う（稼働率 >= 99%, 成立率/送信率閾値等）。
    - コマンドラインオプションで期間 (--from/--to) と DB パス (--db) を指定可能。
- DuckDB 統合ポイント
  - いくつかのモジュール（execution/engine、research/factor_research 等）で DuckDB 接続を受け取る設計を採用。DuckDB パスは Settings.duckdb_path で管理。
- research/factor_research のスケルトン実装を追加（src/kabusys/research/factor_research.py）
  - モメンタム/ボラティリティ/バリュー/流動性等のファクター計算方針と定数を定義。DuckDB を使った計算を想定した設計。モジュールは部分実装（ファイル末尾でコードが途中まで）だが、API と設計方針を用意。

### Changed
- ログ出力の統一
  - すべての起動スクリプトから setup_logging を呼び出して一貫したログ設定を行う設計に変更（run_execution, run_monitoring）。
  - StreamHandler は stdout に出力（stderr ではなく）して、cron 等でのリダイレクト運用を想定。
- 環境ファイルの読み込みポリシー
  - .env と .env.local の読み込み順・上書き規則を明確化（.env.local が .env を上書き、ただし OS 環境は保護）。
- 停止／キルフラグの取り扱い
  - 実行・監視プロセスはプロジェクトルートの data/stop_requested.flag を監視して安全終了する共通パターンを採用。

### Fixed / Robustness
- MONITOR_POLL_INTERVAL の不正値対策
  - run_monitoring のポーリング間隔取得で 0 以下や非数が与えられた場合に警告しデフォルト値を使用するようにして、time.sleep に渡せる値で安全化。
- .env 読み込み時の例外ハンドリング
  - 読み込み失敗時に warnings.warn を発行しプロセスを継続するようにした（権限エラーや IO エラーに対処）。
- ログディレクトリ作成失敗時のフォールバック
  - setup_logging はディレクトリ作成に失敗してもコンソールログだけで継続するため、起動失敗のリスクを軽減。

### Documentation / Examples
- config_setup が生成する .env テンプレートにコメント付きのセクション分け（J-Quants / kabu API / LINE / DB / Kill Switch 等）を追加してユーザー向けのドキュメントを兼ねた出力を提供。
- validate_config の出力は INFO/WARNING/ERROR を分けて表示し、--strict モードでの CI チェックを想定。

### Internal / Non-user visible
- 複数のユーティリティでログのフォーマットや日付フォーマットを統一（ISO 風タイムスタンプ）。
- process_priority は Windows と POSIX 両方に対応するため psutil の定数取得を getattr で安全化。

---

今後の想定改善点（メモ）
- research/factor_research の完全実装（SQL クエリ・出力フォーマットの完成）。
- portfolioconstruction における lot_size を銘柄別に持つ拡張（stocks マスタの導入）。
- more extensive error handling / retry 戦略（ブローカー通信や DB 接続周り）。
- 単体テスト・CI ワークフローで validate_config を利用して自動検出を強化。

もし特定の変更点をより詳細に記載したい、あるいは別のバージョン区分（Unreleased を用意する等）で出力したい場合は教えてください。