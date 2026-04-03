# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
ETL・ニュース収集・ニュースNLP（LLMを用いた銘柄センチメント）・市場レジーム判定・品質チェック・監査ログの初期化など、投資ストラテジーの研究〜運用に必要な機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような目的で設計されたモジュール群です。

- J-Quants API からデータを差分取得して DuckDB に保存する ETL（株価、財務、カレンダー等）
- RSS ベースのニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（銘柄単位）
- ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成した市場レジーム判定
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用テーブルの初期化ユーティリティ
- データ基盤・リサーチ用のファクター計算ユーティリティ（モメンタム／バリュー／ボラティリティ等）

設計上の共通方針として「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API障害時はスキップして継続）」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch/save 各種）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得、前処理、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（監査スキーマの初期化、専用 DB 初期化ユーティリティ）
  - 統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP（score_news: LLM による銘柄別スコアリング）
  - レジーム判定（score_regime: ETF MA200 乖離 + マクロニュースの合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・IC / forward return 計算等

---

## 依存関係

主な Python ライブラリ（例）:

- Python 3.9+
- duckdb
- openai
- defusedxml

開発環境ではこれらをインストールしてください。例:

```bash
pip install duckdb openai defusedxml
```

（プロジェクト配布に requirements.txt / pyproject.toml があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリへ配置
2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
4. 環境変数を設定（.env を作成するか OS 環境変数に設定）
   - 推奨: プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
5. DuckDB ファイル格納ディレクトリ（デフォルト `data/`）等を用意

---

## 環境変数（主なもの）

以下はコードで参照される主要な環境変数例です。`.env.example` をプロジェクトに用意してそこからコピーする想定です。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（注文実行モジュール等で使用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視関連
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_ENV: development / paper_trading / live

自動環境読み込みを一時的に無効化する:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（代表的な使用例）

下記は各主要ユースケースの最小例です。実際はログ設定や例外ハンドリングを追加してください。

- DuckDB 接続の作成例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- ETL（1日分）を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（ai.news_nlp.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ai.regime_detector.score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（専用 DuckDB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

- 市場カレンダーの夜間更新ジョブ（差分取得）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"保存レコード数: {saved}")
```

---

## ディレクトリ構成（主なファイル・モジュール）

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの LLM スコアリング（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch/save）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— 市場カレンダー管理
    - news_collector.py     — RSS ニュース収集（SSRF対策・前処理）
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログ DDL と初期化ユーティリティ
    - etl.py                — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— forward returns / IC / factor summary

---

## 開発・運用メモ

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト中や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。
- OpenAI 呼び出しは retry/backoff と JSON モード（厳密な JSON 出力期待）を前提としています。APIエラー時はフェイルセーフとしてスコア 0.0（中立）で継続する設計です。
- J-Quants API 呼び出しは内部でレート制御とトークン自動リフレッシュを実装しています。`JQUANTS_REFRESH_TOKEN` の値は必須です。
- DuckDB を利用しているため、大量データ処理のパフォーマンスやファイルロックに注意してください。
- ニュース収集は SSRF 対策・サイズチェック・トラッキングパラメータ除去を実装しています。

---

この README はコードベースの概要説明・最小限の利用方法を示したものです。各モジュールの詳細な使い方やパラメータはソースの docstring を参照してください。必要であれば、サンプルの .env.example・運用手順（cron / systemd）・ロギング設定例等も追加できます。