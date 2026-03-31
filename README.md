# KabuSys

日本株向けのデータプラットフォーム＆自動売買支援ライブラリ。J-Quants からのデータ取得（株価・財務・マーケットカレンダー）、ニュース収集・AIによるニュース/レジーム判定、研究用ファクター計算、ETL パイプライン、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価（日次 OHLCV）、財務データ、JPX マーケットカレンダーの差分取得（ページネーション・再試行・レート制御対応）
  - ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを順次実行
  - データ品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集・NLP
  - RSS フィードからニュースを収集し raw_news / news_symbols に保存（SSRF 対策・トラッキング除去・サイズ制限）
  - OpenAI を用いた銘柄ごとのニュースセンチメント算出（score_news）
  - マクロニュース + ETF（1321）200 日 MA 乖離から市場レジーム（bull/neutral/bear）を判定（score_regime）

- 研究支援（research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）・統計サマリ・正規化ユーティリティ

- 監査・実行トレーサビリティ
  - signal_events / order_requests / executions を持つ監査ログスキーマ（DuckDB）を初期化・管理（init_audit_db / init_audit_schema）
  - 冪等性・ステータス管理を前提とした設計

- 設定管理
  - .env（および .env.local / OS 環境変数）読み込み/管理（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由で主要設定参照（API トークンパス、DB パス、監視閾値、環境切替など）

---

## 要件

- Python 3.10 以上（型注釈の構文等を利用）
- 外部パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトで使用する具体的なバージョンは pyproject.toml / requirements.txt に合わせてください）

---

## セットアップ手順（開発環境）

1. リポジトリをクローンして仮想環境を作成・有効化
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール
   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。ない場合は最低限の例）
   ```
   pip install duckdb openai defusedxml
   ```

3. （任意）パッケージを開発モードでインストール
   ```
   pip install -e .
   ```

4. 環境変数 / .env を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（ただしテスト時など KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API のパスワード
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : 通知用 Slack 設定
     - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で使用）
     - DUCKDB_PATH : デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 sqlite パス（例: data/monitoring.db）
     - KABUSYS_ENV : development | paper_trading | live
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要なコード例）

以下はライブラリをインポートして使う簡単な例です。各関数は DuckDB 接続（duckdb.connect(...) で得られる接続オブジェクト）を受け取ります。

- ETL（日次パイプライン）を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定していれば api_key=None で OK
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"wrote {n_written} scores")
```

- 市場レジーム判定（ETF 1321 MA200 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリがなければ自動作成
# 以降 conn を使って監査ログへアクセス可能
```

- RSS の取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

source = "yahoo_finance"
url = DEFAULT_RSS_SOURCES[source]
articles = fetch_rss(url, source)
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.kabu_api_base_url, settings.env)
```

注意:
- OpenAI を使用する関数（score_news, score_regime）は api_key 引数で明示的にキーを渡すか、環境変数 OPENAI_API_KEY を設定してください。
- news_collector は RSS 取得時に SSRF 対策やレスポンスサイズ制限等を行います。fetch_rss はネットワークエラーをそのまま投げる可能性があります。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（OpenAI）
    - regime_detector.py         — 市場レジーム判定（ETF + マクロ）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存ロジック
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETL 公開インタフェース（ETLResult）
    - news_collector.py          — RSS 収集（SSRF 対策等）
    - quality.py                 — データ品質チェック
    - stats.py                   — 汎用統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py     — 市場カレンダー管理（営業日判定等）
    - audit.py                   — 監査ログ（テーブル定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py         — モメンタム/ボラティリティ/バリュー
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ

（上記は主要モジュールの抜粋。実際のファイルは src/kabusys 以下を参照してください）

---

## 設定・運用に関する注意点

- 自動 .env 読み込み:
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を自動で読み込みます。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

- 環境（KABUSYS_ENV）:
  - 有効値: development, paper_trading, live
  - settings.is_live / is_paper / is_dev で環境判定可能

- DB パス:
  - デフォルト DuckDB: data/kabusys.duckdb（settings.duckdb_path）

- OpenAI 呼び出し:
  - gpt-4o-mini を利用する想定で JSON mode を使用しています。API レスポンスの検証やリトライ・フォールバック処理が実装されていますが、API のバージョンや応答形式の変更によりパースエラーが発生する可能性があります。

- テスト時の差し替え:
  - AI / API 呼び出し部分はモックしやすいよう内部呼び出しを小さな関数に切り出しています（例: _call_openai_api のモック）。

---

## 開発・デバッグのヒント

- ログレベルは環境変数 `LOG_LEVEL` で制御できます。
- ETL やニュース系は外部 API に依存するため、ユニットテストでは jquants_client / OpenAI クライアント / network 呼び出しをモックしてください。
- DuckDB を用いるため、直接 SQL を実行して中間テーブルの状態を確認できます。
- news_collector や jquants_client にはネットワーク/HTTP の再試行・レートリミット処理が含まれているため、API 側の制限に合わせて動作します。

---

もし README に追加したい「例: .env.example の具体的な雛形」や「CI / デプロイ手順」のような項目があれば教えてください。README を目的（開発者向け、運用者向け、エンドユーザ向け）に合わせてさらにカスタマイズできます。