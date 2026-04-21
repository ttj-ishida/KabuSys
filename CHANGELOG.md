# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはリポジトリ内のコードから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-21

初回リリース。システム全体の起動スクリプト、設定管理、監視・実行エンジン、ポートフォリオ構築ロジック、ユーティリティ、及び検証ツールを含む。

### 追加
- 全体
  - パッケージ初期版を公開。パッケージのバージョンは `kabusys.__version__ == "0.1.0"`。

- 設定管理
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を起点）。OS環境変数 > .env.local > .env の優先順で読み込む。
  - Settings クラスを導入し、環境変数からアプリケーション設定を型付けで取得可能に。
    - J-Quants / kabuステーション / LINE / DB / 監視設定 / システム設定などをプロパティとして提供。
    - env（KABUSYS_ENV）とログレベルのバリデーションを実施。
  - PAPER_FILL_MODE（paper trading の約定挙動）サポート: "instant" | "partial" | "never" | "reject"。
  - Paper Trading 用 DB パスを別途指定可能: PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）。

- 設定補助 CLI
  - config_setup: 対話式ウィザードで .env の初期生成 / 更新を支援する CLI を追加。
    - 秘匿値はマスク表示。生成された .env テンプレートは Git にコミットしない旨の注意を含む。
  - validate_config: 起動前チェック用 CLI を追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ確認、config/*.yaml の存在および（PyYAML があれば）パース検証を行う。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START 警告など）。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、本番 DB と分離して paper_trading.db に記録。
    - 起動時にプロセス優先度を "high" にセットし、PID ファイル / stop フラグによる安全停止をサポート。
    - 注文管理コンポーネント群（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の初期化ルーチンを含む。
    - RiskManager のデフォルト設定を定義（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 等）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず production 用 sqlite_path を使用する設計（注意点として明記）。

- データ分析 / ツール
  - tools/paper_verification_report: Paper Trading の検証レポート生成ツールを追加。
    - 指標: 稼働率 (uptime_pct)、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg / max / P95）。
    - 合否基準（デフォルト閾値）を定義: 稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms。
    - --from / --to / --db オプションをサポート。DB 存在チェックと例外ハンドリングあり。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークに signal_rank を使用して候補選定。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分。スコア全ゼロ時は等配分にフォールバックし警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック。既存ポジションに基づくセクター露出を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数決定。
      - risk_based: 損切り幅と許容リスクからベースシェアを算出。
      - equal/score: 各銘柄配分重みから株数計算。
      - 単元株（lot_size）で丸め、1銘柄上限・アグリゲートキャップ（available_cash）に基づくスケールダウンを実装。
      - cost_buffer により保守的なコスト見積を実施。端数は残差の大きい順に lot 単位で追加配分。

- ユーティリティ
  - utils/logging_setup.py
    - 一貫したロギング初期化ユーティリティを追加。
      - StreamHandler を stdout に出力（cron 等でのリダイレクトを想定）、TimedRotatingFileHandler で日次ローテーション（30 日保持）。
      - 既存ハンドラをクリアして二重登録を防止。ログディレクトリ作成に失敗した場合はファイル出力をスキップして警告を出力。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（Windows / POSIX）を実装。
    - set_cpu_affinity: 指定コア数に固定する機能を提供（権限不足等は警告してスキップ）。

- 研究モジュール（骨子）
  - research/factor_research.py
    - モメンタム・ボラティリティ等のファクター計算を行うためのモジュールを追加（DuckDB 接続を受ける設計）。
    - モメンタム計算（calc_momentum）などの関数を実装開始（注: ファイルの最後が現状では途中までの実装/スニペット状態）。

### 変更
- なし（初期リリースのためイニシャル導入内容のみ）。

### 修正
- なし（初期リリース）。

### 既知の注意点（設計上の明記）
- run_monitoring は KABUSYS_ENV にかかわらず設定された sqlite_path（production 想定）を使用するため、監視 DB の扱いに注意が必要。
- config_setup によって生成される .env は秘匿情報を含むため、絶対に Git にコミットしないことを README 等で明記することを推奨。
- portfolio.position_sizing の価格欠損（price が 0.0 や未定義）の場合、エクスポージャーが過小評価される可能性があり、将来的にフォールバック価格の導入を検討する旨コメントあり。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で失敗する場合があり、実行時には警告でスキップする設計。

### セキュリティ
- 環境変数に必須のシークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を要求。validate_config でプレースホルダ値の検出や未設定検出を行う。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる（配布後の安全性を考慮）。

---

注: この CHANGELOG は与えられたソースコードから推測して作成したものであり、実際のコミット履歴や変更履歴に基づくものではありません。必要に応じて現実のコミットログ・リリースノートで補完してください。