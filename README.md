# KabuSys — 日本株自動売買システム

軽量な日本株向けデータプラットフォームとリサーチ / AI 補助の指標生成、監査ログ・ETL パイプラインを提供するライブラリ群です。DuckDB をストレージに用い、J-Quants / OpenAI / RSS 等と連携してデータ収集・品質チェック・ファクター生成・ニュースセンチメント評価・市場レジーム判定などを行います。

主な用途例：
- 日次 ETL（株価・財務・カレンダー）自動取得・保存
- ニュースを LLM でセンチメント評価して銘柄単位スコアを生成
- ETF を用いた市場レジーム判定（MA + マクロニュース）
- ファクター計算・特徴量探索（研究用）
- 監査ログ（シグナル→発注→約定トレース）用スキーマ初期化

---

## 機能一覧

- 環境設定読み込み（.env / .env.local 自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化）
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー取得
  - レートリミット管理／リトライ／トークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT で更新）
- ETL パイプライン（data.pipeline）
  - 日次 ETL 実行（calendar → prices → financials → 品質チェック）
  - 個別ジョブの実行・差分取得
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキング除去、ID生成）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント集約）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM スコア合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリ、Zスコア正規化）
- 監査ログスキーマの初期化（signal_events / order_requests / executions 等）
- DuckDB ベースの監査 DB 初期化ユーティリティ

---

## 要件（推奨）

- Python 3.10+
- 必須パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリのみで動く機能も多いですが、上記は主要機能（ETL / LLM / RSS）で必要です。

インストール（例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# （プロジェクトを editable install する場合）
pip install -e .
```

※ packaging 用の pyproject.toml がある前提で pip install -e . を想定しています。単体ファイルを直接使う場合は PYTHONPATH に `src` を追加してください。

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得
2. 仮想環境の作成（推奨）と依存インストール（上記参照）
3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` として必要な設定を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
4. 必要な環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector で使用）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必要な場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（default data/monitoring.db）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
   - KABUSYS_ENV: development / paper_trading / live（default: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL （default: INFO）
5. データディレクトリ作成（必要に応じて）
```bash
mkdir -p data
```

.env の自動ロードについて:
- 読み込み順は OS 環境 > .env.local > .env（.env.local は .env を上書き）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能

---

## 使い方（主要な API と例）

以下は代表的な利用例です。どの関数も DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

1) DuckDB 接続を作る
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3) ニュースセンチメントをスコアして ai_scores テーブルに保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数か api_key 引数で指定
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"wrote {written} codes")
```

4) 市場レジーム判定を実行（ETF 1321 の MA200 とマクロニュース合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ用の DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル(signal_events, order_requests, executions 等)が作成されます
```

6) J-Quants から日足を直接取得（テスト・対話用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
```

7) RSS を取得（ニュースコレクタのユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

注意:
- LLM（OpenAI）系の関数は API キーが必須です。api_key 引数を使うか環境変数 OPENAI_API_KEY を設定してください。
- 各処理は Look-ahead bias を避ける設計（target_date 未満のデータのみ参照）になっています。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースを LLM でスコアリングし ai_scores を更新
    - regime_detector.py    — 市場レジーム判定（1321 MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult の re-export
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - news_collector.py     — RSS 取得・前処理・保存ユーティリティ
    - quality.py            — データ品質チェック
    - stats.py              — Zスコア等の統計ユーティリティ
    - audit.py              — 監査ログスキーマ定義／初期化
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリ 等
  - monitoring/ (未記載の実装ファイルが想定される時はここに配置)
  - execution/ (発注・ブローカー連携などの想定モジュール)
  - strategy/ (戦略生成・フィルタなどの想定モジュール)

（README 内で省略しているファイルやモジュールもありますが、上記が主要な公開 API の所在です）

---

## 運用上のポイント / ベストプラクティス

- 環境分離:
  - KABUSYS_ENV を `development` / `paper_trading` / `live` に設定して運用モードを切り替えてください。
- 秘密情報:
  - J-Quants トークン・OpenAI キー等は `.env` に記載するか環境変数として安全に管理してください。
- データ安全性:
  - ETL は部分失敗を許容する設計です。run_daily_etl の戻り値（ETLResult）を確認し、quality_issues と errors を必ず監視してください。
- テスト / CI:
  - config の自動 .env 読み込みはテスト時に副作用を起こす場合があるため、テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境を注入してください。
- LLM コスト・レート制御:
  - news_nlp / regime_detector は OpenAI 呼び出しを行うため、使用頻度とバッチ設定（_BATCH_SIZE など）に注意してください。

---

## 貢献 / 発展案

- ブローカー接続（kabu ステーション等）と発注ロジックの実装（execution モジュール）
- Web UI / モニタリング（LINE / Prometheus / Grafana 連携）
- バックテストツールとの統合（StrategyModel に基づくシミュレーション）
- テストカバレッジ追加、CI ワークフロー整備

---

ご不明点や README に追記してほしいサンプル（たとえば具体的な .env.example、起動スクリプト、systemd ユニット例など）があれば教えてください。必要に応じて追記します。