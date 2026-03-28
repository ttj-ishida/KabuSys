# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリ。  
J-Quants / RSS / OpenAI 等を組み合わせて、データ取得（ETL）、データ品質チェック、ニュースNLPによる銘柄センチメント、マーケットレジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）を提供します。

注意: 本リポジトリは取引の実行を伴うコンポーネントを含みます。実運用（特に本番口座）で使う場合は十分な検証とリスク管理を行ってください。

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE 等）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合等の一括チェック（run_all_checks）
- ニュース収集 / 前処理
  - RSS フィード取得（SSRF対策、gzip・サイズ制限、URL 正規化）
  - raw_news / news_symbols への保存処理想定（冪等）
- ニュース NLP（OpenAI）
  - 銘柄別ニュースを LLM で集約評価し ai_scores に書き込む（score_news）
  - マクロニュースと ETF（1321）のMA乖離を組み合わせて市場レジーム判定（score_regime）
  - API 呼び出しはリトライ・バックオフ、フェイルセーフ実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Spearman）・統計サマリー、Z スコア正規化等
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 用の監査スキーマ作成（init_audit_schema / init_audit_db）
  - 発注フローを UUID ベースでトレース可能にする設計

---

## 要件（推奨）

- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （その他標準ライブラリのみで実装している箇所が多いですが、実行する機能に応じて追加パッケージが必要になる場合があります）

requirements.txt が無い場合は最低限次をインストールしてください:

pip install duckdb openai defusedxml

（パッケージバージョンは運用環境に合わせて固定してください）

---

## 環境変数（主なもの）

本パッケージは環境変数から設定を読み込みます。`.env` / `.env.local` をプロジェクトルートに置くことで自動読み込みします（OS 環境変数 > .env.local > .env の優先順）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（注文実行等）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能がある場合）
- SLACK_CHANNEL_ID: Slack チャネル ID

任意 / デフォルトあり:
- KABUS_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視等に使用, デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールの api_key 引数が未指定時に参照）

.env 例:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   git clone <repo_url>
   cd <repo>

2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install --upgrade pip
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. 環境変数（.env）を準備
   - プロジェクトルートに `.env` または `.env.local` を作成
   - 上記「環境変数（主なもの）」を参照して設定

5. DB ディレクトリの作成（必要に応じて）
   mkdir -p data

---

## 使い方（代表的な例）

以下は Python から直接利用する例です。DuckDB 接続は duckdb.connect() を使います。

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得・品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API 必須）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA とマクロ記事の組合せ）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB の初期化:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。必要に応じてトランザクションで操作できます。
```

- J-Quants の ID トークンを取得（テスト / 手動実行）:

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token が必要
print(token)
```

注意点:
- AI モジュールは OpenAI API（gpt-4o-mini を想定）を利用します。API 呼び出しはリトライやバックオフ・エラーハンドリングがありますが、APIキーや課金・レート制限に注意してください。
- ETL・ニュース収集・J-Quants クライアントはネットワークアクセスを伴います。API レート制限や認証情報を適切に管理してください。

---

## 主要モジュール / ディレクトリ構成

（ソースは `src/kabusys` 配下）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定の管理（.env 自動読み込みロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースの LLM スコアリング（score_news）
    - regime_detector.py            — マクロ + MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 + 保存ユーティリティ）
    - pipeline.py                   — ETL 実行ロジック（run_daily_etl 等）
    - etl.py                        — ETL 公開型（ETLResult の再エクスポート）
    - news_collector.py             — RSS 収集 / 前処理（SSRF 対策等）
    - calendar_management.py        — 市場カレンダー管理（営業日判定・更新ジョブ）
    - quality.py                    — データ品質チェック（欠損・重複・スパイク等）
    - stats.py                      — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査ログスキーマ初期化・DB初期化
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility 等のファクター計算
    - feature_exploration.py        — 将来リターン、IC、統計サマリー等
  - ai/、data/、research/ 配下にさらに補助関数やロジックが多数

---

## 設計上の重要なポイント（抜粋）

- Look-ahead bias 対策
  - 日付処理で datetime.today() 等の直接参照を避け、target_date を明示して評価する実装方針が徹底されています。
- 冪等性
  - DuckDB への保存は可能な限り冪等に（ON CONFLICT など）実装されています。
- フェイルセーフ
  - API 呼び出し失敗時は基本的に処理を継続し、部分失敗はログとともにスキップする設計。重大な DB 書き込み失敗時は例外を伝播。
- セキュリティ / 安全性
  - RSS 取得時の SSRF 対策、XML の defusedxml 利用、レスポンスサイズ上限、URL 正規化等を実装。
- 外部 API のレート制御・リトライ
  - J-Quants は固定間隔レートリミッタ、OpenAI 呼び出しはリトライ/指数バックオフ。

---

## 開発・運用上のヒント

- テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env 自動読み込みを無効にできます（テストの isolation 向け）。
- DuckDB ファイルを共有するときはバージョン差やロックに注意してください。単体テストは :memory: を使うと便利です。
- AI 呼び出し部分はモジュール内で関数単位に差し替え（モック）可能な設計になっています（ユニットテスト容易性を考慮）。
- 本リポジトリでは発注実行（ブローカー連携）を想定した監査テーブルや kabu API の設定があります。実際の発注を有効にする際は十分な検証と機構を用意してください。

---

## 最後に

この README はコード内コメントとモジュール実装を要約したものです。各機能の詳細な挙動・引数仕様は該当モジュール（src/kabusys/**）の docstring を参照してください。README の補完や導入手順の自動化（requirements.txt / setup.py / CI スクリプト）を追加すると導入がよりスムーズになります。