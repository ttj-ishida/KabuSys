# KabuSys

KabuSys は日本株向けのデータパイプライン、リサーチ/ファクター計算、ニュース NLP と市場レジーム判定、監査ログ（トレーサビリティ）等を含む自動売買プラットフォームのライブラリ群です。本リポジトリは主にバックテスト・データ基盤・研究用途（および実運用の周辺モジュール）に役立つコンポーネントを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API と実行例）
- 環境変数（主要なキー）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J‑Quants API からのデータ ETL（株価、財務、JPX カレンダー）
- DuckDB を用いたデータ保存・品質チェック・監査ログ
- ニュース収集（RSS）・前処理・OpenAI を使ったニュースセンチメント（銘柄別）
- 市場レジーム判定（ETF の MA200 とマクロニュースの LLM スコアの合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（シグナル→発注→約定をトレースするテーブル群）

設計上のポイント:
- ルックアヘッドバイアスを避けるため、内部で現在時刻を無闘的に参照しない設計の関数が多い（target_date を明示）。
- DuckDB を中心に SQL を活用して高速に集計・ETL を行う。
- 外部 API 呼び出しはリトライやレート制御、エラーハンドリングを備える。

---

## 機能一覧

- data.jquants_client: J‑Quants からのデータ取得と DuckDB への冪等保存
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - get_id_token（リフレッシュトークン経由）
- data.pipeline: 日次 ETL パイプライン (run_daily_etl) と個別 ETL ジョブ
- data.quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- data.calendar_management: 営業日判定・前後営業日の取得・カレンダー更新ジョブ
- data.news_collector: RSS からのニュース収集・前処理・保存補助（SSRF 対策等を含む）
- data.audit: 監査ログ（signal_events / order_requests / executions）の初期化と DB ユーティリティ
- data.stats: zscore_normalize（クロスセクション正規化）
- research: ファクター計算・特徴量探索（calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank）
- ai.news_nlp: ニュースを LLM（OpenAI）でスコアリングして ai_scores に書き込む（score_news）
- ai.regime_detector: ETF（1321）MA200 とニュースセンチメントを合成して market_regime を計算（score_regime）
- config: 環境変数読み込み・管理（.env 自動ロード、settings オブジェクト提供）

---

## セットアップ手順

前提
- Python 3.10+（typing の | 表記などが使われているため）
- 開発環境に以下の主要依存パッケージをインストールしてください（例）:

推奨パッケージ（抜粋）
- duckdb
- openai
- defusedxml

例:
1. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを使用）
   - pip install duckdb openai defusedxml

3. パッケージをインストール（開発モード）
   - pip install -e .

注意:
- 実行するには J‑Quants のリフレッシュトークンや OpenAI API キーなどの環境変数設定が必要です（下記参照）。
- config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（主要）

config.Settings で参照される主要な環境変数（一部）:

- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須。関数引数でも指定可）

.env.example（プロジェクトに合わせて作成）を用意して .env を作成してください。

---

## 使い方（主要 API と実行例）

以下は最小限の利用例です。すべての操作は明示的な DuckDB 接続（duckdb.connect）を受け取るか、DB パスを用いて行います。

1) DuckDB に接続して ETL を実行する（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored:", n_written)
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ（audit）スキーマ初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# または既存 conn に対して init_audit_schema(conn)
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

6) 環境設定にアクセスする
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- score_news / score_regime 等の AI 呼び出しは OpenAI SDK を用いるため、API レートやコストに注意してください。関数は API 呼び出し失敗時にフェイルセーフ（スコア = 0 など）で継続する設計です。
- ETL 関数は基本的に冪等性（ON CONFLICT DO UPDATE）を考慮した保存を行います。

---

## ディレクトリ構成

主要なファイル/モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数/.env 管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP スコアリング（score_news）
    - regime_detector.py     # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J‑Quants API クライアント + DuckDB 保存関数
    - pipeline.py            # ETL パイプライン（run_daily_etl 他）
    - etl.py                 # ETLResult の再エクスポート
    - calendar_management.py # 市場カレンダー管理（営業日判定等）
    - stats.py               # 汎用統計ユーティリティ（zscore_normalize）
    - quality.py             # データ品質チェック
    - news_collector.py      # RSS 収集・前処理
    - audit.py               # 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     # モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py # 将来リターン / IC / 統計サマリー
  - research/*.py
  - （その他: strategy, execution, monitoring パッケージを想定しているが実装は一部のみ）

（プロジェクトルートに .env / .env.local / pyproject.toml / README.md などを配置する想定）

---

## 注意事項 / 運用ヒント

- OpenAI 呼び出しはコストが発生するため、テストではモック（unittest.mock）で API 呼び出し関数を差し替えることを推奨します（モジュール内に _call_openai_api の差し替えポイントがあります）。
- J‑Quants API はレート制限や認証を考慮する必要があります。jquants_client はレートリミッタ・リトライ・401 自動リフレッシュ等を実装していますが、運用時は API キーの取り扱いに注意してください。
- DuckDB の executemany に関するバージョン差異（空リストでの挙動など）をコード中で考慮しています。DuckDB のバージョンアップ時は互換性の確認を行ってください。
- データ品質チェック（data.quality.run_all_checks）は ETL 後に自動で走るよう設計されていますが、問題発覚時の運用フロー（停止/通知/ロールバックなど）は別途ポリシーを設計してください。

---

必要であれば以下も作成できます:
- .env.example テンプレート
- requirements.txt / constraints.txt
- 実行スクリプト（CLI）例（ETL/run_daily_etl の cron ランナー）
- ユニットテスト／モックのサンプル

ご要望があれば README の追加改善（例: 実運用フロー、監視アラート設定、Slack 通知の使い方、具体的な SQL スキーマの説明等）を作成します。