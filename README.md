# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買 / 研究ユーティリティ群を提供するライブラリです。J-Quants や各種 RSS / OpenAI と連携してデータ収集・ETL・品質チェック・特徴量計算・ニュースセンチメント解析・市場レジーム判定・監査ログの整備などを行える設計になっています。

本 README はプロジェクトの概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

- 目的: 日本株の自動売買・リサーチを支援するためのデータ基盤および解析モジュール群。
- 特徴:
  - J-Quants API からの差分 ETL（株価、財務、カレンダーなど）
  - DuckDB を使ったローカルデータストレージ（冪等保存）
  - ニュースの収集・前処理・LLM によるセンチメント分析（gpt-4o-mini を想定）
  - 市場レジーム判定（ETF MA とマクロニュースの組合せ）
  - ファクター計算、将来リターン、IC（研究ユーティリティ）
  - データ品質チェック（欠損・スパイク・重複・日付不整合など）
  - 約定まで追跡可能な監査ログスキーマ（監査テーブル初期化ユーティリティ）
  - 設定は環境変数 / .env ファイルで管理（自動ロード機構あり）

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 設定オブジェクト `kabusys.config.settings`
- データ取得・ETL
  - J-Quants API クライアント（認証・ページネーション・レート制御・再試行）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - DuckDB への冪等保存（ON CONFLICT による上書き）
- ニュース収集・NLP
  - RSS 収集（追跡パラメータの除去、SSRF 対策、受信サイズ制限）
  - ニュースを銘柄に紐付けて保存
  - OpenAI を用いた銘柄別ニュースセンチメント（news_nlp.score_news）
  - マクロニュースとETF MA を組み合わせた市場レジーム判定（ai.regime_detector.score_regime）
- 研究ユーティリティ
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（将来リターン、IC、統計サマリー、ランク変換、Zスコア正規化）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合検出（quality.run_all_checks）
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
  - 監査用 DuckDB 初期化（init_audit_db）

設計方針として「ルックアヘッドバイアスを避ける」「冪等性」「フェイルセーフ（API 失敗時の継続）」を重視しています。

---

## セットアップ手順

前提:
- Python 3.10 以降（| 型アノテーションや union 演算子を使用しているため）
- ネットワーク接続（J-Quants, OpenAI, RSS）

1. リポジトリをクローン / 配布パッケージを配置
2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要なパッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトで requirements.txt がある場合はそれを使用）
4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（デフォルト）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
5. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（任意、デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（任意、デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視設定）
   - KABUSYS_ENV: development | paper_trading | live（任意、デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（任意）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等で利用）
6. (任意) DuckDB スキーマ初期化
   - スキーマ定義はプロジェクト内で別途提供されている想定です。audit 用 DB を初期化する例は下記参照。

サンプル .env（抜粋）
    JQUANTS_REFRESH_TOKEN=xxxxx
    OPENAI_API_KEY=sk-xxxxx
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

---

## 使い方（基本例）

以下はライブラリの代表的な使い方のサンプルコードです。実行は Python スクリプトやジョブランナーから行います。

- DuckDB 接続の作成（設定からパス取得）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（株価 / 財務 / カレンダー + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai によるスコア付け）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 を使った MA とマクロニュースの組合せ）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は必要なテーブルを作成し、UTC タイムゾーンを設定します
```

- J-Quants クライアントの直接呼び出し（例: 上場銘柄情報取得）
```python
from kabusys.data.jquants_client import fetch_listed_info
from datetime import date

records = fetch_listed_info(date_=date(2026, 3, 1))
print(len(records))
```

注意点:
- OpenAI API を使う機能（news_nlp, regime_detector）は API キーが必要です。api_key 引数で注入可能ですが、環境変数 OPENAI_API_KEY を設定しておくのが便利です。
- run_daily_etl は内部で calendar ETL を先に実行してから prices / financials ETL を行い、最後に品質チェックを実行します。
- 多くの I/O 操作（API 呼出し・DB 書き込み）に対してリトライやフェイルセーフが組み込まれていますが、ネットワーク/認証エラーなどはログを確認してください。

---

## 自動 .env ロードについて

- パッケージ初期化時点でプロジェクトルート（.git または pyproject.toml を基準）を探索し、ルートにある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local（override=True） > .env（override=False）
- 自動ロードを無効にするには環境変数を設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env ファイルのパースはコメント・クォート・エクスポート形式に対応しており、一般的な .env フォーマットをサポートします。

---

## ディレクトリ構成（抜粋）

ソースルートは `src/kabusys` 配下に配置されています。主要ファイル / モジュールは次のとおりです。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          # ニュースの LLM ベーススコアリング
    - regime_detector.py   # マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント（取得 + 保存）
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - etl.py               # ETL 結果クラス再エクスポート
    - news_collector.py    # RSS 収集と前処理
    - quality.py           # データ品質チェック
    - calendar_management.py # マーケットカレンダー管理（営業日判定等）
    - stats.py             # 統計ユーティリティ（zscore_normalize 等）
    - audit.py             # 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py   # Momentum / Value / Volatility 等の計算
    - feature_exploration.py # 将来リターン / IC / 統計サマリー 等

各モジュールは単体でテスト・呼び出し可能な関数群を公開しており、ETL / 解析 / 監視 / 実行の各レイヤーで再利用できます。

---

## 設計上の注意点

- Look-ahead バイアス回避:
  - 多くの関数は把握可能な期間でのみデータを参照するよう設計されています（例: target_date 未満のみ使用）。
- 冪等性:
  - DuckDB への保存は ON CONFLICT による上書きを行います（重複や再実行に強い）。
- フェイルセーフ:
  - 外部 API（OpenAI や J-Quants）での一時エラーはリトライやフォールバック値 (macro_sentiment=0.0 など) により処理継続します。
- セキュリティ:
  - RSS 収集は SSRF 対策、受信サイズ制限、XML パースの安全実装（defusedxml）を行っています。

---

## 追加情報 / 連絡先

- 本 README はコードベースの説明を目的としており、運用設定（cron や systemd、監視アラートなど）は各プロジェクトの運用ルールに従って構築してください。
- 具体的な CLI や Web UI、CI 設定はこの README に含まれていません。必要に応じて util スクリプトやジョブランナーを追加してください。

---

README の内容やサンプル・環境変数の一覧などをプロジェクト固有の運用ルールに合わせてカスタマイズしたい場合は、必要なポイント（例: 必須 env の追加、サンプル .env ファイル）を教えてください。README をそれに合わせて更新します。