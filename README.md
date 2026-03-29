# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買パイプラインを支援するライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・LLM によるニュースセンチメント解析、ファクター計算・リサーチ、監査ログ（オーダー追跡）などのユーティリティを提供します。

主な対象:
- データ取得・品質管理（DuckDB ベース）
- ニュース収集と LLM を使った銘柄センチメントスコアリング
- 市場レジーム判定（テクニカル + マクロニュース）
- ファクター計算・探索的解析（リサーチ用）
- 監査ログテーブル初期化（発注フローのトレーサビリティ）

---

## 主な機能一覧

- 環境設定管理
  - settings オブジェクト経由で環境変数を取得
  - プロジェクトルートの `.env` / `.env.local` の自動読み込み（必要に応じて無効化可）
- データ ETL（J-Quants）
  - 株価日足（OHLCV）・財務データ・マーケットカレンダーの取得と DuckDB への冪等保存
  - 差分取得 / バックフィル / 品質チェック付き（重複・欠損・スパイク・日付不整合）
- ニュース収集（RSS）
  - RSS 取得、前処理、raw_news への保存（SSRF / Gzip / XML の安全対策付き）
- ニュース NLP（OpenAI）
  - 銘柄単位のニュースをまとめて LLM に投げ、銘柄ごとの ai_score を ai_scores に書き込む
  - レートリミット・再試行・レスポンスバリデーションあり
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定
- リサーチユーティリティ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン算出、IC（Spearman）や統計サマリー、Z スコア正規化
- 監査ログ初期化
  - signal_events / order_requests / executions 等の監査テーブルを DuckDB に冪等作成
  - init_audit_db によるファイル DB 初期化補助

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型ヒント・近代的 API を使用）
- DuckDB、openai SDK、defusedxml 等が必要

例: 仮想環境を作成して依存をインストールする

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# その他プロジェクト依存があればここで追加
```

環境変数（.env）  
プロジェクトルート（`.git` または `pyproject.toml` を基準）に `.env` / `.env.local` を置くと自動で読み込まれます。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY (必須 for AI 呼び出し) — OpenAI API キー
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — 有効値: development, paper_trading, live
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL

例 `.env`（最小）

```
JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（主要 API の例）

まず settings を参照して環境設定を取得できます:

```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_dev)
```

DuckDB 接続を開いて ETL を実行（例: 日次 ETL）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメントスコアリング（LLM）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
print(f"wrote scores: {n_written}")
```

市場レジーム判定:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログ DB 初期化（独立 DB を使う場合）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

リサーチ（ファクター計算）例:

```python
from datetime import date
from kabusys.research import calc_momentum, zscore_normalize

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- LLM（OpenAI）呼び出しは API キーが必要です。score_news / score_regime の引数 api_key で注入できます（テスト時の差し替えに便利）。
- 各モジュールはルックアヘッドバイアス防止の観点から内部で date を明示的に受け取り、datetime.today() を直接参照しない設計です。

---

## ディレクトリ構成（主要ファイル）

リポジトリのルートは src/kabusys 配下にパッケージ化されています。主要モジュール:

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数読み込み・settings オブジェクト
- src/kabusys/ai/
  - news_nlp.py           — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py    — ETF MA とマクロニュースを組み合わせて市場レジーム判定
- src/kabusys/data/
  - pipeline.py           — 日次 ETL / 個別 ETL のエントリポイント
  - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py     — RSS 取得・前処理・raw_news 保存
  - quality.py            — データ品質チェック一式
  - calendar_management.py— 市場カレンダー（営業日判定 / 更新ジョブ）
  - audit.py              — 監査ログテーブル定義 / 初期化
  - etl.py                — ETLResult の再エクスポート
  - stats.py              — Z スコアなどの統計ユーティリティ
- src/kabusys/research/
  - factor_research.py    — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py— 将来リターン, IC, summary, rank
- src/kabusys/ai/__init__.py
- src/kabusys/research/__init__.py

（上記は主要ファイルの一覧・役割の簡易説明です）

---

## 実運用・注意事項

- 環境分離:
  - KABUSYS_ENV により動作モード（development / paper_trading / live）を切替可能。live モードでは実取引のフローと接続する場合があるため十分な検証を行ってください。
- セキュリティ:
  - RSS 取得時は SSRF 対策、gzip サイズチェック、defusedxml を使った XML パース等の安全策を講じています。
  - OpenAI キーや J-Quants トークンなどは漏洩しないように `.env` を管理してください。
- 冪等性:
  - J-Quants データ保存、監査テーブル作成、ai_scores の置換などは基本的に冪等操作になるように設計されています。
- テスト:
  - LLM / HTTP 呼び出し箇所はモック差し替えが容易な実装（内部呼び出し関数を patch 可能）になっています。

---

## 貢献 / 開発

- コードの拡張やバグ修正は Pull Request を通じてお願いします。
- 新しい外部 API 呼び出しを追加する場合は、同様のリトライ・レートリミット・フェイルセーフ（失敗時に処理を継続）を守る実装方針に従ってください。
- ドキュメントの追加・改善も歓迎します。

---

README に含めてほしい追加情報（インストール方法、CI、ライセンスなど）があれば教えてください。必要に応じてサンプル .env.example や簡易スクリプト（cron や systemd 用）のテンプレートも作成できます。