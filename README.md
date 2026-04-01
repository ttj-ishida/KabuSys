# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL・データ品質・ニュース収集・AI を利用したニュースセンチメント / 市場レジーム判定、監査ログ（オーダー追跡）の管理までを含むモジュール群を提供します。

現在のバージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数（.env の例）
- ディレクトリ構成
- 注意事項 / 実装上のポイント

---

## プロジェクト概要

KabuSys は日本株のデータ取得・整備・品質管理・リサーチ・AI ベースのニュース解析・市場レジーム判定・監査ログを統合するための Python ライブラリ群です。  
内部で DuckDB をデータストアとして使用し、J-Quants API からのデータ取り込みや RSS ニュース収集、OpenAI（gpt-4o-mini）を用いたセンチメント評価などを行います。バックテスト用にルックアヘッドバイアスを避ける設計思想が反映されています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - 環境変数/.env の自動読み込みと Settings オブジェクトによる集中管理
- kabusys.data
  - jquants_client: J-Quants API との通信（株価、財務、カレンダー）、DuckDB への永続化（冪等）
  - pipeline: 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）、ETLResult
  - quality: データ品質チェック（欠損／重複／スパイク／日付不整合）
  - news_collector: RSS 取得と前処理（SSRF対策、トラッキング除去、記事ID生成）
  - calendar_management: JPX カレンダー管理・営業日ロジック
  - audit: 監査テーブルの初期化（signal_events / order_requests / executions）
  - stats: z-score などの統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを取得して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュースを合成し市場レジーム判定
- kabusys.research
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー 等

設計上のポイント:
- ルックアヘッドバイアスを避ける（内部で date.today() に依存しない設計が多い）
- API 呼び出しはリトライ・バックオフ、レート制御を備える
- データ保存は冪等（ON CONFLICT）で行う
- セキュリティ考慮（RSS の SSRF 対策、defusedxml 利用等）

---

## セットアップ手順

1. Python 環境を用意
   - 推奨 Python バージョン: 3.9+（ソースは型注釈に Python 3.10 風の記法を使っていますが、3.9 以降で動作することを想定）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 基本的な依存（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ pyproject.toml / requirements.txt がある場合はそちらを利用してください。開発中は editable install が便利です:
   - pip install -e .

4. 環境変数 / .env の設定
   - プロジェクトルートに `.env` / `.env.local` を配置するか OS 環境変数で設定します（自動ロードされます）。
   - 自動ロードを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. データベース用ディレクトリ作成（必要なら）
   - デフォルトでは data/ 配下にファイルを作成します。ディレクトリがない場合 init 関数が自動作成しますが、権限等に注意してください。

---

## 使い方（主要 API の例）

以下は簡単な利用例です。事前に必要な環境変数（OpenAI API キー、J-Quants トークン等）を設定してください。

- DuckDB 接続を作成して日次 ETL を実行する例
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを取得して ai_scores に書き込む（OpenAI API キー必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジームをスコアリングして market_regime テーブルに書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査用 DuckDB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- カレンダー判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026,3,20)))
print(next_trading_day(conn, date(2026,3,20)))
```

---

## 環境変数（.env の例）

主要な環境変数例（.env に記載）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション API
KABU_API_PASSWORD=your_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス 等
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid

# 実行環境 / ログレベル
KABUSYS_ENV=development        # development | paper_trading | live
LOG_LEVEL=INFO
```

注意:
- Settings クラスは必須の値（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD など）を参照し、未設定時は ValueError を送出します。
- `.env.local` が存在する場合は OS 環境変数より優先して値が上書きされます（自動ロード設定のままの場合）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py (パッケージのエントリ)
- config.py (設定 / .env ロード)
- ai/
  - __init__.py
  - news_nlp.py (ニュースセンチメント→ai_scores)
  - regime_detector.py (市場レジーム判定)
- data/
  - __init__.py
  - jquants_client.py (J-Quants API クライアント & DuckDB 保存)
  - pipeline.py (ETL パイプライン / ETLResult)
  - quality.py (品質チェック)
  - calendar_management.py (マーケットカレンダーユーティリティ)
  - news_collector.py (RSS 取得・前処理)
  - audit.py (監査ログスキーマ初期化)
  - stats.py (統計ユーティリティ)
  - etl.py (ETLResult 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*（ファクター / IC / サマリー等）

README にある通り、モジュールは DuckDB 接続を受け取り SQL と Python の組み合わせで処理します。外部資源（発注 API 等）には基本的にアクセスしないモジュール（research 等）も含まれます。

---

## 注意事項 / 実装上のポイント

- セキュリティ
  - RSS 収集では SSRF 対策（リダイレクト検査、プライベートアドレス拒否）を実装しています。
  - XML パースには defusedxml を使用して XML Bomb 等に対処しています。
- API 利用
  - J-Quants / OpenAI 呼び出しはリトライ・バックオフやレートリミット制御を備えています。
  - OpenAI の呼び出しは JSON Mode を想定し、壊れたレスポンスに対しては安全にフォールバックします（多くは 0.0 等の中立値で継続）。
- ルックアヘッドバイアス対策
  - 多くの処理（ニュースウィンドウ計算、MA 計算、ETL）は「target_date 未満 / 以前」を厳密に使い、実行時の日付を直接参照しない設計です。
- 自動 .env ロード
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）を見つけて `.env` / `.env.local` を自動で読み込みます。テスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要に応じて README に追加したい内容（CI / テストの実行方法、詳細なスキーマ、運用手順など）があればお知らせください。