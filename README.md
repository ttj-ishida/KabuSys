# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリ。  
ETL、ニュース収集・NLP（OpenAI ベース）、ファクター計算、マーケットカレンダー管理、監査ログ（約定トレーサビリティ）など、取引戦略開発と運用に必要な基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で date.today()/datetime.today() を直接参照しない設計が多い）
- DuckDB を中心としたローカル DB を利用した ETL / 分析パイプライン
- 外部 API（J-Quants、OpenAI、kabuステーション 等）との堅牢な接続（リトライ・レートリミット対策）
- 冪等性を重視した DB 保存・監査ログ設計

---

## 機能一覧

- 環境変数 / .env 読み込み・管理（kabusys.config）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）
  - 必須環境変数検査とユーティリティを提供

- データ ETL（kabusys.data.pipeline）
  - J-Quants API から株価（日足）・財務・JPX カレンダーを差分取得・保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行
  - 日次 ETL の統合実行 `run_daily_etl`

- J-Quants クライアント（kabusys.data.jquants_client）
  - ページネーション対応、レートリミット管理、トークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存の想定実装

- カレンダー管理（kabusys.data.calendar_management）
  - market_calendar テーブルを利用した営業日判定 / 前後営業日の取得 / バッチ更新

- 監査ログ（kabusys.data.audit）
  - signal -> order_request -> execution といったトレーサビリティ用テーブル定義と初期化ユーティリティ

- ニュース NLP / 市場レジーム判定（kabusys.ai）
  - gpt-4o-mini を用いたニュースセンチメント（銘柄毎） scoring（score_news）
  - ETF (1321) の MA 乖離とマクロニュースセンチメントを合成した市場レジーム判定（score_regime）
  - API 呼び出しに対するリトライ / フォールバック設計

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- 汎用統計ユーティリティ（kabusys.data.stats）
  - Z-score 正規化など

---

## セットアップ手順

前提
- Python 3.10+（typing union 表記などを考慮）
- DuckDB、OpenAI クライアント、defusedxml などの依存が必要

例: 仮想環境作成とインストール（一般的な手順）
1. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要ライブラリをインストール（プロジェクトにrequirements.txt/pyproject.toml があればそちらを利用）
   例（最小限の依存例）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ 実運用では http クライアントやロギング、Slack 通知など他の依存も必要です。

3. 開発中はパッケージを編集可能インストール
   ```bash
   pip install -e .
   ```

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を配置すると自動読み込みされます（自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
- 主な環境変数（必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード
  - SLACK_BOT_TOKEN — Slack 通知用 Bot Token
  - SLACK_CHANNEL_ID — Slack 通知チャンネル ID
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を使う場合）
- システム設定
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト "development"）
  - LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本的な例）

以下はライブラリの典型的な利用例です。実行前に環境変数や DB 初期化を行ってください。

1) DuckDB 接続を作成して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクトを返します
conn = duckdb.connect(str(settings.duckdb_path))
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

2) ニュースセンチメント（銘柄別）を生成する（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # settings から自動参照
print(f"書き込んだ銘柄数: {n_written}")
```

3) 市場レジーム（ETF 1321 の MA200 とマクロニュースを合成）をスコアリングする
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

4) 監査ログ DB を初期化する（専用 DB を用意する場合）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

conn_audit = init_audit_db(Path("data/audit.duckdb"))
# conn_audit を使って監査テーブルにアクセスできます
```

5) RSS フィード取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点:
- OpenAI や J-Quants の API コールには課金やレート制限があります。テスト時は API 呼び出し関数をモックすることを推奨します。
- 多くの関数は DuckDB 上の特定テーブル（prices_daily/raw_prices/raw_news/raw_financials/ai_scores/market_regime 等）を前提としています。スキーマ初期化は別途用意してください（本リポジトリには schema init の想定箇所があります）。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src レイアウトの Python パッケージ構成です。主要ファイルと役割は以下の通りです。

- src/kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境変数 / .env 読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースのセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult のエクスポート
    - news_collector.py — RSS 収集と前処理
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログ（signal/order_request/executions スキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility 等）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - ai/*, research/* と data/* が主に分析・ETL・AI 機能を提供します。
  - （strategy/, execution/, monitoring/ が __all__ に含まれていますが、実装は分散しているか別途提供される想定です）

---

## 設計上の重要な注意点

- ルックアヘッドバイアス防止のため、バックテストや指標計算関数は基本的に target_date を引数で受け、内部で現在時刻を直接参照しない実装方針です。
- 外部 API 呼び出しは冗長性（リトライ・バックオフ）、レート制限の管理、エラー時のフォールバック（例: LLM の失敗時はスコア 0.0 など）を組み込んでいます。
- DB への書き込みは可能な限り冪等化（ON CONFLICT / DELETE+INSERT のパターン）しているため、繰り返し実行しても安全な設計です。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト中に自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## さらに学ぶ / 貢献

- 各モジュールの docstring に詳細な設計説明や想定スキーマ・制約が書かれています。実運用や拡張を行う際は該当モジュールのドキュメントを参照してください。
- バックテストや実取引のインテグレーション、Slack 通知、kabuステーション 実行モジュールなどは本パッケージ外で補完する想定です。実運用時は安全性（冪等性・二重発注防止）を十分考慮してください。

---

問題や補足したい箇所があれば、README の具体的なセクション（例: サンプル .env、起動スクリプト、スキーマ定義）を指定してください。必要に応じてより詳細なセットアップ手順や例スクリプトを追加します。