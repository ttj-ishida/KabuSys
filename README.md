# KabuSys

日本株向けのデータプラットフォーム & 自動売買 / 研究ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、ファクター計算、監査ログ、監視・実行周りの基盤機能を提供します。

---

## 概要

KabuSys は日本株の自動売買システム構築に必要な共通機能群をモジュール化した Python パッケージです。主な責務は次の通りです。

- J-Quants API を用いた日次データ（株価・財務・カレンダー）の差分 ETL
- RSS ニュースの収集と前処理、LLM（OpenAI）を使ったニュースセンチメント評価
- マーケットレジーム判定（ETF の MA とマクロニュースを統合）
- ファクター（モメンタム、バリュー、ボラティリティ等）の計算・探索用ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 設定・.env の自動ロード機能

設計上の重点:
- ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を不用意に参照しない）
- 冪等性（DB への保存は ON CONFLICT/UPDATE 等で安全に）
- フェイルセーフ（外部API失敗時は例外にせず許容する箇所がある）
- DuckDB を主要データベースに想定（軽量で分析向け）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系、get_id_token）
  - 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - ニュース収集（RSS 取得・前処理、SSRF/サイズ対策）
  - データ品質チェック（missing, spike, duplicates, date consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを LLM でスコアリングし ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュースで市場レジーム判定
- research/
  - factor_research: モメンタム / ボラティリティ / バリューの計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー等
- config.py: 環境変数・設定管理（.env 自動読み込み、設定プロパティ）
- audit / monitoring / execution 等の補助モジュール（コードベースに準拠）

---

## 必要要件

- Python 3.10+
- 主要 Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

requirements.txt（例）:
```
duckdb
openai
defusedxml
```

※ 実際のプロジェクトでは他に slack SDK や kabu API クライアント等が必要になる場合があります。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存関係をインストール
   ```
   pip install -r requirements.txt
   # あるいは開発インストール
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な利用例）

Python REPL / スクリプトで各機能を呼び出して利用できます。

- ETL（日次 ETL を実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーを環境変数または引数で渡す）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {count}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究用途）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査ログの操作が可能
```

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## 注意点 / 運用上のヒント

- OpenAI 呼び出しは料金が発生します。テスト時はモック（unittest.mock.patch）を使って _call_openai_api を差し替えてください（各 ai モジュールでその設計をサポートしています）。
- J-Quants の API はレート制限があります（モジュール内でレート制御あり）。長時間の大量取得や並列化には注意してください。
- DuckDB の executemany に空リストが渡せないバージョン向けのガード（params が空のときは実行しない）をコードで対応していますが、DuckDB のバージョンに依存する挙動がある点に留意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト時など自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py (ETLResult 再エクスポート etc.)
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - (その他 research ユーティリティ)
    - research/
      - __init__.py
    - ai/
      - __init__.py
    - (その他: execution, monitoring, strategy 等のトップレベルモジュール想定)

各モジュールには docstring で設計意図・処理フロー・フェイルセーフの振る舞いが詳細に書かれています。まずはドキュメントや docstring を参照してから利用してください。

---

## 開発・テスト

- 単体テストでは外部 API 呼び出し（OpenAI / J-Quants / HTTP）はモックすることを推奨します。各 ai モジュールや jquants_client 内のネットワーク呼び出し箇所はモック差し替えが容易な作りになっています。
- 型ヒント・ロギングが充実しており、解析やデバッグがしやすい設計です。

---

本 README はコードベースの概要と主要な利用方法をまとめたものです。細かな API 仕様やテーブルスキーマ、さらに運用手順についてはソース内の docstring（各モジュール冒頭）およびプロジェクトの設計ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。