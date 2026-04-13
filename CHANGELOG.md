CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」規約に準拠しています。

フォーマット
-----------
- バージョン見出しは [Unreleased] または [X.Y.Z] - YYYY-MM-DD の形式を使用します。
- 変更はカテゴリ (Added, Changed, Fixed, Deprecated, Removed, Security) に分けて記載します。

[Unreleased]
------------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------
Added
- プロジェクト初期リリースとして以下の主要機能を実装。
  - 実行系
    - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
      - 環境ごとに本番/ペーパー（paper_trading）を切り替え可能。KABUSYS_ENV=paper_trading の場合は専用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全分離。
      - BrokerClientFactory を利用したブローカークライアント生成。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてセッション実行（engine.run_session）。
      - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。
      - 起動時にプロセス優先度を "high" に設定（プラットフォーム差異は utils/process_priority が吸収）。
  - 監視（Monitoring）
    - SystemMonitor 用ポーリングループ起動スクリプト (src/kabusys/run_monitoring.py)
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒、無効値はデフォルトへフォールバック）。
      - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB は常に本番の監視 DB に記録）。
      - monitoring DB の初期化（init_monitoring_db）を起動時に行う（冪等）。
  - 設定管理
    - Settings クラス (src/kabusys/config.py) により環境変数を統一管理。
      - .env / .env.local の自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml を基準）。OS 環境変数を保護するため上書きルールを実装。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - 複数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）。
      - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許容）。
      - KABUSYS_ENV の検証（development, paper_trading, live のみ許容）。
      - 各種スレッショルド値（CPU/MEMORY/DISK）やフラグを環境変数経由で設定可能。
      - .env パーサは export 構文、クォート、エスケープ、インラインコメント等に対応。
  - ポートフォリオ構築（純粋関数群）
    - 銘柄候補選定と重み付け (src/kabusys/portfolio/portfolio_builder.py)
      - select_candidates（スコア降順、同点時は signal_rank でタイブレーク）
      - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）
    - セクター制限・レジーム乗数 (src/kabusys/portfolio/risk_adjustment.py)
      - apply_sector_cap：既存保有のセクター比率が閾値を超える場合に新規候補を除外（"unknown" セクターは制限対象外）。
      - calc_regime_multiplier：market レジームに応じた資金乗数 (bull/neutral/bear) を提供（未知レジームはフォールバック）。
    - ポジションサイズ決定 (src/kabusys/portfolio/position_sizing.py)
      - allocation_method に応じた株数算出（risk_based / equal / score）。
      - 単元株（lot_size）で丸め、per-position 上限や aggregate cap を考慮してスケーリング。
      - cost_buffer を用いた保守的見積もりと余剰キャッシュを用いた切り上げ配分ロジックを実装。
  - リサーチ / ファクター計算（DuckDB ベース）
    - ファクター計算モジュール (src/kabusys/research/factor_research.py)
      - calc_momentum：1M/3M/6M リターン、MA200 乖離率等を計算。
      - calc_volatility：ATR20、相対 ATR、20日平均売買代金、出来高比等を計算。
      - calc_value：最新財務データ（raw_financials）と株価から PER / ROE を計算。
      - DuckDB の SQL ウィンドウ関数を活用した高効率実装。
    - 特徴量探索ユーティリティ (src/kabusys/research/feature_exploration.py)
      - calc_forward_returns：複数ホライズンの将来リターンをまとめて計算。
      - calc_ic：Spearman ランク相関（IC）を計算（最小有効レコード数チェックあり）。
      - rank / factor_summary：ランク付けと基本統計量集計（count/mean/std/min/max/median）。
    - research パッケージは zscore_normalize 等を外部にエクスポート（src/kabusys/research/__init__.py）。
  - AI / ニュース NLP
    - news_nlp モジュール (src/kabusys/ai/news_nlp.py)
      - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む。
      - バッチサイズ、記事数・文字数上限（トリム）、JSON Mode 応答検証、スコアクリップ、部分成功時の DB 更新戦略（部分置換）を備えた堅牢実装。
      - 429/ネットワーク/タイムアウト/5xx に対する指数的バックオフリトライ（上限制御）。
      - API キーは引数または環境変数 OPENAI_API_KEY で供給。未設定時は明確にエラー。
  - ツール
    - paper_verification_report (src/kabusys/tools/paper_verification_report.py)
      - ペーパー取引データベースから稼働率、注文成功率、送信率、P95 レイテンシなどを集計・判定してレポートを標準出力へ出力する CLI ツール。
      - デフォルト閾値（稼働率 99%、注文成功率 90% 等）を定義し PASS/FAIL 判定を行う。
      - 日付フィルタ／DB パス指定 (--from/--to/--db) に対応。
  - ユーティリティ
    - process_priority (src/kabusys/utils/process_priority.py)
      - set_process_priority(level) で Windows / POSIX を吸収して優先度設定（"high"/"normal"/"low"）。
      - set_cpu_affinity(cpu_count) でプロセスの CPU affinity を設定（利用不可環境では警告ログを出力してスキップ）。
      - 許可されていない OS や権限不足時は安全にスキップして警告ログ。
  - パッケージ基礎
    - パッケージメタ情報に __version__ = "0.1.0" を設定 (src/kabusys/__init__.py)。
    - パッケージ化を意識した __all__ の整備（portfolio, research 等の公開 API）。

Changed
- 起動/運用に関する設計上の重要点を明示。
  - 監視プロセスは設定にかかわらず本番 sqlite_path を使用する（監視データは常に本番側に記録）。
  - .env 読み込みはプロジェクトルートの検出に依存（__file__ を起点に親ディレクトリを検索）することで CWD に依存しない挙動を実現。
  - calc_position_sizes 等の関数は将来的な拡張（銘柄別 lot_size 等）を想定したコメント / TODO を含む。

Fixed
- 入力検証・堅牢性の改善。
  - MONITOR_POLL_INTERVAL が 0 以下や非整数のときは警告を出してデフォルトにフォールバック（run_monitoring）。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の不正値検出と明確なエラーを追加（Settings）。
  - .env パーサでのクォート/エスケープ/コメント処理に対応し、より実用的な .env 構文をサポート。

Notes / Implementation Details
- DuckDB はデータ分析処理（research, ai scoring の集約等）に利用。
- SQLite は主に監視・注文ログ等のトランザクション的データ保存に使用（paper_trading では別 DB を用いることで実運用と分離）。
- 外部依存:
  - psutil（プロセス優先度 / CPU affinity）
  - duckdb
  - openai（news_nlp で OpenAI API を呼ぶ際に使用）
- フェイルセーフ設計: AI API 失敗や DB テーブル未存在時にはログを残して処理を継続／安全にフォールバックする実装方針。

今後の予定（予定・提案）
- 銘柄別 lot_size のサポートや手数料・スリッページモデルの高度化（position_sizing の拡張）。
- news_nlp のモデル切替やローカルキャッシュによるコスト最適化。
- モニタリングの通知（LINE 等）や、監視指標の可視化ダッシュボード連携。
- テストカバレッジの拡充（特に OpenAI API 周りの統合テスト用フック）。

--------------------------------------------------------------------
（注）本 CHANGELOG はコード内容から推測して作成しています。実際のリリースノートや変更履歴と差異がある可能性があります。必要に応じて加筆・修正してください。