# KabuSys

日本株向けの自動売買・データパイプラインおよび研究用ユーティリティ群です。  
DuckDB をデータ層に利用し、J-Quants API からのデータ取得、ニュース収集・LLM によるニュースセンチメント、ファクター計算、品質チェック、監査ログ（order → execution トレーサビリティ）などを提供します。

---

## 特徴（概要）

- ETL パイプライン（株価・財務・市場カレンダー）の差分取得と保存（J-Quants）
- ニュース収集（RSS）と LLM（OpenAI）を使った銘柄別センチメント算出
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- ファクター計算（Momentum / Value / Volatility 等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログスキーマ（signal / order_request / executions）および初期化ユーティリティ
- 環境変数による設定管理（.env の自動読み込み、テストで無効化可能）

---

## 主な機能一覧

- data:
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（ページネーション・レート制御・リトライ含む）
  - market calendar 管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - news_collector: RSS 取得と raw_news への保存（SSRF 対策・サイズ制限）
  - quality: 各種データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - audit: 監査ログスキーマ定義と初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize（ファクター正規化ユーティリティ）
  - pipeline: ETLResult（ETL 実行結果のデータクラス）
- ai:
  - news_nlp.score_news: ニュースを LLM で処理して ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF ma200 乖離 + マクロニュース LLM 結果を合成して market_regime テーブルへ書き込み
- research:
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- 設定:
  - kabusys.config.settings: 環境変数を型で取得（必須キーは未設定時に ValueError 発生）

---

## セットアップ手順

1. Python（推奨: 3.10+）を用意

2. 依存ライブラリをインストール（例）
   - 必要最低限:
     - duckdb
     - openai
     - defusedxml
   - 開発/利用環境に応じて他ライブラリが必要な場合があります。

   例:
   pip install duckdb openai defusedxml

   （パッケージ配布時は requirements.txt / pyproject.toml を参照してください）

3. リポジトリをインストール（開発モード）
   - プロジェクトルートで:
     pip install -e .

4. 環境変数の設定
   - .env または環境変数で設定します。.env.example を参照してください（プロジェクトルートに .env / .env.local を置くと自動ロードされます）。
   - 自動ロードを無効化したい場合（テストなど）:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須の主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（data.jquants_client.get_id_token で使用）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注等に使用）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用する場合。各関数は引数でキー注入可）

   任意 / デフォルト:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: デフォルト data/kabusys.duckdb
   - SQLITE_PATH: デフォルト data/monitoring.db

5. データディレクトリの準備
   - デフォルトの DB パス（data/ ディレクトリ）を作成しておくと便利:
     mkdir -p data

---

## 使い方（簡単な例）

以下は Python スクリプト / REPL 例です。DuckDB 接続は duckdb.connect(...) を使用します。

- 日次 ETL を実行する（J-Quants から差分取得して保存・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（ai_scores）を生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)
```
api_key を指定しないと環境変数 OPENAI_API_KEY を参照します。

- 市場レジームをスコアリングして保存する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/kabusys_audit.duckdb")
# conn は DuckDB 接続。監査テーブルが作成された状態
```

- 設定値にアクセスする
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.is_live)
```

---

## 環境変数（主要）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- OpenAI:
  - OPENAI_API_KEY（ai.news_nlp / ai.regime_detector を実行する際に参照されます）

- 動作制御:
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

- DB パス:
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db

---

## 注意事項 / 設計上のポイント

- Look-ahead bias 防止:
  - モジュール内の関数は datetime.today() / date.today() を直接使わないよう設計されています（target_date を明示的に渡すことでバックテスト等でルックアヘッドを防止）。
- 冪等性:
  - J-Quants 保存関数は ON CONFLICT DO UPDATE（冪等）で DB へ保存します。
  - ニュース収集は URL 正規化＋ハッシュで記事 ID を決定し冪等保存を狙います。
  - 監査ログの order_request_id は冪等キーとして設計されています。
- フェイルセーフ:
  - LLM 呼び出しや外部 API はリトライ・フォールバックを実装し、個別処理失敗が全体を停止させない設計です（ただし外部依存がある処理は事前にキーやネットワークが必要）。
- セキュリティ:
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml を利用した XML パース保護等を実装しています。
- DuckDB の互換性:
  - 一部 executemany の挙動（空リスト不可など）や SQL の記述は DuckDB のバージョンによる挙動を考慮して記述されています。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュールの一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (その他ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__all__ として各種計算ユーティリティを再公開

（上記はリポジトリに含まれる主なモジュールの抜粋です。詳細はソースを参照してください）

---

## よくある操作例（補足）

- .env 自動ロード
  - プロジェクトルートに `.env` および `.env.local` を置くと、config モジュールが起動時に自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き）
  - テストで自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- OpenAI 呼び出し
  - news_nlp と regime_detector は gpt-4o-mini を想定した JSON Mode 呼び出しを行います。API レスポンスのパース失敗時はスコア 0.0 にフォールバックしたり、銘柄単位でスキップする設計です。

- J-Quants API
  - rate limit（120 req/min）に合わせた RateLimiter とリトライロジックを実装しています。
  - get_id_token は settings.jquants_refresh_token を使って ID トークンを取得します。

---

## 貢献 / 開発

- フォルダ構成・関数シグネチャはドメイン要件（DataPlatform.md / StrategyModel.md）に基づいて設計されています。
- 単体テスト・統合テストの追加、ドキュメント整備、運用監視（ログ/メトリクス）の強化を歓迎します。

---

必要に応じて README に例となる .env.example、requirements.txt、簡易 CLI スクリプト（etl_runner など）を追加できます。具体的に追記したい項目（例: 実際の .env の雛形、より詳しい API 使用例、CLI コマンド例）があれば教えてください。