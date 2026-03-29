# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けのデータプラットフォーム・リサーチ・自動売買のための共通ライブラリ群です。ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター計算、監査ログなどを含みます。

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API からの株価／財務／マーケットカレンダー等の差分取得（ETL）
- raw_news の収集・前処理、OpenAI を使ったニュースセンチメント解析（ai.news_nlp）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメント合成）（ai.regime_detector）
- 研究用ファクター計算・特徴量探索（research）
- データ品質チェック、監査ログ（data.quality / data.audit）
- DuckDB をコア DB として設計（デフォルトは data/kabusys.duckdb）

設計方針の要点：
- ルックアヘッドバイアス回避（内部処理で datetime.today() を直接参照しない等）
- 冪等性（DB へは ON CONFLICT を用いた更新）
- 外部 API 呼び出しに対する堅牢なリトライ・バックオフ・エラーハンドリング
- テスト容易性（API 呼び出し部分は差し替え可能）

---

## 機能一覧

主な機能（モジュール）:

- kabusys.config
  - .env / 環境変数の自動読み込み（.env.local を優先）
  - 必須設定の取得ユーティリティ（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得/保存/認証/レート制御）
  - pipeline: 日次 ETL 実行（run_daily_etl など）
  - news_collector: RSS 収集・前処理（fetch_rss 等）
  - calendar_management: 市場カレンダー・営業日判定（is_trading_day, next_trading_day 等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用テーブル初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄別に OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF の MA とマクロ記事の LLM センチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

（strategy / execution / monitoring はパッケージ定義に含まれますが、この README に添付のコード断片では一部のみ実装されています）

---

## 必要条件 / 依存関係

主な依存ライブラリ（一例）:

- Python 3.9+
- duckdb
- openai (OpenAI SDK、gpt-4o-mini を利用する場合)
- defusedxml (RSS パースの安全化)
- 標準ライブラリ（urllib, json, datetime, logging 等）

実際のプロジェクトでは pyproject.toml / requirements.txt を用意し、pip 等でインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install -e .           # 開発インストール（パッケージとして配布されている前提）
pip install duckdb openai defusedxml
```

---

## 環境変数（重要）

kabusys.config.Settings が参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション向けパスワード（発注系で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API 呼び出しに使用（ai モジュール）

任意（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env 読込を無効化
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等に使用（デフォルト: data/monitoring.db）
- KABUS_API_BASE_URL — kabu REST API のベース URL（デフォルト http://localhost:18080/kabusapi）

自動 .env 読み込み:
- プロジェクトルートに .env / .env.local がある場合、環境変数として自動読み込みします。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- テストなどで自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サンプル .env（README 用簡易例）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定
   - 上のサンプルのように .env をプロジェクトルートに作成するか、OS 環境変数で設定してください。
   - 自動ロードは .env / .env.local を参照します（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。

4. DuckDB 初期化（監査ログなど） — 任意
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # あるいは既存の接続にスキーマ追加:
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（主要な例）

以降のコード例は Python REPL やスクリプトで実行できます。事前に環境変数と依存関係のセットアップを行ってください。

- DuckDB 接続の作成（デフォルト path は settings.duckdb_path）
```python
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得と品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント集計（ai.news_nlp）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
# OpenAI API キーが環境変数 OPENAI_API_KEY にある前提
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ai.regime_detector）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算・リサーチ関数（research）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- ニュース RSS 取得（一部：fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

- 監査ログ初期化（audit）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意点:
- OpenAI 呼び出しや J-Quants 呼び出しは課金やレート制限の対象です。テスト時は対応関数をモックしてください（コード内にモックしやすい設計がされています）。
- DuckDB の executemany はバージョン差異で挙動があるため、モジュール内でも空リスト回避などの対策を行っています。

---

## 開発・テストのヒント

- 環境変数の自動読み込みを無効にするには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  これによりテスト環境で任意の環境変数セットを制御しやすくなります。

- OpenAI / J-Quants 呼び出しはユニットテストで差し替え可能です（モジュール内の _call_openai_api, jquants_client._request などを patch する設計になっています）。

- RSS の取得は外部へのネットワークアクセスをするため、fetch_rss をモックしてローカル XML を返すようにすると安定したテストが可能です。

---

## ディレクトリ構成（主要ファイル）

（README に含まれるコードベースに対応するファイル一覧）

- src/kabusys/
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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: pipeline の ETLResult を etl.py で再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai, research などから参照されるユーティリティやモジュール群

各ファイルの役割:
- config.py: 環境変数・.env 読み込み、設定オブジェクト（settings）
- jquants_client.py: J-Quants API の取得・保存ロジック（認証・レート制御・リトライ）
- pipeline.py / etl.py: 差分ETL と日次パイプライン実装
- news_collector.py: RSS 取得・前処理（SSRF 対策やサイズ上限対応）
- news_nlp.py / regime_detector.py: OpenAI を使ったスコアリングロジック
- research/*: ファクター計算・特徴量探索処理
- audit.py: 監査ログ用スキーマ初期化、DB 接続ユーティリティ
- quality.py: データ品質チェック群
- stats.py: 共通統計ユーティリティ（Z スコア等）

---

## 補足 / 注意事項

- 本 README はリポジトリに含まれるコード断片に基づいた利用ガイドです。実プロジェクトでの運用時は権限管理、鍵の安全な保管、ログ監視、運用手順（本番/ペーパートレード分離）を必ず整備してください。
- 発注（kabu ステーション）や実売買に関わる箇所は慎重なテストが必要です。live 環境フラグ（KABUSYS_ENV）を正しく設定し、紙上確認とシミュレーションを行ってから運用してください。

---

必要であれば、README に含めるコマンド例や CI / デプロイ手順（例えば GitHub Actions、Systemd タイマーで ETL を定期実行する例）や .env.example のテンプレートを追加します。どの情報を詳細化したいか教えてください。