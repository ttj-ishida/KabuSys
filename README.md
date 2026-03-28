# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ等を含んでいます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要なデータ基盤・研究・AI・監査機能を提供する Python パッケージです。主な目的は以下の通りです。

- J-Quants API からの差分 ETL（株価、財務、JPX カレンダー）
- RSS ニュース収集と LLM による銘柄センチメントスコア算出
- マクロセンチメント + MA 乖離を使った市場レジーム判定
- ファクター計算 / 特徴量探索（モメンタム、バリュー、ボラティリティ 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数ベースの設定管理（自動 .env ロード）

設計上の特徴として「ルックアヘッドバイアス防止」「冪等性を考慮した DB 操作」「外部 API のリトライ・フェイルセーフ」等を重視しています。

---

## 機能一覧（主要 API）

- 環境設定
  - `kabusys.config.settings`：環境変数からの設定取得（必須キーのチェック等）
  - 自動 .env ロード（プロジェクトルートを .git または pyproject.toml で探索）
  - 自動ロード無効化環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データ ETL / Data Platform
  - `kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)`：日次 ETL（calendar, prices, financials + 品質チェック）
  - `kabusys.data.jquants_client`：J-Quants API クライアント（取得・保存ユーティリティ）
  - `kabusys.data.calendar_management`：営業日判定・カレンダー更新
  - `kabusys.data.quality`：データ品質チェック（欠損/重複/スパイク/将来日付 等）
  - `kabusys.data.news_collector`：RSS フィード収集・前処理

- AI / NLP
  - `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`：銘柄ごとのニュースセンチメントを計算して `ai_scores` テーブルへ格納
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`：ETF 1321 の MA 乖離とマクロニュースの LLM センチメントを合成して `market_regime` を更新

- リサーチ
  - `kabusys.research.factor_research`：`calc_momentum` / `calc_value` / `calc_volatility`
  - `kabusys.research.feature_exploration`：将来リターン/IC/統計サマリー等
  - `kabusys.data.stats.zscore_normalize`：Zスコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - `kabusys.data.audit.init_audit_db(db_path)`：監査用 DuckDB を初期化して接続を返す
  - 監査テーブル：`signal_events`, `order_requests`, `executions`（冪等キー・ステータス管理あり）

---

## 必要要件

- Python 3.10 以上（型ヒントに `|` を使用）
- 主な外部依存パッケージ（コード参照）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml

（その他は標準ライブラリで実装されています。実際の運用ではさらに slack 等の依存が出る可能性があります）

インストール例（開発用）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトで requirements.txt があればそれを使用
# pip install -r requirements.txt
```

---

## 環境変数（主なキー）

このプロジェクトは環境変数により設定します。必須の主なキー:

- JQUANTS_REFRESH_TOKEN - J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD - kabu API のパスワード（必須）
- SLACK_BOT_TOKEN - Slack Bot トークン（必須）
- SLACK_CHANNEL_ID - Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY - OpenAI API キー（AI 機能を使う場合必須）
- KABUSYS_ENV - environment: "development" / "paper_trading" / "live"（省略時 development）
- LOG_LEVEL - ログレベル（DEBUG/INFO/...、省略時 INFO）
- DUCKDB_PATH - DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH - Monitoring 用 SQLite パス（省略時 data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD - 自動 .env ロードを無効化する場合に `1` をセット

注意:
- パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml が見つかるディレクトリ）にある `.env` / `.env.local` を自動でロードします（OS 環境変数 > .env.local > .env の優先順）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカルでの最低限の準備）

1. リポジトリをクローンして仮想環境を作成

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール

   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定（.env を作成）

   プロジェクトルートに `.env` を作成して必要なキーを設定します（例）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動ロードは config モジュールにより行われます（詳細は上記参照）。

4. ディレクトリを作成（DB 保存先）

   ```bash
   mkdir -p data
   ```

5. 監査 DB 初期化（オプション）

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（主要な例）

以下は対話的に使うときの簡単な例です。DuckDB 接続を渡して関数を呼び出します。

- 日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニュース NLP スコアを作成する（OpenAI API キー必須）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # api_key=None -> 環境変数 OPENAI_API_KEY を使用
print("written:", n_written)
conn.close()
```

- 市場レジーム判定を実行する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
conn.close()
```

- 監査 DB を作成する（別 DB として分離）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# 以後、order_requests / executions 等を利用して監査ログを記録可能
conn.close()
```

注意点:
- OpenAI 呼び出しはネットワーク・料金が発生します。API 呼び出しに失敗した場合は各モジュールがフェイルセーフ（スコア 0.0 を使う等）する設計です。
- データベーススキーマ（テーブル定義）や監査テーブルの初期化はコード側で提供されている関数を使ってください（例: `init_audit_db`）。

---

## ディレクトリ構成（主なファイルと説明）

以下は src/kabusys 以下の主要ファイルと役割の一覧です。パッケージはサブモジュール群に分かれています。

- kabusys/
  - __init__.py — パッケージルート、__version__
  - config.py — 環境変数管理・自動 .env ロード・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュース集約と OpenAI による銘柄センチメント算出（score_news）
    - regime_detector.py — ETF 1321 MA + マクロニュースで市場レジームを判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 系）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
    - calendar_management.py — JPX カレンダー管理・営業日判定
    - news_collector.py — RSS 収集・前処理
    - quality.py — データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログテーブル初期化とユーティリティ
    - etl.py — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/、data/、research/ はそれぞれの主要機能を実装

ファイルの docstring に設計方針や注意点が詳細に記述されています。実装の理解や拡張時は該当ファイルの docstring を参照してください。

---

## 運用・開発に関する備考

- 自動ロードされる .env の優先順位: OS 環境変数 > .env.local > .env
- 自動ロードの動作はプロジェクトルートの判定に依存（.git または pyproject.toml）。配布後の挙動にも配慮して実装されています。
- J-Quants や OpenAI 呼び出しはレート制御・リトライ・トークン自動リフレッシュなどに対応していますが、本番稼働前に鍵・レート・コストの確認を行ってください。
- DuckDB をローカルファイルで使用する場合、保存先ディレクトリに書き込み可能な権限が必要です。
- テスト時は各種外部呼び出し（HTTP、OpenAI）をモックすることを想定した設計になっています（各モジュールで差し替え可能な内部関数を用意）。

---

## トラブルシューティング

- 環境変数が見つからない場合は `kabusys.config.settings` が ValueError を投げます。必須キーの設定を確認してください。
- OpenAI のレスポンスパースエラーや API エラーは通常の運用でスコア 0.0 にフォールバックします。ログを確認してリトライやキーの状態を確認してください。
- DuckDB による executemany 空リストの取り扱いに注意しています（コード内で空リストチェック済み）。直接 SQL を叩く場合は互換性に注意してください。

---

必要に応じて README を拡張（CI / テスト手順、より詳細な設定例、運用手順）できます。追加で盛り込みたい情報があれば教えてください。