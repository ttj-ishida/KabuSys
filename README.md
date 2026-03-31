# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL、ニュースNLP、リサーチ用ファクター計算、監査ログスキーマ、J-Quants / RSS 連携などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買およびリサーチ基盤向けに設計されたモジュール群です。主な用途は次のとおりです。

- J-Quants API を用いたデータ取得（株価・財務・市場カレンダー）
- DuckDB を用いたデータ蓄積と品質チェック（ETL）
- RSS ニュース収集と LLM を用いたニュースセンチメント算出（OpenAI）
- 市場レジーム判定（ETF + マクロニュースの合成）
- 研究（ファクター計算・特徴量探索）ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ定義

設計上の重要ポイント：
- ルックアヘッドバイアス対策（内部で date.today()/datetime.now() に依存しない、または明示的に target_date を受け取る）
- 冪等性（DB 保存は ON CONFLICT / upsert を使用）
- API リトライ／レート制御／フェイルセーフ（失敗時は安全なデフォルトで継続）
- SSRF 対策・サイズ制限などの堅牢なネットワーク処理

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・トークン自動リフレッシュ・レート制御）
  - pipeline: 日次 ETL のエントリポイント（run_daily_etl 等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 収集（SSRF 対策・正規化・raw_news 保存）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログ用テーブル定義と初期化ユーティリティ
  - stats: z-score 正規化等の統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースをまとめて OpenAI でスコアリング → ai_scores へ保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースを組み合わせて市場レジームを判定
- research/: ファクター計算・特徴量探索（mom, value, volatility, forward returns, IC 等）
- config: 環境変数読み込みと Settings（.env 自動読み込み機能あり）

---

## 必要条件

- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク経由の API を使用するため適切な API キー（J-Quants、OpenAI）等を用意してください。

（プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを参照してください）

---

## インストール（開発環境）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（例）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# ローカル編集しながら使う場合
pip install -e .
```

---

## 環境変数 / .env

パッケージ起動時にルート（.git または pyproject.toml を基準）で `.env` / `.env.local` を自動読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（Settings から参照される）：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring) のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development|paper_trading|live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で指定しない場合に参照）

.env の簡易例:

```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（DB / 監査スキーマ初期化例）

DuckDB ファイルを用意して、監査ログスキーマを初期化する例:

```python
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# ファイルパスは settings.duckdb_path で指定された値（Path オブジェクト）
conn = init_audit_db(settings.duckdb_path)
# もしくはメモリDB:
# conn = init_audit_db(":memory:")
```

監査スキーマのみを既存接続へ追加する場合:

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 使い方：主な API と実行例

以下はライブラリの代表的な呼び出し例です。各関数は duckdb の接続オブジェクトを受け取ります。

1) 日次 ETL を実行（run_daily_etl）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースを LLM でスコアリングして ai_scores へ保存

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {n_written}")
```

3) 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) ファクター計算（research）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
recs = calc_momentum(conn, target_date=date(2026, 3, 20))
# recs は各銘柄ごとの dict list
```

5) J-Quants API から直接データ取得（ライブラリ関数）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用
rows = fetch_daily_quotes(id_token=id_token, date_from=date(2026,3,1), date_to=date(2026,3,20))
```

---

## よく使うユーティリティと注意点

- settings: kabusys.config.settings により環境変数をプロパティとして取得できます（必須キーは未設定時に ValueError を送出）。
- DuckDB への保存は基本的に冪等（ON CONFLICT）です。ETL は差分取得を行う設計。
- LLM 呼び出し（OpenAI）はリトライ/フェイルセーフを実装していますが、API キーと利用料に注意してください。
- news_collector.fetch_rss は SSRF 対策・サイズ制限・XML パースの安全策を実装しています。
- date の扱い：多くの関数は target_date を明示的に受け取り、内部で現在時刻を参照しないよう配慮されています（バックテストのルックアヘッド防止）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py
  - etl.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
  - (その他リサーチユーティリティ)
- monitoring/ (パッケージ名は __all__ に含まれるが実装に応じて存在)
- strategy/, execution/ 等（戦略・約定モジュールはパッケージレベルで公開予定）

（上記は主要ファイルを抜粋しています。詳細はソースツリーを参照してください。）

---

## 設計上の注意・ベストプラクティス

- テスト環境で自動 .env 読み込みが邪魔な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- DuckDB の executemany に空リストを渡すとバージョン依存の挙動となるため、ライブラリ側で空チェックが行われています。アプリ側でも空データを書き込まないようにしてください。
- OpenAI 呼び出しは JSON mode を使用し、レスポンスの厳密なバリデーションを行っています。スコアのクリッピングやリトライ方針に注意してください。
- J-Quants API はレート制限があるため、jquants_client の RateLimiter に依存する処理を単体で短時間に大量実行しないでください。

---

必要であれば、README にサンプル .env.example、より詳しい使用例（ETL スケジューリング、Slack 通知連携、strategy → execution の統合フロー）を追加します。どの部分を詳細化したいか教えてください。