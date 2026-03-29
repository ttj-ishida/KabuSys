KabuSys — 日本株データプラットフォーム & 自動売買ユーティリティ
=================================================================

概要
----
KabuSys は日本株向けのデータ収集（ETL）、データ品質チェック、ニュース NLP、研究用ファクター計算、そして自動売買監査ログ（トレーサビリティ）や市場レジーム判定などを含むユーティリティ群を提供する Python パッケージです。DuckDB をデータ層に用い、J-Quants や外部 RSS / OpenAI（LLM）を活用する設計になっています。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を安易に参照しない）
- DuckDB を中心とした SQL + 軽量 Python 実装（外部依存を最小化）
- API 呼び出しはリトライ・レートリミット制御・フェイルセーフを備える
- ETL / 品質チェック / 監査ログは冪等（idempotent）に実行可能

機能一覧
--------
- データ ETL（J-Quants から株価 / 財務 / 市場カレンダーの差分取得・保存）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS から raw_news へ安全に保存）
- ニュース NLP（OpenAI を使った銘柄別センチメントスコア生成）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化等）
- 監査ログ（signal_events / order_requests / executions）テーブルの初期化ユーティリティ
- 市場カレンダー管理（営業日判定 / next/prev_trading_day 等）

必要条件（主な依存）
-------------------
- Python 3.10+
- duckdb
- openai (OpenAI SDK)
- defusedxml
- （標準ライブラリで実装されている部分が多いため外部依存は限定的）

セットアップ手順
----------------

1. リポジトリを取得・インストール（開発モード推奨）
   - ローカル開発:
     - git clone ...
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e ".[dev]" または最低限: pip install -e .

   あるいは最小依存のみ:
     - pip install duckdb openai defusedxml

2. .env の準備
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）に .env を配置すると自動で読み込まれます（環境変数より優先度は低い）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

3. 必要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabus_api_password
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (必要に応じて)
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567
   - OPENAI_API_KEY=sk-...
   - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
   - SQLITE_PATH=data/monitoring.db    (デフォルト)
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   .env 例（.env.example を参考にしてください）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

使い方（主要なユーティリティ）
------------------------------

以下は代表的な利用例です。DuckDB 接続は duckdb.connect() を使って作成します。

1) 日次 ETL を実行する
- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックの順で実行します。

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントをスコア化して ai_scores に保存する
- OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定します。

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

3) 市場レジーム（bull/neutral/bear）を判定して market_regime に保存する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用の DuckDB を初期化する
- 監査テーブル（signal_events, order_requests, executions）を作成します。

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査ログを書き込めます
```

5) 研究用関数（ファクター計算など）
- calc_momentum / calc_volatility / calc_value などは duckdb 接続と target_date を渡して利用します。

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
```

注意点・運用上のポイント
-----------------------
- OpenAI 呼び出しは gpt-4o-mini を想定した実装になっており、JSON Mode レスポンスをパースします。API トークン・コストに注意してください。
- J-Quants API 呼び出しにはレート制限とリトライが組み込まれています。refresh token を設定して get_id_token が利用可能であることを確認してください。
- ETL と品質チェックはフェイルセーフを重視しており、一部のステップでエラーが発生しても可能な限り処理を継続して結果を返します。ETLResult の errors / quality_issues を確認してください。
- ニュース収集（RSS）は SSRF / XML Bomb 対策を実装しています。外部の RSS を追加する際は信頼できるソースを用いてください。
- 自動で .env を読み込みますが、CI やテストで干渉する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。

ディレクトリ構成（主なファイル）
------------------------------

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP（OpenAI を用いた銘柄別スコア）
  - regime_detector.py      — 市場レジーム判定（MA200 + マクロ記事 LLM 合成）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - etl.py                  — ETL 用型の再エクスポート
  - calendar_management.py  — 市場カレンダー管理 & 営業日判定
  - news_collector.py       — RSS 収集（安全対策付き）
  - quality.py              — 品質チェック群（欠損、重複、スパイク、日付整合）
  - stats.py                — 汎用統計ユーティリティ（Z スコア正規化等）
  - audit.py                — 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py      — ファクター算出（モメンタム/バリュー/ボラティリティ）
  - feature_exploration.py  — 将来リターン / IC / 統計サマリー
- monitoring/                 (存在が示唆されるが実装は別ファイルで管理)
- strategy/                  (戦略実装層の格納先)
- execution/                 (発注・証券会社 API 連携の層)

補足（開発・テスト）
------------------
- モジュール内にはテストしやすいように _call_openai_api 等の内部関数をモック可能にしている箇所が多くあります（unittest.mock.patch により差し替え可能）。
- DuckDB の executemany に制約があるバージョンを考慮した実装（空リストの扱い等）が含まれます。

ライセンス
---------
- 本 README ではライセンス情報は含めていません。実プロジェクトでは LICENSE ファイルを追加してください。

最後に
------
この README はコードベースの主要機能と運用上の注意点をまとめたものです。実際の運用では .env の秘匿情報管理、API クレジット消費管理、バックテスト目的での「取得済みデータのみ利用する」運用などに留意してください。質問や補足があればお知らせください。