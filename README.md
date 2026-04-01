# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
J-Quants / JPX のデータ取得、ETL、データ品質チェック、ニュースの NLP スコアリング（OpenAI）、
市場レジーム判定、ファクター研究、監査ログ（約定トレース）などを包含します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得・ETL
  - J-Quants API から株価（日足）、財務（四半期）および市場カレンダーを差分取得・保存（DuckDB）
  - 差分取得・バックフィル・ページネーション対応、トークン自動リフレッシュ、レートリミット制御
- データ品質管理
  - 欠損、重複、将来日付、株価スパイクなどのチェックをまとめて実行
- ニュース収集・NLP
  - RSS からニュース収集（SSRF対策、トラッキング除去）、raw_news への冪等保存
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（ai_scores）生成
- 市場レジーム判定
  - ETF(1321) の 200日MA乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成
- 研究モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン、IC、統計サマリー
- 監査・トレーサビリティ
  - シグナル → 発注 → 約定の監査テーブル群（DuckDB）を初期化するユーティリティ
- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート判定）、設定は Settings 経由で取得

---

## 必須環境変数（例）
以下は本システムが参照する主な環境変数の例です。プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- KABU_API_PASSWORD=<kabu_station_api_password>
- KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY=<your_openai_api_key>  （各関数に api_key を渡すことも可能）
- SLACK_BOT_TOKEN=<slack_bot_token>
- SLACK_CHANNEL_ID=<slack_channel_id>
- DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可, デフォルト: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

簡易の `.env.example`（README 用）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

---

## セットアップ

1. Python 環境を用意（推奨: 3.10+）
2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（プロジェクトに requirements.txt があればそちらを使用してください）。本リポジトリから推定される主な依存:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリのみで済む部分も多いですが上記は必要）
   例:
   - pip install duckdb openai defusedxml
4. 環境変数を設定（.env / .env.local をプロジェクトルートに設置するのが簡便）
   - 自動読み込みはパッケージ内で .git / pyproject.toml を基準にプロジェクトルートを探して行われます。
   - テストや一時的に自動ロードを抑えたい場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. DuckDB データディレクトリを作成（デフォルト `data/`）:
   - mkdir -p data

---

## 使い方（主な API と実行例）

以下は簡単な Python からの利用例です。DuckDB 接続は duckdb.connect() で取得して渡します。

- 基本設定の取得:
```
from kabusys.config import settings
print(settings.duckdb_path)
```

- 日次 ETL 実行:
```
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア化（OpenAI を使用）:
```
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None -> env OPENAI_API_KEY を参照
print(f"scored {n_written} codes")
```

- 市場レジーム判定:
```
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DB 初期化:
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンがセットされます
```

- ファクター計算（研究用）:
```
from kabusys.research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
volatility = calc_volatility(conn, date(2026,3,20))
```

注意点:
- 各スコアリング / モジュールは内部で datetime.today() / date.today() を参照しない設計になっています（バックテストや一貫性確保のため）。
- OpenAI 呼び出しは API エラー・タイムアウト時にフェイルセーフ（0.0 など）で継続するよう設計されています。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py
  - 環境変数 / 設定読み込み（.env 自動読み込み、Settings クラス）
- ai/
  - __init__.py (score_news エクスポート)
  - news_nlp.py
    - ニュースの集約・OpenAI による銘柄別センチメント算出
  - regime_detector.py
    - ETF(1321) MA200 乖離 + マクロニュース LLM を合成した市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py
    - JPX カレンダー管理、営業日判定、次営業日/前営業日の取得
  - etl.py
    - ETLResult の再エクスポート
  - pipeline.py
    - 日次 ETL パイプライン（run_daily_etl 等）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック群（欠損・重複・スパイク・日付不整合）
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）の DDL と初期化
  - jquants_client.py
    - J-Quants API クライアント（取得・保存関数）
  - news_collector.py
    - RSS 取得・前処理・冪等保存、SSRF 対策
- research/
  - __init__.py
  - factor_research.py
    - momentum / value / volatility 等のファクター計算
  - feature_exploration.py
    - 将来リターン計算、IC（Spearman）、統計サマリー、ランク関数
- monitoring, strategy, execution 等のトップレベルパッケージ参照は __all__ に含む（将来的な拡張を想定）

---

## 追加メモ / 運用上の注意

- .env の読み込み順: OS 環境変数 > .env.local > .env（.env.local が優先して上書き）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB への書き込みは基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で設計されていますが、ETL 実行時のトランザクションや並列実行に注意してください。
- OpenAI の呼び出しは JSON Mode を用い、レスポンス検証やリトライ処理を実装済みです。それでも API の応答が不正な場合はスキップして処理継続します（フェイルセーフ）。
- jquants_client は API レート制限（120 req/min）を守るためレートリミッタが内蔵されています。
- 本リポジトリは本番での自動売買の最終発注ロジック・ブローカ連携を含みません。発注・実行系は別モジュール（execution）で扱う想定です。実際の売買を行う際は十分なテストと監視を行ってください。

---

この README はコードベースの主要部分をまとめたものです。より詳細な仕様は各モジュールの docstring を参照してください。ご要望があればセットアップの自動化スクリプトやサンプル .env.example ファイルの追加を提供します。