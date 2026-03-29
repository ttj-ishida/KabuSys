# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J‑Quants からの市場データ取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレース可能な発注／約定ログ）などを提供します。

バージョン: 0.1.0

## 概要
KabuSys は以下の用途を想定したモジュール群を含みます。

- J‑Quants API を用いた株価・財務・市場カレンダーの差分 ETL（duckdb へ保存）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント／マクロセンチメント評価（JSON Mode）
- マーケットレジーム判定（ETF 1321 の MA と LLM の合成）
- 研究用のファクター計算・特徴量探索（momentum, value, volatility, forward returns, IC 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査（signal → order_request → execution）テーブルの初期化ユーティリティ

設計方針の概要:
- ルックアヘッドバイアスを防ぐ（target_date を明示し、datetime.today()/date.today() を安易に参照しない）
- DuckDB を中心としたローカル DB でデータ管理
- API 呼び出しはリトライ・バックオフ・フェイルセーフ等の堅牢な扱い
- 冪等性を重視（ETL 保存は ON CONFLICT DO UPDATE 等）

## 主な機能一覧
- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J‑Quants クライアント（fetch / save / get_id_token）
  - market calendar 管理（is_trading_day 等）
  - news_collector（RSS 取得・前処理・raw_news 保存用ロジック）
  - quality チェック（欠損 / スパイク / 重複 / 日付整合性）
  - audit（監査ログ用 DDL と初期化）
  - stats（zscore_normalize 等）
- ai
  - news_nlp.score_news（ニュースの銘柄別センチメントを ai_scores に書き込む）
  - regime_detector.score_regime（マクロ + MA による market_regime の判定）
- research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み（.env / .env.local 自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化）
  - settings オブジェクトによる設定取得（JQUANTS_REFRESH_TOKEN 等の必須チェック）

## セットアップ手順（開発環境）
以下は一般的な手順例です。プロジェクトの配布形態によって若干異なる場合があります。

1. Python（推奨: 3.10+）を用意
2. 仮想環境を作成・有効化
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate
3. 依存パッケージをインストール
   - 必要な主なパッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - （パッケージ化されている場合は）プロジェクトルートで:
     ```
     pip install -e .
     ```
4. 環境変数 / .env の準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（少なくとも実行する機能に応じて必要）:
     - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuAPI パスワード（発注等を行う場合）
     - SLACK_BOT_TOKEN — Slack 通知を行う場合
     - SLACK_CHANNEL_ID — Slack 通知チャンネル
     - OPENAI_API_KEY — OpenAI を使用する場合（score_news / score_regime）
   - データベースパス（任意、デフォルトあり）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視等の sqlite 用）

注意: .env の書式は shell の export 形式や key=value をサポートします。config モジュールがコメントやクォート処理などを解析して自動読み込みします。

## 使い方（簡易例）
以下はライブラリ API を直接使う例です。DuckDB 接続は duckdb.connect(...) で得られます。

1) 日次 ETL を実行してデータを取得・保存する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成（OpenAI 必須）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored:", count)
```

3) マーケットレジーム判定を実行:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ用 DB を初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests / signal_events / executions を利用できる
```

5) 研究用ファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は dict のリストとして返る
```

注意点:
- OpenAI 呼び出しは外部 API に依存するため api_key が必要です。テストでは内部の _call_openai_api をモックして呼び出しを差し替え可能です。
- run_daily_etl 等は例外を捕捉して処理を継続する設計ですが、result.errors / result.quality_issues を確認して異常を検知してください。

## 環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須: J‑Quants 認証用)
- KABU_API_PASSWORD (kabu ステーション API を使う場合)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (OpenAI を使う場合)
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (Slack 通知)
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- KABUSYS_ENV (development | paper_trading | live、デフォルト development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

.env 自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索して自動で .env / .env.local を読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

## ディレクトリ構成（主要ファイル）
プロジェクトの主要モジュール構成は以下の通りです（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境設定 / .env 読み込み
  - ai/
    - __init__.py
    - news_nlp.py                      — 銘柄別ニュースセンチメントの取得/保存
    - regime_detector.py               — MA と LLM で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                — J‑Quants API クライアント（fetch / save）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETLResult の再エクスポート
    - calendar_management.py           — market_calendar 管理 / 営業日判定
    - news_collector.py                — RSS 取得・前処理
    - quality.py                       — データ品質チェック
    - stats.py                         — zscore_normalize 等統計ユーティリティ
    - audit.py                         — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py               — momentum/value/volatility
    - feature_exploration.py           — forward returns / IC / summary

この構成は用途別にモジュール化されており、研究（research）、データパイプライン（data）、AI（ai）を分離しています。

## テスト・開発メモ
- OpenAI 呼び出しは _call_openai_api を用いており、ユニットテストではこの関数を unittest.mock.patch で差し替え可能です（news_nlp と regime_detector はそれぞれ別実装を持つためモジュール間での private 関数共有は行っていません）。
- DuckDB をテストに使う場合は ":memory:" を渡してインメモリ DB を利用できます（audit.init_audit_db 等はサポート）。
- .env.example をリポジトリ内に置いて必要な環境変数を明示しておくと導入が容易です（このリポジトリには .env.example の参照メッセージが存在します）。

## セキュリティと運用上の注意
- RSS 取得時は SSRF 対策（スキーム検証・プライベート IP ブロック・リダイレクト検査・応答サイズ制限）を実装していますが、実運用では追加のネットワーク制御（プロキシ / egress ルール）も推奨します。
- OpenAI / J‑Quants API キーは安全に保管し、ログに出力しないよう注意してください。
- 実稼働での発注機能を使う場合は paper_trading → live ステージングを踏んで安全確認を行ってください（KABUSYS_ENV を利用）。

---

ご希望であれば以下の追加情報を README に追記できます:
- 依存関係の完全な requirements.txt（現行コードから推定）
- .env.example のサンプル
- CI / テスト実行手順（pytest の例）
- 具体的な ETL スケジュール例（cron / Airflow）