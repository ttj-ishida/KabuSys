# KabuSys

日本株向けのデータパイプライン・リサーチ・AI支援・監査ログを備えた自動売買基盤のコアライブラリです。DuckDB をデータ層に用い、J-Quants / OpenAI / RSS / kabuステーション 等と連携するモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の要素を組み合わせて、研究（リサーチ）→ETL（データ収集/保存/品質チェック）→AI（ニュースセンチメント、マーケットレジーム判定）→運用（監査ログ）を支援する Python モジュール群です。

主な設計方針:
- DuckDB を中核に SQL + Python で処理を実装
- Look-ahead bias を避ける（関数は内部で date.today() に依存しない等）
- ETL は差分取得およびバックフィル対応、品質チェックを実装
- OpenAI 呼び出しはリトライ・バックオフ・レスポンスバリデーションを実装
- ニュース収集は SSRF / XML 脆弱性対策を実装

---

## 機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（無効化可）
  - 各種必須設定のラッパー（J-Quants, OpenAI, Slack, DB パス等）

- データ (kabusys.data)
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save / 認証・リトライ・レート制御）
  - ニュース収集（RSS パーシング、SSRF 対策、記事正規化、raw_news 保存）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal_events / order_requests / executions テーブル、初期化ユーティリティ）

- AI（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）：銘柄ごとのニュースを集約して OpenAI でスコア化、ai_scores テーブルへ書き込み
  - マーケットレジーム判定（regime_detector.score_regime）：1321 ETF の 200 日 MA 乖離 + マクロ記事の LLM センチメントで日次レジームを判定し market_regime に保存

- リサーチ（kabusys.research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（情報係数）、統計サマリ、Z スコア正規化ユーティリティ

---

## 前提 / 依存関係

- Python 3.9+
- 必要な主なパッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実際のパッケージ管理はプロジェクトの pyproject.toml / requirements.txt に従ってください）

例:
```
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境を作成してパッケージをインストール
```
python -m venv .venv
source .venv/bin/activate
pip install -e .
# または依存パッケージを個別インストール
pip install duckdb openai defusedxml
```

3. 環境変数を設定（.env をプロジェクトルートに置くと自動で読み込まれます）
- 自動読み込みはデフォルトで有効（kabusys.config が .git または pyproject.toml を基準に .env/.env.local を読み込みます）
- 自動読み込みを無効化する場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

推奨の .env（例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. データディレクトリ作成（例）
```
mkdir -p data
```

---

## 使い方（概要・サンプル）

以下は基本的な利用例です。各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。

- DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

# ファイル DB を使用
conn = duckdb.connect(str(settings.duckdb_path))
# またはメモリ
# conn = duckdb.connect(":memory:")
```

- ETL（日次パイプライン）を実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key 引数を渡すか、環境変数 OPENAI_API_KEY を設定してください
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("書き込み銘柄数:", n_written)
```

- マーケットレジーム判定を実行
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026,3,20), api_key=None)
print("score_regime result:", res)
```

- 監査用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は内部で UTC タイムゾーンを設定します
```

- 設定値にアクセスする
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- OpenAI の呼び出しはレスポンス検証・リトライ・失敗時のフェイルセーフ（スコア 0 へのフォールバックなど）を持っていますが、APIキー・利用料の管理は利用者責任です。
- ETL / AI 関数はいずれも「target_date」を引数に取り、内部で現在日時に依存しない設計になっています（バックテスト用途に適切）。

---

## 環境変数（主要項目）

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- KABU_API_PASSWORD: kabu API パスワード（発注系で利用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能で利用）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: environment (development, paper_trading, live)
- LOG_LEVEL: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する場合に 1 を設定

---

## ディレクトリ構成

リポジトリの主要モジュール構成（概要）
```
src/kabusys/
├── __init__.py
├── config.py                     # 環境変数・設定管理
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py               # ニュースセンチメント (score_news)
│   └── regime_detector.py        # 市場レジーム判定 (score_regime)
├── data/
│   ├── __init__.py
│   ├── jquants_client.py         # J-Quants API クライアント（fetch/save）
│   ├── pipeline.py               # ETL パイプライン (run_daily_etl 等)
│   ├── news_collector.py         # RSS ニュース収集
│   ├── calendar_management.py    # 市場カレンダー管理
│   ├── quality.py                # データ品質チェック
│   ├── audit.py                  # 監査ログテーブル初期化
│   ├── etl.py                    # ETLResult 公開インターフェース
│   └── stats.py                  # 統計ユーティリティ（zscore_normalize）
├── research/
│   ├── __init__.py
│   ├── factor_research.py        # Momentum/Value/Volatility 等
│   └── feature_exploration.py    # forward returns, IC, summary, rank
└── monitoring/ (場合によって存在)
```

---

## 注意事項 / 実運用上のヒント

- 本ライブラリは「データ取得・スコア算出・監査ログ保存」を目的としており、発注（ブローカーへの実際の送信）やフロントエンド部分は別モジュールで実装する想定です。
- 本番（live）環境と paper_trading 環境を区別するために KABUSYS_ENV を設定してください。settings.is_live / is_paper で判定できます。
- ETL を定期実行する際は、J-Quants のレート制限と API 料金に注意してください。jquants_client はレート制御とリトライを実装しています。
- OpenAI 呼び出し回数はコストに直結します。news_nlp・regime_detector はバッチ化・最大記事数制限を行っていますが、商用運用時はコスト管理を検討してください。
- ニュース収集は外部 RSS を取り込むため SSRF・XML 脆弱性対策が入っていますが、社内運用ポリシーに従いアクセス先ホワイトリスト等を採用することを推奨します。

---

必要であれば、README に含める具体的なコマンド例（systemd / cron による定期実行、Dockerfile、CI 設定、より詳しい .env.example など）を追加します。どの項目を詳しく書き足しましょうか？