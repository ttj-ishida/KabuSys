# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
ETL（J-Quants などからのデータ取得）・データ品質チェック・ニュースNLP（OpenAI）・市場レジーム判定・リサーチ用ファクター計算・監査ログ等を統合的に提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB をローカルデータストアに用いる（冪等保存、ON CONFLICT 挙動を前提）
- API 呼び出しはリトライ・バックオフ・レート制御を実装
- 監査ログでシグナル→発注→約定のトレーサビリティを保証

---

## 主な機能一覧
- データ取得（J-Quants）
  - 株価日足（OHLCV）取得・保存（差分ETL、ページネーション対応）
  - 財務データ（四半期）取得・保存
  - JPX マーケットカレンダー取得・保存
- ETL パイプライン
  - run_daily_etl: カレンダー→株価→財務→品質チェックの一括処理
  - 個別実行: run_prices_etl, run_financials_etl, run_calendar_etl
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）
  - URL 正規化、SSRF 対策、XML の安全パース（defusedxml）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメントを取得して ai_scores テーブルへ保存
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントの合成）
- リサーチ用ファクター計算
  - モメンタム、ボラティリティ、バリュー等の計算ユーティリティ
  - forward returns / IC / 統計サマリー等
- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - init_audit_db で監査用 DB を初期化
- 設定管理
  - .env 自動読み込み（OS > .env.local > .env、無効化フラグあり）
  - settings オブジェクト経由で各種パス／閾値等を参照可能

---

## 必要条件
- Python 3.10 以上（型注釈に | を用いているため）
- 推奨パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （開発時は pip install -e . を使ってローカルパッケージとしてインストールできる想定）

3. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml のある場所）を自動検出し、以下を自動で読み込みます（既定：OS > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   例 `.env`（必須と思われる最小例）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   # Optional: KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知等で使用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678

   # OpenAI
   OPENAI_API_KEY=sk-...

   # DB パス（デフォルトを使う場合は不要）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境・ロギング
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須環境変数（Settings で _require() が呼ばれるもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   AI モジュールは `OPENAI_API_KEY` を参照します（引数で上書き可能）。

---

## 使い方（例）

以下はライブラリをインポートして利用する最小例です。実行は Python スクリプトや REPL から行えます。

- DuckDB 接続準備（settings を利用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（market calendar → prices → financials → quality checks）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP によるスコア付け（OpenAI API キーは環境変数 OPENAI_API_KEY を使用）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import os

cnt = score_news(conn, date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
print(f"書き込み銘柄数: {cnt}")
```

- 市場レジーム判定（1321 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import os

score_regime(conn, date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
```

- 監査ログスキーマの初期化（監査用テーブル作成）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# init_audit_db は DuckDB の接続を返します（ファイルがなければ作成）
audit_conn = init_audit_db(settings.duckdb_path)
```

- 設定参照例
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env, settings.is_live)
```

注意：
- OpenAI 呼び出しは課金対象になります。API キー・レートに注意してください。
- ETL / API 呼び出しはネットワークアクセスを行います。J-Quants の利用には適切なトークンが必要です。
- ニュース収集には SSRF 対策や最大応答サイズ制限が組み込まれていますが、実行時のネットワーク安全性は運用側でも配慮してください。

---

## 設計上の重要なポイント（運用メモ）
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行うため、パッケージ配布後でも CWD に依存せず動作する想定。
- 自動ロードの優先順は OS 環境変数 > .env.local > .env です。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って抑制できます。
- J-Quants API 呼び出しは 120 req/min のレート制御を行います（内部 RateLimiter）。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE）を基本としています。
- AI モジュールはレスポンスパース失敗や API エラー時にフェイルセーフ（スコア 0.0 など）で継続するよう設計されています。
- 監査ログのタイムスタンプは UTC 保存を前提としています（init_audit_schema は SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成（抜粋）
プロジェクトは src/kabusys 以下に実装されています。主要ファイルを抜粋すると：

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（OpenAI）と ai_scores 書き込み
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py        — J-Quants API クライアント（取得 + 保存）
    - news_collector.py        — RSS ニュース収集（SSRF 対策等）
    - quality.py               — データ品質チェック（欠損・スパイク等）
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py   — 市場カレンダー管理（営業日判定等）
    - audit.py                 — 監査ログ DDL / 初期化ユーティリティ
    - etl.py                   — ETL インターフェース（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py       — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py   — forward returns / IC / 統計サマリー

（上記は主要モジュールの抜粋です。実際のソース全体は src/kabusys 以下をご参照ください）

---

## 開発・テスト時の注意
- 自動 .env ロードをテストで無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- OpenAI 呼び出しなど外部 API はテスト時にモックすることを推奨します（モジュール内で明示的に _call_openai_api を差し替え可能な設計になっています）。
- DuckDB はインメモリ（":memory:"）で接続可能なのでユニットテストが容易です（audit.init_audit_db も ":memory:" をサポート）。

---

必要であれば、README に追加すべき運用手順（cron / systemd による定期 ETL 実行、ログ監視、Slack 通知の統合例等）や具体的な .env.example ファイルのテンプレート、サンプルデータを使ったハンズオン手順を作成します。どの情報を優先して追加しますか？