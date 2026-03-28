# KabuSys

KabuSys は日本株向けのデータプラットフォームと研究／自動売買補助ライブラリです。J-Quants からのデータ取得、ニュース収集・NLP による銘柄センチメント評価、ファクター計算、ETL パイプライン、監査ログ（監査テーブル）など、システム全体の基盤機能を提供します。

---

## 主な特徴

- J-Quants API からの差分取得（株価・財務・上場銘柄・マーケットカレンダー）と DuckDB への冪等保存
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）およびマクロセンチメント合成による市場レジーム判定
- 研究用ユーティリティ（モメンタム／バリュー／ボラティリティ等のファクター計算、将来リターン、IC、統計サマリー）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal_events, order_requests, executions）スキーマの初期化ユーティリティ
- 環境変数 / .env 管理（自動ロード機能 / テスト時の無効化）

---

## 機能一覧（モジュール別）

- kabusys.config
  - 環境変数読み込み（.env / .env.local）と Settings（必要なキーをプロパティとして取得）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline / etl: 日次 ETL（差分取得・保存・品質チェック）
  - news_collector: RSS フィードの取得・前処理・保存
  - calendar_management: JPX カレンダー管理・営業日判定
  - quality: データ品質チェック
  - audit: 監査テーブル定義・初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize など）
- kabusys.ai
  - news_nlp.score_news: ニュースをまとめて LLM に送信し ai_scores を作成
  - regime_detector.score_regime: ETF（1321）の MA とマクロセンチメントを合成して market_regime を生成
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提・依存関係

- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK v1系を想定)
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース、OpenAI）
- 各種環境変数（下記参照）

（実際の requirements.txt や pyproject.toml はプロジェクトに合わせて用意してください）

---

## 環境変数（主なもの）

以下は Settings（kabusys.config.Settings）で利用される主な環境変数。`.env` / `.env.local` をプロジェクトルートに置くことで自動読み込みされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（発注等で使用する場合）
- SLACK_BOT_TOKEN — Slack 通知で使用するトークン（必要な場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必要な場合）

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで利用）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン / プロジェクトルートへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) または .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - その他テスト / 開発に必要なパッケージを追加
4. プロジェクトルートに `.env` または `.env.local` を作成し上記環境変数を設定（.env.local は .env の上書き）
   - 自動読み込みはプロジェクトルートが `.git` または `pyproject.toml` を含む場合に有効
   - テストなどで自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
5. DuckDB 用ディレクトリが必要なら作成（例: data/）

---

## 使い方（サンプル）

※ 下記は最小の使用例です。実運用ではエラーハンドリングやログ設定を追加してください。

- 日次 ETL（データ取得 → 保存 → 品質チェック）

```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores への書き込み）

```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（market_regime テーブルへ）

```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB の初期化（監査用 DuckDB を作る）

```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# 以後 conn を使って監査テーブルにレコードを追加・照会できます
```

- 研究用ファクター計算

```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の mom_1m/mom_3m/mom_6m/ma200_dev を含む dict のリスト
```

---

## 注意事項 / 設計上のポイント

- Look-ahead bias 防止:
  - 多くの関数は date 引数を明示的に受け取り、内部で date.today() を参照しない設計です。バックテストでの使用時は必ず適切な target_date を渡してください。
- OpenAI 呼び出し:
  - AI モジュールは OpenAI の Chat Completions（gpt-4o-mini, JSON mode）を利用します。API キーは OPENAI_API_KEY（引数でも指定可）で与えてください。API エラー時はフェイルセーフとしてスコアを 0 にフォールバックする箇所があります。
- J-Quants API:
  - モジュール内でトークンリフレッシュ、自動リトライ、レートリミッティングを実装しています。J-Quants の利用規約・レート制限に従ってください。
- ニュース収集（RSS）:
  - SSRF 対策、gzip サイズ制限、XML パースに defusedxml を使用するなど安全性に配慮しています。
- DuckDB への保存は多くの箇所で ON CONFLICT / 冪等処理を行います。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの `src/kabusys/` に配置されている主要なモジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - audit_db 初期化用関数など
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research / data 間のユーティリティを含む（zscore_normalize など）

（実際のリポジトリには上記以外にもユーティリティやテスト、ドキュメント等が含まれる可能性があります）

---

## 開発・テストのヒント

- 自動 .env ロードはプロジェクトルートの検出に __file__ の親ディレクトリから `.git` または `pyproject.toml` を探します。テスト時に自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- AI 呼び出しやネットワーク依存部分は関数単位でモック可能に設計されています（ユニットテスト時は _call_openai_api や _urlopen などをパッチしてください）。
- DuckDB はインメモリ (":memory:") でのテストが可能です。

---

## おわりに

この README はコードベースの主要機能と利用方法を簡潔にまとめたものです。より詳細な運用や設計意図（データスキーマ、ETL の詳細、運用ジョブのスケジューリング等）はプロジェクト内のドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。追加の説明やサンプルが必要であれば教えてください。