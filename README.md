# KabuSys

日本株向け自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants からのデータ取り込み（ETL）、ニュース収集・NLP スコアリング、マーケットカレンダー管理、ファクター計算、監査ログ（発注→約定トレーサビリティ）などを一貫して提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を参照しない等）
- DuckDB を中心としたローカルデータレイヤ
- API 呼び出しはリトライ／バックオフ・レート制御を備えた安全な実装
- DB 書き込みは可能な限り冪等（ON CONFLICT / DELETE→INSERT 等）
- 外部 API キーは環境変数で管理（.env 自動ロード機能あり）

---

## 機能一覧

- データ ETL（J-Quants API からの日次株価・財務・カレンダー取得）
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付整合性）
- 市場カレンダー管理（営業日判定 / 前後営業日取得 / バッチ更新）
- ニュース収集（RSS → raw_news、SSRF/サイズ対策、トラッキングパラメータ除去）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア → ai_scores）
- レジーム判定（ETF 1321 の MA とマクロニュースから市場レジームを算出）
- 研究用モジュール（ファクター計算: モメンタム／バリュー／ボラティリティ、forward returns、IC、サマリー）
- 統計ユーティリティ（Zスコア正規化など）
- 監査ログ（signal_events / order_requests / executions の監査スキーマ初期化）
- J-Quants クライアント（rate limiting / retry / token refresh 対応）
- 設定管理（.env 自動読み込み、必須 env チェック、環境判定）

---

## 必要条件

- Python 3.10 以降（型記法に `|` を使用）
- 推奨パッケージ（概略）
  - duckdb
  - openai
  - defusedxml

（実行環境に応じて追加で sqlite3 等が必要になる場合があります）

例（仮の最小インストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

プロジェクトが pip installable な場合は `pip install -e .` を使ってインストールしてください。

---

## 環境変数（主なもの）

このライブラリは環境変数（または .env / .env.local）から設定を読み込みます。プロジェクトルートに `.git` または `pyproject.toml` があると自動で `.env` / `.env.local` を読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（get_id_token に必要）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（発注周り）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI 呼び出しに使用（ai モジュールで省略時参照）

任意 / デフォルトあり:
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

サンプル `.env`（必須項目のみ例）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル実行例）

1. リポジトリをクローン／チェックアウト
2. 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成（`.env.example` を参照）
5. DuckDB ファイル格納用ディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```
6. 必要なら監査 DB を初期化（Python スニペット参照）

---

## 使い方（Python API の例）

以下は主要な機能の簡単な呼び出し例です。実運用では適切なログ設定や例外処理を行ってください。

- DuckDB 接続を作る（settings を利用）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースの NLP スコアを生成（OpenAI API キーは環境変数か引数で指定）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print("written:", written)
```

- 市場レジームをスコアリング:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB（監査テーブル）を初期化:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

- RSS を取得（ニュース収集テスト）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["datetime"], a["title"])
```

- J-Quants データ取得（直接呼ぶ場合）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用して ID トークン取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))
```

---

## 注意点・設計に関するメモ

- Look-ahead Bias の回避を重視：データ取得・AI スコアリング・判定はいずれも「対象日以前の情報のみ」を前提に設計されています。
- 冪等性：DB への保存は ON CONFLICT / DELETE→INSERT などにより重複を避けます。
- 外部 API 呼び出し：レート制御・リトライ（指数バックオフ）・401 の自動トークン更新等を実装しています。OpenAI 呼び出しはモデルとレスポンス検証を行います。
- テスト時のヒント：自動で .env を読み込む機能は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。OpenAI 呼び出しやネットワークはモック化してテストしてください（ソースコードはテスト用に差し替えやすい実装になっています）。

---

## ディレクトリ構成（主なファイル・モジュール）

以下は src/kabusys 以下の主要モジュールと役割の抜粋です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py  — MA とマクロニュースを合成して market_regime を更新
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー判定・更新ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - jquants_client.py      — J-Quants API クライアント（取得/保存関数）
    - news_collector.py      — RSS 取得・前処理・raw_news 保存補助
    - quality.py             — データ品質チェック群（欠損・スパイク等）
    - stats.py               — zscore_normalize 等統計ユーティリティ
    - audit.py               — 監査ログスキーマ作成・初期化
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Value/Volatility 等ファクター計算
    - feature_exploration.py— forward_returns / calc_ic / factor_summary / rank

---

## 開発 / 貢献

- テストを書く際は外部 API 呼び出し（OpenAI / J-Quants）をモックしてください。
- .env の自動ロードはプロジェクトルート探索に依存します（__file__ ベース）。テスト環境で挙動を変えたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使ってください。

---

必要であれば README にサンプル .env.example、CI / テストの実行例、より詳しい API リファレンス（関数引数の説明や戻り値の例）を追加します。どの情報を追記しますか？