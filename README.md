# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・AI 評価・監査ログを備えた自動売買支援ライブラリです。DuckDB をデータストアとして用い、J-Quants API / RSS / OpenAI を組み合わせてデータ収集、品質チェック、ファクター計算、ニュース NLP、マーケットレジーム判定などを行います。

---

## 主要な機能

- データ収集（J-Quants API）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存（ページネーション対応、冪等保存）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - run_daily_etl による市場カレンダー→株価→財務→品質チェックの一括処理
  - 差分取得、バックフィル、品質チェックの実行
- データ品質チェック
  - 欠損（OHLC）、スパイク（前日比）、重複、日付不整合などを検出
- ニュース収集・NLP
  - RSS から記事収集（SSRF 対策／トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）で銘柄別ニュースセンチメント（score_news）
- レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュースセンチメントを組み合わせて市場レジームを判定（score_regime）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（ファクター探索・IC 計算等）
  - Z スコア正規化ユーティリティ
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定のトレーサビリティ用テーブル群と初期化ユーティリティ
- ユーティリティ
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - DuckDB 用の初期化ユーティリティ、監査 DB 作成補助

---

## 要件（主な依存ライブラリ）

本リポジトリのコードが依存する主要パッケージ（抜粋）：

- Python 3.10+（型アノテーションで union types を使用）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローンする（src 配下にパッケージがある構成です）:

   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作成して有効化:

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要なパッケージをインストール:

   pip install duckdb openai defusedxml

   （プロジェクトに pip install -e . や requirements.txt があればそちらを使用してください）

4. データディレクトリを作成（デフォルトの DuckDB / SQLite パスを使用する場合）:

   mkdir -p data

5. 環境変数を設定:
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（読み込みの優先順位: OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

---

## 必要な環境変数（主なもの）

※ .env.example があればそれを参考にしてください。主要項目は以下の通りです。

- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（API から id_token を取得するため）
- KABU_API_PASSWORD
  - kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - Slack 通知用（必要に応じて）
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - デフォルト: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - 監視設定
- KABUSYS_ENV
  - 有効値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY
  - OpenAI API を使う機能（news_nlp, regime_detector）で必要

---

## 使い方（簡単なサンプル）

以下は以降の例で `settings` を通じて設定値を使う想定です。

- DuckDB コネクションを用意して日次 ETL を実行する例

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニューススコア算出（score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を読む
print(f"scored: {n_written} codes")
```

- 市場レジーム判定（score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

- RSS を取得する（ニュースコレクタの低レベルユーティリティ）

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

（上記はいずれも例です。実際の運用ではトランザクション管理やログ設定、エラーハンドリングを追加してください）

---

## 重要な設計上の注意点

- ルックアヘッドバイアス対策:
  - モジュールの多くは内部で date.today() / datetime.today() を参照せず、呼び出し元が target_date を渡す設計です。バックテストでの使用時は過去時点のデータだけを用いるよう注意してください。
- 冪等性:
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を使って冪等保存を行います。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）で失敗した場合、多くの部分はログ出力してフォールバック（スコア 0 等）するか、部分的にスキップして継続します。

---

## ディレクトリ構成（主要ファイルの説明）

（src 配下をパッケージ root とした例）

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__）とサブモジュールの公開

- src/kabusys/config.py
  - 環境変数 / .env ロードロジック、設定クラス settings
  - 自動 .env 読み込み（.git または pyproject.toml を基準にプロジェクトルートを特定）
  - 必須設定取得ヘルパー _require

- src/kabusys/ai/
  - news_nlp.py
    - raw_news → OpenAI による銘柄別ニュースセンチメント算出（score_news）
  - regime_detector.py
    - ETF 1321 の MA とマクロニュース（LLM）を合成して market_regime を算出（score_regime）

- src/kabusys/data/
  - jquants_client.py
    - J-Quants API クライアント、fetch_* / save_* / get_id_token 等
  - pipeline.py
    - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）と ETLResult
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - news_collector.py
    - RSS 取得・前処理・記事 ID 生成（SSRF 対策、サイズ制限）
  - calendar_management.py
    - market_calendar の取得 / 営業日判定 / next/prev_trading_day 等
  - audit.py
    - 監査ログ用テーブル DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - etl.py
    - ETLResult の公開（軽量ラッパー）

- src/kabusys/research/
  - factor_research.py
    - Momentum / Volatility / Value の計算関数（calc_momentum, calc_volatility, calc_value）
  - feature_exploration.py
    - 将来リターン算出、IC 計算、統計サマリー等
  - __init__.py
    - 研究系ユーティリティの公開

- src/kabusys/data/jquants_client.py
  - J-Quants API を扱う低レイヤー（レートリミット、リトライ、ページネーション）

---

## 開発・運用上のヒント

- テスト時は env 自動ロードを無効化したい場合、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しをテストで差し替えたい場合、内部の `_call_openai_api` を unittest.mock.patch でモックできます（news_nlp / regime_detector で個別に実装を持っています）。
- DuckDB への executemany に空リストを渡すとエラーになるバージョンがあるため、パラメータが空かどうかのチェックを各所で行っています。これに注意してデータ投入ロジックを拡張してください。

---

必要があれば README を拡張して、実運用向けのデプロイ手順、cron / systemd サービス例、Slack 通知の設定、監視（Prometheus / ログ集約）などの追加セクションを作成します。どの内容を追加したいか教えてください。