# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のモジュール群です。  
DuckDB を用いたデータパイプライン、J-Quants / RSS 収集、ニュースの NLP（OpenAI）、市場レジーム判定、ファクター計算、品質チェック、監査ログ等のユーティリティを含みます。

---

## 主な特徴（機能一覧）
- データ収集 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分で取得・保存
  - 差分取得・バックフィル・ページネーション・レートリミット・リトライ対応
- ニュース収集 & NLP
  - RSS からニュースを収集し raw_news に保存（SSRF 対策、トラッキング除去、重複排除）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（ai_scores）算出
  - マクロニュースを用いた市場レジーム判定（ma200 + macro sentiment の合成）
- 研究（Research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue レポート形式）
- マーケットカレンダー管理
  - market_calendar テーブルを元に営業日判定・前後営業日の検索・バッチ更新ジョブ
- 監査ログ（Audit）
  - signal → order_request → execution を辿れる監査テーブル（監査スキーマ初期化ユーティリティ）
- 設定管理
  - .env（.env.local）または環境変数から設定読み込み（自動ロード機能、無効化オプションあり）

---

## 必要要件（依存ライブラリ）
主要な依存（実行に必要なもの）:
- Python 3.9+
- duckdb
- openai
- defusedxml

その他プロジェクトや実行環境に応じて標準ライブラリ以外の追加パッケージが必要になる場合があります。適切に requirements.txt を用意して pip でインストールしてください。

例:
```
pip install duckdb openai defusedxml
```

---

## 環境変数 / .env について
パッケージ起動時、プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（必須やデフォルトあり）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot Token
- SLACK_CHANNEL_ID (必須) — Slack channel ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定で使用）

例 `.env`（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（例）
1. リポジトリをクローン
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt  （もし用意している場合）
   - または最低限: pip install duckdb openai defusedxml
4. .env を作成して環境変数を設定（上記テンプレート参照）
5. DuckDB/監査 DB 用ディレクトリを作る（必要に応じて）
   - mkdir -p data

注: パッケージは src レイアウトのため、開発時はリポジトリルートで以下を実行すると便利です:
```
pip install -e .
```
（setup の設定がある前提。無ければインポートパスに src を追加してください）

---

## 基本的な使い方（コード例）
以下はライブラリ API を直接呼ぶ簡単な例です。DuckDB 接続は duckdb.connect(...) を利用します。

- 日次 ETL の実行（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print(f"scored {n_written} codes")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

- 監査スキーマの初期化
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duckdb.db")
# または既存接続に対して:
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```

- マーケットカレンダー関連ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import next_trading_day, is_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- 各関数はルックアヘッドバイアスを避けるため内部で現在日時に依存しないよう設計されています（target_date を明示してください）。
- OpenAI 呼び出し時は API キー（api_key 引数 or OPENAI_API_KEY 環境変数）が必要です。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN を要します。

---

## テスト時の便利な設定
- 自動で .env を読み込む機能を無効にする:
  - 環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- AI 呼び出し等をモックするために各モジュール内の _call_openai_api 等を patch してテストできます（各モジュールに差し替えポイントあり）。

---

## ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys 配下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                            — 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py                         — ニュースセンチメント算出（OpenAI）
    - regime_detector.py                  — 市場レジーム判定（MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py                   — J-Quants API クライアント + 保存処理
    - pipeline.py                         — ETL パイプライン（run_daily_etl 等）
    - etl.py                              — ETLResult の公開
    - news_collector.py                   — RSS 収集 / 前処理 / raw_news 保存
    - calendar_management.py              — market_calendar 管理 / 営業日ロジック
    - stats.py                            — zscore_normalize 等の統計ユーティリティ
    - quality.py                          — データ品質チェック
    - audit.py                            — 監査ログスキーマ初期化／DB 初期化
  - research/
    - __init__.py
    - factor_research.py                  — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py               — 将来リターン/IC/統計サマリー 等

（上記以外にも execution / monitoring / strategy 等のパッケージ予備領域が __all__ に含まれる想定）

---

## 補足・設計方針（抜粋）
- Look-ahead バイアス防止: 各モジュールは内部で date.today() を直接参照せず、必ず target_date を受け取る設計になっています。
- 冪等性: J-Quants やニュースの保存は DB 側で ON CONFLICT / 明示的な PK チェックを行い冪等に保存します。
- フェイルセーフ: 外部 API 失敗時は可能な限りゼロ値でフォールバックし、全体処理を停止させない実装方針を採用しています（ログを残す）。
- セキュリティ: RSS の SSRF 対策、defusedxml による XML パース保護、公開される URL 正規化等が組み込まれています。

---

もし README に含めたい README に書き足すべき情報（例: license、CI / 開発フロー、具体的な requirements.txt の内容、実運用でのデプロイ手順など）があれば教えてください。必要に応じて追記します。