# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション / RSS / OpenAI 等を組み合わせ、データ収集（ETL）・品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログなどを提供します。

---

## 概要

KabuSys は日本株の自動売買システム／データプラットフォーム向けに設計された Python モジュール群です。主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー等の差分取得（ETL）
- DuckDB を用いたデータ保存と品質チェック
- RSS を用いたニュース収集とニュース単位／銘柄単位の NLP（OpenAI）スコアリング
- マクロセンチメントと ETF MA に基づく市場レジーム判定（LLM 併用）
- ファクター計算・特徴量探索（研究用途）
- 発注〜約定までの監査ログ（監査テーブル／インデックス定義）
- 環境変数ベースの設定管理（.env 自動ロード対応）

---

## 主な機能一覧

- data（ETL / カレンダー / news collector / J-Quants クライアント）
  - run_daily_etl（株価・財務・カレンダーの差分 ETL）
  - jquants_client（API レート制御・リトライ・保存ロジック）
  - market calendar 管理（is_trading_day / next_trading_day 等）
  - news_collector（RSS 取得、前処理、raw_news 保存）
  - quality（欠損・スパイク・重複・日付整合性チェック）
  - audit（監査テーブルの初期化・監査 DB 作成ユーティリティ）
- ai（ニュース NLP / 市場レジーム判定）
  - score_news（銘柄ごとのニュースセンチメントを ai_scores に書き込み）
  - score_regime（ETF 1321 の MA とマクロニュースを合成して market_regime に書き込み）
- research（ファクター計算・特徴量解析）
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
- config（環境変数管理・.env 自動読み込み・設定アクセス）
- data.stats（zscore_normalize 等の統計ユーティリティ）

設計方針としては「ルックアヘッドバイアスの排除」「冪等性」「外部 API のレート制御・リトライ」「DuckDB による高速ローカル分析」を重視しています。

---

## 必要条件 / 依存関係

（プロジェクトに requirements.txt がある想定ですが、最低限の依存は下記です）

- Python 3.9+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （標準ライブラリ以外の追加パッケージは用途に応じてインストールしてください）

例:
pip install duckdb openai defusedxml

---

## 環境変数（必須・推奨）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` で指定できます。パッケージは起動時に自動でプロジェクトルートの .env を読み込みます（自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（少なくとも実行する機能に応じて設定してください）:
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（jquants_client）
- KABU_API_PASSWORD      — kabuステーション API パスワード（execution 関連）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID
- OPENAI_API_KEY         — OpenAI 呼び出し（news_nlp / regime_detector）で使用

その他:
- KABUSYS_ENV            — "development" | "paper_trading" | "live"（既定: development）
- LOG_LEVEL              — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（既定: INFO）
- DUCKDB_PATH            — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite パス（既定: data/monitoring.db）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

注意: `.env.local` は `.env` より優先して上書きされます（OS 環境変数はさらに優先）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、必要な環境変数をエクスポート
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な例）

以下は主要なユースケースの最小例です。実運用ではログ設定・エラーハンドリング・スケジューリングを追加してください。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリングを実行（OpenAI API 必要）:
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

- 市場レジーム（regime）スコアを計算:
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests / executions 等を操作できます
```

- 研究用ファクター計算:
```python
from kabusys.research import calc_momentum, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意: OpenAI を使う機能は環境変数 OPENAI_API_KEY を設定してください。J-Quants API を使う ETL は JQUANTS_REFRESH_TOKEN を必要とします。

---

## 開発 / デバッグ上のポイント

- 設定管理: kabusys.config.settings を経由して設定にアクセスできます（例: settings.jquants_refresh_token）。
- .env 読み込み: プロジェクトルート（.git / pyproject.toml を基準）から自動で .env/.env.local を読み込みます。自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ルックアヘッドバイアス防止: AI スコアや ETL 処理は内部で date 引数を要求し、datetime.today() 等による暗黙の参照を避ける設計です。バックテスト時は target_date を明示してください。
- DuckDB executemany の制約: 空パラメータの executemany は一部の DuckDB バージョンでエラーになるため、コード中で空チェックを行っています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / .env 自動ロード / 設定オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py          — ニュース NLP（OpenAI）スコアリング（ai_scores 生成）
    - regime_detector.py   — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（リクエスト・保存）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py    — RSS 収集・前処理・保存
    - quality.py           — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - audit.py             — 監査ログスキーマ定義 / 初期化ユーティリティ
    - stats.py             — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py          — (上記) ETL 実装と ETLResult
    - etl.py               — ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py   — momentum / value / volatility
    - feature_exploration.py — forward returns / IC / summary / rank
  - research/feature_exploration.py
  - その他: execution, monitoring, strategy など（パッケージ公開用 __all__ に含まれる想定）

---

## 注意事項 / 運用上の留意点

- 実際の発注やライブ環境での運用は十分なテストと安全対策（レート制御、リスク管理、冪等性確認）を行ってください。
- OpenAI API を利用する処理はコストとレイテンシを伴います。バッチサイズやモデル選択は運用要件に合わせて調整してください。
- J-Quants API のレート制限を尊重してください（内部で RateLimiter を実装済みですが運用側でも配慮を）。
- DuckDB ファイルはバックアップ・管理を行ってください。デフォルトは data/kabusys.duckdb。
- セキュリティ: .env に秘密情報を平文で置く場合はアクセス制御に注意してください。

---

README は以上です。必要であれば以下を追加で作成します:
- requirements.txt の例
- 実行スクリプト（CLI）サンプル
- `.env.example` ファイルテンプレート
- 各モジュールの詳細ドキュメント（関数シグネチャ・例）