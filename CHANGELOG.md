CHANGELOG
=========

すべての重要な変更点を記録します。これは Keep a Changelog のフォーマットに準拠しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

Unreleased
----------

（現時点のワーキングツリー。リリース前の変更はここに記載します。）

0.1.0 - 2026-04-13
------------------

Added
- 初回公開リリース。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderRepository・OrderManager・RiskManager・Reconciler の組み立て、ExecutionEngine のセッション実行を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、監視用 DB 初期化、pid ファイル管理を実装。
- 設定管理
  - config.py: .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）を追加。環境変数保護（OS 環境変数の上書きを制御）を実装。
  - Settings クラスを導入し、各種環境変数（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定など）をプロパティで提供。値のバリデーション（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）を含む。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア全体が 0 の場合のフォールバックを実装。
  - portfolio.risk_adjustment: セクター集中制限適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数計算 (calc_regime_multiplier) を追加。unknown セクターの扱い、レジーム不明時のフォールバック動作を定義。
  - portfolio.position_sizing: position sizing（risk_based / equal / score）、単元株丸め、aggregate cap によるスケール調整、手数料/スリッページ用の cost_buffer を実装。
  - portfolio/__init__.py: 主要関数のエクスポートを追加。
- 監視・ユーティリティ
  - utils.process_priority: プラットフォーム差分を吸収したプロセス優先度設定 (set_process_priority) と CPU affinity 設定 (set_cpu_affinity) を追加。Windows / POSIX の差分、権限不足時の警告処理を実装。
- 研究・ファクター計算
  - research.factor_research: DuckDB を用いたファクター計算機能を追加（calc_momentum、calc_volatility、calc_value）。各ファクターは prices_daily / raw_financials テーブルを参照し、データ不足時は None を返す設計。
  - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、ファクター統計サマリー (factor_summary)、ランク化ユーティリティ (rank) を追加。pandas に依存しない純標準ライブラリ実装。
  - research/__init__.py: zscore_normalize の再エクスポートを含む主要関数群をエクスポート。
- AI ニューススコアリング
  - ai.news_nlp: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。処理フロー、時間ウィンドウ計算（JST→UTC 変換）、チャンク処理、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリッピングを備える。API キー未設定時の ValueError を導入。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。PAPER_TRADING_SQLITE_PATH を参照してシステム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して判定（PASS/FAIL）を出力。P95 計算や期間フィルタ処理を実装。
- DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db の利用を通じ、監視用テーブルの冪等な初期化を実行するよう統合（run_execution/run_monitoring）。

Changed
- （この初回リリースにおける主要な設計決定）
  - 監視プロセスは KABUSYS_ENV に関係なくデフォルトの本番 sqlite_path（data/monitoring.db）を使用するよう明示。
  - run_execution は paper_trading 環境判定により paper 用専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。

Fixed
- env ファイルパーサの強化:
  - export プレフィックス対応、クォート文字列内でのバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなし時の '#' をコメントとして扱うルール（直前がスペース/タブ の場合）などを実装し、より堅牢に .env を読み込めるようにした。
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックする実装（警告出力を追加）。
- position_sizing の aggregate cap ロジック: cost_buffer を加味した保守的なコスト見積もりと、端数処理（lot_size 単位）に基づく再配分ロジックを実装。

Security
- .env 自動読み込み時に OS 環境変数を protected として上書きを防止する仕組みを導入。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供。

Notes / Known limitations
- position_sizing や apply_sector_cap は価格欠損（0.0）の場合にエクスポージャーが過少に見積もられる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨を TODO コメントとして残している。
- ai.news_nlp は OpenAI API を使用するため API 利用制限・コスト・レスポンスフォーマットの破損に対する運用上の注意が必要。部分失敗時は影響を最小化するため変更対象コードを絞って置換する設計になっている。
- research モジュールは DuckDB 内の prices_daily / raw_financials テーブルに依存するため、データ品質に応じて一部指標が None を返すことがある。

Acknowledgements
- 本プロジェクトは DuckDB、psutil、OpenAI クライアント等の OSS を利用しています。

---

今後の予定（例）
- 単元株ごとの lot_size を銘柄別に扱う拡張（stocks マスタの導入）
- ai.news_nlp の出力検証強化および非同期バッチ処理最適化
- より詳細なモニタリング指標（ディスク/I/O、プロセス別メモリ内訳）の追加

（以上）