# KabuSys — 日本株自動売買システム (README)

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数 (.env) の例
- 使い方（主要 API / 実行例）
- ディレクトリ構成
- 注意事項 / 設計方針

---

## プロジェクト概要

KabuSys は日本株に特化したデータ平台・研究・AI 分析・監査ログ・ETL および自動化実行のためのライブラリ群です。  
主に以下を提供します。

- J-Quants API からの株価・財務・カレンダー等の差分ETL（DuckDB 保存）
- ニュース（RSS）収集と LLM によるニュースセンチメント評価
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）スキーマ初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 実運用向けの設定管理・環境変数自動ロードなど

この README はソースツリー（src/kabusys）に基づく開発者向けの利用手引きです。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env/.env.local 自動ロード（プロジェクトルート検出）
  - 設定値アクセス（J-Quants トークン、KabuAPI パスワード、Slack トークン等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（認証・ページネーション・リトライ・レート制御）
  - pipeline: 日次 ETL 実行エントリ（run_daily_etl）と個別 ETL ジョブ
  - news_collector: RSS 収集（SSRF 対策、正規化、前処理）
  - calendar_management: JPX カレンダー管理・営業日判定ヘルパー
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用スキーマ初期化・DB 作成ユーティリティ
  - stats: 汎用統計（Zスコア正規化 等）
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM（OpenAI）でセンチメントスコア化して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) MA200 乖離＋マクロニュースで市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

その他、監視・実行・取引系のパッケージ群（execution, monitoring, strategy 等）に接続しやすい構成を意図しています。

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法や標準ライブラリの使用のため）
- DuckDB を利用します（pip 経由でインストール）

手順（ローカル開発環境向けの一例）:

1. リポジトリをチェックアウト
   - git clone ... && cd project-root

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージのインストール
   - 最低限必要なパッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発モードでパッケージをインストールする（プロジェクトをパッケージ化している場合）:
     ```
     pip install -e .
     ```

4. 環境変数 (.env) を作る
   - プロジェクトルートに `.env` または `.env.local` を作成してください（下記参照）。

5. DuckDB ファイル・ディレクトリ作成（必要に応じて）
   - デフォルトでは data/kabusys.duckdb 等を想定しています（設定は環境変数で上書き可能）。

6. 実行例は次節参照。

自動環境ロードを無効化したい場合:
- 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。

---

## 環境変数 (.env) の例

必要な主要環境変数（kabusys.config.Settings 参照）:

- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL      — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       — 通知先 Slack チャンネル ID（必須）
- DUCKDB_PATH            — DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 sqlite DB パス（例: data/monitoring.db）
- PID_FILE_PATH          — 実行監視用 PID ファイル（例: data/execution.pid）
- OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime で使用）
- KABUSYS_ENV            — environment ('development'|'paper_trading'|'live')（省略時 development）
- LOG_LEVEL              — ログレベル ('DEBUG','INFO',...)（省略時 INFO）

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=passw0rd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意:
- `kabusys.config` はプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動ロードします。
- `.env.local` は OS 環境変数を上書きできる（override=True）ためローカル開発専用の機密情報置き場として使えます。

---

## 使い方（主要 API / 実行例）

以下は Python から直接利用する簡単な例です。DuckDB 接続は duckdb.connect(...) を使用します。

1) DuckDB 接続の例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行（市場カレンダー / 株価 / 財務 / 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのスコアリング（OpenAI API 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY で渡すか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote scores for {n_written} codes")
```

4) 市場レジームスコアの計算（1321 MA200 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

5) RSS フィードを取得（単体テストやカスタム収集）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

6) 監査 DB 初期化（監査ログ専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル群が作成されます
```

7) ファクター計算の例
```python
from kabusys.research.factor_research import calc_momentum

momentum = calc_momentum(conn, target_date=date(2026,3,20))
# momentum は各銘柄ごとの dict のリスト (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)
```

注意点
- OpenAI / J-Quants など外部 API 呼び出しはリトライやフォールバックロジックを持っていますが、API キー・レート制限の設定は必須です。
- 各関数はルックアヘッドバイアスを防ぐ実装になっており、内部で datetime.today() を参照しないよう配慮されています（バックテストでの利用に適しています）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュールの一覧（抜粋）です。

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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult re-export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/** (utils for factor research)
  - (その他) strategy/, execution/, monitoring/ （パッケージ公開名に含まれるがここに該当ファイルがあればそれぞれ）

主要な役割
- data/jquants_client.py: J-Quants との通信と DuckDB 保存ロジック
- data/pipeline.py: ETL の高レベル制御（run_daily_etl など）
- ai/news_nlp.py, ai/regime_detector.py: OpenAI を利用した NLP/レジーム判定
- research/*: ファクター計算と分析用ユーティリティ
- data/news_collector.py: RSS 取得と前処理（SSRF 対策・正規化等）
- data/audit.py: 監査ログ用スキーマ定義・初期化

---

## 注意事項 / 設計方針（抜粋）

- Look-ahead bias 対策
  - バックテスト用途を強く意識し、各処理は "target_date" を受け取り内部で現在時刻を参照しないように実装されています。
  - prices_daily などのクエリでは date < target_date 等の排他条件を利用しています。

- フェイルセーフ
  - LLM や外部 API の失敗時はゼロや空でフォールバックし、処理継続を優先する箇所があります（ログは出力）。
  - J-Quants API はレート制限とリトライを実装しています（120 req/min, 指数バックオフ、401 のトークンリフレッシュ等）。

- セキュリティ
  - news_collector では SSRF 対策（ホスト検証、リダイレクト検査）、受信サイズ制限、defusedxml による XML パース防御を実施しています。

- DuckDB との互換性
  - executemany に空リストを渡すと動作しないバージョンを考慮した実装（呼び出し前に空でないことを確認）があります。
  - ON CONFLICT DO UPDATE による冪等保存を前提とした ETL 設計です。

---

必要に応じて README を拡張して、CI / テスト実行方法やデプロイ手順（本番 KABU API 連携、Slack 通知ハンドラー、daemon 起動スクリプト等）を追加してください。質問やサンプルコードの追記が必要であればお知らせください。