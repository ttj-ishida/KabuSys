# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由での株価・財務・カレンダー取得）、ニュース収集・NLP（LLM を用いたセンチメント）、ファクター計算・リサーチ、監査ログ（発注・約定のトレーサビリティ）、および運用ユーティリティを提供します。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「堅牢な API リトライ/フェイルセーフ」「DuckDB によるローカル DB 管理」です。

---

## 機能一覧

- データ ETL（J-Quants API 経由）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの差分取得・保存
  - 差分/バックフィル、ページネーション対応、レートリミット・再試行実装
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF と XML 攻撃対策（URL 検証・defusedxml 等）
- ニュース NLP（OpenAI）
  - 銘柄ごとにニュースを統合して LLM に送信し ai_scores にスコアを保存（score_news）
  - タイムウィンドウやトリム、バッチ・リトライ、レスポンス検証を実装
- 市場レジーム判定（OpenAI + MA200）
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して日次で 'bull'/'neutral'/'bear' を算出（score_regime）
- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリュー等ファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損・重複・将来日付・スパイク検出など（QualityIssue オブジェクトで集約）
- 監査ログ（audit）
  - signal → order_request → execution の階層的トレースを行うテーブルの初期化・DB 作成ユーティリティ（init_audit_db）
- 環境設定ユーティリティ
  - .env の自動ロード（プロジェクトルート検知）と Settings ラッパー（settings オブジェクト）

---

## 必要条件 / 依存パッケージ（代表例）

実行に最低限必要になる主要パッケージ（実装から推測）:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他: 標準ライブラリ（urllib, datetime, json, logging 等）

環境によっては追加で sqlite3, requests 等が必要になる場合があります。プロジェクト配布時は requirements.txt や pyproject.toml を参照してください。

---

## 環境変数（主なもの）

config.Settings で参照される主要環境変数：

必須（ETL / J-Quants 用）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）

必須（kabu ステーション連携が必要な場合）
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- KABU_API_BASE_URL: （任意）kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

OpenAI（ニュース NLP / レジーム判定）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime が参照）

任意（通知等）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

データベース / ファイルパス（デフォルトあり）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

運用モード / ログ
- KABUSYS_ENV: development | paper_trading | live（default: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

.env 自動読み込み:
- package はプロジェクトルート（.git または pyproject.toml 存在箇所）を検出して .env → .env.local を自動読み込みします。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順（ローカル開発向けの例）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（プロジェクトに requirements.txt があればそれを使用）
   - pip install duckdb openai defusedxml

   あるいは（パッケージ配布がある場合）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env を作成するか環境変数を設定します。
   - 最低でも JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY（NLP を使う場合）を設定してください。

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB データディレクトリ作成
   - 必要に応じて data/ ディレクトリ等を作成してください（Settings.duckdb_path に依存）。

---

## 使い方（クイックスタート）

以下はライブラリ API を直接呼ぶ簡単な例です。実運用ではログ設定や例外ハンドリング、cron/ジョブ管理を組み合わせて下さい。

共通: DuckDB 接続の例
```
from kabusys.config import settings
import duckdb

db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)  # ":memory:" を指定するとメモリ DB
```

1) 日次 ETL を実行する（run_daily_etl）
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアを作成（score_news）
- OpenAI API キーは OPENAI_API_KEY 環境変数、または api_key 引数で指定可能
```
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20))  # returns 書込銘柄数
```

3) 市場レジーム判定（score_regime）
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB を初期化（監査用 DuckDB を作る）
```
from kabusys.data.audit import init_audit_db
from pathlib import Path

aud_conn = init_audit_db(Path("data/audit.duckdb"))
# これで signal_events / order_requests / executions テーブルが作成されます
```

5) RSS フィードを取得して raw_news に保存するワークフローは news_collector.fetch_rss を利用し、取得した記事を jquants_client 相当の保存関数経由で DB に格納する想定です（プロジェクトの運用スクリプトに組み込んでください）。

---

## 代表的なモジュール & API（抜粋）

- kabusys.config
  - settings: 環境変数ラッパー（settings.jquants_refresh_token, settings.duckdb_path, settings.env など）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...): ETL のエントリポイント
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize (kabusys.data.stats)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

（主要ファイルのみ抜粋: src/kabusys 以下）
- kabusys/
  - __init__.py
  - config.py                         -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      -- ニュース NLP / スコアリング
    - regime_detector.py               -- レジーム判定ロジック（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py                -- J-Quants API クライアント & 保存ロジック
    - pipeline.py                      -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py           -- 市場カレンダー・営業日ユーティリティ
    - news_collector.py                -- RSS 収集 / 前処理
    - stats.py                         -- 汎用統計（zscore_normalize）
    - quality.py                       -- データ品質チェック
    - audit.py                         -- 監査ログテーブル初期化 / DB 作成
    - etl.py                           -- ETLResult の公開再エクスポート
  - research/
    - __init__.py
    - factor_research.py               -- ファクター算出（momentum/value/volatility）
    - feature_exploration.py           -- 将来リターン, IC, summary 等

---

## 運用・開発上の注意

- ルックアヘッドバイアス防止: 多くの関数は内部で date.today() を参照しないよう設計されています。バックテスト用途で使用する場合は target_date を明示的に渡してください。
- 環境変数の自動ロード: プロジェクトルート判定に .git または pyproject.toml を使用します。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト実行時に便利です）。
- OpenAI 呼び出し: レスポンスの整合性チェックやリトライを行っていますが、API レスポンスの不整合時はフォールバック値（0.0 等）を使用するため、ログを必ず確認してください。
- DuckDB バージョン互換: 一部の executemany 空リスト扱い等、DuckDB バージョン差分で挙動が変わる箇所があります。推奨バージョンをプロジェクト要件に合わせてください。

---

README はここまでです。より詳しい使用例や運用手順（cron/システムd ジョブ構成、LINE 通知連携、kabu ステーション連携等）が必要であれば、どの機能に関するドキュメントを優先して作成するか教えてください。