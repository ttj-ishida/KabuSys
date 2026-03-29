# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLPによる銘柄スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などの機能を備えています。

---

## 目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存関係
- セットアップ手順
- 環境変数（.env）について
- 使い方（簡単な利用例）
  - ETL（デイリー）
  - ニューススコアリング（score_news）
  - レジーム判定（score_regime）
  - 監査DB初期化
  - 研究用ユーティリティ（ファクター計算等）
- ディレクトリ構成（主なモジュールと役割）
- 開発・テスト時のヒント

---

## プロジェクト概要
KabuSys は日本株向けに設計された内部ライブラリ群で、以下を目的としています。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL と DuckDB への保存（冪等）
- RSS ニュース収集・前処理・銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析（銘柄ごとの ai_score やマクロセンチメント）
- ETF（1321）を用いた移動平均乖離等と LLM のマクロセンチメントを合成した市場レジーム判定
- ファクター計算（Momentum / Value / Volatility 等）や将来リターン計算、IC分析など研究ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定に対する監査ログテーブル初期化ユーティリティ（トレーサビリティ確保）

設計上の重要点として「ルックアヘッドバイアスの排除」「DB への冪等保存」「外部 API 呼び出し失敗時のフェイルセーフ」が考慮されています。

---

## 機能一覧
主な機能（モジュール単位）：

- kabusys.config
  - 環境変数の読み込み・検証（自動で .env / .env.local をプロジェクトルートから読み込む）
- kabusys.data.jquants_client
  - J-Quants API からのデータ取得（daily_quotes, financials, market_calendar, listed_info）
  - DuckDB へ冪等保存（save_daily_quotes, save_financial_statements, save_market_calendar）
- kabusys.data.pipeline / etl
  - 日次 ETL パイプライン（run_daily_etl）と個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - ETL 結果オブジェクト（ETLResult）
- kabusys.data.news_collector
  - RSS フィード取得、前処理、raw_news への冪等保存（SSRF・サイズ制限・トラッキング除去等を実装）
- kabusys.ai.news_nlp
  - 銘柄ごとのニュースをまとめて LLM に投げ、ai_scores に保存（score_news）
- kabusys.ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM スコアを合成し market_regime に保存（score_regime）
- kabusys.data.quality
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- kabusys.data.calendar_management
  - market_calendar を元に営業日判定・前後営業日取得等のユーティリティ
- kabusys.data.audit
  - 監査ログ用テーブル（signal_events / order_requests / executions）および初期化ユーティリティ（init_audit_db / init_audit_schema）
- kabusys.research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）、将来リターン、IC / 統計サマリー等
- kabusys.data.stats
  - zscore_normalize 等の統計ユーティリティ

---

## 前提条件 / 依存関係
- Python >= 3.10（型アノテーションの `X | Y` を使用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード 等）
- J-Quants / OpenAI の API キー等の環境変数設定が必要

（実際の requirements.txt はプロジェクトに合わせて作成してください）

---

## セットアップ手順（例）
1. レポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存関係インストール（例）
   - pip install duckdb openai defusedxml
   - あるいはプロジェクトに requirements.txt がある場合: pip install -r requirements.txt
4. パッケージを編集可能モードでインストール（任意）
   - pip install -e .
5. .env を作成（下記参照）

---

## 環境変数（.env）について
パッケージは起動時に自動でプロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を読み込みます。読み込み順は OS 環境変数 > .env.local > .env（.env.local は上書き）です。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector 実行時に使用。関数に直接 api_key を渡すことも可能）

オプション:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: 監視DBなど `data/monitoring.db`

.env の例（.env.example をプロジェクトに置くことを推奨）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単な利用例）
以下はライブラリを直接 Python から利用する例です。各例では duckdb 接続を利用します。

- 共通準備:
```python
import duckdb
from kabusys.config import settings

# ファイル DB を使用する例（settings.duckdb_path は Path オブジェクト）
conn = duckdb.connect(str(settings.duckdb_path))
```

### 1) 日次 ETL を実行する
J-Quants からデータを取得して DuckDB に保存し、品質チェックまで行う一連の処理:
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しなければ今日（settings.env により営業日調整あり）
result = run_daily_etl(conn, target_date=None)
print(result.to_dict())
```

### 2) ニューススコアリング（OpenAI を使用）
前日15:00 JST 〜 当日08:30 JST のウィンドウの記事を銘柄ごとに集約して LLM に投げ、ai_scores テーブルへ書き込みます。
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} ai_scores")
# 必要に応じて api_key 引数で OPENAI_API_KEY を上書きできます
# score_news(conn, date(2026,3,20), api_key="sk-...")
```

### 3) マーケットレジーム判定
1321 ETF の MA とマクロニュースを合成して market_regime テーブルに保存します。
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

### 4) 監査DB（発注・約定）を初期化する
監査ログ用に専用 DuckDB を初期化する例:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は transactional=True 相当の初期化を内部で行います
```

### 5) 研究用ユーティリティ（ファクター計算等）
ファクター計算や将来リターン、IC 計算など:
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
forward = calc_forward_returns(conn, date(2026,3,20))
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
```

---

## ディレクトリ構成（src/kabusys）
主要ファイル / モジュールと概要：

- kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — 環境変数管理・自動 .env ロード・設定アクセス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM に送り銘柄スコア生成（score_news）
    - regime_detector.py — ETF + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得＋DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS フィード収集・前処理・保存
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログ用テーブル定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等

---

## 開発・テスト時のヒント
- 自動 .env 読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。ユニットテスト時に環境汚染を避けたい場合に便利です。
- OpenAI 呼び出しなどは関数内部の `_call_openai_api` を unittest.mock.patch してモック化できるよう設計されています（テスト容易性を考慮）。
- DuckDB はファイルベースなのでテストでは `":memory:"` を渡すとインメモリ DB が使えます（init_audit_db 等も対応）。
- J-Quants クライアントはレートリミットとリトライを実装済みですが、テスト時はネットワーク呼び出しをモックしてください。

---

もし README に追記したい具体的な使い方（例: CI ワークフロー、cron ジョブでの ETL 実行手順、Slack 通知のサンプル等）があれば、必要な情報に合わせて章を追加します。