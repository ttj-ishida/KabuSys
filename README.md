# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants 経由の株価・財務・市場カレンダー収集）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）と自動読み込み
- 使い方（簡易サンプル）
- ディレクトリ構成

---

プロジェクト概要
- 日本株向けのデータ基盤＋研究／戦略支援ライブラリ群。
- DuckDB を中心にデータを保持し、J-Quants API から差分取得するETLパイプラインを備えます。
- ニュースの収集・前処理、OpenAI（gpt-4o-mini）を用いたセンチメント評価、レジーム判定、ファクター計算、データ品質チェック、監査ログ（注文→約定のトレーサビリティ）などを提供します。
- Look-ahead bias（先見性バイアス）回避や冪等性（INSERT ... ON CONFLICT）など運用上の考慮が多数組み込まれています。

---

主な機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートを検出）
  - settings オブジェクト経由で必須設定を取得
- データ収集（kabusys.data）
  - jquants_client: J-Quants API クライアント（レートリミット、トークン自動リフレッシュ、リトライ付き）
  - pipeline: run_daily_etl 等の日次 ETL（株価・財務・カレンダー）
  - news_collector: RSS 収集、前処理、SSRF対策、冪等保存
  - calendar_management: JPX カレンダー管理＆営業日ロジック
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログ（signal_events, order_requests, executions）の初期化／DB化
  - stats: 汎用統計（zscore 正規化）
- AI（kabusys.ai）
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM でスコア付けし ai_scores に保存
  - regime_detector.score_regime: ETF（1321）のMA乖離とマクロニュースを組み合わせて市場レジーム判定
- 研究（kabusys.research）
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: forward returns, IC（Spearman）、統計サマリー、ランク付けなど

---

セットアップ手順（開発環境）
前提: Python 3.10 以上を推奨（typing の | 型注釈等を利用）

1. リポジトリをクローン（例）
   git clone <repository_url>
   cd <repository>

2. 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell)

3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   補足: 実際の運用では依存に応じてさらにパッケージを追加してください（例: slack SDK 等）。

4. 開発インストール（編集しながら使う場合）
   pip install -e .

---

環境変数（.env）と自動読み込み
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml）を探索し、優先順位で環境変数を読み込みます:
  1. OS 環境変数（最優先）
  2. .env.local（存在する場合、上書き）
  3. .env（存在する場合）
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- 必須環境変数（settings から参照される）:
  - JQUANTS_REFRESH_TOKEN   : J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD       : kabuステーション API パスワード（必須）
  - SLACK_BOT_TOKEN         : Slack 通知用トークン（必須）
  - SLACK_CHANNEL_ID        : Slack チャネル ID（必須）
  - OPENAI_API_KEY          : OpenAI 呼び出しに使用（score_news / score_regime の引数でも指定可能）
- 任意 / デフォルト:
  - KABUSYS_ENV             : development | paper_trading | live（デフォルト development）
  - LOG_LEVEL               : DEBUG|INFO|...（デフォルト INFO）
  - KABU_API_BASE_URL       : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH             : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH             : 監視DB等の sqlite パス（デフォルト data/monitoring.db）

.env の例（.env.example を作成しておくと便利）
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

使い方（代表的なサンプル）
以下は簡単な Python スニペット例です。必要に応じてログ設定等を追加してください。

- DuckDB 接続を作って日次 ETL を実行
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリングを実行（OpenAI API キーは環境変数 OPENAI_API_KEY でも可）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB 初期化（監査用専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn を使って監査テーブルへ挿入等を行う

- 研究用ファクター計算
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect(str(settings.duckdb_path))
  momentum_records = calc_momentum(conn, date(2026,3,20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(momentum_records, ["mom_1m", "mom_3m", "mom_6m"])

注意点
- OpenAI 呼び出しには API キー（OPENAI_API_KEY）が必要です。score_news / score_regime は api_key 引数でキーを上書き可能です。
- J-Quants API はレートリミットと認証トークン（リフレッシュ）を扱います。JQUANTS_REFRESH_TOKEN を .env に設定してください。
- DuckDB への書き込みは多くが ON CONFLICT DO UPDATE により冪等設計になっています。

---

ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイル一覧（本リポジトリの実装に基づく抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境設定 / .env 自動読み込み
    - ai/
      - __init__.py
      - news_nlp.py                  # ニュースセンチメント計算 / ai_scores 書き込み
      - regime_detector.py           # 市場レジーム判定（1321 MA + マクロニュース）
    - data/
      - __init__.py
      - jquants_client.py            # J-Quants API クライアント、保存関数
      - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
      - etl.py                       # ETLResult の再エクスポート
      - news_collector.py            # RSS 収集・前処理
      - calendar_management.py       # マーケットカレンダー・営業日ロジック
      - quality.py                   # データ品質チェック
      - stats.py                     # zscore_normalize 等
      - audit.py                     # 監査ログ用スキーマ初期化
    - research/
      - __init__.py
      - factor_research.py           # momentum/volatility/value ファクター
      - feature_exploration.py       # forward returns / IC / rank / summary
    - monitoring/ (存在が想定されるがここでは主要ファイルは抜粋外)
    - strategy/ (戦略関連モジュールが入る想定)
    - execution/ (約定/発注ラッパーが入る想定)

（実際のリポジトリでは他にユーティリティやテスト、CLI スクリプト等が存在する可能性があります）

---

運用上の注意
- 本ライブラリには実際の注文発注・実口座操作を行うための設計要素を含みます（監査ログ、kabu API 用設定など）。ライブ環境で使う際は十分な検証と安全対策（サンドボックス、ポジション制限、テストモード）を行ってください。
- LLM 呼び出しは外部 API のコストとレイテンシ、安定性に依存します。API 失敗時は安全側のフォールバック（スコア 0 等）となる実装方針が取られていますが、運用ポリシーはプロジェクトごとに検討してください。
- ETL / カレンダー更新は定期バッチ（夜間）での実行を想定しています。バックフィル・再取得ロジックにより API 側の訂正を吸収する設計になっています。

---

さらに詳しい利用方法や API 仕様、運用ガイドはプロジェクト内の設計ドキュメント（例: DataPlatform.md, StrategyModel.md 等）や各モジュールの docstring を参照してください。

必要であれば README に実際の .env.example のテンプレートや、よくあるトラブルシュート（OpenAI のレスポンスパース失敗、J-Quants トークン期限切れ等）を追記します。どの項目を優先して追加しますか?