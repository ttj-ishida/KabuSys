# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを備えています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやデータプラットフォームの基盤として使えるモジュール群です。主な責務は次のとおりです。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL（duckdb 保存）
- RSS ベースのニュース収集（SSRF 対策・正規化）
- ニュースの LLM（OpenAI）による銘柄センチメント算出（ai_scores への保存）
- マクロニュース＋ETF（1321）MA200 乖離を用いた市場レジーム判定
- ファクター計算、特徴量探索、統計ユーティリティ
- 監査ログ（signal / order_request / execution）用スキーマの初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計方針として、ルックアヘッドバイアス防止、冪等性（ON CONFLICT）、外部 API 呼び出しのリトライやフェイルセーフ処理、テスト容易性（キー注入・モック可能）を重視しています。

---

## 主な機能一覧

- data.jquants_client: J-Quants API クライアント（認証、ページネーション、レート制御、保存ユーティリティ）
- data.pipeline: 日次 ETL パイプライン（run_daily_etl 等）
- data.quality: データ品質チェック群（run_all_checks 等）
- data.news_collector: RSS 収集・前処理（SSRF 対策・記事ID 生成）
- data.calendar_management: 市場カレンダー管理・営業日ロジック
- data.audit: 監査ログテーブルのスキーマ初期化と DB 初期化ユーティリティ
- ai.news_nlp: ニュースを LLM でスコア化する score_news
- ai.regime_detector: ETF + マクロニュースを用いて日次市場レジームを判定する score_regime
- research: ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー、IC、統計サマリー）
- data.stats: Zスコア正規化ユーティリティ

---

## 前提・依存関係

- Python 3.10 以上（ソースに | 型注釈などを使用）
- 主要な外部ライブラリ:
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
- 標準ライブラリの urllib、json、logging 等を使用

インストール例（仮）:
```bash
python -m pip install -U pip
python -m pip install duckdb openai defusedxml
# またはローカルで開発する場合
# python -m pip install -e .
```

※ 実プロジェクトでは requirements.txt / pyproject.toml を用意してください。

---

## 環境変数 / 設定 (.env)

kabusys/config.py は .env / .env.local（プロジェクトルート）および OS 環境変数から設定を読み込みます。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

必須の環境変数（Settings で _require されるもの）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabu ステーション API 用パスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack チャンネル ID

OpenAI 用:
- OPENAI_API_KEY : OpenAI 呼び出しに使用（score_news / score_regime に渡すか環境変数で設定）

他のオプション（デフォルトがあるもの）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV (development|paper_trading|live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

.example の .env ファイル例:
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-....
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python と依存パッケージのインストール
   - Python 3.10+
   - pip で duckdb / openai / defusedxml をインストール

2. リポジトリを取得してインストール（任意）
   - git clone ...
   - python -m pip install -e . など（パッケージ配布を想定）

3. 環境変数を設定
   - プロジェクトルートに .env または .env.local を作成
   - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定

4. データディレクトリを作成（必要に応じて）
   - DUCKDB_PATH の親ディレクトリを作成
   - 例: mkdir -p data

---

## 使い方（主要ユースケース）

以下は最小限の利用例です。実行前に設定（環境変数 / .env）を整えてください。

- 日次 ETL の実行（DuckDB 接続を渡す）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（1321 + マクロニュース→ market_regime テーブルへ書込）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# conn を使って query / insert 可能
```

- J-Quants API から株価を直接取得（認証は settings 経由）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
from datetime import date

records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
print(len(records))
```

注意:
- score_news / score_regime は OpenAI 呼び出しを行います。API 使用量に注意してください。
- news_collector.fetch_rss は SSRF 対策やレスポンスサイズチェックを行います。外部 URL を扱う際は安全性を確認してください。

---

## 主要 API の説明（短め）

- data.pipeline.run_daily_etl(conn, target_date, ...): 日次 ETL を実行して ETLResult を返す。内部で calendar / prices / financials ETL を順に実行し、品質チェックを行います。
- ai.news_nlp.score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI に送信、ai_scores に保存します。
- ai.regime_detector.score_regime(conn, target_date, api_key=None): ETF 1321 の MA とマクロニュース（LLM）を合成して market_regime に書き込みます。
- data.jquants_client.fetch_* / save_*: API からの取得と DuckDB への保存ユーティリティ。
- data.audit.init_audit_db(path): 監査ログ用 DB を作成・初期化します。

---

## ディレクトリ構成

（主要ファイル抜粋）

- src/kabusys/
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
    - etl.py
    - stats.py
    - quality.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - etl.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - その他モジュール（strategy / execution / monitoring を想定するエントリは __all__ に含まれる）

※ 上記はソースに含まれる主なモジュールです。実際のリポジトリではさらに補助モジュールや CLI が存在する可能性があります。

---

## 運用上の注意 / ベストプラクティス

- 環境（KABUSYS_ENV）を適切に設定し、live 環境では API キーや実取引の設定を慎重に管理してください。
- OpenAI 呼び出しはコストが発生するため、テストでは小さな日付範囲やモックを使うことを推奨します。テスト時は内部の _call_openai_api をモックできます（score_news / regime_detector の実装で想定）。
- J-Quants API のレート制御・リトライが組み込まれていますが、適切な id_token とネットワーク条件を確認してください。
- DuckDB の executemany に空リストを渡すと問題となる箇所があるため、呼び出し時の引数に注意（実装でガード済み）。

---

## サポート / 拡張

- ニュースソースの追加: data/news_collector.DEFAULT_RSS_SOURCES に追加してください。
- 新しいファクターや研究用関数は research パッケージに追加してください。zscore_normalize など統計ユーティリティは data.stats にあります。
- 監査スキーマを変更する場合は data.audit の DDL を更新し、init_audit_schema を用いて初期化してください。

---

README は以上です。特定の利用例や追加のセットアップ（CI、パッケージング、テスト）について詳しく記載したい場合は、用途に応じて追記します。必要な箇所を指定してください。