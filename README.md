# KabuSys

日本株向けのデータプラットフォーム兼自動売買リサーチ基盤（KabuSys）。  
ETL（J-Quants からの株価・財務・カレンダー取得）・データ品質チェック・ニュース収集・LLM を用いたニュースセンチメント付与・市場レジーム判定・ファクター計算・監査ログ（発注トレーサビリティ）等の機能を備えたライブラリ群です。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API クライアント（認証、ページネーション、レートリミット、リトライ）
  - 差分 ETL（株価日足 / 財務 / 市場カレンダー）
  - ETL 結果を表す ETLResult 型

- データ保存・品質管理
  - DuckDB を前提とした永続化ユーティリティ（raw_prices, raw_financials, market_calendar など）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 市場カレンダー管理（営業日判定・前後営業日取得・カレンダー更新ジョブ）

- ニュース収集・NLP
  - RSS フィードからの安全なニュース収集（SSRF 対策、サイズ制限、トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント付与（ai_scores）
  - LLM 呼び出しに対する堅牢なリトライ・レスポンス検証

- 市場レジーム判定
  - ETF（1321）200 日MA 乖離とマクロニュースの LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を算出・保存

- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ

- 監査・トレーサビリティ
  - シグナル→発注要求→約定までを追える監査スキーマ（DuckDB にテーブルとインデックスを初期化）
  - 発注の冪等性を考慮した設計

---

## 要件（推奨）

- Python 3.10 以上（ソース内で `X | None` 型アノテーションを使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt があればそれを使用してください。なければ下記の最小インストール例を参照）

---

## セットアップ手順

1. リポジトリをクローン（このプロジェクトルートは .git または pyproject.toml を想定）
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成して有効化
   (例: venv)
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   最低限:
   ```
   pip install duckdb openai defusedxml
   ```
   開発インストール（パッケージ化されている場合）:
   ```
   pip install -e .
   ```

4. 環境変数の設定
   プロジェクトルートの `.env` または OS 環境変数で必要なパラメータを設定します。自動で `.env` / `.env.local` を読み込む仕組みがあります（テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注等に利用）
   - SLACK_BOT_TOKEN: Slack 通知用トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で利用）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   ```

5. データベースディレクトリ作成（必要に応じて）
   デフォルトの DuckDB ファイルパス: `data/kabusys.duckdb`  
   監査用 DB のデフォルトパス: `data/monitoring.db`

---

## 初期化例（監査スキーマ作成 / DB 接続）

Python REPL またはスクリプトで DuckDB 接続を作り、監査スキーマを初期化します。

```python
import duckdb
from kabusys.data import audit

# ファイル DB を作成して監査スキーマを初期化
conn = audit.init_audit_db("data/monitoring.db")
# または既存の接続に対してテーブルを追加
# conn = duckdb.connect("data/kabusys.duckdb")
# audit.init_audit_schema(conn)
```

---

## 使い方（主な API 例）

- 日次 ETL を実行（J-Quants から価格・財務・カレンダー取得、品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメント付与（ai_scores へ書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究ユーティリティの利用例

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
forward = calc_forward_returns(conn, target_date=date(2026, 3, 20))
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- 市場カレンダー / 営業日ヘルパー

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

注意点:
- LLM 呼び出し（OpenAI）を行う関数は API キーを直接引数で渡すか、環境変数 `OPENAI_API_KEY` を利用します。
- 日付参照は全てルックアヘッドバイアスを避ける設計になっており、関数は内部で `date.today()` や `datetime.today()` を参照しないように配慮されています（引数で日付を渡すことが推奨）。

---

## 環境変数 / 設定の詳細

- 自動 .env ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動で読み込みます。
  - 読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

- 主な設定は `kabusys.config.settings` 経由で取得可能です（例: `settings.jquants_refresh_token`, `settings.duckdb_path`, `settings.env` など）。

---

## ディレクトリ構成（主要ファイルの説明）

（src 配下を想定）

- src/kabusys/
  - __init__.py
    - パッケージ公開 API（data, strategy, execution, monitoring を __all__ に定義。strategy 等は別途実装想定）
  - config.py
    - 環境変数/.env 読み込みと Settings クラス（各種設定をプロパティで取得）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約して OpenAI に投げ、ai_scores テーブルへ書き込む
    - regime_detector.py
      - ETF(1321)のMA200乖離とマクロニュースの LLM センチメントを合成して market_regime へ書き込む
  - data/
    - __init__.py
    - calendar_management.py
      - 市場カレンダー管理、営業日判定・前後営業日取得・更新ジョブ
    - pipeline.py
      - 日次 ETL パイプライン実装（run_daily_etl 等）
    - etl.py
      - ETLResult の再エクスポート
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / 認証・リトライ・レート制御）
    - news_collector.py
      - RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策等）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize など汎用統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）DDL + 初期化処理
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / バリュー / ボラティリティ等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC, ランク付け、統計サマリ

---

## 開発 / テストについて

- LLM や外部 API 呼び出し部分（OpenAI / J-Quants / HTTP）については、ユニットテストでモック化しやすい設計（内部 API 呼び出しをラップしている関数をパッチ）になっています。
- 自動 .env ロードを無効化して環境依存を切る場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ライセンス / 貢献

- ライセンス情報や貢献ガイドについてはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（このリポジトリに該当ファイルがある場合）。

---

README の内容はコードベース（src/kabusys 配下）からの抜粋説明に基づき作成しています。実運用やデプロイ時は API キーや機密情報の取り扱い、バックテスト時のルックアヘッド対策（データのタイムトラベリング）に十分注意してください。