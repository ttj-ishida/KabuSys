# KabuSys

KabuSys は日本株のデータパイプライン、AI ベースのニュースセンチメント/市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などを提供する自動売買システム基盤ライブラリです。本リポジトリは DuckDB を中核にしたデータレイヤ、J-Quants からの ETL、RSS ニュース収集、OpenAI を用いた NLP 評価、研究用ユーティリティを含みます。

この README はプロジェクトの概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（.env）
- 基本的な使い方（コード例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は次のコンポーネントを統合した、日本株向けのデータ基盤・リサーチ・自動化レイヤです。

- J-Quants API 経由のデータ取得（株価日足、財務、上場情報、マーケットカレンダー）
- DuckDB を用いた永続化（raw_prices / raw_financials / market_calendar / raw_news / ai_scores / audit テーブル群 等）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と前処理（SSRF・XML 脆弱性対策あり）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロセンチメント評価
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- リサーチ用ユーティリティ（ファクター計算、Zスコア正規化、将来リターン、IC 計算）
- 監査ログ（signal → order_request → execution のトレーサビリティ）初期化ユーティリティ

設計上の特徴：
- ルックアヘッドバイアス防止（内部で date.today() を直接参照せず、target_date を明示）
- 冪等性を考慮した DB 書き込み（ON CONFLICT / DELETE → INSERT 等）
- ネットワーク / API 呼び出しに対するリトライ・バックオフ・レート制御
- セキュリティ対策（RSS の SSRF 防止、defusedxml の利用等）

---

## 機能一覧

主な機能（モジュール別）:

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - アプリ設定の取得（J-Quants トークン、OpenAI キー、Slack トークン等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - news_collector: RSS 収集、テキスト前処理、raw_news への保存
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit: 監査ログテーブル初期化（signal_events / order_requests / executions）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを生成して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 とマクロセンチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要な Python パッケージをインストール
   - 最低限の依存例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用や extras がある場合はプロジェクトに合わせて requirements を用意してください。
   - （パッケージ配布を想定している場合）プロジェクトルートで:
     ```
     pip install -e .
     ```

3. 環境変数の準備
   - 必須環境変数（後述）を .env に記載するか OS 環境変数で設定してください。
   - 本パッケージはルート（.git または pyproject.toml が存在するディレクトリ）を自動検出して `.env` と `.env.local` を読み込みます。自動ロードを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. データベースディレクトリの作成
   - デフォルト DuckDB パスは `data/kabusys.duckdb`（設定で変更可能）なので、`data/` ディレクトリを作成しておくと良いです。

---

## 環境変数（主なもの）

必須（Settings._require により取得されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携等で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視/モニタリング用 SQLite（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector の引数を渡さない場合に使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — set to "1" で自動 .env 読み込みを無効化

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

注意: `.env.local` が存在する場合は `.env` より優先して上書きされます。OS 環境変数はさらに優先されます。

---

## 基本的な使い方（コード例）

以下は代表的な利用シナリオの簡単なコード例です。各関数は target_date を明示的に受け取る設計になっており、バックテスト時のルックアヘッドを防止できます。

- DuckDB 接続の準備:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントを評価して ai_scores に書き込む:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", n_written)
```

- 市場レジームスコアを算出して market_regime に書き込む:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB を初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は DuckDB 接続を返す
```

- リサーチ関数の例（モメンタム計算）:
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# calc_momentum は [{"date":..., "code":..., "mom_1m":..., ...}, ...] を返す
```

注意点:
- OpenAI API 呼び出しはリトライとフェイルセーフを備えていますが、API キー・使用モデルの利用料が発生します。
- J-Quants API はレート制限と認証が必要です。get_id_token 等でトークンを取得して利用します。
- ETL / news scoring / regime scoring は target_date を明示すること（ルックアヘッド防止）。

---

## ディレクトリ構成（抜粋）

以下はソースツリー（主要ファイル）の抜粋です。実際のプロジェクトでは pyproject.toml / setup.cfg / tests 等が別途存在する可能性があります。

src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py                # ETLResult の再エクスポート
      calendar_management.py
      news_collector.py
      quality.py
      stats.py
      audit.py
      pipeline.py
      etl.py
      # （その他、jquants_client の内部ユーティリティ等）
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    monitoring/             # README 要求のモジュール一覧に含まれる可能性あり（実装ファイルは本ツリーに依存）
    strategy/               # 戦略レイヤ（本ツリーでは参照のみ）
    execution/              # 約定実行レイヤ（本ツリーでは参照のみ）

主な DB テーブル（コード参照）:
- raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / market_regime
- audit テーブル群: signal_events, order_requests, executions

---

## 運用上の注意・推奨

- ルックアヘッドバイアスを避けるため、運用・バックテスト双方で target_date を明示する習慣をつけてください。
- OpenAI 呼び出し (news_nlp, regime_detector) は API コストが発生するため、本番では必要に応じてキャッシュや頻度制限を検討してください。
- J-Quants の API レート制限（120 req/min）に合わせた実装済みですが、長時間のバッチ実行時に監視ログを出すことを推奨します。
- RSS フェッチは外部 HTTP に依存するため、SSRF 対策や受信サイズ制限が施されていますが、実運用ではソースの安定性を確認してください。

---

もし README に追加したい情報（例: CI/CD 手順、サンプル .env.example の追加、詳細な API 使用例、テストの実行方法など）がありましたら教えてください。必要に応じて追記・調整します。