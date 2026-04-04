# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログスキーマなど、取引システム／研究用途に必要となる主要機能を提供します。

---

## 主要コンセプト（概要）
- DuckDB を中心にローカルにデータを蓄積し、ETL で J-Quants API から差分取得・保存します。
- ニュースは RSS から収集し raw_news に保存、OpenAI を用いた銘柄別センチメント評価（ai_scores）を行います。
- ETF（1321）の 200 日移動平均やマクロニュースセンチメントを合成して市場レジーム（bull / neutral / bear）を判定します。
- 監査ログ（signal / order_request / executions）用の冪等なスキーマを提供し、シグナルから約定までのトレーサビリティを担保します。
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー）を持ち、バックテストや因子解析に利用できます。

---

## 機能一覧
- 環境設定の自動読み込み（.env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants API クライアント（取得、ページネーション、トークン自動リフレッシュ、レート制御、保存）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- マーケットカレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
- ニュース収集（RSS の安全な取得、SSRF 対策、前処理、raw_news への保存ロジック）
- ニュースNLP（OpenAI を用いた銘柄別センチメント、バッチ・リトライ・レスポンス検証）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- 研究モジュール（モメンタム／ボラティリティ／バリュー計算、forward returns、IC、統計）
- 監査ログスキーマ（init_audit_schema / init_audit_db）
- 汎用統計ユーティリティ（Z-score 正規化 等）

---

## 必要な環境変数
主に以下を使用します（用途別に分けています）。プロジェクトルートの `.env` / `.env.local` に設定すると自動読み込みされます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須（機能を使う場合に必要）
- JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>  (jquants_client.get_id_token で使用)
- OPENAI_API_KEY = <OpenAI API キー>  (news_nlp, regime_detector で使用)

その他（必要に応じて）
- KABU_API_PASSWORD = <kabuステーション API のパスワード>
- KABU_API_BASE_URL = http://localhost:18080/kabusapi  (デフォルト)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用)
- DUCKDB_PATH = data/kabusys.duckdb (デフォルト)
- SQLITE_PATH = data/monitoring.db (デフォルト)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV = development | paper_trading | live (デフォルト development)
- LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

例（.env）
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO

---

## セットアップ手順（開発環境）
1. Python 3.10+ を用意してください。
2. 仮想環境を作成・有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）:
   - pip install duckdb openai defusedxml
   - 追加でテスト・実行に必要なパッケージがあれば適宜インストールしてください。
   - （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用）

4. プロジェクトルートに `.env`（および必要なら `.env.local`）を配置して環境変数を設定します。
   - 自動読み込みが働くと、プロジェクトルート（.git または pyproject.toml を基準）から `.env` が読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要な API と例）

※ どの API も DuckDB 接続を受け取ることが多いです。まず接続を用意します。

例: DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は .env の DUCKDB_PATH を反映
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメント（ai_scores）を作成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
print("scored:", written)
```

市場レジーム判定（market_regime テーブルへの書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
```

監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセスできます
```

ニュース RSS の取得（単体）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

研究モジュールの利用（例: モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は {"date","code","mom_1m",...} のリスト
```

ログレベル・環境モード
- 環境変数 `LOG_LEVEL` と `KABUSYS_ENV` によって挙動・ログが変わります。KABUSYS_ENV は `development`, `paper_trading`, `live` のいずれかを指定してください。

---

## ディレクトリ構成（主要ファイル）
プロジェクトの重要モジュールを抜粋して示します（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースを銘柄別にスコアリング（OpenAI）
    - regime_detector.py           — マーケットレジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存・認証）
    - pipeline.py                  — ETL パイプライン（run_daily_etl など）
    - calendar_management.py       — 市場カレンダー管理（営業日判定・更新ジョブ）
    - news_collector.py            — RSS 収集・前処理
    - quality.py                   — 品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                     — zscore_normalize 等汎用統計ユーティリティ
    - audit.py                     — 監査ログ用スキーマ初期化
    - etl.py                       — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py       — forward returns / IC / factor summary / rank
  - ai、research、data の他に strategy / execution / monitoring パッケージを想定した公開が行われています（__all__ 参照）。

---

## 注意事項 / 設計上のポイント
- ルックアヘッドバイアスへの配慮: 各所で date を明示的に渡し、datetime.today() 参照を避ける実装方針です。バックテスト用途では適切な「その時点で利用可能なデータ」を再現できます。
- 冪等性: ETL の保存処理は ON CONFLICT DO UPDATE など冪等化を重視しています。
- OpenAI 呼び出し: レスポンス検証・JSON モードの扱い、429/5xx に対するリトライを備えています。API キーは引数で注入可能（テストのため）。
- セキュリティ: news_collector は SSRF 防止、XML Bomb 防止（defusedxml）などを実装しています。
- 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込みます。テスト時に自動読み込みを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 開発・運用のヒント
- DuckDB ファイルは settings.duckdb_path で管理されます。複数環境（dev / paper / live）で異なる DB を使うことを推奨します。
- OpenAI 呼び出しはコストがかかるため、研究時はモックを使ったユニットテストを整備してください（_call_openai_api を patch する設計が各モジュールにあります）。
- ETL は監査ログや品質チェックと組み合わせて運用してください。ETLResult に品質チェックの結果とエラー情報が纏まって返るため、監視アラートやランブックに利用できます。

---

もし README に追記したい内容（CLI コマンド、サンプル .env.example、デプロイ手順、ユニットテストの実行方法など）があれば教えてください。必要に応じて README を拡張します。