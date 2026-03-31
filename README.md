# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（DuckDB）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python ライブラリです：

- J-Quants API からの株価・財務・市場カレンダーの差分取得・保存（ETL）
- RSS ニュース収集と OpenAI を用いた銘柄センチメント解析（news_nlp）
- マクロセンチメントと ETF の移動平均乖離から市場レジームを判定（regime_detector）
- リサーチ用のファクター計算・特徴量解析（momentum, value, volatility, IC 等）
- 監査（signal → order → execution）をトレースする監査スキーマの初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント：
- DuckDB を主要なローカルデータストアとして使用
- OpenAI 呼び出しは JSON Mode を活用し堅牢性・リトライを配慮
- Look-ahead バイアス防止のため、現在時刻の直接参照を極力避ける設計
- ETL / 保存は冪等（ON CONFLICT）を意識

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_*/save_*（daily_quotes, financials, market_calendar, listed_info 等）
  - カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - ニュース収集: RSS パーシング・前処理・保存ロジック（SSRF対策、トラッキングパラメータ除去等）
  - データ品質チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 汎用統計: zscore_normalize
- ai
  - news_nlp.score_news: ニュースをまとめて OpenAI に投げ、ai_scores を更新
  - regime_detector.score_regime: ETF(1321)のMA乖離＋マクロニュースで市場レジーム判定
- research
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要環境 / 依存ライブラリ

主な依存（抜粋）：
- Python 3.9+（型アノテーションで union 演算子等を使用）
- duckdb
- openai（OpenAI Python SDK）
- defusedxml（RSSパースの安全対策）

（プロジェクト環境に合わせた requirements.txt / pyproject.toml を用意してください）

---

## 環境変数（主なもの）

このライブラリは環境変数（または .env）を参照して動作します。必須のものは README 内の該当箇所で明示します。

必須（実行する機能により変わります）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先
- OPENAI_API_KEY — OpenAI 呼び出しに使用（関数引数で上書き可能）
- KABU_API_PASSWORD — kabuステーション API を使う場合

任意／デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）から .env と .env.local を自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env.example を参考に .env を作成してください（.env.example はプロジェクトに含める想定）。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトの requirements.txt / pyproject.toml があればそれを利用）

4. .env を作成（例）
   - プロジェクトルートに .env を作成し下記を設定（必須値を適宜埋める）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB データベース初期化（監査DB 等）
   - Python スクリプトで init_audit_db を呼ぶか、ETL 実行の中で必要なスキーマを作成してください。

---

## 使い方（代表的な呼び出し例）

以下は簡単な Python スクリプト例です。実行前に必要な環境変数（特に OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続を作って日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアを生成して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
# OPENAI_API_KEY は環境変数に設定されていること
```

- 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB 初期化（専用ファイル）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以後 conn を用いて監査テーブルへ書き込み可能
```

注意点:
- news_nlp.score_news / regime_detector.score_regime は OpenAI API を呼び出します。APIキーは引数で渡すこともできます（api_key="..."）。
- デフォルトで各機能はフェイルセーフ（API 失敗時はスキップして継続）を意識した実装です。ログを確認してください。

---

## ディレクトリ構成（主なファイル）

以下は本リポジトリの主なファイル/ディレクトリ（src 配下）です：

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境設定/.env 読み込み
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント解析 / ai_scores 書き込み
    - regime_detector.py            -- 市場レジーム判定（1321 MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント & 保存ロジック
    - pipeline.py                   -- ETL パイプライン (run_daily_etl 等)
    - etl.py                        -- ETLResult 再エクスポート
    - news_collector.py             -- RSS 取得/前処理/保存（SSRF 対策等）
    - calendar_management.py        -- 市場カレンダー管理 / calendar_update_job
    - quality.py                    -- データ品質チェック
    - stats.py                      -- zscore_normalize 等
    - audit.py                      -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py        -- calc_forward_returns / calc_ic / factor_summary / rank
  - research/* (その他)
  - (その他：strategy, execution, monitoring パッケージを想定)

---

## 開発・運用に関するメモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行います。CI/テスト環境で自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分はリトライ・バックオフ・レスポンスバリデーションを組み込んでいますが、クレジット消費・API レートに注意してください。
- J-Quants API に対してはモジュール内部でレートリミッタ（120 req/min）とリトライを実装しています。
- ETL 実行時は品質チェック（quality.run_all_checks）を有効にすることを推奨します。品質問題は ETLResult.quality_issues に集約されます。
- DuckDB の executemany は空リストを受け付けないバージョンの挙動に配慮した実装になっています。

---

## ライセンス / 貢献

この README はコードベースからの抜粋に基づく説明です。実際のリポジトリには LICENSE / CONTRIBUTING ガイドラインを配置してください。

ご不明点や追加したい使用例があれば教えてください。README を拡張して具体的な cli や systemd / cron での運用例、サンプル .env.example を追記できます。