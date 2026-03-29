# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL・データ品質チェック・ニュース収集・LLMベースのニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター計算・監査ログ（発注トレーサビリティ）など、取引システムと研究環境の両方で使えるユーティリティ群を提供します。

---

## 主要機能（Feature一覧）

- データ取得・ETL
  - J-Quants API から株価（OHLCV）・財務データ・上場情報・市場カレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次バッチ用の総合 ETL エントリポイント（run_daily_etl）

- データ品質管理
  - 欠損・重複・スパイク（急変）・日付不整合などを検出する品質チェック群（quality モジュール）
  - 品質チェック結果は QualityIssue オブジェクトで取得可能

- カレンダー管理
  - JPX カレンダーの保存・営業日判定・前後の営業日取得などのユーティリティ
  - calendar_update_job による差分更新処理

- ニュース収集
  - RSS フィードから記事取得（SSRF対策・gzip・サイズ制限・URL正規化）
  - raw_news / news_symbols への冪等保存を想定した実装

- ニュース NLP（LLM ベース）
  - ニュースを銘柄単位に集約して OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ保存（score_news）
  - レート制限・再試行・レスポンス検証を備えた堅牢な呼び出し実装

- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次で「bull/neutral/bear」を判定（score_regime）

- 研究（Research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化ユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルを初期化・利用する機能（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティを UUID ベースで保持

---

## 必要条件 / 依存

- Python 3.10+
- 主要依存ライブラリ（抜粋）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI API 等）

（プロジェクトに pyproject.toml / requirements.txt があればそちらからインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを入手）
   - 例: git clone ...

2. 仮想環境の作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements ファイルがあれば pip install -r requirements.txt）

4. 環境変数の設定
   - システム環境変数、またはプロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます。
   - 自動読み込みを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      — kabuステーション API パスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（監視等）
   - SLACK_CHANNEL_ID       — Slack 送信先チャンネル ID
   - OPENAI_API_KEY         — OpenAI API キー（news_nlp / regime_detector が使用）

   設定例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方（簡単な例）

以下の例は DuckDB を使って各主要処理を実行する流れです。実運用ではログ設定や例外ハンドリングを追加してください。

- DuckDB 接続の作成（設定ファイル経由）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（LLM）でスコア付け
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数に設定するか api_key 引数で渡す
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {num_written}")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

# OpenAI API キーは環境変数または api_key 引数で指定
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# 監査ログ用に別 DB を用意する場合も可能。settings.duckdb_path を使ってもよい。
audit_conn = init_audit_db(settings.duckdb_path)
# または init_audit_schema(conn) で既存接続にスキーマを追加
```

- RSS の取得（ニュースコレクタのユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES['yahoo_finance'], source='yahoo_finance')
for a in articles:
    print(a['id'], a['datetime'], a['title'])
```

---

## 自動環境変数読み込みについて

- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）を検出し、以下の優先順位で環境変数を読み込みます:
  - OS 環境変数（既存）
  - .env.local（存在すれば上書き）
  - .env（存在すれば未設定のキーをセット）
- テストなどで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要ディレクトリ構成

（リポジトリ内の src/kabusys を想定）

- src/kabusys/
  - __init__.py                     — パッケージ初期化（__version__）
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースの LLM スコアリング（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch / save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - news_collector.py             — RSS 収集・前処理
    - quality.py                    — データ品質チェック
    - stats.py                      — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査ログスキーマ初期化
    - etl.py                        — ETL の公開型再エクスポート
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン・IC・統計サマリー
  - ai, data, research のサブモジュールがそれぞれの責務を持つ

---

## 設計上の留意点 / 動作方針

- ルックアヘッドバイアス回避：内部で datetime.today() や date.today() を直接参照する箇所を避け、処理対象日を明示的に受け取る設計。
- 冪等性（idempotency）：DB 書き込みは可能な限り ON CONFLICT DO UPDATE / INSERT RETURNING 等で冪等に実施。
- API 呼び出しはレート制御・再試行・フェイルセーフ（必要ならスキップして続行）を組み込み。
- セキュリティ考慮：RSS 取得時の SSRF 対策、defusedxml による XML パース、防御的な URL 正規化など。

---

## 開発・テストに関して

- 自動 env ロードを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI など外部 API を呼ぶ部分は、ユニットテスト時にモック差し替え（patch）することを想定して実装されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。

---

追加のドキュメント（使用例、運用ガイド、DB スキーマ一覧、ETL スケジューリング例、Slack 通知フォーマットなど）は別途作成することを推奨します。必要であれば README に追記する項目や、具体的な運用手順（systemd / Airflow / cron 連携例）も作成しますのでお知らせください。