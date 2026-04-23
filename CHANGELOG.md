# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付は本リリース作成日です。

## [Unreleased]

※現在未リリースの変更はありません。

---

## [0.1.0] - 2026-04-23

### 追加 (Added)
- 起動スクリプト / 実行ユーティリティを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止制御用フラグファイル (`data/stop_requested.flag`) を検出してループを終了。
    - 起動時にプロセス優先度を "high" に設定（utils のユーティリティを利用）。
    - SQLite / DuckDB 接続を確立し、監視 DB の初期化を行う。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=`paper_trading` の場合はペーパートレード用の専用 SQLite を使用（本番 DB と分離）。
    - BrokerClientFactory 経由でブローカークライアント生成、OrderRepository 等の依存コンポーネントを組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグファイル検出で安全にエンジン停止。PID ファイルの管理（data/execution.pid）。
- 設定管理・ウィザード・検証 CLI を追加
  - config_setup.py
    - 対話式ウィザードで `.env` を作成・更新するユーティリティを実装。
    - デフォルト項目・入力ヘルプ・シークレットマスク表示などを提供。
  - validate_config.py
    - .env と config/*.yaml の起動前検証ツールを実装（--strict オプションあり）。
    - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性検証、DB パスの親ディレクトリチェック、YAML パース検証（PyYAML があれば）を行う。
- 設定読み込み・ラッパーを追加
  - config.py
    - プロジェクトルート検出（.git または pyproject.toml）に基づく自動 `.env` 読み込み（.env, .env.local、OS 環境変数保護）。
    - export 付き行、クォート付き値、インラインコメントなどに対応した .env パーサを実装。
    - Settings クラスでアプリ全体の環境変数アクセスを集約（DB パス・ログレベル・KABUSYS_ENV 判定・Paper Trading 関連設定など）。
    - PAPER_FILL_MODE の妥当性検証（instant/partial/never/reject）。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティ。
    - LOG_DIR / LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティ（"high"/"normal"/"low"）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity 関数を提供（設定失敗時は警告ログでフォールバック）。
- ポートフォリオ構成・サイズ計算モジュールを追加
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア順）、等金額・スコア加重の重み計算（score が全て 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター別エクスポージャから新規候補を除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear、未知のレジームはフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限・総投資上限（aggregate cap）スケールダウン、cost_buffer を考慮した安全な配分を行う。
- Paper Trading 検証レポートツールを追加
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を解析して稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計・判定する CLI ツールを実装。
    - PASS/FAIL 基準値を定義（稼働率 99% など）し、期間指定オプション (--from/--to) に対応。
- research/factor_research.py（ファクター計算）を追加（骨組み）
  - DuckDB 接続を受け prices_daily / raw_financials を参照してモメンタム等の要因を計算する設計ドキュメント的な実装スタブを追加。

### 変更 (Changed)
- 監視プロセスの DB 接続方針
  - run_monitoring.py: Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する実装（監視データは本番 DB に集約する意図）。
- ログ出力の標準化
  - 全スクリプトで utils.logging_setup.setup_logging を用いてログ設定を統一（stdout 出力 + ローテートファイル）。

### 修正 (Fixed)
- .env パーサの堅牢性向上
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応し、既存の環境変数を保護するための protected set を導入。

### ドキュメント / 実装ノート (Notes)
- 各モジュールに詳細な docstring を追加し、設計意図・制約・将来の拡張ポイント（例: lot_size の銘柄別対応、価格欠損時のフォールバックなど）を明記。
- validate_config.py は PyYAML が未インストール時には YAML の内容検証をスキップして警告を出すようにしてあるため、環境により検証の厳密さが変わる点に注意。

### 既知の制約 (Known issues)
- research/factor_research.py は一部実装が未完（ファイル末尾が途中）で、モメンタム等の計算ルーチンの SQL 実装が未完となっている。
- position_sizing で price が 0 または欠損の場合の扱いは現状スキップしており、将来的に前日終値などのフォールバックを検討する旨の TODO がある。

---

今後の予定:
- research/factor_research の完成（DuckDB を用いたファクター計算の実装完了）
- 単体テスト・統合テストの追加（特に position sizing / risk adjustment の数値的検証）
- Paper Trading の検証レポートを CI に組み込むなど自動化

（以上）