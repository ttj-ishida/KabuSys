# KabuSys

日本株向けのデータプラットフォームと自動売買（バックエンド）コンポーネント群です。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、市場レジーム判定、リサーチ（ファクター計算）および監査ログ（発注／約定追跡）などの機能を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数一覧（必須／任意）
- ディレクトリ構成
- 注意事項 / 設計方針

---

## プロジェクト概要
KabuSys は日本株向けのデータ基盤とアルゴリズム開発支援ライブラリです。主に以下を目的とします。

- J-Quants API を介した日次 ETL（株価 / 財務 / カレンダー）の差分取得と保存（DuckDB）
- RSS ベースのニュース収集と前処理、記事と銘柄の紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント算出（銘柄別 / マクロ）
- ETF（1321）200日移動平均乖離とマクロセンチメントを合成した市場レジーム判定
- 研究用ファクターの計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ
- データ品質チェックと監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上、ルックアヘッドバイアス回避や API 呼び出しの堅牢化（リトライ・レート制御）に配慮しています。

---

## 主な機能（抜粋）
- ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- ニュース収集: fetch_rss、news_collector の前処理・保存処理（kabusys.data.news_collector）
- ニュース NLP: score_news（銘柄別 ai_scores 作成、OpenAI JSON Mode を使用）
- 市場レジーム判定: score_regime（ETF 1321 の MA 乖離 + マクロセンチメント）
- 研究（research）: calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- データ品質チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency（kabusys.data.quality）
- 監査ログ初期化: init_audit_db / init_audit_schema（冪等な DDL を実行）
- J-Quants クライアント: get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_*（kabusys.data.jquants_client）

---

## セットアップ手順

前提:
- Python 3.10+（型注釈や Union 型の表記に依存）
- システムで pip が利用可能

1. リポジトリをチェックアウト
   - 例: git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - ※ requirements.txt がない場合は少なくとも以下をインストールしてください:
     - duckdb
     - openai
     - defusedxml

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（モジュール kabusys.config がプロジェクトルートを探索して読み込み）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な環境変数は次節を参照してください。

---

## 環境変数（主要）
必須（稼働する機能により必要なものが変わります）:

- JQUANTS_REFRESH_TOKEN  
  - J-Quants のリフレッシュトークン（ETL 実行に必須）
- KABU_API_PASSWORD  
  - kabuステーション API を使う場合に必要
- SLACK_BOT_TOKEN  
  - Slack 通知を使う場合
- SLACK_CHANNEL_ID  
  - Slack 通知先チャンネル ID
- OPENAI_API_KEY  
  - news_nlp / regime_detector で OpenAI を呼ぶ場合に必要

任意／システム設定:

- DUCKDB_PATH  (デフォルト: data/kabusys.duckdb)  
- SQLITE_PATH  (デフォルト: data/monitoring.db)  
- KABUSYS_ENV (development | paper_trading | live) — default: development  
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（簡易サンプル）

以下は最小限の Python 例です。実際はログ設定・例外処理などを適宜追加してください。

- DuckDB に接続して日次 ETL を実行（J-Quants トークンが環境にある前提）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（ai スコア付け）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"scored {n_written} codes")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査関連テーブルが作成されます
```

- RSS フェッチ（ニュース収集単体テスト）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["title"], a["datetime"], a["url"])
```

注意:
- score_news / score_regime は OpenAI API を呼び出すため、api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl 等の ETL は J-Quants のトークンを必要とします（JQUANTS_REFRESH_TOKEN）。
- ライブラリはルックアヘッドバイアス回避のため、内部で date.today() や datetime.now() を不用意に利用しない方針で書かれています（多くの関数は target_date を明示的に受け取ります）。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env の自動ロードと Settings
  - ai/
    - __init__.py
    - news_nlp.py       — 銘柄別ニュースセンチメント算出
    - regime_detector.py — ETF MA + マクロで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアントと DuckDB 保存ヘルパー
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETL インターフェース再エクスポート
    - news_collector.py  — RSS 収集と前処理
    - calendar_management.py — JPX カレンダー管理（営業日判定等）
    - quality.py         — データ品質チェック
    - stats.py           — z-score 等の統計ユーティリティ
    - audit.py           — 監査ログ（DDL/初期化）
  - research/
    - __init__.py
    - factor_research.py        — mom/value/volatility 等の計算
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー
  - ai/, data/, research/ はそれぞれ公開 API を __all__ で定義しています

---

## 注意事項 / 設計方針（抜粋）
- ルックアヘッドバイアス対策: 多くの処理は target_date を外部から与える設計で、現在日時を内部的に参照しないようにしてあります（バックテスト対応）。
- API 呼び出し: レート制御、リトライ（指数バックオフ）、HTTP ステータス別挙動（401 はトークン再取得）などに対応。
- 冪等性: J-Quants の保存関数は ON CONFLICT DO UPDATE を用いて既存データを上書きし、ETL の冪等性を確保しています。
- セキュリティ: news_collector は SSRF / XML Bomb 対策（スキーム検証、プライベート IP 検査、defusedxml、レスポンスサイズ制限）を行っています。
- テスト性: OpenAI 呼び出し箇所や HTTP 層は置き換えやモックがしやすいように設計されています。自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能です。

---

## よくある質問
Q: OpenAI の呼び出しで失敗したらどうなる？  
A: 多くのケース（429/タイムアウト/ネットワーク断/5xx）はリトライし、最終的にフェイルセーフ値（例: macro_sentiment = 0.0）で継続する設計です。致命的なエラーはログに残しますが、処理全体を停止しない場合が多いです。

Q: DuckDB のスキーマはどこにある？  
A: ETL 実行や監査初期化関数（init_audit_schema / init_audit_db）が必要なテーブルを作成します。プロジェクトの別途 schema 初期化モジュールを用意している場合はそちらを実行してください。

---

README に書かれている以外の詳細な使用方法や運用手順（CI/CD、運用監視、Slack 通知フロー、戦略・発注の実装など）は別途ドキュメント（運用手順書 / StrategyModel.md / DataPlatform.md）を参照してください。

ご希望があれば、README に以下を追加できます：
- 詳しい環境変数の .env.example（テンプレート）
- よく使う CLI スクリプトの例
- より詳しいディレクトリツリー（全ファイル一覧）
- 典型的な運用フロー（夜間 ETL → 研究 → シグナル生成 → 発注）