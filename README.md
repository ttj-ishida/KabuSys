# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
データ収集（J-Quants, RSS）、ETL、データ品質チェック、研究用ファクター計算、ニュースのL​LMベース評価、マーケットレジーム判定、監査ログ（発注→約定トレース）等を一貫して提供します。

主な設計方針
- ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB を中心としたローカルデータベース設計（ETLは冪等性を重視）
- 外部API呼び出しはリトライ／バックオフやレート制御を備えた堅牢な実装
- セキュリティ配慮（RSS の SSRF対策・XML攻撃対策、環境変数管理）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）。無効化フラグあり。
- データ収集 / ETL
  - J-Quants API クライアント（株価日足・財務・マーケットカレンダー）
  - 差分取得、ページネーション、安全なリクエスト／トークンリフレッシュ、保存（DuckDB）
  - ETL パイプライン（run_daily_etl）と個別 ETL（prices / financials / calendar）
- ニュース収集
  - RSS 収集（トラッキング除去、URL正規化、SSRF対策、defusedxml利用）
  - raw_news への冪等保存、銘柄紐付け
- ニュース NLP（LLM を用いたセンチメント）
  - 銘柄単位で記事を集約して OpenAI に投げ、ai_scores に保存（score_news）
  - 再試行・バッチ処理・レスポンス検証機構を搭載
- 市場レジーム判定
  - ETF(1321) の MA200 乖離とマクロニュースの LLMセンチメントを重み付けして日次レジーム判定（score_regime）
- 研究用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合チェック（run_all_checks）
- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブルDDL と初期化ユーティリティ
  - 監査DBの初期化関数（init_audit_db / init_audit_schema）

---

## 必要条件（推奨）

- Python 3.10+（構文：型ヒントで PEP 604 を使用）
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

※ 実行環境に合わせて requirements.txt を用意してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
   - プロジェクトルートに `.git` または `pyproject.toml` があることを想定しています（自動 .env ロードに利用）。

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - プロジェクトに requirements.txt があれば:
     ```
     pip install -r requirements.txt
     ```

4. 環境変数の設定
   - ルートに `.env` / `.env.local` を配置すると自動で読み込まれます（package import 時にプロジェクトルート検出して読み込み）。
   - 自動読み込みを無効化するには環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な主な環境変数（例）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY : OpenAI APIキー（score_news / score_regime で使用。関数引数からも渡せます）
     - KABU_API_PASSWORD : kabuステーション API パスワード（発注系で使用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : 監視通知用
     - DUCKDB_PATH (デフォルト `data/kabusys.duckdb`)
     - SQLITE_PATH (デフォルト `data/monitoring.db`)
     - KABUSYS_ENV : development / paper_trading / live
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL

   例の .env（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベースの準備
   - DuckDB ファイルは settings.duckdb_path（環境変数 DUCKDB_PATH）を参照します。該当ディレクトリがなければモジュール内で作成される処理もあります（audit.init_audit_db などでディレクトリ自動作成）。

---

## 使い方（簡単な例）

下記は Python REPL やスクリプトからの利用例です。適切に環境変数を設定した上で実行してください。

- DuckDB 接続と ETL を実行する（日次ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# 今日分の ETL を実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（前日15:00〜当日08:30 JST の窓）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 を参照）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 研究用ファクター計算例
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

- 監査データベース初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンに設定されます
```

---

## 注意点 / 実運用上のポイント

- OpenAI 呼び出し
  - news_nlp と regime_detector は OpenAI を使用します。APIキーは引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
  - レスポンスの検証、jsonパースのフェイルセーフ処理、リトライロジックを備えていますが、API利用コスト・レート制限に注意してください。

- J-Quants API
  - rate limit（120 req/min）をモジュールで調整しています。認証トークンは refresh トークンから ID トークンを取得する仕組みです（自動リフレッシュ）。

- セキュリティ
  - RSS 取得には SSRF 防止、URL 正規化、XML攻撃対策を組み込んでいます。
  - 環境変数の取り扱い（.env 自動読み込み）により、機密情報はファイルおよび環境で管理してください。自動ロードを無効化するフラグあり（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

- ルックアヘッドバイアス回避
  - バックテストや研究で重要な設計として、内部ロジックはターゲット日以前のデータのみ参照するよう注意されています（関数は target_date を引数に取る等）。

---

## ディレクトリ構成（概要）

以下は主要なパッケージ構成の抜粋です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースの LLM スコアリング
    - regime_detector.py               — マクロ＋MA200 合成によるレジーム判定
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETL 結果型エクスポート（ETLResult）
    - news_collector.py                — RSS 収集と保存
    - calendar_management.py           — 市場カレンダー管理・営業日ロジック
    - stats.py                         — zscore_normalize 等統計ユーティリティ
    - quality.py                       — データ品質チェック
    - audit.py                         — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py               — momentum / volatility / value 等
    - feature_exploration.py           — forward returns, IC, summary 等
  - ai/、research/、data/ の内部はさらに細分化された関数群を提供

---

## 開発・テスト

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行います。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants の外部依存はユニットテストでモック化しやすいように実装されています（内部の _call_openai_api や _urlopen などを patch 可能）。
- DuckDB を使っているためテストでは ":memory:" を指定するとインメモリ DB が使えます。

---

## 参考（主な公開 API）

- 環境設定
  - from kabusys.config import settings

- ETL / Data
  - kabusys.data.pipeline.run_daily_etl(...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
  - kabusys.data.news_collector.fetch_rss

- AI
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- Research
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.stats.zscore_normalize

- Audit
  - kabusys.data.audit.init_audit_db(path)
  - kabusys.data.audit.init_audit_schema(conn, transactional=False)

---

もし README に追加したい項目（例: 実運用での Cron / Airflow の設定例、より詳しい .env.example、requirements.txt、API利用コストについての注意など）があれば、それに合わせて追記します。