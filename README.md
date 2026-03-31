# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP、研究用ファクター計算、監査ログ（発注・約定トレース）等のユーティリティを提供します。

主な設計方針
- バックテスト時のルックアヘッドバイアス回避（日時参照や取得範囲制御に配慮）
- DuckDB を中心としたローカル DB 保存（冪等性を考慮）
- 外部 API 呼び出しはリトライ・レートリミット等の堅牢性実装
- AI（OpenAI）呼び出しはフェイルセーフ（エラー時はスコアを中立にフォールバック）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じ無効化可能）
  - 必須環境変数チェック（Settings クラス）
- データ ETL（J-Quants クライアント）
  - 株価日足（raw_prices）取得・保存
  - 財務データ（raw_financials）取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分更新・バックフィル・品質チェック付きの日次 ETL (`run_daily_etl`)
- ニュース収集
  - RSS 取得・前処理・raw_news への冪等保存（SSRF や XML 攻撃対策あり）
- ニュース NLP / AI
  - 銘柄ごとのニュースセンチメントを OpenAI で評価 → `ai.score_news`
  - マクロニュース + ETF MA200 を合成して市場レジーム判定 → `ai.regime_detector.score_regime`
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェック
- 監査ログ（監査テーブル）
  - signal_events / order_requests / executions テーブル、DDL 初期化ユーティリティ
  - 監査DB初期化 (`data.audit.init_audit_db`)

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントの | 表記などを使用）
- DuckDB を利用（ローカルファイルまたはインメモリ）
- OpenAI API を利用する場合は OpenAI の API キーが必要
- J-Quants のリフレッシュトークンが必要

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   ※実際の requirements.txt があれば `pip install -r requirements.txt` を推奨。

4. 環境変数設定
   - プロジェクトルートに `.env` を作成すると、自動で読み込まれます（`.env.local` があれば優先）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

例: `.env`（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB の初期化（監査用 DB など）
   - 監査DBを初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（簡易例）

- Settings の利用
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 必須設定（未設定なら例外）
```

- DuckDB 接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日を処理
print(result.to_dict())
```

- ニュースセンチメントスコア（OpenAI 必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20))  # 日付は過去のトラディングデイを想定
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定（OpenAI 必要）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from kabusys.research import calc_momentum, zscore_normalize
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
normed = zscore_normalize(records, ["mom_1m", "mom_3m"])
```

- RSS フィード取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

---

## 重要な環境変数

（Settings クラスで使用／必須とされるもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (AI モジュール使用時に必須)
- KABUSYS_ENV (development / paper_trading / live のいずれか、デフォルト development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB、デフォルト data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

設定不足や不正値は Settings プロパティで ValueError が投げられます。

---

## ディレクトリ構成（概観）

src/kabusys/ 以下の主要モジュール構成:

- kabusys/
  - __init__.py
  - config.py                         # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      # 銘柄別ニューススコアリング（OpenAI）
    - regime_detector.py               # マクロ + MA200 合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                # J-Quants API クライアント（取得・保存）
    - pipeline.py                      # ETL パイプライン / run_daily_etl 等
    - etl.py                           # ETLResult 再エクスポート
    - calendar_management.py           # 市場カレンダー管理 / 営業日判定
    - news_collector.py                # RSS 収集 / 前処理
    - quality.py                       # データ品質チェック
    - stats.py                         # z-score 正規化など
    - audit.py                         # 監査ログ（DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py               # Momentum / Value / Volatility 計算
    - feature_exploration.py           # 将来リターン / IC / 統計サマリー

この README は主要な公開 API とユースケースを簡潔に示したものです。各モジュールの docstring に詳細な設計方針・前提・戻り値仕様が記載されていますので、実装や拡張時はソース内コメントも参照してください。

---

## 開発・テストメモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を検索）を基準に行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うか、テスト用環境変数を直接注入してください。
- OpenAI 呼び出し部分は内部で専用のラッパー関数を経由する設計になっており、テスト時は該当関数をモック可能です（例: news_nlp._call_openai_api を patch）。
- DuckDB の executemany は空リストを受け付けないバージョン依存の考慮が随所に入っています。ユニットテストでは小さなデータセットで動作確認を推奨します。

---

ご不明点や README に追加したい内容（例: 具体的な CI / デプロイ手順、詳細なスキーマ一覧、サンプル .env.example）などがあれば教えてください。README を拡張して提供します。