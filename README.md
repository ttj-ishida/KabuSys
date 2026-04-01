# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ。  
J-Quants / JPX / RSS / OpenAI 等を組み合わせて、データ取得（ETL）・品質チェック・ニュース NLP・市場レジーム判定・監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの研究・運用向けユーティリティ群をまとたパッケージです。主に以下を提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得・DuckDB 保存（ETL）
- ニュース収集（RSS）と OpenAI を使った銘柄単位のニュースセンチメントスコアリング
- マクロ + ETF（1321）の MA200 乖離 を使った日次市場レジーム判定（LLM と併用）
- ファクター計算 / 特徴量探索（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal / order_request / executions）用スキーマ初期化ユーティリティ
- 環境変数ベースの設定管理（.env 自動ロードをサポート）

設計上の特徴として、ルックアヘッドバイアスを避けるため日時の決定に date.today()/datetime.today() を不用意に参照しない、安全対策（SSRF や XML 脆弱性対策）、API 呼び出しの堅牢なリトライやフェイルセーフが組み込まれています。

---

## 主な機能一覧

- data/
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: API 呼び出し（ページネーション・レート制御・トークン自動リフレッシュ）
  - market calendar 管理・判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - news_collector: RSS 収集・正規化・raw_news 保存（SSRF/サイズ制限/トラッキング除去）
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログ用スキーマ初期化・専用 DB 初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント生成（gpt-4o-mini を想定）
  - regime_detector.score_regime: ETF(1321) MA200 乖離 + マクロニュース LLM を合成した市場レジーム判定
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings: 環境変数経由の設定管理（.env 自動ロード、各種パス・閾値等）

---

## 要件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai (OpenAI の新しい SDK を利用する想定)
- defusedxml
- （標準ライブラリで多くをまかなっていますが、ネットワーク・DB操作に必要なパッケージを事前にインストールしてください）

実行環境依存やバージョンはリポジトリの pyproject.toml / requirements.txt がある場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （実プロジェクトでは pip install -e . や requirements.txt を利用してください）

4. 環境変数 / .env の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化可能）。

必須の環境変数（少なくとも設定しておくもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合
- その他（任意/デフォルトあり）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト）

例 .env (プロジェクトルート)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単なコード例）

以下は Python REPL やスクリプトから主要機能を呼ぶ例です。

- 設定値にアクセスする
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB 接続を作り ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))  # settings は上で取得
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（AI）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（AI + MA200）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンにセットされます
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意:
- score_news と score_regime は OpenAI API を使用します。環境変数 OPENAI_API_KEY を設定するか、api_key 引数で渡してください。
- ETL / jquants_client は J-Quants の認証トークン（JQUANTS_REFRESH_TOKEN）を必要とします。

---

## 重要な設計注意点 / 運用メモ

- .env 自動ロード:
  - プロジェクトルートの .env / .env.local が自動的に読み込まれます（OS 環境変数が優先）。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ルックアヘッドバイアス対策:
  - 多くの関数は target_date を明示的に受け取り、date.today()/datetime.today() に依存しない実装です。バックテスト用途では target_date を明示して使用してください。
- 外部 API の堅牢性:
  - J-Quants クライアントはレート制御・リトライ・401 時のリフレッシュ機構を備えています。
  - OpenAI 呼び出しはリトライ/フェイルセーフ処理が入っていますが、API キーやコスト制御は運用側で行ってください。
- セキュリティ:
  - RSS 取得では SSRF 対策、XML パースでは defusedxml を使用しています。
  - news_collector はレスポンス最大サイズを制限し、URL の正規化・トラッキング除去を実施します。

---

## ディレクトリ構成（抜粋）

プロジェクトの主なファイル/ディレクトリ構成（src/kabusys 以下）:

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
    - stats.py
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - ...
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター計算・特徴量探索）
  - research/__init__.py
  - (その他 strategy / execution / monitoring 等のパッケージが想定されます)

---

## 開発・テストについて

- モジュールは外部サービス呼び出しを行う箇所があるため、ユニットテストでは OpenAI 呼び出し・HTTP 通信・jquants_client のネットワーク部分をモックして検証することを推奨します（コード中にモック差し替えのためのパス指定が行われている箇所があります）。
- DuckDB を使ったテストは ":memory:" 接続を用いることでローカルのファイルを汚さずに実行できます。

---

ご不明点や README に追加したい情報（例: インストール可能なパッケージ一覧、CI 設定、実運用時の推奨設定など）があれば追加します。