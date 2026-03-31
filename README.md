# KabuSys

KabuSys は日本株のデータプラットフォームおよび自動売買支援ライブラリです。J-Quants からのデータ取得／ETL、ニュース収集と LLM によるニュースセンチメント解析、各種ファクター算出、マーケットレジーム判定、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主な用途:
- データ取得・品質管理（DuckDB に格納）
- ニュースの収集と AI によるスコア付け
- ファクター計算・リサーチ支援
- 市場レジーム判定（MA + マクロニュース）
- 監査ログスキーマの初期化（発注・約定のトレース）
- ETL バッチ（run_daily_etl など）

---

## 機能一覧

- data (kabusys.data)
  - jquants_client: J-Quants API クライアント（差分取得・リトライ・レート制御・保存）
  - pipeline: 日次 ETL（run_daily_etl）／個別 ETL（prices/financials/calendar）
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - calendar_management: JPX カレンダー管理（営業日判定・next/prev／カレンダー更新ジョブ）
  - audit: 監査ログテーブル定義と初期化（signal_events / order_requests / executions）
  - news_collector: RSS 取得と記事前処理（SSRF 対策・トラッキング除去）
  - stats: 共通統計ユーティリティ（zscore_normalize 等）
- ai (kabusys.ai)
  - news_nlp.score_news: ニュースを LLM (gpt-4o-mini) に投げて銘柄別スコアを ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離 + マクロニュースセンチメントで市場レジーム判定
- research (kabusys.research)
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー 等
- その他
  - 設定読み込み（kabusys.config）: .env / .env.local / OS 環境変数の取り込み、必須変数チェック

---

## セットアップ手順

前提:
- Python 3.10+（型注釈に | を使用）
- DuckDB 使用（ローカルファイルまたは :memory:）
- OpenAI SDK（AI モジュール利用時）
- defusedxml（RSS パーサ）

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. 本パッケージを開発モードでインストール（プロジェクトルートで）
   ```
   pip install -e .
   ```
   （パッケージ配布構成がある前提。ない場合は import path を調整して下さい）

4. 環境変数の設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き）。
   - 自動ロードを無効化する場合は環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
   - OPENAI_API_KEY: OpenAI を使う場合に必須（news_nlp, regime_detector）
   - その他（任意）:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   簡易的な .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（主な例）

以下は Python での簡単な利用例です。適宜ログ設定や例外ハンドリングを追加してください。

- DuckDB 接続を作って ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコア付け（news_nlp）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定している場合は api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定（regime_detector）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を使用する例（別ファイルでも可）
conn_audit = init_audit_db(settings.duckdb_path)
# 既存接続にテーブルだけ追加したい場合:
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn_audit, transactional=True)
```

- RSS フェッチ（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
# 取得した記事を raw_news に保存する処理はシステム側で実装して下さい
```

注意:
- AI 呼び出し（OpenAI）はネットワーク・料金・レイテンシが発生します。テスト時はモック（unittest.mock.patch）で `_call_openai_api` を差し替えられる設計です（kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api）。
- run_daily_etl は ETL 中に発生した品質問題やエラー情報を ETLResult に収集します。戻り値から has_errors / has_quality_errors を確認できます。

---

## ディレクトリ構成

（プロジェクトの src/kabusys 下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数と設定管理
  - ai/
    - __init__.py
    - news_nlp.py                # ニュース NLP スコアリング（ai_scores へ書込）
    - regime_detector.py        # 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - quality.py                # データ品質チェック
    - calendar_management.py    # 市場カレンダー管理（営業日判定・更新ジョブ）
    - news_collector.py         # RSS 収集と前処理（SSRF 対策等）
    - audit.py                  # 監査ログテーブル定義 / 初期化
    - etl.py                    # ETLResult の再エクスポート
    - stats.py                  # 共通統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py        # Momentum / Value / Volatility
    - feature_exploration.py    # forward returns / IC / summary

---

## 開発・テストのヒント

- 環境変数の自動読み込み:
  - プロジェクトルートの .env, .env.local を自動的に読み込みます（優先順位: OS 環境 > .env.local > .env）。
  - テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止できます。
- OpenAI 呼び出しはモック可能:
  - 単体テストでは kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api を patch して応答をシミュレートすると高速かつ安定します。
- DuckDB の executemany は空リストだと失敗するバージョンがあります。コード内で空チェックがされている点に注意してください。
- ETL は部分失敗を許容してログと ETLResult に情報を残す設計です。運用側で警告・停止ポリシーを決めてください。

---

## 参考・補足

- 設定クラス: kabusys.config.settings からプロジェクト全体の設定を取得できます（例: settings.duckdb_path）。
- OpenAI の JSON Mode を利用して厳密な JSON レスポンスを期待する設計になっています。レスポンスパース失敗時はフェイルセーフで 0.0 を返す等の処理が組まれています。
- J-Quants の API レート制御やトークン自動リフレッシュは jquants_client に実装されています。

---

必要に応じて README に実行スクリプト例（cron / systemd / Dockerfile）や .env.example、requirements.txt を追加できます。追加して欲しい実行例や詳しい運用手順（例: 本番デプロイ時の注意点）があれば教えてください。