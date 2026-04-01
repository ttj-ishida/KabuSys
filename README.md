# KabuSys

日本株のデータ基盤・リサーチ・自動売買のための Python ライブラリ群です。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース収集・NLP（OpenAI）による銘柄センチメント評価、リサーチ用ファクター計算、監査ログ（発注→約定のトレース）などの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得（J-Quants API 経由）
  - 株価日足（OHLCV）、財務データ、上場銘柄一覧、JPX カレンダー など（ページネーション対応）
  - レートリミット / リトライ / トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを一貫実行
  - 品質チェックは欠損・スパイク・重複・日付不整合を検出
- ニュース収集と NLP
  - RSS から記事を収集し raw_news / news_symbols に保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（score_news）
  - マクロニュースと ETF の MA200 を融合した市場レジーム判定（score_regime）
- リサーチ用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン、IC（Information Coefficient）、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions のテーブル定義と初期化
  - order_request_id による冪等性、UTC タイムスタンプポリシー

---

## 必要条件（想定）

- Python 3.10+
- 外部ライブラリ（一例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

requirements.txt の例（プロジェクトに合わせて調整してください）:
```text
duckdb
openai
defusedxml
```

---

## 環境変数 / 設定

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。  
必須の環境変数（Settings クラスで参照）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD : kabuステーション API 用パスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack チャネル ID

オプション（デフォルトあり）:

- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV, LOG_LEVEL

.env の例:
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - （install optional）pip install duckdb openai defusedxml
4. .env を作成して必要な環境変数を設定
5. DuckDB ファイルやディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な API 例）

以下はライブラリをインポートして利用する基本例です。実行時には settings（環境変数）や OpenAI / J-Quants の認証情報が必要です。

- DuckDB 接続の取得（例）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key が None の場合 OPENAI_API_KEY を使う
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
res = score_regime(conn, target_date=date(2026, 3, 20))
print("score_regime returned:", res)
```

- 監査ログ用 DB 初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)  # テーブルを作成して接続を返す
```

- RSS フィード取得（news_collector.fetch_rss の例）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意:
- OpenAI 呼び出しは API レート・コストが発生します。テスト時はモックを利用してください。
- ETL / save 系関数は DuckDB のテーブルスキーマが前提です。事前にスキーマ定義（data.schema 等）を用意してください（本コードベースの schema 定義は別途実装を想定）。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys/ 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py  -- 環境変数・Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py        -- ニュースセンチメント解析（OpenAI）
    - regime_detector.py -- マクロ + ETF MA200 を用いた市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py -- 市場カレンダー操作・営業日判定
    - pipeline.py            -- ETL 実行のメインロジック（run_daily_etl等）
    - etl.py                 -- ETLResult エクスポート
    - jquants_client.py      -- J-Quants API クライアント（fetch/save 系）
    - news_collector.py      -- RSS 収集と前処理
    - quality.py             -- データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py               -- z-score 正規化等統計ユーティリティ
    - audit.py               -- 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     -- Momentum/Value/Volatility 等ファクター算出
    - feature_exploration.py -- 将来リターン、IC、統計サマリーなど

---

## 設計方針・注意点（抜粋）

- ルックアヘッドバイアス防止:
  - 各モジュール（news_nlp, regime_detector, pipeline 等）は内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DB クエリでは target_date 未満（排他）や適切なウィンドウ指定を行い、テストやバックテストでの再現性を重視。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）失敗時は、可能な限り部分的に継続するように設計（例えば macro_sentiment のフォールバックは 0.0）。
- 冪等性:
  - DuckDB への保存は可能な箇所で ON CONFLICT DO UPDATE / DO NOTHING を使用して冪等化。
- セキュリティ:
  - news_collector は SSRF 対策（ホストのプライベート判定、リダイレクト検査）や defusedxml による XML パース防御を実装。
- ロギング:
  - 各モジュールは logger を利用して処理状況を出力。運用時には LOG_LEVEL を設定してください。

---

## 開発・テスト

- 単体テストは各モジュールの入出力を分離してモックを利用して実行することを想定しています（例: OpenAI 呼び出し・ネットワークアクセスを unittest.mock.patch で差し替え）。
- DB を使うテストは :memory: の DuckDB を使うと簡便です。

---

必要に応じて README を拡張します。導入手順（schema の生成や初回 ETL 実行、Slack 通知設定、kabuステーション連携など）について詳しく追記できますので、追加で必要な項目があれば教えてください。