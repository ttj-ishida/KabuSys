# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ用 README。  
この README はリポジトリ内のコード構成（AI／データパイプライン／リサーチ／監査ログ等）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・データ基盤を構築するためのモジュール群です。主な目的は以下です。

- J-Quants API からのデータ取得（株価、財務、JPXカレンダーなど）
- ETL（差分取得、保存、品質チェック）パイプライン
- ニュースの収集・NLP によるセンチメントスコア付与（OpenAI を利用）
- 市場レジーム判定（ETF の移動平均乖離 + マクロニュースセンチメント）
- ファクター計算・特徴量探索（リサーチ用ユーティリティ）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化

設計方針として、バックテスト時のルックアヘッドバイアス回避、冪等性（DB への保存）、外部 API 呼び出しのリトライ・レート制御、フェイルセーフ（API 失敗時はスキップや中立化）を重視しています。

---

## 主な機能一覧

- data
  - J-Quants クライアント（データ取得・保存・認証・レート制御）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS 取得、安全対策、トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（Zスコア正規化）
- ai
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースを合成して市場レジームを判定
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（将来リターン計算、IC、統計サマリー、ランク化）
- config
  - 環境変数/設定読み込み（.env 自動ロード、必須項目チェック）
- audit
  - 監査ログスキーマの作成 / DB 初期化ユーティリティ

---

## 必要条件 / 依存パッケージ（参考）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリのみで実装されている機能も多いですが、上記は主要外部依存です）

インストール例（仮の requirements）:
```
pip install duckdb openai defusedxml
```

※ 実際のパッケージ管理は pyproject.toml / requirements.txt を参照して下さい（本 README はコードベースから推定した内容です）。

---

## 環境変数（必須・任意）

config.Settings が参照する主要な環境変数：

必須（実行に必要）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード（本コードでは参照のみ）
- SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

OpenAI 関連（関数呼び出し時に api_key 引数で上書き可能）
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector 等が参照）

任意 / デフォルトあり
- KABUSYS_ENV           : "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABU_API_BASE_URL     : kabuAPI ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 をセットすると .env 自動読み込みを無効化

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml がある場所）を探索して `.env` → `.env.local` の順で自動ロードします（OS 環境変数が優先）。テスト等で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順（ローカル開発向け）

1. Python 3.10+ を用意する
2. 仮想環境を作る（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要なパッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）
4. .env を作成
   - リポジトリのルートに `.env.example` がある想定です。例を参考に `.env` を作成してください。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB のデータベースを初期化（監査ログ等）
   - 監査ログ専用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
6. （必要に応じて）J-Quants / OpenAI / kabuステーション の API キーやエンドポイントを確認

---

## 使い方（主要な例）

以下はライブラリをインポートして利用する簡単な例です。

- 日次 ETL を実行する（DuckDB 接続を渡す）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（ai.news_nlp.score_news）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {num_written}")
```

- 市場レジーム判定（ai.regime_detector.score_regime）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマの初期化（既存 DuckDB 接続に対して）
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

注意点
- OpenAI の呼び出しは API キー（OPENAI_API_KEY）を要求します。score_news / score_regime 共に api_key 引数で明示的に渡すこともできます。
- DuckDB の接続オブジェクトは各関数で前提にされるテーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）が存在していることを前提とします。スキーマ作成は別途実行してください（ETL の最初の run を通じて作成される場合があります）。

---

## ディレクトリ構成（抜粋）

リポジトリはおおむね以下のような構成です（src 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (他: strategy/ execution/ monitoring などを含む場合があるが本 README のコード抜粋では一部未提供)

ファイル単位で重要な処理:
- data/jquants_client.py : J-Quants API の取得・保存・認証・リトライ・レート制御
- data/pipeline.py : run_daily_etl を含む ETL 管理
- data/news_collector.py : RSS 収集と前処理（SSRF/サイズ上限/トラッキング除去）
- ai/news_nlp.py : ニュースを LLM でスコアリングするロジック（バッチ・検証・リトライ）
- ai/regime_detector.py : ETF MA とマクロニュースを合成する市場レジーム判定
- research/* : ファクター計算・IC/統計サマリー等

---

## 設計上の注意 / 運用上のポイント

- ルックアヘッドバイアス対策：多くの関数で datetime.today() / date.today() の直接参照を避け、呼び出し側が target_date を指定する設計です。バックテスト時は必ず過去のデータだけを参照しているか確認してください。
- 冪等性：J-Quants 等から取得したデータは ON CONFLICT DO UPDATE（重複上書き）で保存されます。監査ログも冪等に初期化できる設計です。
- API レート制御・リトライ：J-Quants と OpenAI 呼び出しにはリトライとレート制御（バックオフ・Retry-After など）が実装されています。
- セキュリティ：news_collector では SSRF 対策、受信サイズ上限、defusedxml による XML パース保護が実施されています。
- フェイルセーフ：外部 API 失敗時はゼロ・中立スコアで継続する等、パイプライン全体が完全停止しないよう配慮されています（ただし重要な環境変数未設定時は例外が発生します）。

---

## 開発・テストに関して

- OpenAI 呼び出し部はユニットテストでモックしやすいように _call_openai_api 等の関数分割やパラメータ注入が行われています。ユニットテストではこれらを patch して外部 API への実際のリクエストを避けてください。
- DuckDB を利用するため、テスト用に ":memory:" を渡してインメモリ DB を使うことができます（例: init_audit_db(":memory:")）。

---

必要であれば、README に以下を追加できます：
- 具体的なスキーマ（CREATE TABLE）の抜粋（監査ログなど）、
- 実行済み ETL のログ例、
- Docker / CI 用の設定例（GitHub Actions 等）、
- 実運用での監視・アラート設計（Slack 通知の使い方）、

追加希望があれば教えてください。