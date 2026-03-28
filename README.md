# KabuSys

日本株向け自動売買・データプラットフォームのライブラリ群です。  
このリポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログ（発注・約定トレーサビリティ）などのユーティリティを提供します。

主な目的は「データ収集 → 品質チェック → 特徴量生成 → シグナル評価 → 発注監査」のワークフローを安全に実行できる基盤を提供することです。

---

## 特徴（機能一覧）

- 環境設定管理
  - .env/.env.local 自動読み込み（パッケージ内で静的にプロジェクトルートを検出）
  - 必須環境変数の検証（Settings クラス）

- データ取得（J-Quants API）
  - 株価日足（OHLCV）・財務データ・上場銘柄情報・JPX カレンダーの取得
  - ページネーション対応・リトライ（指数バックオフ）・401 の自動リフレッシュ
  - レートリミット（120 req/min）を守る RateLimiter 実装
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル対応
  - ETL 結果（ETLResult）に品質チェック結果を格納

- データ品質チェック
  - 欠損（OHLC）・スパイク（前日比閾値）・重複・日付不整合チェック
  - QualityIssue オブジェクトで問題を集約

- ニュース収集 & NLP
  - RSS フィード取得（SSRF 対策、gzip 上限、URL 正規化）
  - ニュースを銘柄に紐付け raw_news/news_symbols に保存
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント集計（score_news）
  - マクロニュースから市場レジーム判定（score_regime）

- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化

- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブル定義
  - 監査スキーマの初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注トレーサビリティ（冪等キー、ステータス遷移）を想定

---

## セットアップ手順

前提
- Python 3.10 以上（typing における `X | Y` 構文を使用）
- DuckDB を使用（ローカルファイルまたは :memory:）

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係をインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （パッケージ化されている場合は `pip install -e .` で開発インストール可能）

4. 環境変数の設定
   - プロジェクトルートに `.env` を配置すると自動読み込みされます（.env.local は上書き）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の主要環境変数（例）
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...         （score_news / regime で使用）
- KABU_API_PASSWORD=...      （kabuステーション連携がある場合）
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb   （デフォルト）
- SQLITE_PATH=data/monitoring.db    （デフォルト）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...

簡単な .env.example
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要ユースケース例）

以下は Python REPL やスクリプトからの利用例です。

- DuckDB 接続を作成して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）を生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込み件数:", n_written)
```

- 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests 等を操作可能
```

- カレンダー更新ジョブ単体
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- Settings を利用して環境変数を取得
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点
- OpenAI にアクセスする関数は API キーを引数で注入可能（テスト容易性のため）。
- 関数はルックアヘッドバイアスを防ぐ設計（内部で date.today() を参照しないことが多い）です。バックテスト用途では target_date を明示してください。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント計算（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETL 公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py     — RSS 収集、raw_news 保存
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py            — 品質チェック（check_missing_data, check_spike 等）
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログスキーマ作成・初期化
  - research/
    - __init__.py
    - factor_research.py    — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/ (上記)
  - research/ (上記)
  - その他:
    - data/                   （デフォルトの DB ファイル配置先）
    - .env / .env.local       （ローカル環境変数）

---

## 実運用時の注意点

- 本コードは「本番発注」や「ライブ口座」の操作を想定した設計要素を含みます。ライブ運用時は設定（KABUSYS_ENV）や SLACK 通知、監査ログの構成を慎重に行ってください。
- OpenAI API コールはコスト発生およびレイテンシを伴います。バッチ数やモデル選択は運用要件に合わせて調整してください。
- J-Quants API のレート制限（120 req/min）や認証トークンの有効期限に注意してください（jquants_client は自動リフレッシュ機能を持ちます）。
- News Collector は外部 RSS を取得するため SSRF 対策やレスポンス上限が実装されていますが、運用時に信頼できるソースだけを使用することを推奨します。

---

## ログ・デバッグ

- LOG_LEVEL 環境変数でログレベルを制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 各モジュールは logger を利用して詳細ログを出力します。デバッグ時は DEBUG に設定してください。

---

以上が KabuSys の基本的な README 内容です。必要に応じて導入ガイド（Docker / systemd / CI 設定）、SQL スキーマ定義ファイル、サンプル .env.example、運用手順（ロールバック・監査）などを追加できます。追加をご希望であれば用途（ETL 実行スケジュール、バックテスト環境、ライブ運用）を教えてください。