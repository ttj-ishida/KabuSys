# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（ライブラリ的に切り出した実装例）。

主な目的:
- J-Quants / RSS 等からデータを取得して DuckDB に保存する ETL
- ニュースの NLP（LLM）によるセンチメント評価と市場レジーム判定
- 研究用ファクター計算・特徴量探索ユーティリティ
- 監査（オーディット）テーブルの初期化・管理
- データ品質チェック・市場カレンダー管理

設計方針として「ルックアヘッドバイアスを避ける」「DuckDB を中心とした再現性」「冪等処理」「外部 API の堅牢なリトライ・レート制御」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（daily ETL / prices / financials / calendar）
  - J-Quants API クライアント（認証、自動リフレッシュ、ページネーション、レートリミット、保存）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days、夜間更新ジョブ）
  - ニュース収集（RSS -> raw_news、URL 正規化、SSRF 対策、トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（signal_events / order_requests / executions schema）
  - 統計ユーティリティ（Zスコア正規化）
- ai
  - ニュースセンチメント（gpt-4o-mini を用いた JSON mode でのバッチ評価）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
  - 両モジュールともにリトライとフォールバック（API失敗時は中立スコア）実装
- research
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- config
  - 環境変数 / .env の自動読み込み（プロジェクトルート検出、.env / .env.local）
  - settings オブジェクト経由で設定値を取得

---

## 前提 / 必要環境

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- その他（標準ライブラリのみで動く箇所も多いですが、上記は必須機能で必要になります）

requirements.txt（例）
```
duckdb
openai
defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン（ローカル環境で）
```
git clone <repository-url>
cd <repository>
```

2. Python 仮想環境を作成・有効化
```
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
```

3. 依存パッケージをインストール
```
pip install -r requirements.txt
```
（requirements.txt がない場合は上記必須ライブラリを個別にインストールしてください）

4. 環境変数の準備
プロジェクトルートに `.env`（および開発機では `.env.local`）を作成します。.env.example があればそれを参考にしてください。

主に必要な環境変数（代表例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 BOT トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 評価を行う場合必須）
- KABU_API_BASE_URL: kabuAPI ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

注意: config モジュールは自動でプロジェクトルートの `.env` / `.env.local` を読み込みます。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（代表的な呼び出し例）

以下はライブラリを直接 Python から呼び出す例です。

- DuckDB 接続の作成（デフォルトパスは settings.duckdb_path）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 / 品質チェックをまとめて行う）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメント評価を実行（ai.score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数で設定されていれば api_key 引数は省略可
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（1321 の MA200 とマクロニュースを組合）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB データベース初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# すでに conn がある場合は init_audit_schema(conn) でも初期化可能
```

- 研究用関数の利用例
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

注意点:
- AI 関連関数は OpenAI API の応答に依存します。APIキーが未設定の場合は ValueError が発生します。
- 多くの関数は「ルックアヘッドバイアス」を避けるために内部で date 引数を受け取り、現在時刻を直接参照しない設計です。バックテストでは適切な target_date を明示してください。

---

## 設定（env / settings）

kabusys.config.Settings から以下の値を取得できます（一例）:

- jquants_refresh_token (JQUANTS_REFRESH_TOKEN) — 必須
- kabu_api_password (KABU_API_PASSWORD) — 必須
- kabu_api_base_url (KABU_API_BASE_URL) — デフォルト: http://localhost:18080/kabusapi
- slack_bot_token (SLACK_BOT_TOKEN) — 必須
- slack_channel_id (SLACK_CHANNEL_ID) — 必須
- duckdb_path (DUCKDB_PATH) — デフォルト: data/kabusys.duckdb
- sqlite_path (SQLITE_PATH) — デフォルト: data/monitoring.db
- pid_file_path, cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

自動 .env 読込:
- プロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` / `.env.local` を読み込みます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースを LLM でスコア化して ai_scores に書き込む
    - regime_detector.py            — ETF MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py                   — ETL パイプライン (run_daily_etl など)
    - etl.py                        — ETLResult の再エクスポート
    - jquants_client.py             — J-Quants API クライアント + 保存関数
    - news_collector.py             — RSS ニュース収集（SSRF 保護・正規化）
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - stats.py                      — zscore_normalize 等の統計ユーティリティ
    - quality.py                    — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                      — 監査ログテーブルの DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py            — momentum / value / volatility の計算
    - feature_exploration.py        — 将来リターン、IC、統計サマリー等
  - ai/、research/、data/ の各モジュールはそれぞれ公開 API を __init__.py でまとめています。

---

## 運用上の注意 / 設計上のポイント

- ルックアヘッドバイアス防止:
  - AI/研究モジュールは target_date ベースで計算するよう設計し、date.today()/datetime.today() を直接参照しない箇所が多いです。
- 冪等性:
  - ETL/保存処理は ON CONFLICT 等で冪等に保存されるよう実装しています。
- フェイルセーフ:
  - AI 呼び出し失敗時はスコアを 0.0 として継続する等、運用時に全体が止まらない設計になっています（ログで警告を出力）。
- セキュリティ:
  - news_collector は SSRF/大容量レスポンス対策、defusedxml による XML 解析等の安全対策を行っています。
- レート制御:
  - J-Quants クライアントは固定間隔のレートリミット（120 req/min）とリトライを実装しています。

---

## 開発 / テストについて

- 単体テストやモックを使ったテストが容易になるよう、API 呼び出し部分（OpenAI / ネットワーク）は内部関数をモック可能な形で実装しています（例: kabusys.ai.news_nlp._call_openai_api を差し替え）。
- config の自動 .env 読み込みはテストで無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

以上がこのコードベースの概要と基本的な使い方です。具体的な利用用途（実際の発注ロジック、UI、運用監視）は別モジュール（execution / monitoring / strategy）などで実装する想定です。必要であれば README にサンプル .env.example、requirements.txt、あるいはデプロイ手順（systemd ジョブやコンテナ化の例）を追加できます。どの情報を追記したいか教えてください。