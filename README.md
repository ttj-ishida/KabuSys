# KabuSys

KabuSys は日本株のデータパイプライン、研究用ファクター計算、ニュース NLP（LLM）によるセンチメント評価、及び監査ログ／発注監視を想定した内部ライブラリです。本リポジトリはバックテストや自動売買システムのデータ基盤・リサーチ・AI 評価・監査機能を提供します。

主な設計方針
- Look-ahead バイアスを避けるため日付参照は明示的な target_date に依存（date.today() を直接参照しない）。
- DuckDB を主要な永続ストアとして利用（ETL は差分更新・冪等保存）。
- OpenAI（gpt-4o-mini 等）を用いたニュース評価は JSON Mode を利用し、堅牢なリトライ/バリデーションを持つ。
- ETL・品質チェック・カレンダー更新・ニュース収集はフェイルセーフで設計（部分失敗を許容しログ・監査で可視化）。

---

## 機能一覧

- 環境設定管理
  - .env/.env.local 自動ロード（プロジェクトルート検出）と必須環境変数取得（kabusys.config）。
- データ ETL & 品質管理
  - J-Quants から株価・財務・カレンダーを差分取得して DuckDB に保存（kabusys.data.jquants_client, pipeline, etl）。
  - データ品質チェック（欠損・スパイク・重複・日付不整合）（kabusys.data.quality）。
- ニュース収集
  - RSS 取得→前処理→raw_news へ冪等保存（SSRF/サイズ/トラッキング除去対策）（kabusys.data.news_collector）。
- AI（LLM）処理
  - ニュースの銘柄別センチメントスコア化（score_news）（kabusys.ai.news_nlp）。
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメント合成）（score_regime）（kabusys.ai.regime_detector）。
- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等ファクター計算（kabusys.research）。
  - クロスセクション正規化等（kabusys.data.stats）。
- 監査ログ（監査テーブル）
  - signal_events, order_requests, executions 等の監査スキーマ初期化・DB 作成（kabusys.data.audit）。
- J-Quants クライアント
  - レート制御・リトライ・トークン自動更新を備えた API クライアント（kabusys.data.jquants_client）。

---

## 必須環境・依存ライブラリ

主に以下が必要です（実環境ではバージョンを固定してください）:

- Python 3.9+
- duckdb
- openai
- defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発中はパッケージを編集可能インストール:
pip install -e .
```

---

## 環境変数 / 設定

kabusys.config.Settings が環境変数を参照します。主要キー:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーション API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime などで使用）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から `.env` と `.env.local` を自動ロードします。
- 無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット。

セキュリティ: API トークンやパスワードはリポジトリにコミットしないでください。

例 .env（最低限のテンプレート）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローンし、仮想環境を作成・有効化する。
2. 依存ライブラリをインストール（上記参照）。
3. 必要な環境変数を `.env` に設定する（プロジェクトルートに配置）。
4. DuckDB ファイルパス（デフォルト data/kabusys.duckdb）用のディレクトリを作成する:
   ```bash
   mkdir -p data
   ```
5. 監査ログ専用 DB を初期化（任意）:
   ```python
   from kabusys.data.audit import init_audit_db
   init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（コード例）

以下は代表的なユースケースの例です。

1) DuckDB 接続を開いて日次 ETL を実行する:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（銘柄別センチメント）を実行する:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数にセットするか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"書込銘柄数: {n_written}")
```

3) 市場レジーム判定（MA200 + マクロニュース）:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

4) 監査テーブルを初期化して接続を取得する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続
```

注意点:
- score_news / score_regime は OPENAI_API_KEY を引数または環境変数で指定する必要があります。未指定の場合 ValueError を送出します。
- ETL / 保存操作は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, ai_scores 等）を前提とします。初期スキーマ生成は本リポジトリに含まれる別コード（schema 初期化ユーティリティ）で行ってください（プロジェクトに応じた初期化手順を用意すること）。

---

## ディレクトリ構成（抜粋）

（src/kabusys 以下の主要ファイル・モジュール）

- kabusys/
  - __init__.py (パッケージ初期化)
  - config.py (環境変数・設定の自動ロードと Settings)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースセンチメントの LLM スコア化: score_news)
    - regime_detector.py (市場レジーム判定: score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント + DuckDB 保存関数)
    - pipeline.py (ETL パイプラインの実装: run_daily_etl 等)
    - etl.py (ETLResult の再エクスポート)
    - news_collector.py (RSS 収集・前処理)
    - calendar_management.py (マーケットカレンダー操作)
    - quality.py (データ品質チェック)
    - stats.py (統計ユーティリティ: zscore_normalize)
    - audit.py (監査ログスキーマ初期化: init_audit_schema / init_audit_db)
  - research/
    - __init__.py
    - factor_research.py (モメンタム/ボラティリティ/バリュー計算)
    - feature_exploration.py (将来リターン・IC・統計サマリー等)

---

## よくある運用上の注意

- APIキーやパスワードは必ず安全に管理し、公開リポジトリに含めないでください。
- DuckDB ファイルは定期バックアップを推奨します（特に監査 DB）。
- OpenAI の呼び出しは費用が発生します。バッチサイズ・頻度を運用要件に合わせて調整してください。
- ニュース収集時の RSS パースやネットワークは外部に依存するため、タイムアウト・例外処理を適切に監視してください。
- テスト環境で自動 .env ロードを妨げたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用できます。

---

お問い合わせ / 貢献
- バグ報告・改善提案は Issue を起票してください。
- 大きな変更は設計意図（Look-ahead 回避や冪等性等）に留意の上、議論してください。

以上。README に含めたい具体的なコマンドや追加の使用例があれば教えてください。