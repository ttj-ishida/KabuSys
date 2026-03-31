# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤ライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ（ファクター計算）、監査ログ（約定トレース）など、自動売買システムに必要な基盤機能を含みます。

---

## 概要

KabuSys は以下の目的で設計されています。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存（ETL）
- RSS によるニュース収集と前処理、ニュースと銘柄の紐付け
- OpenAI を用いたニュースセンチメント解析（銘柄別 / マクロ）と市場レジーム判定
- 研究用モジュール（ファクター計算、将来リターン、IC、統計サマリー）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- 環境・設定管理、.env 自動読み込み（プロジェクトルート検出）

設計上の方針として、バックテスト時のルックアヘッドバイアス回避、冪等性、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル対応）
  - データ保存（DuckDB への冪等 INSERT / ON CONFLICT DO UPDATE）

- ニュース収集・NLP
  - RSS フィード取得（SSRF対策、gzip上限、トラッキングパラメータ除去）
  - preprocess_text（URL除去・空白正規化）
  - OpenAI を利用した銘柄別ニュースセンチメント score_news
  - マクロニュース + ETF MA による市場レジーム判定 score_regime

- 研究（Research）
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索・評価）
  - zscore_normalize（クロスセクション正規化）

- データ品質（quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（ETL 後の集約チェック）

- カレンダー管理（market_calendar）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（J-Quants からの夜間バッチ更新）

- 監査ログ（audit）
  - 監査テーブル DDL とインデックス、init_audit_schema / init_audit_db
  - signal_events, order_requests, executions 等の管理

- 設定管理（config）
  - 環境変数 / .env 自動読み込み（プロジェクトルートの .git または pyproject.toml を基準）
  - settings オブジェクト経由で各種設定取得

---

## 必要な環境変数

主に以下を設定してください（.env に記載して運用するのが便利です）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL

自動 .env ロードの振る舞い:
- 優先順位: OS 環境 > .env.local > .env
- プロジェクトルートを自動検出し .env を読み込みます
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

---

## セットアップ手順（ローカル開発向け）

1. Python インストール（推奨: 3.10+）
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（プロジェクトに requirements.txt が無い場合の例）
   - pip install duckdb openai defusedxml
   - 追加で必要なパッケージがあれば適宜インストールしてください（例: slack-sdk など）
4. ソースを開発モードでインストール（任意）
   - pip install -e .
5. .env の用意
   - リポジトリルートに .env を作成し、上記の環境変数を設定してください
   - サンプル: .env.example を参照して作成してください

注: OpenAI を利用する機能を実行する場合は OPENAI_API_KEY が必要です。関数呼び出し時に api_key 引数で直接渡すこともできます。

---

## 基本的な使い方（例）

以下は代表的な利用例です。実行前に DuckDB 接続先や環境変数を適切に設定してください。

- DuckDB 接続を作って ETL を実行する（run_daily_etl の例）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成する（score_news）:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジームを判定して書き込む（score_regime）:

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査ログ操作が可能
```

- リサーチ用ファクターを計算する:

```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect('data/kabusys.duckdb')
mom = calc_momentum(conn, date(2026, 3, 20))
# mom は各銘柄ごとの辞書リスト
```

注意:
- OpenAI 呼び出しは API キーが必要です（api_key 引数か環境変数 OPENAI_API_KEY）。
- ETL は J-Quants の認証トークン（JQUANTS_REFRESH_TOKEN）を用いて動作します。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         -- 銘柄別ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py  -- マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py         -- ETL パイプライン（run_daily_etl など）
    - etl.py              -- ETLResult の再エクスポート
    - jquants_client.py   -- J-Quants API クライアント + 保存ロジック
    - news_collector.py   -- RSS ニュース取得・前処理・保存ロジック
    - calendar_management.py -- マーケットカレンダー管理（営業日判定など）
    - quality.py          -- データ品質チェック
    - stats.py            -- zscore_normalize 等の統計ユーティリティ
    - audit.py            -- 監査テーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py  -- Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py -- 将来リターン・IC・統計サマリー
  - ai/ (上記)
  - research/ (上記)
  - その他: monitoring, execution, strategy 等（パッケージ公開済み）

---

## 運用上の注意・設計上のポイント

- ルックアヘッドバイアス対策:
  - 多くのモジュールが date の比較を「target_date 未満 / 以下」等で設計し、内部で datetime.today() を直接参照しないようになっています。バックテストでの使用時は注意してください。

- 冪等性:
  - データ保存関数は ON CONFLICT DO UPDATE を用いて冪等性を確保しています。ETL の再実行による上書きを前提に設計されています。

- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）の失敗時は、全体が停止しないようにフォールバックやログ出力で処理を継続する設計です。ただし重要な環境変数が未設定の場合は明示的に例外を投げます。

- セキュリティ対策:
  - news_collector では SSRF 対策、gzip/サイズ上限、defusedxml を利用して XML の安全性を確保しています。
  - jquants_client はレートリミッタと再試行ロジックを備えています。

---

## 贡献・拡張

- 新しいニュースソースの追加: data/news_collector.py の DEFAULT_RSS_SOURCES を拡張
- 新しいファクターや指標の追加: research/*.py に関数を追加して既存の研究パイプラインから利用
- 実運用（ライブ発注）を行う場合は、KABUSYS_ENV を適切に設定（paper_trading / live）し、発注周り（execution, strategy, risk管理）を十分にテストしてください。

---

もし README に含めたい追加項目（API の詳細な使用例、CLI コマンド、CI 設定、requirements.txt など）があれば教えてください。README を用途（開発者向け / 運用向け / API 参照向け）に合わせて拡張できます。