# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、ETL・品質チェック、監査ログ（発注/約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本市場向けに設計された「データプラットフォーム + 自動売買補助」ライブラリです。  
主な目的は以下のとおりです。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得・保存する ETL
- RSS によるニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析と市場レジーム判定
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティなど）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定の監査ログ（監査テーブル初期化・DB 保存）
- DuckDB ベースのローカルデータ管理

設計上の特徴として、バックテスト時のルックアヘッドバイアス防止、API リトライ／レートリミット対策、DB への冪等保存が意識されています。

---

## 主な機能一覧

- data パッケージ
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - マーケットカレンダー管理（is_trading_day, next_trading_day, get_trading_days 等）
  - ニュース収集（RSS -> raw_news、SSRF 対策、正規化）
  - 品質チェック（missing_data / spike / duplicates / date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai パッケージ
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime） — ETF 1321 の MA200 乖離 + マクロ記事センチメントを組み合わせ
- research パッケージ
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- config モジュール
  - 環境変数 / .env 自動読み込み（プロジェクトルート検出）
  - 各種必須設定（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）をプロパティで提供

---

## 前提・依存ライブラリ（例）

最低限必要となる主なパッケージ（バージョンは利用者側で適宜指定してください）:

- python 3.10+（型アノテーションの union 表記等を使用）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

インストール例（最低限）:

pip install duckdb openai defusedxml

※プロジェクトによっては追加の依存が必要になる場合があります。requirements.txt がある場合はそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローン（例）:
   git clone <repo-url>
2. 仮想環境を作成して有効化:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール:
   pip install duckdb openai defusedxml
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数設定:
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動でロードされます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- SLACK_BOT_TOKEN — Slack 通知等で必要（必須：モジュール利用時）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル（必須：モジュール利用時）
- KABU_API_PASSWORD — kabuステーション API パスワード（利用環境で必須）
- OPENAI_API_KEY — OpenAI を使う関数に渡すか、環境変数で設定
オプション／デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite（デフォルト data/monitoring.db）

注意: config.Settings のプロパティは未設定の場合 ValueError を投げます（必須項目）。

---

## 使い方（基本例）

以下は代表的な使い方の例です。実行は仮想環境内で行ってください。

- DuckDB 接続を作って日次 ETL を実行する:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニューススコアリング（OpenAI API キーは env または引数で指定）:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"scored {n} codes")

- 市場レジーム判定:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB の初期化（監査用 DuckDB を生成）:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を用いて監査ログテーブルにアクセスできます

- データ品質チェックの実行:

from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)

注意点:
- OpenAI 呼び出しは api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- score_news / score_regime は LLM 呼び出しに失敗した場合にフォールバック処理を行うよう実装されていますが、API 利用料やレート制限に注意してください。
- ETL / calendar 更新等は DB のスキーマが整っている前提です。最初に適切なスキーマ初期化（プロジェクト独自のスクリプト）を行ってください。

---

## 環境変数と .env 自動読み込み

- config モジュールはプロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - `.env.local` は `.env` を上書きする用途に使います（ローカル専用の秘密キー等）。
- 自動ロードを無効にするには env に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- .env ファイルのパーサはコメントやクォート、export プレフィックス等の一般的形式をサポートします。
- 必須の値は Settings クラスのプロパティから参照してください。未設定時は ValueError が発生します。

---

## ディレクトリ構成

以下は主要なファイル/モジュールの概要です（src/kabusys 以下）。

- __init__.py
  - パッケージの version と public API 宣言
- config.py
  - 環境変数読み込み・Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント解析（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL メイン処理（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — マーケットカレンダー管理
  - news_collector.py — RSS 収集・前処理（SSRF 対策等）
  - quality.py — データ品質チェック（欠損、スパイク、重複、日付不整合）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ（テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum, value, volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- その他
  - ai や data 内の多数の補助関数・定数・内部実装

（README に収まりきらない詳細は各モジュールの docstring を参照してください）

---

## 開発上の注意 / 設計方針（抜粋）

- ルックアヘッドバイアス防止:
  - 日付判定や ETL/AI 評価では `datetime.today()` を内部で参照せず、呼び出し側が target_date を渡す設計です。
- 冪等性:
  - DB への保存は可能な範囲で ON CONFLICT DO UPDATE を用いて冪等に実装されています。
- フェイルセーフ:
  - LLM/API 呼び出しに失敗した場合、多くの処理はゼロや中立値でフォールバックし、例外を上位へあげない設計箇所があります（ログ出力は行われます）。
- セキュリティ:
  - news_collector は SSRF 対策、受信サイズ上限、XML パースの安全実装を備えています。
- レート制限・リトライ:
  - J-Quants クライアントは固定間隔のレートリミッタと指数バックオフを備えています。OpenAI 呼び出しもリトライ処理を行います。

---

## 参考・開発補助

- 各モジュールの docstring に実装詳細と設計意図が記載されています。まずはそれらを参照してください。
- テスト用に .env.example を用意し、必要なシークレットは CI/ローカルで適切に設定してください。
- OpenAI 等の外部 API を使う処理はコストがかかります。開発時はモック（unittest.mock.patch）で外部依存を置換することを推奨します（コード中でもテスト差し替えを想定した実装がされています）。

---

以上がプロジェクトの概要と基本的な使い方です。詳細な API（関数引数・戻り値など）は各モジュールの docstring を参照してください。README に含めたい追加情報（例: CI 手順、具体的な .env.example 内容、実行スクリプト）などがあればお知らせください。