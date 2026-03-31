# KabuSys

日本株自動売買 / データプラットフォーム用ライブラリ KabuSys の README（日本語）

簡潔な説明、セットアップ方法、使い方サンプル、ディレクトリ構成を記載します。

---

## プロジェクト概要

KabuSys は日本株向けのデータ ETL、ニュース NLP（LLMベース）、ファクター計算、研究ユーティリティ、監査（オーディット）および市場レジーム判定を含むライブラリ群です。  
主に以下の用途を想定しています。

- J-Quants API からの株価 / 財務 / 市場カレンダーの差分 ETL
- RSS ニュース収集と LLM による銘柄単位センチメント評価（ai_scores）
- マクロニュースと ETF（1321）の MA200 を組み合わせた市場レジーム判定
- ファクター（モメンタム / バリュー / ボラティリティ等）の計算と特徴量解析（研究用）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマの初期化
- データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）

設計上の特徴：
- DuckDB を使ったローカル DB ベースの ETL/解析ワークフロー
- LLM（OpenAI）との連携は JSON Mode を用いた厳密な入出力バリデーション
- Look-ahead bias を防ぐために日付処理で未来参照を行わない設計
- API 呼び出しに対するリトライ・バックオフ・レート制限対応
- 冪等性を考慮した DB 保存（ON CONFLICT / DELETE→INSERT 等）

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: J-Quants API 呼び出し（ページネーション / トークン自動リフレッシュ / 保存関数）
  - calendar_management: 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - news_collector: RSS 収集（SSRF 対策・サイズ上限・トラッキング除去）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize などの統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュースの LLM スコアを合成して market_regime テーブルへ書き込み
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings: 環境変数管理（自動 .env 読み込み、必須チェック、便利プロパティ）

---

## セットアップ手順

前提
- Python 3.10 以上推奨（typing の union と from __future__ を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   コードベースから必要となる主要なパッケージ例：
   - duckdb
   - openai
   - defusedxml

   例（pip）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   実際のプロジェクトでは requirements.txt / pyproject.toml に依存を定義してください。

4. 環境変数（.env）の準備  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   例 `.env`:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=eyJr...your_jquants_refresh_token...

   # OpenAI
   OPENAI_API_KEY=sk-...your_openai_key...

   # kabuステーション API（必要な場合）
   KABU_API_PASSWORD=your_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（モニタリング通知等）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 動作モード
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   Settings の必須項目（不足時は ValueError）
   - JQUANTS_REFRESH_TOKEN
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - KABU_API_PASSWORD（kabu 経由の注文を使う場合）

---

## 使い方（基本的な例）

以下は最も典型的な操作例です。すべて Python スクリプト内で実行します。

1) DuckDB 接続を作り、日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使う場合:
from kabusys.config import settings
db_path = str(settings.duckdb_path)  # 例: data/kabusys.duckdb

conn = duckdb.connect(db_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース NLP（銘柄別センチメント）を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# target_date に対するニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）が対象
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

3) 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査データベース（audit DB）を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリが無ければ作成される
# この conn を使って order/audit 関連の CRUD を行う
```

5) 設定参照（プログラム内）
```python
from kabusys.config import settings
print(settings.env, settings.is_live, settings.duckdb_path)
```

注意点:
- OpenAI API 呼び出しを行う関数は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / API 呼び出しはネットワーク遅延や API レート制限を受けるため、スケジューリングは夜間バッチやワーカーでの実行を推奨します。
- 本ライブラリは取引実行（execution）モジュールが含まれる場合、実際の発注は重大なリスクを伴います。KABUSYS_ENV を `paper_trading` にして試験してください。`is_live` で本番判定が可能です。

---

## よく使う API（抜粋）

- kabusys.data.pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
  - 日次 ETL（カレンダー、価格、財務、品質チェック）を実行するメイン関数。返り値は ETLResult。

- kabusys.data.jquants_client.fetch_daily_quotes(...)
  - J-Quants から日足を取得（ページネーション対応）。テスト用に id_token を渡せます。

- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースを LLM に送信して銘柄別 ai_scores を書き込む。

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - MA200 とマクロニュース（LLM）を組み合わせて market_regime テーブルへ書き込む。

- kabusys.data.audit.init_audit_db(path)
  - 監査用 DuckDB を作成してスキーマを初期化する（UTC タイムゾーン固定）。

---

## ディレクトリ構成（主要ファイル）

（src 配下を想定）

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
    - etl.py (再エクスポート)
    - calendar_management.py
    - news_collector.py
    - quality.py
    - audit.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/ 以下: ファクター計算・特徴量探索
  - data/jquants_client.py: J-Quants API クライアント（取得・保存関数）
  - data/news_collector.py: RSS 取得・前処理・保存支援
  - data/audit.py: 監査テーブル DDL と初期化ヘルパー

各モジュールは docstring に設計方針・処理フロー・注意点が詳細に記載されています。実装を読みながら用途ごとに関数を呼び出してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI の API キー（LLM 呼び出しに必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携時）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

config.Settings クラスからこれらに安全にアクセスできます（必須項目は未設定時にエラーを投げます）。

---

## テスト / 開発時のヒント

- 自動で .env 読み込みをしたくない（ユニットテスト等）は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants API 呼び出し部分は内部的にラッパー関数を経由しているため、ユニットテストではその内部関数を patch / monkeypatch してスタブ化できます（コード中に置換ポイントあり）。
- DuckDB を使うことでテストでは ":memory:" を渡すことでインメモリ DB を利用できます。

---

## 注意事項

- 本リポジトリには実際の売買ロジックや証券会社への発注を行う場合の安全対策（取引量制限、ポジション制約、二重発注防止など）が含まれる必要があります。実運用する場合は十分なテストとリスク管理を行ってください。
- OpenAI / J-Quants の課金・レート制限に注意してください。LLM呼び出しはバッチ処理・レート制御を推奨します。
- RSS フィード収集では SSRF / XML Bomb 等に対する対策を実装済みですが、外部ソースへアクセスする際は運用監視を行ってください。

---

不明点や README に追加してほしいサンプル（例: systemd ジョブや Airflow での実行例、docker-compose での環境構築など）があれば教えてください。必要に応じて追記します。