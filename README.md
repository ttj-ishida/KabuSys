# KabuSys

日本株の自動売買・データプラットフォーム用ライブラリ群。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（DuckDB）、
市場カレンダー管理、品質チェック、研究用ユーティリティ等を提供します。

バージョン: 0.1.0

---

## 主要機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXマーケットカレンダー取得
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得（バックフィル対応）・保存（冪等/ON CONFLICT）・品質チェック
  - 日次 ETL のエントリポイント（run_daily_etl）
- ニュース収集（RSS）
  - URL 正規化、SSRF対策、トラッキングパラメータ除去、前処理、raw_news への冪等保存設計（news_collector）
- ニュース NLP / AI
  - OpenAI（gpt-4o-mini）によるニュースセンチメント付与（score_news）
  - マクロニュースとETF MA200乖離を合成して市場レジーム判定（score_regime）
  - JSON Mode を使った堅牢な入出力・リトライ設計
- 研究用ユーティリティ（research）
  - モメンタム/ボラティリティ/バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化
- データ品質チェック（quality）
  - 欠損、重複、スパイク、日付不整合などを検出して QualityIssue リストで返す
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル初期化・DB化（DuckDB）
  - UUID・冪等キー設計、UTC タイムスタンプポリシー

---

## 必要条件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
  - （その他：標準ライブラリのみで実装されている部分多数）

依存はプロジェクトの pyproject.toml / requirements.txt を参照してインストールしてください。

---

## インストール

開発中パッケージとしてローカルにインストールする例:

```bash
# プロジェクトルートで
python -m pip install -e .
# または必要な依存のみインストール
python -m pip install duckdb openai defusedxml
```

---

## 環境変数（.env）

パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、jquants_client.get_id_token で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必要に応じて）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必要に応じて）
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID
- OPENAI_API_KEY: OpenAI API キー（AI機能を使う場合必須）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite path（例: data/monitoring.db）
- KABUSYS_ENV: environment を指定（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）

例 `.env`:

```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（簡易）

1. リポジトリをチェックアウトし、依存をインストールする。
2. `.env` を作成して必要なトークン等を設定する。
3. DuckDB ファイルを作る（必要に応じて）：
   - 監査ログ専用 DB を作成する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用 DuckDB（あらかじめスキーマを作る想定）:
     - schema 初期化ユーティリティが別途ある想定（ここでは ETL が期待するテーブルが存在すること）

4. J-Quants / OpenAI の API キーを `.env` に格納。

---

## 使い方（代表的な API）

以下は Python インタプリタやスクリプト内で利用する例です。

- 日次 ETL 実行（run_daily_etl）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコア付与（score_news）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にあるか、api_key に文字列を渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- 市場レジーム判定（score_regime）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログDB初期化（init_audit_db / init_audit_schema）:

```python
from kabusys.data.audit import init_audit_db, init_audit_schema
# ファイル DB を作成してテーブルを初期化
conn = init_audit_db("data/audit.duckdb")
# 既存 connection に対してスキーマを追加する場合
init_audit_schema(conn, transactional=True)
```

- ニュース RSS 取得（単体テストや収集に）:

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 研究系ユーティリティの利用例:

```python
from kabusys.research.factor_research import calc_momentum
conn = duckdb.connect("data/kabusys.duckdb")
res = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(res, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- score_news / score_regime は OpenAI API キーが必要です（引数で渡すか環境変数 OPENAI_API_KEY を使用）。
- ETL / J-Quants は J-Quants トークンが必要です（JQUANTS_REFRESH_TOKEN）。

---

## 設定・挙動に関する補足

- 自動 .env ロード
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env で上書きされません。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 環境値検証
  - KABUSYS_ENV は development / paper_trading / live のいずれかで検証されます。
  - LOG_LEVEL は標準的なログレベルのみ許容されます。

- LLM 呼び出しの設計
  - OpenAI の呼び出しは JSON Mode を利用し、リトライ（429・ネットワーク・5xx）やパースエラーに対するフォールバックを持ちます。
  - テスト容易性のため、内部の API 呼び出し関数をモックできるように分離されています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは `src/kabusys` 配下に主要モジュールを配置しています。主なファイル一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数/設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLU / score_news
    - regime_detector.py     -- マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch/save 等）
    - pipeline.py            -- ETL パイプライン / run_daily_etl / ETLResult
    - etl.py                 -- ETL インターフェース再エクスポート
    - news_collector.py      -- RSS ニュース収集
    - calendar_management.py -- 市場カレンダー管理
    - quality.py             -- データ品質チェック
    - stats.py               -- 汎用統計ユーティリティ
    - audit.py               -- 監査ログスキーマ・初期化
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム/ボラ/Bal 等
    - feature_exploration.py -- 将来リターン/IC/summary 等
  - ai/、data/、research/ の下に多数の補助関数・モジュールが含まれます。

---

## 開発・テスト

- 各種ネットワーク依存（J-Quants / OpenAI / RSS）を含むため、ユニットテストでは依存関数をモックして実行することを推奨します（コード内にも unittest.mock.patch で差し替え可能な仕組みが記載されています）。
- 自動ロードされる `.env` をテストで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ライセンス / 貢献

- 本 README にはライセンス情報を含めていません。実際のプロジェクトでは LICENSE ファイル等を参照してください。
- 貢献は Pull Request / Issue の形で行ってください（プロジェクト運用ルールに従ってください）。

---

以上がこのコードベースの概要・セットアップ・使い方のまとめです。README に追加したい具体的な手順（例: DB スキーマ初期化 SQL、cron / Airflow 用のジョブ例、より詳しい .env.example）や、想定される実行コマンド（CLI）等があれば教えてください。必要に応じて追記します。