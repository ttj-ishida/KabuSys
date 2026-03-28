# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータプラットフォームと研究・自動売買基盤のコンポーネント群です。J-Quants API によるデータ取得、DuckDB を用いたデータ保管・品質チェック、ニュース NLP / LLM を用いた銘柄センチメント評価、市場レジーム判定、監査ログ（トレーサビリティ）などのユーティリティを提供します。

主な設計方針は次のとおりです。
- ルックアヘッドバイアス回避（内部で date.today() 等を直接参照しない設計）
- ETL / 保存処理は冪等（重複は ON CONFLICT で処理）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- DuckDB を主な永続層とし、監査用 DB も DuckDB で管理可能

---

## 機能一覧

- data
  - ETL パイプライン（prices / financials / calendar の差分取得と保存）
  - J-Quants API クライアント（認証・ページネーション・レート制御・保存ユーティリティ）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS 取得・正規化・保存）
  - 監査ログ（signal → order_request → execution のトレーサビリティ、テーブル初期化）
  - 統計ユーティリティ（Zスコア正規化等）
- ai
  - ニュース NLP（銘柄ごとのセンチメントを LLM で評価して ai_scores へ保存）
  - 市場レジーム検出（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
  - OpenAI 呼び出しはリトライ・エラー処理あり（フェイルセーフは 0.0 等）
- research
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- audit
  - 監査 DB 初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクト（環境変数経由）

---

## セットアップ手順（開発 / 実行）

前提：
- Python 3.9+（typing 仕様に合わせてください）
- DuckDB、OpenAI SDK、defusedxml などの依存パッケージが必要です。

例: pip を使ったインストール（プロジェクトの requirements.txt がある想定の場合）
```
pip install duckdb openai defusedxml
```

1. リポジトリをクローン／チェックアウト
2. プロジェクトルートに `.env` を配置（自動読み込みあり）
   - 自動読み込みは、パッケージ内から .git または pyproject.toml を探索して行われます
   - テスト時に自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
3. 必要な環境変数（最低限の例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=your_openai_api_key
   - KABU_API_PASSWORD=your_kabu_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development  # development | paper_trading | live
   - LOG_LEVEL=INFO
4. DuckDB 用のデータディレクトリを作成（必要に応じて）
```
mkdir -p data
```

※ README に同梱される `.env.example` を参考に `.env` を作成してください（コード内にも .env.example を参照するメッセージがあります）。

---

## 使い方（主要 API と実行例）

下記は代表的な呼び出し例です。いずれもパッケージ内の関数を直接インポートして使用できます。

- Settings の利用（環境変数読取）
```python
from kabusys.config import settings

print(settings.duckdb_path)        # Path オブジェクト
print(settings.is_live)           # True/False
```

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())  # ETLResult の概要
```

- ニュース NLP スコアリング（ai_scores への書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None の場合 OPENAI_API_KEY を参照
print("written:", n_written)
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 監査テーブル (signal_events, order_requests, executions) が作成されます
```

- RSS 取得（ニュース収集ヘルパー）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

ログレベルは環境変数 LOG_LEVEL で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

## 注意点 / 実運用のためのポイント

- OpenAI（LLM）を利用する処理（news_nlp, regime_detector）は API 失敗時にフェイルセーフ（スコア 0 など）で継続する設計ですが、API キーの準備・コスト管理が必要です。
- J-Quants API 呼び出しはレート制御と自動リフレッシュを実装しています。J-Quants のリフレッシュトークンを JQUANTS_REFRESH_TOKEN に設定してください。
- ETL は差分取得かつバックフィル機能を備えています。運用ではスケジューリング（cron 等）で日次実行する想定です。
- DuckDB スキーマや監査テーブルは初期化処理を提供しています。監査トレーサビリティを使う場合は init_audit_db / init_audit_schema を利用してください。
- .env の自動読み込みはプロジェクトルート検出に依存します。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル）

以下はパッケージ内の主要ファイルと役割の概略です（src/kabusys 以下）。

- __init__.py
  - パッケージのバージョンと __all__ 定義
- config.py
  - 環境変数読み込み、Settings クラス (.env 自動ロード含む)
- ai/
  - __init__.py
  - news_nlp.py         — ニュースベースの銘柄センチメント評価（LLM 呼び出し・バッチ処理）
  - regime_detector.py  — マクロ + ETF MA200 による市場レジーム判定（LLM 呼び出し）
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント、保存ユーティリティ
  - pipeline.py         — ETL パイプライン（run_daily_etl 他）
  - quality.py          — データ品質チェック
  - stats.py            — 統計ユーティリティ（zscore_normalize）
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - news_collector.py   — RSS ニュース収集と整備
  - audit.py            — 監査ログテーブル定義 / 初期化
  - etl.py              — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py  — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー
- research/... (その他ユーティリティ)
- その他（strategy, execution, monitoring）: パッケージレベルで名前を公開していますが、コードベースに応じて実装・拡張できます。

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートの検出はこのパッケージファイル位置を基準に行われます。ルートに .git または pyproject.toml が存在することを確認してください。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI のレスポンスパースで失敗する
  - モジュールは JSON パース失敗時に警告を出してスコアを 0 にフォールバックします。API レスポンスを安定化するにはトークンやモデル、温度（本実装は temperature=0）を適切に管理してください。
- J-Quants 認証エラー（401）
  - jquants_client は 401 時にリフレッシュトークンで自動再取得を試みます。JQUANTS_REFRESH_TOKEN が正しいか確認してください。

---

必要であれば、CI 用のテスト例、Docker コンテナ化、運用向けの crontab / systemd ユニット例、あるいは各テーブルの DDL（DuckDB）を追加で記載できます。どの情報が欲しいか教えてください。