# KabuSys

日本株向け自動売買プラットフォームのライブラリ実装（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、ファクター研究、監査ログ（約定トレーサビリティ）などを提供します。

---

## 概要

KabuSys は日本株運用のためのデータ基盤と戦略支援モジュール群をまとめたパッケージです。  
主に以下を目的としています。

- J-Quants からの株価・財務・カレンダー取得と DuckDB への冪等保存（ETL）
- RSS によるニュース収集と前処理
- OpenAI を用いたニュースセンチメント解析（銘柄ごとの ai_score / マクロセンチメント）
- ETF / マクロ情報を用いた市場レジーム判定（bull / neutral / bear）
- ファクター算出・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

---

## 主な機能一覧

- data/jquants_client.py: J-Quants API クライアント（認証・レートリミット・ページネーション・保存関数）
- data/pipeline.py, data/etl.py: 日次 ETL パイプライン（差分取得・保存・品質チェック）
- data/news_collector.py: RSS 収集・前処理・SSRF 対策・冪等保存支援
- data/quality.py: 品質チェック（欠損、スパイク、重複、日付不整合）
- data/calendar_management.py: マーケットカレンダー管理・営業日判定ユーティリティ
- data/audit.py: 監査ログスキーマ作成・監査DB初期化
- ai/news_nlp.py: ニュース（銘柄別）センチメントスコア生成（OpenAI）
- ai/regime_detector.py: ETF（1321）MA乖離 + マクロセンチメントから日次市場レジーム判定
- research/*: ファクター計算（momentum / value / volatility）と特徴量解析ユーティリティ
- data/stats.py: zscore 正規化など共通統計ユーティリティ
- config.py: 環境変数 / .env 自動読み込みと設定オブジェクト（settings）

設計上の配慮点（抜粋）:
- Look-ahead バイアス防止（日時参照の運用に注意）
- API 呼び出しに対するリトライ / バックオフ / フェイルセーフ
- DuckDB に対する冪等保存（ON CONFLICT / DELETE→INSERT 等）
- セキュリティ対策（SSRF、XML デシリアライズ対策、レスポンスサイズ制限）

---

## 必要条件

- Python 3.10 以上（ソースで PEP 604 の型記法（|）を使用）
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml
  - その他 標準ライブラリ外のパッケージ（urllib 等は標準）

※ 実際の requirements はプロジェクトの packaging 設定に合わせて下さい。

---

## セットアップ手順

1. リポジトリをクローン / 展開
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール（一例）
   ```
   pip install duckdb openai defusedxml
   # またはパッケージ配布用に:
   pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` として以下を設定してください（.env.example を参考に作成）。
     必須（コードから参照されるキー）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...  (ai モジュールを使う場合)
     任意（デフォルト値あり）:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development / paper_trading / live, default=development)
     - LOG_LEVEL (DEBUG / INFO / ...)

   - 自動読み込みはデフォルトで有効。テスト等で無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. データベース用ディレクトリの作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（基本サンプル）

以降は Python REPL / スクリプトでの利用例です。

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続作成（監査DB 初期化）
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = duckdb.connect(str(settings.duckdb_path))
# 監査スキーマを既存 conn に追加する
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # transactional=True を必要に応じて指定

# あるいは監査専用 DB を作る
audit_conn = init_audit_db("data/audit.duckdb")
```

- 日次 ETL 実行（J-Quants からの差分取得 → 保存 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア付与（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None で OPENAI_API_KEY を使用
print(f"written {written} codes")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算 / 研究用ユーティリティ
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
normed = zscore_normalize(mom, ["mom_1m", "mom_3m"])
```

- RSS フェッチ（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- OpenAI 呼び出しは API 失敗時にフォールバックやリトライロジックを持ちますが、APIキーと利用料に注意してください。
- ETL / 研究用関数は DuckDB のスキーマ（prices_daily / raw_news / raw_financials 等）に依存します。初期スキーマは別途定義・初期化してください。

---

## .env 優先順位と自動読み込み

- 自動ロード順序: OS 環境変数 > .env.local > .env
- テストや特殊環境で自動ロードを無効にするには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 必須 env が未設定の場合、settings の各プロパティは ValueError を発生させます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。

---

## ディレクトリ構成（主要ファイル）

概観（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 管理 (settings)
  - ai/
    - __init__.py
    - news_nlp.py                 — 銘柄別ニュースセンチメント（OpenAI）
    - regime_detector.py         — マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント / DuckDB 保存
    - pipeline.py                — ETL パイプライン実装（run_daily_etl 等）
    - etl.py                     — ETL 結果型の公開
    - news_collector.py          — RSS 取得・前処理・SSRF 対策
    - quality.py                 — データ品質チェック
    - calendar_management.py     — マーケットカレンダー管理 / 営業日判定
    - stats.py                   — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                   — 監査ログスキーマ / init_audit_db
  - research/
    - __init__.py
    - factor_research.py         — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py     — 将来リターン / IC / summary / rank

各モジュールはドメインごとに責務を分離しており、テスト時に内部の API 呼び出し部分（例: OpenAI 呼び出し、HTTP オープン）をモックしやすい設計になっています。

---

## 開発メモ / 注意事項

- OpenAI 呼び出し部分はテスト容易性のため差し替え可能な内部関数を用意しています。ユニットテストでは該当関数をパッチしてください（例: kabusys.ai.news_nlp._call_openai_api のモック）。
- J-Quants クライアントはレート制御とリトライロジックを実装しています。API 利用制限に注意してください。
- データ保存は可能な限り冪等（ON CONFLICT / DELETE→INSERT）を意識していますが、DB スキーマが存在すること（テーブル作成済み）を前提とする箇所があります。初期スキーマはプロジェクトドキュメント / migrations で管理してください。
- セキュリティ面: news_collector は SSRF / XML Bomb / レスポンスサイズ制限の対策を実装していますが、外部フィードの取り扱いは常に注意してください。

---

## サポート・拡張

- 追加したい機能例:
  - バックテスト用のデータアクセスラッパー
  - Strategy 層（シグナル生成・ポジション管理）の実装
  - CI 用の DB スキーマ初期化スクリプト / fixtures
  - Prometheus メトリクスやより詳細な監視（monitoring モジュール拡張）

---

README に記載の無い細かい使い方や API 仕様は各モジュールの docstring を参照してください。必要であれば、特定機能の使い方サンプルやスキーマ定義ドキュメントを追加で作成します。