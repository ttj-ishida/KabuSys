# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース NLU（OpenAI を用いたセンチメント解析）、ファクター/リサーチユーティリティ、監査ログ（発注トレーサビリティ）、マーケットカレンダー管理などを含むモジュール群を提供します。

主な目的は「バックテスト／リサーチ／本番運用に使える一貫したデータ基盤とアルゴリズムユーティリティ」を提供することです。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants からの日次株価（OHLCV）、財務データ、JPX カレンダーの差分取得と DuckDB への冪等保存
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等のエントリポイント

- データ品質チェック
  - 欠損値・スパイク・重複・日付不整合の検出（quality モジュール）
  - QualityIssue データ構造で詳細を取得可能

- ニュース収集 / 前処理
  - RSS 取得（SSRF 対策、gzip 上限検査、トラッキングパラメータ除去）
  - raw_news / news_symbols へ冪等保存（news_collector）

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM で評価して ai_scores に保存（news_nlp.score_news）
  - マクロニュースを使った市場レジーム判定（regime_detector.score_regime）

- 研究・ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（research/factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー（feature_exploration）
  - クロスセクション Z スコア正規化（data.stats.zscore_normalize）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（data.audit）
  - init_audit_db で専用 DuckDB を初期化して接続取得可能

- ユーティリティ
  - 環境変数管理（kabusys.config.settings）
  - J-Quants クライアント（rate limit / リトライ / トークン自動リフレッシュ）
  - カレンダー管理（営業日判定・前後営業日取得）

---

## 要件

- Python 3.10+
- 推奨ライブラリ（少なくとも以下が必要）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの配布形態により requirements.txt / pyproject.toml を参照してください。）

---

## 環境変数（主なもの）

このパッケージは .env ファイルまたは環境変数を読み込みます（kabusys.config が自動ロード）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（利用する機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（注文実行に必要）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知を使う場合

オプション・設定:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite（data/monitoring.db など）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（ローカル開発向け）

1. ソースを取得
   - git clone ... （任意の方法でソースを入手）

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   例（最低限）:
   ```
   pip install "duckdb" "openai" "defusedxml"
   ```
   開発用に requirements.txt / pyproject.toml があればそちらを使ってください:
   ```
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成するか、CI/OS 環境変数を設定してください。
   - 自動ロードはプロジェクトルートに .git または pyproject.toml を置いている場合に有効です。

5. データ保存先ディレクトリを作る
   ```
   mkdir -p data
   ```

---

## 使い方（いくつかの例）

以下は主要 API の利用例（簡易）。

- 基本的な接続と ETL 実行
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path を返します
conn = duckdb.connect(str(settings.duckdb_path))
# 日次 ETL（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを取得して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を使用
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ma200 とマクロニュース合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# これで signal_events / order_requests / executions テーブルが作成されます
```

- news_collector の RSS 取得
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意:
- OpenAI 関連関数は API 呼び出しが行われるため、OPENAI_API_KEY を環境変数に設定しておく必要があります（または関数引数で api_key を渡す）。
- J-Quants API を使う ETL は JQUANTS_REFRESH_TOKEN が必須です。

---

## 設計上の注意点 / 実装方針（抜粋）

- ルックアヘッドバイアスを避けるため、関数内で datetime.today() を直接参照しない設計（target_date を明示的に渡すことを想定）。
- J-Quants クライアントはレート制御（120 req/min）・リトライ・401 リフレッシュ等を実装。
- ニュース収集は SSRF・XML Bomb・最大レスポンスサイズ等の安全対策を実装。
- OpenAI 呼び出しは冪等性やリトライ（429/5xx に対するバックオフ）に配慮。
- DuckDB への保存は可能な限り冪等（ON CONFLICT 等）で実装。

---

## ディレクトリ構成（主なファイル/モジュール）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント解析（score_news）
    - regime_detector.py            — マクロ＋MA200 を使った市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント & DuckDB 保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL の公開インターフェース（ETLResult）
    - news_collector.py             — RSS 収集・前処理
    - quality.py                    — データ品質チェック
    - calendar_management.py        — 市場カレンダー管理（営業日判定等）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ初期化（init_audit_db 等）
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン計算、IC、統計サマリー

---

## 開発 / 貢献

- バグ報告や改善要望は Issue を立ててください。
- テストはユニットテストの追加を歓迎します。AI / 外部 API 呼び出し部分はモック可能な設計になっています。
- 本 README はプロジェクト内部の実装に基づく概要です。実際のデプロイや本番運用時は環境変数の管理（シークレット）、監視、リスク管理ルールの適用を必ず行ってください。

---

もし特定の機能（例: ETL の詳細な運用手順、OpenAI の課金対策、ニュース収集の CSV エクスポート方法等）について README を拡張したい場合は、用途を教えてください。追加で具体的なコマンド例や運用チェックリストも用意できます。