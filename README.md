# KabuSys

日本株向けのデータパイプライン・研究・自動売買補助ライブラリです。  
DuckDB を中心としたローカルデータベース、J-Quants API からの ETL、ニュースの NLP スコアリング（OpenAI）や市場レジーム判定、監査トレース用テーブルなどを提供します。

---

## 主な特徴

- J-Quants API と連携した差分 ETL（株価・財務・市場カレンダー）
- DuckDB を用いた高速ローカルデータ保存（冪等保存 / ON CONFLICT）
- ニュース収集（RSS）と LLM ベースのニュースセンチメント解析（gpt-4o-mini）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー、IC 等）
- データ品質チェック（欠損、スパイク、重複、日付矛盾）
- 監査ログ（signal → order_request → executions）のスキーマ & 初期化ヘルパー
- 環境変数 / .env 自動読み込み機能（プロジェクトルートの .env / .env.local）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / RSS / OpenAI）

（実際のインストールはプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール
   - 開発環境例:
     - git clone ...
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt
     - または pip install -e .

2. 環境変数の準備
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

3. 必須の環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
   - KABU_API_PASSWORD — kabuステーション API パスワード（発注等がある場合）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack チャンネル ID
   - その他（任意/デフォルトあり）
     - KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
     - LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — sqlite（monitoring 用）パス（デフォルト: data/monitoring.db）

4. DuckDB/データベース初期化（監査用等）
   - 監査用 DB を初期化するには `kabusys.data.audit.init_audit_db` を使用します（サンプルは下記）。

---

## 簡単な使い方（コード例）

以下は代表的な処理の呼び出し例です。全て Python スクリプト / REPL 内で実行できます。

- 共通: 設定・DB パスは `kabusys.config.settings` から取得できます。

1) 日次 ETL を実行（株価・財務・カレンダーの差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

2) ニュースセンチメントのスコアリング（ai_scores テーブルへ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key が None の場合 ENV の OPENAI_API_KEY が使われる
print(f"scored {count} symbols")
conn.close()
```

3) 市場レジームを判定して書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
conn.close()
```

4) 監査用 DuckDB を作成・初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path とは別に監査ログ専用 DB を作ることを推奨
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は初期化済みの DuckDB 接続を返す
audit_conn.close()
```

5) 研究用ユーティリティ（ファクター計算 / 正規化）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))

# Z-score 正規化の例
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
conn.close()
```

---

## .env の例（.env.example）
プロジェクトルートに `.env` を作成して必須値を設定してください（実際の値は機密）。
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

注意事項:
- `.env.local` は `.env` の値を上書きします（ローカル専用）。OS 環境変数が優先されます。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動ロードを含む）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py      — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ロジック
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult エクスポート
    - news_collector.py       — RSS 収集・前処理（SSRF 対策・サイズ制限）
    - calendar_management.py  — 市場カレンダーの管理と営業日ロジック
    - quality.py              — データ品質チェック
    - stats.py                — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — forward returns, IC, rank, summary
  - (その他) strategy/, execution/, monitoring/ パッケージの存在が想定される（__all__ に含まれる）

---

## ロギング・デバッグ

- 環境変数 `LOG_LEVEL` でログレベルを制御できます（例: `DEBUG`）。
- OpenAI・J-Quants 等の外部 API 呼び出しはリトライやフェイルセーフを組み込んでいますが、ネットワーク障害時はログに詳細が出ます。
- テスト時には環境変数自動ロードを無効化する (`KABUSYS_DISABLE_AUTO_ENV_LOAD=1`) と便利です。
- news_nlp/regime_detector の OpenAI 呼び出しはテストで容易にモックできるよう、内部 API 呼び出し関数を差し替え可能に設計されています。

---

## 注意点 / 設計上の方針（概要）

- ルックアヘッドバイアス防止: 多くの関数は内部で `date.today()` を直接参照しない、または対象日以前のデータのみを使用するように設計されています。
- データ保存は冪等化（ON CONFLICT DO UPDATE / INSERT ... DO NOTHING）されています。
- API 呼び出しはレート制御・指数バックオフ・401 の自動リフレッシュ等を実装。
- ニュース収集は SSRF 対策、受信サイズ制限、XML パース安全対策（defusedxml）を組み込んでいます。
- DuckDB を前提に SQL を書いているため、他 DB での互換性は考慮していません。

---

## 貢献・拡張

- 新しい ETL ソース（RSS、API）や戦略モジュール、実行ブローカー連携はモジュールを追加することで拡張できます。
- テストを書く際は環境変数自動ロードを無効化し、OpenAI / J-Quants の呼び出しをモックしてください。
- ドキュメント改善やサンプルスクリプトの追加を歓迎します。

---

この README はコードベースの主要機能と初期利用方法の概要をまとめたものです。より詳細な仕様書（DataPlatform.md / StrategyModel.md 等）に沿った実装・運用が本プロジェクトの前提となります。必要であれば、用途別のサンプルスクリプト（ETL 定期実行、ニュース収集バッチ、監査 DB 初期化、戦略実行フロー）を追加で用意できます — 要望があれば教えてください。