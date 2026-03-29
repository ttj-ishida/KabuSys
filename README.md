# KabuSys

日本株向けのデータプラットフォーム・リサーチ・自動売買支援ライブラリです。  
J-Quants API を用いたデータ ETL、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（トレーサビリティ）、市場カレンダー管理、そして簡易な AI を用いた市場レジーム判定など、バックテスト／運用に必要な基盤機能を提供します。

主に DuckDB をデータストアとして使用し、OpenAI（gpt-4o-mini）をニュースセンチメントやマクロ評価に利用する設計になっています。

---

目次
- プロジェクト概要
- 機能一覧
- 必要環境・依存
- セットアップ手順
- 環境変数（.env）一覧
- 使い方（簡単なコード例）
- ディレクトリ構成（概要）
- 補足・注意事項

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群をまとめたライブラリです。

- J-Quants API からのデータ取得（株価・財務・上場情報・市場カレンダー）
- ETL パイプライン（差分取得・冪等保存・品質チェック）
- ニュース収集（RSS）と NLP による銘柄別センチメント算出（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価を合成）
- 研究（ファクター計算・将来リターン・IC 等）
- 監査ログ（signal → order_request → execution までトレースできるスキーマ）
- マーケットカレンダー管理（営業日判定・前後営業日取得）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計方針として「バックテスト時のルックアヘッドバイアス防止」「ETL の冪等性」「API エラーに対するフェイルセーフ」「DuckDB による高速な列志向処理」を重視しています。

---

## 機能一覧（主要）

- data/
  - jquants_client: J-Quants API 呼び出し、保存ロジック（レートリミット・リトライ・トークン自動更新）
  - pipeline: 日次 ETL（prices, financials, calendar）と ETLResult
  - news_collector: RSS 取得・正規化・保存（SSRF/サイズ/署名対策）
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - calendar_management: 営業日判定・next/prev/get_trading_days・calendar 更新ジョブ
  - audit: 監査ログスキーマ初期化・監査 DB 作成ユーティリティ
  - stats: z-score 正規化など共通統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM に投げ、ai_scores を書き込む
  - regime_detector.score_regime: ETF（1321）200日 MA とマクロニュース LLM を合成して market_regime を書き込む
- research/
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリーなどの解析ユーティリティ
- config: 環境変数管理（.env の自動読み込み・必須変数チェック）
  
---

## 必要環境・依存

- Python 3.10+（型ヒントの Union 表記やタプル型注釈が使われています）
- 主な依存ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib 等）を広く使用

（実際の requirements.txt がある場合はそれを参照してください。ない場合は pip で上記をインストールしてください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

3. 依存ライブラリをインストール
   ```bash
   pip install duckdb openai defusedxml
   # または requirements.txt があれば
   # pip install -r requirements.txt
   ```

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成してください。
   - 自動で .env を読み込む機能が有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数は後述の「環境変数一覧」を参照してください。

5. DuckDB 接続ファイルの準備
   - デフォルトの DuckDB パスは `data/kabusys.duckdb`（settings.duckdb_path）。
   - 監査ログ専用 DB を初期化するには後述の使用例を参照。

---

## 環境変数（.env）一覧（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabu ステーション API 用パスワード
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack チャンネル ID
- 任意 / デフォルトあり
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - KABUSYS_ENV: development / paper_trading / live（default: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（default: INFO）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
- 自動読み込み
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` → `.env.local` を順に読み込みます。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## 使い方（主要な例）

以下は最小限の呼び出し例です。各関数は DuckDB 接続を受け取る設計になっています。

- DuckDB 接続を作って ETL を実行する（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使いたい場合:
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())  # ETL の結果概要
```

- ニュース NLP スコアリング（OpenAI API キーが環境変数 OPENAI_API_KEY に設定されていること）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))  # api_key を直接渡すことも可能
print(f"書き込んだ銘柄数: {count}")
```

- 市場レジーム判定（1321 の MA + マクロニュース LLM）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- J-Quants から日次株価を直接フェッチする
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# get_id_token() は settings.jquants_refresh_token を使用して id_token を取得
records = fetch_daily_quotes(date_from=..., date_to=...)
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋した構成）

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
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (コードベースに監視関連が予定されていることを示唆)
  - execution/ (発注/ブローカー連携は別モジュールとして想定)

（上記は本リードミー作成時点の主要モジュールです。詳細なファイルはリポジトリを参照してください。）

---

## 補足・注意事項

- 環境変数の自動読み込みは .env / .env.local をプロジェクトルートから読み込みます。CI やユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。
- AI（OpenAI）呼び出しではリトライ・タイムアウト処理を行いますが、API キーやレート制御は実運用で十分な管理が必要です。
- ETL やスキーマ操作（監査スキーマの初期化）はデータベース上の操作なのでバックアップや注意の上で実行してください。
- 本ライブラリは DuckDB を前提としていますが、監査 DB は別ファイルに分けることが可能です（init_audit_db）。
- セキュリティ考慮:
  - news_collector は SSRF 対策、レスポンスサイズ制限、XML パース時の安全化（defusedxml）を実装しています。
  - jquants_client はトークン自動リフレッシュとレート制御を実装しています。

---

問題の報告や改善提案がある場合は、リポジトリの Issue を作成してください。必要であれば README に含める追加情報（例: CI の設定、より詳細な実行手順、サンプル .env.example）を追記します。