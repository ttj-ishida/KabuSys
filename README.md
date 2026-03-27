# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
ETL（J-Quants）→ DuckDB 保存、ニュースの収集・NLP スコアリング（OpenAI）、ファクター計算、マーケットレジーム判定、監査ログなど自動売買システムに必要な主要機能を提供します。

バージョン: 0.1.0

---

## 概要（Project overview）

KabuSys は日本株の自動売買／リサーチプラットフォームのために設計された Python モジュール群です。主な役割は次の通りです。

- J-Quants API からのデータ取得（株価日足、財務、JPX カレンダー 等）
- DuckDB を用いたローカルデータ保存（冪等保存）
- ニュース収集（RSS）と LLM によるセンチメント評価（OpenAI）
- 市場レジーム判定（MA とマクロニュースの組合せ）
- ファクター算出（モメンタム、ボラティリティ、バリュー等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレース）用スキーマ初期化

設計上の重点:
- Look-ahead bias を避ける日付取り扱い
- API 呼び出しのリトライ / バックオフ・レート制御
- 冪等性（DB 書き込みは ON CONFLICT 等で整合）
- フェイルセーフ（外部 API 失敗時は安全側の代替動作）

---

## 機能一覧（Features）

- Data
  - J-Quants client: fetch & save（株価 / 財務 / カレンダー / 上場情報）
  - ETL パイプライン（差分更新・バックフィル・品質チェック）
  - calendar management: 営業日判定 / next/prev trading day / カレンダー更新ジョブ
  - news_collector: RSS 収集・前処理・raw_news 保存（SSRF / XML 攻撃対策・サイズ上限）
  - audit: 監査ログスキーマ（signal_events, order_requests, executions）と初期化ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: z-score 正規化等の統計ユーティリティ

- AI
  - news_nlp.score_news: ニュース記事を銘柄ごとに LLM でセンチメント化して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュース LLM を合成して市場レジーム判定

- Research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize を含むデータ加工支援

- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルート検出）
  - Settings オブジェクト経由で必要な設定を取得

---

## セットアップ手順（Setup）

前提: Python 3.10+（コードは typing union などを利用）

1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な主要パッケージ: duckdb, openai, defusedxml
   - 例:
     pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使用してください）

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知に使用
     - SLACK_CHANNEL_ID: 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（関数呼び出し時に引数で渡すことも可）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|…（デフォルト INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

4. データディレクトリ
   - DuckDB ファイル等を保存するディレクトリ（data/ 等）を作成しておくと便利です。

---

## 使い方（Examples）

下記は主要なユースケースの簡単な使用例です。実行時は必ず適切な環境変数（特に API キー）を設定してください。

- DuckDB 接続の例
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（全体）を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 株価データのみ ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl

fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
```

- ニュースの NLP スコアを取得して ai_scores に保存（OpenAI API key を指定）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査DB 初期化（監査用別 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- カレンダー系ユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 4, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- テスト時の注意点
  - OpenAI / J-Quants など外部 API 呼び出しは unittest.mock.patch で `_call_openai_api` や jquants_client._request 等を差し替えてテストしてください。
  - 自動 env ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (オプション, default=http://localhost:18080/kabusapi)
- OPENAI_API_KEY (必須または関数引数で指定)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (オプション, default=data/kabusys.duckdb)
- SQLITE_PATH (オプション, default=data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG/INFO/…)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動 .env 読み込みを無効化)

settings オブジェクトは kabusys.config.settings で利用できます。

---

## ディレクトリ構成（Directory structure）

主要ファイル・モジュール（src/kabusys 以下の抜粋）:

- kabusys/
  - __init__.py
  - config.py                     # 環境変数・設定管理、自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py                 # ニュースの LLM スコアリング（score_news）
    - regime_detector.py         # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           # J-Quants API クライアント（fetch / save）
    - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
    - etl.py                      # ETL の公開インターフェース（ETLResult）
    - calendar_management.py      # 市場カレンダー管理（is_trading_day 等）
    - news_collector.py           # RSS 収集・前処理
    - quality.py                  # 品質チェック
    - stats.py                    # zscore_normalize 等
    - audit.py                    # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py          # モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py      # forward returns / IC / 統計サマリ

各モジュールは責務を分離しており、ETL と研究用機能は DB 接続（duckdb connection）を受け取って純粋に処理します。発注等の実際のブローカー接続はこのコードベースには含まれていません（監査用スキーマは発注フローを取り込むための土台を提供します）。

---

## 開発・運用上の注意

- Look-ahead bias を避けるため、各処理は内部で date / datetime を外部から渡す方式を採用しています（date.today() への直接依存を最小化）。
- 外部 API 呼び出しはリトライやレートリミット・バックオフを組み込んでいますが、実運用では API キーの管理や呼び出し頻度の監視を行ってください。
- DuckDB の executemany に対する互換性（空リスト不可など）に配慮した実装があります。DuckDB バージョンに依存する挙動に注意してください。
- ログレベルや環境（development/paper_trading/live）は settings で切り替え可能です。critical な環境変数未設定時は ValueError を投げます。

---

必要があれば README に含めるサンプル .env 例や追加の CLI/起動スクリプトの記載を作成します。どの部分をより詳しく説明したいか教えてください。