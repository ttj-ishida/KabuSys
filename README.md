# KabuSys

日本株向けの自動売買・データ基盤ライブラリ／ユーティリティ集です。  
ETL（J-Quants → DuckDB）、ニュース収集／NLP（OpenAI 経由）、リサーチ用ファクター計算、監査ログ／発注トレーサビリティ、マーケットカレンダー管理などを提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・特徴量計算・AI によるニュース分析・市場レジーム判定・監査用スキーマ初期化までをカバーする内部ライブラリです。  
主に以下用途を想定しています。

- 日次 ETL：J-Quants API から株価・財務・カレンダーを差分取得し DuckDB に保存
- ニュース収集：RSS からニュースを収集して raw_news に保存
- ニュース NLP：OpenAI（gpt-4o-mini 等）で銘柄単位のセンチメントを算出して ai_scores に保存
- 市場レジーム判定：ETF（1321）MA とマクロニュースを合成して market_regime を作成
- リサーチ：ファクター（モメンタム／ボラティリティ／バリュー等）と統計ユーティリティ
- 監査ログ：signal → order_request → execution を辿れる監査テーブル定義と初期化

---

## 主な機能一覧

- 環境設定管理（自動 .env ロード、settings オブジェクト）
- J-Quants クライアント（認証・ページネーション・レート制御・保存用ユーティリティ）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS → raw_news、SSRF 対策、トラッキング除去）
- OpenAI ベースのニュース NLP（銘柄単位スコアリング）
- 市場レジーム判定（ETF MA200 とマクロセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、forward returns、IC、Zスコア正規化）
- 監査ログ初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の `X | Y` 型注釈を使用）
- DuckDB、openai SDK、defusedxml などが必要

推奨的な手順（プロジェクトルートで実行）:

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   requirements.txt が無ければ下記を参考にインストールしてください:
   - pip install duckdb openai defusedxml

   例:
   - pip install -U pip
   - pip install duckdb openai defusedxml

3. パッケージのインストール（開発モード）
   - pip install -e .

4. 環境変数の設定
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（環境変数が優先）。

   必須（利用する機能に応じて設定してください）:
   - JQUANTS_REFRESH_TOKEN=...   （J-Quants のリフレッシュトークン）
   - OPENAI_API_KEY=...          （OpenAI API キー、news/regime で必須）
   - KABU_API_PASSWORD=...       （kabu ステーション API を使う場合）
   - その他（任意）
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

   自動ロードを無効化する場合:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   .env の読み込み順序:
   - OS 環境変数（優先） > .env.local > .env

---

## 使い方（抜粋：主要 API の例）

まず DuckDB 接続を用意します:

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
```

1) 日次 ETL を実行する（J-Quants から差分取得→保存→品質チェック）:

```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しなければ今日が対象
result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```

2) ニュースの AI スコアリング（前日15:00〜当日08:30 JST ウィンドウ）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

注意: OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定する必要があります。

3) 市場レジーム判定:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

4) ファクター計算例（モメンタム）:

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

5) 監査用 DB の初期化:

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

6) 設定値の取得:

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 未設定なら ValueError
print(settings.duckdb_path)            # Path オブジェクト
```

---

## よく使う環境変数（例）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（news_nlp / regime_detector）
- KABU_API_PASSWORD — kabu API を利用する場合のパスワード
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動 .env ロードを抑止

`.env.example` を参照してファイルを作成してください（プロジェクトルートに置くと自動読み込みされます）。

---

## ディレクトリ構成（主要ファイルと役割）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージのエクスポート定義（data, strategy, execution, monitoring）

- config.py
  - 環境変数管理・settings オブジェクト
  - .env 自動ロードロジック（プロジェクトルート検出）

- ai/
  - news_nlp.py
    - ニュースを銘柄ごとに集約し OpenAI でセンチメントを算出、ai_scores へ書き込み
  - regime_detector.py
    - ETF 1321 の MA200 とマクロ記事の LLM センチメントを合成して market_regime を作成

- data/
  - jquants_client.py
    - J-Quants API クライアント（認証・取得・保存）
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py
    - ETLResult の再エクスポート
  - news_collector.py
    - RSS 取得・前処理・raw_news への保存（SSRF 対策等含む）
  - calendar_management.py
    - 市場カレンダー管理／営業日判定／calendar_update_job
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査ログ（signal/order_request/executions）DDL と初期化関数

- research/
  - factor_research.py
    - Momentum/Volatility/Value ファクター計算
  - feature_exploration.py
    - forward returns, IC, rank, factor_summary 等
  - __init__.py
    - 研究向け関数のエクスポート

- その他
  - strategy/, execution/, monitoring/（本 README に含まれない部分は実装の追加想定）

---

## 注意事項 / 実運用でのポイント

- OpenAI や J-Quants の API キーは機密情報です。環境変数 / シークレット管理を利用してください。
- DuckDB のファイルパスは single-writer を想定しています。複数プロセスでの同時書き込みは避けてください。
- ETL や OpenAI 呼び出しは外部 API のレート制限や失敗を考慮していますが、実運用では監視・リトライポリシーの調整が必要です。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを抑止できます。
- ニュース収集や LLM 呼び出しはコスト（API 利用料）と遅延を伴います。バッチ設計やバッチサイズの調整を行ってください。

---

## ライセンス・貢献

本 README はコードベースに基づく説明ドキュメントです。実際のライセンスや貢献ルールについてはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

---

何か追加で README に載せたい利用例、CI 手順、依存関係の lockfile（requirements.txt / pyproject.toml）などがあれば教えてください。README をそれに合わせて拡張します。