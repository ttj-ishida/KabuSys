# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。ETL・データ品質チェック・ニュースNLP・市場レジーム判定・リサーチ用ファクター計算・監査ログなど、取引システム／研究ワークフローを支えるユーティリティ群を提供します。

主な設計方針は「ルックアヘッドバイアスを防ぐ」「DuckDB を中心としたローカルデータ管理」「外部 API 呼び出しはリトライ・レート制御を実装」「フェイルセーフ（API失敗時は影響を局所化）」です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（例）
- 環境変数 / .env 例
- ディレクトリ構成（概要）

---

## プロジェクト概要

KabuSys は、日本株のデータプラットフォームとリサーチ／自動売買のための共通処理をまとめた Python パッケージです。主に以下を目的とします。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL（DuckDB 保存）
- ニュースの RSS 収集と LLM を用いた銘柄別センチメントスコア算出
- マクロニュースと 1321（ETF）の 200 日移動平均乖離を組み合わせた市場レジーム判定
- 各種ファクター（モメンタム、バリュー、ボラティリティ）の計算・正規化
- データ品質チェック（欠損・異常値・重複・日付整合性）
- 発注・約定を追跡する監査ログスキーマの初期化ユーティリティ

コアは DuckDB を用いてローカルにデータを保存・集計し、OpenAI（gpt-4o-mini）など外部 API は慎重に呼び出します。

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制御）
  - save_* 関数により DuckDB へ冪等保存（ON CONFLICT）
  - 市場カレンダーの差分更新ジョブ

- ETL パイプライン
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - 個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）

- ニュース収集 & NLP
  - RSS フィード取得（SSRF 対策・gzip 上限）
  - ニュース前処理・記事ID生成（URL正規化）
  - OpenAI を用いた銘柄別センチメントスコア（ai_scores 保存）
  - マクロニュースの LLM スコアと MA 乖離を組み合わせた市場レジーム判定

- リサーチ（研究）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC 計算、統計サマリー、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - init_audit_db による監査用 DuckDB 初期化

- 設定管理
  - settings（環境変数 / .env 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須変数未設定時には明確なエラーを発生

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで | 演算子を使用）
- 任意の OS（DuckDB は対応するプラットフォームで動作）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクト化されている場合はルートで）
   - pip install -e .

   実際のプロジェクトでは requirements.txt / pyproject.toml を用意して依存管理してください。

3. 環境変数設定
   プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）に `.env` / `.env.local` を配置すると、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必須変数は README の「環境変数」セクションを参照してください。

---

## 使い方（簡単な例）

以下は最小限の使用例です。各例では duckdb パッケージと kabusys パッケージをインポートします。

- DuckDB 接続の例
```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（全体）
```
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日（ローカル日）を対象
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（AI）
```
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API key を環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} scores")
```

- 市場レジーム判定
```
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, date(2026, 3, 20))
values = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

- 監査ログ DB 初期化
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って発注/実行ログを書き込む用意ができる
```

- RSS フェッチ（ニュース収集単体）
```
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
```

注意:
- OpenAI 呼び出しには API キー（OPENAI_API_KEY）が必要です。関数は api_key 引数で明示的に渡すこともできます。
- ETL / スコアリングは DB 上のスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime 等）を前提とします。最初にスキーマ初期化を行ってください（プロジェクトの別モジュールで schema 初期化機能が提供される想定）。

---

## 環境変数（主なもの）

必須（実運用時）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携がある場合）

推奨 / 任意
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）

サンプル .env（プロジェクトルートに配置）
```
# .env (例)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は .env → .env.local の順で上書きされます。OS 環境変数は .env より優先され、.env.local は .env を上書きします。プロジェクトルートはパッケージの config モジュールが .git または pyproject.toml を基準に自動検出します。

---

## ディレクトリ構成（主なファイルと役割）

以下はパッケージ内の主要モジュール（src/kabusys 以下）と簡単な説明です。

- kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — 環境変数 / .env 読み込み、Settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — ニュースをまとめて LLM で銘柄別スコアを算出（score_news）
    - regime_detector.py — MA 乖離 + マクロニュース LLM で市場レジームを判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - news_collector.py — RSS 収集と前処理
    - quality.py — データ品質チェック（各種 check_*）
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ定義と初期化
  - research/
    - __init__.py — 研究用関数の再エクスポート
    - factor_research.py — momentum / value / volatility 等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - monitoring/ (パッケージの __all__ に含まれるが一覧外ファイルの可能性あり)
  - execution/, strategy/（発注・戦略層はこのコードベースの外部または別モジュールで実装想定）

各モジュールは DuckDB の接続オブジェクトを引数に取り、DB 操作を行う設計です。外部 API 呼び出しはモジュール内で明示的に処理され、リトライやレート制御を持ちます。

---

## 注意点 / 運用上のヒント

- Look-ahead バイアス対策:
  - 多くの処理で date や target_date を明示的に渡す設計になっています。datetime.today() を直接参照しない関数も多く、バックテストでは target_date を過去に固定して使用してください。
- OpenAI 呼び出し:
  - API 呼び出しはリトライとフォールバック（失敗時は 0.0 など）を行いますが、コストとレート制限に注意してください。テスト時はモック差し替え (unittest.mock.patch) を推奨します。
- .env 自動読み込み:
  - config.py はパッケクトルート（.git または pyproject.toml）から .env を自動ロードします。CI やテストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- スキーマ:
  - DuckDB に保存するテーブル（raw_prices / raw_financials / raw_news / ai_scores / market_regime / market_calendar 等）は別スクリプトやマイグレーションで初期化しておく必要があります。audit.init_audit_db は監査テーブルの初期化を行います。

---

この README はコードの概要と使い方の出発点を示しています。詳細な API 仕様やスキーマ定義、運用手順（Cron / Airflow による定期実行、Slack 通知など）はプロジェクトの他ドキュメント（Design doc / DataPlatform.md / StrategyModel.md）を参照してください。ご質問があれば、どの機能のドキュメントをより詳しく作るか教えてください。