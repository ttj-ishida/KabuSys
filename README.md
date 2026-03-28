# KabuSys — 日本株自動売買プラットフォーム（README）

本リポジトリは日本株向けのデータ基盤 / リサーチ / AIセンチメント / 監査ログ / ETL を備えた自動売買基盤の一部実装です。主要な機能群は DuckDB をデータレイヤに用い、J-Quants API・RSS・OpenAI 等と連携してデータ取得・品質チェック・AIスコアリング・市場レジーム判定・監査ログ（発注→約定トレーサビリティ）などを行います。

注意事項:
- 本リポジトリには実際の発注（ブローカー）連携や本番運用に関わる設定が含まれます。実運用前にコードの理解・検証・リスク管理を必ず行ってください。
- Python の型アノテーション（| 演算子等）を使用しているため、Python 3.10+ を想定しています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数 / 設定
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意

---

## プロジェクト概要

KabuSys は次のコンポーネントを備える日本株向けの自動売買基盤向けライブラリです。

- ETL（J-Quants からの差分取得、保存、品質チェック）
- ニュース収集（RSS）と NLP による銘柄別センチメントスコア化（OpenAI）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを統合）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 市場カレンダー管理（営業日判定）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ
- J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）

---

## 主な機能一覧

- kabusys.data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（fetch/save 関数）
  - market_calendar 管理（営業日判定・前後営業日の取得）
  - ニュース収集（RSS）と前処理、安全対策（SSRF 対策、サイズ制限、トラッキング除去）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（z-score 正規化）

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime を書き込み

- kabusys.research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
  - 再現可能な、外部 API にアクセスしないロジック

- 設定管理: kabusys.config で .env 自動読み込み（.git や pyproject.toml を基準にプロジェクトルート探索）と Settings オブジェクト

---

## セットアップ手順

想定環境: Python 3.10+

1. リポジトリをクローン／チェックアウト
   git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要なパッケージをインストール
   主要な依存（抜粋）:
   - duckdb
   - openai
   - defusedxml

   例:
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数を設定
   プロジェクトルートに `.env` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須の主な環境変数（.env に記入例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=...
   KABUSYS_ENV=development   # development / paper_trading / live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データフォルダ作成（必要に応じて）
   mkdir -p data

---

## 簡単な使い方（コード例）

すべての操作は Python スクリプトやジョブランナー（cron / Airflow / Prefect 等）から呼べます。以下は一部抜粋です。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP の実行
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込んだ銘柄数:", written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査 DB 初期化（監査ログ専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って later に INSERT/SELECT など
```

- 研究 / ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト
```

- market_calendar の利用例
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## 環境変数 / 設定（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime などで使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携で利用）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 ("development", "paper_trading", "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

設定は .env ファイル（プロジェクトルート）または OS 環境変数で指定可能。config モジュールはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を自動検出して .env / .env.local を読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイルの説明）

以下は主要モジュールと役割の概観です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを集約して OpenAI に投げ、銘柄別 ai_scores を書き込む
    - regime_detector.py — ETF 1321 の MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save/認証）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
    - calendar_management.py — 市場カレンダー管理、営業日判定
    - news_collector.py — RSS 収集・前処理・保存（SSRF 対策、サイズ制約）
    - quality.py — データ品質チェック（欠損、スパイク、重複、日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログ（signal_events / order_requests / executions）スキーマ定義・初期化
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 計算
    - feature_exploration.py — forward returns / IC / factor_summary / rank
  - research パッケージは data.stats と連携してリサーチ処理を行う

---

## 運用上の注意 / ベストプラクティス

- OpenAI 呼び出しはコストとレイテンシが発生します。バッチサイズ・トークン制御を適切に設定してください。
- J-Quants API はレート制限があるため、jquants_client の RateLimiter を尊重してください（120 req/min を想定）。
- ETL / AI の実行はスケジューラ（夜間バッチ）で実行する想定です。run_daily_etl は品質チェックを行いますが、検出された問題に対しては呼び出し側で対処してください。
- 本番発注連携を行う場合は KABUSYS_ENV を必ず確認し、paper_trading と live の切り替えを明示的に行ってください。
- DB のバックアップと監査ログの保全を徹底してください（監査ログは削除しない前提）。

---

もし README に追加したい使用例や運用手順（CI/CD、Airflow の DAG 例、Slack 通知設定等）があれば教えてください。必要に応じて README を拡張します。