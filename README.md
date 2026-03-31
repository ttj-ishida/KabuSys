# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース NLP による銘柄センチメント評価、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（order/execution）の初期化などを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today() を直接参照しない設計）
- DuckDB を中心としたローカルデータレイヤ
- 外部 API（J-Quants / OpenAI）呼び出しはリトライ・レート制御・フォールバックを備える
- 冪等性（ETL 保存／監査テーブルの初期化など）を重視

---

## 機能一覧

- データ収集・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存（duckdb）
  - 差分取得・バックフィル・品質チェックを含む日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック
- ニュース収集 / 前処理
  - RSS フィード取得（SSRF 対策・gzip/サイズチェック・トラッキング除去）
  - raw_news / news_symbols への冪等保存（記事ID は正規化 URL の SHA-256）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に投げ、ai_scores テーブルへ書き込む（score_news）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM センチメントの合成: score_regime）
  - OpenAI API 呼び出しは JSON mode を利用し、リトライやフォールバックを実装
- リサーチ / ファクター計算
  - Momentum / Value / Volatility ファクター計算（prices_daily / raw_financials に基づく）
  - 将来リターン計算、IC（Spearman）算出、統計サマリー、Z スコア正規化
- 監査ログ（tracing）
  - signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティを UUID ベースで担保

---

## セットアップ手順

前提
- Python 3.10+（typing の一部構文で | 型を使用）
- システムに DuckDB をインストール可能な環境

1. リポジトリをクローン・作業ディレクトリへ移動
   - 例: git clone ... && cd ...

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - requirements.txt がない場合、主な依存は以下：
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使用してください）

4. パッケージのインストール（開発モード）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートの .env または .env.local に設定を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（ETL）
     - SLACK_BOT_TOKEN — Slack 通知用（もし Slack 機能を使う場合）
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - KABU_API_PASSWORD — kabuステーション API パスワード（注文連携を行う場合）
     - OPENAI_API_KEY — OpenAI を使う機能（score_news / score_regime 等）
   - 任意 / デフォルト可:
     - KABUSYS_ENV (development/paper_trading/live) — デプロイ環境
     - LOG_LEVEL (DEBUG/INFO/...) — ログレベル
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=yourpass
```

---

## 使い方（主要な API / 実行例）

以下は Python スクリプト / REPL での利用例です。各モジュールは duckdb の接続オブジェクトを受け取る設計です。

1. DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)
print(result.to_dict())
```

2. ニュース NLP（OpenAI）でスコアを生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 19))  # 前日のニュースウィンドウを対象
print(f"書き込み銘柄数: {n_written}")
```

3. 市場レジームを判定して保存する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19))
```

4. リサーチ用のファクター計算や統計
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect(str(settings.duckdb_path))
date0 = date(2026, 3, 19)
mom = calc_momentum(conn, date0)
vol = calc_volatility(conn, date0)
val = calc_value(conn, date0)
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

5. 監査ログ（audit DB）を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
# テーブル（signal_events, order_requests, executions）が作成されます
```

注意点:
- OpenAI を利用する関数は api_key 引数を受け取ります（None の場合は環境変数 OPENAI_API_KEY を使用）。
- ETL は J-Quants API へのリクエスト制御・トークンリフレッシュ・リトライを内包します。JQUANTS_REFRESH_TOKEN は必須です。
- 自動環境ファイル読み込みは .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から探します。必要であれば KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## ディレクトリ構成

主要なファイル / モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings（J-Quants, kabu API, Slack, DB パス, 環境フラグ等）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM スコアリング（score_news）
    - regime_detector.py  — マクロセンチメント + ETF MA200 を合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント、fetch / save 関数（rate limiter, retry, token refresh）
    - pipeline.py         — ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - calendar_management.py — 市場カレンダー管理・営業日ロジック
    - news_collector.py   — RSS 収集、前処理、SSRF 対策
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py            — Z スコア正規化など汎用統計ユーティリティ
    - audit.py            — 監査ログ（signal_events / order_requests / executions）初期化
    - pipeline.py         — ETLResult 型の定義（再エクスポート: data.etl.ETLResult）
    - etl.py              — ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank
  - monitoring/ (存在すれば監視関連)
  - strategy/ (戦略実装用フォルダ)
  - execution/ (発注・ブローカー連携)
  - その他モジュール（将来的な拡張箇所）

---

## 追加の注意事項・運用上のポイント

- 環境分離:
  - KABUSYS_ENV = development / paper_trading / live により挙動の分岐（settings.is_live 等）が可能です。live では発注機能の安全対策を必ず確認してください。
- ログ:
  - settings.log_level を使用してログレベルを制御できます。デフォルトは INFO。
- テスト:
  - OpenAI / ネットワーク呼び出し部分はモック可能な設計（個別モジュールの _call_openai_api 等を patch）になっています。
- セキュリティ:
  - news_collector は SSRF / XML インジェクション対策（defusedxml、ホスト判定、リダイレクト検査）を行っています。
  - J-Quants のトークンリフレッシュ処理、OpenAI 呼び出しのリトライロジックは冗長性を持たせていますが、秘密情報は必ず安全に保管してください。

---

必要であれば、README に以下を追加可能です：
- 開発用の依存ファイル（pyproject.toml / requirements.txt）の具体例
- CI / CD 用のワークフロー例（ETL 定期実行、監視アラート）
- データベーススキーマの詳細（raw_prices, raw_financials, ai_scores 等のカラム定義）
- 実運用での設定例（Docker、systemd タイマー、Kubernetes CronJob）

上記の中で追加したい項目があれば教えてください。README を環境（開発/運用）向けにカスタマイズして拡張します。