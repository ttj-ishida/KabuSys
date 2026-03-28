# KabuSys

日本株向けのデータプラットフォーム／自動売買補助ライブラリです。  
DuckDB をデータストアとして利用し、J-Quants API からの ETL、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（発注トレーサビリティ）などを提供します。

主な用途
- 日次 ETL（株価・財務・市場カレンダー）の取得・保存・品質チェック
- RSS ニュース収集と LLM を用いた銘柄センチメント算出（ai_score）
- 市場レジーム判定（MA200 と マクロニュースの LLM センチメントの合成）
- 研究用ファクター算出（モメンタム・ボラティリティ・バリュー等）
- 監査用テーブル（シグナル → 発注 → 約定のトレーサビリティ）初期化ユーティリティ

---

## 機能一覧

- 環境変数管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須変数未設定時に明示的なエラー

- データ ETL（kabusys.data.pipeline / etl）
  - J-Quants API から差分取得、DuckDB への冪等保存
  - 市場カレンダー ETL、株価日足 ETL、財務データ ETL
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策、gzip 上限、トラッキング除去）
  - テキスト前処理、記事ID（SHA-256 ベース）の冪等化

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出
  - バッチ処理、レスポンス検証、リトライ（指数バックオフ）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離 + マクロニュース LLM センチメントの合成
  - DuckDB への冪等書き込み

- 研究用（kabusys.research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン、IC（Spearman）計算、Zスコア正規化、統計サマリー

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - すべて UTC 保存、冪等的初期化機能

---

## セットアップ手順

1. Python 環境を準備（推奨: venv）
   - Python 3.10+ を想定（型注釈に | を使用しているため 3.10+ が望ましい）

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   - 必須（プロジェクト内参照に基づく最小セット）
     - duckdb
     - openai
     - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して pip install -e . などで管理してください。

3. 環境変数設定
   - プロジェクトルートに `.env`（開発）や `.env.local`（ローカル上書き）を作成すると自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン（必須）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）

   任意 / デフォルトあり
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡易サンプル）

以下は主要ユーティリティの簡単な使い方例です。いずれも duckdb の接続を作成し、該当関数を呼び出します。

- 共通インポート例
```python
import duckdb
from datetime import date

# パッケージ内機能を直接インポートして使用
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.audit import init_audit_db
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime
```

- 日次 ETL を実行（株価・財務・カレンダーを差分取得）
```python
conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）を算出
```python
conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY が環境で設定されている想定
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定を実行
```python
conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions 等のテーブルが作成されます
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
```

注意点
- OpenAI 呼び出しを行う関数（score_news, score_regime 等）は OPENAI_API_KEY を参照します。api_key 引数で明示的に渡すことも可能です。
- ETL / API 呼び出しにはネットワークアクセスが必要です。J-Quants の認証情報（リフレッシュトークン）が必須です。
- DuckDB 側のスキーマ作成・マイグレーションは別途スキーマ初期化ロジックが必要です（プロジェクト内別モジュールで管理されている想定）。

---

## ディレクトリ構成（抜粋）

（src/kabusys 以下の主要ファイル・モジュール一覧）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLU / OpenAI バッチ処理
    - regime_detector.py     # 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py # 市場カレンダー管理・営業日ロジック
    - etl.py                 # ETL 再エクスポート（ETLResult 等）
    - pipeline.py            # ETL パイプラインと run_daily_etl 等
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - quality.py             # 品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py               # 監査ログ（テーブル定義・初期化）
    - jquants_client.py      # J-Quants API クライアント（取得・保存関数）
    - news_collector.py      # RSS ニュース収集・前処理
  - research/
    - __init__.py
    - factor_research.py     # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py # 将来リターン / IC / 統計サマリー

---

## 追加メモ・運用上の注意

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。プロジェクト外での実行時は自動ロードされない場合があります。
- 自動ロードを無効にする環境変数:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- J-Quants API のレート制限（120 req/min）を考慮した実装が含まれています（RateLimiter）。
- OpenAI 呼び出しではリトライ（429/5xx/ネットワーク等）や JSON 検証を行い、失敗時はフェイルセーフ（スコア 0.0 やスキップ）で継続する設計です。
- DuckDB の一部バージョンに依存する挙動（executemany の空リスト等）に対する回避策が実装されています。

---

この README はコードベースの主要機能と利用方法をまとめたものです。実際の導入時は環境変数や DuckDB スキーマ定義、外部サービス（J-Quants / OpenAI）の認証情報管理を十分に行ってください。さらに詳しい API 仕様や運用手順は別途ドキュメント（Design/Platform 文書）を参照してください。