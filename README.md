# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。J-Quants からのデータ取得（ETL）、ニュース収集・NLP による銘柄スコアリング、マーケットレジーム判定、研究用ファクター計算、データ品質チェック、監査ログ用スキーマなどを提供します。

---

## 主な特徴

- ETL パイプライン
  - J-Quants API から株価（日足）・財務・市場カレンダーを差分取得し DuckDB へ保存
  - 差分取得・バックフィル・品質チェック（欠損・重複・スパイク・日付不整合）
- データ管理
  - 市場カレンダー管理（営業日判定・前後営業日取得・カレンダー更新ジョブ）
  - ニュース収集（RSS）と記事の前処理（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - J-Quants クライアント（レート制限・リトライ・トークン自動リフレッシュ）
- AI / NLP
  - ニュースベースの銘柄センチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定（bull / neutral / bear）
- 研究支援
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の冪等・監査スキーマ生成ユーティリティ
- 汎用ユーティリティ
  - 日時ウィンドウ計算、DuckDB 保存ユーティリティ、統計関数など

---

## 必要条件 / 推奨環境

- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI API）

実際のプロジェクトでは requirements.txt / pyproject.toml を使用して依存関係を明示してください。

例（インストール）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはリポジトリに requirements.txt があれば:
# pip install -r requirements.txt
```

---

## 環境変数（.env）

config モジュールはプロジェクトルート（`.git` または `pyproject.toml` を基準）を探索して `.env` / `.env.local` を自動読み込みします。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（本番で必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注連携等で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

その他（任意・デフォルトあり）
- OPENAI_API_KEY — OpenAI API キー（AI 関連関数のデフォルト）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite （モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment 名（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例: `.env.example`
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・アクティベート
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` を作成する（`.env.example` を参考に）
   - 必須のトークン類を設定する

5. DuckDB データベースディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（コード例）

以下はライブラリの代表的な使い方例です。各関数は DuckDB 接続（duckdb.connect）を受け取ります。

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（株価 / 財務 / カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
# api_key を明示するか、環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"wrote scores for {n_written} codes")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロ記事センチメントの合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査用 DB 初期化（監査ログ専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_db_path = Path("data/audit.duckdb")
audit_conn = init_audit_db(audit_db_path)
# audit_conn を使って監査テーブルへアクセス可能
```

- カレンダー操作例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- AI 関連（news_nlp, regime_detector）は OpenAI API を使用します。API 利用にはコストが発生します。
- ETL やニュース収集はネットワーク I/O を伴うため、ジョブ化（cron / scheduler）して実行するのが一般的です。

---

## 実装上の注意点

- Look-ahead bias 回避
  - 内部実装は target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計です。バックテスト用途でも日付制御が可能です。
- 冪等性
  - J-Quants から保存する際は ON CONFLICT DO UPDATE を利用して冪等性を確保しています。
- リトライ / レート制御
  - J-Quants クライアントは固定間隔スロットリングとリトライ（指数バックオフ）を実装しています。
  - OpenAI 呼び出しは 5xx / レート等に対するリトライロジックを持ち、失敗時はフェイルセーフ（スコア 0.0）で継続する箇所があります。
- セキュリティ
  - RSS 収集では SSRF 対策、Content-Length / 最大バイト制限、defusedxml を用いた XML パースを行っています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なモジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント（銘柄別）
    - regime_detector.py     # マクロ＋MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得＋保存）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - etl.py                 # ETL インターフェース（ETLResult の再エクスポート）
    - news_collector.py      # RSS 取得・前処理
    - calendar_management.py # 市場カレンダー管理
    - quality.py             # 品質チェック
    - stats.py               # 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py               # 監査ログスキーマ初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     # モメンタム・バリュー・ボラティリティ等
    - feature_exploration.py # 将来リターン・IC・統計サマリー
  - monitoring/ (該当ファイルは抽象)
  - execution/  (発注・約定周りの実装想定)
  - strategy/   (戦略モデル想定)

この README は主要 API と運用上の注意点をまとめたものです。細かな API（引数や戻り値）や追加のユーティリティは各モジュールの docstring を参照してください。

---

## ライセンス / 貢献

本 README ではライセンスや貢献方法の記載は省略しています。リポジトリのトップレベルに LICENSE や CONTRIBUTING.md を用意してください。

---

必要があれば、README に以下を追記します:
- CLI 例（cron / systemd タスクのサンプル）
- さらに詳細な .env.example（推奨値）
- Docker / コンテナ化手順
- テスト実行方法（ユニットテストのコマンド）