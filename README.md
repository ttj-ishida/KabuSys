# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームのライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・LLM を用いた記事センチメント評価、ファクター計算、監査ログ（注文／約定トレーサビリティ）、市場カレンダー管理など、取引システムやリサーチ基盤で必要となる機能をモジュール化して提供します。

主な設計思想:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB を一次データストアとして利用
- API 呼び出しに対して堅牢なリトライとレート制御（J-Quants / OpenAI）
- 冪等性を意識した DB 書き込み（ON CONFLICT / DELETE→INSERT 等）
- テスト容易性のため設定注入やモック差し替えを想定

---

## 機能一覧

- データ収集 / ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、上場情報、マーケットカレンダー取得（fetch_* 系）
  - 差分取得・バックフィル・品質チェック・保存（data.pipeline.run_daily_etl 等）
- ニュース関連
  - RSS 収集（news_collector.fetch_rss）
  - ニュース -> 銘柄紐付け（news_symbols 経由を想定）
  - LLM による銘柄ごとのニュースセンチメントスコアリング（ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM スコアを合成して日次レジーム判定（ai.regime_detector.score_regime）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算・IC 計算・統計サマリー（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- カレンダー管理
  - JPX カレンダーの保持・営業日判定・前後営業日取得（data.calendar_management）
- 監査ログ（オーダー → 約定 のトレーサビリティ）
  - 監査スキーマ初期化／専用 DB 初期化（data.audit.init_audit_schema / init_audit_db）
- 設定管理
  - .env（プロジェクトルート）自動読み込み、環境変数ベースの設定取得（config.Settings）

---

## セットアップ手順

以下は開発環境での基本セットアップ例です。プロジェクトの packaging / CI に応じて調整してください。

1. Python 環境（3.10+ 想定）を用意
2. 必要パッケージをインストール（代表的なパッケージ）
   - duckdb
   - openai
   - defusedxml
   - その他標準ライブラリ外で利用しているもの（例: typing-extensions 等が必要であれば適宜）

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発用にパッケージを editable インストールする場合:
pip install -e .
```

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動でロードされます（モジュール内の自動ロード機能）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須となる主な環境変数（config.Settings に準拠）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（fetch 系で使用）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector の LLM 呼び出し）
- KABU_API_PASSWORD : kabuステーション API のパスワード（execution 等で使用想定）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（monitoring 用など）
- SLACK_CHANNEL_ID : Slack チャンネル ID

任意 / デフォルト付き:
- KABUSYS_ENV : environment（development / paper_trading / live）デフォルトは development
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）デフォルト INFO
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 sqlite パス（デフォルト data/monitoring.db）

サンプル .env（.env.example）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（主要なユースケース例）

以下はライブラリの一部 API を使う簡単な例です。実際にはログ設定や例外処理を適宜追加してください。

- DuckDB 接続の取得（例）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの LLM スコアリング（ai.news_nlp.score_news）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定しておく
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {count}")
```

- 市場レジーム判定（ai.regime_detector.score_regime）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して監査用テーブルが作成される
```

- カレンダー・営業日の利用例:
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- LLM を呼ぶ関数は API 呼び出し時にリトライやフェイルセーフ（失敗時はスコア 0.0 等）を行いますが、API キーは必須です。テスト時は該当関数をモック化してください（モジュール内での _call_openai_api をパッチする設計を想定しています）。
- ETL / 保存処理は DuckDB のスキーマが整っていることを前提とします（初期スキーマ作成機能は別途用意することを想定）。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 配下にモジュール群が配置されています。主要ファイル・モジュールは以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースの LLM スコアリング（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch / save 系）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult 型の再エクスポート
    - news_collector.py      -- RSS ニュース収集
    - calendar_management.py -- JPX カレンダー管理
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - quality.py             -- データ品質チェック
    - audit.py               -- 監査ログ（オーダー/約定）スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー
  - ai、data、research 以下の補助モジュール群（上記に含まれる）

各モジュールは DuckDB 接続を引数に取る関数群が多く、DB スキーマやテーブルは ETL と併せて運用する想定です。

---

## 追加メモ / 運用時の注意

- 自動 .env ロード
  - config._find_project_root を使い、プロジェクトルートの `.env` / `.env.local` を自動読み込みします。テスト時などで不要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 環境（KABUSYS_ENV）
  - 有効値: development / paper_trading / live。live 時は実際の発注等を行う処理を厳重に管理してください（実装側で is_live フラグを参照）。
- レート制御 / リトライ
  - J-Quants クライアントは 120 req/min の固定間隔レートリミッタを実装しています。API の呼び出し回数に注意してください。
- テスト
  - LLM / ネットワーク呼び出しはモックしてテストする設計になっています（モジュール内の _call_openai_api などを patch）。
- スキーマ管理
  - DuckDB の初期スキーマや audit スキーマの初期化は `data.audit.init_audit_schema` / `init_audit_db` を使用してください。既存 DB に対して冪等的に実行されます。

---

この README はソース内部のドキュメント（docstring）を元にまとめています。より詳細な API 仕様や実運用手順（CI / スケジューラ設定、監視、ロギング設定、バックテストとの連携など）は別途ドキュメント化することを推奨します。