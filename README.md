# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株のデータプラットフォーム／リサーチ／自動売買に必要なコア機能群を提供する Python パッケージです。J-Quants API からのデータ取得、DuckDB によるデータ蓄積、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを含みます。

主な用途
- データ ETL（株価・財務・マーケットカレンダー）
- ニュースを用いた銘柄単位の AI センチメントスコアリング
- マーケットレジーム（bull/neutral/bear）判定
- 研究用ファクター計算・特徴量探索（IC、将来リターン等）
- 監査ログ（signal → order → execution のトレーサビリティ）

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数 / .env の自動読み込みと設定ラッパー（settings）
  - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- kabusys.data
  - jquants_client: J-Quants API クライアント（トークン自動リフレッシュ、レートリミット、リトライ、DuckDB 保存）
  - pipeline: 日次 ETL を統括（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl 等）
  - calendar_management: マーケットカレンダー管理 / 営業日判定ユーティリティ
  - news_collector: RSS 収集（SSRF対策／トラッキング除去／前処理）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマの初期化・監査 DB 操作
  - stats: 汎用統計ユーティリティ（zscore_normalize など）

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA200 とマクロニュース（LLM）を合成して market_regime に書き込む

- kabusys.research
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー、ランク関数等

---

## 必要要件（例）

このリポジトリは通常 Python パッケージとして管理されます。主要な依存例は以下です（プロジェクトの pyproject.toml / requirements.txt を参照してください）:

- Python 3.9+（コード内の型ヒントに合わせて適宜）
- duckdb
- openai
- defusedxml

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# パッケージを editable インストールする場合
pip install -e .
```

---

## 環境変数（必須・推奨）

KabuSys は以下の環境変数を参照します（settings からアクセス可能）。

必須（実行機能により異なる）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client にて使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（Slack 機能を使う場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabuステーション API パスワード（発注等を行う場合）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / regime_detector を使う場合）

任意 / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に "1" を設定
- KABUSYS_ENV 関連: settings.is_live / is_paper / is_dev を利用可能

.env ファイルの優先順位:
- OS 環境変数 > .env.local > .env
- .env はプロジェクトのルート（.git または pyproject.toml があるディレクトリ）から自動読み込みされます

簡単な .env サンプル（実際の値は環境に合わせて設定してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし、仮想環境を用意
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

2. 依存ライブラリをインストール
   ```bash
   pip install duckdb openai defusedxml
   # その他プロジェクト依存があれば requirements.txt / pyproject.toml に従ってインストール
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作り、上記の必須値を記載する
   - 自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する

4. DuckDB データベースファイルの準備（デフォルト）
   - settings.duckdb_path のデフォルトは `data/kabusys.duckdb`
   - ディレクトリがなければ自動作成されるモジュールもありますが、手動で用意しておくと安心です

---

## 使い方（コード例）

以下は主要な機能の利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- ETL（日次パイプライン）を実行する:
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP による銘柄スコアリング:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(Settings().duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # APIキーは環境変数 OPENAI_API_KEY から取得
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB 初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring.db")  # ":memory:" でも可
# これで signal_events / order_requests / executions テーブル等が作成されます
```

- 営業日判定や次営業日の取得:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI を使う機能は OPENAI_API_KEY が必要です（関数引数で明示的に api_key を渡すことも可）。
- J-Quants API を使う機能は JQUANTS_REFRESH_TOKEN が必須です。

---

## 主要関数と戻り値（抜粋）

- data.pipeline.run_daily_etl(...) -> ETLResult
  - ETLResult.to_dict() で実行概要・品質問題等を取得可能

- ai.news_nlp.score_news(conn, target_date, api_key=None) -> int
  - 書き込んだ銘柄数を返す。API 失敗時はスキップして継続する設計。

- ai.regime_detector.score_regime(conn, target_date, api_key=None) -> int
  - market_regime テーブルへ書き込み（1 を返す）

- data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(...)
  - J-Quants からの取得・DuckDB への保存を実装

- data.audit.init_audit_db(path) -> duckdb connection
  - 監査スキーマを作成して接続を返す

---

## ディレクトリ構成（概要）

プロジェクトは src/kabusys 配下に実装されています。主なファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定 / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存
    - pipeline.py            — ETL パイプライン（run_daily_etl 他）
    - calendar_management.py — マーケットカレンダー／営業日ユーティリティ
    - news_collector.py      — RSS 収集・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ初期化 / init_audit_db
    - etl.py                 — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

（上記は実装ファイルの要約です。詳細はそれぞれのモジュールの docstring を参照してください。）

---

## 注意点 / 運用上のヒント

- ルックアヘッドバイアス対策: 多くの関数は date.today() を内部で参照しない設計（target_date を明示）になっており、バックテスト時のデータ分離に配慮しています。
- OpenAI 呼び出し: レスポンスのパースや API 失敗時のフォールバック（0.0 にする等）を実装しており、フェイルセーフを重視しています。
- J-Quants API: レート制限・リトライ・トークン自動リフレッシュが実装されています。API トークンは JQUANTS_REFRESH_TOKEN を設定してください。
- 自動 .env 読み込み: プロジェクトルート（.git か pyproject.toml を基準）から .env/.env.local を自動で読み込みます。テスト中に自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- テスト・モック: OpenAI 呼び出しや外部ネットワーク呼び出しは関数単位で差し替え（モック）しやすい設計になっています（テスト時は各 _call_openai_api などを patch できます）。

---

## 補足 / 参考

- 各モジュールの docstring に詳細な設計方針・処理フロー・フェイルセーフが記載されています。実装の意図や注意点はそちらを参照してください。
- 実運用（本番）では settings.is_live / is_paper を活用し、発注ロジックの有効化やログレベルを制御してください。
- セキュリティ: news_collector は SSRF 対策や XML デシリアライズの安全化（defusedxml）を実装していますが、運用時はさらにネットワーク制限や監査を行ってください。

---

必要であれば、以下の内容を追加で作成できます:
- 詳細なセットアップスクリプト（docker-compose / systemd / cron 用）
- CI 用のテスト例（pytest 用モック例）
- サンプル .env.example ファイル

ご希望があればどれを追加するか教えてください。