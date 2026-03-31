# KabuSys

KabuSys は日本株向けのデータプラットフォームとリサーチ／自動売買支援ライブラリです。J-Quants / RSS / OpenAI を用いたデータ取得、品質チェック、ニュース NLP（LLM）による銘柄センチメント、マーケットレジーム判定、ETLパイプライン、監査ログなどを提供します。

主な設計方針：
- ルックアヘッドバイアスに配慮した日付処理（内部で datetime.today() を使わない）
- DuckDB を中心としたローカルデータストア
- 冪等（idempotent）な保存ロジック（ON CONFLICT / DELETE→INSERT のパターン）
- 外部 API 呼び出しはリトライ / レート制御 / フェイルセーフ実装

バージョン: 0.1.0

---

## 機能一覧

- データ取得・ETL
  - J-Quants API クライアント（株価日足・財務データ・市場カレンダー）
  - 差分取得・バックフィル対応の ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS 取得と前処理（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロ記事＋ETF MA を組み合わせた市場レジーム判定（score_regime）
- 研究ユーティリティ
  - モメンタム・バリュー・ボラティリティ等のファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター要約（factor_summary）
  - クロスセクション Z スコア正規化ユーティリティ
- 監査ログ（Order / Signal / Execution）
  - 監査スキーマ初期化（init_audit_schema / init_audit_db）
  - 発注フローを UUID で追跡するためのテーブル定義
- 設定管理
  - .env または OS 環境変数からの設定読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）

---

## 必要条件（推奨）

- Python 3.10 以上（PEP 604 型表記や list[str] などを利用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最小例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用にパッケージ一覧がある場合:
     ```
     pip install -r requirements.txt
     ```
   - パッケージを editable インストール（開発時）:
     ```
     pip install -e .
     ```

4. 環境変数 / .env を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただしテスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants 用リフレッシュトークン）
     - OPENAI_API_KEY（score_news / score_regime を使う場合）
     - KABU_API_PASSWORD（kabuステーション API を使う場合）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知を利用する場合）

---

## 使い方（代表的な例）

以下はライブラリをインポートして使う例です。実行前に必要な環境変数を設定してください。

- DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（LLM）で ai_scores を作る
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # api_key には OPENAI_API_KEY を渡す
print("書き込み銘柄数:", n_written)
```
（通常は api_key に OPENAI_API_KEY を使います。上例は示意的です）

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # api_key は OPENAI_API_KEY
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn をそのまま利用して監査テーブルへ書き込み可能
```

- 研究用ファクター計算（例）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は [{ "date":..., "code": "...", "mom_1m": ..., ...}, ...]
```

注意点
- score_news / score_regime は OpenAI API を呼ぶため、API キーと通信環境が必要です。API 呼び出しはリトライやフォールバックを組み込んでいますが、失敗時は該当箇所をスキップして継続する設計です（例: スコアが取れない場合は 0.0 を使用する等）。
- ETL 実行時は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, ai_scores, ...）が前提です。初期スキーマが必要な場合はプロジェクトの schema 初期化ユーティリティ（存在する場合）を用いてください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news/score_regime で必要）
- KABU_API_PASSWORD — kabuステーション API パスワード（必要な機能で使用）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）DB パス（デフォルト data/monitoring.db）
- SLACK_BOT_TOKEN — Slack ボットトークン（Slack 通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャネル ID

自動 .env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

（設定の取得は kabusys.config.settings 経由で行ってください）

---

## ディレクトリ構成（抜粋）

以下は主要なモジュール・ファイルの構成です（src/kabusys をルートに示します）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP / score_news（OpenAI 呼び出し）
    - regime_detector.py            — マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL インターフェース（ETLResult 再エクスポート）
    - calendar_management.py        — 市場カレンダー管理（営業日判定等）
    - news_collector.py             — RSS 収集と前処理
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログ（スキーマ定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー
  - research/（その他ファイル）
  - (その他: strategy/, execution/, monitoring/ などは __all__ に含まれることが想定)

---

## 開発・テストに関するメモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml の親）を探索して行います。テスト時などに自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出し部はテスト容易性を考慮して内部の _call_openai_api をモック可能な形に実装しています（unittest.mock.patch を使用して差し替え可能）。
- J-Quants API クライアントは内部でレート制御とトークン自動リフレッシュを行います。テストでは get_id_token / _request をモックすることを推奨します。
- DuckDB に対する executemany の空引数制約（バージョン依存）に注意して実装されています。テスト DB は ":memory:" を使用できます。

---

## ライセンス / 貢献

本リポジトリに LICENSE ファイルが含まれている場合はそちらに従ってください。貢献はプルリクエストと issue を通じて受け付けてください。

---

README に記載のない内部 API や使い方については、モジュール内の docstring を参照してください（各関数・クラスに詳細な説明と設計方針が記載されています）。必要であれば利用例や設計ドキュメント（StrategyModel.md / DataPlatform.md など）に基づく追加の README セクションを作成します。