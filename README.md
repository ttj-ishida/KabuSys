# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリ群です。データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI を利用したセンチメント）、市場レジーム判定、リサーチ用のファクター計算、監査ログ（発注／約定のトレーサビリティ）といった機能を提供します。

本リポジトリは Python パッケージとして設計されており、DuckDB を主要なオンディスク DB として利用します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（主要な設定）
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は次の機能ブロックから構成されます（主要な設計方針の抜粋）:

- データ取得（J-Quants API）と ETL（差分取得・バックフィル・品質チェック）
- 市場カレンダー管理（JPX カレンダーの差分同期と営業日判定）
- ニュース収集（RSS）と NLP による銘柄別センチメント評価（OpenAI）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロ記事の LLM センチメント）
- 研究用モジュール（ファクター計算・将来リターン・IC 計測・統計ユーティリティ）
- 監査ログ（signal → order_request → executions のトレーサビリティテーブル）
- 設定管理（.env ファイル自動ロード機能・環境変数経由の設定）

設計上の重要点:
- ルックアヘッドバイアスを避ける実装（target_date を明示する設計）
- DuckDB を中心に SQL + 最小限の標準ライブラリで実装
- OpenAI 呼び出しはリトライとフェイルセーフ（失敗時はスコア 0 等）を実装

---

## 機能一覧

- ETL
  - run_daily_etl: 市場カレンダー、株価（日足）、財務データの差分取得・保存
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果を ETLResult オブジェクトで報告

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出（前日比閾値）、重複検出、日付整合性チェック
  - run_all_checks による一括実行

- J-Quants クライアント
  - 認証（refresh_token → id_token）、ページネーション対応、リトライ/レート制御
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - DuckDB への冪等保存関数（save_daily_quotes 等）

- ニュース収集 / NLP
  - RSS 取得・前処理（SSRF 対策・トラッキングパラメータ除去）
  - news_nlp.score_news: 銘柄ごとのセンチメントを OpenAI で取得して ai_scores に書き込む
  - OpenAI の JSON Mode を利用し、レスポンス検証と安全なクリッピング

- 市場レジーム判定
  - regime_detector.score_regime: ETF 1321 の MA200 乖離 + マクロ記事 LLM センチメントを合成して market_regime テーブルへ書き込む

- 監査ログ（audit）
  - init_audit_schema / init_audit_db: signal_events, order_requests, executions 等のテーブルを初期化
  - トレーサビリティと冪等キー設計（order_request_id、broker_execution_id）

- 研究（research）
  - ファクター計算 (momentum, value, volatility)
  - 将来リターン計算、IC 計算、統計サマリ、Z スコア正規化

---

## セットアップ手順（開発環境向け）

前提:
- Python 3.10 以上（| 型ヒント等を使用）
- Git

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（最低限）
   - 必要な主要パッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   （将来的に requirements.txt / pyproject.toml があればそちらを利用してください）

4. パッケージを開発モードでインストール（オプション）
   ```
   pip install -e .
   ```

5. 環境変数を設定
   - プロジェクトルートに `.env` を置くと自動的に読み込まれます（設定管理モジュールで .env / .env.local を自動ロード）
   - 自動ロードを無効にする: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 主要な環境変数は次節参照

---

## 主要な環境変数（設定）

settings クラスは環境変数から読み込みます。主要なキー:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン

- kabu（kabuステーション API）
  - KABU_API_PASSWORD — kabuAPI のパスワード
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi

- OpenAI / 通知
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime が参照）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）

- DB / ファイルパス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PID_FILE_PATH / KILL_FLAG_PATH — 監視用ファイルパス

- 実行環境 / ログ
  - KABUSYS_ENV — development / paper_trading / live
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

例 .env（最低限: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY を設定してください）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡易サンプル）

以下はパッケージの主要 API を Python から利用する例です。実行前に環境変数や DB パスを設定してください。

- DuckDB 接続を作って ETL を実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# settings が DUCKDB_PATH を提供する想定
conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアを付与する（OpenAI API キー 必須）:
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {n_written} codes")
```

- 市場レジームを判定する:
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB を初期化する:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

- RSS を取得する（news_collector の低レベル関数）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["title"], a["datetime"])
```

注意:
- OpenAI 呼び出しは gpt-4o-mini を想定した JSON Mode を使用しています。API レスポンスは厳密な JSON を期待して検証・パースします。
- J-Quants API はレート制限（120 req/min）に対応するレートリミッタとリトライを備えています。

---

## ディレクトリ構成（主要ファイルと説明）

パッケージルート: src/kabusys

- __init__.py
  - package エクスポートの定義（data, strategy, execution, monitoring 等）

- config.py
  - .env 自動読み込み、Settings クラス（環境変数経由の設定取得）

- ai/
  - __init__.py
  - news_nlp.py
    - ニュース記事から銘柄別センチメントを取得して ai_scores に書き込む機能
  - regime_detector.py
    - ETF 1321 の MA200 乖離とマクロ記事センチメントを合成して market_regime を作成

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API の認証・取得・DuckDB 保存ロジック（レート制御・リトライ・ページネーション）
  - pipeline.py
    - ETL のメインロジック（run_daily_etl, run_prices_etl 他）と ETLResult
  - etl.py
    - ETLResult の再エクスポート
  - calendar_management.py
    - market_calendar 管理、営業日判定、calendar_update_job
  - news_collector.py
    - RSS 収集、前処理、SSRF 対策、記事 ID 正規化
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査ログ（signal_events, order_requests, executions）DDL・初期化
  - その他（将来的に jquants クライアントの補助等）

- research/
  - __init__.py
  - factor_research.py
    - momentum/value/volatility 等のファクター計算
  - feature_exploration.py
    - calc_forward_returns, calc_ic, factor_summary, rank 等

---

## 運用上の注意点

- 本ライブラリはバックテストや自動売買の支援用途向けに設計されています。実際の証券会社への発注を組み合わせる場合は十分な検証（特に冪等性・エラーハンドリング）を行ってください。
- OpenAI の API 呼び出しや外部 API 呼び出しはコストとレート制限がかかります。ローカル開発ではモック化してテストすることを推奨します（モジュール内の _call_openai_api を patch 可能に設計）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に探索します。CI / テスト実行時に不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB への executemany に空リストを渡せないバージョン依存の配慮がコード内でされています（空チェックに注意）。

---

必要であれば README にサンプル .env.example、CI 用の設定、詳細な API ドキュメント（各モジュール関数の引数/戻り値詳細）、ユニットテストの実行方法等も追加できます。追加を希望する項目を教えてください。