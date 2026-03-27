# KabuSys

日本株向けの自動売買 / データプラットフォーム基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集、LLM を用いたニュースセンチメント評価、ファクター算出、監査ログ（発注/約定トレーサビリティ）などを含んだモジュール群を提供します。

---

目次
- プロジェクト概要
- 主な機能
- 必要条件・依存関係
- セットアップ手順
- 環境変数（.env）/ 設定
- 使い方（簡易サンプル）
- よく使う API の説明
- ディレクトリ構成

---

プロジェクト概要
- 名前: KabuSys
- 目的: 日本株のデータプラットフォームと自動売買基盤を構築するための共通ライブラリ群
- 主な設計方針:
  - Look-ahead bias を避ける（内部で datetime.today() 等を直接参照しない設計）
  - DuckDB をローカル DB として利用し、ETL は冪等・差分更新を行う
  - 外部 API 呼び出しはリトライやレートリミット制御を備える
  - LLM（OpenAI）をニュースのセンチメント評価や市場レジーム判定に利用
  - 監査ログ（signal → order_request → execution のチェーン）を保持しトレーサビリティを確保

---

主な機能一覧
- データ取得 / ETL
  - J-Quants API 経由で株価日足、財務データ、JPX カレンダーを差分で取得・保存（kabusys.data.pipeline）
  - 品質チェック（欠損・スパイク・重複・日付不整合）機能（kabusys.data.quality）
- ニュース収集
  - RSS フィードの安全な取得（SSRF対策・gzip/サイズ制限・トラッキング除去）と raw_news への保存（kabusys.data.news_collector）
- AI（LLM）連携
  - ニュースを銘柄単位で集約して OpenAI（gpt-4o-mini 等）でセンチメント評価（kabusys.ai.news_nlp.score_news）
  - ETF（1321）MA200乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- リサーチ / ファクター算出
  - Momentum / Volatility / Value 等のファクター計算（kabusys.research）
  - 将来リターンや IC（Information Coefficient）計算、統計サマリ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル群を DuckDB に作成・初期化（kabusys.data.audit）
- ユーティリティ
  - 環境変数自動読み込み・管理（kabusys.config）
  - 汎用統計ユーティリティ（Zスコア正規化等）

---

必要条件 / 依存関係
- Python 3.10+
- 主な依存パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml
- そのほか標準ライブラリ・typing 等

（実プロジェクトでは requirements.txt / pyproject.toml で依存を管理してください）

---

セットアップ手順（ローカル開発向けの最短手順）
1. Python 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml がある場合は pip install -e . を推奨）

3. 環境変数の準備
   - プロジェクトルートに .env を作成するか OS 環境変数を設定します。
   - 以下の必須環境変数が利用されます（詳細は次項参照）。

4. データディレクトリを作成（必要に応じて）
   - mkdir -p data

---

環境変数 / 設定（kabusys.config.Settings）
- 自動読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env を自動的に読み込みます。
  - 自動ロードを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途など）。

- 主な環境変数（必須・任意）
  - 必須:
    - JQUANTS_REFRESH_TOKEN : J-Quants API 用のリフレッシュトークン
    - KABU_API_PASSWORD      : kabuステーション API のパスワード
    - SLACK_BOT_TOKEN       : Slack 通知用 Bot Token
    - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
    - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
  - 任意 / デフォルトあり:
    - KABUSYS_ENV           : 実行環境 ("development", "paper_trading", "live")。デフォルト "development"
    - LOG_LEVEL             : ログレベル ("INFO" 等)。デフォルト "INFO"
    - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH           : SQLite（モニタリング用）パス（デフォルト data/monitoring.db）

- .env 例（.env.example としてプロジェクトに置くことを推奨）
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

---

使い方（サンプルコード）
- DuckDB 接続を作り ETL を走らせる（日次 ETL の例）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントスコア生成（OpenAI API キーを環境変数 OPENAI_API_KEY にセットしてください）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定（ETF 1321 の ma200 とマクロニュース評価）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

# audit 用の別 DB を作る例
conn_audit = init_audit_db("data/audit.duckdb")
```

- ニュース RSS を取得（news_collector.fetch_rss は生の取得。保存ロジックは別実装へ組み込む）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["title"], a["datetime"], a["url"])
```

注意事項
- OpenAI 呼び出しや J-Quants API 呼び出しはそれぞれ API レート制限や料金が発生します。運用時はキーの扱いとコストに注意してください。
- ETL / DB 書き込みは冪等性を保つよう実装されていますが、実行前に必ずバックアップ運用やローカル検証を行ってください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境変数自動読み込みを無効化できます。

---

よく使うモジュールと説明（短評）
- kabusys.config
  - 環境変数の自動読み込み、Settings クラス経由のアクセス
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL のトップレベル API と ETLResult
- kabusys.data.jquants_client
  - J-Quants API との通信、取得＆DuckDB への保存関数（fetch_* / save_*）
- kabusys.data.news_collector
  - RSS の安全な取得と前処理ユーティリティ
- kabusys.ai.news_nlp
  - ニュースを銘柄ごとに集約して LLM でセンチメントを算出し ai_scores へ保存
- kabusys.ai.regime_detector
  - ETF（1321）MA200 とマクロニュースの LLMセンチメントを合成して市場レジーム判定
- kabusys.research
  - ファクター計算（momentum/value/volatility）や統計・IC 計算ユーティリティ
- kabusys.data.audit
  - 監査ログスキーマの初期化関数（init_audit_schema / init_audit_db）

---

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                         # 環境変数管理
    - ai/
      - __init__.py
      - news_nlp.py                     # ニュースセンチメント（LLM）
      - regime_detector.py              # 市場レジーム判定（MA200 + LLM）
    - data/
      - __init__.py
      - jquants_client.py               # J-Quants API クライアント（fetch/save）
      - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py          # 市場カレンダー管理（is_trading_day 等）
      - news_collector.py               # RSS 収集・前処理
      - quality.py                      # データ品質チェック
      - stats.py                        # 汎用統計ユーティリティ（zscore_normalize）
      - etl.py                          # ETL の公開インターフェース（ETLResult 再エクスポート）
      - audit.py                        # 監査ログ初期化（監査スキーマ）
    - research/
      - __init__.py
      - factor_research.py              # ファクター計算（momentum/value/volatility）
      - feature_exploration.py          # 将来リターン / IC / 統計サマリ

---

貢献 / 開発メモ
- コードはモジュール単位でテスト可能なように設計されています（外部 API 呼び出しは差し替え可能）。
- テスト時は外部 API 呼び出しやファイル IO をモックしてください（例: news_collector._urlopen, ai._call_openai_api 等）。
- 大きな処理（ETL・AI呼び出し）はログ出力が充実しているため、運用時はログレベルの管理を行ってください。

---

ライセンス
- 本 README ではライセンス情報を含めていません。実プロジェクトでは LICENSE ファイルを追加してください。

---

質問・補足
- README に追加してほしいサンプル（cron / systemd ジョブ例、Slack 通知サンプル、Docker 化手順など）があれば教えてください。必要に応じて追記します。