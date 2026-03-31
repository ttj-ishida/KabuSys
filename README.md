# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ（KabuSys）。  
ETL、ニュースNLP、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ等のユーティリティを提供します。

## プロジェクト概要
- DuckDB をデータストアに用いた日本株データパイプラインと研究用ユーティリティ群。
- J-Quants API から株価・財務・マーケットカレンダーを差分取得して保存する ETL。
- RSS を収集してニュースを保存・前処理するニュースコレクタ。
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント解析（銘柄単位）とマクロセンチメントを組み合わせた市場レジーム判定。
- ファクター計算（モメンタム・バリュー・ボラティリティなど）、特徴量解析ユーティリティ。
- データ品質チェック（欠損・スパイク・重複・日付不整合）。
- 発注〜約定までをトレースする監査ログ（DuckDB スキーマ）。

パッケージのバージョンは `kabusys.__version__` で確認できます（現状 0.1.0）。

## 主な機能一覧
- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai/
  - ニュースセンチメント解析（score_news）
  - 市場レジーム判定（score_regime）
- research/
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config.py
  - 環境変数の読み込み・管理（自動でプロジェクトルートの .env / .env.local を読み込み）
  - settings オブジェクト経由で設定値を取得

## 必要環境（推奨）
- Python 3.10+
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全化）
- その他標準ライブラリ（urllib 等）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発インストール（プロジェクトルートで）
pip install -e .
```

※ package の配布形態により install コマンドは調整してください。

## 環境変数 / .env
パッケージは起動時にプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます（OS 環境変数優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment (development / paper_trading / live)、デフォルトは development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

config からは `from kabusys.config import settings` でアクセスできます。

## セットアップ手順（簡易）
1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成して環境変数を設定
5. DuckDB ファイルや必要ディレクトリ（data/ 等）を用意（多くはコードが自動作成）

例:
```bash
git clone <repo-url>
cd <repo-dir>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # または必要パッケージを個別にインストール
# .env を作成
cp .env.example .env
# .env に各トークン/キーを設定
```

## 基本的な使い方（コード例）
以下は主要な API を呼び出すためのサンプルです。実行前に環境変数を整えてください（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等）。

- DuckDB 接続の作成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（カレンダー取得 → 株価/財務取得 → 品質チェック）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {num_written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを組み合わせる）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# すでに作成済みの conn にスキーマを追加する場合:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- ファクター計算（研究用）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

## 自動 .env 読み込みの詳細
- 優先順位: OS 環境変数 > .env.local > .env
- プロジェクトルートの検出は `config._find_project_root()` により `.git` または `pyproject.toml` を基準に行います（現在の CWD に依存しない）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時などに利用）。

## 注意事項 / 設計上の留意点
- Look-ahead bias（未来情報参照）を避ける設計思想が随所に入っています（target_date 未満のデータのみ使用、ETL で fetched_at を記録 等）。
- OpenAI 呼び出しはリトライ・フォールバックロジックを持ち、API 失敗時は安全なデフォルト（0.0）を用いるようになっています。
- DuckDB に対する executemany の空リストバインド等、バージョン差分を考慮した実装上の注意が含まれています。
- ETL は冪等（idempotent）になるよう save_* 関数は ON CONFLICT DO UPDATE を使います。
- ニュース収集は SSRF 対策や XML の安全パース（defusedxml）を意識して実装されています。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント解析、score_news
    - regime_detector.py — 市場レジーム判定、score_regime
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / rate limit / auth）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集・前処理・保存
    - calendar_management.py — 市場カレンダー管理（営業日判定）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - research/*, ai/* などの補助モジュール

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

## テストとデバッグ
- OpenAI 呼び出しやネットワーク関連処理はモックしやすい形で実装されています（内部の _call_openai_api や _urlopen などを patch）。
- 自動 .env 読み込みを無効化してユニットテストを実行するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。

---

この README はコードベースの主要機能と使い方を簡潔にまとめたものです。詳細な API リファレンスや運用手順（cron / ワーカー設定、Slack 通知、kabu API 経由の実際の発注フロー等）は別途ドキュメント化してください。質問があればさらに具体的な利用例やコマンド例を追記します。