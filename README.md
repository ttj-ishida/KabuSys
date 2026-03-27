# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ。  
DuckDB をデータストアとして用い、J-Quants API からデータを取得して ETL、ニュース NLP（OpenAI）に基づく銘柄センチメント算出、市場レジーム判定、監査ログ（発注→約定トレーサビリティ）などを提供します。

主な設計方針は「ルックアヘッドバイアスの回避」「冪等性」「フェイルセーフ（API失敗時の安全なフォールバック）」「DuckDB を用いた SQL 中心の処理」です。

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から日次株価（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（ページネーション・リトライ・レート制御対応）
  - ETL 統合エントリポイント（run_daily_etl）と個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェック（欠損・重複・スパイク・日付不整合）の自動検出

- ニュース収集 / NLP
  - RSS 取得時の SSRF 対策、URL 正規化、前処理、raw_news への冪等保存（news_collector）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（news_nlp.score_news）
  - レート制限・リトライ・レスポンスバリデーションを備えた実装

- 市場レジーム判定
  - ETF（1321）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して、日次で市場レジーム（bull/neutral/bear）を判定（ai.regime_detector.score_regime）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 の階層的トレーサビリティ用テーブルを DuckDB に冪等作成（init_audit_schema / init_audit_db）
  - 各種インデックス・制約・ステータス遷移を含む設計

- 研究ユーティリティ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）、将来リターン計算、IC（Spearman）や統計サマリー、Z スコア正規化など（kabusys.research）

- 設定管理
  - .env ファイルまたは環境変数から設定を自動読み込み（kabusys.config）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

## 必要条件 / 依存関係

- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース等）

（実際のパッケージ名・バージョンはプロジェクトの pyproject.toml / requirements ファイルを参照してください）

---

## セットアップ手順

1. リポジトリをクローン／取得し、仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 例:
     - pip install -U pip
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements ファイルや pyproject があればそれに従ってください）

3. パッケージをインストール（開発モード推奨）
   - pip install -e .

4. 環境変数設定（.env をプロジェクトルートに配置）
   - 必須（本コードベースで _require() により参照されるもの）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 推奨 / 任意:
     - OPENAI_API_KEY=...           （score_news / score_regime で使用可能）
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
     - DUCKDB_PATH=data/kabusys.duckdb   （デフォルト）
     - SQLITE_PATH=data/monitoring.db    （デフォルト）
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   .env のパースは bash 風の export KEY=val やクォート、コメント行対応があります。

---

## 使い方（基本例）

下記はライブラリ API を直接呼ぶ Python の簡単な使用例です。実運用ではログ設定や例外処理、スケジューラ（cron / Airflow 等）を組み合わせてください。

- DuckDB 接続を作成して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は .env や環境変数で上書き可能
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
# OPENAI_API_KEY が環境変数に設定されていない場合は api_key 引数を渡すこと
# score_news(conn, date(2026,3,20), api_key="sk-...")
```

- 市場レジーム（market_regime テーブル）を評定する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する（監査専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブル等が作成されます
```

- 研究ユーティリティの呼び出し例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- OpenAI 呼び出しを行う関数（score_news / score_regime）は API キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- DuckDB のスキーマ（テーブル定義）は別途スキーマ初期化コードやマイグレーションが必要です。本リポジトリには各モジュールが期待するテーブル名や列を参照するコードがあります（例: raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, prices_daily, market_regime など）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN ・・・ J-Quants 用のリフレッシュトークン（必須）
- KABU_API_PASSWORD      ・・・ kabuステーション API パスワード（必須）
- KABU_API_BASE_URL      ・・・ kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        ・・・ Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       ・・・ Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY         ・・・ OpenAI API キー（score_news / score_regime 用）
- KABUSYS_ENV            ・・・ execution 環境 (development|paper_trading|live, default=development)
- LOG_LEVEL              ・・・ ログレベル (default=INFO)
- DUCKDB_PATH            ・・・ DuckDB ファイルパス（default=data/kabusys.duckdb）
- SQLITE_PATH            ・・・ SQLite パス（monitoring 用, default=data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD ・・・ 自動 .env 読み込みを無効にするフラグ（1 で無効化）

---

## テスト時のヒント

- 自動 .env 読み込みを無効化する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出し部分はユニットテストしやすいように内部の _call_openai_api を patch/mocking する設計になっています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 -- ニュース NLP（score_news）
    - regime_detector.py          -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント（fetch / save）
    - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
    - etl.py                      -- ETLResult 再エクスポート
    - news_collector.py           -- RSS 収集・前処理
    - quality.py                  -- データ品質チェック
    - calendar_management.py      -- マーケットカレンダー管理
    - audit.py                    -- 監査ログ初期化（init_audit_schema / init_audit_db）
    - stats.py                    -- 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py          -- モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py      -- 将来リターン / IC / 統計サマリー 等

（上記は主要モジュールの抜粋です。詳細は各ファイル内ドキュメントを参照してください）

---

## 注意事項 / 運用上のポイント

- 本ライブラリは実際の売買システムの構成要素を含みます。ライブ発注や資金を扱うパーツと組み合わせる際は十分なテスト・リスク管理（保護環境、ポジション制限、冪等キー管理等）を実施してください。
- OpenAI / J-Quants など外部 API 利用時は API キー管理と利用料に注意してください。
- DuckDB スキーマは別途初期化が必要な場合があります（audit.init_audit_db は監査スキーマ用の初期化を行いますが、ETL が期待するテーブル群はスキーマ定義に基づいて作成してください）。

---

README に書ききれない詳細は各モジュールの docstring を参照してください（例: src/kabusys/data/jquants_client.py、src/kabusys/ai/news_nlp.py など）。必要ならば README を拡張して具体的なスキーマ定義や運用手順を追加できます。