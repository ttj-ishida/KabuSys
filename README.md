# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・LLM によるセンチメント評価、ファクター計算、監査ログ（発注/約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を含む Python パッケージです。

- J-Quants API を使ったデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を使った ETL パイプライン（差分取得、品質チェック）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を利用したニュース / マクロセンチメント評価（JSON Mode）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC 等）
- 監査ログ（signal → order_request → execution の冪等な保存・検索）
- 環境変数による設定管理（自動 .env ロード機能あり）

設計方針は「バックテストでのルックアヘッドバイアス排除」「フェイルセーフ」「DB への冪等保存」「外部 API はリトライ・レート制御」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch/save のラッパー（ページネーション・リトライ・認証自動更新）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - ニュース収集: RSS 取得と前処理（SSRF 対策・巨大レスポンス防止）
  - 品質チェック: 欠損 / 重複 / スパイク / 日付不整合の検出
  - 監査ログ初期化: init_audit_db / init_audit_schema

- ai
  - score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に保存
  - score_regime: ETF(1321) の MA 乖離とマクロニュースを合成して market_regime に保存

- research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量解析: calc_forward_returns / calc_ic / factor_summary / rank
  - 統計ユーティリティ: zscore_normalize

- config
  - Settings クラス: 環境変数 / .env から設定を読み込み（自動読み込み機能あり）

---

## セットアップ手順

必要環境:
- Python 3.10+
- 推奨パッケージ（例）: duckdb, openai, defusedxml
（requirements.txt / pyproject.toml がある場合はそちらを利用してください）

1. リポジトリをクローン / ダウンロード

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - 開発中: pip install -e .
   - もしくは必要な依存のみ: pip install duckdb openai defusedxml

4. 環境変数（.env）の用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（既存の OS 環境変数は上書きされません。`.env.local` は上書き可能）。
   - 自動ロードを無効にする場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注関連を使う場合）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API を使う場合（score_news / score_regime 等）

データベースの既定パス:
- DUCKDB_PATH: data/kabusys.duckdb （Settings.duckdb_path）
- SQLITE_PATH: data/monitoring.db （Settings.sqlite_path）

---

## 使い方（サンプル）

以下は Python REPL／スクリプトからの利用例です。各関数は DuckDB 接続（duckdb.connect(...) の戻り値）を受け取ります。

1) 設定と DB 接続の準備
```python
from kabusys.config import settings
import duckdb

# デフォルトの DuckDB パスを使用
conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行（市場カレンダー・株価・財務の差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

3) ニュースセンチメント評価（OpenAI API キーが必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# score_news は raw_news / news_symbols テーブルを参照し ai_scores に書き込みます
written = score_news(conn, target_date=date(2026, 3, 20))  # api_key を引数に渡して上書き可
print(f"書き込み銘柄数: {written}")
```

4) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数か引数で指定
```

5) 監査ログ DB の初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 必要に応じて audit_conn を使って監査テーブルにアクセス
```

6) J-Quants からのデータ取得（開発用、直接呼び出す場合）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使って取得
records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
saved = save_daily_quotes(conn, records)
```

注意点:
- score_news / score_regime の内部の OpenAI 呼び出しはリトライやフォールバックを行いますが、API キーが未設定だと ValueError を投げます。
- テスト時は各モジュールの内部関数（例: kabusys.ai.news_nlp._call_openai_api）をモックして API 呼び出しを差し替えることが想定されています。

---

## 環境変数と自動 .env ロード

- パッケージは起動時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` および `.env.local` を自動で読み込みます（既存 OS 環境変数は保護）。
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須 for J-Quants)
- OPENAI_API_KEY (OpenAI を使う機能で必要)
- KABU_API_PASSWORD (kabuAPI を使用する時)
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/...）

Settings クラスからは settings.<property> でアクセスできます。

---

## テスト・開発メモ

- OpenAI 呼び出し周りはモジュール内でラップされており、テストでは該当関数をパッチする方針になっています（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- RSS 取得は SSRF や gzip/BOM を考慮した堅牢な実装になっています。ネットワーク周りをモックして単体テストを行うと良いです。
- DuckDB の executemany に空リストを渡してはいけない箇所があるため、テストデータ／モックでも空チェックが必要です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数/設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                        — ニュースセンチメント（ai_scores）処理
    - regime_detector.py                 — 市場レジーム判定（market_regime）
  - data/
    - __init__.py
    - jquants_client.py                  — J-Quants API クライアント / DuckDB 保存
    - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
    - etl.py                             — ETL の公開インターフェース（ETLResult）
    - news_collector.py                  — RSS 収集と前処理
    - calendar_management.py             — 市場カレンダーの管理 / 更新ジョブ
    - quality.py                         — データ品質チェック
    - stats.py                           — 統計ユーティリティ（zscore_normalize）
    - audit.py                           — 監査ログ（テーブル定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py                 — momentum/value/volatility など
    - feature_exploration.py             — forward returns / IC / summary
  - monitoring/ (モニタリング関連のコードがある想定)
  - execution/, strategy/  (発注や戦略に関するモジュールが想定される)

---

## 追加情報

- ライセンス情報や CI / テストの説明はリポジトリに含めてください（この README には記載していません）。
- 本ライブラリは実際の資金を扱うシステムに接続する機能を含むため、本番運用前に十分なレビュー・テスト・リスク管理を行ってください（特に発注部分・kabuAPI 接続設定）。

---

もし README に追記してほしい使用例（例: バックテスト連携、Slack 通知の設定、kabu発注フロー等）があれば教えてください。必要に応じてサンプル .env.example も作成します。