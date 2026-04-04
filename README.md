# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群です。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（約定トレーサビリティ）など、システム運用に必要なコンポーネントを提供します。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 環境変数（.env）
- 基本的な使い方（コード例）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株の自動売買やリサーチを支援するライブラリ群です。  
主に以下の役割を担います。

- J-Quants API からのデータ取得（株価・財務・カレンダー等）
- DuckDB を用いたデータ保存・ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- RSS を使ったニュース収集と前処理（SSRF対策／トラッキング除去）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント分析と市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 監査ログテーブル（signal → order → execution のトレーサビリティ）

設計上、バックテストでのルックアヘッドバイアスを避けるために
「現在日時を勝手に参照しない」実装方針が各モジュールに適用されています（関数は target_date を受け取る等）。

---

## 主な機能一覧
- data/
  - jquants_client: J-Quants API 呼び出し、ページネーション、保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL 実行 (run_daily_etl) と個別 ETL（run_prices_etl 等）
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策、URL 正規化）
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
  - audit: 監査ログスキーマ初期化（signal_events, order_requests, executions）
  - stats: Zスコア正規化ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: 将来リターン計算、IC（情報係数）、統計サマリー等
- 設定:
  - config.Settings: .env または環境変数から各種設定を読み込み（自動 .env ロードを実装）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子等を使用）
- Git リポジトリルートで操作することを想定（config の自動 .env ロードが .git か pyproject.toml を探索します）

1. リポジトリをクローン:
   git clone <repo-url>
   cd <repo>

2. 仮想環境の作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール（例）:
   pip install duckdb openai defusedxml

   ※プロジェクトで requirements.txt / pyproject.toml があればそちらを利用してください。

4. 必要なディレクトリの作成（デフォルトの DB 配置先等）:
   mkdir -p data

5. 環境変数の用意:
   プロジェクトルートに `.env` を作成するか、直接環境変数を設定します。主なキーは下記参照。

注意:
- 自動で .env を読み込む仕組みがあります。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主なもの）
以下は Settings クラスで参照されるキーです。`.env.example` を作成して管理してください。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（get_id_token で使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必要な機能がある場合）

任意 / 推奨:
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（空でも可）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視設定
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: environment ('development' | 'paper_trading' | 'live') デフォルト development
- LOG_LEVEL: 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'（デフォルト INFO）

注意: Settings は未設定の必須キーに対して ValueError を発生させます。

---

## 基本的な使い方（コード例）

以下は代表的な利用例です。いずれも DuckDB の接続を渡して操作します。

1) DuckDB に接続して ETL を実行（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# 日次 ETL を実行（target_date を省略すると今日を使用）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントをスコアリングして ai_scores に保存
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込んだ銘柄数:", n_written)
```

3) 市場レジーム判定（regime）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
# list[dict] を返す
```

5) 監査ログテーブルの初期化（監査専用DBを作る場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions が作成されます
```

6) カレンダー補助関数
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
is_trading = is_trading_day(conn, date(2026, 3, 20))
next_td = next_trading_day(conn, date(2026, 3, 20))
```

---

## 注意点・運用上のヒント
- OpenAI や J-Quants への API 呼び出しはレート制限・エラー処理・リトライを内部で実装していますが、運用環境ではキー管理やコスト管理に注意してください。
- ニュース収集は外部 RSS を取得するため SSRF 対策等を実装しています。RSS ソース追加は慎重に行ってください。
- ETL は部分失敗を考慮して実装されています（各ステップで例外を集約し、可能な処理は継続）。運用時には ETLResult の errors / quality_issues を監視してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、該当コードは空チェックを行っています。DuckDB のバージョンに留意してください。
- .env は Git 管理に含めないでください。`.env.example` を作成して必要なキーを示す運用を推奨します。

---

## ディレクトリ構成（主要ファイル）
（プロジェクトの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュースセンチメント計算（ai_scores）
    - regime_detector.py            - 市場レジーム判定（market_regime）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント・保存ロジック
    - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
    - etl.py                        - ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py             - RSS 収集・前処理
    - calendar_management.py        - 市場カレンダー管理 / 営業日判定
    - quality.py                    - データ品質チェック
    - stats.py                      - 統計ユーティリティ（zscore_normalize 等）
    - audit.py                      - 監査ログテーブルの DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py            - モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py        - 将来リターン / IC / 統計サマリー

---

## ライセンス・貢献
- ライセンス情報やコントリビューション手順はリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要に応じて README に追加したい具体的な実行コマンド、CI 設定、docker-compose 例などがあれば教えてください。README をそれらに合わせて拡張します。