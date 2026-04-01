# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤ライブラリです。  
J-Quants / RSS / OpenAI を組み合わせてデータ収集・品質チェック・AIセンチメント評価・市場レジーム判定・監査ログの管理までをサポートします。

主な用途:
- 日次 ETL（株価・財務・カレンダー）と品質チェック
- ニュースを用いた銘柄ごとの AI センチメントスコア算出
- マクロ＋テクニカルを統合した市場レジーム判定
- 監査ログ（signal → order → execution）のスキーマ初期化と運用ユーティリティ
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ）と統計ユーティリティ

バージョン: 0.1.0

---

## 機能一覧

- 環境変数・設定管理（.env 自動ロード、保護付き上書き）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得・保存（ページネーション・リトライ・レート制御）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
- ETL パイプライン（差分取得・backfill・品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）と前処理（SSRF対策・トラッキングパラメータ除去）
- OpenAI を使ったニュース NLP（銘柄別センチメント、チャンクバッチ送信・検証・リトライ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- 研究用ファクター計算と統計ユーティリティ（Zスコア正規化等）
- 監査ログスキーマ定義・初期化ユーティリティ（DuckDB）

---

## セットアップ

前提:
- Python 3.10+（型注釈の union operator 等を使用）
- DuckDB が動作する環境
- ネットワーク: J-Quants / OpenAI / RSS にアクセス可能であること

推奨インストール（例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# その他、プロジェクトの依存があれば requirements.txt を用意して pip install -r requirements.txt
```

環境変数（.env ファイル推奨）:
必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API のパスワード（発注等を行う場合）
- SLACK_BOT_TOKEN        — Slack 通知を行うボットトークン
- SLACK_CHANNEL_ID       — Slack の通知先チャンネルID

OpenAI 関連（関数呼び出し時に api_key 引数で注入可能）:
- OPENAI_API_KEY         — OpenAI API キー（gpt-4o-mini を利用）

（任意、デフォルトあり）
- KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 .env（README 用サンプル）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は最小限の利用例（Python スクリプト）です。DuckDB 接続には標準の duckdb.connect を使用します。

1) 日次 ETL を実行する（株価・財務・カレンダー・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（銘柄別 AI スコア）を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数か api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

3) 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DuckDB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# スキーマが作成され、UTC タイムゾーンが設定される
```

5) RSS を取得して raw_news に保存するワークフローは news_collector モジュールを参照してください。
（fetch_rss 関数は RSS フィードをパースして NewsArticle 型を返します。DB保存は別機能で実施します。）

注意点:
- OpenAI 呼び出しは API の制限/コストがあるため、開発時は小さなバッチでテストしてください。
- J-Quants の取得はレート制限（120 req/min）に従うよう組み込まれています。
- ETL/AI 周りは「ルックアヘッドバイアス」対策が設計に反映されています（target_date 指定、取得窓の排他条件など）。

---

## モジュール・ディレクトリ構成

パッケージルート: src/kabusys

主要ファイル・サブパッケージ:
- kabusys/__init__.py
- kabusys/config.py
  - 環境変数・.env 自動ロード・Settings クラス
- kabusys/ai/
  - __init__.py
  - news_nlp.py        — ニュースの AI センチメント算出（銘柄別）
  - regime_detector.py — ETF + マクロセンチメントを用いた市場レジーム判定
- kabusys/data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント + DuckDB 保存ユーティリティ
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETL 結果データクラス再エクスポート（ETLResult）
  - calendar_management.py— 市場カレンダー管理（営業日判定・更新ジョブ）
  - news_collector.py     — RSS 収集・前処理（SSRF 対策・記事ID生成）
  - quality.py            — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py              — 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py              — 監査ログスキーマ定義・初期化
- kabusys/research/
  - __init__.py
  - factor_research.py    — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py— 将来リターン計算・IC・factor_summary・rank 等

ツリービュー（概要）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ etl.py
│  ├─ calendar_management.py
│  ├─ news_collector.py
│  ├─ quality.py
│  ├─ stats.py
│  └─ audit.py
└─ research/
   ├─ __init__.py
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## 実運用・セキュリティ上の注意

- シークレット（API トークン等）は .env に保存する場合、アクセス権を適切に管理してください。
- news_collector は SSRF 対策・レスポンスサイズ制限等を実装していますが、実運用の RSS ソースは慎重に選定してください。
- OpenAI / J-Quants の API 呼び出しは課金やレート制限を発生させるため、開発時はモックやテストキーを利用してください。
- DuckDB のファイルは定期バックアップ、アクセス制御を行ってください。
- kabuステーション等ブローカーAPIに接続して実際に発注を行う機能を利用する場合は、paper_trading 環境や十分なリスク管理を実施してください（KABUSYS_ENV=paper_trading をサポート）。

---

## 貢献・拡張

- テスト: 各モジュールは外部依存（HTTP や OpenAI）を抽象化しており、ユニットテストで差し替え（モック）しやすく設計されています。
- 拡張候補:
  - 追加のニュースソース統合や言語処理の高度化
  - strategy / execution / monitoring レイヤー（README 上部 __all__ に記載あり、将来的に実装）
  - CLI / Scheduler の追加（cron / Airflow 連携）

---

必要であれば README に「実行例の詳細」「.env.example ファイル」「依存関係の固定（requirements.txt）」「テスト実行方法（pytest）」などの追記も可能です。どの情報がさらに必要か教えてください。