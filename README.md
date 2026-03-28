# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants や RSS、OpenAI（LLM）を活用してデータ収集（ETL）、ニュースセンチメント評価、マーケットレジーム判定、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能群を備えた Python パッケージです：

- J-Quants API を用いた株価・財務・カレンダーの差分取得・保存（DuckDB）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI を用いたニュースセンチメント（銘柄単位）とマクロセンチメントの評価
- 市場レジーム（bull / neutral / bear）判定
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を管理する DuckDB スキーマ
- 研究・ファクター計算ユーティリティ（モメンタム・バリュー・ボラティリティ、将来リターン・IC 等）

設計上、バックテストでのルックアヘッドバイアス防止やフェイルセーフ（API失敗時のデフォルト動作）に配慮されています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存関数 / レート制御・リトライ・トークンリフレッシュ）
  - ニュース収集（RSS → raw_news、SSRF / gzip / トラッキングパラメータ対応）
  - カレンダー管理（営業日判定・next/prev/get_trading_days、calendar_update_job）
  - 品質チェック（missing_data / spike / duplicates / date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM に投げ、ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースの LLM スコアを合成して市場レジームを判定
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - Settings クラス: 環境変数/.env 読み込み（自動読み込み機能あり）と必須設定の検証

---

## セットアップ手順

前提: Python 3.10+（typing 表記を使用）を推奨します。

1. リポジトリをクローン
   git clone <your-repo-url>
   cd <repo>

2. 仮想環境作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   ※ pyproject.toml / requirements.txt がある場合はそちらを使用してください。最低限必要なパッケージ:
   pip install duckdb openai defusedxml

   開発時は editable install:
   pip install -e .

4. 環境変数設定
   プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。
   自動ロードを無効にする場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（発注等で使用する場合）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（任意の通知実装で必須）
   - SLACK_CHANNEL_ID      : Slack チャネル ID
   - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector 実行時）

   データベースパス（デフォルトをそのまま使う場合は未設定可）:
   - DUCKDB_PATH  (default: data/kabusys.duckdb)
   - SQLITE_PATH  (default: data/monitoring.db)

5. ロギング設定
   標準の logging を使っているため、アプリ側でハンドラ/レベルを設定してください。環境変数 LOG_LEVEL で設定可能（DEBUG/INFO/...）。

---

## 使い方（例）

Python スクリプトや REPL から主要機能を呼び出す例を示します。

- DuckDB 接続を開いて日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアを計算して ai_scores に保存する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されている前提
num_scored = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {num_scored} codes")
```

- 市場レジームを判定する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI APIキーは環境変数 or 引数で渡す
```

- 監査ログ用 DuckDB を初期化する（監査スキーマ作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセスできます
```

- Settings の使い方（環境変数から簡単に参照）
```python
from kabusys.config import settings
print(settings.duckdb_path)        # Path('data/kabusys.duckdb')
print(settings.is_live)            # KABUSYS_ENV の値に依存
```

注意点:
- news_nlp と regime_detector は OpenAI を使用します。API 呼び出しに失敗した場合はフェイルセーフ（スコア=0 等）で継続する設計ですが、APIキーは必須です（引数で渡すことも可）。
- DuckDB の executemany に空リストを渡すと例外になるバージョンがあるため、関数内部で保護処理が入っています。

---

## ディレクトリ構成

主要ファイル / モジュールを抜粋したツリー:

```
src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      calendar_management.py
      news_collector.py
      quality.py
      stats.py
      audit.py
      pipeline.py
      etl.py
      # ...（その他 ETL/utility ファイル）
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/ ... (factor/feature utilities)
    # strategy, execution, monitoring パッケージは __all__ に含まれていますが
    # 本リストには主要な data/ai/research モジュールを記載しています
```

各主要モジュールの役割（短縮）:
- config.py: .env 自動読み込み・環境変数取得ラッパ（Settings）
- data/jquants_client.py: J-Quants API 通信・保存ロジック（リトライ・レート制御・id_token 管理）
- data/pipeline.py: 日次 ETL のオーケストレーション（run_daily_etl 等）
- data/news_collector.py: RSS 取得・前処理・raw_news 保存ロジック（SSRF 対策）
- data/quality.py: データ品質チェック（欠損・スパイク等）
- data/audit.py: 監査テーブル DDL と初期化ユーティリティ
- ai/news_nlp.py: 銘柄ごとのニュースセンチメント算出・ai_scores への保存
- ai/regime_detector.py: ETF MA と LLM マクロセンチメントの合成による市場レジーム判定
- research/*: ファクター計算・特徴量解析ユーティリティ

---

## 注意事項 / ベストプラクティス

- 環境変数・シークレットは .env/.env.local を使い、リポジトリには含めないでください。
- OpenAI の呼び出しや外部 API 呼び出しはコスト・レート制限に注意してください。news_nlp はバッチ処理で銘柄をまとめて送り、retry/backoff 処理を行うよう設計されています。
- DuckDB ファイルは容量が大きくなる可能性があるため、バックアップ・ローテーションを検討してください。
- ETL や LLM 呼び出しは自動化ジョブ（cron / Airflow / GitHub Actions 等）でスケジュール運用する際、KABUSYS_DISABLE_AUTO_ENV_LOAD を必要に応じて設定してテスト容易性を保持してください。
- 監査テーブルは削除しない前提（監査用）です。init_audit_db で初期化後はアプリ側で created_at/updated_at を管理してください。

---

## サポート / 貢献

- バグレポートや機能要望は Issue を作成してください。
- コントリビュートする場合は PR を作成し、関連するユニットテストと簡潔な説明を付けてください。

---

README の記載はこのコードベースの主要機能と操作例に基づいて作成しています。追加のコマンドラインツール、CI 設定、requirements ファイル等がある場合は、それらに合わせて README を拡張してください。