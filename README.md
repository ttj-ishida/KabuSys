# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
DuckDB をデータレイクとして用い、J-Quants からのデータ取得、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算、ETL パイプライン、監査ログ（発注トレース）などのユーティリティを提供します。

現在のバージョン: 0.1.0

---

## プロジェクト概要

KabuSys は下記の目的を持つモジュール群で構成されています。

- J-Quants API からの株価・財務・カレンダー取得（レートリミット・リトライ・ID トークン自動更新対応）
- RSS ベースのニュース収集と前処理（SSRF・XML/サイズ攻撃対策）
- OpenAI を用いたニュースセンチメント評価（銘柄単位 / マクロセンチメント）
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- 研究用ファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）用のスキーマ初期化機能
- 環境変数ベースの設定管理（.env 自動読み込み機能あり）

設計方針としては、バックテストでのルックアヘッドバイアス回避、冪等性（ON CONFLICT 等）、フェイルセーフ（API失敗時の継続）を重視しています。

---

## 主な機能一覧

- 環境設定管理
  - .env/.env.local 自動読み込み（プロジェクトルート検出）
  - 必須キーチェックと便利なプロパティ（settings オブジェクト）

- データ取得 / ETL
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar 等）
  - DuckDB への冪等保存（save_* 関数）
  - 日次 ETL 実行エントリ（run_daily_etl）と個別 ETL ジョブ

- ニュース収集 / NLP
  - RSS フィード収集（SSRF・gzip・サイズ制限など安全仕様）
  - ニュース前処理（URL除去／正規化）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（score_news）
  - マクロセンチメント＋MA200 を用いた市場レジーム推定（score_regime）

- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算 / IC（Information Coefficient）計算 / 統計サマリー

- データ品質チェック
  - 欠損、重複、将来日付、前日比スパイクなどを検出（run_all_checks）

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルの DDL と初期化ヘルパー（init_audit_schema / init_audit_db）
  - 監査向けインデックス作成や UTC タイムゾーン固定

---

## 必要な環境変数（主要）

設定は環境変数またはプロジェクトルートの `.env`, `.env.local` から読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

必須（Settings._require が要求するもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）

注意: OpenAI を使う関数（score_news, score_regime 等）は api_key 引数を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。

---

## セットアップ手順（例）

1. Python バージョン
   - Python 3.10+ を想定（typing | 型ヒント等を使用）。プロジェクトの pyproject.toml がある場合はそちらを参照してください。

2. インストール（開発中の場合）
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - 必要パッケージをインストール（例）
     - pip install -r requirements.txt
     - または開発環境であれば: pip install -e .

   （※ 本リポジトリの requirements.txt はサンプルに依存します。openai, duckdb, defusedxml 等が必要です）

3. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、上記必須キーを設定します。
     例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB 用ディレクトリ作成
   - settings.duckdb_path に基づく親ディレクトリを作成（モジュールの関数が自動作成する場合あり）
   - 例: mkdir -p data

---

## 使い方（主要なユースケース・コード例）

以下はライブラリを Python から直接呼ぶ際の簡単な例です。DuckDB 接続は duckdb パッケージを利用します。

- 設定を参照する
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> OPENAI_API_KEY を参照
print(f"書込み銘柄数: {n_written}")
```

- 市場レジーム（マクロ + MA200）を算出して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で環境変数参照
```

- RSS を取得して raw_news に挿入する（news_collector の保存関数と組み合わせて利用）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

- 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って以後監査ログを書き込めます
```

- J-Quants の ID トークンを取得する（内部でリフレッシュを行う）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

---

## よく使うモジュール一覧（概略）

- kabusys.config
  - settings: 環境設定（プロパティ経由で各種キーを取得）
  - .env/.env.local の自動ロード機構を内蔵

- kabusys.data
  - jquants_client: API 呼び出し・保存ロジック
  - pipeline: run_daily_etl / individual ETL ジョブ / ETLResult
  - news_collector: RSS 取得・前処理
  - calendar_management: 市場カレンダーと営業日判定
  - quality: データ品質チェック
  - audit: 監査スキーマ初期化ユーティリティ
  - stats: zscore_normalize など

- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント算出
  - regime_detector.score_regime: 日次市場レジーム判定

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成（src 内、抜粋）

以下は主要ファイルのツリー例（完全版はリポジトリ参照）:

- src/
  - kabusys/
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
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（その他ユーティリティ群）
    - ai/（OpenAI 連携）
    - monitoring/（モニタリング関連は __all__ に含まれるが実装ファイルは該当ディレクトリ参照）

（注）実際のファイル一覧はリポジトリの src/kabusys 以下を参照してください。

---

## 運用上の注意点 / ベストプラクティス

- Look-ahead バイアス対策
  - ライブラリ内の多くの関数は date/target_date を明示的に受け取り、date.today()/datetime.today() を直接参照しないよう設計されています。バックテスト時は target_date を必ず固定してください。

- 冪等性
  - ETL 保存処理は ON CONFLICT / UPDATE を用いて冪等化されています。外部からデータを入れる場合でも基本的に安全ですが、スキーマ変更時は注意してください。

- OpenAI 呼び出し
  - レスポンスのパース失敗や API エラー時はフェイルセーフでスコア 0.0（またはスキップ）にフォールバックする実装です。大量バッチを投げる場合はレートやコストに留意してください。

- セキュリティ
  - news_collector は SSRF や XML 攻撃対策（defusedxml、リダイレクト時のホストチェック、サイズ上限など）を含みますが、利用環境のセキュリティ要件に合わせて監査してください。

---

## 貢献 / 開発

- ローカルでの開発は仮想環境を用意し、必要な依存パッケージ（duckdb, openai, defusedxml など）をインストールしてから行ってください。
- テストの際は自動 .env 読み込みが邪魔な場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- OpenAI や J-Quants の API 呼び出しは外部依存のため、ユニットテストでは各モジュールの _call_openai_api や _urlopen、_request 等をパッチしてモックしてください（コード内にその旨の記載があります）。

---

README にない具体的な使い方（例：特定の ETL ワークフロー、モニタリングや発注フローの詳細）や、CI / デプロイ手順、requirements.txt のサンプル等が必要であれば、実際の運用目的に合わせて追加で作成します。何を優先して追記しましょうか？