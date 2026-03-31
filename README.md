# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー収集）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算・リサーチ用ユーティリティ、監査ログ（発注〜約定のトレーサビリティ）などを含むモジュール群を提供します。

主な設計方針（抜粋）
- ルックアヘッドバイアス対策：処理内で date.today()/datetime.today() を盲目的に使わず、呼び出し側が対象日を明示できるよう設計。
- 冪等性：ETL/保存処理は ON CONFLICT DO UPDATE 等で冪等に動作。
- フェイルセーフ：外部 API 失敗時は影響を最小化し継続する（スコアを 0 にフォールバックする等）。
- セキュリティ：RSS 収集での SSRF 対策、XML の安全なパース等に配慮。
- 再利用性：DuckDB 接続を引数で受け取るなどテストしやすい設計。

---

## 機能一覧

- データ取得・ETL
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー、上場情報）
  - 差分 ETL / バックフィル / 品質チェック（欠損・スパイク・重複・日付不整合）
  - market_calendar の更新ジョブ
- ニュース収集・前処理
  - RSS からの記事取得（SSRF 対策・トラッキング除去・正規化）
  - raw_news / news_symbols への保存フローを想定
- NLP（OpenAI）連携
  - 銘柄ごとのニュースセンチメントスコアリング（ai.news_nlp.score_news）
  - マクロニュースと ETF MA200 乖離から市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI 呼び出しはリトライやレスポンス検証を実装
- リサーチ / ファクター
  - momentum/value/volatility 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ（オーディット）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（data.audit）
  - audit DB 初期化関数（init_audit_db）
- ユーティリティ
  - 環境変数/設定管理（config.Settings）
  - .env 自動ロード（プロジェクトルートの .env / .env.local。ただし無効化可能）

---

## セットアップ

前提
- Python 3.9 以上を推奨（typing の一部に union 表記や型ヒント使用）
- system-level の依存: ネットワーク接続（J-Quants / OpenAI / RSS）

インストール（開発環境での例）
1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（例: duckdb, openai, defusedxml）

例:
```bash
git clone <repo-url>
cd <repo-root>
python -m venv .venv
source .venv/bin/activate
pip install -e .             # setup.py/pyproject があれば editable install
pip install duckdb openai defusedxml
```

環境変数
- 自動でプロジェクトルートの `.env` および `.env.local` を読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須環境変数（Settings 参照）:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
  - KABU_API_PASSWORD : kabu ステーション API パスワード（本コードでは設定のみ）
  - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID : Slack チャンネル ID
- 任意 / デフォルト付き:
  - KABUSYS_ENV : development | paper_trading | live （デフォルト development）
  - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動読み込み無効
  - OPENAI_API_KEY : OpenAI 呼び出しに使う API キー（score_news/score_regime は引数でも指定可）
  - DUCKDB_PATH : DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH : 監視用途などの SQLite（デフォルト data/monitoring.db）
  - KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

サンプル .env（README 用の簡易例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は Python からの直接利用例です。すべての関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

1) ETL を実行する（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 19))
print(result.to_dict())
```

2) ニュースの NLP スコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を None にすると環境変数 OPENAI_API_KEY を使用
n_written = score_news(conn, target_date=date(2026, 3, 19), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

3) マーケットレジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19), api_key=None)
```

4) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# これで signal_events/order_requests/executions 等のテーブルが作成されます
```

5) J-Quants API を直接使う（トークン取得・データ取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使う
quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,19))
```

注意点
- OpenAI 呼び出し（news_nlp / regime_detector）は大量トークン消費やレート制限のリスクがあるため、api_key の管理・コストに注意してください。
- ETL は J-Quants のレート制限を守るよう実装されていますが、実運用では ID トークンや API レートに関する監視が必要です。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py              -- 環境変数/設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py          -- ニュース NLP スコアリング（OpenAI 連携）
    - regime_detector.py   -- マーケットレジーム判定（ETF MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py          -- ETL パイプラインとユーティリティ（run_daily_etl 等）
    - quality.py           -- データ品質チェック（欠損・スパイク・重複・日付不整合）
    - news_collector.py    -- RSS 収集・前処理
    - calendar_management.py -- マーケットカレンダー管理（営業日判断等）
    - stats.py             -- 統計ユーティリティ（zscore_normalize 等）
    - audit.py             -- 監査ログ（オーディット）テーブル初期化
    - pipeline.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py   -- Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー
  - ai, research, data などのサブモジュールが主要機能を提供

---

## 開発・テスト時のヒント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を起点に行われます。CI やテストで明示的に環境を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化してください。
- OpenAI / J-Quants 呼び出しはネットワーク依存かつコストが発生するため、ユニットテストでは該当関数（例: kabusys.ai.news_nlp._call_openai_api や kabusys.data.jquants_client._request）をモックすることを推奨します。
- DuckDB の接続は容易にメモリ内 (":memory:") に切り替えられるため、単体テストでの DB 初期化は楽に行えます。

---

必要であれば、README に以下を追加できます：
- 各テーブルスキーマの詳細（raw_prices / raw_financials / raw_news / ai_scores / market_regime 等）
- 実運用時のデプロイ手順（systemd / cron / Airflow 等でのバッチ実行例）
- Slack 通知や kabu ステーションへの発注フローの利用例

追加して欲しい項目があれば教えてください。