# KabuSys

日本株向けのデータプラットフォーム兼自動売買（研究・ETL・監査・AI支援）ライブラリです。  
このリポジトリは以下の機能群を備え、DuckDB を中心にデータ取得・品質管理・特徴量生成・AI スコアリング・監査ログを提供します。

- ETL（J-Quants からの株価・財務・カレンダー取得）
- ニュース収集と NLP による銘柄センチメント（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算（Momentum / Value / Volatility 等）
- データ品質チェック
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- J-Quants クライアント（レート制限・リトライ・トークン管理）
- マーケットカレンダー管理（営業日判定等）

以下はこのコードベースの簡潔な使い方・セットアップ・ディレクトリ構成です。

---

## 機能一覧（抜粋）
- data/jquants_client.py
  - J-Quants API との通信（ページネーション・トークン自動更新・レート制御・保存ユーティリティ）
  - save_daily_quotes / save_financial_statements / save_market_calendar
- data/pipeline.py
  - run_daily_etl: カレンダー・株価・財務の差分 ETL、品質チェックを統合
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- data/news_collector.py
  - RSS フィード取得、前処理、raw_news への冪等保存（SSRF 対策・トラッキング除去）
- ai/news_nlp.py
  - ニュースを銘柄別に集約して OpenAI でセンチメントを取得し ai_scores に保存
- ai/regime_detector.py
  - ETF（1321）200 日 MA 乖離とマクロニュース LLM スコアを合成して市場レジームを判定
- data/quality.py
  - 欠損・重複・スパイク・日付不整合のチェック（QualityIssue を返す）
- research/
  - factor_research.py, feature_exploration.py：ファクター計算・将来リターン・IC・統計サマリ
- data/audit.py
  - 監査テーブルの DDL と初期化（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提:
- Python 3.10+（型アノテーションに | を使用しているため）
- Git リポジトリをクローン済み

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（優先度: OS env > .env.local > .env）。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（アプリの実行で必要になる）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   AI 関連（OpenAI）:
   - OPENAI_API_KEY: news_nlp / regime_detector のデフォルトで参照される（関数呼び出しで api_key を渡すことも可）。

   任意（デフォルト値あり）
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/...）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等（監視用）

4. データベース用ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な API 例）

以下はいくつかの典型的な呼び出し例です。実行前に必ず必要な環境変数を設定してください。

- 共通：settings を使った経路取得・設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（株価・財務・カレンダーの差分 ETL + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（OpenAI を用いて ai_scores に書き込み）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込んだ銘柄数: {n}")
```

- 市場レジーム判定（ma200 とマクロニュースの LLM スコア合成）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

conn = init_audit_db(Path("data/audit.duckdb"))
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
recs = calc_momentum(conn, target_date=date(2026,3,20))
# recs は各銘柄ごとの dict のリスト
```

注意:
- AI 呼び出し (OpenAI) は API のレート・使用料金が発生します。テスト時は api_key にダミーを与えたり、モック化してください。
- DuckDB のバージョンや動作環境に依存する部分（executemany 空リスト等）の取り扱いに注意してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数・設定読み込みロジック（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py            — ニュース NLP（OpenAI）バッチスコアリング
  - regime_detector.py     — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得・保存）
  - pipeline.py            — ETL パイプラインと個別ジョブ
  - calendar_management.py — マーケットカレンダー管理（営業日判定等）
  - news_collector.py      — RSS ニュース収集（SSRF 対策等）
  - quality.py             — データ品質チェック
  - stats.py               — 共通統計ユーティリティ（Z-score 等）
  - etl.py                 — ETLResult 再エクスポート
  - audit.py               — 監査ログ DDL / 初期化
- research/
  - __init__.py
  - factor_research.py     — Momentum / Volatility / Value の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリ 等
- research/ ... （その他補助モジュール）

（注）README はコードベースの主要な部分を抜粋しています。細かい実装上の仕様は各モジュールの docstring を参照してください。

---

## 環境変数一覧（要約）
必須
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     — kabu API 用パスワード
- SLACK_BOT_TOKEN       — Slack ボットトークン（通知）
- SLACK_CHANNEL_ID      — Slack チャネル ID

必須（AI機能を使う場合）
- OPENAI_API_KEY        — OpenAI API キー（関数呼び出し時に api_key を与えることも可）

任意 / デフォルトあり
- DUCKDB_PATH           — data/kabusys.duckdb（デフォルト）
- SQLITE_PATH           — data/monitoring.db（デフォルト）
- KABUSYS_ENV           — development | paper_trading | live（default: development）
- LOG_LEVEL             — INFO（デフォルト）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットで .env 自動読み込みを無効化

---

## 開発・テストのヒント
- AI 呼び出しや外部 API 呼び出しはユニットテストでモック化してテストしてください（news_nlp などは _call_openai_api をモック可能）。
- .env.example を用意して環境を共有すると再現性が高まります。
- DuckDB は軽量でローカルファイルをそのまま利用できるため、テスト用に ":memory:" 接続を使うことも可能です（audit.init_audit_db で ":memory:" を指定可能）。
- ETL/パイプラインは例外を全て捕捉しつつ結果オブジェクト（ETLResult）で状況を返す設計になっています。ログを参照して問題を診断してください。

---

もし README の内容をプロジェクトの実際の pyproject.toml、requirements、.env.example に合わせて調整したい場合は、それらのファイルを提供してください。さらに具体的な実行例やデプロイ手順（systemd ユニット、cron、コンテナ化など）も必要であれば追記します。