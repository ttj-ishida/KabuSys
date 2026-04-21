# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

※ 本リポジトリの初期バージョンとして以下を記載します。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 基本アーキテクチャと起動用スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を利用する分離設計を採用。
    - エンジンは別スレッドで run_session を実行し、data/stop_requested.flag の検出で安全に停止する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。
    - execution.pid を PID ファイルとして扱う。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。
- 設定管理機能を追加
  - config.py:
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）を実装し、.env/.env.local の自動ロード（OS 環境変数を上書きしない既定の動作）。
    - .env パースを強化（export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメント処理の挙動など）。
    - Settings クラスを提供し、各種環境設定をプロパティ経由で取得（DB パス、紙トレード設定、監視しきい値、ログレベルなど）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
- 設定ユーティリティと CLI を追加
  - config_setup.py:
    - 対話式ウィザードで .env を作成・更新するツールを提供。シークレット項目はマスク表示、選択肢サポート、既存 .env の読み込み・上書き。
  - validate_config.py:
    - 起動前に .env と config/*.yaml の基本検証を行う CLI を提供。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリの存在確認、YAML パース（PyYAML が利用可能な場合）などを検証。--strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築ロジック（純粋関数群）を追加
  - portfolio/portfolio_builder.py:
    - 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。スコア全0 の場合はフォールバックを実装。
  - portfolio/risk_adjustment.py:
    - セクター集中制限適用(apply_sector_cap)、市場レジームに応じた投下資金乗数(calc_regime_multiplier) を実装。未知レジームはフォールバックで警告を出す。
  - portfolio/position_sizing.py:
    - position sizing（risk_based / equal / score）を実装。単元株丸め、1銘柄上限、aggregate cap（利用可能資金に合わせたスケーリング）、cost_buffer を考慮した保守的なコスト見積り、残余配分ロジックなどを実装。
- ログ & プロセス管理ユーティリティを追加
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py:
    - Windows / POSIX を透過するプロセス優先度設定(set_process_priority) と CPU affinity 設定(set_cpu_affinity) を実装。psutil の例外をハンドルして安全にスキップ。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py:
    - Paper Trading の SQLite（デフォルト: data/paper_trading.db）を読み、システム稼働率、注文成功率/送信率、リスク却下数、平均/最大/P95 レイテンシ等を集計しレポートを生成するスクリプトを実装。閾値に基づく PASS/FAIL 判定を行う。
- 研究モジュール骨格を追加
  - research/factor_research.py:
    - Momentum 等ファクター計算の設計と定数を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計（実装は継続中）。

### 変更 (Changed)
- パッケージメタ情報
  - __init__.py にバージョン番号を追加: __version__ = "0.1.0"
  - パッケージのエクスポートに主要モジュールを追加（data, strategy, execution, monitoring）。
- DB 初期化の挙動
  - run_execution.py と run_monitoring.py の両方で init_monitoring_db を呼び、監視用テーブルが存在することを保証（冪等的な初期化）。

### 修正 (Fixed)
- .env 自動読み込みの堅牢化
  - config.py でプロジェクトルートが特定できない場合は自動ロードをスキップするようにして、パッケージ配布時や CWD 依存の問題を回避。
  - .env の読み込みで OS 環境変数を保護する機構（protected set）を導入し、既存の OS 環境設定を不意に上書きしないようにした。

### ドキュメント (Docs)
- 各スクリプト・モジュールにモジュールレベルの docstring を充実化（使用方法、環境変数、設計方針、注意点などを記載）。

### 注意点 / 既知の制限 (Known Issues)
- research/factor_research.py の関数実装がファイル末尾で途切れており、モメンタム計算の実装が未完（継続作業が必要）。
- position_sizing の価格フォールバック未実装: price_map/open_prices に欠損（0.0）がある場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討予定。
- 一部機能は外部モジュール（psutil, duckdb, PyYAML 等）に依存しており、環境により機能が制限される場合がある。各ユーティリティは依存ライブラリがない場合に graceful にフォールバックする実装になっているが、完全な機能を利用するには依存パッケージのインストールが必要。

---

今後の予定:
- factor_research の完成（Momentum / Value / Volatility / Liquidity の算出実装）。
- monitoring/system_monitor, execution エンジン内部の詳細実装とそれらのユニットテスト整備。
- CI による静的解析・型チェックおよび自動テスト導入。
- ドキュメント（README、運用手順、デプロイ手順）の強化。

(END)