# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
J-Quants / kabuステーション / RSS / OpenAI（LLM）などを組み合わせて、データ取得 (ETL)、品質チェック、ニュース NLP、マーケットレジーム判定、監査ログ管理、リサーチ用ファクター計算などを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つ内部ライブラリです。

- J-Quants API からの株価・財務・カレンダー取得（差分取得・ページネーション対応・リトライ・レート制御）
- DuckDB を用いた ETL パイプラインとデータ品質チェック
- RSS ニュース収集と記事前処理・銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロセンチメント評価
- マーケットレジーム（bull / neutral / bear）判定
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ初期化ユーティリティ
- 研究（research）モジュール：ファクター計算・特徴量探索ユーティリティ

設計方針の一例：
- ルックアヘッドバイアスを防ぐため、内部処理で date.today()/datetime.today() を無暗に参照しない
- API 呼び出しは堅牢に（リトライ、バックオフ、フェイルセーフ）
- DuckDB を中心にシンプルな SQL + Python 実装

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得 + DuckDB 保存機能）
  - pipeline: 日次 ETL 実行（run_daily_etl）と ETL 結果（ETLResult）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定
  - news_collector: RSS 収集・前処理・保存用ユーティリティ
  - audit: 監査ログ（signal / order_request / executions）スキーマ初期化
  - stats: z-score 正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュース（LLM）を合成して日次レジーム判定・保存
- research/
  - factor_research: momentum / value / volatility 等のファクター算出
  - feature_exploration: 将来リターン計算、IC（ランク相関）、統計サマリー

---

## セットアップ手順

前提
- Python 3.9+（コードは型ヒントに Union | を使っているため 3.10 以上が望ましい）
- DuckDB（Python パッケージとして pip でインストールします）
- OpenAI Python SDK（gpt-4o-mini を使うため）
- defusedxml（RSS パースの安全化）

推奨セットアップ（例）
1. リポジトリをクローン（省略）
2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール（プロジェクトに requirements.txt がある場合はそちらを使ってください）。最低限の依存例:
   ```
   pip install duckdb openai defusedxml
   ```
   その他テストや CI に応じて logging 等が使われます。

4. パッケージを開発モードでインストール（src レイアウトを想定）
   ```
   pip install -e .
   ```

5. 環境変数 (.env) を用意
   - 設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動読み込み）。  
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（config.py に基づく）
- JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>  （必須）
- OPENAI_API_KEY = <OpenAI API key> （news_nlp / regime_detector 実行に必要）
- KABU_API_PASSWORD
- KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用・任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB 用）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU/MEMORY/DISK 閾値
- KABUSYS_ENV = development | paper_trading | live
- LOG_LEVEL = DEBUG|INFO|...

サンプル `.env`（例）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（例）

以下は主要ユースケースの最小実行例です。適宜エラーハンドリング・ログ設定を追加してください。

1) DuckDB 接続作成（監査 DB の初期化）
```python
import duckdb
from kabusys.data.audit import init_audit_db

# ファイル DB を初期化して接続を取得（ディレクトリは自動作成されます）
conn = init_audit_db("data/audit.duckdb")
```

2) メインデータベース接続（ETL 用）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

3) 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 対象日を指定（省略すると今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

4) ニュースセンチメントのスコア付け（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {n_written}")
```

5) 市場レジーム判定（AI + MA200 合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

6) RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

source = "yahoo_finance"
url = DEFAULT_RSS_SOURCES[source]
articles = fetch_rss(url, source)
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

7) 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

注意:
- OpenAI 呼び出しはネットワーク・料金がかかるため、テスト時は該当関数をモックすることを推奨します（コード内でもテスト用に差し替え可能な構造にしてあります）。
- ETL / データ保存は DuckDB のスキーマが前提です。スキーマ初期化手順（DDL）は別モジュールやドキュメントを参照してください（audit モジュールは監査テーブルを初期化します）。

---

## よく使うユーティリティ

- kabusys.config.settings
  - 環境変数から設定を取得するシングルトン。必須変数未設定時は例外を投げます。

- kabusys.data.jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()

- kabusys.data.pipeline.run_daily_etl(...)
  - 日次の ETL（カレンダー→株価→財務→品質チェック）を順に実行し ETLResult を返す

- kabusys.ai.news_nlp.score_news(...)
  - 銘柄ごとのニュースセンチメントを計算し ai_scores テーブルに保存

- kabusys.ai.regime_detector.score_regime(...)
  - マクロセンチメント＋ETF MA200 を合成して market_regime に保存

---

## ディレクトリ構成

概略（主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - quality.py
      - news_collector.py
      - calendar_management.py
      - audit.py
      - stats.py
      - (その他データ関連モジュール)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (README 要求で示唆されているがコード抜粋には含まれない場合あり)
    - strategy/, execution/ (パッケージの __all__ に列挙されている。実装はプロジェクト内に存在)

各モジュールは docstring に設計意図・処理フロー・フェイルセーフの仕様が記載されており、テストしやすいように外部副作用を分離する設計になっています。

---

## 注意事項 / 運用上のヒント

- API キー・トークン類は `.env` に保存せず、環境変数やシークレットマネージャを使うのが安全です。開発時はローカル `.env` を用いても構いません。
- OpenAI のコストとレート制限に注意してください。news_nlp / regime_detector はバッチ処理向けに設計されていますが、実行頻度・バッチサイズに気を付けてください。
- J-Quants API にはレート制限があるため、jquants_client は内部でレートリミッタとリトライを実装していますが、複数プロセスから同時に大量に叩くと制限に達します。
- DuckDB の executemany は空リストを受け付けないバージョン互換性考慮がコード中にあります。ETL の結果が空の場合の分岐処理に注意してください。

---

この README はコードベースに含まれる docstring と実装を要約したものです。より詳しい API リファレンスや実行スクリプト（CLI / cron ジョブ等）はリポジトリ内の別ドキュメントを参照してください。必要であれば README にサンプル .env.example や schema 初期化手順を追記します。