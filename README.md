# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤のコアライブラリ群です。  
DuckDB をデータレイクとして利用し、J-Quants / RSS / OpenAI 等と連携してデータ収集（ETL）、品質チェック、特徴量作成、ニュース NLP、監査ログ、監視・発注の基礎機能を提供します。

バージョン: 0.1.0

---

## 主要な設計方針（要約）
- Look-ahead bias を避ける設計（内部で `datetime.today()` や `date.today()` を直接参照しない）
- DuckDB を中心とした idempotent な ETL／保存（ON CONFLICT DO UPDATE）
- 外部 API 呼び出しはリトライ・レート制御を実装（J-Quants / OpenAI）
- ニュース収集で SSRF / XML 攻撃 / 大容量応答に対する安全対策
- 監査ログ（signal → order_request → execution）の永続化とトレーサビリティ

---

## 機能一覧
- データ ETL
  - J-Quants から株価日足、財務データ、JPX カレンダーを差分取得・保存
  - ETL の品質チェック（欠損、重複、スパイク、日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集 / NLP
  - RSS 収集（トラッキング除去、SSRF 防止、gzip 対応）
  - OpenAI による銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF MA による市場レジーム判定（score_regime）
- リサーチ / ファクター
  - Momentum / Value / Volatility 等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Z-score 正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査 DB 初期化 helper（init_audit_db / init_audit_schema）
- ユーティリティ
  - 環境変数読み込み・管理（自動でプロジェクトルートの `.env` / `.env.local` を読み込み）
  - J-Quants クライアント（レートリミット・リトライ・トークン自動更新）
  - DuckDB 用の idempotent 保存関数（raw_prices, raw_financials, market_calendar 等）

---

## 必要要件（例）
- Python 3.10+
- 必須パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

（実際の依存はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順（開発環境向け）
1. リポジトリをクローンして、パッケージをインストール
   - pip install -e .（もしくは poetry/poetry install 等）
2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
3. .env をプロジェクトルートに配置（下記の環境変数を設定）
4. DuckDB ファイルや SQLite DB のパスは環境変数で上書き可能

---

## 環境変数（主なもの）
README の簡易一覧（.env.example を参考にしてください）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると自動 .env 読み込みを無効化

注意:
- パッケージ起動時に自動でプロジェクトルート（.git または pyproject.toml）を探索し、`.env` / `.env.local` を読み込みます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要な API と例）

以下は簡単な Python スニペット例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続の取得と ETL 実行（日次 ETL）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は環境変数で上書き可能
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を計算して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("data/kabusys.duckdb"))
# OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数を渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- 市場レジーム判定（ETF 1321 + マクロニュース）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を監査DB用に使うか別パスを指定
conn = init_audit_db(settings.duckdb_path)
# これで signal_events / order_requests / executions 等の作成が済む
```

- ファクター計算や Research ユーティリティ:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

---

## 注意点 / 運用上のポイント
- OpenAI 呼び出しは外部 API 利用になります。APIキー管理とコストに注意してください。score_news / score_regime はリトライとフォールバック（失敗時はスコア=0）を備えていますが、レートやコストには配慮してください。
- J-Quants API はレート制限（120 req/min）管理とトークンリフレッシュを組み込んでいます。ID トークンは内部でキャッシュされます。
- ETL の品質チェックは Fail-Fast せず問題を収集して返します。呼び出し側で対応方針（停止/通知等）を決めてください。
- news_collector は RSS 収集で SSRF/大容量応答/XML攻撃対策を組み込んでいます。本番で追加ソースを登録する前に動作確認をお勧めします。

---

## ディレクトリ構成（主要ファイル）
以下はパッケージ内の主要モジュール一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py — 環境変数/設定管理、自動 .env 読み込み
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + 保存関数
    - pipeline.py — ETL パイプライン実装（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポートインターフェース
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - news_collector.py — RSS 収集
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（z-score）
    - audit.py — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py — ファクター計算 (momentum/value/volatility)
    - feature_exploration.py — 将来リターン/IC/統計サマリー
  - ai/、research/、data/ 以下にそれぞれの機能実装があります

---

## テスト・開発時のヒント
- 自動 .env 読み込みを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI の呼び出し関数は内部でモジュールごとにラップされており、ユニットテストでは該当関数をモック（patch）することで外部呼び出しをスタブ可能です（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB に対する executemany では空リストを渡すと問題になるバージョンがあるため、ライブラリ実装側で空チェックを行っています。テスト用に in-memory DB (":memory:") を使うことができます。

---

必要であれば、README にサンプル .env.example、詳細な CLI の起動方法や systemd / cron での運用例、より詳しい API リファレンスを追記します。どの情報がさらに必要か教えてください。