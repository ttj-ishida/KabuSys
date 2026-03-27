# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants / RSS / OpenAI（LLM）等と連携してデータ収集・品質チェック・NLPスコアリング・市場レジーム判定・リサーチ用ファクター計算・監査ログを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() 等を不用意に参照しない）
- DuckDB を中心としたローカルデータベース設計
- API 呼び出しはレート制御・リトライ・フェイルセーフを実装
- ETL / 保存は冪等（ON CONFLICT / idempotent）を重視
- 監査ログでシグナル→発注→約定までトレーサビリティ確保

---

## 機能一覧

- データ収集・ETL（J-Quants 経由）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー取得 / 保存
  - 差分取得・バックフィル・ページネーション対応
  - レート制限、401 自動リフレッシュ、リトライ（指数バックオフ）
- ニュース収集
  - RSS フィード取得、URL 正規化、SSRF 対策、gzip 限度チェック
  - raw_news テーブルへ冪等保存・銘柄紐付け
- ニュース NLP（OpenAI）
  - 銘柄毎に記事を集約して LLM によるセンチメント評価（gpt-4o-mini を想定）
  - レスポンス検証・スコアクリップ・バッチ処理・リトライ実装
- 市場レジーム判定
  - ETF（1321）200 日 MA 乖離 + マクロニュースセンチメントを合成して daily レジーム判定（bull/neutral/bear）
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクター算出
  - 将来リターン計算・IC（Spearman）計算・Zスコア正規化等
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合検出
  - QualityIssue データ構造で詳細を返す
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの定義と初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注防止
- 設定管理
  - .env / 環境変数の自動ロード（プロジェクトルート検出）
  - 必須設定は明示的に検査

---

## 必要な環境・依存

最低限の依存例（実際の requirements はプロジェクトに合わせて管理してください）：
- Python 3.10+
- duckdb
- openai（または OpenAI の公式 Python SDK）
- defusedxml

インストール（開発環境例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを編集可能モードでインストールする場合
pip install -e .
```

---

## 環境変数 / .env

パッケージはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）から `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用する環境変数（Settings）：
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しで参照）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env の書式はシェル互換（`KEY=val`、`export KEY=val`、クォート対応、コメント対応）です。

---

## セットアップ手順（要点）

1. リポジトリをクローンし、仮想環境を作成・有効化
2. 依存をインストール（上記参照）
3. プロジェクトルートに `.env`（必要なキー）を作成
   - 例: `.env.example` を元に `JQUANTS_REFRESH_TOKEN` / `OPENAI_API_KEY` 等を設定
4. DuckDB ファイルを置くディレクトリを用意（デフォルト `data/`）
5. （任意）監査用 DB の初期化を実行

---

## 使い方（サンプル）

以下は基本的な Python からの利用例です。バックグラウンドジョブや DAG から呼び出すことを想定しています。

- DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行（差分取得・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別センチメントスコアリング）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示的に渡すことも可能（None の場合は OPENAI_API_KEY 環境変数を参照）
written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("wrote", written, "codes to ai_scores")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
# market_regime テーブルに結果が書き込まれます
```

- 監査データベース初期化（独立 DB）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# 監査テーブル(signal_events, order_requests, executions)が作成されます
```

- 設定参照例
```python
from kabusys.config import settings
print(settings.duckdb_path)     # Path object
print(settings.is_live)         # bool
```

注意点:
- LLM 呼び出し関数（score_news, score_regime）は api_key を受け取り、None の場合は環境変数 `OPENAI_API_KEY` を使用します。キーが未設定だと ValueError を投げます。
- ETL / API コールは外部ネットワークに依存するため、実行時に適切なトークン／ネットワーク設定が必要です。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリ内の主要モジュール構成（src/kabusys 配下の抜粋）です。

- src/kabusys/
  - __init__.py  — パッケージ定義（version 等）
  - config.py    — 環境変数 / 設定管理（.env 自動ロード, Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの LLM スコアリング（score_news）
    - regime_detector.py — マクロセンチメント + MA200 で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save系）
    - pipeline.py           — ETL パイプライン / run_daily_etl / run_prices_etl 等
    - etl.py                — ETL 便利インターフェース（ETLResult 再エクスポート）
    - news_collector.py     — RSS 収集 / 正規化 / raw_news 保存
    - calendar_management.py— 市場カレンダー操作（is_trading_day 等）
    - quality.py            — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py              — 共通統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログスキーマ定義 / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Volatility / Value の計算
    - feature_exploration.py— 将来リターン・IC・統計サマリー関連

（各モジュールは docstring に詳細な処理フロー・設計方針が記載されています。まずは該当モジュールを参照してください。）

---

## 設計上の注意・運用上のヒント

- Look-ahead バイアスを避けるため、関数は target_date を引数で受け取り内部で未来データを参照しないよう設計されています。バックテストでは target_date を適切に設定してください。
- J-Quants API の rate limit（120 req/min）に合わせた RateLimiter を実装済みです。外部ループから短時間に大量リクエストしないでください。
- OpenAI の呼び出しは JSON mode を想定し、レスポンスパースに失敗した場合はフェイルセーフ（0.0 等）へフォールバックする実装です。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、空チェックを行なってから呼んでいます。
- 監査ログは削除しない前提です（削除禁止／FK制約）。order_request_id を冪等キーとして利用してください。

---

## 参考（トラブルシューティング）

- 環境変数が読み込まれない場合:
  - プロジェクトルートが検出できない（.git や pyproject.toml がない）場合、自動ロードはスキップされます。手動で `.env` をロードするか環境変数を export してください。
  - 自動ロードを明示的に無効にしている場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認してください。
- OpenAI 呼び出しで API エラーが多い場合:
  - `OPENAI_API_KEY` の権限とレート制限状況を確認してください。リトライ挙動はログに出力されます。
- DuckDB のスキーマが存在しない場合:
  - ETL で使用するテーブル群は別途スキーマ初期化処理（プロジェクトの schema init スクリプト等）で作成する必要があります。audit の初期化は `init_audit_db` で実行できます。

---

この README はコードベースの主要点を簡潔にまとめたものです。各モジュール内の docstring に設計意図・詳細な処理フローが記載されていますので、実装・拡張時は該当ファイルを参照してください。ご不明点があれば、どの機能についての説明が必要か教えてください。