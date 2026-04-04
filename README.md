# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）による銘柄センチメント算出、リサーチ用ファクター計算、監査ログ（発注 → 約定のトレーサビリティ）、マーケットカレンダー管理などを提供します。

---

## 概要

KabuSys は以下の主要コンポーネントを含みます。

- データ取り込み（J-Quants API 経由）と ETL パイプライン（DuckDB を想定）
- ニュース収集（RSS）と LLM によるニュースセンチメント算出
- 市場レジーム判定（ETF の MA とマクロセンチメントの合成）
- ファクター計算 / 特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境設定管理（.env 自動読み込み）

設計上の特徴：
- ルックアヘッドバイアス防止のため内部で現在時刻を直接参照しない（呼び出し側が target_date を渡す）
- DuckDB を用いた SQL + Python 混在処理
- OpenAI（gpt-4o-mini）を JSON Mode で利用する設計（リトライ・フォールバック実装あり）
- 冪等性（DB 保存は ON CONFLICT / DELETE→INSERT を採用）

---

## 主な機能一覧

- ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー、株価、財務データの差分取得・保存・品質チェック
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl

- データ取得クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB に冪等保存

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news への保存（冪等化を想定）

- ニュース NLP（kabusys.ai.news_nlp）
  - score_news: 銘柄ごとの ai_score を生成して ai_scores テーブルへ保存

- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime: ETF 1321 の MA200 乖離 + マクロニュース LLM により市場レジームを判定して market_regime に保存

- 研究用（kabusys.research）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank 等

- データ品質（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合などのチェック関数と集約関数 run_all_checks

- 監査ログ（kabusys.data.audit）
  - init_audit_schema / init_audit_db: 発注・約定のトレーサビリティ用スキーマ初期化

- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml）
  - settings オブジェクト経由で各種設定を取得

---

## セットアップ手順

前提
- Python 3.10 以上（| 型ヒント等を利用）
- DuckDB を利用する環境

1. リポジトリを取得
   - 例: git clone ...

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   あるいはプロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

3. 環境変数の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。
   - 最低限の必須環境変数:
     - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD：kabuステーション API のパスワード（必須）
     - OPENAI_API_KEY：OpenAI API キー（score_news / score_regime を使う場合、関数引数でも渡せます）
   - 任意 / デフォルト（settings 参照）:
     - KABUSYS_ENV：development / paper_trading / live（デフォルト development）
     - LOG_LEVEL：DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - DUCKDB_PATH：data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 閾値など

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=./data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

4. 自動 .env 読み込みの動作
   - パッケージ読み込み時にプロジェクトルートを探し `.env` → `.env.local` の順で環境変数を自動読み込みします。
   - テスト等で自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要な例）

以下はライブラリを直接利用する最小例です。実際の利用ではログ・例外処理を適宜追加してください。

- DuckDB 接続を作成して ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path 型
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- news_nlp: 銘柄ごとのニューススコアを生成する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key 指定しなければ OPENAI_API_KEY を参照
print("written:", n_written)
```

- regime_detector: 市場レジームスコアを算出する
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env か引数で
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # :memory: も可
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- RSS 取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出しはネットワーク遅延やレート制限を考慮した実装になっていますが、API キーは必須です（関数引数で上書き可）。
- DuckDB のバージョンや挙動に依存する SQL が含まれるため、DuckDB の安定版を推奨します。

---

## 設定（settings）で取得できる主な項目

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabu API パスワード（必須）
- kabu_api_base_url: kabu API エンドポイント（デフォルト: http://localhost:18080/kabusapi）
- line_channel_access_token / line_user_id: LINE 通知用（任意）
- duckdb_path: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- sqlite_path: 監視用 SQLite（data/monitoring.db）
- pid_file_path / kill_flag_path / 各種閾値（CPU/MEM/DISK）
- KABUSYS_ENV の値: development / paper_trading / live（不正なら ValueError）
- LOG_LEVEL: DEBUG/INFO/...（不正なら ValueError）

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py        — ニュース NLP（score_news 等）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント / 保存ロジック
  - pipeline.py        — ETL パイプライン（run_daily_etl 等）
  - etl.py             — ETL 結果クラス再エクスポート
  - stats.py           — 統計ユーティリティ（zscore_normalize）
  - quality.py         — 品質チェック（欠損・スパイク等）
  - calendar_management.py — マーケットカレンダー管理
  - news_collector.py  — RSS 取得 / 前処理
  - audit.py           — 監査ログスキーマ・初期化
- research/
  - __init__.py
  - factor_research.py     — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- monitoring / execution / strategy / 残りのサブパッケージ（エントリや発注関連が想定されます）

---

## テスト・開発時のヒント

- 自動 .env 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテストで便利）。
- OpenAI の呼び出し箇所は _call_openai_api をモックする設計になっています（ユニットテスト容易化）。
- DuckDB に対する executemany に空配列を渡すとエラーになる古いバージョンがあるため、呼び出し側で空チェックを行う実装になっています。

---

必要であれば README に以下を追加できます：
- 例としての .env.example 全体
- CI / GitHub Actions 用の実行例
- 詳細な DB スキーマドキュメント（raw_prices / ai_scores / market_regime / market_calendar 等）
- strategy / execution レイヤーの使い方（発注フローのサンプル）

追加希望があれば教えてください。