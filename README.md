# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション 等の外部データソースからデータを取得・保存し、ニュース NLP / 市場レジーム判定 / ファクター計算 / ETL パイプライン / 監査ログ（トレーサビリティ）など、売買システムに必要な基盤機能を提供します。

主な用途
- 日次 ETL による株価・財務・市場カレンダーの収集と品質チェック
- ニュースを使った銘柄ごとの AI（LLM）センチメントスコアリング
- ETF とマクロニュースを組み合わせた市場レジーム判定
- リサーチ用ファクター計算・前方リターン・IC 等の解析ユーティリティ
- 監査ログ（signal → order_request → execution）を格納する DuckDB ベースのスキーマ

---

## 主な機能（一覧）

- 環境・設定管理
  - .env（および .env.local）自動読み込み機構、必須環境変数の検査（kabusys.config.Settings）
- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（レート制御・自動リフレッシュ・リトライ）
  - daily quotes / financial statements / market calendar の取得と DuckDB への冪等保存
  - 日次 ETL パイプライン（run_daily_etl）
  - カレンダー管理、営業日判定ユーティリティ
  - ニュース収集（RSS）、前処理、raw_news 保存ロジック（SSRF／XML／サイズ制限対策）
  - データ品質チェック（欠損・重複・スパイク・未来日付等）
  - 監査ログ（signal_events / order_requests / executions）スキーマ作成・初期化
- AI（LLM）関連（kabusys.ai）
  - ニュース NLP による銘柄別センチメント（score_news）
  - ETF（1321）200 日 MA とマクロ記事の LLM センチメント合成による市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を JSON Mode で利用する設計（リトライ / フォールバック実装あり）
- リサーチ（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）、統計サマリー、Zスコア正規化ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに | を使用）
- ネットワーク接続（J-Quants / OpenAI / RSS 取得）

依存パッケージ（最低限）
- duckdb
- openai (OpenAI の公式 SDK)
- defusedxml
- （標準ライブラリ以外が必要な場合は requirements.txt を用意してインストール）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード（本ライブラリの一部で参照）
- SLACK_BOT_TOKEN        : Slack 通知を使う場合のボットトークン
- SLACK_CHANNEL_ID       : Slack 通知先チャンネル ID
- OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime で使用）

オプション（デフォルト値あり）
- KABUSYS_ENV            : development / paper_trading / live（デフォルト development）
- LOG_LEVEL              : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 sqlite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する場合に 1 を設定

.env 自動ロードについて
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探して自動で .env を読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単な例）

DuckDB に接続して日次 ETL を実行する例:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュース NLP（銘柄ごとの ai_scores 書き込み）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {n_written} scores")
```

市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

監査ログ用 DB の初期化（監査専用 DB を別に持つ場合）:
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# 以降 conn_audit に対して監査レコードを INSERT していく
```

設定参照（コード中での利用例）:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
```

ニュース RSS の取得（低レベルユーティリティ）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
```

注意点
- AI（OpenAI）呼び出しは外部 API を利用します。API キーの管理・課金に注意してください。
- score_news / score_regime は Look-ahead bias を避ける設計（target_date 未満のデータのみ参照）になっています。
- ETL・保存処理は DuckDB の ON CONFLICT を利用して冪等性を担保します。

---

## ディレクトリ構成

以下は主要なパッケージ構成（src/kabusys 配下）。実際のリポジトリはこれにテスト・CI・ドキュメント等が含まれます。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント & DuckDB 保存
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL の公開型（ETLResult 再エクスポート）
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py       — RSS 収集・前処理
    - quality.py              — データ品質チェック（欠損・スパイク・重複等）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログ（テーブル初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 等
    - feature_exploration.py  — forward returns / IC / rank / factor_summary
  - research/* (その他の研究用モジュール)
  - その他（strategy / execution / monitoring 等の名前空間は __all__ に用意）

---

## 実運用上の注意・ベストプラクティス

- 本ライブラリは本番（実際の発注）と研究（バックテスト／解析）で使われる機能を含みます。特に発注・監査周りは慎重にテストしてください。
- OPENAI_API_KEY や J-Quants のトークンは安全に保管し、Git 等に含めないでください（.env を利用し .gitignore に入れる）。
- ETL 実行はスケジューラ（cron / Airflow 等）で日次に自動実行するケースが一般的です。run_daily_etl は内部でカレンダー調整・backfill を行うためそのまま利用できます。
- テスト・ローカル実行時に .env の自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出しはレスポンスの変化や料金に依存するため、rate limit、retry、コストを意識して運用してください。

---

もし README に追加したい具体的な情報（例: pyproject.toml / setup の手順、CI 設定、より詳細な API ドキュメントや使用例）などがあれば教えてください。必要に応じて実際のコマンド例やトラブルシューティングも追記します。