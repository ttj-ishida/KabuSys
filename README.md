# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。ETL（J-Quants）による市場データ収集、ニュースの NLP スコアリング、ファクター計算、マーケットレジーム判定、監査（トレーサビリティ）など、アルゴリズムトレード基盤の主要コンポーネントを提供します。

---

## 概要

KabuSys は以下の用途を想定した Python モジュール群です。

- J-Quants API からの株価・財務・カレンダーの差分 ETL
- RSS ニュース収集と OpenAI を用いた記事／銘柄ごとのセンチメントスコア生成
- ETF を用いた市場レジーム判定（MA とマクロニュースの併合）
- リサーチ用のファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェックと監査用の監査ログ（発注・約定のトレーサビリティ）
- DuckDB を中心としたローカルデータ管理

設計上、ルックアヘッドバイアスを避けるために「現在日時を勝手に参照しない」設計や、API 呼び出しの堅牢なリトライ/フォールバックが組み込まれています。

---

## 主な機能一覧

- ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API からの差分取得（ページネーション・レート制御・自動トークン更新）
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース NLP（kabusys.ai.news_nlp）
  - RSS 由来の raw_news をまとめて OpenAI（gpt-4o-mini, JSON mode）に投げる
  - 銘柄ごとの ai_scores テーブルへの保存（チャンク & 再試行付き）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM スコア（重み 30%）の合成で daily regime（bull/neutral/bear）判定

- リサーチ（kabusys.research）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（kabusys.data.stats）を利用可能

- データ管理（kabusys.data）
  - jquants_client: API クライアント + DuckDB への保存関数
  - news_collector: RSS 取得・前処理・保存（SSRF 防御・サイズ制限）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - audit: 監査テーブル（signal_events / order_requests / executions）作成ユーティリティ

- 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルートを探索）
  - settings オブジェクト経由で環境変数を型安全に取得

---

## 必要条件 / 依存ライブラリ

- Python >= 3.10（typing の | 演算子等を使用）
- 必須（実行する機能に応じて）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, logging, datetime, pathlib 等

（プロジェクトに requirements.txt があればそれを利用してください。例: pip install -r requirements.txt）

---

## 環境変数（主なもの）

以下はアプリケーションで参照される主要な環境変数の例です。プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます）。

例 (.env):

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=xxx
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO

注意:
- settings.jquants_refresh_token 等プロパティは未設定時に ValueError を投げる（必須）
- 自動読み込みは .git または pyproject.toml を探してプロジェクトルートを検出します

---

## セットアップ手順（開発用）

1. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

2. 依存ライブラリをインストール
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使用）

3. パッケージを編集モードでインストール（任意）
   pip install -e .

4. 必要な環境変数を .env/.env.local に設定（上記を参照）

---

## 使い方（主要な実行例）

以下はライブラリを直接インポートして使う最小例です。関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り）を受け取ります。

- DuckDB 接続例

from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（市場カレンダー・株価・財務を差分取得して保存）

from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースの NLP スコア付け（前日 15:00 JST 〜 当日 08:30 JST の記事を対象）

from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key="your_openai_api_key")
print(f"Wrote scores for {written} codes")

- 市場レジーム判定（ETF 1321 の MA とマクロニュースで判定）

from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="your_openai_api_key")

- 監査ログ用 DB 初期化（監査専用 DB を新規作成）

from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を発注・約定ログ記録に利用

- 設定値を参照

from kabusys.config import settings
print(settings.duckdb_path, settings.is_live)

---

## ディレクトリ構成（概要）

（パッケージルート: src/kabusys）

- __init__.py
  - バージョンとサブパッケージのエクスポート

- config.py
  - 環境変数読み込み・settings オブジェクト

- ai/
  - news_nlp.py: ニュースの OpenAI によるスコアリング（チャンク・バリデーション・保存）
  - regime_detector.py: 市場レジーム判定ロジック（ETF MA + マクロニュース）

- data/
  - jquants_client.py: J-Quants API クライアント、保存関数（raw_prices / raw_financials / market_calendar）
  - pipeline.py: ETL パイプライン（run_daily_etl など）
  - news_collector.py: RSS 収集・前処理・保存
  - calendar_management.py: 営業日判定と calendar_update_job
  - quality.py: データ品質チェック
  - audit.py: 監査ログスキーマ初期化ユーティリティ
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - etl.py: ETLResult の再エクスポート

- research/
  - factor_research.py: calc_momentum / calc_value / calc_volatility
  - feature_exploration.py: calc_forward_returns / calc_ic / factor_summary / rank

---

## 開発上の注意点

- ルックアヘッドバイアス対策:
  - 多くの関数は内部で date.today()/datetime.today() を直接参照せず、target_date を引数で受け取る設計です。バックテストや再現性に注意してください。

- 自動環境読み込み:
  - kabusys.config は .env / .env.local の自動読み込みを行います（プロジェクトルート検出）。テストで無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI 呼び出し:
  - news_nlp と regime_detector は OpenAI の JSON Mode を利用して厳密な JSON を要求しています。API レスポンスのパース失敗や API エラーはフェイルセーフとして「スコア 0」やスキップを行いますが、運用時はログを監視してください。

- DuckDB executemany の注意:
  - 一部の実装は DuckDB のバージョンにより executemany の空リストを扱えない点に配慮しています。空の params は渡さない実装にしています。

---

## 例: .env のテンプレート

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=./data/kabusys.duckdb
SQLITE_PATH=./data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 貢献 / バグ報告

- バグや改善アイデアがある場合は Issue を作成してください。ユニットテスト、型チェック、ログ出力の改善は歓迎です。

---

この README はコードベース（src/kabusys）に基づく概要と利用例を簡潔にまとめたものです。個別の機能（関数）の詳細実装やパラメータの仕様は各モジュールのドキュメント文字列（docstring）をご参照ください。