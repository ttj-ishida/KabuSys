# KabuSys

日本株自動売買プラットフォームのライブラリ群。データ収集（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定のトレース）など、自動売買システムを構成する主要コンポーネントを提供します。

---

目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 環境変数（必須・任意）
- 使い方（簡易例）
- ディレクトリ構成（主要ファイル）
- 注意事項

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームのコアライブラリ群です。主な目的は以下：

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集と LLM による銘柄別センチメント算出
- 市場レジーム判定（ETF の MA とマクロニュースの合成）
- リサーチ用ファクター（モメンタム、バリュー、ボラティリティ等）の計算
- 発注・約定までの監査ログ（監査テーブル初期化ユーティリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針として、ルックアヘッドバイアスを避ける実装、DuckDB を用いたローカル DB 保存、外部 API への堅牢なリトライ／レート制御、安全性（SSRF 対策等）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証・ページネーション・保存関数）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - news_collector: RSS 収集・前処理（SSRF 対策、正規化）
  - audit: 監査ログテーブル初期化（order_requests, executions, signal_events 等）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp: 銘柄別ニュースセンチメント算出（OpenAI）
  - regime_detector: ETF とマクロニュースから日次市場レジーム判定
- research/
  - factor_research: momentum/value/volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（情報係数）など
- config.py: .env 読み込みと Settings（環境変数ベースの設定）
- data.audit.init_audit_db: 監査用 DuckDB の初期化ユーティリティ

---

## 必要条件

- Python 3.10 以上（型ヒントに `|` を使用）
- 必須パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

※実行する機能により追加パッケージや外部 API（J-Quants, OpenAI, kabuステーション など）のアカウント・認証情報が必要です。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存インストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （パッケージがセットアップ可能なら）pip install -e .

   ※プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

4. 環境変数設定
   - ルートに .env/.env.local を置くと自動で読み込まれます（config.py によりプロジェクトルートを探索して自動ロード）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

---

## 環境変数（設定項目）

config.Settings で読み込む主な環境変数：

必須
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（ETL に必須）
- KABU_API_PASSWORD : kabu ステーション接続用パスワード（執行周りで使用）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（通知機能使用時）
- SLACK_CHANNEL_ID : Slack 通知先チャネル ID

任意 / デフォルトあり
- KABU_API_BASE_URL : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH : 実行 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視しきい値
- KABUSYS_ENV : environment（development / paper_trading / live）デフォルト: development
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）デフォルト: INFO

.env のサンプル（README 用）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易例）

以下はライブラリの典型的な使い方例です。実行は仮想環境内で行ってください。

- DuckDB 接続を作って日次 ETL を実行する
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニュースセンチメント（ai.news_nlp）
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込み銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB）
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# これで signal_events/order_requests/executions テーブルが作成されます
```

- J-Quants から株価データを直接取得する（テスト等）
```
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,19))
print(len(records))
```

- 研究用ファクター計算
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026,3,20))
v = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要構成（抜粋、src/kabusys 以下）:

- src/kabusys/
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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - audit.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (監視関連モジュール: PID, CPU/メモリ/ディスク監視など)  ※詳細はコード参照
  - execution/ (注文実行まわりの実装)  ※詳細は実装次第

（上記に加えテストやドキュメント、CI 設定ファイルがプロジェクトルートに存在する場合があります）

---

## 注意事項 / 運用メモ

- 環境変数や API キーは厳重に管理してください。誤って公開しないでください。
- OpenAI 呼び出し（news_nlp, regime_detector）は API 使用料が発生します。バッチサイズや呼び出し頻度に注意してください。
- J-Quants API のレート制限（120 req/min）を尊重する実装になっていますが、運用時はさらに注意してください。
- DuckDB に対する executemany の挙動（バージョン差）や SQL の互換性に注意してください。コード中にも互換性対策のコメントがあります。
- 自動 .env 読み込みは config.py がプロジェクトルート（.git または pyproject.toml）を探して行います。テスト環境で自動読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 監査ログは削除しない前提の設計です（トレーサビリティ確保）。DB 設計やバックアップ方針を検討してください。

---

この README はコードベースから抽出した主要機能・使い方のサマリです。より詳細な API 仕様や運用手順、ETL の設計書（DataPlatform.md / StrategyModel.md 等）がプロジェクトに含まれている場合はそちらを参照してください。追加で「導入手順」や「具体的な運用例（cron/airflow での ETL スケジュール設定など）」を README に追加したい場合は、その要件を教えてください。