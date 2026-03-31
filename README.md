# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants からの市場データ取得、DuckDB を用いた永続化、ニュースの NLP スコアリング、研究用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などを包括的に提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.now() に依存しない設計）
- DuckDB を中心に SQL と最小限の Python でデータ処理
- 外部 API（J-Quants / OpenAI）への呼び出しはリトライ・レート制御・失敗時フォールバックを備える
- ETL / 品質チェック / 監査テーブルなど、運用を考慮した堅牢な実装

---

## 機能一覧

- Data
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
  - ETL パイプライン（差分取得、保存、品質チェック）
  - マーケットカレンダー管理（営業日判定、next/prev トレード日など）
  - ニュース収集（RSS -> raw_news、SSRF 対策、トラッキング除去）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ（signal / order_request / executions テーブル、冪等性）
  - 汎用統計ユーティリティ（Zスコア正規化等）
- AI / NLP
  - ニュースの銘柄別センチメントスコア（OpenAI を利用）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメント合成）
  - OpenAI 呼び出しは JSON Mode を使い、レスポンス検証・リトライ実装あり
- Research
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC 計算、統計サマリー等

---

## 必要な環境変数（.env）

以下はコード内で参照される主要な環境変数です。プロジェクトルートに `.env`（および開発用に `.env.local`）を置くと自動的に読み込まれます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（実行する機能により不要なものもあります）：
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注連携等）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector）

オプション / デフォルトあり：
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視）
- KABUSYS_ENV（development/paper_trading/live, default: development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO）

例（.env の簡易例）:
```env
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 環境
   - Python 3.10+ を推奨（typing の union 表記などを使用）
2. リポジトリをクローン / パッケージを配置
3. 依存パッケージをインストール（例）
   - pip install -r requirements.txt
   - 主な依存:
     - duckdb
     - openai
     - defusedxml
     - （標準ライブラリのみで書かれている部分が多いです）
4. .env を設定（上記を参照）
5. DuckDB ファイル用ディレクトリを作成（必要に応じて）
   - 例: mkdir -p data

注意:
- config モジュールはプロジェクトルート（.git または pyproject.toml）を起点に `.env`/.env.local を自動読み込みします。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（代表的な例）

以下は主要ユースケースのサンプルコードです。実行は Python スクリプトや REPL から可能です。

- DuckDB 接続の作成と ETL 実行（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（news_nlp.score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数、または api_key 引数として渡せます
n_written = score_news(conn, target_date=date(2026,3,20))
print("scored:", n_written)
```

- 市場レジーム判定（regime_detector.score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB の初期化（監査専用 DuckDB）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- RSS フィードを取得して保存する（ニュース収集部分を使う場合）
fetch_rss 関数はネットワーク I/O を行うため、エラーハンドリングを行ってください。
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
# raw_news テーブルへの保存ロジックは別途実装されている想定（jquants_client.save_* のように）
```

注意点:
- OpenAI 呼び出しは API レートやコストが関係するため、テスト時はモック化することを推奨します（コード内でもテスト差し替え用に _call_openai_api を patch する設計あり）。
- ETL は J-Quants の API レート制限を守る実装がありますが、API キーの準備と利用規約の確認を行ってください。

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル/モジュール構成（src/kabusys 以下）：

- kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュース NLP（OpenAI）: score_news
    - regime_detector.py                — 市場レジーム判定: score_regime
  - data/
    - __init__.py
    - calendar_management.py            — マーケットカレンダー管理
    - etl.py                            — ETL 公開インターフェース（ETLResult）
    - pipeline.py                       — ETL パイプラインの実装（run_daily_etl 等）
    - stats.py                          — 統計ユーティリティ（zscore_normalize）
    - quality.py                        — データ品質チェック
    - audit.py                          — 監査ログテーブル初期化 / init_audit_db
    - jquants_client.py                 — J-Quants API クライアント（fetch/save 等）
    - news_collector.py                 — RSS ニュース収集/前処理
  - research/
    - __init__.py
    - factor_research.py                — ファクター計算（momentum/value/volatility）
    - feature_exploration.py            — 将来リターン / IC / summary
  - (その他：strategy, execution, monitoring などのパッケージ名は __all__ に記載されていますが、ここでは主に data/ ai/ research を中心に説明しました)

---

## 開発 / テスト時のヒント

- 設定の自動読み込みを無効化するには環境変数:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI のテストは API を叩くとコストが発生するため、内部の _call_openai_api を unittest.mock.patch で差し替えてテストするよう設計されています。
- DuckDB による executemany の空リストバグ回避等、コード中に互換性考慮が入っています。DuckDB のバージョンは安定版を利用してください。

---

もし README に追加したい内容（例：詳しい API 仕様、SQL スキーマ、運用手順、CI 設定、サンプル .env.example）や、特定モジュールの詳細ドキュメントが必要であれば教えてください。必要に応じてサンプル .env.example や簡易チュートリアルを追記します。