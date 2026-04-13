CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣例に概ね準拠しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-13
-------------------

Added
- 初回リリース。以下の主要機能およびモジュールを追加。
  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを提供。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はログ警告のうえデフォルトにフォールバック。
      - 監視 DB は KABUSYS_ENV に依らず本番 sqlite_path を使用。
      - 起動時にプロセス優先度を "high" に設定（プラットフォームに依存して失敗時は警告）。
      - SIGINT (KeyboardInterrupt) を受け終了可能。DB 接続（SQLite / DuckDB）を確実にクローズ。
    - run_execution.py
      - ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db がデフォルト）を使用し、MockBrokerClient と分離された検証環境を提供。
      - ブローカークライアント生成（BrokerClientFactory）、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと session 実行を行う。
      - 起動時にプロセス優先度を "high" に設定。
  - 設定管理
    - kabusys.config.Settings を導入。
      - .env / .env.local の自動ロード（プロジェクトルート detection: .git または pyproject.toml を基準）。
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。
      - export KEY=val 形式、クォートされた値（エスケープ処理含む）、インラインコメント処理などに対応する .env パーサを実装。
      - 多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定 等）。
      - 入力検証を導入（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の有効値チェック）。
  - モニタリング DB 初期化ユーティリティ（init_monitoring_db）呼び出しを各起動スクリプトで実行（冪等）。
  - portfolio（銘柄選定と配分）
    - select_candidates: スコア降順・同点時は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化による配分（全銘柄スコア0 の場合は等配分にフォールバック）。
  - risk_adjustment（リスク調整）
    - apply_sector_cap: 既存保有に基づくセクター集中上限チェック（unknown セクターは上限適用外）。
    - calc_regime_multiplier: market レジーム (bull/neutral/bear) に基づく投下資金乗数を返す（既知レジーム以外は警告を出して 1.0 にフォールバック）。
  - position_sizing（株数決定）
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。
    - 単元（lot_size）で丸め、per-position 上限や aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer による保守的見積りを実装。
    - スケーリング時の端数処理は残差に基づく再配分で再現性を担保。
  - utils/process_priority
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows/Linux(macOS/FreeBSD) 間の差分を吸収。権限不足等はログ警告でスキップ。
  - research（因子計算・解析）
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を利用するファクター計算を実装（各ファンクションは target_date に対する結果を返す）。
    - calc_forward_returns: 将来リターンを任意ホライズンで計算（horizons の検証あり）。
    - calc_ic, rank, factor_summary: IC（Spearman ランク相関）、ランク付け、ファクター統計サマリーを提供。
    - 全体設計は外部 API 非依存、DuckDB 接続受け取りでサーバ側データにのみ依存する方針。
  - ai/news_nlp
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込むワークフローを実装。
    - 機能: ニュースウィンドウ計算（JST に基づく UTC 変換）、記事トリム（記事数・文字数上限）、最大 20 銘柄のバッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライ（上限）、JSON レスポンスの厳格バリデーション、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護する差替戦略（DELETE→INSERT を限定コードで実行）。
    - score_news は api_key 引数か環境変数 OPENAI_API_KEY を使う。未設定時は ValueError を送出。
  - tools/paper_verification_report
    - Paper Trading 用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）。閾値に基づく PASS/FAIL 判定を出力。
    - P95 算出、日付フィルタ（ISO8601 UTC 変換）、DB テーブル未存在時の安全なフォールバック（OperationalError キャッチ）を実装。

Fixed / Defensive changes
- 各所で入力検証・防御的コーディングを導入。
  - MONITOR_POLL_INTERVAL の不正値フォールバック（警告ログ）。
  - PAPER_FILL_MODE の有効値チェック（無効なら ValueError）。
  - Settings._require は未設定変数の際に分かりやすい例外メッセージを出す。
  - paper_verification_report ではテーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値にフォールバック。
  - AI モジュールでは OpenAI API のエラーを想定したリトライとフェイルセーフ（API失敗時はスキップして継続）を実装。

Documentation / Examples
- 主要コマンド例:
  - 監視ループ起動:
    - python -m kabusys.run_monitoring
    - 環境変数: MONITOR_POLL_INTERVAL（秒）
  - 実行エンジン起動:
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、Paper Trading DB を使用
  - Paper Trading 検証レポート:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - または --db PATH / 環境変数 PAPER_TRADING_SQLITE_PATH で DB 指定
- .env 自動ロード
  - プロジェクトルートに .env / .env.local を置くことで起動時に環境変数が読み込まれる（OS 環境変数は上書き保護）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

Notes / Breaking changes / Migration
- 監視（run_monitoring）は常に Settings.sqlite_path（本番用）を使用します。テストや paper_trading と完全に分離したい場合は別途運用を検討してください。
- OpenAI を使う ai/news_nlp.score_news を実行するには OPENAI_API_KEY（または関数引数）が必須です。未設定時は ValueError を発生させ処理を中止します。
- DuckDB のクエリは prices_daily / raw_financials / raw_news / news_symbols / ai_scores 等のテーブルを前提としています。スキーマ不整合や欠損があると計算結果が None になったり、ツールが想定どおり動作しない可能性があります。
- process_priority や cpu_affinity の設定は OS と権限に依存し、失敗するとログ警告が出て処理は継続します。
- position_sizing の将来拡張点: 銘柄別の lot_size を導入する予定（現行は全銘柄共通 lot_size を想定）。price 欠損時のフォールバック価格処理が TODO として残っています。

Acknowledgements / Implementation remarks
- DuckDB を分析 / 研究処理に利用し、高速な SQL ベースの因子計算を行う設計になっています。
- 外部 API 呼び出し（発注・口座情報取得）部分は BrokerClientFactory を介して抽象化され、paper_trading を用いた検証と本番の分離をサポートしています。
- 各モジュールは可能な限り副作用を抑えた純粋関数（portfolio や研究機能）と、外部資源（DB / API）を扱う副作用を伴うコンポーネントに分離しています。

--- 

必要であれば、各リリースノートのエントリをさらに分解して関数毎の変更点やファイル別の差分説明（例: 重要な関数のシグネチャ、戻り値、例外条件）を追加できます。どのレベルの詳細が必要か教えてください。