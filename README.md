# KabuSys

日本株自動売買プラットフォームのライブラリ群です。データ収集（J-Quants）、データ品質チェック、ニュースのNLPスコアリング、マーケットレジーム判定、ETLパイプライン、監査ログ（オーダー/約定トレーサビリティ）などの機能を提供します。

---

## プロジェクト概要

KabuSys は日本株向けの研究・自動売買プラットフォームを構成する内部ライブラリ群です。主に以下を目的としています。

- J-Quants API を用いた市場データ（株価/財務/カレンダー）の差分取得と DuckDB への保存（ETL）
- ニュース（RSS）収集と前処理、OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / execution）用のスキーマ初期化ユーティリティ
- 研究用ユーティリティ（ファクター計算・将来リターン・IC 計算・統計正規化 等）

主な依存：Python 標準ライブラリ、duckdb、openai、defusedxml（ネットワークや XML 処理のため）など。

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl: 市場カレンダー・株価日足・財務データの差分取得・保存・品質チェック
  - jquants_client: J-Quants API クライアント（認証・レートリミット・リトライ実装）
- データ品質
  - quality.run_all_checks：欠損・重複・スパイク・日付不整合チェック
- ニュース収集 / NLP
  - news_collector.fetch_rss: RSS からの安全な記事取得（SSRF対策・gzip上限など）
  - news_nlp.score_news: OpenAI を使った銘柄別センチメント解析 → ai_scores テーブルに書き込み
- レジーム判定
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成 → market_regime テーブルに書き込み
- 研究用ツール
  - research.calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 監査ログ（オーダー/実行）
  - audit.init_audit_db / init_audit_schema: 監査テーブルとインデックスを生成（DuckDB）

---

## セットアップ手順

以下はローカル開発・実行の最低手順例です。

1. 前提
   - Python 3.10+ 推奨（typing の union 型注釈などを使用）
   - DuckDB を利用（pip からインストールされます）

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。
   例:
   - pip install -r requirements.txt
   または
   - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（少なくとも実行する機能に応じて設定してください）:

     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client 用）
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知を使う場合
     - OPENAI_API_KEY — OpenAI を使う場合（news_nlp / regime_detector）
     - LOG_LEVEL — ログレベル（例: INFO、DEBUG）
     - KABUSYS_ENV — 実行環境: development / paper_trading / live

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データディレクトリ作成（任意）
   - デフォルトでは data/ 以下に DuckDB・SQLite を作成します。必要に応じてパスを作ってください。
   - mkdir -p data

---

## 使い方（簡単な例）

以下はライブラリを使った代表的な操作例です。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date: None なら今日を使います（ETL 実行日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントを計算して ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数で設定していれば api_key=None でOK
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} scores")
```

- 市場レジームを判定して market_regime に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用のデータベース初期化（監査テーブルを作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
# 以降 conn を使って order_requests / signal_events / executions に書き込み可能
```

- 研究用：モメンタムやボラティリティの計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとに mom_1m, mom_3m, mom_6m, ma200_dev を含む dict のリスト
```

注意点:
- OpenAI を使う関数は api_key を引数で渡すか環境変数 OPENAI_API_KEY をセットしてください。
- 時系列処理はルックアヘッドバイアスを避ける実装になっています（target_date を明示的に渡すことを推奨）。

---

## 環境変数（要確認）

主な環境変数（コード内参照）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須 for ETL）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- KABUS_API_PASSWORD — kabuステーション連携用パスワード（発注機能がある場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_ENV — development / paper_trading / live
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値が設定されていれば無効）

config.Settings クラスが環境値を検証します。必須が不足している場合は ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要モジュールと想定される構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 自動読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（銘柄別センチメント）
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py             — J-Quants API クライアント（取得/保存）
    - news_collector.py             — RSS 収集（SSRF 対策・正規化）
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ / init
    - etl.py                        — ETL のインターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン/IC/summary/rank
  - ai/、data/、research/ 以下に追加のユーティリティやモジュールあり

その他:
- pyproject.toml / setup.cfg / requirements.txt 等（プロジェクトルートに存在する想定）

---

## 開発上の注意事項

- ルックアヘッドバイアス回避: 多くの処理は date 引数を受け取り、datetime.today()/date.today() を直接参照しない設計です。バックテストや再現性のある処理では target_date を明示的に与えてください。
- 自動 .env 読み込み: config._find_project_root() により .git や pyproject.toml を探索して .env を自動読み込みします。CI/テストで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出し: news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持っています（テスト容易性のため）。テストではユニットテストで該当関数をモックしてください。
- DuckDB に対する executemany の空リスト渡しに注意（コード内でガード済み）。
- ニュース収集は RSS の最大受信バイト数や gzip 解凍後の大きさチェック等、安全対策を行っています。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンス情報や貢献ルールを記載してください。例: MIT License など）

---

もし README に追加したい具体的な実行例（cron ジョブ設定、Dockerfile、CI ワークフロー例）や、requirements の正確なリスト・pyproject.toml の内容が必要であれば、その情報を教えてください。README をそれに合わせて拡張します。