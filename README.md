# KabuSys

日本株向けの自動売買／データプラットフォームのライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、監査ログ（発注 / 約定のトレース）、市場カレンダー管理など、トレーディングシステムの基盤機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件・インストール
- 環境変数 (.env) と設定
- セットアップ手順
- 使い方（簡易サンプル）
- ディレクトリ構成
- 開発・テストに関する補足

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引に必要なデータ基盤と分析・実行支援ツール群を集めた Python パッケージです。主に以下を目的としています。

- J-Quants API からの差分 ETL（株価日足 / 財務 / 市場カレンダー）
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI を用いたニュースセンチメント解析および市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 市場カレンダー管理（JPX カレンダー）と営業日判定ユーティリティ

設計上の特徴:
- ルックアヘッドバイアスを避けるため、日付参照は明示的な target_date を基本とします。
- DuckDB をデータストアとして利用（オンメモリやファイル両対応）。
- API 呼び出しにはリトライ・バックオフ・レート制限を備えた堅牢な実装。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - ニュース収集（RSS パース・URL 正規化・SSRF 対策）
  - カレンダー管理（is_trading_day / next_trading_day / get_trading_days 等）
  - データ品質チェック（missing_data / spike / duplicates / date_consistency）
  - 監査ログ DB 初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースをまとめて OpenAI で銘柄別センチメントを算出し ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースを組み合わせ市場レジームを判定
- research/
  - factor_research (calc_momentum, calc_value, calc_volatility)
  - feature_exploration (calc_forward_returns, calc_ic, factor_summary, rank)
- config.py
  - .env / 環境変数の自動読み込み、settings オブジェクトによる一元管理

---

## 必要条件・インストール

- Python 3.10 以上（型注釈や union 型演算子 `|` を使用）
- 主な依存パッケージ（プロジェクトの環境によって調整してください）:
  - duckdb
  - openai
  - defusedxml

例（venv を作り、pip でインストール）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージをソースからインストールする場合（プロジェクトルートで）
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml がある想定で適宜インストールしてください）

---

## 環境変数 (.env) と設定

自動で .env / .env.local を読み込む仕組みがあります（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（一部）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI 呼び出しに必要（ai モジュールを利用する際）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例: .env の最小例

```
JQUANTS_REFRESH_TOKEN=（ここにリフレッシュトークン）
OPENAI_API_KEY=（OpenAI API キー）
KABU_API_PASSWORD=（kabu API パスワード）
SLACK_BOT_TOKEN=（Slack Bot Token）
SLACK_CHANNEL_ID=（Slack Channel ID）
DUCKDB_PATH=data/kabusys.duckdb
```

設定は `kabusys.config.settings` 経由で参照できます:
```py
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## セットアップ手順

1. Python と依存パッケージをインストール
2. プロジェクトルートに .env（と必要なら .env.local）を配置
3. DuckDB 用ディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```
4. 必要なテーブルを初期化（監査ログなど）:
   - 監査ログ専用 DB 初期化サンプル:
     ```py
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn は duckdb 接続オブジェクト
     ```
   - 他スキーマ初期化のユーティリティ（プロジェクト側で用意されている場合）を実行してください。

---

## 使い方（簡易サンプル）

以下はインタラクティブに主要機能を呼び出す例です。実運用ではエラーハンドリングやロギング設定等を追加してください。

- ETL（日次）を実行する

```py
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI によるニューススコアリング（ai.news_nlp.score_news）

```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- レジーム判定（ai.regime_detector.score_regime）

```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- カレンダー関数例

```py
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- 監査ログ初期化（監査 DB を作る）

```py
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成されます
```

---

## ディレクトリ構成（主なファイル / モジュール）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント解析と ai_scores への書き込み
  - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理、営業日判定
  - etl.py — ETL 用インターフェース再エクスポート
  - pipeline.py — 日次 ETL 実装（差分取得・保存・品質チェック）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェックモジュール
  - audit.py — 監査ログ（DDL・初期化ロジック）
  - jquants_client.py — J-Quants API クライアント（fetch, save 等）
  - news_collector.py — RSS 取得・前処理・保存ロジック
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等

---

## 開発・運用上の注意・補足

- API キーや秘密情報は .env に置くか、環境変数で渡してください。settings は必須キー未設定時に例外を投げます。
- OpenAI を使う処理はネットワークエラーやパース失敗時にフェイルセーフ（デフォルト値にフォールバック）する実装が多いですが、運用での再試行・監視は必須です。
- DuckDB の executemany に対する挙動やパラメータ制約に注意（実装内で注意書きがある箇所があります）。
- news_collector には SSRF 対策・レスポンスサイズ制限・XML パースの安全処理が組み込まれていますが、実稼働前に RSS ソースごとの検証を行ってください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Python のバージョンは 3.10 以上を想定しています（型注釈に `|` を使用）。

---

必要があれば README に含める実行例（cron ジョブ設定、systemd サービス例、監視・ログ設定、より詳細な .env.example）も作成します。どの部分を拡張するか教えてください。