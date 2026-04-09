# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ

このリポジトリは「KabuSys」と呼ばれる日本株向けの自動売買 & データ基盤用 Python モジュール群です。データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）、研究用ファクター計算などを含むコンポーネント群を提供します。

---

## 主要機能（概要）

- データ取得 / ETL
  - J-Quants API から株価（日足）、財務データ、マーケットカレンダーを差分取得して DuckDB に保存（冪等）
  - 差分更新 / バックフィル / 品質チェックを備えた日次 ETL パイプライン

- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合（未来日・非営業日）の検出

- ニュース収集・NLP
  - RSS からニュースを収集し raw_news に保存
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメント算出（ai_scores への書き込み）
  - マクロニュースを用いた市場レジーム（bull/neutral/bear）判定

- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー系のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z-score 正規化

- 監査ログ（Audit）
  - シグナル → 発注 → 約定まで UUID を用いたトレーサビリティ用テーブルを DuckDB に初期化・管理

- 設定管理
  - .env や環境変数をサポート。プロジェクトルートの .env/.env.local を自動読み込み（必要に応じて無効化可能）

---

## 必要条件 / 依存パッケージ

主に以下のパッケージを利用します（実行環境に合わせて最新バージョンを指定してください）:

- Python 3.10+
- duckdb
- openai
- defusedxml

（ネットワーク/HTTP は標準ライブラリ urllib を使用。その他標準ライブラリ多数使用）

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発時: pip install -e .
```

パッケージ管理はプロジェクトの pyproject.toml / requirements.txt を参照してください。

---

## 環境変数（主なもの）

config.Settings で参照される主要な環境変数は次の通りです（デフォルトや必須性はコード内コメントを参照してください）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI 呼び出し時) — OpenAI API キー
- KABU_API_PASSWORD — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading のモック約定モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 実行監視関連
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 環境 (development|paper_trading|live)。settings.is_live / is_paper / is_dev で判定
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

自動 .env 読み込み:
- プロジェクトルートに `.env` / `.env.local` があれば自動読み込みします（読み込み条件は config モジュール参照）。
- 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 読み込み優先度: OS 環境変数 > .env.local > .env

例の .env（最小）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存ライブラリをインストール
   ```
   pip install duckdb openai defusedxml
   # 開発インストール（パッケージ化されている場合）
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートしてください。
   - 必須: JQUANTS_REFRESH_TOKEN（ETL）、OPENAI_API_KEY（AI 機能を使う場合）

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下は基本的な Python スクリプトからの呼び出し例です。必要に応じて例を改変して利用してください。

- DuckDB 接続を作って日次 ETL を実行する（run_daily_etl）:
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイル指定は settings.duckdb_path を使うのが推奨
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む（score_news）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数に設定されている前提
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

- 市場レジームを判定して market_regime に書き込む（score_regime）:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を別 DB にして監査用 DB を分けることも可能
conn = init_audit_db(settings.duckdb_path)
# 以後 conn に対して order_requests 等のテーブルが利用可能
```

- RSS を収集して raw_news に保存する（news_collector の実行は独自ラッパースクリプト推奨。fetch_rss を利用して記事を取得し保存ロジックを実装してください）

---

## 主な API / モジュール説明

- kabusys.config
  - Settings クラス: アプリ設定を環境変数から取得
  - 自動 .env ロードを実装（プロジェクトルート検出）

- kabusys.data
  - jquants_client: J-Quants API の取得・保存（fetch_* / save_*）
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / ETLResult
  - quality: データ品質チェック（check_missing_data / check_spike / ...）
  - news_collector: RSS 取得 / 前処理 / 保存ユーティリティ
  - calendar_management: 市場カレンダー管理・営業日判定・calendar_update_job
  - audit: 監査ログテーブルの DDL と初期化ユーティリティ
  - stats: zscore_normalize 等の汎用統計関数

- kabusys.ai
  - news_nlp.score_news: ニュースをまとめて OpenAI に投げ、銘柄別スコアを ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースを合成して market_regime に保存

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats の zscore_normalize との連携

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・モジュール構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - stats.py
    - etl.py (ETLResult エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージは研究用の指標・解析ユーティリティ群

（実際のファイルは上記以外にも多く含まれるため、細かな実装は該当ファイルを参照してください）

---

## 運用上の注意 / 設計上のポイント

- Look-ahead bias 回避: 多くの関数は内部で date.today() を直接参照せず、target_date を明示的に渡す設計になっています。バックテスト時は明示的な日付を渡してください。
- ETL の冪等性: DuckDB への保存は ON CONFLICT / INSERT ... DO UPDATE を使って冪等に実装されています。
- API リトライとレート制御: J-Quants の呼び出しは固定間隔スロットリングと指数バックオフ＋401リフレッシュ対応を備えています。
- AI 呼び出しのフェイルセーフ: OpenAI 呼び出し失敗時はスコアを 0 にフォールバックする等、処理の継続性を重視しています。
- セキュリティ: news_collector は SSRF 対策、defusedxml を使った XML パース、安全な URL 正規化等を実装しています。

---

## 追加情報 / 貢献

- バグ報告や機能追加は issue を立ててください。
- データスキーマ（raw_prices / raw_financials / market_calendar / ai_scores / market_regime / audit テーブル等）に関する変更は互換性に注意して行ってください（特に監査ログは削除しない前提）。

---

README の作成にあたっては主要なモジュールの docstring とコード構造を元に要点をまとめました。実運用での具体的な設定や DB スキーマの詳細は各モジュールの実装ファイル（src/kabusys/data/*.py など）をご参照ください。必要なら運用手順書（デプロイ、cron/ジョブ設定、監視）やサンプルスクリプトも作成します。どの部分を優先してドキュメント化するか指示してください。