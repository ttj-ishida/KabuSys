# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買のためのライブラリ群です。  
DuckDB をデータレイクとして用い、J-Quants からのデータ取得・ETL、ニュースの収集・NLP スコアリング、ファクター計算、監査ログ（トレーサビリティ）などを通して、研究〜運用までのワークフローをサポートします。

バージョン: 0.1.0

---

## 主な機能

- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー、上場銘柄情報の取得と DuckDB への冪等保存
  - レート制御、リトライ、トークン自動リフレッシュ対応

- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）の実行
  - 差分更新・バックフィル機能、品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集・NLP
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた記事/銘柄単位のセンチメントスコアリング（バッチ処理、リトライ、レスポンス検証）
  - マクロニュースを利用した市場レジーム判定（ETF 1321 の MA200 乖離 + LLM センチメントの合成）

- リサーチ（ファクター計算）
  - モメンタム / バリュー / ボラティリティ等の定量ファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）や統計サマリー
  - Z スコア正規化ユーティリティ

- カレンダー管理
  - JPX カレンダー取得、営業日判定、次/前営業日の算出、期間内営業日取得
  - DB の有無に応じた曜日ベースのフォールバック

- 監査ログ（Audit）
  - signal → order_request → execution の階層的トレーサビリティ用テーブル／インデックスの初期化
  - DuckDB に監査用 DB を作成するユーティリティ

---

## セットアップ

前提
- Python 3.10+（typing の union 型等を想定）
- ネットワーク接続（J-Quants / OpenAI を利用する場合）
- DuckDB（Python パッケージとしてインストール）

1. リポジトリをクローン / コピー

2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt がある場合はそれを利用してください。実装内で他の標準パッケージも使用していますが、上記は主要な外部依存です。）

4. パッケージとしてインストール（開発）
   pip install -e .

5. 環境変数設定
   プロジェクトルートの .env または .env.local に必要な環境変数を定義できます。パッケージ起動時に自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

推奨する環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必要に応じて）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: データベースファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視等に使う sqlite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: development|paper_trading|live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

例（.env）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要ユーティリティ例）

以下は簡単な Python スニペット例です。実行前に環境変数を設定してください。

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニューススコア算出（score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されていれば api_key は不要
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。テーブルが作成されている。
```

- ニュース RSS 取得（単体）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- J-Quants からの直接データ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # 環境変数から JQUANTS_REFRESH_TOKEN を使って取得
records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
```

注意点
- AI 関連関数（score_news / score_regime）は OpenAI API に依存します。API キーが必要です。
- ETL/保存系は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, etc.）を前提としています。事前にスキーマ初期化しておくか、ETL を実行して自動で作成される運用に合わせてください。
- 自動 .env ロードはパッケージ import 時に実行されます。テスト時に無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル・モジュール）

プロジェクトの主要なソースは src/kabusys/ 以下にあります。重要なモジュールを抜粋します。

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数のロードと Settings クラス（各種設定の取得）
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py         - ニュースの LLM センチメントスコアリング（score_news）
  - regime_detector.py  - 市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py   - J-Quants API クライアント（fetch / save / 認証 / rate limit）
  - pipeline.py         - ETL パイプライン（run_daily_etl 等）
  - etl.py              - ETLResult の再エクスポート
  - news_collector.py   - RSS 収集・前処理・保存ユーティリティ
  - calendar_management.py - マーケットカレンダー管理（is_trading_day 等）
  - stats.py            - zscore_normalize 等の統計ユーティリティ
  - quality.py          - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py            - 監査ログテーブル定義・初期化ユーティリティ
- src/kabusys/research/
  - __init__.py
  - factor_research.py  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - feature_exploration.py - 将来リターン計算・IC・統計サマリーなど

（上記は主要なファイルの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 設計上のポイント / 運用上の注意

- Look-ahead bias 回避
  - date.now()/today() を直接参照せず、target_date を明示的に渡して処理する設計を採用しています（backtest / 運用での時間軸整合性保持）。

- フェイルセーフ設計
  - 外部 API（J-Quants、OpenAI）失敗時は可能な限り処理を継続し、ステータスやログで問題を記録します。AI 呼び出しの失敗やレスポンスパース失敗時はスコアを 0.0 にフォールバックする等の保護があります。

- 冪等性
  - データ保存関数は基本的に ON CONFLICT DO UPDATE を用いて冪等に保存します。監査ログの order_request_id は冪等キーとして利用できます。

- セキュリティ対策
  - ニュース取得時は SSRF 対策（リダイレクト検証、プライベート IP ブロック）、defusedxml の使用、受信サイズ制限などを実装しています。

---

## 開発・貢献

- コードベース内の docstring が実装の仕様書になっています。新しい機能追加やバグ修正の際は、関連モジュールの docstring およびテストを更新してください。
- 自動環境変数ロードは .env / .env.local をサポートします。CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して制御できます。

---

README に書かれている使い方・設定はこのコードベースの代表的な利用方法です。実際の運用では DB スキーマの初期化、API キー管理、ログ/監視/アラート設定などを適切に行ってください。追加の例や詳細が必要であれば、どの機能について深掘りしたいか教えてください。