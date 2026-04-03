# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → ニュースNLP（OpenAI） → 市場レジーム判定 → 監査ログといった機能群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を想定したモジュール群です。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）と特徴量解析ユーティリティ
- ニュース収集 / ニュースの NLP スコアリング（OpenAI）による銘柄別 AI スコア生成
- ETF とマクロニュースを組み合わせた市場レジーム判定（LLM と価格指標の合成）
- 発注・約定に至る監査ログ（監査テーブル初期化ユーティリティ）
- 環境変数管理（.env 自動ロード、必須設定チェック）

設計方針として、ルックアヘッドバイアスの排除、冪等性（DB の ON CONFLICT）、API リトライやフェイルセーフ（API失敗時はスコアを 0 にフォールバック）などが盛り込まれています。

---

## 機能一覧（主な公開 API）

- 設定管理
  - kabusys.config.settings（環境変数からの設定参照、自動 .env ロード）
- データ ETL / 品質
  - kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL（カレンダー・株価・財務・品質チェック）
  - kabusys.data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl
  - kabusys.data.quality.run_all_checks(...) — 品質チェック一括実行
  - kabusys.data.jquants_client.* — J-Quants API クライアント（fetch / save）
- カレンダー
  - kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job — JPX カレンダー差分取得ジョブ
- ニュース収集 / NLP
  - kabusys.data.news_collector.fetch_rss(...) — RSS 取得・正規化ユーティリティ
  - kabusys.ai.news_nlp.score_news(...) — 銘柄ごとのニュースセンチメントを ai_scores に書き込む
- レジーム判定
  - kabusys.ai.regime_detector.score_regime(...) — ETF MA 乖離とマクロ記事の LLM センチメント合成
- 研究用ファクター / 統計
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.stats.zscore_normalize
- 監査ログ（audit）
  - kabusys.data.audit.init_audit_db / init_audit_schema — 監査テーブル初期化ユーティリティ

---

## 動作環境 / 依存

- Python 3.10+
- 主要依存（抜粋）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- その他: 標準ライブラリの urllib, json, datetime 等を使用

インストール例（プロジェクトルートで）:

```bash
# 開発インストール（srcレイアウトを想定）
pip install -e .

# 必要パッケージを個別にインストールする場合
pip install duckdb openai defusedxml
```

（requirements.txt / pyproject.toml を用意している場合はそちらを参照してください）

---

## 環境変数（.env）

パッケージはプロジェクトルートの `.env` / `.env.local` を自動的に読み込みます（読み込み順: OS 環境 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に利用される環境変数（代表）:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須)
- kabu ステーション（発注等）
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OpenAI / ニュース NLP
  - OPENAI_API_KEY (score_news / score_regime は api_key 引数で上書き可)
- 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB / ファイルパス
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
- 監視 / 実行制御
  - PID_FILE_PATH (default data/execution.pid)
  - KILL_FLAG_PATH (default data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
- システム設定
  - KABUSYS_ENV: development | paper_trading | live (デフォルト development)
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

簡単な .env 例:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxx
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／取得し、プロジェクトルート（pyproject.toml または .git を含むディレクトリ）に移動する。

2. Python 仮想環境を作成して有効化:

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. 依存パッケージをインストール:

```bash
pip install -e .            # または pip install -r requirements.txt
```

4. `.env` を作成して必要な環境変数を設定（上記参照）。プロジェクトルートに配置すると自動ロードされます。

5. DuckDB ファイルや保存先ディレクトリが必要な場合は作成されますが、念のため `data/` を作成しておくと安心です:

```bash
mkdir -p data
```

---

## 使い方（主要な利用例）

以降の例では duckdb 接続に標準的な使い方を示します。settings からデフォルトパスを取得できます。

- 日次 ETL を実行する:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアを生成（OpenAI API 必須）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください
n = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定を実行（ETF 1321 の MA とマクロニュースを合成）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ用 DB を初期化:

```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# settings.duckdb_path を監査用 DB にも利用可能（用途に応じて別DBを推奨）
conn = init_audit_db(settings.duckdb_path)
```

- J-Quants API を直接使ってデータ取得（テスト用）:

```python
from kabusys.data.jquants_client import fetch_daily_quotes
from datetime import date

records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,31))
print(len(records))
```

注意点:
- OpenAI 呼び出しは成功しない場合（API エラー等）にスコアを 0 にフォールバックする実装です（警告ログ）。
- score_news / score_regime は api_key 引数を受け取り、テストやキー切替に対応します（None の場合は環境変数 OPENAI_API_KEY を参照）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは `src/kabusys` 配下に実装されています。主なファイル・モジュール:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - quality.py
  - stats.py
  - news_collector.py
  - calendar_management.py
  - audit.py
  - audit DB 初期化ユーティリティや ETLResult 等を含む
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記以外に strategy / execution / monitoring 等のパッケージを __all__ で公開する準備があります。）

簡易ツリー:

```
src/
  kabusys/
    __init__.py
    config.py
    ai/
      news_nlp.py
      regime_detector.py
    data/
      jquants_client.py
      pipeline.py
      etl.py
      quality.py
      stats.py
      news_collector.py
      calendar_management.py
      audit.py
      ...
    research/
      factor_research.py
      feature_exploration.py
    research/__init__.py
```

---

## 注意・トラブルシューティング

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行われます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants の API 呼び出しはリトライ・バックオフや 401 の自動リフレッシュ等を行いますが、API キー/リフレッシュトークンは必ず安全に管理してください。
- DuckDB への executemany 等は空リストを渡せないケース（古い DuckDB）に配慮した実装になっています。何らかの挙動がおかしい場合は DuckDB のバージョン確認を推奨します。
- news_collector は外部 RSS を取得するため SSRF 対策や受信サイズ制限等の安全対策を実装しています。カスタムフィードを追加する場合は必ず http/https と公開ホストであることを確認してください。

---

## 貢献 / 拡張

- 研究用ファクターの追加、戦略層（signal → order_request → execution の連携）、実際のブローカー発注モジュール（kabu ステーション連携）等をプラグイン的に追加できます。
- テスト: OpenAI 呼び出しなどは内部で分離・パッチ可能な設計になっているため、単体テストのモック化が容易です。

---

もし README に追記したい具体的な使用例（cron ジョブ、Docker 化、CI 設定、実際の戦略フロー例など）があれば内容に合わせてサンプルを追加します。