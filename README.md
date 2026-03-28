# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
本リポジトリはデータ取得（J-Quants）、ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（監査テーブル初期化）などの機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買やリサーチに必要なデータパイプラインと分析ユーティリティを提供する Python パッケージです。主な役割は次のとおりです。

- J-Quants API から株価/財務/カレンダー等の差分取得（ページネーション・レート制御・リトライ対応）
- DuckDB を利用した ETL パイプライン（差分取得・保存・品質チェック）
- RSS ベースのニュース収集と OpenAI を用いたニュースセンチメント（銘柄別 ai_score）算出
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と統計ユーティリティ
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）用テーブルの初期化ユーティリティ

設計上、ルックアヘッドバイアス防止やフェイルセーフ（API 失敗時はスキップや中立値を採用）に配慮されています。

---

## 機能一覧

主なモジュールと提供機能（抜粋）：

- kabusys.config
  - .env 自動読み込み（プロジェクトルート：.git または pyproject.toml 基準）
  - 環境変数管理（必須値の検証）
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、ページネーション、トークンリフレッシュ、保存用関数（DuckDB への冪等保存）
- kabusys.data.pipeline
  - run_daily_etl: 日次 ETL（カレンダー・株価・財務・品質チェック）
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETLResult データクラス
- kabusys.data.news_collector
  - RSS 取得、テキスト前処理、raw_news への冪等保存（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
- kabusys.ai.news_nlp
  - score_news: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores に保存
- kabusys.ai.regime_detector
  - score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM スコアを組み合わせて market_regime を書き込み
- kabusys.research
  - calc_momentum / calc_volatility / calc_value：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank：研究用ユーティリティ
- kabusys.data.audit
  - 監査テーブル（signal_events / order_requests / executions）作成・初期化（init_audit_schema / init_audit_db）
- kabusys.data.quality
  - データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）

---

## セットアップ手順

前提
- Python 3.10+（型注釈や union 表現を利用）
- Git リポジトリのルートに .env / .env.local を置くと自動で読み込まれます（無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

推奨手順（例）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo_url>
   - cd <repo>

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - 最低限の依存例:
     - duckdb
     - openai
     - defusedxml
   - インストールコマンド例:
     - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは pyproject.toml / requirements.txt を参照してインストールしてください。

4. 環境変数の設定
   - プロジェクトルートに .env を作成するか、シェル環境にエクスポートします。最低限必要な変数:

     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_station_api_password>
     - SLACK_BOT_TOKEN=<slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>

   - 省略可能 / デフォルトあり:
     - KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
     - KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   - .env のパースはシェル形式に近い挙動（export 付きやクォート、コメント処理）に対応しています。

---

## 使い方（簡単な例）

以下はサンプルコード例です。実行前に DuckDB ファイルパスを settings.duckdb_path で確認・設定してください。

1) DuckDB 接続を作成して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は環境変数で上書き可能（デフォルト data/kabusys.duckdb）
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントスコアを生成する（OpenAI API キーを環境変数 OPENAI_API_KEY または api_key 引数で指定）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))  # returns written count
print("written:", written)
```

3) 市場レジーム判定を行う（OpenAI API 使用）

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # returns 1 on success
```

4) 監査ログ用 DB を初期化する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
# テーブルが作成され、UTC タイムゾーンがセットされます
```

注意:
- OpenAI API 呼び出しは環境変数 OPENAI_API_KEY を参照します。関数呼び出し時に api_key を明示的に渡すことも可能です。
- OpenAI へは gpt-4o-mini を利用する想定で JSON Mode を使用しています。API エラー時はフォールバック動作（中立値等）があります。

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP / score_news（OpenAI）
    - regime_detector.py        — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch / save）
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — 市場カレンダー管理・営業日判定
    - news_collector.py         — RSS 収集・前処理
    - audit.py                  — 監査ログテーブル作成／初期化
    - etl.py                    — ETLResult 再エクスポート
    - quality.py                — データ品質チェック
    - stats.py                  — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py        — ファクター計算（momentum/value/volatility）
    - feature_exploration.py    — forward returns / IC / summary / rank
  - research/** (その他の研究用ユーティリティ)

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り SQL と Python を組み合わせて処理します。実行時に外部 API（J-Quants / OpenAI）を呼ぶモジュールがあるため、API キーやネットワーク設定に注意してください。

---

## 環境変数（まとめ）

主に使用される環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu ステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（本コード内ではプレースホルダ）
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

.env の書式は Bash ライクな key=value（export prefix, クォート, コメントなど一般的な .env 表記にかなり対応）です。

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス防止：多くの処理で date.today() / datetime.today() を直接参照せず、関数の引数として target_date を受け取る設計になっています。バッチ処理やバックテストでの安全性を高めています。
- フェイルセーフ：外部 API（OpenAI/J-Quants）の一時障害時はフォールバック（中立スコア、スキップ）する実装です。エラーはログに記録され呼び出し元で判断できます。
- 冪等性：DuckDB への保存は ON CONFLICT を使って上書き（冪等）を保証しています。
- セキュリティ：news_collector は SSRF 対策、受信サイズ制限、defusedxml の使用など安全性を考慮しています。
- テスト容易性：OpenAI 呼び出しなどは内部で差し替え（mock）しやすい実装になっています。

---

## 開発 / 貢献

- コーディング規約やテストフレームワークはリポジトリへ追記してください（本 README はコードベースの説明用）。
- 依存関係は pyproject.toml / requirements.txt に明記することを推奨します。
- 機密情報（API キー等）は .env を用いてローカルで管理し、リポジトリにコミットしないでください。

---

もし README に追記したい実例（CI 実行方法、デプロイ手順、より詳細な .env.example、ユニットテストの例など）があれば教えてください。README をそれに合わせて拡張します。