# KabuSys

日本株向けのデータプラットフォーム兼自動売買・リサーチライブラリです。  
DuckDB をデータレイヤーに、J-Quants / JPYマーケットカレンダー / RSS / OpenAI を組み合わせて、ETL・データ品質チェック・ニュース NLP・市場レジーム判定・ファクター計算・監査ログなどの機能を提供します。

注意: この README はソースコード（src/kabusys/*）に基づいて作成しています。

## 特徴（機能一覧）

- 環境変数と .env の自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得・ページネーション対応
  - 財務データ取得
  - JPX マーケットカレンダー取得
  - 保存関数（DuckDB へ冪等保存）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL 実行結果を ETLResult で返却
- ニュース収集（RSS）と前処理（SSRF 対策・URL 正規化）
- ニュース NLP（OpenAI）での銘柄別センチメントスコアリング（ai_scores への書き込み）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース LLM を合成）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマ初期化とインデックス
  - init_audit_schema / init_audit_db 提供
- 汎用統計ユーティリティ（zscore_normalize 等）

## 動作環境・前提

- Python 3.10 以上（型ヒントで | 演算子を使用）
- DuckDB
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全化）
- ネットワークアクセス（J-Quants API、RSS フィード、OpenAI）

推奨パッケージ（例）
- duckdb
- openai
- defusedxml

（実際のプロジェクトには requirements.txt や pyproject.toml を用意してください）

## セットアップ手順

1. Python 環境を用意（3.10+ 推奨）
2. リポジトリをクローン / ソースを配置
3. 開発用に依存をインストール
   - 例: pip install duckdb openai defusedxml
   - またはプロジェクトの pyproject.toml / requirements.txt を使用
4. パッケージのインストール（編集可能インストール）
   - pip install -e .

### 環境変数

プロジェクトは .env / .env.local をプロジェクトルートから自動読み込みします（優先順位: OS 環境 > .env.local > .env）。自動ロードを無効にするには環境変数を設定します:

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な設定項目（.env に設定する例）

- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO

config.Settings を通じてアプリ内から参照できます:
```py
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

## 使い方（代表的な例）

以下は Python REPL あるいはスクリプトでの利用例です。事前に必要な環境変数（OpenAI / J-Quants 等）と DuckDB データベースファイルのパスを設定してください。

- DuckDB 接続例:
```py
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルなければ作成される
```

- 日次 ETL 実行:
```py
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 株価のみ差分 ETL:
```py
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

- ニュースのセンチメント付与（OpenAI APIキーは環境変数 OPENAI_API_KEY または api_key 引数で指定）:
```py
from datetime import date
from kabusys.ai.news_nlp import score_news
count = score_news(conn, target_date=date(2026,3,20))
print(f"scored {count} codes")
```

- 市場レジーム判定:
```py
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログテーブル初期化:
```py
from kabusys.data.audit import init_audit_db, init_audit_schema
# 監査専用 DB を作る:
audit_conn = init_audit_db("data/audit.duckdb")
# 既存 conn にスキーマを追加:
init_audit_schema(conn, transactional=True)
```

- ファクター計算（研究用途）:
```py
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date
mom = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
```

- Zスコア正規化:
```py
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "ma200_dev"])
```

## 注意点・設計上の考慮

- ルックアヘッドバイアス対策
  - モジュールの多くは内部で datetime.today()/date.today() を直接参照しません。引数として target_date を受け取り、その日付より前のデータのみを参照するように設計されています。
- 冪等性
  - J-Quants からの保存処理（save_*）は ON CONFLICT DO UPDATE を用いて冪等に保存します。
- フェイルセーフ設計
  - OpenAI や API 呼び出しの失敗は多くの場所で安全にフォールバック（0.0 スコアやスキップ）するようになっています。ログ出力は残しますが、全体処理が止まらないように配慮されています。
- セキュリティ
  - ニュース収集では SSRF 対策（リダイレクト検査・プライベートホストブロック等）、defusedxml による XML パース保護、受信サイズ制限などが実装されています。
- 自動環境変数ロード
  - config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みします。テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 主要モジュール・ディレクトリ構成

リポジトリ内の主なファイル配置（src/kabusys 配下の抜粋）:

- kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP（銘柄別スコアリング）
    - regime_detector.py     # 市場レジーム判定（MA200 + マクロLLM）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - pipeline.py            # ETL パイプライン（run_daily_etl など）
    - etl.py                 # ETL 結果型の公開
    - news_collector.py      # RSS 収集・前処理
    - calendar_management.py # 市場カレンダー管理・営業日ロジック
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - quality.py             # 品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py               # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     # Momentum / Volatility / Value 等
    - feature_exploration.py # 将来リターン / IC / サマリー等

（上記は主要なファイルのみを抜粋。実際のリポジトリには更にモジュールが含まれます。）

## ロギング・実行環境

- ログレベルは環境変数 LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）で制御されます（settings.log_level）。
- 環境（development / paper_trading / live）は KABUSYS_ENV で制御されます（settings.env）。
- Slack 連携用に SLACK_BOT_TOKEN / SLACK_CHANNEL_ID を設定して通知機能を実装できます（本実装の外側で通知ロジックを組み合わせてください）。

## 開発・テストに関するヒント

- テスト時は config の自動 .env 読み込みを無効化するか、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境を固定してください。
- OpenAI の呼び出しを行う関数は内部で _call_openai_api をラップしているため、テスト時は該当関数をモックして外部コールを回避できます（ソース内にテスト用差し替えコメントあり）。
- DuckDB を使うため、インメモリでの単体テストは duckdb.connect(":memory:") で可能です。

---

さらに細かい使用例や schema 定義、CI 設定、実運用の監視／バックアップ、Slack 通知フロー等はプロジェクトの運用ドキュメントに追記してください。必要であれば README の追記（例: .env.example、requirements.txt、実行スクリプト例）を作成します。どの項目を詳細化したいか教えてください。