# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集、AIによるニュース/レジーム判定、ファクター計算、監査ログなどを含むモジュール群を提供します。

主な目的は「バックテストや研究に耐えるデータ基盤」と「本番/ペーパートレードでの運用に使える監査・実行基盤」の両立です。

---

## 主な機能一覧

- データ収集・ETL
  - J-Quants API から株価（OHLCV）、財務データ、上場銘柄情報、JPXカレンダーを取得・保存
  - 差分取得、ページネーション、リトライ、レートリミット制御を実装
- データ品質チェック
  - 欠損値、重複、スパイク、日付不整合の検査
- ニュース収集
  - RSS フィードの取得、URL 正規化、SSRF対策、前処理、raw_news への冪等保存
- AI（OpenAI）連携
  - ニュース記事を銘柄ごとにスコアリング（news_nlp.score_news）
  - ETF MA とマクロニュースのセンチメントを組合せた市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しはリトライ・フェイルセーフ実装
- リサーチ / ファクター処理
  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマン）計測、Zスコア正規化、統計サマリー
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 までトレース可能な監査テーブルの初期化・管理
  - DuckDB ベースで冪等的にスキーマ構築
- 設定管理
  - .env / 環境変数自動読み込み（プロジェクトルート基準、.env.local 上書き）
  - 必須・任意設定を Settings クラスで提供

---

## 要求環境 / 依存パッケージ（代表例）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- 標準ライブラリ（urllib, json, datetime など）

（実際のインストールはプロジェクトの pyproject.toml / requirements.txt に従ってください。）

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトルートに pyproject.toml / requirements.txt があればそれに従ってください）
4. 環境変数 / .env を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
5. DuckDB データベースファイルのディレクトリを作成（必要な場合）
   - デフォルトは `data/kabusys.duckdb`（settings.duckdb_path）

---

## 必須 / 推奨環境変数（.env 例）

以下は本コードが参照する主な環境変数の例です。必須項目は Settings クラスで参照され、未設定時はエラーになります。

.env の例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション（発注用）
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL はオプション（デフォルト: http://localhost:18080/kabusapi）
# KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知等)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# OpenAI (AI スコアリング用)
OPENAI_API_KEY=sk-...

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development    # development | paper_trading | live
LOG_LEVEL=INFO
```

※ 自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。

---

## 使い方（代表的な呼び出し例）

以下は主要なモジュールを簡単に使うためのサンプルコードです。実行は Python スクリプトや REPL 上で行います。

- DuckDB 接続と ETL 実行（日次ETL）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP による銘柄スコア生成
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境に設定しておく
print("scored:", count)
```

- 市場レジーム判定（ETF 1321 ベース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算 / リサーチユーティリティ
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルとインデックスが生成されます
```

- RSS フィード取得（ニュース収集ヘルパ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 設定と自動 .env 読み込みの挙動

- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）を基準に行うため、カレントワークディレクトリに依存しません。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Settings クラスは必須キーが未設定の場合に ValueError を発生させます（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。

---

## 主要ディレクトリ構成

（プロジェクトの src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py    — 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - etl.py                — ETLResult の再エクスポート
    - news_collector.py     — RSS 収集・前処理
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン/IC/統計サマリー

---

## 注意点・設計方針メモ

- ルックアヘッドバイアス防止
  - ほとんどの処理は `date` / `target_date` を明示的に受け取り、内部で date.today() に依存しない設計になっています。バックテスト用途に配慮した作りです。
- フェイルセーフ
  - 外部 API（OpenAI / J-Quants）呼び出しはリトライやフォールバックを備え、可能な限り一部障害でも処理継続する実装です。
- 冪等性
  - DuckDB への保存は ON CONFLICT / UPDATE / 個別 DELETE → INSERT 等で冪等性を保つよう設計されています。
- セキュリティ
  - RSS収集に対する SSRF 対策、defusedxml の利用、OpenAI 呼出し時の JSON モード利用などを取り入れています。ただし運用時は追加のセキュリティ対策・監査を行ってください。

---

## 開発 / テスト / 貢献

- 新しい機能の追加やバグ修正はモジュール単位でのユニットテスト追加を推奨します（外部 API 呼び出しはモックしてテストすること）。
- 環境変数の自動読み込みはテストで邪魔になる場合があるため、テスト実行時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると良いです。

---

必要であれば README により具体的なコマンド例（セットアップスクリプト、systemd / cron 用の起動例、CI 設定例）や、pyproject.toml / packaging によるインストール方法の章を追加します。どの情報を補足しますか？