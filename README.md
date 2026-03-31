# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants からのデータ収集、ニュースの NLP スコアリング、ファクター計算、監査ログ（発注トレーサビリティ）、市場レジーム判定などを含むユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- RSS ニュース収集と OpenAI による銘柄別センチメントスコア算出
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントの合成）
- ファクター（モメンタム／バリュー／ボラティリティ）計算、特徴量探索（IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマ初期化と DB 操作ユーティリティ
- 環境変数設定管理（.env 自動読み込み機能）

設計では「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ」「外部 API のレート制御とリトライ」を重視しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系関数、認証トークン管理、レートリミット）
  - カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS の安全取得、前処理、raw_news への保存ロジック）
  - データ品質チェック（missing_data / spike / duplicates / date_consistency / run_all_checks）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄ごとのセンチメントを OpenAI で評価して ai_scores へ保存）
  - 市場レジーム判定（score_regime：ETF 1321 の MA200 乖離 + マクロニュースの LLM スコア合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数の自動読み込み（.env / .env.local をプロジェクトルートから読み込む）
  - settings オブジェクトで設定値を提供

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で `X | Y` などを使用しているため）
- DuckDB を利用（ローカルに duckdb ファイルを作成）

例: 仮想環境の作成と必要パッケージのインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 必要に応じて requests 等を追加
```

環境変数（必須/推奨）
- 必須（動作に必要な最小セット）
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 用）
  - SLACK_BOT_TOKEN       : Slack 通知用トークン（使用する場合）
  - SLACK_CHANNEL_ID      : Slack チャネル ID（使用する場合）
- KabuSys 固有設定
  - KABU_API_PASSWORD     : kabuステーション API パスワード（発注等を利用する場合）
  - KABUSYS_ENV           : development / paper_trading / live （デフォルト: development）
  - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動 .env ロード
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。
- テスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: .env（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C0123456
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要なユースケース）

以下は Python REPL やスクリプトでの利用例です。DuckDB 接続は標準の duckdb.connect を使用します。

1) ETL（日次パイプライン）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの NLP スコア算出（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示的に渡すことも可能。None の場合は OPENAI_API_KEY を参照。
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
# これで signal_events, order_requests, executions 等のテーブルが作成されます
```

5) J-Quants の直接操作（トークン取得やフェッチ）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2026, 3, 1), date_to=date(2026, 3, 20))
```

注意点
- 関数群は DuckDB 接続を受け取り、SQL テーブル（raw_prices / raw_financials / raw_news / ai_scores / market_regime 等）を前提とします。初期スキーマは別途用意する必要があります（プロジェクト内の schema 初期化ユーティリティを利用してください）。
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON mode を利用します。API レート制限・リトライ挙動は内部で実装されています。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
  - パッケージ初期化。公開 subpackages を定義。
- config.py
  - 環境変数管理、settings オブジェクト、自動 .env 読み込みロジック。
- ai/
  - __init__.py
  - news_nlp.py
    - ニュースの集約、OpenAI での銘柄センチメント算出（score_news）
  - regime_detector.py
    - ETF MA200 とマクロニュース LLM を合成して市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API 呼び出し、ID トークン管理、fetch/save 系関数
  - pipeline.py
    - ETL のエントリポイント（run_daily_etl 等）および ETLResult
  - etl.py
    - ETL インターフェース（ETLResult の再エクスポート）
  - news_collector.py
    - RSS フィード収集・前処理・SSRF 対策
  - calendar_management.py
    - 市場カレンダー管理、営業日判定、calendar_update_job
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査ログ（signal/order_request/execution）の DDL と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py
    - calc_momentum / calc_value / calc_volatility
  - feature_exploration.py
    - calc_forward_returns / calc_ic / factor_summary / rank
- ai/__init__.py、research/__init__.py などで主要 API を公開

---

## 開発・運用上の注意

- 型注釈や一部実装により Python 3.10 以上を推奨します。
- OpenAI や J-Quants の API キーは機密情報なので .env やシークレットマネージャで安全に管理してください。
- news_collector は外部 RSS を取得するため SSRF 対策や受信サイズ制限、XML パースの防御（defusedxml）を実装していますが、運用環境ではネットワーク ACL 等も合わせて検討してください。
- DuckDB のバージョン差異により executemany の空パラメータやリストバインドの挙動が異なるため、コード側で空リストチェック等の防御を行っていますが、運用時は使用する DuckDB バージョンでの動作確認を推奨します。
- ETL、LLM 呼び出しは外部 API に依存し、失敗時はフェイルセーフ（スキップ・部分成功）を基本方針としています。ログを必ず確認してください。

---

必要があれば、README に含める具体的な .env.example や DB スキーマ初期化スクリプトの例、docker-compose / systemd サービス例なども作成します。どの情報を追加しますか？