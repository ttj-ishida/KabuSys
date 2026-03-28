# KabuSys

日本株向け自動売買・データパイプライン基盤ライブラリ（KabuSys）。  
データ収集（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、ETL、監査ログなどの主要機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するライブラリ群です。主な目的は以下です。

- J-Quants API からの株価・財務・マーケットカレンダー取得と DuckDB への保存（ETL）
- RSS ニュース収集とニュースに基づく銘柄別 NLP スコアリング（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM 評価を合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution）を保存する監査用スキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計思想としては「ルックアヘッドバイアスを避ける」「DB による冪等保存」「API リトライとレート制御」「フェイルセーフ（API失敗時はスキップして継続）」を重視しています。

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch / save 関数群
- ニュース収集
  - RSS 取得と前処理（kabusys.data.news_collector）
- ニュース NLP（OpenAI）
  - score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルへ保存（kabusys.ai.news_nlp）
- 市場レジーム判定
  - score_regime: ETF(1321) の MA とマクロニュースを合成して market_regime を作成（kabusys.ai.regime_detector）
- 研究ツール
  - calc_momentum / calc_value / calc_volatility（kabusys.research.factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）
- データ品質チェック
  - run_all_checks（欠損、スパイク、重複、日付不整合）（kabusys.data.quality）
- 監査ログ
  - init_audit_schema / init_audit_db（kabusys.data.audit）

---

## 必要要件（主な Python パッケージ）

- Python 3.10+
- duckdb
- openai
- defusedxml

（pyproject.toml / requirements.txt がある場合はそちらを優先してください）

インストール例（プロジェクトルートで）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .    # または pip install -r requirements.txt
```

---

## 環境変数 / 設定

kabusys は環境変数または .env ファイルから設定を読み込みます（自動ロード）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視用）データベースパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

設定は `from kabusys.config import settings` を使って参照できます（プロパティ化されています）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン・チェックアウト
2. 仮想環境を作成して依存関係をインストール
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定（.env.example を参考にする想定）
4. DuckDB データベースの用意（デフォルト: data/kabusys.duckdb）
   - フォルダが存在しない場合は自動で作成されます（監査 DB 初期化関数も同様に親ディレクトリを作成します）
5. OpenAI API キー（OPENAI_API_KEY）を環境変数に設定（news_nlp / regime_detector が必要に応じ参照）

例（Linux / macOS）:

```bash
# 仮想環境準備
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 環境変数（例）
export JQUANTS_REFRESH_TOKEN="xxxx"
export OPENAI_API_KEY="sk-xxxx"
export SLACK_BOT_TOKEN="xoxb-xxxx"
export SLACK_CHANNEL_ID="C01234567"
```

---

## 使い方（代表的な例）

Python スクリプトや REPL から直接利用できます。以下は代表的な呼び出し例です。

- DuckDB 接続を作成して ETL を走らせる（日次 ETL）:

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア付け（OpenAI キーが必要）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB）:

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit に対して order_requests / executions 等を操作可能
```

- 研究用ファクター計算（例: momentum）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト
```

---

## 便利な挙動メモ

- 自動 .env ロード
  - パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動ロードします。
  - テストなどで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは内部でリトライ（指数バックオフ）や 5xx のハンドリングを行います。API 失敗時はフェイルセーフとして 0.0 を返したりスキップして継続する設計です。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE / INSERT … DO UPDATE）で実装されています。
- DuckDB の executemany に空リストを与えると失敗するバージョンがあるため、空チェック後に executemany を実行する実装が随所にあります。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - news_collector.py — RSS フィード収集・正規化
    - calendar_management.py — マーケットカレンダー管理 / 営業日判定
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - etl.py — ETLResult の再エクスポート
    - audit.py — 監査ログスキーマ初期化 / audit DB ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py — 将来リターン, IC, 統計サマリー 等
  - ai/ (上記)
  - research/ (上記)
  - ほか（strategy / execution / monitoring 等が __all__ に含まれる想定）

---

## 開発・デバッグのヒント

- ログレベルは環境変数 `LOG_LEVEL` で変更可能（デフォルト INFO）。
- OpenAI 呼び出しはモジュール単位でテスト用に内部関数を patch して差し替え可能（unit テストでのモックを想定）。
- DuckDB を使うため、ローカルで高速にテーブルを作成して機能確認できます。監査スキーマの初期化は `init_audit_schema` / `init_audit_db` を利用してください。
- News collector は defusedxml を使用し、SSRF / Gzip Bomb / レスポンスサイズ制限などセキュリティを考慮した実装になっています。

---

## ライセンス / 貢献

（この README では省略しています。リポジトリの LICENSE ファイルを参照してください。）

---

何か追加で README に含めたい情報（例: CI 手順、より詳細な .env.example、実運用上の注意点など）があれば教えてください。README をその内容に合わせて拡張します。