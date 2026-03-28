# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。J-Quants や kabuステーション、OpenAI などと連携し、データ取得（ETL）、データ品質チェック、ニュース NLP、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## 概要

主に以下の用途を想定しています。

- J-Quants API からの株価・財務・カレンダーデータ取得（差分ETL、保存、品質チェック）
- RSS ベースのニュース収集と LLM を用いたニュースセンチメント解析（銘柄別 ai_score）
- マクロ＆テクニカルを組み合わせた市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量探索ユーティリティ
- 監査用テーブル（シグナル→発注→約定のトレーサビリティ）を DuckDB に初期化
- 環境変数ベースの設定管理（.env 自動読み込み、設定検証）

設計上の共通方針：
- ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しない設計）
- 冪等性（ETL・保存処理は idempotent）
- フェイルセーフ（外部 API 失敗時は部分的にスキップして継続）
- 外部依存を限定（主要処理は DuckDB + 標準ライブラリ + 最低限の外部ライブラリ）

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証メソッド提供
- データ ETL（kabusys.data.pipeline / etl / jquants_client）
  - J-Quants からの差分取得（株価・財務・カレンダー）
  - DuckDB への冪等保存（ON CONFLICT）
  - 日次 ETL エントリ run_daily_etl
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合チェック
  - QualityIssue を集約して返却
- 市場カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日の取得・カレンダー更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF・gzip・追跡パラメータ除去等の安全対策）
  - raw_news / news_symbols へ冪等保存
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごとのニュースを LLM でスコアリングし ai_scores に保存
  - バッチ／チャンク処理、リトライ、レスポンスバリデーション
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - z-score 正規化ユーティリティ（kabusys.data.stats）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査テーブルの DDL と初期化関数
  - init_audit_db / init_audit_schema を提供

---

## セットアップ手順

前提:
- Python 3.9+（型注釈の | を使うため 3.10 推奨）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（AI 機能を使う場合）
- defusedxml（ニュース XML パース保護）

1. リポジトリをクローン（例）
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   必要最小限（例）:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数の設定
   プロジェクトルート（.git や pyproject.toml がある場所）に `.env` を置くと自動読み込みされます（.env.local は .env を上書き）。
   自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（必須）：
   - JQUANTS_REFRESH_TOKEN = <J-Quants リフレッシュトークン>
   - KABU_API_PASSWORD = <kabuステーション API パスワード>
   - SLACK_BOT_TOKEN = <Slack Bot トークン>
   - SLACK_CHANNEL_ID = <Slack 通知先チャンネルID>

   任意 / デフォルトあり:
   - OPENAI_API_KEY = <OpenAI API キー>（AI 機能利用時、または関数呼び出し時に api_key 引数でも可）
   - DUCKDB_PATH = data/kabusys.duckdb
   - SQLITE_PATH = data/monitoring.db
   - KABUSYS_ENV = development | paper_trading | live
   - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

   .env の例（プロジェクトルート/.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡単な例）

以下は簡単な Python サンプル（REPL やスクリプトから呼び出す例）です。

- 共通準備：DuckDB 接続と設定読み出し
```python
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（J-Quants トークンは settings から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- ニューススコアリング（OpenAI キーが必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# 環境変数 OPENAI_API_KEY が設定されているか、api_key 引数で指定
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {count}")
```

- 市場レジーム判定（OpenAI キーが必要）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（監査専用の DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.db")
# audit_conn は DuckDB 接続オブジェクト
```

- 研究用関数の例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

d = date(2026, 3, 20)
momentum = calc_momentum(conn, d)
forw = calc_forward_returns(conn, d, horizons=[1,5,21])
ic = calc_ic(momentum, forw, factor_col="mom_1m", return_col="fwd_1d")
print(ic)
```

注意点：
- AI 関数（score_news / score_regime）は OpenAI API を呼び出します。API キーを環境変数 `OPENAI_API_KEY` に設定するか、関数呼び出し時に `api_key=` を渡してください。
- ETL / データ取得はネットワーク依存（J-Quants）です。J-Quants トークンは `JQUANTS_REFRESH_TOKEN` で設定され、jquants_client.get_id_token で ID トークンを取得します。
- ETL 実行時は DuckDB スキーマ（raw_prices/raw_financials/market_calendar 等）が必要です。初期スキーマ作成の仕組みが別途ある想定です（プロジェクトの schema 初期化機能を利用してください）。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要なファイル／モジュールの配置（src/kabusys 以下）：

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP（銘柄別スコアリング）
    - regime_detector.py     -- マーケットレジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py            -- ETL パイプライン（run_daily_etl等）
    - etl.py                 -- ETL の公開インターフェース（ETLResult）
    - calendar_management.py -- 市場カレンダー管理（営業日判定等）
    - news_collector.py      -- RSS ニュース収集・前処理
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - audit.py               -- 監査ログテーブルの DDL と初期化
  - research/
    - __init__.py
    - factor_research.py     -- Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py -- 将来リターン計算、IC、summary 等
  - monitoring/ (※実装ファイルがある想定: モニタリング用コード)

各モジュールはドキュメント文字列内に設計方針・入出力・例外振る舞いが記載されています。実装詳細は各ファイルの docstring を参照してください。

---

## その他の注意点

- .env 自動読み込み:
  - 実行時、プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を読み込みます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - テストや CI で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 環境（KABUSYS_ENV）:
  - 有効値: development / paper_trading / live
  - ログレベルは環境変数 `LOG_LEVEL` で制御可能
- DuckDB:
  - デフォルトの DB パスは `data/kabusys.duckdb`（settings.duckdb_path）
  - audit 用 DB は別ファイルで初期化可能（init_audit_db）
- セキュリティ／堅牢性:
  - RSS 取得では SSRF 防止、gzip/サイズチェック、XML の安全パース等を実装
  - J-Quants クライアントはレートリミット・リトライ・トークン自動リフレッシュ対応

---

ご不明点や README に追加したい利用手順（CI、Docker、schema 初期化スクリプト、運用スケジュール例など）があれば教えてください。必要に応じて用途別のガイド（開発用、運用用、テスト用）を追記します。