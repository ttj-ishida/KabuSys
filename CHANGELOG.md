# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
SemVer に従い、バージョン番号は `src/kabusys/__init__.py` の `__version__` を基にしています。

全般注意
- この記録はソースコードから推測して作成したもので、実際のコミット履歴ではありません。
- 一部モジュール（研究用ファクター計算など）は実装途中の箇所があり、その旨を注記しています。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 初期リリース: KabuSys 自動売買システムの基本機能群を追加。
- 実行・監視用スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。プロセス優先度設定、DB 接続、依存コンポーネントの組み立て、スレッド起動／停止フローを実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルによる終了処理を実装。
- 環境設定関連
  - config_setup: 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。秘密項目はマスク表示。
  - validate_config: `.env` と `config/*.yaml` の事前検証 CLI を追加。必須環境変数チェック、パスチェック、YAML パース検証、`--strict` オプションを提供。
  - Settings クラス: 環境変数を参照する設定ラッパーを実装。`env`／`is_live`／`is_paper` 等のプロパティや、データベースパス、paper_trading 用の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）を追加。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みする仕組みを実装。OS 環境変数の保護を考慮。
  - .env パース改善: シングル/ダブルクォート内のエスケープ、export KEY=val 形式、インラインコメントの扱いなどを正しく処理。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: stdout に出力する StreamHandler と日次ローテーションでファイル出力する TimedRotatingFileHandler をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ作成の失敗時にフォールバックする安全策あり。
  - utils.process_priority: Windows / POSIX を吸収してプロセス優先度（high/normal/low）や CPU affinity を設定するユーティリティを追加。実行時の例外（権限不足等）をハンドルして警告ログを出す。
- Execution / Risk / Order 周辺
  - BrokerClientFactory（インターフェース）により、`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を利用し、Paper Trading 用 DB に記録する設計を導入（実装の詳細はブローカーファクトリに依存）。
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager を組み合わせて実行フローを構築。RiskManager に `RiskConfig`（デフォルト値含む）を導入し、初期ポートフォリオ値をブローカから取得して設定する仕組みを追加。
- データベース / 分析基盤
  - DuckDB 接続サポートを追加（duckdb ファイルパスは設定から取得）。duckdb は分析用途（factor 計算等）向けに利用。
  - init_monitoring_db: 監視用 SQLite DB の初期化関数を呼び出して監視テーブルの存在を保証（冪等）。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順／タイブレークで選出。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化による配分（全スコアが 0.0 の場合は等金額にフォールバックし WARNING を出力）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を抑制するため、既存保有のセクター比率が所定閾値を超える場合に新規候補を除外するロジックを追加。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を実装。未知のレジームは警告後 1.0 にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式に対応した株数計算ロジックを追加。単元株（lot_size）丸め、per-position と aggregate キャップ、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングと残余配分アルゴリズムを実装。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、P95 レイテンシなどを算出し、閾値に基づいて PASS/FAIL を判定できる。P95 計算、日付フィルタ、各種 SQL クエリを実装。
- 研究モジュール（部分実装）
  - research.factor_research: DuckDB を用いたファクター計算モジュールを導入。モメンタム・移動平均・ATR 等を計算する設計で、関数の骨子が組まれている（ただし一部実装が途中の箇所あり）。

### 変更 (Changed)
- DB/監視の挙動
  - 監視ループ（run_monitoring）は KABUSYS_ENV に依存せず常に本番用 sqlite_path を使用する方針を明示（監視は本番データで行うため）。
- ログ出力の統一
  - すべての起動スクリプトは setup_logging を使用してログ挙動を統一するよう変更（root ロガーの再初期化を行い二重ハンドラ設定を防止）。
- .env ロードの優先順位を明確化
  - OS 環境変数 > .env.local > .env の順で解決。`.env.local` は既存環境を上書き可能だが OS 環境変数は保護される。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - _parse_env_line にて引用符付き値のエスケープ処理、インラインコメント処理を改善。export プレフィックス対応を追加。
- ポーリング間隔の安全処理
  - MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合にログ警告を出しデフォルト値（60 秒）にフォールバックするよう修正。time.sleep に渡す不正値で例外が発生するのを防止。
- プロセス優先度設定の健全化
  - Windows / POSIX の差異を吸収し、権限エラーや未サポート環境で例外を吸収して警告ログを出すように変更。
- Execution 起動フローの停止安全性
  - スレッド監視中に停止フラグを検知した場合、ExecutionEngine.stop() を呼び出してエレガントに停止する仕組みを追加。

### 既知の問題・制限 (Known issues / Limitations)
- research.factor_research モジュールは一部実装が途中（ソース末尾が途中で切れている箇所あり）。実用化には追加実装が必要。
- portfolio.apply_sector_cap の価格欠損処理は簡易的（価格が 0.0 の場合エクスポージャが過小評価される可能性あり）。将来的に前日終値や取得原価でのフォールバックを検討する旨を TODO コメントに記載。
- 単元株や銘柄別 lot_size の将来的拡張は TODO として残っている（現在はグローバルな lot_size を想定）。
- run_monitoring は監視 DB として常に sqlite_path を使用するため、paper_trading 環境で監視データを分離したい場合には別途対応が必要。

### ドキュメント（補足）
- config_setup により生成される `.env` ファイルは README 相当のヘッダとキーを含み、生成後に `python -m kabusys.validate_config` で検証することが推奨される旨を案内する文言を出力する。
- tools.paper_verification_report はコマンドライン引数 `--from` / `--to` / `--db` をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` を利用可能。

---

（以降のバージョンでは、実際のコミット差分や issue を基に各項目を詳細化してください。）