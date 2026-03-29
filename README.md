# KabuSys

日本株向けのデータプラットフォームおよび自動売買／リサーチ基盤ライブラリです。  
DuckDB をデータ層に用い、J-Quants API / RSS / OpenAI（LLM）等を組み合わせて、データ取得（ETL）・品質チェック・ニュース NLP・市場レジーム判定・ファクター計算・監査ログ等の機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得（ETL）
  - J-Quants API 経由で株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存
  - 差分更新／バックフィル／ページネーション対応
  - レート制御・リトライ・トークン自動リフレッシュ対応

- データ品質管理
  - 欠損・重複・スパイク・日付不整合などのチェック（quality モジュール）
  - ETL 実行結果を ETLResult に集約

- ニュース収集（news_collector）
  - RSS フィードから記事を取得・正規化し raw_news / news_symbols に保存
  - SSRF や XML Bomb、巨大レスポンス対策を考慮した実装

- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコアを算出・ai_scores に保存
  - バッチ処理、リトライ、レスポンス検証、スコアクリップ等の堅牢な実装

- 市場レジーム判定（ai.regime_detector）
  - ETF (1321) の 200 日移動平均乖離とマクロニュース（LLM によるセンチメント）を重み付けして市場レジーム（bull/neutral/bear）を判定・market_regime に保存
  - ルックアヘッドバイアス回避、API エラー時のフェイルセーフ等を考慮

- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、z-score 正規化

- 監査ログ（data.audit）
  - signal → order_request → execution までのトレーサビリティを確保する監査スキーマの初期化・管理
  - 冪等性・UTC タイムスタンプ等の設計原則に準拠

---

## 要件

- Python 3.10+
- 主要依存（抜粋）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI など）

（実プロジェクトでは pyproject.toml / requirements.txt を用意してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン（あるいはソースを配置）
2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
4. パッケージをインストール（開発モード）
   ```bash
   pip install -e .
   ```
   ※ pyproject.toml/setup.cfg がある場合に有効です。なければ直接 PYTHONPATH を通すかパッケージ配布手順に従ってください。

---

## 環境変数／設定

自動でプロジェクトルートの `.env` / `.env.local` を読み込み、環境変数をセットします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。環境変数は `kabusys.config.settings` から参照可能です。

主な設定項目（必須・推奨）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live"), デフォルト "development"
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

設定値は必須のものは Settings プロパティ呼び出し時にチェックされ、未設定時は ValueError を投げます。

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な例）

以下は最小限の使用例です。すべての関数は DuckDB 接続（duckdb.connect(...) が返す接続オブジェクト）を受け取ります。

- 日次 ETL を実行（株価 / 財務 / カレンダー / 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコア付け（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20))  # 戻り値は書き込んだ銘柄数
print("scored:", n)
```

- 市場レジーム判定（1321 の MA200 とマクロニュースを組み合わせる）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルに書き込む
```
OpenAI API キーを引数で渡すことも可能:
```python
score_regime(conn, date(2026,3,20), api_key="sk-...")
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作成して監査スキーマを初期化
conn_audit = init_audit_db("data/audit.duckdb")
# またはインメモリ:
conn_mem = init_audit_db(":memory:")
```

- マーケットカレンダー関連ユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026,3,20)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

注意事項:
- ai.news_nlp / ai.regime_detector は OpenAI を呼び出します。API キーが必要です。API 呼び出しはリトライ処理やレスポンス検証を行いますが、API に依存するためコストやレート制限に注意してください。
- ETL / データ保存は DuckDB に対する SQL 実行が中心です。既存テーブルスキーマが必要です（スキーマ作成ロジックはプロジェクトに実装されている想定です）。

---

## ディレクトリ構成（抜粋）

プロジェクト単位の主要ファイル・モジュール構成を示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数読み込み・設定 (Settings)
  - ai/
    - __init__.py
    - news_nlp.py                     # ニュース NLP（OpenAI） -> ai_scores 書込み
    - regime_detector.py              # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               # J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py                     # ETL パイプライン / run_daily_etl 等
    - etl.py                          # ETLResult のエクスポート
    - news_collector.py               # RSS 収集・前処理・保存
    - calendar_management.py          # 市場カレンダー管理・検索ユーティリティ
    - quality.py                       # データ品質チェック
    - stats.py                         # 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                         # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py              # ファクター計算（momentum/value/volatility）
    - feature_exploration.py          # 将来リターン / IC / 統計サマリー
  - ai, research, data 以下にさらに補助関数やユーティリティが含まれます

注意: パッケージ top-level の __all__ には data, strategy, execution, monitoring 等が含まれていますが、このスニペットに全てのサブモジュール（strategy / execution / monitoring）の実装は含まれていません。プロジェクト全体ではそれらが別ファイルとして存在する想定です。

---

## 開発・運用上の注意

- ルックアヘッドバイアス防止:
  - 多くの処理（ETL / NLP / レジーム判定 / ファクター計算）は date を明示的引数として受け取り、内部で現在日時を参照しない実装方針です。バックテスト時のバイアスに注意してください。

- 環境変数自動ロード:
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動で読み込みます。テスト時などで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 外部 API のレート制御・リトライ:
  - J-Quants は 120 req/min のレート制限を考慮した実装です（固定間隔スロットリング）。
  - OpenAI 呼び出しはリトライや 5xx/429 ハンドリングを実装していますが、過度の呼び出しは避けてください。

- セキュリティ / 安全性:
  - news_collector は SSRF／XML 攻撃／Gzip Bomb 等の対策を備えています。外部 URL を扱う際は例外処理に注意してください。

---

## 参考 / 追加情報

- settings（kabusys.config.Settings）は必要な環境変数をラズし、is_live / is_paper / is_dev の判定を行います。
- DuckDB スキーマ（raw_prices / raw_financials / raw_news / ai_scores / market_regime / market_calendar / audit テーブル等）はプロジェクト内のスキーマ初期化ロジックで作成することを想定しています（スニペット内では audit.init_audit_schema 等を利用可能）。
- OpenAI 呼び出しで使用するモデルは gpt-4o-mini（現状定義）。使用するモデルや料金体系は随時見直してください。

---

もし README に追加したい具体的な内容（例: 実行スクリプト、CI 用手順、DB スキーマの DDL、requirements.txt の完全な一覧など）があれば教えてください。必要に応じてサンプル .env.example も作成します。