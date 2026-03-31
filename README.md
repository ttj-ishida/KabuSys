# KabuSys — 日本株自動売買プラットフォーム（README）

本リポジトリは日本株のデータプラットフォーム・リサーチ・AI スコアリング・監査ログ・ETL 等を備えた自動売買基盤のコアライブラリ群です。以下はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成のまとめです。

※本 README はコードベース（src/kabusys 配下）の実装に基づいて作成しています。

---

## プロジェクト概要

KabuSys は次を目的とした Python ライブラリ群です。

- J-Quants API からの株価・財務・市場カレンダー等の差分 ETL（取得・保存・品質チェック）
- ニュース収集（RSS）と LLM によるニュースセンチメントの銘柄別スコア化
- 市場レジーム判定（ETF の MA200 とマクロニュースの LLM スコア合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合など）

設計上の特徴：
- DuckDB を主要なローカル DB として使用（ETL や監査ログ保存）
- J-Quants API に対するレート制御・リトライ・トークン自動更新
- OpenAI（gpt-4o-mini）を用いるニュース/マクロ評価（JSON mode）
- ルックアヘッドバイアスを避ける設計（date.today() を不用意に参照しない等）
- 冪等性（保存は ON CONFLICT / DO UPDATE 等で再実行可能）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch/save、get_id_token、rate limiter、pagination）
  - 市場カレンダー管理（営業日判定 / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得、前処理、SSRF 対策、DB 保存に向けた整形）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化と監査 DB ヘルパー（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: ニュースの銘柄別センチメントを LLM で評価し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM スコア合成で市場レジームを判定・保存
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・評価（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - .env 自動読み込み（.env / .env.local）と Settings クラスによる環境管理
  - 自動ロード抑止フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 要件

- Python 3.10 以上（型注釈で | を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, json, datetime, logging 等

（実際の pyproject.toml / requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係のインストール（例）
   - pip install duckdb openai defusedxml

   ※実際のプロジェクトでは pyproject.toml / requirements.txt が提供されている想定なので、それに従ってください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env または .env.local を置くことで自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   推奨する最低環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=your_openai_api_key
   - KABU_API_PASSWORD=your_kabuapi_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - DUCKDB_PATH=data/kabusys.duckdb      (省略時のデフォルト)
   - SQLITE_PATH=data/monitoring.db       (省略時のデフォルト)
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な呼び出し方）

以下はライブラリをインポートして使う際の代表的な例です。実行前に必要な環境変数が設定されていることを確認してください。

- DuckDB 接続の作成（デフォルトファイルは settings.duckdb_path）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェックを順に実行）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニューススコアリング（指定日分のニュースを LLM で評価して ai_scores に保存）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

num_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None で OPENAI_API_KEY を参照
print(f"written: {num_written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DuckDB を新規作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を用いて order_requests / signal_events / executions テーブルへアクセス可能
```

- RSS フィード取得（ニュース収集ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- J-Quants の ID トークン取得（手動）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

注意点：
- OpenAI 呼び出し部分はネットワーク/課金が発生します。テスト時は該当関数をモックする設計になっています（内部で _call_openai_api を分離）。
- J-Quants API 呼び出しはレート制御・リトライを行いますが、API 利用規約に従ってください。
- ETL や保存は冪等設計（ON CONFLICT）で再実行可能です。

---

## 環境変数 / 設定（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携に使用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: development / paper_trading / live（動作モード）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する（値があると無効）

設定は Settings クラス経由で参照可能:
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.env, settings.is_live)
```

---

## 安全性・設計ノート

- ニュース収集には SSRF 対策と受信サイズ制限が組み込まれています（_is_private_host, redirect 検査, MAX_RESPONSE_BYTES 等）。
- J-Quants API は rate limiter（120 req/min）を守る実装が組まれています。
- OpenAI 呼び出しは JSON mode を用い、レスポンスのバリデーション・リトライ戦略を実装しています。
- ルックアヘッドバイアス防止のため、関数は target_date を明示的に受け取り、内部で date.today() を不用意に参照しない方針です。
- DB 保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）にしています。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news: ニュースセンチメントを銘柄別に算出して ai_scores に保存
    - regime_detector.py
      - score_regime: ETF MA200 とマクロニュースを組み合わせて market_regime を更新
  - data/
    - __init__.py
    - pipeline.py
      - ETL のエントリポイント (run_daily_etl, run_prices_etl, ...)
      - ETLResult dataclass
    - etl.py
      - ETLResult の再エクスポート
    - jquants_client.py
      - J-Quants API クライアント（fetch_*, save_*）
      - get_id_token、rate limiter、HTTP リトライ等
    - news_collector.py
      - RSS 取得、前処理、記事 ID 生成、SSRF 対策
    - calendar_management.py
      - market_calendar の操作、営業日判定、calendar_update_job
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログテーブル DDL と初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - (その他)
    - monitoring / execution / strategy 等は __all__ に含まれていますが、今回のコード抜粋では詳細は省略

---

## よくある操作・コマンド例

- ETL を cron / Airflow などで日次実行する場合
  - Python スクリプトから run_daily_etl を呼ぶ。exceptions はログに残して再試行可能にする。
- ニュース収集ジョブ
  - RSS 一覧を定期取得して raw_news / news_symbols に保存 → score_news を呼ぶ
- 監査 DB 初期化
  - 起動時またはデプロイ時に init_audit_db を実行して監査 DB を作成

---

## 開発・テストについて

- OpenAI や外部 API 呼び出しはユニットテストでモック可能に設計（内部の _call_openai_api や _urlopen 等を patch できる）。
- .env の自動ロードを無効にしてテスト環境用に個別設定を渡すことができます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## ライセンス・注意事項

- 本 README は実装コードに基づく説明です。実際に運用する際は API キーや機密情報の管理、取引リスク、法令遵守に十分注意してください。
- 実際の自動売買を行う場合は、paper_trading（模擬取引）環境で十分な検証を行い、live モードへの切替時は慎重に運用してください。

---

必要であれば、以下を追加で用意できます：
- CI 用のテスト実行方法（pytest 例）
- pyproject.toml / requirements.txt の推奨内容
- さらに詳細な API リファレンス（各関数の引数/戻り値一覧）
- デプロイ・運用手順（systemd / Supervisor / Docker イメージ等）

ご希望があれば上記のいずれかを追加で作成します。