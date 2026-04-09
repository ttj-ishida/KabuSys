# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
データ取得（J-Quants）→ ETL → 品質チェック → 研究（ファクター計算）→ AI ニュース評価 → 監査ログ／発注用の基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群をまとめたライブラリです。

- J-Quants API からの差分取得と DuckDB への冪等保存（ETL）
- マーケットカレンダー管理・営業日ロジック
- ニュース収集・前処理（RSS）と LLM によるニュースセンチメント評価
- 市場レジーム判定（ETF の移動平均乖離 + マクロニュースセンチメント）
- ファクター計算（Momentum / Volatility / Value 等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal / order_request / executions）テーブルの初期化ユーティリティ
- 環境変数による設定管理（自動 .env ロード機能付き）

パッケージは src/kabusys 配下にモジュール化されています。

---

## 主な機能一覧

- data/
  - ETL: daily ETL 実行 run_daily_etl（差分取得・保存・品質チェック）
  - jquants_client: API 呼び出し、レートリミット・リトライ・トークン管理、DuckDB 保存関数
  - news_collector: RSS 取得・前処理・保存
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - quality: データ品質チェック関数群
  - audit: 監査ログ（DDL / 初期化 / DB 作成）
  - stats: z-score 正規化ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを LLM（gpt-4o-mini）で銘柄ごとにセンチメント評価し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA 乖離とマクロニュースを組合せた市場レジーム判定
- research/
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、サマリー等
- config
  - 環境変数読み込み・設定ラッパ（自動 .env / .env.local 読込、必要変数チェック）

その他、ユーティリティ・設計上のフォールバックやフェイルセーフが多く組み込まれています（例: API 失敗時のフォールバックスコア、DB 未登録時の曜日ベース判定等）。

---

## セットアップ手順

前提:
- Python 3.10+（typing の | などを利用）
- DuckDB、OpenAI SDK、defusedxml 等の依存あり

例（仮想環境推奨）:

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（プロジェクトの requirements.txt があればそちらを使用）
   例:
   ```bash
   pip install duckdb openai defusedxml
   # 追加で必要なパッケージがあれば適宜インストール
   ```

3. 開発インストール（任意）
   ```bash
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (LLM 機能を使う場合は必須)

---

## 重要な環境変数（主要）

設定ラッパ config.Settings で参照される主要環境変数一覧:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_FILL_MODE — Paper Trading のモックフィルモード（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- PID_FILE_PATH, KILL_FLAG_PATH — 監視関連のファイルパス
- KILL_FLAG_CLEAR_ON_START — "1" で起動時に kill フラグをクリア
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — DEBUG|INFO|...（デフォルト INFO）

自動 .env 読み込み:
- パッケージ import 時にプロジェクトルートを探索して `.env` → `.env.local` の順で読み込みます（OS 環境変数優先）。
- 無効化: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（例）

以下は代表的な利用例です。各関数は duckdb 接続を受け取り DB 操作を行います。

1) DuckDB 接続作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（差分取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース RSS を取得（単体）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

4) ニュースを LLM で銘柄ごとにスコア付けして ai_scores テーブルへ書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)
```

5) 市場レジーム判定（regime_score を market_regime テーブルに書き込む）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

6) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(":memory:")  # or str(settings.duckdb_path)
# または既存 conn に対してスキーマを追加:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注意点:
- LLM 呼び出しは OpenAI SDK を使います。APIキーは OPENAI_API_KEY か関数引数で渡してください。
- 各処理はルックアヘッドバイアス対策（target_date を明示的に渡す等）を実装しています。テスト／バックテスト時は target_date を指定してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメントスコアリング
    - regime_detector.py         — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     — マーケットカレンダー管理
    - news_collector.py          — RSS 収集 + 前処理
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログスキーマ / 初期化
    - stats.py                   — zscore_normalize 等
    - etl.py                     — ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Value / Volatility
    - feature_exploration.py     — forward returns / IC / summary / rank
  - ai/, data/, research/ 以下にさらに細かい実装が含まれます

---

## 開発上のメモ / 設計上の注意点

- Look-ahead バイアス防止:
  - 多くの関数は内部で datetime.today()/date.today() を参照せず、必ず target_date を引数で受け取る設計です。バックテストでは target_date を明示してください。
- フェイルセーフ:
  - LLM/API の失敗は例外で即停止させず、フォールバック値（例: macro_sentiment=0.0）で継続する箇所が多くあります。
- DuckDB:
  - 一部の処理は DuckDB の executemany に関する注意（空リスト不可）や SQL の互換性配慮があります。
- テスト容易性:
  - LLM 呼び出し等は内部の _call_openai_api を patch して差し替え可能です（ユニットテスト向け）。

---

## よくあるコマンド / ワークフロー

- ETL を cron / Airflow 等から日次で実行する:
  - Python スクリプトで run_daily_etl を呼ぶ（target_date を明示するのが安全）。
- LLM バッチ実行:
  - news_nlp.score_news を ETL 直後か、別バッチで定期実行。
- 研究用途:
  - research.calc_momentum / calc_volatility 等で特徴量を生成 → zscore_normalize → feature_exploration.calc_ic で評価。

---

## 問い合わせ / 貢献

README に書かれている使い方で不明点があれば、該当モジュールの docstring（各ファイル冒頭）をご参照ください。設計意図・インターフェースは docstring に詳述されています。プルリクエスト歓迎します。

---

以上がこのコードベースの README.md（概要・セットアップ・使い方・ディレクトリ説明）です。必要であればサンプル .env.example や requirements.txt、簡単な起動スクリプト（run_etl.py など）のテンプレートも作成します。どちらがよいですか？