# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
データ取得（J-Quants）、ETL、データ品質チェック、ファクター計算、ニュースNLP / LLM を用いた市場レジーム判定、監査ログ（トレーサビリティ）などを含みます。

主な目的は「バッチでのデータパイプライン」「研究用ファクター・特徴量探索」「AI を使ったニュースセンチメント評価」「注文・約定に至る監査ログ管理」を安全に行えることです。設計上、ルックアヘッドバイアス防止・冪等性・フェイルセーフを重視しています。

---

## 主要機能

- 環境設定管理
  - `.env` ファイルまたは環境変数から設定を読み込み（自動読み込み・上書きルールあり）
  - 必須設定値の取得（例: J-Quants トークン、Slack トークン 等）

- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（株価、財務、マーケットカレンダー、上場情報）
  - 差分取得・ページネーション・レートリミット・トークン自動リフレッシュ
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ保存（DuckDB への冪等保存）
  - データ品質チェック（欠損、スパイク、重複、日付整合性）

- ニュース収集・NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - RSS フィード収集（SSRF 対策、サイズ上限、トラッキングパラメタ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント付与（ai_scores テーブル）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200 日移動平均乖離とマクロニュース LLM センチメントを組み合わせて日次レジーム判定（bull/neutral/bear）
  - API 冗長性対策・リトライ・フェイルセーフ（失敗時は中立）

- リサーチ / ファクター（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリー、Z スコア正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution を UUID で連鎖させた監査テーブルの初期化・管理
  - DuckDB に監査専用 DB を作成するユーティリティ

---

## 必要条件

- Python 3.10 以上（型ヒントに `X | None` を使用しているため）
- 主な外部依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がある場合はそちらを優先してください。）

---

## 環境変数（主要）

以下はこのコードベースで参照される主要な環境変数の一覧（必須/任意）です。実運用時は `.env` ファイルをプロジェクトルートに置くことができます（自動読み込み: OS 環境変数 > .env.local > .env）。

必須（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL / jquants_client）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack のチャンネル ID
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注機能を使う場合）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必須（関数引数からも渡せます）

任意:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 `.env` ロードを無効にする（テスト用途）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABU_API_BASE_URL — kabu API ベースURL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用に使われる SQLite パス（data/monitoring.db）

.env の簡易例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=passw0rd
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発用）

1. リポジトリをクローン:
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成・有効化:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（例）:
   ```
   pip install duckdb openai defusedxml
   ```

   実際にはプロジェクトの requirements.txt / pyproject.toml を使ってインストールしてください。

4. `.env` をプロジェクトルートに作成し、上記の必須値を設定。

5. DuckDB 用ディレクトリ作成（必要に応じて）:
   ```
   mkdir -p data
   ```

---

## 使い方（主な例）

以下は Python スクリプトから主要機能を呼び出す例です。実行前に `.env` を正しく設定しておいてください。

- DuckDB 接続の作成（settings からパスを取得）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリング（OpenAI API キーを環境変数にセット）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（1321 の MA200 とマクロニュースを組み合わせる）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

注意点:
- OpenAI 呼び出しはネットワーク/API エラーを考慮し、関数側でフェイルセーフ（スコア 0.0 等）を取る設計ですが、API キーが未設定だと ValueError が発生します。
- ETL は差分取得を行うため、初回実行時は過去データ全件のダウンロードには時間がかかる場合があります。

---

## 設計上の重要なポイント

- ルックアヘッドバイアス防止
  - AI / レジーム判定・ファクター計算などで内部的に date.today() を直接参照しない設計（ターゲット日を引数で渡す）
  - DB クエリでは target_date 未満／排他条件を用いる等の注意を払っています

- 冪等性（idempotency）
  - J-Quants から取得したデータは DuckDB に対して ON CONFLICT（UPDATE）で保存しているため、再実行でデータが重複しません

- フェイルセーフ
  - OpenAI や外部 API の失敗時は例外を投げずに中立値で継続する箇所がある（ログは残す）

- セキュリティ対策（ニュース収集等）
  - RSS フェッチで SSRF 対策、リダイレクト検査、プライベート IP の判定、最大レスポンスサイズの検算、defusedxml による XML パース等を実施

---

## ディレクトリ構成

（主要ファイルのみ抜粋）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ calendar_management.py
│  ├─ pipeline.py
│  ├─ etl.py
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ quality.py
│  ├─ stats.py
│  └─ audit.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
```

各サブパッケージの目的:
- kabusys.config: 環境変数 / 設定管理（自動 .env ロード）
- kabusys.data: データ取得・ETL・品質・カレンダー・ニュース収集・監査ログ
- kabusys.ai: ニュースNLP（銘柄センチメント）・市場レジーム判定
- kabusys.research: ファクター計算・統計分析ユーティリティ

---

## 補足 / トラブルシューティング

- OpenAI を使う関数を呼ぶ際は OPENAI_API_KEY を設定するか、関数の引数で明示的に渡してください。
- 自動 `.env` ロードがテストの邪魔になる場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB に対する executemany の仕様（空リスト不可など）に注意している実装になっています。DB エラーが出る場合はログを確認してください。
- J-Quants API はレート制限と 401 のトークン更新を考慮した実装です。認証トークンの更新や API 応答のログを参照してください。

---

この README はコードベースの概要と利用方法をまとめたものです。実運用やデプロイでは、追加の設定（監視、ジョブスケジューラ、バックテスト用データの事前ロード、発注ロジックの追加など）を検討してください。必要であればサンプルスクリプトや docker-compose、CI 設定などの追加ドキュメントも作成できます。