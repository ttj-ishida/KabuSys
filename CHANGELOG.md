# Changelog

すべての注目すべき変更はここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のリリース履歴は以下の通りです。

## [0.1.0] - 2026-04-18

初回リリース。コードベースから推測される主要機能と変更点をまとめています。

### 追加 (Added)
- 実行用 CLI スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV による paper_trading モード対応：paper_trading 時は専用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient 経由で発注をシミュレートする設計。
    - PID ファイル管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）に対応。
    - 実行中スレッドを監視し、停止フラグで安全にエンジン停止する仕組みを実装。
    - RiskManager、OrderManager、Reconciler 等の組み立て処理を含む。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出しデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する旨の挙動。

- 設定管理・ユーティリティ
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env/.env.local の読み込みルール（OS 環境変数を保護しつつ .env.local で上書き可能）。
    - 複雑な .env パース実装：export プレフィックス、クォート内のエスケープ、インラインコメント扱い等に対応。
    - Settings クラスにより各種環境変数アクセスを提供（J-Quants / kabuAPI / DB パス / PID/kill flag 設定 / 監視しきい値 / 環境判定など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）とログレベルチェック。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。
    - 秘匿入力のマスク、既存値の再利用、保存確認機能を実装。
    - デフォルト項目や説明を含むテンプレート出力。
  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数の存在チェック、プレースホルダ検出、DB パスや config/*.yaml の存在・パースチェック（PyYAML が利用不可ならスキップして警告）。
    - KABUSYS_ENV=live のときに追加警告（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険な設定など）。
    - --strict モードで警告を FAIL 扱いにできるオプション。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。
    - レジームは 'bull'/'neutral'/'bear' をサポート。未知のレジームは 1.0 にフォールバック（警告）。
    - セクター不明 ("unknown") の扱いと既存保有を考慮したエクスポージャ計算を実装。
  - portfolio/position_sizing.py
    - position size（発注株数）計算ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap、コストバッファ（スリッページ・手数料見積り）を考慮したスケーリング処理。
    - 利用可能現金に対するスケールダウンと余剰キャッシュを用いた端数調整ロジックを実装。

- リサーチ / ファクター計算
  - research/factor_research.py（ファクター計算モジュール）
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルを用いて Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計（関数化、日数定数を定義）。
    - 設計方針として外部 API へアクセスせず、DuckDB + SQL/Python で完結することを明示。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - --from/--to/--db オプションで期間および DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を参照。
    - P95 計算、NULL/データ欠損ハンドリング、しきい値閾値定義を実装。

- 共通ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を提供。
    - stdout への StreamHandler（stdout を使用）、日次ローテートのファイルハンドラ（TimedRotatingFileHandler / デフォルト logs/ 、30 日保持）を設定。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしコンソールのみで継続するフォールバック実装。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定 (set_process_priority)。
    - CPU affinity を設定する set_cpu_affinity を提供（psutil ベース、失敗時は警告でスキップ）。
    - 起動時に優先度を "high" に設定する呼び出し箇所あり（run_execution/run_monitoring）。
  - utils モジュールを通じて、起動スクリプトから一貫した動作を提供。

### 変更 (Changed)
- 初回リリースのため該当なし（新規機能集合のリリース）。

### 修正 (Fixed)
- 初回リリースのため該当なし。ただし多くの箇所で安全なフォールバック動作（例: ディレクトリ作成失敗時のログ出力抑制、環境変数不備の警告とフォールバック、DB 存在チェックなど）を実装して堅牢性を高めている。

### 注意点 / 既知の制限 (Notes)
- .env 自動ロードはプロジェクトルートが検出できない場合スキップされる（パッケージ配布後の動作互換を考慮）。
- PAPER_FILL_MODE や KABUSYS_ENV 等の環境変数に不正値が設定された場合は ValueError を送出する箇所があるため、validate_config や config_setup での事前確認を推奨。
- process_priority / cpu_affinity は権限やプラットフォームに依存し、失敗時は警告を出してスキップする実装。
- 一部 TODO コメントあり（例: position_sizing の銘柄別 lot_size 対応、risk_adjustment の価格フォールバック等）。

---

（この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際の開発履歴やコミットログとは差異がある可能性があります。）