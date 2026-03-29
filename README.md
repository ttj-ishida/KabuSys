# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ、マーケットカレンダーなどを統合的に提供します。

---

## 概要

KabuSys は以下の機能群を持つ Python モジュール群です。

- J-Quants API を使った株価・財務・マーケットカレンダーの差分取得と DuckDB への冪等保存
- ETL パイプライン（run_daily_etl）と品質チェック
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI を利用したニュースセンチメント（score_news）と市場レジーム判定（score_regime）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）および統計ユーティリティ
- 監査（audit）テーブルと初期化ユーティリティ（監査ログ／発注トレーサビリティ）
- カレンダー管理（営業日判定・更新ジョブ）

設計上の重要点：
- ルックアヘッドバイアスを避けるため、内部で date.today() / datetime.today() を不用意に参照しない実装方針
- API リクエストのリトライ／指数バックオフ、レートリミット遵守（J-Quants）
- DuckDB への保存は冪等設計（ON CONFLICT DO UPDATE 等）
- ニュース関連には SSRF 対策・トラッキングパラメータ除去・XML の安全パースを実装

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得 + DuckDB 保存関数）
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl 等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - news_collector: RSS 収集・前処理・保存ロジック（SSRF 対策）
  - calendar_management: 市場カレンダー管理・営業日判定
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats: z-score 正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを用いた銘柄別 NLP スコアリング（OpenAI 呼び出し）
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースを組み合わせた市場レジーム判定
- research/
  - factor_research: momentum, volatility, value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー 等
- config.py: 環境変数管理・自動 .env ロード（プロジェクトルート検出）と Settings API

---

## セットアップ手順

前提
- Python 3.10 以上推奨（Union 型記法や型ヒントを利用）
- DuckDB が必要（Python パッケージとして duckdb を利用）
- OpenAI を使う場合は openai パッケージが必要
- defusedxml（RSS パースの安全対策）など

例: 仮想環境作成とインストール（最小例）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# もしパッケージとしてインストール可能なら:
# pip install -e .
```

推奨・想定パッケージ（プロジェクトに合わせて追加してください）
- duckdb
- openai
- defusedxml

環境変数
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（本プロジェクトの別機能向け）
- KABU_API_BASE_URL (任意) — デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN (必須) — Slack 通知用（使用する場合）
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネルID
- DUCKDB_PATH (任意) — duckdb ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 sqlite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG/INFO/etc（デフォルト INFO）
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー

.env 自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）を検出し、
  `.env` と `.env.local` を自動的に読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env（必要な値だけ）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本的な呼び出し例）

1) DuckDB 接続の準備と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# 日次 ETL（target_date を省略すると today を使います）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（OpenAI を利用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print(f"written scores: {n_written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査データベース初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# init_audit_db はスキーマを作成して接続を返します
```

5) RSS フィード取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意事項
- OpenAI 呼び出しは API レスポンスのバリデーションやリトライを行いますが、API キーは必ず安全に管理してください。
- run_daily_etl 等は ETLResult を返し、品質問題やエラーは result.quality_issues / result.errors に収集されます。

---

## ディレクトリ構成（主要ファイル）

この README は src/kabusys 以下のコードをベースに説明しています。主要ファイルのツリーは次の通りです。

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
    - pipeline.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/  (README要件では __all__ に含まれているが実装は別途)
  - strategy/    (戦略層は別モジュールで追加想定)
  - execution/   (発注実装層は別モジュールで追加想定)

各モジュールの役割は先の「主な機能一覧」を参照してください。

---

## 設計上の注意（開発者向け）

- ルックアヘッド回避: AI スコアリングや指標計算は target_date に対して過去データのみを使用するよう設計されています（date < target_date や window の排他条件など）。
- 冪等性: J-Quants から取得したデータの DB 保存は ON CONFLICT DO UPDATE を用いて冪等化しています。
- エラーハンドリング: 外部 API はリトライ／バックオフ処理、失敗時のフェイルセーフ（例: macro_sentiment=0.0）を備えています。
- セキュリティ: news_collector は SSRF 対策、XML の安全パース、受信サイズ制限、トラッキングパラメータ除去などを実施しています。
- DuckDB: 本プロジェクトは DuckDB を主に利用します。接続は duckdb.connect(path) で行います。

---

## 追加情報 / 今後の拡張

- strategy, execution, monitoring 等の実装は別モジュールで追加可能です（README にある __all__ のエントリは将来拡張を示唆）。
- Slack 連携や kabuステーション発注の実装はプロジェクトに合わせて追加してください（config にトークン設定はありますが、発注ロジック自体は別実装を想定）。
- テスト: 各種外部呼び出し（OpenAI / J-Quants / HTTP）に対してはモックを利用したユニットテストを推奨します（module 内で差し替え可能な関数を設計済みです）。

---

必要であれば README に含めるサンプル .env.example、より詳しい API 使用例、あるいは CI / デプロイ手順 (Dockerfile, systemd unit など) を追加で作成しますか？