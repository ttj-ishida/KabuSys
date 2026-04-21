# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
語彙は日本語で記載しています。日付は本リリースの想定日です。

フォーマット:
- Unreleased: 今後の変更予定
- 各リリースはバージョンと日付（YYYY-MM-DD）

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-21
初回公開リリース。以下の主要機能・ユーティリティ・CLI・ライブラリを実装しました。

### 追加 (Added)
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler 組み立て、およびスレッドベースでのエンジン実行／停止処理を実装。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - 起動前に停止フラグ（data/stop_requested.flag）を検知して起動を中止する処理を追加。
    - 実行中は停止フラグ検知でエンジンを安全に停止し、PID ファイル管理を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知によるループ終了、check_once() の例外保護、KeyboardInterrupt ハンドリングを実装。

- 設定管理・作成・検証
  - config.py
    - Settings クラスで環境変数の抽象化を提供（DB パス、各種閾値、KABUSYS_ENV、LOG_LEVEL、paper_trading など）。
    - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。.env / .env.local の優先順位を考慮し、既存 OS 環境変数を保護。
    - .env パースはクォート／エスケープ／コメント処理に対応。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START などの設定を取得するプロパティを実装。
  - config_setup.py
    - 対話式ウィザードで .env を作成／更新する CLI を追加。シークレット値のマスク表示、既存値の読み込み、ファイルへの安全な書き出しを実装。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の妥当性をチェックする CLI を追加。必須環境変数チェック、KABUSYS_ENV の値チェック、DB パス親ディレクトリ存在チェック、PyYAML が存在する場合は YAML のパースチェック、KABUSYS_ENV=live 時の追加警告等を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合のフォールバック警告を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有のセクター別時価を計算して上限を超えるセクターの新規候補を除外。unknown セクターは制限対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピング、未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装。allocation_method に応じた株数算出（risk_based/equal/score）を提供。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮した安全なスケーリングアルゴリズムを実装。
    - 価格欠損時のスキップやログによるデバッグを考慮。

- モニタリング DB 初期化
  - monitoring/monitoring_db.py（参照される init_monitoring_db をコード内から使用）
    - 実行スクリプトから監視テーブルが存在することを保証する初期化処理を呼び出す設計（冪等）。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。コンソール（stdout）と TimedRotatingFileHandler（日次ローテーション、30日分保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - stdout を使用することで cron 等での出力統合を想定。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加し、Windows / POSIX を抽象化。psutil の例外（権限不足等）を安全にハンドリングしてフォールバック。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）等を集計し、閾値と照らして PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）および DB パス指定オプション（--db）をサポート。
    - P95 計算や欠損データ時の N/A 表示を実装。

- リサーチ（ファクター計算）スケルトン
  - research/factor_research.py
    - DuckDB を利用したファクター計算モジュールの初期実装（モメンタム、MA、ATR、流動性などの設計と calc_momentum の骨組み）。実データ（prices_daily / raw_financials）を参照する設計。

- パッケージ初期情報
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

### 変更 (Changed)
- 設定の自動ロード挙動
  - .env/.env.local の自動読み込みを実装し、OS の既存環境変数は保護されるよう変更（override の取り扱い、protected set）。
- ログ関連の挙動
  - 既にハンドラが設定されている場合は一旦 flush/close してから再設定することで二重出力を防止。
- Process 優先度設定のフォールバック
  - Windows 用定数や POSIX nice 値の取得に安全なフォールバックを追加。

### 修正 (Fixed)
- 環境変数パーサーの堅牢化
  - クォート内のバックスラッシュエスケープやインラインコメントの扱い、export プレフィックス対応を実装して .env のパースがより堅牢に。
- 起動時の不整合防止
  - run_execution/run_monitoring が停止フラグ検知を行い、安全に起動中止・停止できるようにして、誤動作による発注・監視の継続を防止。
- DB 初期化の冪等化
  - init_monitoring_db の呼び出しにより、監視テーブルが存在しない環境でも安全に起動できるよう改善。

### 既知の問題 / 注意点 (Known issues / Notes)
- research/factor_research.py の calc_momentum 実装はファイル末尾で途中終了している（未完）。実データを用いた完全なファクター計算は今後の実装予定。
- position_sizing の price の欠損（0.0）によりエクスポージャーが過少見積りされる可能性がある旨を注記（将来的に前日終値などのフォールバックを検討）。
- process_priority.set_cpu_affinity は権限や OS に依存し、失敗した場合は警告でスキップされる。必要に応じて実運用サーバでの事前確認を推奨。
- validate_config による YAML 検証は PyYAML 非インストール時はスキップされる（警告）。YAML 検証を有効にするには PyYAML を導入すること。

### セキュリティ (Security)
- 本リリースではセキュリティ修正は特になし。シークレットは .env に保管する想定で、config_setup では .env を Git 管理から除外するよう注意書きあり。

---

今後の予定（例）
- research モジュールの完全実装（Momentum / Value / Volatility / Liquidity の各ファクター計算）
- ExecutionEngine と RiskManager の統合テスト・シミュレーション強化
- Paper Trading の検証レポートを自動化し CI での定期チェックを追加
- ロギングの Structured Logging（JSON）対応や監視アラート（LINE連携）の拡張

もし特定の変更点をより詳しく記述したい場合は、対象のファイルや関数を指定してください。