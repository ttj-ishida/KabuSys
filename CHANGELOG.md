# CHANGELOG

すべての重要な変更点を記録します。本ログは「Keep a Changelog」準拠で書かれています。

フォーマット:
- Added: 新規追加の機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

## [0.1.0] - 2026-04-21

初回公開リリース。日本株自動売買システム KabuSys のコア機能群を実装しました。
主に環境設定・起動スクリプト・ポートフォリオ構築・発注制御・監視・ユーティリティ・検証ツールを含みます。

### Added
- 基本パッケージ情報とバージョンを追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
- 環境設定管理を実装（src/kabusys/config.py）。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により .env 自動ロードを行う。
  - .env / .env.local の読み込みロジックを提供（OS 環境変数を保護して上書き制御）。
  - .env 行パーサは export 形式、クォート文字列、エスケープ、コメント処理をサポート。
  - 環境変数の必須取得関数（_require）と各種設定プロパティ（DB パス、PID ファイル、しきい値など）を提供。
  - PAPER_FILL_MODE 等の列挙的設定に対する検証とエラーメッセージを実装。

- 対話式設定ウィザードを追加（src/kabusys/config_setup.py）。
  - .env の初期作成・更新を対話形式で支援。シークレット項目のマスク表示、選択肢サポート、保存確認機能を実装。
  - .env を書き出す安全ヘッダ（`.env は絶対に Git にコミットしないこと`）を出力。

- 設定検証 CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パス親ディレクトリ確認、config/*.yaml の存在/パース検証（PyYAML がない場合はスキップして警告）。
  - --strict モード（警告を FAIL 扱い）を実装。

- 起動スクリプトを追加
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を High に設定して実行。
    - KABUSYS_ENV=paper_trading 時は専用の paper DB（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler を組み立ててデーモンスレッドでセッション実行。停止フラグ（data/stop_requested.flag）検知による安全停止を実装。
    - 実行 PID ファイル path を扱う（data/execution.pid）。
    - RiskManager のデフォルト設定を提供（max_position_pct=0.20 等、初期ポートフォリオ値は broker.get_available_cash() で取得）。

  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - プロセス優先度を High に設定して実行。
    - 監視は環境に依らず本番 sqlite_path を使用（監視データの一元化）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトへフォールバック。
    - stop flag によるループ終了判定、monitor.check_once() 呼び出し時の例外捕捉とログ化を実装。

- 監視 DB 初期化ユーティリティを追加参照（init_monitoring_db を各起動スクリプトで呼び出し、監視用テーブル存在を保証/冪等）。

- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - paper_trading SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出。
  - P95 計算、日付フィルタ（--from/--to）、閾値に基づく PASS/FAIL 判定を実装。
  - データ欠落やテーブル未存在時に graceful に N/A を表示。

- ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
  - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション, 30日保管）を設定。
  - 既存ハンドラのクリア処理、ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

- プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - Windows / POSIX の差分を吸収して nice 値や Windows 優先度クラスに設定を試みる。
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。psutil によるアクセス権限エラーや未実装環境でのフォールバックロギングを実装。

- ポートフォリオ構築・リスク調整・ポジションサイジングの純関数群を実装（src/kabusys/portfolio/*.py）。
  - 候補選定（select_candidates）および等金額・スコア重み付け（calc_equal_weights / calc_score_weights）。
  - セクター集中上限チェック（apply_sector_cap）: 当日売却予定銘柄を排除、unknown セクターは上限適用外などの挙動を設計。
  - レジーム乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバック）。
  - ポジションサイズ計算（calc_position_sizes）:
    - risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、合計投資上限（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残差配分アルゴリズムを実装。
    - price 欠損時のログとスキップ、合計コスト超過時のスケールダウンロジックを実装。
    - 将来の拡張点（銘柄別 lot_size マッピング）を TODO として明示。

- リサーチ（factor_research）モジュールの骨組みを追加（src/kabusys/research/factor_research.py）。
  - モメンタムや MA200 乖離、ATR、流動性指標等の計算方針と定数を実装。DuckDB を用いた計算を前提に設計（関数の実装は部分的に存在）。

### Changed
- 起動時の挙動統一:
  - すべての起動スクリプトで最初に set_process_priority("high") を呼び出すようにし、プロセス優先度の統一を図った（run_execution.py, run_monitoring.py）。
- .env の自動ロードの動作:
  - OS 環境変数を保護するための protected セットを導入し、.env.local は .env より後に上書きで読み込む仕様とした（config.py）。
- ロギング:
  - TimedRotatingFileHandler の導入に伴い、ログファイル名や出力先の決定ロジックを統一（logging_setup.py）。

### Fixed
- .env パーサでのクォート/エスケープ/コメント処理を強化し、値の誤解析を防止（config.py: _parse_env_line）。
- 起動中の DB 接続が finally で確実にクローズされるようにした（run_execution.py, run_monitoring.py）。
- ポーリング間隔環境変数 MONITOR_POLL_INTERVAL が不正な値や 0 以下の場合に time.sleep で ValueError になる問題を防ぐため、妥当性チェックとデフォルトフォールバックを実装（run_monitoring.py: _get_poll_interval）。

### Deprecated
- なし（初版リリース）。

### Removed
- なし（初版リリース）。

### Security
- .env ファイルは機密情報を含むため、出力テンプレートに「.env は絶対に Git にコミットしないこと」を明示。
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト目的）。

### Notes / Known limitations / TODO
- portfolio.position_sizing: 銘柄別 lot_size サポートや価格欠損時のフォールバック価格（前日終値 / 取得原価）の取り扱いは未実装で TODO として残す。
- research.factor_research モジュールは設計方針と定数を含むが、関数の完全実装は継続作業が必要（ファクター計算の SQL/ロジック実装）。
- RiskManager の初期_portfolio_value は broker.get_available_cash() に依存するため、Broker 実装に依存した動作となる点に注意。
- プロセス優先度や CPU affinity の設定は環境・権限によって失敗する可能性があり、失敗時はログ警告でスキップする設計。

---

今後の予定:
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の具体実装）。
- strategy / data / execution のユニットテスト追加と CI 整備。
- 銘柄別単元株対応や取引コスト推定の改善、Paper Trading の検証指標強化。

(この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴・過去バージョンとの差分に基づくものではない点にご留意ください。)