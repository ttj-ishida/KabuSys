# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算・リサーチ用ユーティリティ、監査ログ（発注トレーサビリティ）など、トレーディングシステムに必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 主な特徴 (機能一覧)

- 環境設定管理
  - .env / .env.local を自動ロード（必要に応じて無効化可能）
  - 必須環境変数の検証

- データ取得 / ETL（J-Quants API）
  - 日次株価（OHLCV）、財務データ、マーケットカレンダーの差分取得・保存
  - レート制御、リトライ、トークン自動リフレッシュ
  - ETL パイプラインの結果を ETLResult 型で取得

- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェック

- ニュース収集
  - RSS フィードの安全な取得（SSRF 対策、XML ディフェンス、サイズ制限）
  - raw_news と news_symbols への冪等保存ロジック（記事 ID は正規化 URL の SHA256）

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（gpt-4o-mini、JSON mode）
  - バッチ処理、リトライ、レスポンス検証、スコアのクリッピング

- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）の合成で
    日次の市場レジーム（bull / neutral / bear）を算出・保存

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルとインデックス定義
  - 監査 DB 初期化ユーティリティ（UTC タイムスタンプ、冪等）

- 研究用ユーティリティ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Spearman）、Zスコア正規化、統計サマリー

---

## 動作環境・前提

- Python 3.10+
  - （ソース中に型ヒントで | 記法や typing の機能を使用）
- 主な依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他標準ライブラリ：urllib, json, datetime 等）
- J-Quants / OpenAI の API キーが必要（詳細は環境変数の項参照）

---

## 環境変数

最低限設定が必要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必要に応じて）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必要に応じて）
- KABUSYS_ENV — 動作モード: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` を自動で読み込みます。
- `.env.local` は `.env` を上書きします。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

例: .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 要件ファイルがある場合は `pip install -r requirements.txt` を使用してください。
   - 最小例:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、シェルで環境変数をエクスポートします。
   - 自動ロードが働くため、`.env` を作成すれば OK（ただし自動ロードを無効化している場合は手動で設定）。

5. データディレクトリ作成
   ```
   mkdir -p data
   ```

---

## 使い方（コード例）

以下はよく使う操作の簡単なサンプルです。Python スクリプトやインタラクティブシェルから実行できます。

- settings（環境変数の使用例）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

- DuckDB に接続して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集（RSS）を取得
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss(
    url="https://news.yahoo.co.jp/rss/categories/business.xml",
    source="yahoo_finance"
)
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

- ニュース NLP（銘柄ごとのスコア付け）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 別ファイルでも良い: ":memory:" も可能
audit_conn = init_audit_db(settings.duckdb_path)
```

- J-Quants のトークン取得 / API 呼び出し
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使用
rows = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,1))
```

注意:
- OpenAI を利用する関数（score_news, score_regime 等）は環境変数 `OPENAI_API_KEY` を参照します。引数で明示的に渡すことも可能です（api_key=...）。

---

## 主要 API（抜粋）

- kabusys.config.settings — アプリケーション設定取得
- kabusys.data.pipeline.run_daily_etl — 日次 ETL 実行（ETLResult を返す）
- kabusys.data.jquants_client — J-Quants API クライアント（fetch_* / save_* / get_id_token）
- kabusys.data.news_collector.fetch_rss — RSS フィード取得
- kabusys.ai.news_nlp.score_news — ニュース NLP スコア付け（ai_scores へ格納）
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定（market_regime へ格納）
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化
- kabusys.research.* — ファクター計算・解析ユーティリティ

---

## ディレクトリ構成（主要ファイル）

（ルート: src/kabusys 以下）

- __init__.py
  - パッケージ公開。バージョン定義。

- config.py
  - 環境変数と .env 自動ロード、Settings クラス。

- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（銘柄別）処理、OpenAI 呼び出し、レスポンス検証
  - regime_detector.py — ETF の MA とマクロニュースを合成して市場レジーム判定

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント、rate limit、保存ロジック
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult 定義
  - etl.py — ETL 型の再エクスポート
  - news_collector.py — RSS 収集、前処理、ID 生成、SSRF 対策
  - calendar_management.py — 市場カレンダー管理・営業日ロジック
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログ（DDL / 初期化 / インデックス）
  - その他（jquants_client に関連関数）

- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー

---

## 運用上の注意点・設計方針（抜粋）

- ルックアヘッドバイアス回避のため、内部関数は date.today() や datetime.now() を無尽蔵に参照せず、呼び出し元で日付を渡す方式をとっています（バックテスト互換を重視）。
- API 呼び出しはリトライや指数バックオフ、レート制御を組み込み、フェイルセーフ（API 失敗時はスコア 0 返却等）を採用しています。
- DB への保存は冪等（ON CONFLICT DO UPDATE / INSERT ... DO NOTHING）で行い、部分失敗の際に既存データを保護します。
- ニュース収集は SSRF 対策／XML 解析の安全化／レスポンスサイズ制限等のセキュリティ対策が実装されています。

---

## テスト・デバッグ

- 自動 .env ロードを無効にしてテストを実行する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI / J-Quants 呼び出し部分は内部でラップされています。ユニットテストでは _call_openai_api や HTTP 入出力をモック（patch）して挙動を検証できます（ソース内にコメントあり）。

---

## 貢献 / ライセンス

この README はコードベースからのドキュメント生成例です。実際に運用する際は README に次を追記してください:
- ライセンス情報
- 貢献ガイド（CONTRIBUTING.md）
- 実運用時の監視・アラート設定例（Slack 通知フロー等）
- requirements.txt の固定バージョン

---

問題や追加で説明が欲しい部分（特定モジュールの詳細な使用例や API レスポンス形式の説明など）があれば教えてください。README を更に詳細化して提供します。