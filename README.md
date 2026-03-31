# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。ETL（J-Quants 経由の株価/財務/カレンダー取得）、ニュース収集・NLPによるセンチメント付与、研究用ファクター計算、監査ログ（発注〜約定トレース）、市場レジーム判定などの機能を提供します。

---

主な対象:
- DuckDB をデータレイヤーに用いたデータパイプライン／研究環境
- J-Quants API を用いたデータ取得
- OpenAI（gpt-4o-mini）を用いたニュース NLP / マクロセンチメント評価
- kabuステーション等の発注層との統合を想定した監査ログ設計

---

前提
- Python 3.10+
- DuckDB, OpenAI Python SDK, defusedxml 等のライブラリが必要（下記セットアップ参照）

---

機能一覧
- データ ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPXカレンダーを差分取得・保存（duckdb）
  - 差分取得・バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL の高レベル関数: run_daily_etl
- ニュース収集
  - RSS 取得・前処理・SSRF/サイズ対策・記事ID正規化
  - raw_news テーブルへ冪等保存、news_symbols との紐付け（news_collector）
- ニュース NLP / マクロ判定（OpenAI）
  - 銘柄別ニュースをまとめて LLM へ投げ ai_scores テーブルへ保存（news_nlp.score_news）
  - マクロ記事とETF（1321）の200日移動平均乖離を組み合わせて市場レジーム判定（ai.regime_detector.score_regime）
  - 両モジュールは JSON Mode を前提とした堅牢なバリデーション／リトライ実装
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー（research.feature_exploration）
  - z-score 正規化ユーティリティ（data.stats.zscore_normalize）
- カレンダー管理
  - market_calendar を用いた営業日判定・前後営業日取得・レンジ取得（data.calendar_management）
  - JPX カレンダーの差分更新ジョブ（calendar_update_job）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）
  - 監査テーブルは冪等かつ UTC タイムゾーンで保存
- J-Quants クライアント（data.jquants_client）
  - rate limiter、トークン自動リフレッシュ、ページネーション、DuckDB への冪等保存（save_* 関数）

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone ... など

2. Python 環境
   - Python 3.10 以上を用意（venv 推奨）
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - requirements.txt が無い場合は主要依存をインストールしてください:
     - pip install duckdb openai defusedxml
   - 必要に応じて追加ライブラリ（例: requests 等）を導入してください。

4. 環境変数（.env）
   - プロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabu API 用パスワード
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack 送信先チャンネル ID
   - 任意／デフォルト設定
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - DUCKDB_PATH           : data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH           : data/monitoring.db（デフォルト）
     - OPENAI_API_KEY        : OpenAI 呼び出し時に使用（score_news / score_regime に渡さない場合必須）

   例（.env）
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

---

使い方（簡単なコード例）
- DuckDB 接続を作り ETL を実行する例:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使う場合:
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

# 今日の ETL を実行
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- news_nlp によるスコア付与（OpenAI APIキーは環境変数 OPENAI_API_KEY または引数で指定）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # Noneで環境変数参照
print(f"scored {count} symbols")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を利用
```

- 監査 DB の初期化（専用 DB を作り監査スキーマを作成）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# conn は監査テーブルが初期化された DuckDB 接続
```

- カレンダー / 営業日ユーティリティ

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点
- LLM 呼び出しは API レート・エラーに対してリトライとフォールバック（スコア=0 など）を実装していますが、API キーや料金に注意して実行してください。
- DuckDB のバージョン差異により executemany の挙動が異なるため、コード内で互換性対策を行っています。
- モジュールの自動 .env 読み込みはプロジェクトルート探査を行うため、パッケージ配布後やテスト時は必要に応じて無効化してください（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

ディレクトリ構成（主なファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                 : 環境変数 / 設定の管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py             : 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py      : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       : J-Quants API クライアント（fetch / save）
    - pipeline.py             : ETL パイプライン（run_daily_etl など）
    - etl.py                  : ETLResult の公開
    - calendar_management.py  : JPX カレンダー管理・営業日ユーティリティ
    - news_collector.py       : RSS 収集 / 前処理
    - quality.py              : 品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py                : zscore_normalize など統計ユーティリティ
    - audit.py                : 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py      : Momentum / Volatility / Value 等の計算
    - feature_exploration.py  : 将来リターン・IC・統計サマリー
  - monitoring/ (README のコードには monitoring モジュールが __all__ に含まれますが省略されている可能性があります)

（上記はソース内ドキュメントを要約したもので、詳細は各モジュールの docstring を参照してください）

---

貢献・拡張
- 新しいデータソース追加、NLP のプロンプト改善、戦略実行層（execution）との結合は想定されており、モジュール分離と冪等性を重視して実装されています。
- テストを書く際は .env 自動読み込みを無効化し、関数に明示的に API キーや接続を渡すことで副作用を抑えてください。

---

ライセンス・注意
- この README はコードベースの説明のためのものです。運用（特に実口座での発注）を行う際は十分なテストとリスク管理を行ってください。