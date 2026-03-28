# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、取引基盤・リサーチ基盤の主要機能を含みます。

## 特徴（概要）
- J-Quants API 経由の株価・財務・上場情報・市場カレンダー取得（レートリミット・リトライ・トークンリフレッシュ対応）
- DuckDB を用いた ETL パイプライン（差分取得、冪等保存、品質チェック）
- RSS ベースのニュース収集と前処理（SSRF・サイズ上限・トラッキング除去対応）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）およびマクロセンチメント評価
- ETF とマクロセンチメントを組み合わせた市場レジーム判定（bull / neutral / bear）
- リサーチ向けファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索ユーティリティ
- 監査ログ（signal → order_request → executions のトレーサビリティ）を提供する監査スキーマ初期化ユーティリティ
- 環境変数 / .env による設定管理（自動ロード機能あり）

---

## 主な機能一覧
- kabusys.config
  - 環境変数の自動ロード（.env / .env.local）、必須変数チェック、設定ラッパー（settings）
- kabusys.data.jquants_client
  - J-Quants からのデータ取得（prices、financials、calendar、listed info）
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar など）
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（ETL 一括実行）
  - ETL 結果を返す ETLResult
- kabusys.data.news_collector
  - RSS 取得、前処理、raw_news への保存（SSRF 対策・gzip 対応・サイズ制限）
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合の品質チェック（QualityIssue を返す）
- kabusys.data.calendar_management
  - 市場カレンダーの判定・前後の営業日取得・カレンダー更新ジョブ
- kabusys.data.audit
  - 監査ログ用テーブル・インデックスの初期化、init_audit_db ユーティリティ
- kabusys.ai.news_nlp
  - ニュース記事を銘柄別に集約し OpenAI でセンチメントスコアを算出して ai_scores に保存する score_news()
- kabusys.ai.regime_detector
  - 1321（ETF）200日MA乖離とマクロセンチメントを組み合わせて市場レジームを判定する score_regime()
- kabusys.research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- ユーティリティ
  - data.stats.zscore_normalize 等の統計ユーティリティ

---

## セットアップ手順（開発 / 実行）
1. Python 環境の用意（3.9+ を想定）
2. 必要パッケージのインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトの他依存は用途に応じて追加してください）

3. 環境変数／.env の用意  
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env`（および任意で `.env.local`）を置くと、自動的に読み込まれます（※自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   例: `.env`（必須項目は用途に応じて設定）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=xxxxx

   # OpenAI（AI 機能を使う場合）
   OPENAI_API_KEY=sk-...

   # kabuステーション API（注文実行等を行う場合）
   KABU_API_PASSWORD=your_kabu_password
   # KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知等）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678

   # DB パス（任意、デフォルトあり）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # システム環境
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   必須となる主要環境変数（使用する機能により必須が変わります）
   - JQUANTS_REFRESH_TOKEN（jquants_client）
   - OPENAI_API_KEY（ai.news_nlp / ai.regime_detector を使う場合）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知を使う場合）
   - KABU_API_PASSWORD（kabu ステーションを使う場合）

4. プロジェクトルートの検出について  
   config モジュールは .env 自動読み込みの際、.git または pyproject.toml を起点にプロジェクトルートを探索します。CWD に依存せずパッケージ配布後も安定して動作します。

---

## 使い方（主要なコード例）
以下は代表的な利用方法（DuckDB を利用した例）です。

- DuckDB 接続を作り ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は .env またはデフォルトから決定される Path
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコアリングする
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数または api_key 引数で指定可能
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written scores: {n_written}")
```

- 市場レジームを判定して保存する
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を使って監査 DB を初期化する例
audit_conn = init_audit_db(settings.duckdb_path)
```

- 研究用ファクター計算の利用例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

注意:
- AI 呼び出し（OpenAI）は API キーが必要です。api_key 引数を関数に渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- ETL / API 呼び出しはネットワーク・API レート制限等の影響を受けます。ログを確認して運用してください。

---

## 設定（settings）について
kabusys.config.Settings にアクセスすると設定値を取得できます。主なプロパティ:
- jquants_refresh_token, kabu_api_password, kabu_api_base_url
- slack_bot_token, slack_channel_id
- duckdb_path, sqlite_path
- env（development | paper_trading | live）, log_level（DEBUG/INFO/...）
- is_live / is_paper / is_dev（ブール）

必須項目が未設定の場合、Settings は ValueError を発生させます。

自動 .env ロードの制御:
- デフォルトで .env, .env.local をプロジェクトルートから読み込みます。
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下の主要モジュール）
- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュースセンチメント（銘柄別）score_news()
    - regime_detector.py  -- ETF + マクロでレジーム判定 score_regime()
  - data/
    - __init__.py
    - jquants_client.py   -- J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py         -- ETL パイプライン / run_daily_etl 等
    - etl.py              -- ETLResult の再エクスポート
    - news_collector.py   -- RSS 収集・前処理
    - quality.py          -- データ品質チェック（missing/spike/duplicates/date_consistency）
    - calendar_management.py -- 市場カレンダー管理（is_trading_day 等）
    - audit.py            -- 監査ログスキーマ初期化 / init_audit_db
    - stats.py            -- zscore_normalize 等統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  -- calc_momentum, calc_value, calc_volatility
    - feature_exploration.py -- calc_forward_returns, calc_ic, factor_summary, rank

各モジュールはドメイン単位に分かれており、データ取得 → ETL → 品質チェック → リサーチ → 実行（オーダー） のパイプラインを組み立てやすい設計です。

---

## 運用上の注意 / ヒント
- Look-ahead バイアス対策が設計に組み込まれています（日時の扱い、ETL の差分取得、fetched_at の記録など）。バッチ実行やバックテスト時は target_date を明示的に与えることを推奨します。
- OpenAI 呼び出しは費用が発生します。バッチ単位／レートを考慮して運用してください。
- J-Quants API はレート制限とトークン期限があるため、get_id_token / _request により自動リフレッシュとレート制御が組み込まれています。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、該当処理は空チェックを行っています。
- 監査ログは削除しない運用を前提に設計されています（FK は ON DELETE RESTRICT）。

---

## 貢献 / 開発
- ソースは src/kabusys 配下にモジュールとして整理されています。ユニットテストやモックを使った API 呼び出しの差し替えがしやすい設計です（内部の _call_openai_api や _urlopen などはテストで差し替え可能）。
- コードにログ出力が豊富にあるため、実行ログを活用して問題解析してください。

---

もし README に加えたい具体的な使い方（例: バッチスクリプト、Dockerfile、CI 設定、サンプル .env.example）や、特定モジュールの詳細ドキュメントを希望する場合はお知らせください。必要に応じてその内容を追加します。