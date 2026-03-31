# KabuSys

日本株向けデータプラットフォーム兼自動売買／リサーチ基盤ライブラリです。  
J-Quants からのデータ取得、DuckDB による ETL・品質チェック、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（オーダー／約定トレース）などを提供します。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可）
  - 必須環境変数のラッパー（`kabusys.config.settings`）
- データ取得・ETL
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
  - 差分更新・バックフィル付きの日次 ETL（`run_daily_etl` 等）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS ベースのニュース収集（SSRF 対策・トラッキング除去）
  - OpenAI を用いた銘柄別ニュースセンチメント（`score_news`）
- 市場レジーム判定
  - ETF(1321)の200日MA乖離とマクロニュースセンチメントを合成（`score_regime`）
- 研究用ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal / order_request / executions の監査テーブル定義と初期化（DuckDB）
  - 冪等性とトレーサビリティを重視

---

## セットアップ手順

前提：
- Python 3.10+（コードは型ヒントに | 型表記など使用）
- DuckDB（Python パッケージ duckdb）
- OpenAI SDK（openai パッケージ）
- defusedxml（RSS パース用）
- ネットワーク接続（J-Quants / OpenAI など）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 代表的な依存例:
     - pip install duckdb openai defusedxml
   - プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください。

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（デフォルト）。
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意/デフォルト
     - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
     - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   例 .env（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データディレクトリ作成（必要なら）
   - mkdir -p data

---

## 使い方（主要な API の例）

※ 以下は python スクリプトや REPL から呼び出す例です。logger の設定やエラーハンドリングは実運用で適宜追加してください。

1. 設定読み取り
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

2. DuckDB 接続を作り ETL を実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3. ニュースのセンチメント評価（OpenAI API キーは env の OPENAI_API_KEY を参照）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {written}")
```

- `score_news` は OpenAI の JSON mode（gpt-4o-mini）を用いて銘柄ごとのスコアを ai_scores テーブルに書き込みます。
- API キーを明示的に渡すことも可能： score_news(conn, date(2026,3,20), api_key="sk-...")

4. 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

5. 監査 DB の初期化（監査ログ専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査テーブルが作成された DuckDB 接続
```

6. 研究用関数例（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026,3,20))
# 結果は dict のリスト: [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
```

---

## 注意点 / 運用上のポイント

- Look-ahead バイアス対策
  - ライブラリの多くは date 引数を明示的に受け取り、内部で datetime.today() を参照しない設計です。バックテストでの使用時は必ず target_date を適切に指定してください。
- OpenAI / J-Quants の API エラー時
  - 多くの箇所でリトライやフェイルセーフ（例: API 失敗時はマクロセンチメント 0.0 にフォールバック）を実装していますが、運用ではレート制限やコストに注意してください。
- DuckDB の executemany の挙動
  - 一部関数は DuckDB 0.10 の仕様を考慮しており、空の executemany を避ける実装になっています（空リスト渡さないこと）。
- 自動 .env 読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動ロードします。テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 主要ディレクトリ構成

（src 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py              -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py          -- ニュースセンチメント（OpenAI）
    - regime_detector.py   -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py          -- ETL パイプライン / run_daily_etl 等
    - etl.py               -- ETLResult の公開
    - news_collector.py    -- RSS 収集 / 前処理
    - calendar_management.py -- 市場カレンダー管理（営業日判定等）
    - quality.py           -- データ品質チェック
    - stats.py             -- 統計ユーティリティ（zscore 正規化等）
    - audit.py             -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py   -- モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー
  - research/（他の研究用モジュール等）
  - (その他: strategy / execution / monitoring 等パッケージ公開を想定)

---

## 開発・テスト

- 単体テストは各モジュールの依存（外部 API 呼び出し）をモックして行うことを推奨します。実装中に注入可能な引数（例: api_key, id_token, モック可能な内部関数）を利用できます。
- ローカルでの実行時は DuckDB のインメモリ接続（":memory:"）を使うとテストが容易です。
- ニュース収集や OpenAI 連携はネットワーク／コストに依存するため CI 上では必ずモックしてください。

---

もし README に追加したい操作手順（例: systemd サービス化、cron での ETL 実行、Slack 通知の仕組み、kabuステーションとの接続手順など）があれば、その要件を教えてください。必要に応じてサンプル .env.example や簡易運用ガイドを追加します。