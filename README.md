# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム向けライブラリです。J-Quants からのデータ取得（ETL）、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用のファクター計算、監査ログ（発注／約定トレース）などを提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を含みます。

- データレイヤ（jquants からのデータ取得、DuckDB への保存、品質チェック、マーケットカレンダー管理、ニュース収集）
- AI レイヤ（ニュースセンチメント、マクロセンチメントを LLM で評価）
- リサーチ（ファクター計算、特徴量解析、Z スコア正規化等）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ用テーブル定義と初期化）

設計方針の要点:
- Look-ahead バイアスを避ける（target_date を明示して処理）
- DuckDB を主要なストレージに想定
- J-Quants API のレート制限やリトライ、OpenAI API のリトライを考慮
- 冪等な DB 保存（ON CONFLICT / upsert）とトランザクション保護

---

## 主な機能一覧

- ETL パイプライン
  - run_daily_etl（市場カレンダー、株価日足、財務データの差分取得と保存）
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別 ETL）
- J-Quants クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token（リフレッシュトークン経由）
- データ品質チェック
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks
- ニュース収集
  - fetch_rss（RSS 取得、SSRF 対策、テキスト前処理）
- AI / NLP
  - score_news（ニュースを銘柄ごとに LLM で評価して ai_scores に書き込み）
  - score_regime（ETF 1321 の MA とマクロニュースから市場レジームを判定）
- リサーチ（因子計算）
  - calc_momentum, calc_value, calc_volatility
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats）
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db（signal_events, order_requests, executions テーブルとインデックスの初期化）
- 設定管理
  - kabusys.config.Settings（環境変数の読み込み、自動 .env ロード）

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーションや標準ライブラリ機能を使用）
- DuckDB を利用（Python パッケージ duckdb）
- OpenAI Python SDK（openai）を利用（gpt 系モデル呼び出し）
- defusedxml（RSS パースの安全化）

1. クローン / ソース配置
   - このリポジトリをクローン、またはパッケージをプロジェクトに配置します。
   - パッケージは src/ 配下にある構成を想定しています。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 例:
     pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらからインストールしてください）

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（kabusys.config がプロジェクトルートを探索します）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（主要）環境変数（コードで _require / settings を参照）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabu ステーション API のパスワード（発注機能を使う場合）
   - SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
   - OPENAI_API_KEY : OpenAI API を使う機能を呼ぶときに必要（score_news / score_regime など）
   - KABUSYS_ENV（任意）: development, paper_trading, live（デフォルト development）
   - LOG_LEVEL（任意）: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   データベースパス（デフォルトを変更したい場合は環境変数で上書き可能）:
   - DUCKDB_PATH （デフォルト `data/kabusys.duckdb`）
   - SQLITE_PATH （監視用 DB。デフォルト `data/monitoring.db`）

   .env の例（プロジェクトルート/.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   OPENAI_API_KEY=sk-xxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

以下は簡単な Python スクリプト例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を利用した ETL 実行（日次 ETL）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings で DUCKDB_PATH を使う場合:
# from kabusys.config import settings
# conn = duckdb.connect(str(settings.duckdb_path))

# もしくは直接ファイルパスで接続
conn = duckdb.connect("data/kabusys.duckdb")

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())  # ETLResult の内容
```

- ニュースセンチメントスコア（ai_scores への書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY が使われる
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（market_regime への書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログデータベースの初期化

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
# 以降 conn を使って発注トレーステーブルを使用可能
```

- リサーチ用ファクター計算の例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"} の dict リスト
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl は J-Quants の認証トークン（get_id_token が内部で settings.jquants_refresh_token を使用）を必要とします。

---

## 設定 / 動作に関する補足

- 自動 .env ロード:
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を探索し、`.env` → `.env.local` の順に読み込みます。
  - OS 環境変数が優先され、`.env.local` は上書き（override）されます。
  - 自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

- 環境切り替え:
  - KABUSYS_ENV によって is_dev / is_paper / is_live が切り替わります。実運用では live を使用してください。

- J-Quants の注意:
  - API のレート制限（120 req/min）に合わせて RateLimiter が実装されています。
  - 401 を受け取ると id_token を自動リフレッシュしてリトライします。
  - 取得したデータは fetched_at を UTC で付与して保存（Look-ahead の検証に役立ちます）。

- OpenAI の注意:
  - gpt-4o-mini を使用（定義済み）。JSON Mode を利用し、レスポンスは JSON でパースされます。
  - API コールはリトライ・バックオフ (指数) を実装しています。失敗時はフェイルセーフでスコア 0.0 を使うなどの挙動があります。

---

## ディレクトリ構成

主要ファイル／ディレクトリの一覧（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news 等）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の公開エイリアス
    - news_collector.py      — RSS ニュース収集
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ（テーブル DDL / init）
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai, data, research 以下のモジュールが公開 API を提供

---

## 開発メモ / 注意事項

- テスト: 各モジュールは外部依存（OpenAI / J-Quants / ネットワーク）を持つため、ユニットテスト実行時は API 呼び出しをモックすることを推奨します（コード内でも各所でモック可能な内部関数を想定しています）。
- DuckDB バージョン差異: DuckDB の executemany の取り扱いやリスト型バインドの差異に配慮した実装があります（pipeline/news_nlp 等）。
- セキュリティ:
  - news_collector は SSRF 回避機構（リダイレクト検査、プライベート IP 拒否、受信サイズ制限）を実装しています。
  - XML パースに defusedxml を使用しています。
- ロギング: settings.log_level でログレベルを調整できます。運用時は適切に設定してください。

---

必要であれば README に以下を追加できます:
- 動作確認用のサンプルデータ生成手順
- CI / テスト実行手順
- 詳細な API 仕様（各関数の引数・戻り値ドキュメントの抜粋）
- デプロイや cron / Airflow 連携例

追加で記載したい項目があれば教えてください。