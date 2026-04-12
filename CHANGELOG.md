CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

- なし

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリース。KabuSys の基本コンポーネントを実装。
  - パッケージ情報
    - パッケージのバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - 設定管理 (src/kabusys/config.py)
    - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサの実装（export 形式・クォート・インラインコメント等への対応）。
    - 環境変数の取得ユーティリティ（必須チェック _require）。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス /監視設定 / システム設定 等をプロパティで取得。
    - 設定値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の許容値チェック）。
    - paper_trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH）と paper_fill_mode のサポート。
    - PID ファイル / kill フラグ /各種閾値（CPU/MEM/DISK）など監視・運用向け設定の提供。
  - 実行エントリ・監視
    - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
      - KABUSYS_ENV=paper_trading 時に MockBroker を使用して paper_trading DB に完全分離して記録する設計。
      - SQLite (本番または paper_trading) と DuckDB の接続管理。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
      - RiskManager のデフォルトコンフィグ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker, max_drawdown 等）。
    - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
      - SystemMonitor を初期化して永続ポーリングループを実行。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
      - 監視は環境に依らず本番 sqlite_path を使用する設計。
  - ユーティリティ (src/kabusys/utils/process_priority.py)
    - クロスプラットフォームでプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）。
    - 権限不足や未サポート環境で安全にスキップするための例外ハンドリングとログ出力。
  - ポートフォリオ構築 (src/kabusys/portfolio/)
    - portfolio_builder.py: 候補選定 select_candidates、等金額 / スコア加重重み計算 calc_equal_weights / calc_score_weights（全スコア 0 の場合は等配分へフォールバック）。
    - risk_adjustment.py: セクター集中上限適用 apply_sector_cap（既存保有を考慮、"unknown" セクターは除外適用せず）、市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知レジームは警告とフォールバック）。
    - position_sizing.py: 各銘柄の発注株数算出 calc_position_sizes（risk_based / equal / score の allocation_method をサポート、lot_size 単位切り捨て、aggregate cap スケーリング、cost_buffer を用いた保守的見積り、各種安全弁）。
    - パッケージ __init__ にて主要関数を公開。
  - リサーチ / ファクター計算 (src/kabusys/research/)
    - factor_research.py: DuckDB を使ったモメンタム / ボラティリティ / バリュー系ファクターの計算（mom_1m/3m/6m、ma200_dev、ATR20、avg_turnover、PER/ROE 等）。ウィンドウサイズや欠損時の扱いを明示。
    - feature_exploration.py: 将来リターン計算 calc_forward_returns（horizons の検証）、IC（Spearman ρ）計算 calc_ic、ランク付け rank、ファクター統計 summary を標準ライブラリのみで実装。
    - research パッケージは外部依存を最小化し、DuckDB のみ利用する方針。
  - AI ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news を OpenAI (gpt-4o-mini) でセンチメントスコア化して ai_scores テーブルへ書き込む機能を実装。
    - スコアリングの設計:
      - JST ベースのニュース収集ウィンドウを UTC に変換して抽出（calc_news_window）。
      - 銘柄ごとに記事を集約（記事数・文字数の上限でトリム）。
      - 最大 20 銘柄/チャンクでバッチ API 呼び出し。JSON モードで厳密な JSON レスポンスを期待。
      - 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフでリトライ（上限回数あり）。
      - レスポンスのバリデーション、スコアを ±1.0 にクリップ。
      - 成功チャンクのスコアのみ対象コードを絞って置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）し、部分的失敗時に既存データを保護する設計。
    - OpenAI API キーは引数または OPENAI_API_KEY 環境変数から解決。未設定時は ValueError を送出。
  - ツール (src/kabusys/tools/paper_verification_report.py)
    - Paper Trading 用検証レポート生成スクリプトを提供（コマンドラインから実行可能）。
    - 指標: 稼働率、注文成功率、送信率、リスク却下数、レイテンシ (avg/max/P95)。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）し、PASS/FAIL 判定を出力。
    - 日付フィルタ (--from / --to)、および --db オプション / 環境変数 PAPER_TRADING_SQLITE_PATH に対応。
    - DB の存在やテーブル欠落に対する安全なフォールバックを実装。
  - DB とクエリ基盤
    - DuckDB を分析用に使用（prices_daily / raw_financials / raw_news 等のテーブル参照を想定）。
    - SQLite をモニタリング / 注文リポジトリ等の永続層として使用（paper_trading モードでの完全分離をサポート）。
  - ロギングとフェイルセーフ
    - 起動時のログレベル設定、例外時のログ出力を徹底してフェイルセーフ（try/except 内でログ記録してループ継続など）。
    - 権限や外部 API 失敗時は処理をスキップして継続する方針。

Changed
- 初回リリースにつき変更履歴なし。

Fixed
- 初回リリースにつき修正履歴なし。

Security
- 初回リリースにつきセキュリティ修正なし。

注記
- ドキュメントやマイグレーション指示は含まれていません。運用時は .env.example を参考に環境変数を設定してください。
- 一部の TODO（例: position_sizing の銘柄別 lot_size サポート、価格欠損時のフォールバック等）がコード内に注記されています。今後の改善候補です。