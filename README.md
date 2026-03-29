# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
市場データの ETL、ニュースの NLP スコアリング、リサーチ用ファクター計算、監査ログ（トレーサビリティ）、API クライアントなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python モジュール群です。

- J-Quants API を使った株価・財務・カレンダーの差分取得（ETL）
- DuckDB を用いた永続化／品質チェック（Data Platform 機能）
- RSS ニュース収集と OpenAI（GPT 系）による銘柄別ニュースセンチメント評価
- マーケットレジーム判定（ETF MA とマクロニュースの LLM スコアを合成）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 発注から約定まで追跡可能な監査ログ（監査テーブル定義・初期化）

設計方針の一部:
- ルックアヘッドバイアス（未来情報の参照）を避ける実装
- API 呼び出しに対するリトライ・バックオフ・レート制御
- DuckDB による冪等的な保存（ON CONFLICT / DELETE→INSERT 等）
- テスト容易性のため設定注入やモック差替え可能な構造

---

## 機能一覧

- データ取得／ETL
  - J-Quants から株価日足、財務、上場情報、JPX カレンダーを差分取得
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック
  - 欠損（OHLC）チェック、スパイク検出、重複チェック、日付整合性チェック
  - run_all_checks
- ニュース収集・前処理
  - RSS 収集（SSRF 対策、URL 正規化、トラッキングパラメータ除去）
- ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM に投げ、ai_scores テーブルへ保存: score_news
  - マクロニュースを元に市場レジームを判定: score_regime
- リサーチ（研究）
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン、IC（Spearman）の計算、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義および初期化 helper
  - init_audit_schema / init_audit_db

その他: レートリミッタ、HTTP リトライ、OpenAI 呼び出しのリトライ制御、ログレベル管理。

---

## 必要条件（例）

最低限の依存（実際の requirements.txt を参照してください）:

- Python 3.10+
- duckdb
- openai
- defusedxml

注: J-Quants / OpenAI / kabuステーション など外部 API の利用には各種 API キーが必要です。

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv && source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトで提供される requirements.txt があればそれを使用）

3. 環境変数設定
   - プロジェクトルートに `.env`（およびローカル上書き用 `.env.local`）を配置すると、自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. DuckDB データベースのディレクトリ作成（例）
   - デフォルトでは `data/kabusys.duckdb` を使用します（設定で変更可能）。

---

## 必要な環境変数（代表）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABUSYS_ENV: 環境（development / paper_trading / live）。デフォルトは development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 等（デフォルト data/monitoring.db）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）

.env の読み込みルール:
- 優先順位: OS 環境 > .env.local > .env
- `.env.local` は .env を上書き（override）します。
- テストや CI で自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## 使い方（主要な例）

以下は基本的な利用例です。実行は Python スクリプトやジョブランナーから行ってください。

- DuckDB に接続して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定しない場合は today が使用されます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントを評価して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written: {n_written}")
```

- マーケットレジーム判定を実行
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB を初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# または init_audit_schema(conn) で既存接続にスキーマ追加
```

- RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 開発・テストのヒント

- 環境読み込みをテストで無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しやネットワーク I/O はユニットテストでモック可能（各モジュールは _call_openai_api や _urlopen など差し替えしやすく設計されています）
- DuckDB をメモリモードで利用して高速テスト: duckdb.connect(":memory:")
- 設定バリデーション: `kabusys.config.settings` が環境変数の存在・値の検査を行います。起動前に必須キーが揃っていることを確認してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数／設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - quality.py              — 品質チェック（check_missing_data 等）
    - news_collector.py       — RSS 収集（fetch_rss 等）
    - calendar_management.py  — 市場カレンダー管理
    - audit.py                — 監査ログ初期化（init_audit_schema / init_audit_db）
    - stats.py                — 共通統計ユーティリティ（zscore_normalize）
    - etl.py                  — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（calc_momentum, calc_value, calc_volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー等
  - research/..., ai/..., data/... の各モジュールに詳細実装あり

---

## 注意点・実運用メモ

- API キーの管理は厳重に（.env は .gitignore に含めること）
- OpenAI / J-Quants の呼び出しはレート制限・課金に注意
- ETL は夜間バッチ向けに設計済み。バックテストでの利用は look-ahead を避ける設計に従ってください
- 実口座での発注は risk 管理が重要（KABUSYS_ENV を正しく設定し、live モードでのみ実際発注するよう分離してください）

---

必要であれば、README にサンプル .env.example のテンプレート、CI 実行手順、詳細なテーブルスキーマや SQL を追記できます。追加で欲しい項目（例: API キー発行手順や実行スクリプト）は教えてください。