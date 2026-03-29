# KabuSys — 日本株自動売買プラットフォーム (README)

KabuSys は日本株向けのデータパイプライン、ファクター研究、ニュース NLP、マーケットレジーム判定、監査ログ機能を備えた自動売買基盤用ライブラリです。内部的には DuckDB をデータ層に使用し、J-Quants API からのデータ取得、RSS ニュース収集、OpenAI（LLM）によるニュースセンチメント評価などの機能を提供します。

以下はコードベース（src/kabusys）に基づく README です。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数（.env）と設定
- ディレクトリ構成 / 主要モジュール
- 開発上の注意点 / テストのヒント

---

## プロジェクト概要

KabuSys は以下を目的としたライブラリ群です。

- J-Quants API から株価日足 / 財務 / マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集（raw_news）と銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄毎・マクロ）
- ETF（1321）の200日移動平均乖離とマクロセンチメントの合成による市場レジーム判定
- ファクター（モメンタム / バリュー / ボラティリティ等）計算と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査（audit）テーブル／DB：シグナル → 発注 → 約定のトレーサビリティ保持

設計上のポイント:
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() を不用意に参照しない設計（多くの関数は target_date を受け取る）
- DuckDB と SQL ウィンドウ関数を多用し依存を最小化
- 外部 API への呼び出しはリトライやレート制御を備えた堅牢な実装

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - カレンダー管理（is_trading_day, next_trading_day, calendar_update_job）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログ初期化（init_audit_schema, init_audit_db）
  - 汎用統計ユーティル（zscore_normalize）
- ai/
  - ニュースセンチメント（score_news）
  - マクロセンチメント合成によるレジーム判定（score_regime）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン・IC・統計サマリー（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - .env または環境変数を読み込み設定を提供（settings オブジェクト）
  - 自動的にプロジェクトルートの .env / .env.local を読み込む（無効化フラグあり）

---

## セットアップ手順

以下は一般的なセットアップ例です。プロジェクトの packaging（pyproject.toml / requirements.txt）により微調整してください。

1. Python 仮想環境を作成
   - 推奨 Python: 3.10+（コードは型アノテーションに | 型や標準ライブラリの型を使用）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは requirements.txt または pyproject.toml を参照してください。

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数（.env） を用意（下記「環境変数」参照）

5. DuckDB ファイルのディレクトリ作成（必要であれば）
   - settings.duckdb_path の親ディレクトリがない場合、自動作成されることが多いですが手動で準備しても良いです。

---

## 環境変数（.env）と設定

config.Settings が主要な設定を提供します。主に次の環境変数が必須です:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot Token
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — execution 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると自動的な .env ロードを無効化

OpenAI:
- OPENAI_API_KEY — score_news / score_regime 等で使用（関数呼び出し時に api_key 引数として渡すことも可）

データベース:
- DUCKDB_PATH — DuckDB のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB などに使用（デフォルト data/monitoring.db）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

注意:
- config モジュールはプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索して .env を自動的に読み込みます。テスト時に自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要 API と例）

以下は簡単な利用例です。実行前に必ず必要な環境変数を設定してください。

1) DuckDB 接続を作る（ETL / 解析で共通）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date=None で本日を対象
print(result.to_dict())
```

3) ニュースセンチメントを計算して ai_scores に保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、下記の api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} scores")
```

4) 市場レジームを評価して market_regime テーブルへ書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) ファクター計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

6) 監査ログ用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または既存 conn に対して init_audit_schema(conn)
```

7) ニュース収集（RSS の取得）
- ニュース収集モジュールは fetch_rss や保存ロジックを提供します。fetch_rss は外部ネットワークを行うため、実行権限・環境に注意して使用してください。

---

## ディレクトリ構成（主要ファイル / モジュール）

以下は src/kabusys 以下の主なファイルと役割の一覧です（抜粋）:

- kabusys/
  - __init__.py — パッケージ情報（__version__）
  - config.py — 環境変数 / 設定読み込み（settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント解析（score_news）
    - regime_detector.py — マクロ + ETF MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py — J-Quants API クライアント（fetch_ / save_）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等, calendar_update_job）
    - news_collector.py — RSS 取得・前処理・保存
    - quality.py — データ品質チェック（check_missing_data 等）
    - stats.py — zscore_normalize 等統計ユーティリティ
    - audit.py — 監査テーブル DDL と初期化
    - pipeline.py, etl.py（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank

（実際のリポジトリにはさらにサポートモジュールやテスト等が存在することがあります）

---

## 開発上の注意点 / テストのヒント

- 外部 API 呼び出し（OpenAI / J-Quants / RSS）はテスト時にネットワークを避けるためモック推奨です。コード中にも unittest.mock.patch で差し替える想定の関数が利用されています（例: kabusys.ai.news_nlp._call_openai_api）。
- config._find_project_root() は __file__ を基準に .git / pyproject.toml を探索して .env を自動ロードします。ユニットテストで .env 自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany に対して空リストを渡すと互換性の問題があるバージョンがあるため、コード中では空チェックを行っています（特に ETL / ai スコア保存周り）。
- OpenAI 呼び出し部分は JSON モードで厳密な JSON を期待しますが、応答のパースに対するロバスト性（最外の {} を抽出する等）も実装されています。
- ニュース収集モジュールは SSRF 対策や受信サイズ上限、gzip 解凍後の再チェックなどセキュリティ考慮が含まれています。外部 RSS 取得は運用上の権限・ネットワークポリシーを確認してください。

---

以上がこのコードベースに対する README.md です。必要ならば、README に含める具体的なコマンド例（systemd / cron のジョブ定義、Dockerfile、CI 用のテスト手順等）や .env.example のテンプレートを追加できます。どの情報を追加したいか教えてください。