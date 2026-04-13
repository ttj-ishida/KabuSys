CHANGELOG
=========
All notable changes to this project will be documented in this file.

このファイルは "Keep a Changelog" の形式に準拠しています。
リリース情報は日付順（新しいものを上）で記載します。

Unreleased
----------
- （現在の開発中の変更点はここに記載してください）

0.1.0 - 2026-04-13
------------------

Added
- 実行エントリ
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - プロセス起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine.run_session の起動処理を実装。
    - リスク管理の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をデフォルト値付きで組み込み。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒、0以下は無効としてフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py: .env 自動読み込み機能を追加（プロジェクトルート検出: .git / pyproject.toml）。
    - .env / .env.local のロード順序制御、既存 OS 環境変数を保護する protected 機能、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を実装。
    - .env の行パーサーを堅牢化（export 先頭対応、クォート内のエスケープ、インラインコメント処理）。
    - Settings クラスを実装し、主要な環境変数をプロパティ経由で取得するインターフェースを提供。
    - 各種バリデーション実装:
      - KABUSYS_ENV（development/paper_trading/live のみ許容）
      - LOG_LEVEL（DEBUG/INFO/...）
      - PAPER_FILL_MODE（instant/partial/never/reject のみ許容）
    - DB パス、pid_file_path、kill_flag 関連、閾値（CPU/MEM/DISK）などの標準プロパティを提供。

- 監視・ツール
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を使用して監視テーブルの冪等初期化を実行（run_execution/run_monitoring から呼び出し）。
  - tools/paper_verification_report.py: Paper Trading 向けの検証レポート生成ツールを追加。
    - CLI で期間指定可能（--from / --to / --db）。
    - 稼働率、注文成功率（Fill率）、送信率、リスク却下数、API レイテンシ（平均・最大・P95）等を算出して標準出力に整形表示。
    - パスが存在しない DB への親切なエラーメッセージを出力。
    - P95 計算、欠損データハンドリング、閾値（稼働率, fill_rate, send_rate, P95）に基づく PASS/FAIL 判定を実装。

- ポートフォリオ構築
  - kabusys.portfolio モジュールを追加。
    - portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights。全スコア 0 の場合は等配分にフォールバックし WARNING）。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier。未知レジームはフォールバックで 1.0）。
    - position_sizing: 各種配分方式（risk_based / equal / score）に基づく発注株数計算を実装。lot_size（単元）丸め、単銘柄上限・aggregate cap、cost_buffer を考慮したスケーリング・再配分アルゴリズムを搭載。
    - モジュールは純粋関数中心で DB 参照なし（メモリ内計算）。

- 研究（Research）
  - kabusys.research モジュールを追加。
    - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 接続から prices_daily / raw_financials を参照）。MA200、ATR20、平均売買代金、ボラティリティ等を算出。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）およびランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。外部ライブラリに依存せず純粋 Python + DuckDB SQL で実装。
    - DuckDB を用いることで大規模時系列データ処理を想定。

- AI / ニュース NLP
  - kabusys.ai.news_nlp モジュールを追加（OpenAI を利用したニュースセンチメントスコアリング）。
    - ニュース収集ウィンドウ計算（JST基準 → UTC 変換）を提供。
    - raw_news と news_symbols を銘柄毎に集約し、記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム。
    - OpenAI (gpt-4o-mini) を JSON Mode でバッチ送信（1 チャンクあたり最大 20 銘柄）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフ再試行を実装。
    - レスポンス検証、スコアの ±1.0 クリップ、部分成功時の ai_scores 更新（既存スコア保護のためコードを絞って置換）などのフェイルセーフを備える。
    - API キー未設定時は ValueError を発出。

- ユーティリティ
  - utils/process_priority.py:
    - Windows / POSIX を吸収するプロセス優先度設定（set_process_priority）を実装。対応 OS で nice / HIGH_PRIORITY_CLASS を設定、失敗時は警告でスキップ。
    - set_cpu_affinity: 最初の N コアにプロセスをピン留めする機能。入力検証とエラー時のフォールバックログを実装。

Changed
- 設計方針の明確化
  - 多くの副作用を持たない純粋関数（ポートフォリオ / リサーチ / ポジションサイズ計算）によりユニットテストと再現性を想定。
  - DuckDB をリサーチ／AI パイプラインのデータソースとして標準採用し、SQL と Python の併用で計算を実行。
  - 実行系（execution）と監視（monitoring）で使用する DB を環境別に分離（paper_trading は専用 DB）。

Fixed / Robustness improvements
- 環境変数パーシングの堅牢化: quoted value のエスケープ処理やコメントパースを改善し、.env の一般的な記法に対応。
- MONITOR_POLL_INTERVAL の不正値（0・負の数・非整数）に対するフォールバックと警告ログを追加。
- calc_score_weights: 全銘柄スコアが 0 の場合に等金額配分へフォールバックし、警告を出すようにしてゼロ除算を回避。
- position_sizing: aggregate cap 適用時の丸め・残差処理を実装し、lot_size 単位での再配分アルゴリズムを提供。価格欠損時のスキップや負荷低減のためのログを追加。
- process_priority: 対応外 OS でのスキップとアクセス権エラー（AccessDenied）を安全に扱うよう改善。

Security
- OpenAI API キーの必須チェックを実装し、未設定時は明確な例外を返す。
- .env 自動ロードは OS 環境変数を上書きしないデフォルト挙動（.env.local のみ override 可）で、重要な OS レベルのキー保護を行う。

Notes / Misc
- パフォーマンスを考慮して、研究系の SQL はウィンドウ関数と事前集計を多用しており、必要なスキャン範囲を限定するために calendar-day のバッファを設定している（例: momentum のスキャンは 400 calendar days）。
- エントリポイントスクリプトは起動時に pid_file を扱うための設定を読み取り、プロセス管理のための PID ファイル利用を想定。
- 一部の関数説明（docstring）で将来的な拡張（銘柄別 lot_size の導入、価格フォールバック戦略など）について TODO コメントを残している。

Acknowledgements
- 本リリースはプロジェクトの初期コア機能群（実行・監視・ポートフォリオ構築・リサーチ・ニュース NLP・ツール）を実装したものです。各モジュールはテスト・監査・パラメータチューニングを経て運用へ移行してください。

References
- Keep a Changelog: https://keepachangelog.com/en/1.0.0/