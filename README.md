# KabuSys

日本株自動売買プラットフォームのコードベース（ライブラリ部分）。  
データ収集（J-Quants / RSS）、データ品質チェック、ETL、AI（ニュースセンチメント/市場レジーム）、リサーチ用ファクター計算、監査ログ（発注→約定トレース）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株向けのデータ基盤とリサーチ／自動売買に必要な共通コンポーネント群を集めたライブラリです。主な目的は次の通りです。

- J-Quants API からの株価・財務・カレンダー等の差分取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントとマクロセンチメント評価
- ETF（1321）200日移動平均等に基づく市場レジーム判定
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリューなど）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 発注／約定の監査ログ用スキーマと初期化ユーティリティ
- 環境変数・設定の集中管理

このリポジトリはバックテスト／リサーチ環境および実運用の基盤処理に使える設計方針（ルックアヘッドバイアス対策、冪等処理、フェイルセーフなど）が反映されています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須変数の取得と validation
- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes 等の DuckDB への冪等保存
  - レートリミット制御、リトライ、トークン自動リフレッシュ
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー→株価→財務→品質チェックを順に実行
  - 個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETLResult クラスで結果を集約
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 防止、前処理、raw_news への冪等保存（設計）
- データ品質チェック（kabusys.data.quality）
  - 欠損 / スパイク / 重複 / 日付整合性のチェック
  - QualityIssue を返す
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化
  - init_audit_schema / init_audit_db
- AI (kabusys.ai)
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に書込み
  - regime_detector.score_regime: ETF 1321 の MA とマクロセンチメントを合成して daily market_regime に書込み
- リサーチ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / zscore_normalize

---

## 必要条件・依存パッケージ

- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

インストール例（仮に pip を使用する場合）:

```bash
python -m pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発時はリポジトリルートで:
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

---

## 環境変数（.env）と設定

kabusys.config.Settings が環境変数を読み込みます。自動ロードの優先順は:

OS 環境変数 > .env.local > .env

プロジェクトルートは __file__ の親ディレクトリから .git または pyproject.toml を探索して決定します。自動ロードを無効化するには:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース (デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG/INFO/...
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector は引数で上書き可能）

例 (.env):

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに .env を作成して必要な環境変数を設定
5. DuckDB ファイル用ディレクトリを作成（自動で作られることが多いですが念のため）
6. 監査DBの初期化（必要に応じて）

例:

```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db
import duckdb

# ファイルで初期化する例
conn = init_audit_db(str(settings.duckdb_path))
# あるいは既存接続にスキーマを追加
# conn = duckdb.connect(str(settings.duckdb_path))
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn)
```

---

## 使い方（代表的なユースケース）

- 日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリング（OpenAI API キーは環境変数か api_key 引数で指定）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- ファクター計算 / リサーチ機能

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

- 監査ログスキーマの初期化（既存 DuckDB 接続へ）

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 開発・テスト向けメモ

- OpenAI 呼び出しやネットワーク I/O はユニットテストで差し替え（mock.patch）されています。news_nlp._call_openai_api や regime_detector._call_openai_api、news_collector._urlopen 等をモック可能です。
- 自動で .env を読み込む挙動は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用）。
- モジュールはルックアヘッドバイアスに配慮して設計されています（date.today()/datetime.today() 参照を直接使わない等）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下）

- __init__.py
  - パッケージのバージョンとエクスポート定義
- config.py
  - 環境変数の読み込み・Settings 定義
- ai/
  - __init__.py (score_news をエクスポート)
  - news_nlp.py — ニュースセンチメント解析（OpenAI）
  - regime_detector.py — マクロセンチメント + 1321 MA による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集と前処理
  - quality.py — データ品質チェック
  - stats.py — zscore_normalize 等の共通統計ユーティリティ
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - audit.py — 発注/約定監査スキーマの DDL と初期化
- research/
  - __init__.py
  - factor_research.py — モメンタム/ボラティリティ/バリュー等
  - feature_exploration.py — 将来リターン、IC、統計サマリー、rank

（この README は上記ファイル群の概要を抜粋して記載しています）

---

## 注意事項

- 本ライブラリの一部は外部 API（J-Quants, OpenAI, RSS）に依存します。API キーやトークンは適切に管理してください。
- DuckDB スキーマ（raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / market_regime 等）は外部のスキーマ初期化スクリプトやマイグレーションなしでは存在しない場合があります。ETL や save_* 関数は既存テーブルを前提とするため、スキーマ作成は別途行ってください（data.schema モジュール等を用意している場合はそれを利用）。
- 実口座での発注／自動売買を行う場合は十分な検証とリスク管理を行ってください（このコードは基盤を提供するものであり、デフォルト状態での実運用を推奨するものではありません）。

---

必要であれば README に実際のテーブルスキーマ、例の .env.example ファイル全文、または各モジュールのより詳しい API 使用例（関数引数／戻り値の詳細）を追加できます。どの部分を詳述しましょうか？