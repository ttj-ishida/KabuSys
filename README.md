# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集とLLMによるニュース/マクロ評価、リサーチ用ファクター計算、監査ログ（発注→約定トレース）等を提供します。

主な設計方針は「ルックアヘッドバイアスを避ける」「DuckDB を用いた冪等な永続化」「外部API呼び出しはリトライ & レート制御」「テストしやすい分離」です。

---

## 主要機能一覧

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPXマーケットカレンダーを差分取得・保存（kabusys.data.jquants_client, kabusys.data.pipeline）
  - ETL の集約エントリポイント: run_daily_etl（戻り値: ETLResult）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）: kabusys.data.quality

- ニュース・NLP
  - RSS からのニュース収集と前処理: kabusys.data.news_collector.fetch_rss
  - ニュースを銘柄ごとに統合し LLM（OpenAI）でセンチメント評価: kabusys.ai.news_nlp.score_news
  - マクロニュース + ETF（1321）200日MA乖離を組み合わせて市場レジーム判定: kabusys.ai.regime_detector.score_regime

- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算: kabusys.research.factor_research（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー等: kabusys.research.feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
  - Z-score 正規化ユーティリティ: kabusys.data.stats.zscore_normalize

- 監査（Audit / Tracing）
  - シグナル→発注→約定が追跡可能な監査テーブルを DuckDB に初期化: kabusys.data.audit.init_audit_db / init_audit_schema

- 環境・設定管理
  - .env（.env.local 優先）自動ロード・保護機能（kabusys.config.settings）

---

## 必要条件

- Python 3.10 以降（typing の新構文を使用）
- 主な外部依存（例）
  - duckdb
  - openai
  - defusedxml
  - （その他：標準ライブラリ以外のパッケージは setup.py / pyproject.toml 参照）

実行環境に応じて追加ツール（例: ネットワークアクセス、OpenAI API キー、J-Quants リフレッシュトークン）が必要です。

---

## セットアップ手順（開発用）

1. リポジトリをクローン
   - git clone <このリポジトリ>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .         # パッケージ開発インストール
   - もしくは requirements.txt / pyproject.toml に従ってインストール

4. 環境変数の準備
   - リポジトリルートに `.env` または `.env.local` を配置すると自動ロードされます（kabusys.config がプロジェクトルートを検出して読み込みます）。
   - 自動ロードを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等）。

---

## 必須／推奨環境変数

kabusys.config.Settings が参照する主なキー:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN — （必須）J-Quants リフレッシュトークン

- kabuステーション API
  - KABU_API_PASSWORD — （必須）kabu API パスワード
  - KABU_API_BASE_URL — （任意、デフォルト: http://localhost:18080/kabusapi）

- OpenAI / LLM
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 呼び出し時に渡すことも可能）

- Slack（通知等）
  - SLACK_BOT_TOKEN — （必須）Slack ボットトークン
  - SLACK_CHANNEL_ID — （必須）通知先チャンネルID

- DB / モニタリング
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite モニタリング DB（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定

- その他
  - KABUSYS_ENV — 環境 (development / paper_trading / live)
  - LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

.env 例（抜粋）
```
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易例）

以下はパッケージ内 API を直接呼び出す例です。DuckDB 接続には duckdb.connect を使用します。

- DuckDB 接続の作成例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定することでルックアヘッドバイアスを避けられます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーの用意が必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で渡すか OPENAI_API_KEY 環境変数を設定
count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"scored {count} symbols")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査DB初期化（order/exec 用）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC TimeZone が設定されます
```

- 研究モジュールの利用例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
from datetime import date

d = date(2026,3,20)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
# 例: calc_ic を使って mom_1m と fwd_1d の IC を計算
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
```

- ニュース RSS 取得（news_collector）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 自動 .env ロードの挙動

- プロジェクトルートはこのモジュールの位置から親ディレクトリを辿り `.git` または `pyproject.toml` を見つけて決定します。これにより CWD に依存せず自動的に `.env` / `.env.local` を読み込みます。
- 読み込み順序: OS 環境 > .env.local > .env
- 自動ロードを無効化する環境変数:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                         -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      -- ニュースセンチメント（LLM）処理
    - regime_detector.py               -- 市場レジーム判定（ETF + マクロLLM合成）
  - data/
    - __init__.py
    - jquants_client.py                -- J-Quants API クライアント & 保存
    - pipeline.py                      -- ETL パイプライン（run_daily_etl 等）
    - etl.py                           -- ETLResult 再公開
    - news_collector.py                -- RSS 収集・前処理・保存
    - quality.py                       -- データ品質チェック
    - stats.py                         -- zscore_normalize 等
    - calendar_management.py           -- 市場カレンダー管理（is_trading_day 等）
    - audit.py                         -- 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py               -- Momentum / Value / Volatility 計算
    - feature_exploration.py           -- forward returns, IC, summary
  - ai/ (上記)
  - research/ (上記)
  - monitoring/, strategy/, execution/ (パッケージ公開用の __all__ に記載あり。実装はこのコードベース内にあるモジュールに依存)

（注）README の一覧は主要機能に焦点を当てています。実際のリポジトリにはさらに補助モジュール・ユーティリティが含まれます。

---

## テスト / 開発上の注意

- LLM（OpenAI）呼び出しはテストでモックすることを想定して設計されています（内部の _call_openai_api を patch する等）。
- J-Quants API 呼び出しは rate limiter とリトライを備えていますが、本番トークンの取り扱いは慎重に行ってください。
- DuckDB に対する executemany の空リストバインド等、DuckDB バージョンごとの挙動に注意した実装上の配慮があります。

---

## 貢献 / ライセンス

- 貢献はプルリクエストを歓迎します。変更はユニットテストと静的解析（型チェック）とともに提出してください。  
- ライセンスはリポジトリ内 LICENSE を参照してください（ここでは明示していません）。

---

この README はコードベースの主なモジュールと利用方法のサマリを示しています。詳細は各モジュールの docstring（ソース内コメント）をご参照ください。必要であればサンプルデータや docker-compose 等の具体的な起動例も追加できます。要望があれば教えてください。