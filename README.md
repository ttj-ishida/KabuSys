# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants や RSS、kabuステーション、OpenAI 等の外部サービスと連携してデータ取得・品質チェック・特徴量計算・ニュースセンチメント・市場レジーム判定・監査ログ管理を行うことを目的としています。

---

## 概要

KabuSys は次の主要機能を備えた内部向けライブラリです。

- J-Quants API からの株価・財務・マーケットカレンダー取得（ページネーション・レート制御・自動リフレッシュ対応）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去・ID生成）
- OpenAI を用いたニュースセンチメント（銘柄毎）およびマクロセンチメント→市場レジーム判定
- ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ用スキーマ）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化 等）

パッケージのエントリポイントは `kabusys`（src/kabusys）で、モジュールは用途別に `data/`, `ai/`, `research/`, `config.py` などに分かれています。

---

## 主な機能一覧

- data
  - jquants_client：J-Quants API 呼び出し、保存関数（raw_prices, raw_financials, market_calendar 等）
  - pipeline：日次 ETL（差分取得・backfill・品質チェック）
  - news_collector：RSS 取得・前処理・raw_news への保存支援
  - quality：品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management：営業日判定・カレンダー更新ジョブ
  - audit：監査ログ用スキーマ作成・監査 DB 初期化
  - stats：Zスコア正規化などの汎用統計ユーティリティ
- ai
  - news_nlp.score_news：銘柄毎ニュースセンチメントを算出して ai_scores テーブルへ保存
  - regime_detector.score_regime：ETF（1321）の MA 乖離とマクロニュースの LLM スコアを合成し market_regime に保存
- research
  - factor_research：モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration：将来リターン算出、IC（スピアマン）、統計サマリー等
- config
  - 環境変数の読み込み（.env / .env.local の自動ロード）、Settings オブジェクトで設定を取得

---

## 必要条件（前提）

- Python 3.10 以上（型ヒントに Union 表記等を使用）
- 外部パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

必要に応じてプロジェクトの requirements.txt / pyproject.toml を参照して依存を追加してください。  
本リポジトリは外部サービス（J-Quants、kabuステーション、OpenAI、Slack 等）への認証情報が必要な機能が多数あります。

---

## セットアップ手順（例）

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用してください）

3. 環境変数を用意する（.env をプロジェクトルートに置くと自動で読み込まれます）
   - .env の例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース用ディレクトリを作成（必要に応じて）
   - デフォルト DuckDB パスは data/kabusys.duckdb（Settings.duckdb_path）
   - 監査用 DB を別に作る場合、init_audit_db にパスを指定できます

---

## 使い方（基本例）

以下は主なユースケースのサンプルです。適宜 import して使用します。

- DuckDB 接続の準備と ETL 実行（日次）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント算出（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う場合は None
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# conn を用いて order_requests / signal_events / executions テーブルを使用可能にします
```

- 設定値の取得
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- news_nlp / regime_detector は OpenAI（gpt-4o-mini）を使用するため、API キー（OPENAI_API_KEY）を環境変数に設定するか、各関数の api_key 引数で明示してください。
- J-Quants API を使う処理（ETL 等）は JQUANTS_REFRESH_TOKEN の設定が必要です。
- ETL の差分処理やニュースウィンドウはルックアヘッドバイアス対策で設計されています（内部で date.today() 等を不用意に参照しない等）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot Token
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視系やモニタリング用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — =1 にすると .env 自動ロードを無効化

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py — パッケージエクスポート
- config.py — 環境変数・Settings 管理（.env 自動ロード、必須変数チェック）

src/kabusys/ai/
- __init__.py
- news_nlp.py — ニュースを銘柄ごとにまとめて OpenAI に送りセンチメントを ai_scores に保存するロジック
- regime_detector.py — ETF(1321) の MA 乖離とマクロニュース LLM スコアを合成して market_regime を作成

src/kabusys/data/
- __init__.py
- jquants_client.py — J-Quants API クライアント（取得/保存/認証/レート制御/リトライ）
- pipeline.py — ETL パイプライン（run_daily_etl, 個別ジョブ）
- etl.py — ETL の公開インターフェース（ETLResult の再エクスポート）
- news_collector.py — RSS 取得・前処理・SSRF 対策・記事ID生成
- calendar_management.py — 市場カレンダー管理・営業日判定・更新ジョブ
- quality.py — データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
- stats.py — zscore_normalize 等の統計ユーティリティ
- audit.py — 監査ログスキーマ定義・初期化・インデックス
- pipeline.py — （上記）ETL の核

src/kabusys/research/
- __init__.py
- factor_research.py — momentum/value/volatility 等のファクター計算
- feature_exploration.py — 将来リターン、ランク変換、IC、統計サマリー等

その他:
- テストや CLI は含まれていません。プロジェクトに応じて小さなラッパー CLI / ジョブスクリプトを作成してください。

---

## 運用上の注意・ベストプラクティス

- 本ライブラリは実際の発注処理（execution）やポジション管理を直接含まない設計になっています。実運用で発注を行う場合は、必ずリスク管理層・冪等性・監査ログを通じて管理してください。
- OpenAI 呼び出しはコスト・レイテンシを伴うため、バッチ処理とリトライ制御を設計に組み込んでいます。API レートやコストに注意してください。
- DuckDB に対する executemany の空リストはバージョン差で問題になるため、コード内で空チェックが行われています。DB バージョンアップ時は互換性テストを行ってください。
- .env ファイルには秘密情報を含むため、リポジトリへコミットしないでください。例として .env.example を用意して鍵名のみ管理してください。

---

この README はコードベースの概要と主要な使い方を示したものです。より詳細な設計方針や各モジュールの仕様はソース内ドキュメンテーション（関数・クラスの docstring）を参照してください。必要があれば、CLI やサンプルジョブ、テストの記述も追加できます。