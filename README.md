# KabuSys

日本株のデータプラットフォームと自動売買に向けたユーティリティ群をまとめたライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集／NLP による銘柄スコアリング、リサーチ用ファクター計算、監査ログ（発注〜約定トレーサビリティ）、マーケットカレンダー管理などを提供します。

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価（日足）・財務指標・マーケットカレンダーの差分取得と DuckDB への冪等保存
  - ETL 結果を表す `ETLResult` を提供

- ニュース収集 / NLP
  - RSS からニュースを収集して前処理し `raw_news` / `news_symbols` テーブルへ保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント評価（`score_news`）
  - マクロニュースと ETF（1321）の MA200 乖離を合成した市場レジーム判定（`score_regime`）

- リサーチ支援
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェックをまとめて実行

- マーケットカレンダー管理
  - JPX カレンダーに基づく営業日判定、次/前営業日取得、期間内営業日取得、夜間バッチ更新ジョブ

- 監査ログ（Audit）
  - signal → order_request → execution のトレーサビリティ用テーブル定義・初期化（DuckDB）

---

## 必要条件 / 依存関係

- Python 3.10 以上（型注釈に | を使用）
- 必要なパッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# パッケージをプロジェクトとしてインストールする場合
pip install -e .
```

（プロジェクト配布時は pyproject.toml / requirements.txt を参照してください）

---

## 環境変数 (.env)

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client で利用）
- KABU_API_PASSWORD     : kabuステーション API 用パスワード（発注系で使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
- OPENAI_API_KEY        : OpenAI API キー（AI モジュール）

任意 / デフォルトあり:
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite ファイルパス（モニタリング用、デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（最小構成）

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成して必要な値を設定
5. DuckDB 用ディレクトリを作成（例: data/）
6. 必要に応じて監査DB初期化などを行う

---

## 使い方（主要 API の例）

以下は簡単な利用例です。実行する前に環境変数（特に OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続を作成して ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを評価して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written:", written)
```

- 市場レジーム判定（ETF 1321 MA200 とマクロセンチメントの合成）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 研究用ファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))

# Zスコア正規化
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

- 監査ログ（audit）テーブルの初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
# conn を使って audit テーブルにアクセス可能
```

- カレンダー関係のユーティリティ:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
print("trading days in range:", get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

注意:
- AI 系機能は OpenAI API（gpt-4o-mini）を使用します。API 呼び出し回数に伴う費用・レート制限に注意してください。
- AI 呼び出しはレスポンス検証・リトライ・フォールバックを備えていますが、実際の運用ではエラーハンドリングを適切に行ってください。

---

## ディレクトリ構成（要約）

プロジェクトは src/kabusys 以下に主要モジュールを配置しています。主なファイル／モジュール:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント評価（銘柄別）
    - regime_detector.py      — 市場レジーム判定（MA + マクロ）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ロジック
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py       — RSS ニュース収集
    - calendar_management.py  — マーケットカレンダー管理
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                — 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - monitoring/ (パッケージ一覧に含まれる想定の監視モジュール)*
  - execution/, strategy/, monitoring/ (パッケージとして __all__ に記載。詳細実装はここに)

(*) 実際のファイル構成はリポジトリの状態に応じて変わります。上は主要モジュールの概観です。

---

## 注意点 / 設計方針（抜粋）

- バックテスト時のルックアヘッドバイアス回避に配慮し、関数内部で datetime.today() / date.today() を安易に参照しない設計になっています（target_date を明示して呼ぶことを想定）。
- DuckDB を主要なデータ保存先として利用。保存操作は可能な限り冪等（ON CONFLICT DO UPDATE）にしています。
- API 呼び出しはリトライ・バックオフ・レート制御・トークン自動リフレッシュ等を備えています。
- ニュース収集モジュールは SSRF / XML 攻撃 / Gzip bomb 等へ対策を実装しています。

---

必要であれば次の内容も追加できます:
- 開発環境でのテスト実行方法（ユニットテスト / CI）
- スキーマ定義（DuckDB の CREATE TABLE DDL）
- よくあるトラブルシュート（API エラー、認証エラーなど）

追加で加えたいセクションや詳細があれば教えてください。