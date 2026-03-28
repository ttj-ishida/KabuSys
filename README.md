# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（監査用 DuckDB スキーマ）などを含むモジュール群を提供します。

## 主な特徴
- J-Quants API からの差分取得（株価日足 / 財務 / 上場情報 / マーケットカレンダー）と DuckDB への冪等保存
- ニュース RSS 収集（SSRF対策・トラッキング除去）と raw_news テーブル保存
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別 ai_score）およびマクロセンチメントを用いた市場レジーム判定
- Research 向けファクター計算（モメンタム / バリュー / ボラティリティ）と統計ユーティリティ（Zスコア）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）の作成ユーティリティ
- 設定は環境変数（.env/.env.local）で管理。テスト用に自動読み込みの無効化可能

## 必要条件
- Python 3.10+
- 主な依存パッケージ（プロジェクト側で管理してください）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装されている部分が多く外部依存は限定的）

※実際のインストールはプロジェクトの packaging / requirements を参照してください。

## 環境変数（主要）
以下の環境変数は本ライブラリ内の各機能で使用されます。必要に応じて .env / .env.local に設定してください。

必須（機能利用時に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token 等で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（注文周りの実装で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp.score_news / regime_detector.score_regime 等で利用）

任意 / デフォルトあり
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にすると .env 自動ロードを無効化（テスト用）

自動ロードについて:
- パッケージ起点で .git または pyproject.toml を探索してプロジェクトルートを決定し、 .env → .env.local の順で自動読み込みします（OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できます。

例: .env.example
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

## セットアップ手順（開発用）
1. リポジトリをチェックアウト
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用）
4. プロジェクトルートに .env を作成して上記の環境変数を設定
5. DuckDB 用ディレクトリを作成（例）
   - mkdir -p data

## 使い方（簡単なコード例）
DuckDB 接続は duckdb.connect("path") で行います。多くの API は duckdb.DuckDBPyConnection を受け取ります。

- 日次 ETL 実行（市場カレンダー、株価、財務、品質チェック）
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- ニュースセンチメントを生成して ai_scores に保存
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込銘柄数: {written}")

- 市場レジーム（マクロ + MA200）スコアリング
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに結果が書き込まれます

- 監査ログ用 DuckDB の初期化
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# signal_events / order_requests / executions 等のテーブルが作成されます

- J-Quants トークン取得（明示的に用いる場合）
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # .env の JQUANTS_REFRESH_TOKEN を利用

例外・エラーハンドリング:
- OpenAI / J-Quants の API キーが未設定だと対応する関数は ValueError を送出します。
- 各 ETL 関数は内部で例外をキャッチしログに残す設計ですが、DB 書き込み失敗などは例外をバブルアップすることがあります。ログを確認してください。

## よく使う API 一覧
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.pipeline.run_prices_etl(...)
- kabusys.data.pipeline.run_financials_etl(...)
- kabusys.data.pipeline.run_calendar_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(...)
- kabusys.data.news_collector.fetch_rss(...)
- kabusys.ai.news_nlp.score_news(...)
- kabusys.ai.regime_detector.score_regime(...)
- kabusys.data.quality.run_all_checks(...)
- kabusys.data.audit.init_audit_db(...)

## ディレクトリ構成（概要）
src/kabusys/
- __init__.py
- config.py                            — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                         — ニュースセンチメント（OpenAI 連携）
  - regime_detector.py                  — マクロ + MA200 による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                   — J-Quants API クライアント + DuckDB 保存
  - pipeline.py                         — ETL パイプライン（run_daily_etl 等）
  - etl.py                              — ETL インターフェース再エクスポート
  - news_collector.py                   — RSS 収集・前処理
  - calendar_management.py              — 市場カレンダー管理（is_trading_day 等）
  - quality.py                          — データ品質チェック
  - stats.py                            — 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py                            — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py                  — Momentum / Value / Volatility 等
  - feature_exploration.py              — forward_returns / IC / factor_summary / rank

（上記は主要ファイルの抜粋です。実際のツリーはソース全体を参照してください）

## 運用上の注意
- Look-ahead バイアス対策やフェイルセーフ設計（API失敗時のフォールバック）が多く組み込まれていますが、本ライブラリを用いて実際の売買を行う場合は必ず十分なテストと運用ルールを整備してください。
- OpenAI API 呼び出しはコストとレート制限に注意してください。news_nlp と regime_detector はリトライ・バッチ処理ロジックを含みますが、利用パターンに合わせた監視が必要です。
- DuckDB ファイルはバックアップ、権限管理を行ってください。監査データは削除されない前提の設計です。

---

さらに詳しい使い方・設計資料（DataPlatform.md / StrategyModel.md 等）がある想定です。開発・運用方針や追加のユーティリティが必要であれば README を拡張します。必要な追加項目（例: CI, テスト実行例, パッケージ化手順）があれば教えてください。