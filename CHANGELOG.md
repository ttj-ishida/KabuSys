# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベース（src/）の内容から推測して作成しています。

## [Unreleased]

### Added
- 全体
  - 初期のアーキテクチャ実装を追加（設定管理・起動スクリプト・ポートフォリオ構築・ユーティリティ・解析ツール等）。
  - パッケージバージョンを設定: `__version__ = "0.1.0"`（src/kabusys/__init__.py）。

- 設定関連
  - 環境変数と .env ファイルを扱う Settings クラスを実装（src/kabusys/config.py）。
    - .env の自動ロード（プロジェクトルート検出: .git / pyproject.toml に基づく）。
    - 環境変数のパースはクォート・エスケープ・インラインコメントに対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 実行環境判定 等）。
    - 環境変数ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。

  - 対話式の .env 作成・更新ウィザードを追加（src/kabusys/config_setup.py）。
    - 複数項目のプロンプト、シークレット入力扱い、既存 .env の読み込みと上書き保存。
    - 保存テンプレートは .env に書き込む形式で実装（Git にコミットしない旨の注意を含む）。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ確認、config/*.yaml の存在／パース検証（PyYAML があればパースを試行）。
    - `--strict` オプションで警告をエラー扱いにできる。

- 実行／監視起動スクリプト
  - 実行エンジン起動スクリプト: run_execution（src/kabusys/run_execution.py）
    - プロセス優先度を高く設定（utils.process_priority を使用）。
    - 環境に応じて paper_trading 用 DB を分離して使用（`PAPER_TRADING_SQLITE_PATH` / Settings.is_paper）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立て。
    - 起動時・実行中に data/stop_requested.flag を監視し安全に停止。PID ファイル出力。
  - 監視ループ起動スクリプト: run_monitoring（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は本番 sqlite_path を使用（環境に依存せず production path を参照する仕様）。
    - 監視ループ内で例外を捕捉してログ出力し継続する実装。停止フラグによる安全終了。DB/duckdb のクローズを保証。

- ポートフォリオ構築
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - シグナルスコアでソートして上位 N を選択、等金額配分とスコア加重配分を実装（スコア全0時は等分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - 既存保有比率に基づくセクター除外ロジック（unknown セクターは除外対象外）。
    - 市場レジームに応じた資金乗数を返す calc_regime_multiplier を実装（bull/neutral/bear）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の配分方法を実装。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料/スリッページ見積）による保守的見積り。
  - portfolio パッケージのエクスポートを追加（src/kabusys/portfolio/__init__.py）。

- ユーティリティ
  - ロギングセットアップ（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_DIR / LOG_LEVEL の解決順を明示し、ディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収して set_process_priority を提供。アクセス権エラー等はログ警告でスキップ。
    - set_cpu_affinity を実装（指定コア数でプロセスをピン留め）。

- モニタリング DB 初期化ヘルパー（import として利用されている init_monitoring_db、src/kabusys/monitoring/... を前提）。
- Paper Trading 検証レポート（CLI ツール）（src/kabusys/tools/paper_verification_report.py）
  - SQLITE DB（paper_trading 用）からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ統計（平均/最大/P95）を集計し PASS/FAIL 判定付きでレポート出力。
  - デフォルト DB パス: data/paper_trading.db、オーバーライドは環境変数または --db オプションで可能。

- リサーチ
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）の骨子を実装（モメンタム・MA200乖離・ATR・流動性等の計算方針と定数）。DuckDB 接続を受け取って prices_daily 等のテーブルを参照する設計。

### Changed
- なし（初期実装想定）。

### Fixed
- run_monitoring: MONITOR_POLL_INTERVAL のパース不正値（0 以下や非整数）に対してデフォルトにフォールバックし、警告ログを出すように実装（src/kabusys/run_monitoring.py）。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、コンソール出力のみで継続する安全なフォールバックを追加（src/kabusys/utils/logging_setup.py）。
- process_priority: 未対応 OS や権限エラー発生時に例外を投げずに警告ログを出すようにハンドリングを強化（src/kabusys/utils/process_priority.py）。
- run_execution/run_monitoring: プログラム終了時に SQLite / DuckDB 接続を確実にクローズするよう finally ブロックを用意。

### Security
- config_setup の .env 出力テンプレートに「.env は絶対に Git にコミットしないこと」という注意を明示。
- Settings._require により、必須環境変数未設定時は早期に ValueError を出して起動を防ぐ。

## [0.1.0] - 2026-04-19

- 初回公開相当（上記 Added の内容を含む初期リリース）。
  - 設定管理、起動スクリプト（実行/監視）、ポートフォリオ構築／サイジング、リスク調整、ユーティリティ（ログ・優先度）、設定ウィザード/検証、Paper Trading 検証レポート、ファクター計算モジュール骨子を含む。

---

注記:
- 本 CHANGELOG はリポジトリ内のソースコード（src/ 以下）を解析して推測した変更履歴です。実際のコミット履歴やリリースノートと差異がある可能性があります。