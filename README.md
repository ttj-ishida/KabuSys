# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のライブラリ群です。  
ETL（J-Quants 経由の価格/財務/カレンダー取得）・データ品質チェック・ニュース収集・AI ベースのニュースセンチメント評価・市場レジーム判定・研究用ファクター算出・監査ログ（発注→約定トレーサビリティ）等を含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を提供します。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- raw データに対する品質チェック（欠損・重複・スパイク・日付整合性）
- RSS ベースのニュース収集と銘柄紐付け
- OpenAI を利用したニュースセンチメント（銘柄ごと）とマクロセンチメントの推定
- 日次の市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究（リサーチ）用のファクター算出／特徴量探索ユーティリティ
- 監査ログ周り（signal → order_request → executions のトレース可能な DB スキーマ）

設計上の特徴：
- ルックアヘッドバイアスを避ける実装（日時参照・クエリ条件の扱いに配慮）
- DuckDB を主要なデータストアとして想定
- J-Quants / OpenAI 呼び出しにリトライ・レート制御を実装
- DB への保存は冪等化（ON CONFLICT）を基本

---

## 機能一覧（抜粋）

- data
  - jquants_client: J-Quants API からの取得・DuckDB への保存（raw_prices / raw_financials / market_calendar 等）
  - pipeline: 日次 ETL の統合エントリポイント（run_daily_etl）
  - quality: データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - news_collector: RSS 収集と前処理、SSRF 対策、記事ID生成
  - calendar_management: 営業日判定・next/prev_trading_day 等のユーティリティ、calendar_update_job
  - audit: 監査ログテーブルの初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースの LLM スコアを合成して market_regime に書き込み
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件 / 依存関係

- Python 3.10+
- 主要ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml

README に記載の最新の依存は pyproject.toml / requirements.txt に合わせてください（本コードは src レイアウト）。

---

## セットアップ手順

1. リポジトリをクローン（例）

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（例）

   ```
   python -m venv .venv
   source .venv/bin/activate  # mac/linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存をインストール

   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # またはパッケージ化されている場合は
   pip install -e .
   ```

4. 環境変数を設定（.env をプロジェクトルートに置くことを想定）

   必須（アプリ起動/ETL/AI 呼び出しに必要なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（本実装で参照されている）
   - SLACK_BOT_TOKEN: Slack 通知用トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   OpenAI を使う場合:
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime のデフォルト参照）

   任意:
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite DB（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development|paper_trading|live（デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動で .env を読み込まない

   例 `.env`（プロジェクトルート）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

   補足: パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします。

---

## データベース初期化

監査ログ専用 DB を初期化する例:

```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作る場合
conn = init_audit_db("data/audit.duckdb")

# またはインメモリ
conn = init_audit_db(":memory:")
```

監査スキーマのみ既存の DuckDB 接続に追加する場合:

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 使い方（主要な例）

以下は最小限の利用例です。各関数は DuckDB 接続（duckdb.connect() の返り値）を受け取ります。

1) 日次 ETL を実行する（run_daily_etl）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ETL はカレンダー → 株価 → 財務 → 品質チェック の順で実行します。
- J-Quants 認証は settings.jquants_refresh_token（または id_token 引数）を使用します。

2) ニュースセンチメントをスコアリングして ai_scores に書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
print("written:", n_written)
```

- api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定してください。
- 設計上、対象ウィンドウは JST 前日 15:00 ～ 当日 08:30（UTC に変換して処理）です。

3) 市場レジームを判定して market_regime に書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
```

- ETF (1321) の MA200 乖離とマクロニュースの LLM スコアを合成して 'bull'/'neutral'/'bear' を判定・保存します。

4) 研究用ファクター算出（例: momentum）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は list[dict]（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

5) データ品質チェックを個別実行:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for issue in issues:
    print(issue)
```

---

## コマンドライン / バッチ運用のヒント

- ETL を cron / Airflow / 他スケジューラで日次実行する想定です。
- 環境変数（.env）から設定をロードするため、CI / 本番環境では適切に環境を注入してください。
- OpenAI 呼び出しはレートとコストに注意（news_nlp はバッチ化して最大 _BATCH_SIZE=20 銘柄／呼び出し）。

---

## 設計上の注意点

- ルックアヘッドバイアス回避のため、内部実装は datetime.today()/date.today() を直接使わないよう配慮しています（target_date を引数で受ける）。
- 外部 API 呼び出しはリトライやレート制御を備え、API 失敗時はフォールバック（例: LLM の失敗 = スコア 0）することが多い設計です。
- DuckDB への保存は基本的に ON CONFLICT（冪等）で行います。部分失敗時に既存データを誤って消さないための工夫が各所にあります。
- ニュース収集では SSRF 対策・受信サイズ制限・XML パースの安全化（defusedxml）を行っています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                           — 環境変数 / 設定読み込み
- ai/
  - __init__.py
  - news_nlp.py                       — ニュースセンチメント（ai_scores 生成）
  - regime_detector.py                — 市場レジーム判定（market_regime 生成）
- data/
  - __init__.py
  - jquants_client.py                 — J-Quants API クライアント & 保存処理
  - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
  - quality.py                        — データ品質チェック
  - news_collector.py                 — RSS 収集・前処理
  - calendar_management.py            — 市場カレンダー管理（営業日判定など）
  - stats.py                          — zscore_normalize 等
  - audit.py                          — 監査ログスキーマ初期化
  - etl.py                            — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py                — Momentum/Value/Volatility 等
  - feature_exploration.py            — forward returns, IC, summaries
- research/（その他ファイル群）
- monitoring/（本リストに含まれないが監視系モジュールが入る想定）
- strategy/, execution/（README 先頭 __all__ に記載された主要パッケージ群のための場所）

（実際のファイル・モジュールは src 配下を参照してください）

---

## テスト / 開発時の便利な設定

- 自動で .env を読み込みたくない場合：
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等で便利）。
- OpenAI 呼び出しをユニットテストで置き換える：
  - モジュール内部の _call_openai_api を unittest.mock.patch などで差し替えられるよう実装されています。

---

## 最後に

本 README はリポジトリ内のモジュールから抽出した要点をまとめたものです。細かい引数や返り値、エラーハンドリング等は各モジュール（src/kabusys/**）の docstring を参照してください。必要であればサンプルスクリプトやデプロイ手順、CI 設定のテンプレートも作成しますので要求を教えてください。