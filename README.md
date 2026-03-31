# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データの ETL、ニュース NLP による銘柄スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログなどを含みます。

主な設計方針として、バックテストでのルックアヘッドバイアス回避、DuckDB を用いたオフライン処理、外部 API 呼び出しの堅牢化（リトライ・レート制御）を重視しています。

----

## 目次
- プロジェクト概要
- 機能一覧
- 必要な環境変数（.env）
- セットアップ手順
- 使い方（簡易例）
- ディレクトリ構成
- 設計上の注意点

----

## プロジェクト概要
KabuSys は日本株を対象としたデータ基盤・リサーチ・自動売買支援のためのモジュール群です。主に以下を提供します。

- J-Quants API からの差分 ETL と DuckDB への永続化
- ニュースの収集・前処理・LLM によるセンチメント付与（ai/news_nlp）
- マクロニュースと価格指標を使った市場レジーム判定（ai/regime_detector）
- 研究用ファクター計算（research/*）
- カレンダー管理、品質チェック（data/*）
- 監査ログ（audit）テーブルの初期化ユーティリティ

----

## 機能一覧
- data/jquants_client: J-Quants API 呼び出し（レートリミット・リトライ・トークン自動リフレッシュ）
  - 株価日足、財務、上場情報、マーケットカレンダーの取得と DuckDB への冪等保存
- data/pipeline: 日次 ETL（run_daily_etl）を含む差分取得パイプライン
- data/news_collector: RSS フィード収集、前処理、raw_news への保存（SSRF対策、サイズ制限、トラッキング除去）
- data/quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
- data/calendar_management: 営業日の判定・翌前営業日の取得・カレンダー更新ジョブ
- data/audit: 監査ログスキーマ作成・監査用 DB 初期化（init_audit_db / init_audit_schema）
- ai/news_nlp: ニュースを銘柄ごとに統合して LLM（gpt-4o-mini）でセンチメントを算出し ai_scores に保存 (score_news)
- ai/regime_detector: ETF(1321) の MA200 乖離と LLM マクロセンチメントを合成して market_regime を更新 (score_regime)
- research/*: モメンタム・ボラティリティ・バリュー等のファクター計算、特徴量解析ユーティリティ

----

## 必要な環境変数（.env）
以下は本ライブラリで参照される主な環境変数です（必須は README に明記）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector 用）
- KABU_API_PASSWORD — kabu ステーション等の API パスワード（注文系統を利用する場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live") （デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")（デフォルト: INFO）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にするとパッケージ起動時の .env 自動ロードを無効化

.env 例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

注意: パッケージはパッケージルート（.git または pyproject.toml のあるディレクトリ）を探索して `.env` と `.env.local` を自動で読み込みます。自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

----

## セットアップ手順

前提:
- Python 3.9+（typing の Union 表記や型ヒントを利用）
- Git リポジトリをクローンしてプロジェクトルートへ移動

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（最低限）
   pip 等でインストールする。以下は一例です：
   ```
   pip install duckdb openai defusedxml
   ```
   - openai: OpenAI API クライアント（score_news / regime_detector）
   - duckdb: データ保存・クエリ
   - defusedxml: RSS パースでの安全対策

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

5. .env を作成して必要な環境変数を設定

----

## 使い方（簡易例）

- DuckDB 接続を作る（ファイル / メモリいずれでも可）:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイル DB
# または conn = duckdb.connect(":memory:")
```

- 日次 ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
run_daily_etl は市場カレンダー -> 株価 -> 財務 -> 品質チェックの順で実行し、ETLResult を返します。

- ニュース NLP による銘柄スコアリング（score_news）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定しておくか、api_key を渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```
score_news は raw_news / news_symbols / ai_scores を利用します。OpenAI 呼び出し時にリトライ処理やレスポンス検証が入り、失敗時はその銘柄チャンクをスキップして継続します。

- 市場レジーム判定（score_regime）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```
ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルを更新します。OPENAI_API_KEY を環境変数か api_key 引数に渡してください。

- 監査ログ用 DB を初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 設定値を直接参照:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```
settings は環境変数から値を読み取るラッパーです。必須変数が欠けている場合は ValueError を発生させます。

----

## ディレクトリ構成（主要ファイル）
プロジェクトの src/kabusys 以下を要約しています。

- kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動ロード・Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - pipeline.py — ETL パイプライン / run_daily_etl / run_*_etl
    - etl.py — ETLResult の公開エイリアス
    - news_collector.py — RSS 収集・前処理
    - quality.py — 品質チェック
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - calendar_management.py — 市場カレンダー管理
    - audit.py — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー

（上記に加えて strategy, execution, monitoring 等の名前は __all__ に含まれており、将来的な拡張を想定しています）

----

## 設計上の注意点 / ベストプラクティス
- ルックアヘッドバイアスの回避:
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は内部で date.today() を直接参照せず、target_date を外部から渡す設計になっています。バックテスト時は常に明示的な date を渡してください。
- 環境変数:
  - settings が必須の環境変数をチェックします。ETL / AI 呼び出し前に .env を整備してください。
- OpenAI 呼び出し:
  - gpt-4o-mini（JSON Mode）を想定した実装です。API レートやレスポンスの不確実性に対するリトライ・バリデーション処理が組み込まれています。
- DuckDB 互換性:
  - 一部の executemany 処理やバインド方法は DuckDB のバージョン差異に配慮しています（空パラメータ回避など）。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査、プライベート IP ブロック）、defusedxml を使用した XML パース、レスポンスサイズ制限等の安全対策を備えています。

----

もし README に追加したい具体的な例（API の実行例、Dockerfile、CI 設定、より詳細な .env.example など）があれば知らせてください。必要に応じて追記・整形します。