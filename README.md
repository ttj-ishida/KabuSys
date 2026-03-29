# KabuSys

日本株のデータプラットフォーム / 自動売買補助ライブラリです。  
ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象にしたデータ取得・品質管理・解析・簡易的な自動売買基盤向けのユーティリティ群です。主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- RSS ニュースの収集と LLM を使った銘柄別センチメント評価（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- ファクター（Momentum / Value / Volatility）計算と研究用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用スキーマ初期化

設計上の特長として、ルックアヘッドバイアスの排除、冪等性、API のリトライ＆レート制御、DuckDB を用いたローカルデータ管理などを重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証 / ページネーション / 保存関数）
  - 市場カレンダー管理（営業日判定、next/prev 等）
  - ニュース収集（RSS → raw_news、SSRF 対策、正規化）
  - 品質チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログスキーマ初期化（監査テーブル・インデックス）
  - 統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP スコア（gpt-4o-mini を利用した銘柄別センチメント）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / summary / rank）
- config
  - 環境変数管理（.env 自動読み込み、必須チェック、設定ラッパー）
- audit
  - 監査用 DB 初期化（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提: Python 3.10+（型ヒントに | を使っているため）を推奨します。

1. リポジトリをクローン
   - git clone ...（お使いのリポジトリ URL）

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージ依存関係をインストール  
   （このリポジトリに requirements.txt / pyproject.toml がある想定で以下例）  
   - pip install -r requirements.txt  
   必要な主要パッケージ（参考）:
     - duckdb
     - openai
     - defusedxml

   もしローカルで開発する場合:
   - pip install -e .

4. 環境変数の設定（.env）
   プロジェクトルートに `.env`（および任意で `.env.local`）を作成してください。以下は主なキー：

   - JQUANTS_REFRESH_TOKEN=...       # 必須（J-Quants のリフレッシュトークン）
   - KABU_API_PASSWORD=...           # 必須（kabuステーション API 用）
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
   - OPENAI_API_KEY=...              # OpenAI API キー（AI 機能を使う場合）
   - SLACK_BOT_TOKEN=...             # 必須（Slack 通知を使う場合）
   - SLACK_CHANNEL_ID=...            # 必須（Slack 通知を使う場合）
   - DUCKDB_PATH=data/kabusys.duckdb # DuckDB データファイルパス（デフォルト）
   - SQLITE_PATH=data/monitoring.db  # 監視用 SQLite パス（デフォルト）
   - KABUSYS_ENV=development|paper_trading|live  # default=development
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  # default=INFO

   自動ロードについて:
   - パッケージ import 時にプロジェクトルート（.git または pyproject.toml がある場所）から `.env` / `.env.local` を自動で読み込みます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡単な例）

以下は最小限の利用例です。DuckDB コネクションを作成し ETL や AI スコアリング関数を呼び出します。

1. DuckDB に接続して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path がデフォルト "data/kabusys.duckdb" を指しますが
# 直接パス指定してもよいです。
conn = duckdb.connect("data/kabusys.duckdb")

# ETL を今日 (または指定日) に対して実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニューススコアリング（OpenAI API キーが必要）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env OPENAI_API_KEY を使う
print(f"scored {count} codes")
```

3. 市場レジーム判定（1321 の MA200 とマクロ記事を合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を使用
```

4. 監査 DB 初期化

```python
from kabusys.data.audit import init_audit_db

# ファイル作成とスキーマ初期化（:memory: でメモリ DB）
conn = init_audit_db("data/audit.duckdb")
```

注意点:
- AI 機能（news_nlp / regime_detector）は OpenAI へリクエストを行います。API キー（OPENAI_API_KEY）を設定してください。
- J-Quants を使う ETL は JQUANTS_REFRESH_TOKEN が必須です。
- 関数は基本的に DuckDB の接続（kabusys.settings.duckdb_path で指す DB）を受け取ります。DB スキーマは必要に応じて前準備（スキーマ初期化）してください。

---

## ディレクトリ構成（主なファイルと役割）

src/kabusys/
- __init__.py
- config.py
  - .env の自動読み込み、Settings クラス（環境変数ラッパー）
- ai/
  - __init__.py
  - news_nlp.py         # ニュースを LLM で銘柄別にスコア化
  - regime_detector.py  # 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py   # J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py         # ETL パイプライン（run_daily_etl 等）
  - etl.py              # ETLResult の再エクスポート
  - calendar_management.py  # 市場カレンダー管理（営業日判定等）
  - news_collector.py   # RSS 取得・前処理・保存ロジック
  - quality.py          # データ品質チェック
  - audit.py            # 監査ログ（テーブル定義・初期化）
  - stats.py            # 統計ユーティリティ（zscore_normalize 等）
- research/
  - __init__.py
  - factor_research.py  # モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py # forward returns / IC / summary / rank

ドキュメント内の各モジュールは README に書かれた設計方針（ルックアヘッド回避、冪等性、リトライ等）に基づいて実装されています。

---

## 追加情報 / 運用上の注意

- ログレベル・実行環境:
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれかである必要があります。
  - LOG_LEVEL は "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" が有効です。

- セキュリティ・運用:
  - news_collector では SSRF 対策・XML インジェクション対策（defusedxml）・レスポンスサイズ制限を実施しています。
  - J-Quants API はレート制限を守る実装（固定間隔スロットル）と 401 時の自動リフレッシュを備えます。
  - AI 呼び出しはリトライとレスポンスバリデーションを行い、失敗時はフェイルセーフ（中央値や 0 を使う）で継続する設計です。

- テスト:
  - AI 呼び出し部分は内部関数（_call_openai_api 等）をモックしやすく実装されています。ユニットテストでの差替えが想定されています。

---

この README はコードベースの主要機能と使い始めに必要な情報を簡潔にまとめたものです。導入・運用時に詳細な API や DB スキーマ、運用手順（デプロイ、ジョブスケジューラ、監視）は別途ドキュメント化することを推奨します。問題・改善要望があれば README を更新してください。