# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の量的投資・自動売買システム構築を支援するライブラリ群です。主な目的は次の通りです。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース取得と前処理、ニュース × 銘柄の紐付け、LLM によるセンチメントスコア生成（gpt-4o-mini を想定）
- マクロニュース + 指定ETF の移動平均乖離から市場レジーム（bull/neutral/bear）を判定
- 研究用ファクター計算 / 将来リターン計算 / IC 計算
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定をトレースする監査テーブルの初期化ユーティリティ
- 環境変数ベースの設定管理（.env 自動ロード機構あり）

設計上の留意点（抜粋）:
- ルックアヘッドバイアスを防ぐ実装（内部で datetime.today()/date.today() を参照しない関数が多い）
- API 呼び出しに対するリトライとフェイルセーフ（失敗時はゼロやスキップして継続することが多い）
- DuckDB を中心に SQL と純粋 Python で高速に処理

---

## 機能一覧（モジュール単位）

- kabusys.config
  - 環境変数読み込み（プロジェクトルートの `.env` / `.env.local` を自動読み込み）
  - 主要設定プロパティ（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）

- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・ページング・DuckDB 保存）
  - pipeline / etl: 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  - news_collector: RSS 取得、前処理、raw_news への保存（SSRF/サイズ上限/トラッキング除去等の対策あり）
  - calendar_management: 営業日判定・next/prev_trading_day 等のユーティリティとカレンダー更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: zscore 正規化などの統計ユーティリティ
  - audit: 発注/約定の監査テーブル定義と初期化ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM に投げ、ai_scores を書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込む

- kabusys.research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算 / IC / 統計サマリー 等

---

## セットアップ手順

1. Python 環境を用意
   - 推奨: Python 3.10+（コードは型ヒントに新しい構文を使用）
   - 仮想環境を作成して有効化することを推奨
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. リポジトリをクローン / パッケージをインストール
   - リポジトリルートに移動して: pip install -e .  
     （実際の setup/pyproject がある前提。なければ直接依存を入れる）

3. 必要な主要依存パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外がある場合は requirements.txt を用意して pip install -r requirements.txt）

   例:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を配置
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...  （AI 機能を使う場合）
     - KABU_API_PASSWORD=...  （kabuAPI を使う場合）
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意 / デフォルト:
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト development）
     - KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)
   - 自動 .env 読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB ファイルの親ディレクトリを準備
   - デフォルトでは data/kabusys.duckdb に保存されます。存在しない場合はコードが作成しますが、権限等に注意。

---

## 使い方（簡易例）

以下は Python REPL / スクリプト内での利用例です。各呼び出しは duckdb 接続オブジェクト（duckdb.connect(...)）を受け取ります。

- 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- 日次 ETL を実行する（pipeline.run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成する（ai.news_nlp.score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ai.regime_detector.score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
```

- カレンダー / 取引日ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- J-Quants から直接データを取得する（jquants_client）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

注意:
- OpenAI を使う関数（score_news, score_regime）は環境変数 OPENAI_API_KEY を参照します。api_key を引数で渡すことも可能です。
- 多くの API 呼び出しは失敗時にフォールバックやスキップを行います（例: LLM 呼び出し失敗時に 0.0 を返す等）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイルの概要です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュースの LLM スコアリング（ai_scores 書き込み）
    - regime_detector.py            # ETF + マクロで市場レジーム判定（market_regime 書き込み）
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（取得・保存）
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - etl.py                        # ETLResult の再エクスポート
    - news_collector.py             # RSS 収集・前処理
    - calendar_management.py        # 市場カレンダー管理・営業日ユーティリティ
    - quality.py                    # データ品質チェック
    - stats.py                      # zscore 等の統計ユーティリティ
    - audit.py                      # 監査ログテーブルの DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py            # momentum / value / volatility 等
    - feature_exploration.py        # 将来リターン, IC, 統計サマリー

（上記は完全な一覧ではありません。実際のリポジトリでファイルツリーを確認してください。）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for AI 機能): OpenAI API キー（score_news など）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト localhost）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）

設定はプロジェクトルートの `.env` / `.env.local` に置くことができます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 注意事項 / 実運用メモ

- DuckDB を利用しているためデータ量やメモリに注意してください（クエリは SQL で最適化されていますが、実運用では適切なインフラ設計が必要です）。
- OpenAI / J-Quants 呼び出しには API 利用料とレート制限が関係します。設定されたレート制限やリトライ挙動を理解した上で利用してください。
- ETL や AI 処理はルックアヘッドバイアスを避けるよう設計されていますが、バックテストや運用時にはデータの取得タイミングに注意してください。
- 監査ログ（audit）テーブルは削除しない前提で設計されています。バックアップ方針を検討してください。
- news_collector には SSRF・Gzip bomb 等への対策が組み込まれていますが、外部フィードの信頼性とセキュリティに留意してください。

---

## 貢献 / 開発

- コードは src/kabusys 以下に配置されています。ユニットテストや Lint を追加していくことを推奨します。
- テスト中に .env 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

---

README はここまでです。必要であれば、使用例のスクリプトテンプレート（systemd / cron での日次 ETL 実行や Slack 通知例）や requirements.txt の雛形を追記します。どの情報を追加しますか？