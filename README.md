# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリ。  
DuckDB をデータレイクとして使い、J-Quants からのデータ取得（株価・財務・マーケットカレンダー）、RSS ニュース収集、LLM を用いたニュースセンチメント評価や市場レジーム判定、ファクター計算・研究用ユーティリティ、監査ログ（注文→約定トレース）などを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 要件（依存関係）
- セットアップ手順
- 環境変数（.env）
- 基本的な使い方（コード例）
  - ETL（日次データ更新）
  - ニューススコアリング（AI）
  - 市場レジーム判定（AI）
  - 監査DB初期化
- 自動.env読み込みの挙動
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の目的を持つ内部ライブラリです。

- J-Quants API を用いて日本市場の株価日足・財務データ・マーケットカレンダーを差分取得し DuckDB に保存する ETL パイプライン
- RSS ニュース収集と前処理、ニュースと銘柄の紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 ai_score / マクロセンチメント）
- ETF（1321）を用いた移動平均ベースのテクニカル情報と LLM を組み合わせた市場レジーム判定
- 研究用途のファクター計算・統計ユーティリティ（モメンタム / ボラティリティ / バリュー 等）
- データ品質チェック・監査ログ（シグナル→発注→約定のトレース）

設計上の特徴：
- DuckDB + SQL を多用して高速に集計
- ルックアヘッドバイアス回避（明示的に target_date を引数に取る設計）
- API 呼び出しはリトライ／バックオフ等の堅牢な実装
- 各書き込みは冪等（ON CONFLICT 等）を意識

---

## 機能一覧

- ETL
  - run_daily_etl: カレンダー・株価・財務の差分取得・保存・品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- データ取得クライアント
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info）
  - レート制御、トークンリフレッシュ、ページネーション対応
- ニュース
  - RSS フィード取得（SSRF 防御、gzip 対応、トラッキングパラメータ除去）
  - preprocess_text / news 保存ロジック（raw_news, news_symbols 連携）
- AI（OpenAI）
  - score_news: 銘柄別ニュースを LLM でスコアリングし ai_scores に保存
  - score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM を合成して market_regime に保存
  - バッチ・チャンク処理・リトライ・レスポンス検証を実装
- 研究（research）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats より）
- データ品質チェック
  - 欠損（OHLC）/ 重複 / スパイク / 日付整合性チェック
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - init_audit_db: 監査用 DuckDB を初期化

---

## 要件（依存関係）

- Python 3.10+
- ライブラリ（代表例）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリで多くをまかないますが、外部ネットワーク呼び出し用に urllib 等を使用します。

（プロジェクト化の際は requirements.txt または pyproject.toml に明記してください）

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
4. パッケージのインストール（プロジェクトとして扱う場合）
   - pip install -e .
   （pyproject.toml/setup.py がある場合はこちらでインストール）

---

## 環境変数（.env）

以下の環境変数が利用されます。必須なものは README 内で明示しています。

必須（実行する機能による）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY: OpenAI を使う機能（score_news / score_regime）で必要（関数引数で注入可）
- SLACK_BOT_TOKEN: Slack 通知を使う場合
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- KABU_API_PASSWORD: kabuステーション API を使う場合

オプション／デフォルトあり:
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視系など）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意:
- パッケージはプロジェクトルート（pyproject.toml または .git のある階層）から .env/.env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- settings オブジェクトから環境変数を参照できます（kabusys.config.settings）。

---

## 基本的な使い方（コード例）

以下は主要ユースケースの簡単な例です。すべて Python スクリプトから呼び出す想定です。

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

### 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn: duckdb connection
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

### ニュースの AI スコアリング（score_news）
- 必要: OPENAI_API_KEY を環境変数か api_key 引数で渡す
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> env の OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {written}")
```

### 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

### 監査データベース初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

---

## 自動 .env 読み込みの挙動

- パッケージは import 時にプロジェクトルートを探索し、ルートにある `.env` と `.env.local` を自動的に読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- テストや明示的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env のパースはシェルスタイルの基本的な構文（コメント、クォート、export プレフィックス等）をサポートします。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - etl.py (公開 re-export)
  - news_collector.py
  - calendar_management.py
  - stats.py
  - quality.py
  - audit.py
  - etl.py (ETLResult re-export)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

主なテーブル（DuckDB 側、コード中で参照・作成／更新される想定）
- raw_prices / raw_financials / market_calendar / raw_news / news_symbols
- ai_scores / market_regime
- audit: signal_events / order_requests / executions

---

## 注意事項・運用上のヒント

- OpenAI 呼び出しはコストとレート制限があります。バッチ/チャンクサイズやリトライの設定はコード内の定数で管理されています（必要に応じて調整してください）。
- J-Quants の API レート制限（例: 120 req/min）に合わせた RateLimiter を実装済みです。大量のページネーションが発生する場合は時間がかかります。
- ETL は部分失敗があっても他処理は継続し、結果（ETLResult）にエラー情報を格納します。ログを参照して適切に運用してください。
- DuckDB のバージョン差異に起因する細かな動作（executemany 空リスト等）に配慮したコードになっていますが、実環境での検証を推奨します。
- 監査ログは削除しない前提です。テーブル定義や制約を変更する場合はマイグレーション方針を設計してください。

---

この README はコードベースからの概要説明です。より詳細な仕様（API レスポンス構造、DB スキーマの正確な列名、運用手順）は別途ドキュメント（Design doc, DataPlatform.md, StrategyModel.md 等）をご参照ください。必要であれば README を拡張して CLI 例・運用手順・デプロイ手順などを追加します。