# KabuSys

日本株向けのデータ基盤＋リサーチ＋自動売買支援ライブラリです。  
DuckDB を用いたローカルデータストア、J-Quants / RSS / OpenAI を組み合わせた ETL / ニュース NLP / 市場レジーム判定 / 監査ログ機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL（DuckDB に永続化）
- RSS ニュースの収集と LLM による銘柄センチメント評価（ai_score）
- マクロセンチメントと ETF MA を組み合わせた市場レジーム判定
- 研究用ファクター計算・統計分析ユーティリティ
- 発注〜約定までを追跡する監査ログスキーマ（監査用 DuckDB）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の共通点として、Look-ahead バイアス回避を重視しており、内部実装は日時参照を直接行わない（外部から target_date を与える）ようになっています。

---

## 主な機能一覧

- データ取得/保存
  - J-Quants からの株価日足 / 財務 / 上場銘柄 / JPX カレンダー取得（ページネーション・レート制御・リトライ）
  - DuckDB への冪等的な保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - run_daily_etl：カレンダー・株価・財務の差分取得 + 品質チェック
  - 個別ジョブ：run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース関連
  - RSS 収集（SSRF 対策、トラッキング除去、前処理）
  - LLM（gpt-4o-mini）での銘柄センチメントスコア付与（score_news）
  - ニュースウィンドウ計算（JST 基準）
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュースの LLM スコアを合成（score_regime）
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン / IC / 統計サマリー・Z スコア正規化
- データ品質チェック（quality）
  - 欠損 / スパイク / 重複 / 日付不整合チェック
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の DDL と初期化ユーティリティ

---

## 要求環境・依存ライブラリ

最低限必要なもの（実行環境に合わせて調整してください）:

- Python 3.9+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, datetime, json, logging など）

インストール例:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクトで requirements.txt を用意する場合はそちらを参照してください）

---

## 環境変数 / .env

パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると `.env` と `.env.local` を自動読み込みします。読み込み順（優先度）は:

1. OS 環境変数
2. .env.local（.env を上書き）
3. .env（基本設定）

自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 環境 ('development'|'paper_trading'|'live')（デフォルト: development）
- LOG_LEVEL             : ログレベル ('DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL')

簡単な .env の例:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして venv を作成・有効化
2. 必要なパッケージをインストール（上記参照）
3. プロジェクトルートに .env を作成して必要なキーを設定
4. データディレクトリを作成（必要なら）

例:

```
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
mkdir -p data
# .env を作成して設定
```

---

## 使い方（主要な例）

以下は Python REPL / スクリプト内での簡単な利用例です。例では DuckDB 接続を直接渡して操作します。

共通準備:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL を実行（カレンダー・株価・財務・品質チェック）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースの NLP スコア付与（score_news）:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"スコア書込み銘柄数: {n_written}")
```

市場レジーム判定（score_regime）:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

監査用 DB の初期化（監査専用ファイル）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# この audit_conn に対して監査テーブルが作成される
```

個別 ETL ジョブ呼び出し例:

```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from datetime import date

run_prices_etl(conn, target_date=date(2026,3,20))
run_financials_etl(conn, target_date=date(2026,3,20))
run_calendar_etl(conn, target_date=date(2026,3,20))
```

品質チェック実行:

```python
from kabusys.data.quality import run_all_checks
from datetime import date

issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意:
- OpenAI API 呼び出しはネットワーク/課金を伴います。テスト時は該当モジュールの _call_openai_api をモックする想定です。
- J-Quants API とのやり取りはレート制御・再試行が入っていますが、適切なトークンとネットワーク環境が必要です。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージ情報・公開モジュール一覧
- config.py
  - 環境変数読み込み・Settings（設定プロパティ）
- ai/
  - news_nlp.py : ニュースの LLM によるスコアリング（score_news）
  - regime_detector.py : 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py : ETL パイプライン run_daily_etl 等、ETLResult
  - jquants_client.py : J-Quants API クライアント（fetch / save 関数）
  - news_collector.py : RSS 収集、前処理、保存ロジック
  - calendar_management.py : 市場カレンダーの判定・更新ジョブ
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - quality.py : データ品質チェック
  - audit.py : 監査テーブル DDL と初期化
  - etl.py : ETLResult の再エクスポート
- research/
  - __init__.py : 研究用ユーティリティのエクスポート
  - factor_research.py : momentum / value / volatility の計算
  - feature_exploration.py : 将来リターン/IC/統計サマリー等
- monitoring / execution / strategy / etc.
  - （README に含めたコードベースの他モジュール名が __all__ に含まれていますが、
     実装は個別ファイルに分かれます）

---

## 実運用に関する注意点

- KABUSYS_ENV を 'live' に設定すると実取引向けのモードとなる可能性があるため、設定は慎重に行ってください（本コードでは is_live プロパティなどで参照）。
- OpenAI / J-Quants など外部 API のキーは漏洩に注意し、CI に平文で置かないでください。
- ETL は差分更新・バックフィルを行いますが、最初の起動時は大量のデータ取得が発生します。レート制限とストレージに注意してください。
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、自前で必要な env を注入してください。
- DuckDB のバージョン差異により executemany の挙動等が異なるケースがあります（コード内に互換処理あり）。

---

README はここまでです。必要なら以下も提供できます:
- .env.example のテンプレート
- Docker / CI 用の起動例
- よく使う SQL スキーマ（raw_prices, raw_financials, ai_scores, market_regime 等）の抜粋

どれを追加しますか？