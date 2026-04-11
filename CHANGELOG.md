CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
リリース日や内容は、提示されたコードベースから推測して記載しています。

[Unreleased]
-------------

- （今後の変更をここに追記）

[0.1.0] - 2026-04-11
--------------------

Added
- 基本パッケージ初期リリース（kabusys v0.1.0）。
  - パッケージメタ情報: __version__ = "0.1.0" を導入。
- 実行／監視起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory によるブローカークライアント生成を採用（モックブローカーの利用を想定）。
    - OrderRepository/OrderManager/Reconciler/RiskManager を組み立て、ExecutionEngine.run_session() を実行。
    - プロセス優先度を最初に High に設定（set_process_priority）。
    - DuckDB と SQLite の接続管理（finally で明示的に close）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は実行環境に依らず本番 sqlite_path を使用（監視用 DB を明確に指定）。
    - プロセス優先度設定、DuckDB/SQLite 接続、例外ハンドリング付きのポーリングループを実装。
- 設定・環境変数管理を追加。
  - config.py
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロードする仕組みを導入（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサを独自実装し、export 形式・クォート・インラインコメント等に対応。
    - OS 環境変数を保護する protected オプションを実装（.env.local が OS 環境変数を上書きしない）。
    - Settings クラスを提供し、アプリ内から安全に各種設定にアクセス可能に（各種バリデーション付き）。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、PID/KILL フラグパス、閾値や PAPER_FILL_MODE（値検証）など多数の設定プロパティを実装。
- ポートフォリオ構築・調整ロジックを追加（純粋関数群）。
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・signal_rank によるタイブレークで候補選定。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑えるための候補フィルタ（売却予定銘柄の除外対応、"unknown" セクターの扱い）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（'bull'/'neutral'/'bear' のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score ベースの株数算出。単元株（lot_size）丸め、1銘柄上限・総投資上限の適用、cost_buffer を加味した保守的見積り、aggregate scaling と残差処理による安定的割当を実装。
- ユーティリティ（プロセス優先度・CPU affinity）を追加。
  - utils/process_priority.py
    - set_process_priority(level): Windows/Linux/macOS 等を吸収し psutil で優先度設定を行う。権限不足や未対応 OS の場合は警告ログを出して安全にスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定する機能。入力検証と権限失敗時のフォールバック。
- リサーチ／ファクター計算モジュールを追加（DuckDB ベース）。
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value: prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを算出（SQL ベース、欠損／十分な履歴がない場合は None 戻り）。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターンの一括取得（任意ホライズン対応、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算。データ不足時は None を返す。
    - rank, factor_summary: ランク付け（平均ランクによる同順位処理）と統計サマリ（count/mean/std/min/max/median）を純粋 Python で実装（外部依存なし）。
- AI 関連モジュールを追加（OpenAI を利用したニュース NLP / レジーム判定）。
  - ai/news_nlp.py
    - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを計算して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ算出（JST 基準の前日 15:00 〜 当日 08:30）、バッチ（最大 20 銘柄）での API 呼び出し、トークン肥大化対策（記事数・文字数制限）、レスポンスバリデーション（JSON mode の復元処理含む）、スコアクリップ、エクスポネンシャルバックオフによるリトライ、DuckDB への冪等書き込み（DELETE → INSERT をトランザクションで実行）を実装。
    - API キー未指定時は例外を投げる（安全設計）。
  - ai/regime_detector.py
    - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成し、日次の market_regime を算出して書き込む機能を実装（MA 偏差 70% / マクロ 30% の重み付け、閾値で 'bull'/'neutral'/'bear' を判定）。
    - prices_daily は target_date 未満のデータのみを使用するなど、ルックアヘッドバイアスへの配慮あり。API 失敗時はマクロセンチメントを 0.0 とするフォールバック。
- research パッケージのエクスポート整備（research/__init__.py）。
- パッケージエクスポート（portfolio, research, ai など）を整理。

Changed
- なし（初期リリースに相当するため変更履歴は追加のみ）。

Fixed
- 入力値検証やフォールバックを多数実装して堅牢性を向上:
  - MONITOR_POLL_INTERVAL が不正な値（0 以下や非整数）の場合にデフォルトへフォールバック。
  - PAPER_FILL_MODE の値検証を実装。無効値は ValueError。
  - calc_score_weights でスコア合計が 0 の場合に等金額配分へフォールバック（警告ログ）。
  - regime 判定や MA200 計算でデータ不足時に中立値を返す等の安全策を導入。
  - OpenAI 呼び出しにおけるリトライ・例外処理・レスポンス検証を強化。
  - DuckDB への書き込みで executemany の空リスト問題（DuckDB 0.10）を考慮して空チェックを実施。

Security
- OpenAI API キー等の必須値を取得する際に未設定の場合に例外を投げることで、誤った公開実行を防止する設計を採用。

Notes / その他
- 多くのモジュールは DuckDB の prices_daily / raw_financials / raw_news 等のテーブル存在を前提としているため、初期データ投入・スキーマ準備が必要。
- 一部のコメントに将来の拡張項目（lot_size の銘柄別化、価格フォールバックなど）が明記されている。
- 実機運用に際しては psutil によるプロセス優先度設定や CPU affinity 設定が権限により失敗する可能性があるため、ログでの確認を推奨。

参考
- 自動ロードされる .env の優先順位: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。