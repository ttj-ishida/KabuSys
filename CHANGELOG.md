# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
日付はコードベースから推測したリリース時点（このスナップショット作成日）です。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-17
初期リリース（コードベースの最初の公開相当）。以下の主要機能・モジュールを含みます。

### 追加
- 全体
  - パッケージメタ情報としてバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - アプリケーション設定読み込みと環境変数管理（kabusys.config.Settings）。
    - プロジェクトルート自動検出（.git または pyproject.toml による）。
    - .env / .env.local の自動ロード（OS 環境変数優先、上書き保護機能付き）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - 複数の必須設定取得ユーティリティと値検証（KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL など）。
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）や監視関連設定（PID ファイル、閾値等）のプロパティを提供。

- 実行系 / 監視
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時に PaperTrading 用の専用 SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live を抽象化）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。スレッドで実行し停止フラグ（data/stop_requested.flag）で安全に停止可能。
    - 起動時に process priority を High に設定する処理を組み込む。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - SystemMonitor を用いたポーリング監視ループを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を使用（監視データは単一 DB に集約）。
    - 停止フラグ検知／KeyboardInterrupt により安全にシャットダウン。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder
    - 信号のスコア降順選定（select_candidates）。
    - 等配分（calc_equal_weights）・スコア加重配分（calc_score_weights）。全スコアが 0 の場合は等配分へフォールバック。
  - risk_adjustment
    - セクター集中制限の適用（apply_sector_cap）：既存保有のセクター比率が上限を超える場合、新規候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）：bull/neutral/bear をサポート、未知レジームは警告の上フォールバック。
  - position_sizing
    - position sizing ロジック（calc_position_sizes）：risk_based / equal / score の配分方式を実装。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超過した場合のスケーリング）を考慮。
    - cost_buffer を用いた手数料・スリッページ見積りをサポート。スケーリング後の残余キャッシュを使ったロット単位の再配分ロジックを実装。

- 研究・ファクター（src/kabusys/research/*）
  - factor_research
    - Momentum（mom_1m/mom_3m/mom_6m）と MA200 乖離、ATR ベースのボラティリティ、平均売買代金などを DuckDB の prices_daily / raw_financials を参照して計算（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 返却や、ウィンドウサイズ設定による安全な集計を考慮。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）。
    - スピアマンランク相関による IC 計算（calc_ic）とランク付けユーティリティ（rank）。
    - ファクター列の統計サマリー（factor_summary）。
  - research パッケージから上記ユーティリティをエクスポート（zscore_normalize を含む）。

- ツール（src/kabusys/tools）
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などを集計して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB 存在チェックを実装。
    - デフォルト DB は data/paper_trading.db。コマンドライン引数で期間／DB 指定可能。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント分析し、銘柄ごとの ai_score を ai_scores テーブルへ書き込むワークフローを実装。
  - バッチ処理（最大 20 銘柄/リクエスト）、テキスト長制限（記事数・文字数）、429/5xx/接続障害に対する指数バックオフ付きリトライを実装。
  - レスポンス検証、スコアを ±1.0 にクリップ、部分失敗時に既存スコアを保護するための部分置換戦略を採用。
  - ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を提供。ルックアヘッドバイアス防止のため外部時刻参照に注意。

- ユーティリティ（src/kabusys/utils）
  - process_priority
    - Windows/Linux/macOS（POSIX）差分を吸収してプロセス優先度を設定するユーティリティ（set_process_priority）。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加。権限不足や未サポート環境での失敗は警告出力してスキップ。

### 変更
- なし（初回リリース相当）

### 修正
- なし（初回リリース相当）

### 既知の注意点 / 今後の改善メモ
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少評価されてしまう旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する必要あり。
- ai/news_nlp:
  - DuckDB に対する executemany の制約（DuckDB 0.10）に関する注意があり、パラメータが空でないことを事前チェックしている。
- utils/process_priority:
  - 一部 OS（Windows 以外や未サポートプラットフォーム）では優先度設定をスキップして警告する実装。権限不足時は警告でフォールバックする設計。
- run_monitoring / run_execution:
  - 監視・実行はファイルフラグ（data/stop_requested.flag）で制御。デプロイ時のファイル配置／権限管理に注意が必要。
- テスト・例外ハンドリング:
  - 多くの DB クエリに対して sqlite3.OperationalError のキャッチが散見され、部分的なテーブル欠損やデータ不足に耐性を持つ設計だが、統合テストでの検証推奨。

---

（本 CHANGELOG は、提示されたソースコードの構成・コメント・実装から推測して作成しています。実際のリリースノートにはリリース日時やコミットハッシュ、影響範囲の詳細追記を推奨します。）