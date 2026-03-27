# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に使い、J-Quants（株価・財務・カレンダー）、RSS ニュース、OpenAI（LLM）を組み合わせてデータ取得・品質管理・NLP・マーケットレジーム判定・ファクター研究・監査ログを提供します。

---

## 概要

KabuSys は以下のような機能群を持つ Python パッケージです。

- J-Quants API からの差分 ETL（株価、財務、カレンダー）
- ニュース収集（RSS）と LLM による銘柄センチメントスコアリング
- マーケットレジーム判定（ETF + マクロニュース + LLM）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究ツール
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注/約定までの監査ログ（監査テーブル群の初期化・管理）
- 簡易的な設定管理（.env ファイルの自動読み込み）

設計上の留意点：
- ルックアヘッドバイアスを避ける実装（内部で date.today()／datetime.today() を直接参照しない等）
- DuckDB を利用した SQL ベースの高速処理
- OpenAI 呼び出しは堅牢なリトライ/バックオフ処理を組み込み
- 冪等性（ON CONFLICT / idempotent 保存）を重視

---

## 主な機能一覧

- data
  - ETL パイプライン（日次 run_daily_etl、個別ジョブ run_prices_etl 等）
  - J-Quants クライアント（fetch/save 関数、rate limiting、トークン自動更新）
  - 市場カレンダー管理（is_trading_day など）
  - ニュース収集（RSS）と前処理（SSRF 対策、サイズ制限）
  - データ品質チェック（missing, spike, duplicates, date consistency）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: RSS で収集した記事を銘柄ごとにまとめ、OpenAI でセンチメントをスコア化して ai_scores に格納
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュース LLM を組み合わせて market_regime にレジーム判定を書き込み
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・評価（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - .env 自動読み込み（プロジェクトルートの .env/.env.local を優先的にロード）
  - 環境変数から設定を取得する Settings オブジェクト

---

## セットアップ手順

前提：
- Python 3.9+ を想定（typing の一部記法や依存ライブラリに合わせて調整してください）
- システムに DuckDB ネイティブ拡張が必要（pip install duckdb で OK）

1. リポジトリをクローン / 取得
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - 代表的な依存例（プロジェクトに requirements.txt がある場合はそれを使ってください）:
     - pip install duckdb openai defusedxml
   - 追加で必要になる可能性があるパッケージ: requests（本実装は urllib を使用）、その他テスト用ライブラリ等

4. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml の階層）に .env ファイルを置くと、自動的に読み込まれます（.env.local が存在すれば上書き）。
   - 自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
   - 必須の環境変数（主なもの）：
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合に必須）
   - 任意・デフォルトあり:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development|paper_trading|live、デフォルト development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO)

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. データベース初期化（監査ログ等）
   - 監査ログスキーマを初期化する例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_schema

     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```
   - 監査用専用 DB を作る場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（コード例）

以下は主要なユースケースの簡単な利用例です。実行前に必ず .env 等で必要な環境変数を設定してください。

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote scores for {written} codes")
  ```

- マーケットレジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

- 設定の参照（settings）
  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.is_live)
  ```

---

## 注意事項 / 運用メモ

- OpenAI 関連:
  - LLM 呼び出しは gpt-4o-mini（コード内定義）を利用する想定。API レスポンスは JSON モードでパースするため、モデルの挙動変更に注意してください。
  - API エラー時はフェイルセーフ（0.0 でのフォールバック、ログ出力）を行う箇所がありますが、運用上は監視（Slack 等）を入れてください。

- J-Quants クライアント:
  - rate limit（120 req/min）に対応する RateLimiter を実装しています。大量リクエストを送る場合は注意してください。
  - 401 はリフレッシュトークンで自動更新して再試行します。

- ニュース収集:
  - RSS の取得では SSRF・gzip bomb・大容量レスポンスに対する防御（ホワイトリストではなくプライベートアドレス拒否）などの安全対策が組み込まれています。
  - defusedxml を使って XML 攻撃対策済み。

- 環境変数の自動読み込み:
  - パッケージ初期化時にプロジェクトルートを探し、`.env` と `.env.local` を読み込みます。テストや CI で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

---

## ディレクトリ構成（抜粋）

（この README は提供されたソースに基づく抜粋です。実際のリポジトリでは他のファイルや設定がある可能性があります。）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - pipeline.py                  — ETL パイプライン / run_daily_etl 等
    - etl.py                       — ETL 結果型の再エクスポート（ETLResult）
    - calendar_management.py       — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py            — RSS 収集・前処理
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログ（DDL / init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Value / Volatility 等
    - feature_exploration.py       — 将来リターン, IC, summary, rank
  - ai/__init__.py
  - research/__init__.py

---

## 貢献・拡張

- 新しい ETL ソースの追加、LLM プロンプト改善、監査ログ拡張、研究用ファクター追加など歓迎します。
- テストの充実（ユニットテスト、統合テスト）を強く推奨します（特に外部 API 呼び出し部分はモック化してのテストが容易になるよう設計されています）。

---

以上です。必要があれば README にインストール手順（requirements.txt の具体的中身、パッケージ化手順、CI / デプロイ例）や各関数の詳細な API リファレンスを追加します。どのレベルの詳細が必要か教えてください。