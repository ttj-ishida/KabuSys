# KabuSys

日本株自動売買システムのライブラリ群（データプラットフォーム / 研究 / AI / 監査ログ 等）。  
このリポジトリは、J-Quants・RSS・OpenAI 等を組み合わせてデータ取得・品質チェック・ニュースセンチメント・市場レジーム判定・ファクター計算・監査ログを提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（主な設定）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株の自動売買プラットフォーム構築のための基盤ライブラリです。  
主に以下を提供します。
- J-Quants API を用いた株価・財務・マーケットカレンダー取得と DuckDB への冪等保存（ETL）
- RSS によるニュース収集と前処理 / 銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）およびマクロセンチメント（市場レジーム）評価
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と特徴量探索ツール（IC、統計サマリー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定までの監査ログスキーマ & 初期化ユーティリティ
- 簡潔な設定管理（.env 自動ロード等）

設計上の特徴:
- ルックアヘッドバイアス対策（target_date を明示、datetime.today() を直接参照しない設計）
- エラーに対してフェイルセーフ：API失敗時はスコア 0 やスキップして継続する等
- DuckDB を中心としたローカルDB運用（軽量かつ高速）

---

## 機能一覧
- 環境/設定管理（kabusys.config）
  - .env 自動ロード（.env → .env.local、OS 環境変数保護）
- データ取得 / ETL（kabusys.data）
  - J-Quants クライアント（fetch/save routines）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（営業日判定等）
  - ニュース収集（RSS）モジュール
  - データ品質チェック（quality.run_all_checks）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- AI（kabusys.ai）
  - 銘柄別ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
- 研究・解析（kabusys.research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算 / IC / 統計サマリー 等
- 汎用ユーティリティ
  - 統計ユーティリティ（zscore_normalize）

---

## セットアップ手順

前提
- Python 3.9+（typing の新しい構文を利用）
- DuckDB、OpenAI SDK、defusedxml などが必要

例: 仮想環境を作成してインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 必要パッケージの例（プロジェクトの pyproject.toml / requirements.txt がある場合はそれを使用）
pip install duckdb openai defusedxml
# 開発時インストール（プロジェクトを編集可能モードでインストール）
pip install -e .
```

環境変数の準備
- プロジェクトルート（.git または pyproject.toml を含む階層）を基準に `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨: .env ファイルを作成して必要なキーを設定します（下記を参照）。

---

## 簡単な使い方（コード例）

1) 設定の使用
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

2) DuckDB 接続を作り ETL を実行（日次）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# ETL を実行（target_date を指定しないと今日が使われる）
result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュースセンチメントを生成（OpenAI API キーが必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数に設定するか、api_key 引数にキー文字列を渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み件数: {written}")
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

5) ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

6) 監査DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成されます
```

7) RSS フィード取得（ニュースコレクタ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url, source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

注意点:
- score_news / score_regime は OpenAI API（OPENAI_API_KEY）を必要とします。api_key パラメータでも注入可能。
- ETL / save 関数は DuckDB に対して冪等的に動作するよう設計されています（ON CONFLICT DO UPDATE 等）。
- ルックアヘッドバイアス防止のため日付引数は明示的に渡すことを推奨します。

---

## 環境変数（主な設定）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ('development' | 'paper_trading' | 'live')（デフォルト: development）
- LOG_LEVEL — ログレベル ('DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL')（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime で参照）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動ロードを無効化

自動ロードの挙動:
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索して `.env` → `.env.local` の順で読み込みます。
- OS 環境変数は保護され、.env の値で上書きされません（ただし .env.local は override=True を使うため上書きされます）。
- .env のパースはシェル風の export/コメント/クォートに対応しています。

---

## ディレクトリ構成（主要ファイル）
以下はコードベースの主なファイル・モジュールです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（銘柄別）
    - regime_detector.py         — 市場レジーム判定（MA + マクロLLM）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult 再エクスポート
    - news_collector.py          — RSS ニュース収集
    - calendar_management.py     — マーケットカレンダー管理
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログスキーマ & 初期化
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/value/volatility）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー 等

この README の例や関数の使い方は、各モジュールの docstring に詳細が記載されています。特に ETL / AI 周りは外部 API（J-Quants, OpenAI）との通信が含まれるため、実行には適切な API キーとネットワークアクセスが必要です。

---

## 備考 / 運用上の注意
- OpenAI 呼び出しは料金が発生します。テスト時はモック（unittest.mock.patch）で _call_openai_api を差し替えることが想定されています。
- J-Quants API のレート制限やトークンリフレッシュ処理は jquants_client に実装されています。大量取得時は RateLimiter に注意してください。
- DuckDB への executemany の振る舞い等、バージョン依存の挙動に対する注釈がコード内にあります。問題発生時は DuckDB バージョンを確認してください。
- 監査ログテーブルは削除しない前提の設計です。運用ルールを整備してください。

---

必要に応じて README にサンプル .env.example や起動スクリプト（cron / systemd / Airflow 等）の例を追記できます。特定のユースケース（バックテスト実行、運用スケジューリング、ローカル開発）について追記希望があれば教えてください。