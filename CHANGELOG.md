CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
この CHANGELOG は「Keep a Changelog」規約に準拠しています。

[Unreleased]
------------

（現時点のコードはリリース v0.1.0 相当の機能群を含むため、未リリース項目はありません。）

0.1.0 - 2026-04-16
------------------

追加 (Added)
- 基本パッケージ初期実装
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 設定管理（kabusys.config）
  - .env / .env.local の自動ロード機構（プロジェクトルートの検出を行い、OS 環境変数を保護して読み込み）。
  - 複雑な .env 行のパースを実装（export プレフィックス、クォート文字列、インラインコメントの扱い、エスケープ対応）。
  - 必須環境変数チェック用 _require() と Settings クラスを提供。
  - 各種設定プロパティを追加：
    - データベースパス: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
    - Paper Trading の fill モード検証（PAPER_FILL_MODE）
    - PID / kill flag / 監視閾値（CPU/MEM/DISK）等の監視関連設定
    - 環境種別検証 (KABUSYS_ENV: development | paper_trading | live) とユーティリティプロパティ（is_live / is_paper / is_dev）
    - LOG_LEVEL の検証

- 実行エントリ群
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時には paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskConfig によるデフォルトリスク制約（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。initial_portfolio_value を broker.get_available_cash() から取得。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による優雅な停止を実装。PID ファイル管理とタイムアウト付き join を実装。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する（監視テーブル初期化）。
    - stop_requested.flag を検知してループ終了、check_once() の例外はログに出力して次ポーリングへ継続。
    - プロセス優先度を最初に "high" に設定する処理を追加。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) 実装：Windows/Linux(macOS/FreeBSD) を吸収して優先度 (high/normal/low) を設定。権限や未対応 OS は警告でスキップ。
  - set_cpu_affinity(cpu_count) 実装：指定コア数に固定するユーティリティ（None 指定で無効化）。権限不足時は警告でスキップ。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順、同点は signal_rank 昇順でのタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額にフォールバックして WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合、新規候補を除外。既存保有のうち "unknown" セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは警告の上 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（risk_based / equal / score）。
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）でのスケーリング、cost_buffer を用いた保守的見積り、スケーリング時の残余配分アルゴリズム（端数処理）を実装。
    - price 欠損時のスキップやログ出力、各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer）をサポート。

- 研究・特徴量計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離率を DuckDB の window 関数を使って計算。
    - calc_volatility: ATR(20), ATR 比率、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播に配慮）。
    - calc_value: raw_financials から直近財務データを取得し PER/ROE を計算（prices_daily と結合）。
  - feature_exploration:
    - calc_forward_returns: LEAD を使って複数ホライズンの将来リターンを一括取得。horizons のバリデーション（1..252）を実施。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を実装。データ不足時は None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - DuckDB を用いた SQL ベースの実装により、大規模時系列処理を想定した設計。

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使ったニュースのセンチメントスコア生成機能を実装（設計段階を含む）。
  - calc_news_window: target_date に対するニュース収集ウィンドウ計算（JST→UTC 変換）を実装。
  - score_news: API キー確認、記事集約（銘柄ごと最大記事数・文字数でトリム）、バッチ処理、429/ネットワーク/5xx に対する指数バックオフリトライ方針、応答の厳密 JSON バリデーション、スコアの ±1.0 クリップ、部分失敗に備えたテーブル書き込み戦略を設計。
  - OpenAI 未設定時には明確な ValueError を発生させる。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 検証レポート生成スクリプトを追加。
  - system_status / trade_logs / risk_logs テーブルからシステム安定性、注文成功率、送信率、リスク却下数、レイテンシ指標（avg/max/P95）を集計。
  - P95 計算ユーティリティ、日付フィルタ、OperationalError によるテーブル未存在時のフォールバック（N/A 表示）を実装。
  - CLI 引数 (--from, --to, --db) をサポートし、閾値に基づく PASS/FAIL 判定を表示。

変更 (Changed)
- DB 利用方針の明確化
  - 監視は環境に関わらず本番 sqlite_path を使用する仕様を明記。
  - paper_trading 環境では専用 SQLite を使用して本番 DB と完全分離する実装を run_execution に導入。

- ログ・例外の扱いを厳格化
  - run_monitoring の check_once() 内の予期せぬ例外をキャッチしてログを出し、ループ継続するフェイルセーフを追加。
  - process_priority 内の失敗ケースは警告ログでスキップするように変更（権限問題や未対応 OS を想定）。

修正 (Fixed)
- env ファイルパーサの堅牢化
  - クォート文字列内のバックスラッシュエスケープ対応、コメント扱いの厳密化、export プレフィックス対応を行い .env のパース不整合を低減。

- weight/score 周りの健全性向上
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックして警告を出すように修正。
  - calc_position_sizes: price が無効な場合のスキップ、lot_size による丸め、aggregate cap によるスケーリング・残余配分ロジックを導入して注文数量の過剰発注を防止。

- レポート・集計の耐障害性
  - paper_verification_report の各クエリ呼び出しを try/except で保護し、テーブル未作成時や OperationalError 発生時に N/A や 0 を返すフォールバックを実装。

既知の制約 / 注意点 (Known issues / Notes)
- ai/news_nlp の score_news 実装は設計方針や前処理ロジックを含むが、ファイル末尾が切れているため完全実装は要確認（実際の API 呼び出し・レスポンス処理の詳細はコード続きでの確認が必要）。
- position_sizing の price が欠損 (0.0) の場合、現在は単純にスキップする実装になっており、将来的に前日終値や取得原価などのフォールバック価格導入を検討する旨の TODO コメントあり。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、期待通り動作しない環境では警告が出て設定をスキップする。

セキュリティ (Security)
- OpenAI API 利用は明示的な API キー設定を必須化（score_news で未設定時は ValueError）。
- .env の自動ロード時に OS 環境変数は上書きされないよう保護（protected set）。

その他
- DuckDB を分析用途に採用し、prices_daily / raw_financials 等に対する SQL ベースの大規模時系列処理を想定した設計が中心。
- 全体的に「外部取引・発注処理と分析処理の明確な分離」「paper_trading による安全な検証環境」「フェイルセーフな監視とバッチ処理」を念頭にした実装群となっている。

今後の改善提案（短期）
- ai/news_nlp の完全実装とリトライ/バッチロジックのエンドツーエンドテスト。
- position_sizing の価格フォールバック戦略（前日終値など）追加。
- 設定や閾値の単体テスト追加（.env パーサの境界ケースや PAPER_FILL_MODE バリデーション等）。
- ExecutionEngine / SystemMonitor の統合テスト（stop flag、PID 管理、例外耐性）。

---

以上。必要であれば特定ファイルごとの差分やリリースノートの英語版も作成します。どの形式／粒度で整備するか指示ください。