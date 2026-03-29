# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB を用いたデータプラットフォーム、J-Quants からの ETL、ニュース収集・NLP（OpenAI）によるスコアリング、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム・データ基盤で使うための共通ユーティリティ群を提供します。主な目的は以下です。

- J-Quants API を用いた株価・財務・マーケットカレンダー等の差分 ETL（DuckDB への永続化）
- RSS を用いたニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロセンチメントのスコアリング（AI モジュール）
- リサーチ用途のファクター計算・特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 取引フローをトレースする監査ログスキーマ（signal → order_request → execution）
- 環境変数 / .env 読み込みや設定管理

設計上、バックテストや運用における「ルックアヘッドバイアス」を避ける実装方針が採られています（date の取扱い、ETL/スコアリングでの明示的な target_date 指定など）。

---

## 主な機能一覧

- 環境設定管理（kabusys.config.settings）
  - .env / .env.local の自動読み込み（無効化可能）
  - 必須設定の検証
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API クライアント（kabusys.data.jquants_client）
  - market_calendar 更新ジョブ（kabusys.data.calendar_management）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、前処理、raw_news への冪等保存想定
- データ品質チェック（kabusys.data.quality）
  - 欠損 / スパイク / 重複 / 日付不整合の検出
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルの初期化とユーティリティ
- AI（kabusys.ai）
  - score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）200日 MA 乖離 + マクロニュースで市場レジーム判定
- リサーチ（kabusys.research）
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントで `X | Y` を使用）
- 必要なネイティブ依存は duckdb などがあるため pip install 時にビルドやバイナリが使われます

1. リポジトリをクローン（またはローカルに配置）  
   例:
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール  
   requirements.txt がある場合はそれを使ってください。無ければ少なくとも以下をインストールしてください:
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクトを editable install する場合:
   ```
   pip install -e .
   ```

4. 環境変数（.env）を準備  
   プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   推奨される `.env`（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要ユースケース）

以下はサンプルコード（Python）と説明です。各関数は duckdb 接続および明示的な target_date 引数を取ることでルックアヘッドを防いでいます。

1) DuckDB 接続を作る（デフォルトファイルは settings.duckdb_path）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl はカレンダー、株価、財務の差分取得および品質チェックを順に行います。
- ETL の実行時に J-Quants 認証トークンは settings.jquants_refresh_token から自動で取得されます（get_id_token を内部で呼ぶ）。

3) ニュースセンチメントを生成して ai_scores に保存する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使うなら api_key=None
print(f"written: {n_written}")
```

4) 市場レジーム判定を実行する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は list[dict]（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

6) 監査ログ（監査DB）初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# init_audit_schema は既に実行され、テーブルが作成される
```

7) J-Quants API の直接利用（必要に応じて）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings

id_token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=id_token, date_from=date(2026,3,1), date_to=date(2026,3,20))
```

注意点:
- OpenAI 呼び出しは `OPENAI_API_KEY` または各関数の `api_key` 引数で渡します。
- ETL / AI 呼び出しは外部 API へアクセスするため、ネットワークと API キーの用意が必要です。
- ETL 実行時は DuckDB に必要なスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime など）が存在することが前提です。初期スキーマ作成ユーティリティが別途用意されている場合はそちらを使用してください。

---

## 環境変数（主なキー）

必須（Settings で require される）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack のチャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV — environment（development / paper_trading / live）デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）

---

## ディレクトリ構成

（主要ファイルのみ抜粋、実際のリポジトリには他のサポートファイルも存在する可能性があります）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP スコアリング（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETL インターフェース（ETLResult）
    - news_collector.py      -- RSS ニュース収集
    - calendar_management.py -- 市場カレンダー管理
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - audit.py               -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py -- 将来リターン計算・IC・統計サマリー
  - monitoring/ (存在する場合)
  - execution/ (発注・ブローカ連携モジュール等、将来的に存在)
  - strategy/  (戦略実装用インターフェース)
  - monitoring/ (監視用 DB 接続など)

---

## 設計上の注意・ベストプラクティス

- すべての「日付を基準にする」処理は明示的に `target_date` を受け取る設計です。これによりバックテストや再現性のある処理が可能になります。
- OpenAI 呼び出しはリトライ・バックオフ処理やフェイルセーフ（失敗時は中立スコア）を備えていますが、API コストやレート制限には注意してください。
- J-Quants API 呼び出しはレート制限（120 req/min）および 401 の自動リフレッシュ、リトライロジックを組み込んでいます。
- news_collector は SSRF 防止・Gzip ボム対策・トラッキングパラメータ除去などセキュリティを考慮しています。
- DuckDB に対する executemany の空リストバインドの制約など互換性の考慮がコード内に反映されています。

---

## 開発・テスト時のヒント

- 自動 .env 読み込みをテストや CI で無効にする場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI など外部 API 呼び出しはモックして単体テストを作成できます（コード内に patch しやすいように分離されたヘルパーがあります）。
- DuckDB を :memory: で初期化するとテストが容易です:
  ```python
  import duckdb
  conn = duckdb.connect(':memory:')
  ```

---

README は以上です。プロジェクト固有の追加ドキュメント（スキーマ定義、StrategyModel.md、DataPlatform.md 等）がある場合は併せて参照してください。必要なら README に追記するテンプレート（.env.example、起動スクリプト、初期スキーマ作成手順など）を作成しますか？