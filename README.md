# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL による市場データ取得、ニュースの NLP スコアリング、ファクター計算、監査ログ、マーケットカレンダー管理、発注履歴の監査スキーマなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得・保存（冪等）
  - DuckDB を用いたローカルデータ保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集・NLP
  - RSS フィード取得（SSRF 対策・サイズ制限・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコアリング（ai_scores）
  - マクロニュースを用いた市場レジーム判定（bull / neutral / bear）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - クロスセクションの Z スコア正規化

- 運用・監査
  - 発注・約定の監査スキーマ（冪等キー・ステータス管理）
  - 市場カレンダー管理（営業日判定、前後営業日探索）
  - 監査ログ専用 DuckDB 初期化ユーティリティ

- その他
  - 環境変数 / .env 自動読み込み（プロジェクトルート探索）
  - フェイルセーフな外部 API 呼び出し（リトライ、バックオフ等）

---

## 前提（依存）

主な依存ライブラリ（この README 作成時点の実装参照）:

- Python 3.9+
- duckdb
- openai (OpenAI SDK)
- defusedxml

その他、標準ライブラリ（urllib 等）を使用します。実際の環境では pyproject.toml / requirements.txt を参照してインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン（プロジェクトは src レイアウト前提）:

   git clone <repository-url>
   cd <repository>

2. 仮想環境を作成・有効化（推奨）:

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存のインストール:

   pip install -U pip
   # ここでは最低限のパッケージ例
   pip install duckdb openai defusedxml

   （パッケージ配布／プロジェクト側で pyproject.toml がある場合は）
   pip install -e .

4. 環境変数の設定（.env をプロジェクトルートに置くと自動読み込みされます）
   - 必須（主に本システムがフル機能を動かすために必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
     - KABU_API_PASSWORD — kabuステーション API パスワード（取引機能利用時）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト `INFO`
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化（テスト等）
     - OPENAI_API_KEY — OpenAI を使う処理（ニュース NLP / レジーム判定）で必須（関数呼び出し時に api_key 引数で注入可能）
     - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   ```

   注意: パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml を探す）から .env を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。

---

## 使い方（簡単なコード例）

※ 以降の例は Python REPL / スクリプト内で実行します。事前に依存と環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）が設定されていることを確認してください。

- DuckDB 接続の作成（settings からパスを取得）:

  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  # target_date を None にすると今日を基準に処理
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP（銘柄別センチメント）を実行する:

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OPENAI_API_KEY を環境変数にセットしているか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written} codes")

- 市場レジーム判定を実行する:

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB を初期化する（監査専用 DB を作る）:

  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit は監査スキーマが作成済みの DuckDB 接続

- RSS フィードを取得する（ニュース収集の一部）:

  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["title"], a["datetime"])

- 市場カレンダーのユーティリティを利用する:

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import datetime
  d = datetime.date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))

---

## 注意事項 / 運用メモ

- Look-ahead バイアス防止:
  - ai モジュールや ETL は内部で date.today() をむやみに参照せず、明示的な日付（target_date）を受け取る設計になっています。バックテスト等での使い方に注意してください。

- OpenAI / J-Quants の API 呼び出し:
  - リトライやバックオフ、API エラー時のフェイルセーフ（0.0 スコア等）の実装がありますが、API キーやレート制限、課金に関しては利用者側で責任を持って管理してください。

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）から .env / .env.local を自動読み込みします。
  - テストやカスタム環境がある場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下に実装されています。主要ファイル・モジュールは次の通りです。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動読み込み、settings オブジェクト
  - ai/
    - __init__.py (score_news 等を公開)
    - news_nlp.py
      - ニュースの LLM ベースセンチメント集約と ai_scores 書き込み
    - regime_detector.py
      - マクロニュース + ETF MA200 乖離による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、fetch / save の実装（rate limiting, retry, id token refresh）
    - pipeline.py
      - ETL のメイン処理（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
      - ETLResult データクラス
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 収集・前処理・SSRF 対策
    - calendar_management.py
      - market_calendar の更新と営業日判定ユーティリティ
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - stats.py
      - zscore_normalize などの統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）の DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - Momentum, Volatility, Value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数

---

## 追加情報 / 開発者向け

- テスト時の差し替え:
  - OpenAI などの外部呼び出しは内部でラップされており、ユニットテストではモック（patch）しやすい設計になっています（例: kabusys.ai.news_nlp._call_openai_api の差し替えなど）。

- トランザクション管理:
  - 重要な DB 更新は BEGIN / COMMIT / ROLLBACK を使って冪等性と回復性を確保しています。DuckDB の executemany の制約（空リスト不可）等に注意してコードが書かれています。

---

この README はコードベースの主要な利用ガイドをまとめたものです。詳細な API やパラメータは各モジュールの docstring を参照してください。必要があれば README の補足（デプロイ例、Dockerfile、CI 設定など）も作成できます。