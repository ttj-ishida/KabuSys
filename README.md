# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集・LLM を用いたニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター計算・監査ログ（発注→約定のトレース）など、トレーディングシステムに必要なコンポーネント群を提供します。

主に DuckDB をデータレイクとして利用し、J-Quants API・RSS・OpenAI（gpt-4o-mini 等）を組み合わせて動作します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単な例）
- 環境変数
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームと研究／実行層のユーティリティ群をまとめたパッケージです。主要コンポーネントは以下です。

- データ取得（J-Quants API クライアント）と ETL（差分取得・保存・品質チェック）
- 市場カレンダー管理・営業日判定
- ニュース収集（RSS）とニュースの NLP（OpenAI を用いたセンチメント）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
- リサーチ用ファクター計算（モメンタム/ボラティリティ/バリュー等）と特徴量解析ツール
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の重要な方針として、バックテストや学習でのルックアヘッドバイアスを避けるために、ターゲット日を明示的に渡す API を採用しており、内部で datetime.today()/date.today() を直接参照しない実装になっています。

---

## 主な機能一覧

- data/
  - ETL pipeline（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API client（認証・ページネーション・リトライ・レート制御）
  - market calendar 管理と営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - news_collector（RSS 収集、SSRF 対策、トラッキングパラメータ除去、前処理）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査ログテーブルの初期化／監査 DB ヘルパー）
  - stats（zscore_normalize 等の汎用統計ユーティリティ）

- ai/
  - news_nlp.score_news: ニュースを銘柄ごとにまとめて LLM に投げ、ai_scores テーブルに格納
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースセンチメントを合成して market_regime に格納

- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

- config
  - Settings クラスで環境変数および .env 自動読み込みを管理（優先順位: OS > .env.local > .env）
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## セットアップ手順

前提
- Python 3.10 以上（typing の `X | None` 等を使用）
- システムに DuckDB のバイナリが不要（pip の duckdb パッケージで動作します）

1. リポジトリをクローン／展開
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （必要に応じて）pip install -e . でローカルインストール
   - 実運用で Slack 通知や sqlite 利用がある場合は追加ライブラリをインストールしてください

4. 環境変数の設定
   - 主要な必須環境変数は下記「環境変数」セクションを参照
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（OS 環境変数が優先）
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

5. DuckDB 用ディレクトリ作成（デフォルトパスは data/ 以下）
   - mkdir -p data

---

## 環境変数（主要なもの）

以下は Settings クラスから読み取られる主要な環境変数です（必須は明示）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須) — kabu API のパスワード（発注等に使用）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）

.env のフォーマットは一般的な KEY=VALUE 形式に対応し、`export KEY=VALUE` のような行も許容します。引用符やコメントの処理も適切に行われます。

---

## 使い方（簡単な例）

下記は最小限の操作例です。各例では既に duckdb パッケージと OpenAI の API キー等が設定されていることを前提としています。

- DuckDB に接続して日次 ETL を実行する例:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア（ai_scores）を生成する例:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => OPENAI_API_KEY を使用
print("wrote scores for", n_written, "codes")
```

- 市場レジーム判定を実行する例:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化する例:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- market calendar の夜間更新ジョブを直接動かす例:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意点:
- OpenAI API 呼び出しや J-Quants API 取得はネットワークを伴うため、API キーやレート制限に注意してください。
- LLM 呼び出しは失敗時フェイルセーフ（スコア 0.0 等）で継続する実装になっていますが、API コストは発生します。

---

## ディレクトリ構成（主なファイル）

リポジトリの主要な Python パッケージ構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py  — ニュースの LLM センチメント評価、ai_scores 書込み
    - regime_detector.py — ETF MA とマクロセンチメント合成による market_regime 書込み
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / 認証 / rate-limit）
    - pipeline.py — ETL パイプラインの実装（run_daily_etl 等）
    - etl.py — ETLResult のエクスポート
    - calendar_management.py — market_calendar 管理、営業日判定、calendar_update_job
    - news_collector.py — RSS 収集・前処理・raw_news 保存ロジック
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログ用テーブル定義と初期化ユーティリティ
    - stats.py — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
  - research/...（その他）

データベース上の想定されるテーブル（主なもの）:
- raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
- raw_financials (code, report_date, period_type, eps, roe, fetched_at, ...)
- market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
- raw_news (id, datetime, source, title, content, url)
- news_symbols (news_id, code)
- ai_scores (date, code, sentiment_score, ai_score)
- market_regime (date, regime_score, regime_label, ma200_ratio, macro_sentiment)
- signal_events / order_requests / executions（監査ログ系）

---

## 運用上の注意

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml の親ディレクトリ検出）を基準に行われます。テスト環境で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限があるため、jquants_client モジュールは内部でスロットリングを行います。大量同時実行は避けてください。
- OpenAI 呼び出しはリトライ・バックオフや JSON 検証を行いますが、API レスポンスの仕様変更によりパースエラーが発生する可能性があります。ログを参照して運用してください。
- DuckDB の executemany はバージョン依存の挙動（空リスト許容の有無）があるため、コード内で空リストの executemany を避ける工夫をしています。DuckDB のバージョンは安定したものをご利用ください。

---

必要に応じて、各モジュールの API ドキュメント（関数引数・返り値）を README に追記します。特定の使い方（例: バックテストでのデータ切り出し、監査テーブルの参照方法、外部システムとの連携サンプル）が必要なら教えてください。