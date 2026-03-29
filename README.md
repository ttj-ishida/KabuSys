# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買/リサーチ基盤を備えたライブラリ群です。J-Quants や RSS / OpenAI（LLM）など外部データソースを組み合わせ、ETL、品質チェック、ニュースセンチメント、ファクター計算、監査ログ管理、マーケットカレンダー管理などを提供します。

主な設計方針は以下です。
- ルックアヘッドバイアスを避ける（内部で date.today() を無闇に参照しない）
- DuckDB を中心に SQL + Python で処理
- 外部 API 呼び出しはリトライ・レート制御・フォールバックを備える
- ETL や DB 書き込みは冪等になるよう実装

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` の自動読み込み（必要に応じ無効化可）
  - 必須環境変数の検査（settings オブジェクト）
- データ ETL（J-Quants）
  - 日次株価（OHLCV）取得・保存（フェッチ／ページネーション対応）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分更新 / バックフィル / 品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL エントリポイント: run_daily_etl
- ニュース収集
  - RSS フィード取得・前処理・SSRF/サイズ/トラッキング除去対策
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント scoring（score_news）
  - マクロニュースを使った市場レジーム判定（score_regime）
  - OpenAI 呼び出しは JSON Mode を利用、リトライ / フォールバック実装
- リサーチ / ファクター計算
  - Momentum / Volatility / Value の各ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン算出、IC（Spearman）計算、統計サマリー、Zスコア正規化
- カレンダー管理（market_calendar）
  - 営業日判定 / 前後の営業日検索 / 期間の営業日取得
  - カレンダー更新ジョブ（calendar_update_job）
- 監査ログ（audit）
  - signal_events / order_requests / executions といった監査テーブルの初期化・インデックス作成
  - init_audit_schema / init_audit_db による冪等初期化
- ユーティリティ
  - 汎用統計関数（zscore_normalize 等）
  - J-Quants クライアント（認証、レートリミット、保存関数）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `X | None` を使用しているため）
- DuckDB を利用するため適宜ネイティブビルド環境が必要な場合あり

1. リポジトリをクローン / 配布パッケージを展開
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要な依存パッケージをインストール
   - 主要依存例（最低限）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - 実プロジェクトでは requirements.txt / pyproject.toml を用意している想定です。開発環境に応じて追加ライブラリ（slackclient など）をインストールしてください。
4. 環境変数（.env）を用意する
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます）。
   - 主に必要とされる環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須) — Slack 通知用（必要時）
     - SLACK_CHANNEL_ID (必須) — Slack 通知先
     - DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (任意、デフォルト: data/monitoring.db)
     - KABUSYS_ENV (任意、default=development)：development / paper_trading / live
     - LOG_LEVEL (任意、default=INFO)：DEBUG/INFO/WARNING/ERROR/CRITICAL
     - OPENAI_API_KEY (OpenAI 呼び出しを行う場合に設定)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)：1 を設定すると .env 自動読み込みを無効化
   - 参考: config.Settings にプロパティとバリデーションがあります

5. DB の初期化（監査用など）
   - 監査ログ DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡単な例）

- DuckDB に接続して日次 ETL を実行する（J-Quants トークンは設定済みの前提）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores テーブルへ書き込む（OpenAI API キーが環境変数にあるか api_key を渡す）:

```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"scored {n} symbols")
```

- 市場レジーム（bull/neutral/bear）を算出して market_regime に書き込む:

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査スキーマ初期化（既存 DuckDB 接続を渡す）:

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- カレンダー関連ユーティリティ:

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026,3,20)))
print(next_trading_day(conn, date(2026,3,20)))
```

注意:
- OpenAI 呼び出しは外部 API 依存のため、テスト時はモック（各モジュールの `_call_openai_api` をパッチ）することが推奨されています。
- ETL は外部 API への呼び出しとデータ保存を行うため、実行前に環境変数と DB パスの確認を行ってください。

---

## ディレクトリ構成

（主要ファイル・モジュールの概要）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings（J-Quants / kabu / Slack / DB パス / 環境設定）
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None) — ニュースセンチメント算出
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None) — マクロ + MA200 で市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・calendar_update_job
    - etl.py
      - ETLResult の公開（pipeline.ETLResult）
    - pipeline.py
      - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl（ETL の中核）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - 品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査テーブル DDL・初期化（init_audit_schema / init_audit_db）
    - jquants_client.py
      - J-Quants API クライアント（認証・フェッチ・保存・レートリミット）
    - news_collector.py
      - RSS 取得 / 前処理 / SS R F 対策 / raw_news への保存
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - monitoring/ (※ README に出てくる可能性はありますがコードベースに具体的なファイルはここには含まれていません)
  - strategy/, execution/, monitoring/ (パッケージ公開名として __all__ に記載されていますが、該当実装はコード抜粋に依存します)

---

## テスト・開発時のヒント

- OpenAI 呼び出し・ネットワーク依存処理はモックしてユニットテストを行ってください。news_nlp と regime_detector は各々 `_call_openai_api` を内部関数として持ち、patch 可能です。
- DuckDB はテストで ":memory:" のインメモリ DB を使うと高速にテストできます（init_audit_db(":memory:") など）。
- .env 自動読み込みはプロジェクトルートの検出を __file__ の親から行います。テストで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 注意事項

- 本ライブラリは実際の売買システムの一部を構成する想定で書かれています。実運用での利用時は十分なテスト、監査、リスク管理（注文二重化回避、資金管理、エラーハンドリング）を実施してください。
- 一部のチェックやデータベーススキーマは DuckDB のバージョンに依存する実装（executemany の制約や型バインディング）を含みます。DuckDB の互換性に注意してください。
- 外部 API の利用（J-Quants / OpenAI / RSS）には各サービスの利用規約とレート制限を守ってください。

---

必要があれば、README にサンプル .env.example、requirements.txt、より詳しい API ドキュメント（関数引数/戻り値のサンプル）や運用手順（Cron / Airflow での ETL スケジュール例）を追加して作成します。どの内容を優先的に追加しますか？