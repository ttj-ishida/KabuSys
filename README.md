# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ。  
J-Quants / kabuステーション / OpenAI 等を用いてデータ取得・品質チェック・特徴量算出・ニュースNLP・市場レジーム判定・監査ログ管理までをカバーします。

バージョン: 0.1.0

---

## 主要機能

- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXマーケットカレンダー
  - レートリミット管理、リトライ、トークン自動リフレッシュ
- ETL パイプライン
  - 差分取得、冪等保存（DuckDB へ ON CONFLICT DO UPDATE）、品質チェック
  - 日次 ETL 実行エントリ（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付整合性チェック
- ニュース収集 & 前処理
  - RSS から記事収集、URL 正規化、SSRF 対策、Gzip/サイズ制限
- ニュース NLP（OpenAI）
  - 銘柄単位のニュースセンチメント（score_news）
  - マクロ記事を用いた市場レジーム判定（score_regime）
  - JSON Mode + リトライ/フォールバック対応
- 研究用ユーティリティ
  - モメンタム/ボラティリティ/バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、Z スコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義と初期化
  - order_request_id を冪等キーとして二重発注防止

---

## 必要条件

- Python 3.10+
- 必須パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

（他に標準ライブラリのみを基本設計としていますが、実行環境に応じて追加のパッケージが必要になることがあります）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## 環境変数 / .env

自動的にプロジェクトルートの `.env` および `.env.local` をロードします（優先順位: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用される環境変数:

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABUS_API_PASSWORD (kabuステーション API パスワード、必須)
  - KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
- OpenAI / ニュース NLP
  - OPENAI_API_KEY (score_news / score_regime に必要)
- Slack（通知等）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (既定: data/kabusys.duckdb)
  - SQLITE_PATH (既定: data/monitoring.db)
- 実行モード / ログ
  - KABUSYS_ENV ∈ {development, paper_trading, live}（既定: development）
  - LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}（既定: INFO）

簡単な `.env` 例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定値は `from kabusys.config import settings` で参照できます（例: settings.jquants_refresh_token）。

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. `.env` / `.env.local` を作成して環境変数を設定
5. DuckDB データベースパス（設定）へアクセス可能か確認

例:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# .env を作成
```

---

## 使い方（簡単な例）

以下は主要 API を呼ぶ簡単な Python スニペット例です。まずは DuckDB 接続を作成します。

初期化・接続例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメント解析（OpenAI 必須）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored", n_written, "codes")
```

市場レジーム判定（ETF 1321 を使用）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログスキーマの初期化:
```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作成してスキーマ初期化
audit_conn = init_audit_db(str(settings.duckdb_path))
```

RSS フィード取得（ニュース収集）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

研究ユーティリティ（ファクター計算例）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト: [{"date": ..., "code": "1301", "mom_1m": 0.05, ...}, ...]
```

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env ロード・設定アクセス
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save 関数）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — マーケットカレンダー管理
  - news_collector.py — RSS 取得・前処理
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログテーブル初期化 / init_audit_db
  - etl.py — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py — ファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- ai/__init__.py, research/__init__.py などで主要 API をエクスポート

（README はリポジトリルートに README.md として置いてください）

---

## 設計上の注意・運用メモ

- Look-ahead バイアス防止設計
  - 多くのモジュールは内部で datetime.today()/date.today() を直接参照せず、引数で `target_date` を受け取る設計です。バックテスト・監査のため、常に適切な target_date を明示することを推奨します。
- 冪等性
  - J-Quants → DuckDB 保存は ON CONFLICT DO UPDATE を使って冪等に設計されています。
- フェイルセーフ
  - OpenAI 等外部 API の失敗時はフェイルセーフとしてスコアを 0 にしたり、個別チャンクをスキップする実装になっています（例: ニューススコアリング）。
- テスト
  - OpenAI 呼び出しなどはモックしやすいように内部関数を分離しています（テスト時に patch 可能）。

---

## 参考・問い合わせ

不明点や拡張要望があれば設計ドキュメント（StrategyModel.md / DataPlatform.md 想定）に沿って議論してください。README の内容はコードベースに合わせて要更新です。