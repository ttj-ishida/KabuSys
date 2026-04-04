# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI でのセンチメント評価）、ファクター計算、監査ログ（発注/約定トレース）、カレンダー管理など、アルゴリズム取引に必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得 (J-Quants API)
  - 日次株価（OHLCV）、財務指標、上場銘柄情報、JPX カレンダーの差分 ETL（ページネーション / 再取得 / 冪等保存対応）
  - Rate limiting / リトライ / トークン自動リフレッシュ対応
- ニュース収集 / 前処理
  - RSS から記事を取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、前処理済テキストを保存
- ニュース NLP（OpenAI）
  - 銘柄単位のニュースセンチメントを gpt-4o-mini で評価し ai_scores に書き込み
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリューなどのファクターを DuckDB 上で計算
  - 将来リターン、IC（Spearman）や統計サマリーの計算ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の冪等・監査テーブル定義と初期化ユーティリティ
- 運用ユーティリティ
  - 市場カレンダー管理、ETL の上位エントリポイント（run_daily_etl） など
- 設計上の配慮
  - ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない設計）
  - 冪等性・フェイルセーフ（API失敗時は部分スキップして継続）
  - DuckDB を用いた軽量なローカル分析基盤

---

## 必要条件（推奨）

- Python 3.10+
- 必要パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がある場合はそちらを利用してください）

例:
```sh
python -m pip install "duckdb" "openai" "defusedxml"
```

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境作成（推奨）
```sh
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール
```sh
pip install duckdb openai defusedxml
# その他のユーティリティが必要なら適宜追加
```

4. 環境変数設定
- ルートに `.env`（または `.env.local`）を作成すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
- 主要な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使用）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必要な場合）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視DBパス（data/monitoring.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - KABUSYS_ENV: development / paper_trading / live
  - PID_FILE_PATH / KILL_FLAG_PATH / その他監視パラメータ

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

---

## 使い方（代表的な例）

以下はライブラリの主要関数の呼び出し例です。実際はログ設定やエラーハンドリングを適宜行ってください。

- DuckDB 接続を作って ETL を実行する（日次 ETL）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントスコアを作る（score_news）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定を実行する（score_regime）:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以降 order_requests / executions 等を利用可能
```

- カレンダー関連ユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- リサーチ系のファクター計算:
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
# records は各銘柄ごとの dict のリスト
```

注意:
- OpenAI 呼び出しを行う関数（score_news / score_regime）は OPENAI_API_KEY を参照します。関数引数で api_key を渡すことも可能です。
- 多くの関数は DuckDB のテーブル構成（raw_prices, raw_news, news_symbols, ai_scores, prices_daily, market_calendar 等）を前提としています。初期スキーマは ETL / audit 初期化処理等で作成してください。

---

## 環境変数（重要なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI の API キー（score_news / regime_detector 等で使用）
- KABU_API_PASSWORD — kabu API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効にする（1 を設定）

自動ロードの優先順: OS 環境変数 > .env.local > .env

---

## ディレクトリ構成

主なファイル / ディレクトリ:
```
src/
  kabusys/
    __init__.py
    config.py                        # 環境変数読み込み・設定
    ai/
      __init__.py
      news_nlp.py                    # ニュースセンチメント（OpenAI）
      regime_detector.py             # 市場レジーム判定（MA200 + マクロセンチメント）
    data/
      __init__.py
      calendar_management.py         # 市場カレンダー管理（is_trading_day 等）
      pipeline.py                    # ETL パイプライン（run_daily_etl 等）
      etl.py                         # ETL 型のエクスポート（ETLResult）
      jquants_client.py              # J-Quants API クライアント + 保存ロジック
      news_collector.py              # RSS 収集・前処理
      stats.py                       # zscore 等共通統計ユーティリティ
      quality.py                     # データ品質チェック
      audit.py                       # 監査ログ初期化 / DDL
    research/
      __init__.py
      factor_research.py             # モメンタム/ボラティリティ/バリュー
      feature_exploration.py         # 将来リターン / IC / 統計サマリー
    research/ (補助モジュール)
    ... (その他 strategy / execution / monitoring モジュールが想定される)
```

---

## 設計上の注意点 / 運用上の留意点

- 多くの処理（ニュース NLP / レジーム判定 / ETL）は「ルックアヘッドバイアス」を避ける設計になっており、内部で現在時刻を直接参照せず、呼び出し側が target_date を明示することを想定しています。バックテストでの使用時は必ず過去データのみを使うようにしてください。
- OpenAI や J-Quants への呼び出しは失敗時にフォールバックやリトライを行いますが、API キーやネットワークの問題で部分的に処理が失敗する可能性があるため、ログと ETLResult.quality_issues を確認してください。
- DuckDB を使うためスキーマやテーブルが無い場合はエラーになります。ETL の最初にスキーマ初期化が必要なケースがあります（audit.init_audit_db 等を参照）。
- セキュリティ: news_collector は SSRF 対策や XML パースの安全化（defusedxml）を実装していますが、運用環境での追加制御（プロキシ、ファイアウォール等）を推奨します。

---

## 貢献 / 開発

- 新しい機能追加やバグ報告は Pull Request / Issue でお願いします。
- テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で `.env*` を読み込まないためユニットテストが容易になります。

---

必要であれば、README にサンプル .env.example、requirements.txt の推奨内容、より詳しい API リファレンス（各関数の引数・戻り値例）を追加します。どの情報が要りますか？