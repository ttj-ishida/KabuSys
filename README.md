# KabuSys — 日本株自動売買・データ基盤ライブラリ

KabuSys は日本株のデータ ETL、NLP によるニューススコアリング、ファクター計算、監査ログなどを含む内部ライブラリ群です。DuckDB をデータレイクとして用い、J-Quants API / RSS / OpenAI を連携してデータ取得・前処理・解析を行うことを目的としています。

## 主な特徴（機能一覧）
- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務情報、JPX カレンダーを差分取得する pipeline（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）。
  - レート制限・トークン自動リフレッシュ・リトライ機構付きの jquants_client。
- データ品質管理
  - 欠損・重複・スパイク・日付不整合などを検出する quality モジュール。
- ニュース収集 / 前処理
  - RSS を取得して raw_news に蓄積する news_collector（URL 正規化、SSRF 防止、サイズ制限、XML の安全パースなど）。
- ニュース NLP（OpenAI）
  - 銘柄別ニュース統合センチメントを ai_scores に書き込む score_news。
  - マクロニュースと ETF（1321）200日MA乖離を組み合わせて市場レジームを判定する score_regime。
  - OpenAI の JSON Mode を使った堅牢なパース、再試行・フォールバック実装。
- リサーチ支援
  - モメンタム・バリュー・ボラティリティ等のファクター計算（research パッケージ）。
  - 将来リターン計算・IC（Information Coefficient）計算・ファクター統計要約。
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを作成・初期化する audit モジュール（init_audit_schema / init_audit_db）。
- 設定管理
  - .env ファイルや環境変数からアプリ設定を読み込む kabusys.config.settings（自動 .env ロード機能付き、無効化フラグあり）。

---

## セットアップ手順

前提:
- Python 3.10+（Union 型 annotation（|）を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   （プロジェクトに requirements.txt がある場合はそれを使ってください。最低で以下パッケージが必要になります）
   ```
   pip install duckdb openai defusedxml
   ```

3. ソースを開発モードでインストール（プロジェクトルートで）
   ```
   pip install -e .
   ```
   （setuptools / pyproject.toml によるインストールが前提です。無い場合は src を PYTHONPATH に追加して利用してください）

4. 環境変数設定
   プロジェクトルートの `.env` または `.env.local` に必要な環境変数を記載します。kabusys.config はプロジェクトルート（.git または pyproject.toml）を自動検出して `.env` を読み込みます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（必須とデフォルト値）:
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID — Slack 送信先チャンネル ID（必須）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — one of {development, paper_trading, live}（デフォルト: development）
   - LOG_LEVEL — one of {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）

   例: .env
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 基本的な使い方（コード例）

以下は典型的な利用例です。DuckDB 接続を作成して各機能を呼び出します。

- DuckDB 接続と ETL 実行（1日分の ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# settings からパスを使う場合
from kabusys.config import settings
db_path = str(settings.duckdb_path)

conn = duckdb.connect(db_path)
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使うなら api_key=None
print(f"scored {n_written} codes")
```

- 市場レジーム判定（OpenAI 必須）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルが作成されていることを確認できます
```

- RSS 取得（news_collector の fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 主要モジュールの説明

- kabusys.config
  - Settings クラス: 環境変数から設定を取得します。自動でプロジェクトルートを探して `.env` / `.env.local` を読み込む仕組みがあります（無効化可能）。
  - 必須値が欠けていると ValueError を送出します。

- kabusys.data.jquants_client
  - J-Quants API と通信してデータを取得・DuckDB に保存する関数群（fetch_* / save_*）。
  - レートリミッター・リトライ・401 リフレッシュ対応。

- kabusys.data.pipeline
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェックの一連 ETL を実行して ETLResult を返します。

- kabusys.data.quality
  - 各データ品質チェック（欠損・スパイク・重複・日付不整合）。

- kabusys.data.news_collector
  - RSS の安全取得と前処理。URL 正規化・トラッキング排除・SSRF 対策・XML の安全パース。

- kabusys.ai.news_nlp / kabusys.ai.regime_detector
  - OpenAI を用いたニュースセンチメント評価。JSON Mode を使い、レスポンスのバリデーションや再試行ロジックを実装。

- kabusys.research
  - ファクター計算・将来リターン・IC 計算・統計サマリー等、研究用途の計算ユーティリティ。

- kabusys.data.audit
  - 監査テーブル定義および初期化関数。トレーサビリティを保証する監査ログスキーマを提供。

---

## 開発 / テスト時のポイント
- 自動 .env 読み込みは、パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に環境汚染を避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分はモジュール内でラップされており、unit test では `_call_openai_api` をモックすることで外部 API 呼び出しを差し替えられるよう実装されています。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるので、該当処理では空の場合はスキップする実装になっています。

---

## ディレクトリ構成

（主要ファイル群を抜粋）

- src/
  - kabusys/
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
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - etl.py (公開インターフェース re-export)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - ...（他ユーティリティ）
    - ai/ (ニュース・レジーム判定等)
    - research/ (ファクター計算等)

（実際のレポジトリに応じて pyproject.toml / requirements.txt / tests/ 等が存在することが想定されます）

---

## 運用上の注意
- OpenAI や J-Quants の API キーは適切に管理してください。ログやソースにハードコードしないでください。
- score_news / score_regime は外部 API への呼び出しを伴うため、実行回数やバッチサイズを運用ポリシーに合わせて調整してください（コスト・レート制限）。
- ETL は部分失敗を考慮した実装になっており、部分的にデータが更新されるケースがあります。監査やモニタリングを併用して運用してください。
- DuckDB ファイルのバックアップ、監査 DB の権限管理を推奨します。

---

もし README に追加したい具体的な手順（例: systemd ジョブ設定、CI 設定、より詳細な環境変数例、SQL スキーマ定義抜粋等）があれば教えてください。必要に応じて追記・整形します。