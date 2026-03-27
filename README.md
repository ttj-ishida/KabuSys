# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、リサーチ（ファクター計算）、監査ログ（発注・約定トレーサビリティ）などを含みます。

## プロジェクト概要
KabuSys は以下の目的を持つモジュール群を提供します。

- J-Quants API からの差分ETL（株価、財務、カレンダー）
- RSS によるニュース収集と記事前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（銘柄・マクロ）のスコアリング
- ファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）
- 市場カレンダー管理（JPX ベース）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- 各種データ品質チェック

設計上の共通方針として、ルックアヘッドバイアスの排除（日時の暗黙参照回避）、冪等性（DB 保存の ON CONFLICT 処理）、外部 API のリトライ / フェイルセーフ処理を重視しています。

## 主な機能一覧
- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）
- ニュース
  - RSS 取得・前処理（kabusys.data.news_collector）
  - 銘柄別ニュースセンチメント score_news（kabusys.ai.news_nlp）
  - マクロセンチメント + MA の合成による市場レジーム判定 score_regime（kabusys.ai.regime_detector）
- リサーチ
  - ファクター計算: calc_momentum, calc_volatility, calc_value（kabusys.research.factor_research）
  - 将来リターン計算 / IC / 統計サマリー（kabusys.research.feature_exploration）
  - Zスコア正規化ユーティリティ（kabusys.data.stats）
- データ品質
  - 欠損・スパイク・重複・日付不整合チェック（kabusys.data.quality）
- カレンダー
  - 営業日判定と探索ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
- 監査ログ
  - 監査スキーマ作成 / 監査 DB 初期化（kabusys.data.audit.init_audit_schema / init_audit_db）

## セットアップ手順（開発環境向け）
以下は一般的な手順例です。プロジェクトに同梱の requirements.txt / pyproject.toml があればそちらを優先してください。

1. リポジトリをクローン
   git clone <repo-url>
2. Python 環境を用意（推奨: 3.10+）
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml
   # 実プロジェクトでは pyproject.toml / requirements.txt の指示に従ってください
4. パッケージを開発モードでインストール（任意）
   pip install -e .

### 環境変数 / .env
kabusys.config.Settings が環境変数から設定を読み込みます。ルートに `.env` / `.env.local` がある場合、自動で読み込まれます（CWD 依存ではなくパッケージファイル位置からプロジェクトルートを探索）。

主要な必須設定:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 投稿先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime などで使用）

オプション（デフォルトは括弧内）:
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) (default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 `.env` 読み込みを無効化できます（テスト時に便利）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していない場合、.env.local が .env を上書きする優先度で読み込まれます。

データベースパス（デフォルト）:
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db

## 使い方（例）
以下は代表的な利用例です。DuckDB 接続は duckdb.connect() を使用します。

- 日次 ETL を実行する（J-Quants から差分取得して保存・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に保存する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム（マクロ + ETF MA）をスコアリングして保存する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用のファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
recs = calc_momentum(conn, target_date=date(2026, 3, 20))
# recs は各銘柄の辞書リスト
```

- 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.db")
# 初期化後、conn を使って監査テーブルへ書き込み可能
```

- 設定取得の例
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数でキー注入可能（テスト容易化）か、環境変数 OPENAI_API_KEY を参照します。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、モジュール側でガード済みです。
- 外部 API 呼び出しはリトライやフォールバックが多く実装されています。API 失敗時は例外を上位へ伝播させず「フェイルセーフ」で継続する設計箇所が多くあります（ただし致命的な問題はロギングやエラーリストに記録されます）。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュール一覧と役割の概略です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py: 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py: ETF MA + マクロセンチメント合成による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（fetch / save / 認証・レート制御）
    - pipeline.py: ETL パイプライン（run_daily_etl 等、ETLResult 定義）
    - news_collector.py: RSS 収集・前処理
    - calendar_management.py: 市場カレンダー / 営業日判定 / calendar_update_job
    - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py: zscore_normalize 等の統計ユーティリティ
    - audit.py: 監査ログスキーマ / init_audit_db
    - etl.py: ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py: Momentum / Volatility / Value の計算
    - feature_exploration.py: 将来リターン計算・IC・統計サマリー
  - ai, research, data 以外の補助モジュールも多数

（上記はコードベースから抽出した主要モジュールです。詳細は各ファイル内の docstring を参照してください）

## ロギング・環境
- log レベルは環境変数 LOG_LEVEL で制御します（デフォルト INFO）。
- KABUSYS_ENV により is_live / is_paper / is_dev の判定が可能です。
- .env 自動読込を無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで意図的に環境を切り替える場合に有用）。

## テスト・モック
- OpenAI 呼び出しは内部でラップしてあるため、ユニットテスト時は各モジュールの _call_openai_api を patch して差し替える想定です（score_news / regime_detector 内でその旨の注記あり）。
- news_collector のネットワーク部分は _urlopen をモック可能です。

---

以上が README の概要です。必要であれば以下を追加で生成します：
- .env.example のテンプレート
- CI / デプロイ手順（systemd / cron / Airflow などでの定期実行例）
- 詳細な API リファレンス（各関数の引数・戻り値一覧）