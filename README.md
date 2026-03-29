# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）など、投資システムの基盤的な機能を提供します。

主に DuckDB を内部データストアとして用い、OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価や、J-Quants API からのデータ取得を行います。

---

## 特徴（機能一覧）

- データ取得（ETL）
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPX マーケットカレンダー取得（ページネーション・レートリミット対応）
  - 差分取得、バックフィル、冪等保存（ON CONFLICT DO UPDATE）
- データ品質チェック
  - 欠損値検出、スパイク検出（前日比閾値）、重複チェック、日付整合性チェック
  - 問題は QualityIssue オブジェクトで集約
- ニュース収集・NLP（AI）
  - RSS からのニュース収集（SSRF・サイズ制限・トラッキング除去など安全対策付き）
  - OpenAI を使った銘柄ごとのニュースセンチメントスコアリング（batch・リトライ・レスポンス検証）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの合成）
- 研究ユーティリティ
  - モメンタム / バリュー / ボラティリティ などのファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - z-score 正規化ユーティリティ
- 監査（Audit）/ トレーサビリティ
  - シグナル→発注→約定までを追跡する監査テーブル定義・初期化機能
  - order_request_id による冪等キー管理
- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定の検証、環境ごとのモード判定（development/paper_trading/live）

---

## 必要条件

- Python 3.10 以上（型注釈に `X | None` を使用）
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - typing（標準）
  - そのほか標準ライブラリのみで実装部分あり

（実際の requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン（またはソースを取得）

2. 仮想環境を作成して有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   - 簡易的なインストール例（必要なライブラリを個別にインストール）:
     ```
     pip install duckdb openai defusedxml
     ```
   - パッケージ化されている場合:
     ```
     pip install -e .
     ```

4. 環境変数を設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（必須と任意の概略）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
     - DUCKDB_PATH (任意, デフォルト data/kabusys.duckdb) — DuckDB ファイルパス
     - SQLITE_PATH (任意, デフォルト data/monitoring.db)
     - KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - OPENAI_API_KEY (必須 for AI calls) — OpenAI API キー

   - 例（.env）
     ```
     JQUANTS_REFRESH_TOKEN=あなたの_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

---

## 基本的な使い方（例）

以下はライブラリを使った主な処理のサンプルです。プロジェクト内のスクリプトやジョブで同様に呼び出します。

1) DuckDB 接続の取得（設定のパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行（株価 / 財務 / カレンダーの差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を指定することも可能
print(result.to_dict())
```

3) ニュースの AI スコアリング（前日15:00 JST〜当日08:30 JST のウィンドウ）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> OPENAI_API_KEY 環境変数を使用
print("書き込んだ銘柄数:", n_written)
```

4) マーケットレジームの判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ DB の初期化（監査テーブルを別 DB に分ける場合の例）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
```

6) RSS フィードの取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## スクリプト化・ジョブ実行のヒント

- 日次バッチ（cron / Airflow / Prefect 等）で run_daily_etl を実行し、その後 AI スコアリングやレジーム判定を順次実行するワークフローが想定されています。
- ETL では J-Quants 側のレート制限（120 req/min）やリトライを内部で管理します。長時間のページネーションが発生するケースも考慮してください。
- OpenAI 呼び出しはレスポンス検証とリトライを持ちますが、API キーや利用上限（コスト）に注意して運用してください。
- .env と .env.local の読み込み順序:
  - OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイル）

（実際のリポジトリは `src/kabusys` 配下に実装されています。ここでは主要モジュールを抜粋）

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP / OpenAI 呼び出し、score_news)
    - regime_detector.py (市場レジーム判定、score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、fetch/save 系)
    - pipeline.py (ETL パイプライン: run_daily_etl 等)
    - etl.py (ETLResult の再エクスポート)
    - calendar_management.py (市場カレンダー管理・営業日ロジック)
    - news_collector.py (RSS 取得・前処理)
    - quality.py (データ品質チェック)
    - stats.py (z-score 正規化等)
    - audit.py (監査ログスキーマ定義・初期化)
  - research/
    - __init__.py
    - factor_research.py (momentum/value/volatility 計算)
    - feature_exploration.py (forward returns, IC, summary, rank)
  - ai/、research/、data/ の各モジュールはそれぞれの責務を分離して提供します。

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアスを避けるため、各処理は内部で現在時刻を盲目的に参照せず、明示的な target_date を受け取る設計を採用しています（内部でも date < target_date のような条件が使われています）。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの厳密なバリデーションを行います。API エラー時はスコアを 0 にフォールバックするなどフェイルセーフ設計です。
- news_collector は SSRF 対策、XML の安全パーサ（defusedxml）、レスポンスサイズ制限などセキュリティ対策を組み込んでいます。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行われます。
- 監査ログは削除しない前提で運用され、order_request_id を冪等キーとして二重発注防止に利用できます。

---

## サポート / 開発時のヒント

- テスト時は環境変数自動読み込みを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）して、明示的に環境を制御すると安定します。
- OpenAI 呼び出しや外部 API へのアクセスは unittest.mock 等で _call_openai_api や _urlopen を差し替えてテスト可能です（コード内でもその点を想定した設計になっています）。
- DuckDB はファイルベースで軽量に使用でき、監査ログや時系列データの扱いに適しています。必要に応じて db ファイルを分離して運用してください（例: data/kabusys.duckdb, data/audit.duckdb）。

---

README に記載のない詳細（スキーマ定義や追加ユーティリティ、実運用ジョブの例など）はプロジェクトのドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。

何か追記したい項目や、具体的なコマンド/ジョブの例（systemd / cron / Airflow 実装例）を希望される場合は指示してください。