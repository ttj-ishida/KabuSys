CHANGELOG
=========

すべての日付はリリース日を示します。  
この CHANGELOG は Keep a Changelog の形式に準拠しています（重要な変更のみを記載）。  
コードベースからの実装内容をもとに推測して記載しています。

Unreleased
----------
- 今後の改良候補（例）
  - ai/news_nlp の部分失敗時のより細かなロールバック/トランザクション制御
  - position_sizing の銘柄ごとの lot_size サポート（TODO に言及あり）
  - duckdb SQL の追加最適化・インデックス検討
  - 単体テストや型チェックの網羅強化

[0.1.0] - 2026-04-13
--------------------
Added
- 初回公開: KabuSys 基幹モジュール群を追加
  - 実行系
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用し本番 DB と分離する挙動を実装（デフォルト path: data/paper_trading.db）。
      - 起動時にプロセス優先度を High に設定するフックを追加。
      - BrokerClientFactory によるブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
      - RiskConfig にデフォルトのリスク制約（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。
  - 監視系
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
      - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を参照する（監視は常に本番データを監視）。
      - プロセス優先度設定を起動直後に実行。
  - 設定管理
    - src/kabusys/config.py
      - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
      - .env/.env.local の読み込み順序と上書きルール（OS 環境変数を protected として保護）。
      - 複雑な .env のパースロジックを実装（export 指定、クォート＋バックスラッシュエスケープ、インラインコメント取り扱い等）。
      - Settings クラスを提供し、J-Quants / kabuAPI / DB パス / PID/KILL フラグ /閾値等の取得を型安全に提供。
      - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の入力値検証を追加。
  - ポートフォリオ構築（純関数群）
    - src/kabusys/portfolio/
      - portfolio_builder: 候補選定 / 等配分・スコア加重配分を追加（スコアが全て 0 の場合は等配分にフォールバック）。
      - risk_adjustment: セクター上限適用ロジック（既存ポジションのセクター別エクスポージャ計算）と市場レジームに基づく投下資金乗数（bull/neutral/bear のマップ）を追加。
      - position_sizing: 株数計算ロジックを追加（risk_based / equal / score の allocation_method サポート、単元株丸め、aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り）。
      - 上記は全て DB 非依存の純関数でメモリ内計算に限定。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - Momentum / Volatility / Value ファクターの DuckDB ベース実装を追加（prices_daily / raw_financials を利用）。
      - 各関数は欠損データや十分なウィンドウがない場合に None を返すなど安全に設計。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（任意ホライズン）、IC（Spearman）計算、ファクター統計サマリ、ランク付けユーティリティを追加。
      - ランク計算は同順位を平均ランクで扱い、丸めで ties の取りこぼしを防止。
    - research/__init__.py で zscore_normalize 等のエクスポートを提供。
  - AI ニューススコアリング
    - src/kabusys/ai/news_nlp.py
      - raw_news を基に OpenAI (gpt-4o-mini) を使った銘柄別センチメントスコアリング機能を追加。
      - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を明確に定義し、ルックアヘッドバイアスを避ける（外部に datetime.today() を使わない設計）。
      - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大化対策（記事数・文字数上限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分更新（対象コードのみ DELETE→INSERT）等の安全策を実装。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 検証レポート生成スクリプトを追加（CLI: --from/--to/--db）。
      - 稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計し、PASS/FAIL 判定を出力する閾値を定義（例: uptime 99%、fill_rate 90%、P95 latency 200 ms）。
      - DB が存在しない・テーブル欠如時の安全なフォールバック処理を実装。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - Windows/Linux/macOS の差分を吸収してプロセス優先度を設定するユーティリティを追加（nice 値、HIGH_PRIORITY_CLASS 等の適応）。
      - CPU affinity を最初 N コアに固定する補助関数を追加（権限不足や未対応 OS では警告を出してスキップ）。
  - パッケージ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- 設計上の決定（初期設計として明示）
  - 監視 DB と Paper Trading DB を明確に分離（監視は常に production sqlite_path を使用、paper_trading は分離された sqlite を使用）。
  - DuckDB を分析/リサーチ用のローカル列指向 DB として採用し、prices_daily/raw_financials テーブルを参照する前提に設計。
  - 外部 API 呼び出し（注文やブローカー操作）は execution モジュールに限定し、research/ai は本番口座や発注 API に一切アクセスしないポリシーを明記。

Fixed
- フォールトトレランスの強化
  - run_monitoring のポーリングループで check_once() からの例外を捕捉してログ出力後に待機を続行するようにし、単発エラーで監視ループが停止しないように改善。
  - process_priority の権限不足や未対応環境での例外をキャッチして警告ログを出すようにし、起動失敗を防止。

Security
- 機密情報の取り扱いに関する注意
  - Settings は必須キー未設定時に ValueError を送出して明示的に fail-fast にする（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
  - .env の自動ロード時に OS 環境変数を protected として上書きを防止する仕様を採用。

Notes / Implementation details
- .env パーサは export 形式・クォート内のバックスラッシュエスケープ・インラインコメント等を考慮した堅牢な実装になっているため、現場で多様な .env 記述を扱いやすい。
- ai/news_nlp は OpenAI クライアントに直接 OpenAI の公式クライアントを使用（OpenAI(api_key=...)）。
- portfolio.position_sizing の aggregate cap 調整は lot_size 単位での丸めと fractional remainder による再配分を行い、再現性のため二次キーに code を使ってソートする。
- research.feature_exploration.calc_ic は ties（同順位）を平均ランクで扱い、サンプル数が不足する場合（<3）には None を返すなど安全策を講じている。
- paper_verification_report はP95の算出、各種 None 安全処理、及び出力フォーマット（日本語）の整備を行っている。

Deprecated
- なし

Removed
- なし

References
- 主要実装ファイル一覧（代表）:
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/config.py
  - src/kabusys/portfolio/*
  - src/kabusys/research/*
  - src/kabusys/ai/news_nlp.py
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/utils/process_priority.py

---

注: 上記は提供されたソースコードから推測して作成した CHANGELOG です。実際のコミット履歴や変更履歴に基づく正確なログを必要とする場合は、Git の履歴（git log）やリポジトリのタグを参照してください。