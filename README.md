# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクタ計算、監査ログ（発注〜約定のトレーサビリティ）などを含みます。

---

## 主な概要

- コア目的: 日本株向けにデータを収集・品質管理し、AI（LLM）を用いたニュースセンチメントや市場レジームを算出、研究・戦略実装のためのユーティリティを提供する。
- DB: DuckDB を主に使用（監査用 DB も DuckDB）。一部監視情報用に SQLite を想定。
- 外部 API:
  - J-Quants（株価・財務・カレンダー取得）
  - OpenAI（ニュースセンチメント / レジーム判定）
  - Slack（通知・モニタリング想定）
- 設計方針:
  - ルックアヘッドバイアス防止（内部で date.today() を直接参照しない設計、関数に target_date を渡す）
  - 冪等性重視（DB への保存は ON CONFLICT 等で上書き）
  - フェイルセーフ（API 失敗時はゼロスコア等で継続）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価（日足）、財務データ、JPX カレンダーを差分（バックフィル対応）で取得・保存
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合等（kabusys.data.quality）
- ニュース収集 / 前処理
  - RSS 収集、URL 正規化、SSRF 対策、前処理（kabusys.data.news_collector）
- ニュースの NLP スコアリング（LLM）
  - 銘柄ごとのニュースをまとめて OpenAI に投げ、ai_scores テーブルへ保存（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成（kabusys.ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）、前方リターン、IC、統計サマリー（kabusys.research.*）
- 監査ログ（発注〜約定のトレーサビリティ）
  - audit スキーマ初期化・専用 DB 初期化（kabusys.data.audit）
- J-Quants クライアント（レート制御・リトライ・トークン自動リフレッシュ）（kabusys.data.jquants_client）
- 環境設定管理（自動 .env ロード、必須キーチェック）（kabusys.config）

---

## 必要な環境変数（主なもの）

config.Settings で参照される主なキー（README 用サンプル）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に省略可能だが、設定推奨）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: (DEBUG/INFO/WARNING/ERROR/CRITICAL)

自動 .env ロード:
- パッケージロード時にプロジェクトルート（.git または pyproject.toml を探索）を基に .env と .env.local を自動で読み込みます。OS 環境変数が優先され、.env.local は .env を上書きします。
- 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成して有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール（最低限の想定依存）
   ```
   pip install -e .  # パッケージとしてインストール（setup がある場合）
   pip install duckdb openai defusedxml
   ```
   ※プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

4. .env を準備
   - プロジェクトルートに .env（および必要なら .env.local）を配置。例は下記を参照。

5. DuckDB データベース用ディレクトリ作成（デフォルト）
   ```
   mkdir -p data
   ```

---

## .env サンプル

プロジェクトルートに `.env`（実際の値は適宜置き換えてください）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: 秘匿情報は公開リポジトリに含めないでください。

---

## 使い方（コード例）

以下は主要機能の簡単な利用例です。すべて関数は同期で、DuckDB の接続オブジェクト（duckdb.connect(...)）を受け取ります。

- ETL（日次パイプライン）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア付与（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY が使われる
print("written:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")  # パスの親ディレクトリが無ければ作成される
```

- 研究用ファクター計算（例: momentum）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
```

---

## 重要な公開 API（抜粋）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult（戻り型）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - preprocess_text(...)

- kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize (kabusys.data.stats)

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys/ 以下）

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 自動ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py        — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - pipeline.py          — ETL パイプライン run_daily_etl 等
    - etl.py               — ETLResult 再エクスポート
    - quality.py           — データ品質チェック
    - news_collector.py    — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理・営業日処理
    - stats.py             — zscore_normalize 等（共通統計）
    - audit.py             — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py   — ファクター計算（momentum/value/vol）
    - feature_exploration.py — 前方リターン・IC・統計サマリー
  - monitoring/ (存在想定: 監視・監査用モジュール)
  - strategy/ (存在想定: 戦略実装用モジュール)
  - execution/ (存在想定: 発注 / ブローカー連携)

---

## 運用上の注意点 / ベストプラクティス

- OpenAI の呼び出しはコストとレートリミットが発生するため、バッチ化・キャッシュを検討してください。
- J-Quants の API レート上限（120 req/min）を守るため内部でレート制御が組み込まれていますが、外部呼び出しの頻度には注意。
- テスト／CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し自動 .env 読み込みを無効化することで環境依存を防げます。
- DuckDB ファイルは定期的にバックアップし、監査ログは削除しない運用を想定しています。
- 本ライブラリは Look-ahead bias を避ける設計方針を採用しているため、バックテスト実行時は target_date の扱いに注意してください。

---

必要であれば、README に次の内容を追加できます:
- 具体的な .env.example ファイル（完全版）
- CI / テスト実行手順（pytest の導入）
- 詳細な schema / テーブル定義（DDL の抜粋）
- デプロイ・運用（systemd サービス例、監視フロー）