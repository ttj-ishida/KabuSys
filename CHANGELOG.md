# CHANGELOG

すべての重要な変更は本ファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています（日本語訳）。

- リリースポリシー: 互換性のない変更はメジャー、機能追加はマイナー、バグ修正はパッチとして扱います。

## [Unreleased]

次回以降に対応予定・注意点（コード内の TODO／未実装に基づく推定）
- research.factor_research モジュールの一部実装（calc_momentum など）が途中で切れている／完成が必要。  
- portfolio.position_sizing:
  - 銘柄ごとの単元（lot_size）を銘柄マスタから取得する拡張（現在はグローバルな lot_size 固定）を予定。  
- portfolio.risk_adjustment:
  - price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価）の利用検討。  
- 全体:
  - 追加の統合テスト・ドキュメント整備（特に paper_trading と live の動作差分確認）を推奨。

---

## [0.1.0] - 2026-04-23

Added
- 初期リリース: KabuSys v0.1.0 を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 設定・環境管理
  - .env 自動読み込み機構を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込む。
    - export 形式・クォート・インラインコメント等を考慮した堅牢なパーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - Settings クラスを実装して環境変数を型付きプロパティで参照可能に。
    - DB パス、Paper Trading 用設定、監視しきい値、ログレベル判定、環境判定（development/paper_trading/live）などを提供。
    - PAPER_FILL_MODE のバリデーションを実装（"instant"|"partial"|"never"|"reject"）。

- 起動 / ランナー
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - 起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て。
    - ExecutionEngine をデーモンスレッドで起動、停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - PID ファイル管理（data/execution.pid）をサポート。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit など）を初期化。
  - 監視プロセス起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告。
    - SystemMonitor を用いたポーリングループ、停止フラグ検知で終了。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視専用 DB の初期化を実行）。
    - DuckDB 接続も初期化して分析向け連携を想定。

- 設定支援・検証 CLI
  - 対話式 .env 設定ウィザード（src/kabusys/config_setup.py）を追加。
    - よく使われる設定項目を対話で入力・既存値のマスク表示・保存をサポート。
    - .env 書き出しテンプレートを用意。
  - 設定検証ツール（src/kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DBパスの親ディレクトリチェック、config/*.yaml の存在および YAML パース（PyYAML があれば）の検証、live 向け追加警告を実行。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順（同点は signal_rank）で上位 N を選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコア 0 の場合は等配分にフォールバックし警告）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価を基にブロック）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知は 1.0 にフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に対応した株数算出、単元（lot_size）で丸め、1 銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、端数配分アルゴリズムを実装。
    - コメントで将来の拡張（銘柄別 lot_map）を明記。

- モニタリング / 検証ツール
  - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
    - DB からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポートを出力。
    - 閾値を定義して PASS/FAIL 判定を行う（稼働率、成功率、P95 など）。
    - --from/--to/--db オプションで期間と DB を指定可能。

- 研究用モジュール
  - research.factor_research（src/kabusys/research/factor_research.py）を追加（ファクター計算の骨格）。
    - Momentum / Value / Volatility / Liquidity 等を想定した定数と calc_momentum のインタフェース定義を追加（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。
    - 設計方針として SQL + Python を併用して外部 API なしで計算することを明記。

- ユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - StreamHandler を stdout（標準出力）に設定し、TimedRotatingFileHandler で日次ローテーション（30 日保持）をサポート。
    - ログレベル・ログディレクトリの解決順と失敗時のフォールバックを安全に実装。
  - プロセス優先度設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) による CPU ピンニングを提供（権限不足等の例外は警告でスキップ）。

Changed
- N/A（初期リリースのため破壊的変更履歴なし）

Fixed
- N/A（初期リリースのためバグ修正履歴なし）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

---

開発者向けメモ
- 本リリースでは paper_trading と live のデータ分離を意識した設計を行っています（run_execution の DB 選択、検証ツール等）。本番運用前に validate_config を使って設定チェックを実施してください。  
- ログ出力先ディレクトリ作成に失敗した際はコンソール出力のみにフォールバックします。ログディレクトリのパーミッションを事前に確認してください。  
- stop フラグ（data/stop_requested.flag）や kill flag の挙動は起動時の設定（KILL_FLAG_CLEAR_ON_START 等）に依存します。特に本番（KABUSYS_ENV=live）では設定値に注意してください。