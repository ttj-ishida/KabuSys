# KabuSys

日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
J-Quants / RSS / OpenAI を組み合わせてデータの ETL、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログや品質チェックを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発のための内部ライブラリ群です。主に以下を担います。

- J-Quants API からの株価・財務・カレンダーデータの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理
- OpenAI を用いたニュースセンチメント解析（銘柄単位）およびマクロセンチメントの評価
- 市場レジーム（bull / neutral / bear）判定
- 研究用のファクター計算・特徴量解析ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → executions）のスキーマ初期化と管理
- 設定管理と自動的な .env の読み込み

設計上の特徴として、ルックアヘッドバイアスを避ける実装（target_date を明示する設計）、DuckDB を中心とした SQL＋純標準ライブラリ実装、外部 API 呼び出しに対するリトライ/バックオフ/フェイルセーフなどを備えています。

---

## 主な機能一覧

- データ取得・保存（J-Quants クライアント）
  - fetch_daily_quotes / save_daily_quotes（株価日次）
  - fetch_financial_statements / save_financial_statements（財務）
  - fetch_market_calendar / save_market_calendar（JPX カレンダー）
- ETL パイプライン
  - run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェックの一括処理）
  - run_prices_etl, run_financials_etl, run_calendar_etl（個別ジョブ）
- ニュース収集・前処理
  - fetch_rss（RSS 取得、SSRF 対策、前処理）
  - preprocess_text（URL 除去、空白正規化）
- ニュース NLP（OpenAI）
  - score_news（銘柄ごとのニュースセンチメントを ai_scores テーブルに書き込み）
  - レスポンス検証、チャンク送信、リトライ実装
- マーケットレジーム判定（AI + テクニカル）
  - score_regime（ETF 1321 の MA200 乖離 + マクロニュースセンチメントによる判定）
- 研究用ユーティリティ
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量解析）
  - zscore_normalize（標準化）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ（監査スキーマ初期化）
  - init_audit_schema / init_audit_db（DuckDB に監査用テーブル・インデックス作成）
- 設定管理
  - kabusys.config.settings（環境変数から設定を取得、.env 自動ロード機能）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法（A | B）を利用しているため）
- DuckDB を利用します（Python パッケージ duckdb）
- OpenAI（openai パッケージ）を利用する機能が一部あるため、OpenAI API キーが必要

1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt がある場合はそちらを使用してください。

3. 環境変数を設定（.env をプロジェクトルートに配置すると自動読み込みされます）
   - 必須（少なくとも OpenAI / J-Quants / Slack を使う場合）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（score_news, score_regime などで使用）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必要な場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合
   - 任意/デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) - デフォルト: INFO
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
     - PID_FILE_PATH: デフォルト data/execution.pid
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値

   自動 .env 読み込み:
   - プロジェクトルートにある .env および .env.local を自動で読み込みます（OS 環境変数が優先されます）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. データディレクトリを作成（DuckDB ファイル保存先など）
   - mkdir -p data

---

## 使い方（主要なユースケース）

以下はライブラリの代表的な使用例です。実運用ではエラー・ログ回収・例外処理を適宜追加してください。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を算出して ai_scores テーブルへ書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- 市場レジームを判定して market_regime テーブルへ書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査データベースを初期化する（監査用 DuckDB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルへ書き込む、またはアプリ起動時にこのDBへ接続
```

- ファクター計算や研究ユーティリティの使用
```python
from kabusys.research import calc_momentum, calc_value, zscore_normalize
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
values = calc_value(conn, date(2026,3,20))
normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

- 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live, settings.log_level)
```

---

## よく使う API / モジュール一覧（短い説明）

- kabusys.config
  - settings: 環境変数ベースの設定オブジェクト（自動 .env ロード含む）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（J-Quants 認証）

- kabusys.data.pipeline
  - run_daily_etl（メイン ETL エントリポイント）
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.news_collector
  - fetch_rss / preprocess_text（RSS 取得・前処理）

- kabusys.ai.news_nlp
  - score_news（銘柄別ニューススコアリング）

- kabusys.ai.regime_detector
  - score_regime（マクロ + MA200 で市場レジームを判定）

- kabusys.research
  - calc_momentum, calc_volatility, calc_value（ファクター群）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量解析）

- kabusys.data.quality
  - run_all_checks（品質チェック一括実行）

- kabusys.data.audit
  - init_audit_schema / init_audit_db（監査スキーマ初期化）

---

## ディレクトリ構成

（リポジトリ内の主要ファイル・ディレクトリを抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env の読み込み・設定
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py  — マーケットレジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得 / 保存 / 認証）
    - pipeline.py         — ETL パイプライン（run_daily_etl 他）
    - etl.py              — ETL の公開型（ETLResult）
    - news_collector.py   — RSS 収集 / 前処理
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - quality.py          — データ品質チェック
    - stats.py            — 共通統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化 / DB 作成
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility 計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - monitoring/ (実装は省略されているファイルもあり得ます)
  - strategy/ (戦略・発注ロジック想定)
  - execution/ (発注・ブローカー連携想定)

---

## 注意事項 / 運用上のポイント

- 型と API 呼び出し
  - OpenAI の呼び出しや J-Quants API 呼び出しはネットワークエラー・レート制限に備えたリトライを内部で行いますが、APIキーやトークンが正しく設定されていることを確認してください。

- ルックアヘッドバイアス対策
  - 多くの関数は target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しないように設計されています。バックテスト時は過去の状態のみを使うよう注意してください。

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。テスト環境などで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

- DuckDB の executemany と空リスト
  - DuckDB 0.10 系では executemany に空リストを渡せない箇所があるため、ライブラリ内で空チェックを行っています。custom な DB バージョンで問題がある場合はご注意ください。

---

## 開発・貢献

バグ報告や機能改善案は Issue を立ててください。テスト・CI の一環として、API 呼び出し部分はモック可能な設計になっています（ユニットテストでモックして外部との依存を切ることが可能です）。

---

README の内容について補足や特定機能の詳しい使い方（例: ETL の運用スケジュール、Slack 通知設定、kabu ステーション連携など）を追加したい場合は、目的に応じたサンプルコード・運用手順を追記します。必要な項目を教えてください。