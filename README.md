# KabuSys

日本株向け自動売買 / データ基盤ライブラリ（KabuSys）。  
DuckDB をデータレイクとして用い、J-Quants からのデータ取得、ニュース収集・NLP（OpenAI）による銘柄スコアリング、リサーチ用ファクター計算、監査ログ（発注トレーサビリティ）などを提供します。

---

## 概要

KabuSys は日本株のデータパイプラインとリサーチ・自動売買の基盤機能を提供する Python パッケージです。主な特徴は次のとおりです。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- DuckDB を利用した永続化（raw_prices / raw_financials / market_calendar など）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 ai_scores）と市場レジーム判定
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → executions）の初期化ユーティリティ
- Look-ahead bias を避ける設計（時間窓・DB 条件により未来データ参照を防止）

---

## 主な機能一覧

- data.jquants_client: J-Quants API 用クライアント（取得・保存・認証・レート制御・リトライ）
- data.pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- data.news_collector: RSS 取得と raw_news への冪等保存
- data.quality: データ品質チェック群（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- data.audit: 監査ログテーブルの初期化（init_audit_schema / init_audit_db）
- data.calendar_management: 営業日判定・next/prev_trading_day・calendar_update_job
- ai.news_nlp: ニュースを銘柄別に集約して OpenAI に投げ、ai_scores に書き込む（score_news）
- ai.regime_detector: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定（score_regime）
- research: ファクター計算・特徴量探索（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）
- data.stats: zscore_normalize（クロスセクション正規化ユーティリティ）

---

## 動作要件

- Python 3.10 以上（PEP 604 の型記法や一部の構文を使用）
- 必要主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

開発環境によっては追加パッケージが必要です。プロジェクトに requirements ファイルがあればそちらを参照してください。

例（最低限のインストール）:
```
pip install duckdb openai defusedxml
```

---

## 環境変数 / 設定

KabuSys は環境変数またはプロジェクトルートの `.env` / `.env.local` を読み込みます（自動ロード）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用される環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 内で参照）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)。デフォルト development
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)。デフォルト INFO

README 用の簡易 .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxx
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

.env のパースは POSIX 風の書式（export プレフィックス・クォート・コメント等）に対応しています。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化:
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール（プロジェクトの requirements.txt があればそれを利用）:
   ```
   pip install -r requirements.txt
   # 或いは最低限
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定（.env または環境変数で）。`.env` をプロジェクトルートに置くと自動読み込みされます。

4. DuckDB の初期スキーマや監査 DB を作成する場合は、アプリから init 関数を呼び出します（例は次節の「使い方」参照）。

---

## 使い方（代表的な API と実行例）

下記の例は Python REPL やスクリプトから直接呼び出すパターンです。すべて DuckDB 接続（duckdb.connect）を渡します。

共通: DuckDB 接続の作成例
```py
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 監査ログ DB の初期化
```py
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# または既存接続にスキーマを追加:
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```

2) 日次 ETL 実行（市場カレンダー・株価・財務の差分 ETL と品質チェック）
```py
from kabusys.data.pipeline import run_daily_etl

# target_date: None で今日。id_token は通常省略してモジュールのキャッシュを利用。
result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュースのセンチメントスコア付与（ai_scores への書き込み）
```py
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
# OpenAI API Key を引数で渡すことも可能:
# score_news(conn, date(2026,3,20), api_key="sk-...")
```

4) 市場レジーム判定（market_regime テーブルへ書き込み）
```py
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

5) ファクター計算 / リサーチ API 例
```py
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
# 正規化:
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(moms, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- OpenAI 呼び出しは rate limit やネットワークエラーを考慮してリトライ/フォールバック実装があります。テスト時はモック（unittest.mock.patch）で _call_openai_api を差し替え可能です。
- 関数群は Look-ahead bias を回避する設計になっています（target_date 未満 / 排他的条件、datetime.today() 参照の回避等）。

---

## ディレクトリ構成

主要ファイル / モジュール（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                          — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュース NLP / ai_scores 書き込み（score_news）
    - regime_detector.py                — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント（fetch/save）
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - etl.py                            — ETLResult 再エクスポート
    - news_collector.py                 — RSS 取得 / 前処理 / raw_news 保存
    - quality.py                        — データ品質チェック
    - stats.py                          — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py            — 市場カレンダー管理・営業日判定・calendar_update_job
    - audit.py                          — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py                — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py             — calc_forward_returns / calc_ic / factor_summary / rank

パッケージのエントリポイントやヘルパーは上記ファイルに集約されています。

---

## 実運用上の注意

- 環境変数（特に API トークン）は漏洩しないように管理してください。
- OpenAI / J-Quants の API 利用にはそれぞれの使用制限・課金があるため、キーの扱いとコール頻度に注意してください。
- ETL の実行はスケジューラ（cron, Airflow 等）で日次夜間に回すのが想定です。calendar_update_job はカレンダーを先に取得します。
- 監査ログは削除前提ではないためディスク容量やバックアップ方針を検討してください。
- DuckDB のバージョンや SQL 構文の互換性による差異に注意（特に executemany の空リストに関する注意書き等がコード内にあります）。

---

## テストとデバッグ

- OpenAI 呼び出しやネットワーク依存部分はモックして単体テストを実行することを推奨します。
- 設定読み込みの自動化は .env 解析ロジックのテスト対象です。自動ロードを回避したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ログレベルは `LOG_LEVEL` 環境変数で制御できます（DEBUG を使うと内部処理ログが得られます）。

---

この README はコードベースの主要機能を簡潔にまとめたものです。各モジュールの詳細な使い方は該当ソースコードの docstring を参照してください。必要に応じてサンプルスクリプトや CI 設定、requirements.txt の整備を行ってください。