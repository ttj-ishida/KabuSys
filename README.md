# KabuSys

KabuSys は日本株の自動売買・データ基盤・リサーチ向けユーティリティ群を集めたライブラリです。  
DuckDB をデータレイクとして使用し、J-Quants API や RSS などからデータを取得して ETL ／ 品質チェック、NLP（OpenAI）によるニュースセンチメント、ファクタ計算、監査ログ管理などを行います。

## 主な特徴（機能一覧）
- データ取得・ETL
  - J-Quants API から株価日足、財務情報、マーケットカレンダーを差分取得・保存（ページネーション・レート制御・自動トークンリフレッシュ対応）
  - DuckDB への冪等保存（ON CONFLICT ベース）
- データ品質管理
  - 欠損・重複・日付不整合・スパイク検知などの品質チェック（QualityIssue を返す）
- ニュース収集・NLP
  - RSS 収集（SSRF 対策・トラッキングパラメータ除去・受信サイズ制限）
  - OpenAI を用いたニュースセンチメント解析（gpt-4o-mini、JSON Mode）
  - 銘柄別の ai_scores 書き込み
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を判定・保存
- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化など
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
- カレンダー管理
  - JPX カレンダーの更新、営業日判定、next/prev trading day 取得等

---

## セットアップ手順

前提
- Python 3.9+（型アノテーションや一部の記法から推奨）
- ネットワーク経由の API キー（J-Quants / OpenAI）を用意

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージのインストール（代表的な依存）
   - pip install duckdb openai defusedxml
   - 必要に応じて他のライブラリ（requests 等）を追加

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. 環境変数の設定
   - .env ファイルまたは環境変数で下記を設定します（必須は後述）
   - 自動でプロジェクトルートの .env と .env.local を読み込みます（CWD ではなくパッケージ位置から .git / pyproject.toml を探索）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

推奨の .env に含めるキー（一例）
- JQUANTS_REFRESH_TOKEN=...        （必須：J-Quants 用リフレッシュトークン）
- OPENAI_API_KEY=...               （必須：OpenAI API キー。score_news/score_regime で使用）
- KABU_API_PASSWORD=...            （kabuステーション API 用パスワード）
- SLACK_BOT_TOKEN=...              （通知用 Slack ボットトークン）
- SLACK_CHANNEL_ID=...             （通知先チャンネル ID）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...
- DUCKDB_PATH=data/kabusys.duckdb   （デフォルト）
- SQLITE_PATH=data/monitoring.db    （監視 DB 等）

注意:
- 環境変数が未設定の場合、一部プロパティは Settings が ValueError を投げます（必須トークンなど）。

---

## 使い方（主な API 使用例）

ライブラリは Python API を通して利用します。例はすべて DuckDB 接続（duckdb.connect(...)）を渡す想定です。

1. DuckDB に接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2. 日次 ETL（株価・財務・カレンダーの差分更新と品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3. ニュースセンチメント解析（ai_scores へ書き込み）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote scores for {count} codes")
```
- OpenAI API キーは OPENAI_API_KEY 環境変数、または score_news の api_key 引数で指定可能。
- テストでは kabusys.ai.news_nlp._call_openai_api をモックして OpenAI コールを差し替えられます。

4. 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5. ETL の個別ジョブ（例: run_prices_etl）
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

6. 監査ログスキーマ初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# 既存 conn を使う場合は init_audit_schema(conn) を呼ぶことも可能
```

7. カレンダー関連ユーティリティ（営業日判定など）
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## テスト／開発メモ
- OpenAI 呼び出しは内部で JSON Mode（response_format={"type": "json_object"}）を使っています。テスト時は _call_openai_api を patch して擬似レスポンスを返してください。
- news_collector は外部ネットワーク（RSS）を扱うため、ネットワーク I/O をモックすると安定します。
- .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われ、OS 環境変数を上書きする順序は .env < .env.local、ただし既存 OS 環境変数は保護されます。
- DuckDB バージョン差異（例: executemany の空引数制約）に注意した実装が含まれています。

---

## ディレクトリ構成（概要）
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（OpenAI 経由）
    - regime_detector.py             — マクロ + MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL 用公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py              — RSS 収集、raw_news 保存
    - calendar_management.py         — 市場カレンダー管理、営業日ユーティリティ
    - quality.py                     — データ品質チェック（QualityIssue）
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum/value/volatility）
    - feature_exploration.py         — 将来リターン、IC、factor_summary 等
  - (その他: strategy, execution, monitoring 等のパッケージは __all__ に含まれている想定)

---

## 環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for news/regime) — OpenAI API キー
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — デフォルトの DuckDB ファイルパス
- SQLITE_PATH — 監視用 SQLite パス（用途に応じ）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化

---

## 注意事項
- バックテストや研究用途でデータ取得関数を使用する際は「Look-ahead bias」に注意してください。ドキュメントや各関数の docstring にある通り、取得日時の扱いや過去データ参照の扱いに配慮して利用してください。
- 実際の発注・ブローカー連携は実装箇所に依存します。本コードベースでは監査ログや order_request の枠組みを提供しますが、実際のブローカー API への送信は別実装が必要です。
- セキュリティ: news_collector では SSRF 対策や XML デシリアライズ対策（defusedxml）を導入しています。外部 URL を扱う箇所は追加の検証を行うことを推奨します。

---

必要であれば、インストール用の requirements.txt / pyproject.toml の雛形や、よく使うサンプルスクリプト（ETL 実行スクリプトなど）を作成します。どのサンプルが欲しいか教えてください。