# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリ（KabuSys）。  
DuckDB を用いたデータ ETL、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター計算、監査ログスキーマなどを提供します。

本 README はコードベース（src/kabusys）に基づく利用ガイドです。

---

## プロジェクト概要

KabuSys は次の目的で設計された Python パッケージです。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL と DuckDB への保存（冪等）
- RSS ベースのニュース収集と記事の前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（銘柄別 ai_score）とマクロレジーム判定
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定を追跡する監査ログスキーマ（DuckDB）初期化ユーティリティ

設計方針の要点：
- ルックアヘッドバイアスを防ぐ（内部で date.today() に依存しない処理が多い）
- 冪等性（ON CONFLICT / 単一の冪等キーなど）
- API 呼び出しはリトライ・バックオフ・フェイルセーフを備える
- DuckDB を中心に SQL と標準ライブラリのみで実装（外部 heavy ライブラリ依存を最小化）

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系関数）
  - market_calendar 管理（is_trading_day, next_trading_day 等）
  - news_collector（RSS 取得、前処理、冪等保存）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査テーブルの初期化、init_audit_db）
  - stats（zscore_normalize など）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None): マクロ + MA200 を合成して market_regime に保存
- research/
  - factor_research (calc_momentum, calc_volatility, calc_value)
  - feature_exploration (calc_forward_returns, calc_ic, factor_summary, rank)
- config.py
  - .env 自動読み込み（プロジェクトルート検出）
  - Settings 型（環境変数の取得・検証）

---

## 動作環境 / 依存

- Python 3.10 以上（型注釈に `|` を使用）
- 主要依存（最低限）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセスが必要（J-Quants API、RSS、OpenAI）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージをローカルインストールする場合（setup があれば）
# pip install -e .
```

---

## 環境変数 / .env

プロジェクトはプロジェクトルート（.git または pyproject.toml を基準）を自動検出し、`.env` と `.env.local` を自動で読み込みます（既定で OS 環境変数を上書きしない; .env.local は上書き可）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須は実行する機能に依存）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- KABU_API_PASSWORD — kabu API パスワード（発注関連）
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知（必須なら）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須なら）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/...、デフォルト: INFO)

例（.env.example）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: トークン類は取り扱いに注意してください（VCS にコミットしないこと）。

---

## セットアップ手順（ローカル）

1. Python 仮想環境作成・有効化
2. 必要パッケージをインストール（duckdb, openai, defusedxml 等）
3. プロジェクトルートに `.env` または `.env.local` を作成し、必要な環境変数を設定
4. DuckDB データベース準備（初期化はアプリ側で行います。audit DB を分離する場合は init_audit_db を利用）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# .env を作成
cp .env.example .env
# 必要な値を編集
```

---

## 使い方（主要ワークフロー例）

以下は Python から直接各機能を呼ぶシンプルな例です。実運用ではジョブスケジューラ（cron / Airflow 等）から呼び出します。

1) DuckDB 接続を開いて日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を省略すると今日（ただし内部で取引日調整あり）を対象に ETL 実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースをスコアリングして ai_scores テーブルへ保存
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使う場合 None
print("書き込んだ銘柄数:", n)
```

3) マクロレジーム判定を実行（market_regime テーブルへ保存）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（専用ファイルに監査用テーブルを作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit_kabusys.duckdb")
# 以後 conn_audit を使って監査ログを操作する
```

5) 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の dict のリスト（date, code, mom_1m, mom_3m, ...）
```

ログレベルや実行モードは環境変数（KABUSYS_ENV / LOG_LEVEL）で制御できます（Settings クラス）。

---

## 実装上の注意点 / 守るべきこと

- OpenAI / J-Quants などの外部 API 呼び出しにはレート制限・課金が伴います。テスト時は API 呼び出しをモックすることを推奨します（コード内で _call_openai_api 等を patch 可能）。
- ETL・保存処理は冪等性（ON CONFLICT）を考慮していますが、DuckDB バージョン差により executemany の振る舞いが異なる部分があります。
- 本ライブラリは取引ロジック（実際の注文送信）を直接行うモジュールを含みますが、実際の資金を使う場合は慎重なテストとガード（is_live フラグ、注文前チェック）を必ず行ってください。
- tokens / secrets は安全に管理し、CI/CD に投入する際は Secret Manager 等を使用してください。

---

## ディレクトリ構成（主要ファイル説明）

（src/kabusys 配下を抜粋）

- __init__.py
  - パッケージ公開モジュール一覧（data, strategy, execution, monitoring）
- config.py
  - 環境変数読み込み、Settings クラス（設定アクセス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの集約・LLM 呼び出し・ai_scores への書込
  - regime_detector.py — MA200 とマクロセンチメントの合成による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult 再エクスポート
  - calendar_management.py — market_calendar と営業日ロジック
  - news_collector.py — RSS 取得・前処理・保存
  - quality.py — データ品質チェック
  - stats.py — zscore_normalize 等
  - audit.py — 監査ログ DDL / 初期化
- research/
  - __init__.py
  - factor_research.py — momentum / value / volatility ファクター計算
  - feature_exploration.py — forward returns, IC, 統計サマリー

---

## よくあるユースケース / コードスニペット

- ETL を定期実行して DuckDB にデータを蓄える（cron）
- 日次バッチでニュースを収集 → score_news → ai_scores を参照してシグナルを作る
- market_regime を参照してポートフォリオのリスクパラメータを調整する
- research モジュールで因子の有効性（IC）を検証する

---

## ライセンス / 貢献

この README はコードベースの説明です。実際のライセンス・貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

必要があれば、README に含めるサンプル .env.example、開発・テスト手順、さらに細かい API 使用例（関数シグネチャ毎）を追加します。どの項目を詳しく記載しますか？