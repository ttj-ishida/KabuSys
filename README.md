# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB を用いたデータプラットフォーム、J-Quants API 経由の ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（オーダー／約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・因子計算・ニュースセンチメント解析・市場レジーム判定・監査ログを統合するための Python モジュール群です。  
主に以下の用途を想定しています。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュースの収集と OpenAI を用いた銘柄ごとのセンチメントスコア付与
- ETF（1321）を用いたテクニカル指標とマクロニュースを組み合わせた市場レジーム判定
- 研究用のファクター計算（モメンタム、ボラティリティ、バリュー等）・統計ユーティリティ
- 発注・約定を追跡する監査（audit）テーブルの初期化ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計方針として「ルックアヘッドバイアスの排除」「API 呼び出しのフェイルセーフ化」「DuckDB 上での冪等保存」「外部依存を最小化した実装」が採用されています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS を安全に取得・正規化して raw_news に保存）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores に保存）
  - 市場レジーム判定（score_regime: ETF MA とマクロ記事の LLM スコアを合成して market_regime に保存）
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込み（.env 自動ロード、必須値チェック）
- audit / execution / strategy 等のための基盤（監査・発注ロギング等の DDL 定義等）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨
- DuckDB を使用（ローカルファイルまたはインメモリ）

1. リポジトリをクローンして開発環境を作成

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   ```

2. 必要なパッケージをインストール

   代表的な依存例（プロジェクトに requirements.txt/pyproject があればそちらを使用してください）:

   ```
   pip install duckdb openai defusedxml
   ```

   openai: LLM 呼び出し用  
   defusedxml: RSS パースで XML 攻撃を防ぐ

3. パッケージを editable インストール（開発用）

   ```
   pip install -e .
   ```

4. データディレクトリ等を作成（デフォルトの DB パスを使う場合）

   ```
   mkdir -p data
   ```

5. 環境変数（または .env）を設定

   主要な環境変数は下記参照。パッケージは起動時にプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数を優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（よく使う関数の実行例）

以下は Python スクリプト / REPL での実行例です。DuckDB 接続には `duckdb.connect(path)` を利用してください。

- ETL（日次パイプライン）を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコア付け（OpenAI が必要）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written codes:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA + マクロニュース）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査用 DuckDB の初期化（監査 DB 専用ファイルを作る）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルとインデックスが作成されます
```

- カレンダー更新ジョブを単体で実行

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- ファクター計算・研究ユーティリティ

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
```

注意:
- OpenAI を使う関数は `OPENAI_API_KEY` 環境変数を参照します。関数呼び出し時に `api_key=` を渡すことで明示的に上書きできます。
- 多くの関数は DuckDB の特定テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime, market_calendar など）を前提とします。ETL を事前に実行してデータを揃えてください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用のリフレッシュトークン
- OPENAI_API_KEY (必須 for AI) — OpenAI API キー（score_news / regime_detector）
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development/paper_trading/live)。不正値はエラー
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要なモジュール構成:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 自動ロード、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM スコア付与（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理・検索
    - news_collector.py      — RSS 収集・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化・init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai, research, data 以外にも strategy / execution / monitoring 用の名前空間が定義されています（将来的な拡張を想定）

---

## 運用上の注意・ベストプラクティス

- ルックアヘッドバイアス防止:
  - コード内で日時判定に date.today()/datetime.today() をむやみに参照しない設計です。ETL / スコアリングでは引数で target_date を渡して実行してください。
- OpenAI / J-Quants の API 呼び出しはレートリミット／リトライ処理を含みますが、実運用では別途監視とレート制御を行ってください。
- DuckDB のスキーマは ETL と audit モジュールで前提されているテーブルを作成する必要があります。audit は init_audit_db / init_audit_schema を使って初期化できます。
- .env に秘密情報を置く場合はアクセス管理に注意してください（例: Git にコミットしない）。
- テスト時は環境変数自動ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると便利です。
- news_collector はネットワーク・SSRF・XML の脅威を考慮した実装になっていますが、外部 RSS を扱う際は取得先の信頼性を確認してください。

---

## 貢献 / 開発

- バグ修正、テスト追加、機能改善は歓迎します。PR の際はユニットテストを添えてください。
- モジュール間の結合を低く保つ設計（例: ai.regime_detector は news_nlp の内部 API を直接呼ばない）を維持してください。

---

以上がプロジェクトの README です。必要であれば「.env.example の完全なテンプレート」や「初期スキーマ作成用の SQL」「よく使う CLI ラッパー例」など、さらに具体的なドキュメントを追加しますか？