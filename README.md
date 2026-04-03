# KabuSys

KabuSys は日本株のデータ取得・前処理・リサーチ・AI スコアリング・監査ログ設計を含む自動売買プラットフォームのコアライブラリです。本リポジトリは以下を主な目的として提供します。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- RSS ニュース収集と銘柄ごとの LLM ベースのセンチメントスコアリング
- 市場レジーム判定（ETF MA + マクロニュースの LLM 評価の合成）
- ファクター計算・特徴量探索（モメンタム / ボラティリティ / バリュー 等）
- データ品質チェック、監査ログ（シグナル→発注→約定のトレース）
- DuckDB をデータレイク / 監査 DB として使用

バイアス防止やフェイルセーフを考慮した設計方針（ルックアヘッドバイアス回避、API リトライ、冪等保存など）を採用しています。

---

## 主な機能一覧

- data/
  - jquants_client：J-Quants API クライアント（ページネーション、認証リフレッシュ、レート制御、DuckDB への冪等保存）
  - pipeline：日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
  - news_collector：RSS 収集、SSRF 対策、記事前処理、raw_news へ保存
  - calendar_management：JPX マーケットカレンダー管理（営業日判定・next/prev/get）
  - quality：データ品質チェック（欠損、重複、スパイク、日付整合性）
  - audit：監査ログ用スキーマ定義と初期化（signal_events, order_requests, executions）
  - stats：z-score 正規化など汎用統計ユーティリティ

- ai/
  - news_nlp：ニュース群を LLM に投げて銘柄別センチメントを ai_scores に保存
  - regime_detector：ETF(1321)の200日MA乖離とマクロニュース LLM を合成して日次市場レジーム判定を market_regime に保存

- research/
  - factor_research：モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration：将来リターン計算、IC（情報係数）、統計サマリ等

- config.py：環境変数管理と自動 .env ロード（プロジェクトルートの .env / .env.local を優先読み込み。無効化可能）

---

## 必要条件

- Python 3.10 以上（型アノテーションで `X | None` を使用しているため）
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS XML の安全パース）
- 標準ライブラリの urllib 等を利用（追加外部依存は最小限）

推奨インストールパッケージ（例）
- duckdb
- openai
- defusedxml

例:
pip install duckdb openai defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

2. 必要パッケージのインストール
   pip install duckdb openai defusedxml

3. 環境変数設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと、自動で読み込まれます（起動時に settings モジュールが読み込まれるとき）。

   主要な環境変数（最低限必要なもの）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL の認証に使用）
   - OPENAI_API_KEY: OpenAI API キー（AI スコアリング・レジーム判定に使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注実装時に使用）
   - KABU_API_BASE_URL: kabu ステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視設定
   - KABUSYS_ENV: 環境 ('development' | 'paper_trading' | 'live')
   - LOG_LEVEL: ログレベル（'DEBUG','INFO','WARNING','ERROR','CRITICAL'）

   .env の自動読み込みを無効化する場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリ作成（必要に応じて）
   mkdir -p data

---

## 基本的な使い方（コード例）

以下はライブラリ API を直接呼ぶ簡単な例です。実行前に環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定してください。

- DuckDB 接続の準備と日次 ETL 実行

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# デフォルトの duckdb ファイルパスは config.settings.duckdb_path
conn = duckdb.connect("data/kabusys.duckdb")

# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（ai.news_nlp.score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- 市場レジーム判定（ai.regime_detector.score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査 DB 初期化（独立した監査用 DB を使う場合）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

注記:
- OpenAI 呼び出し部分はテストのためにモックしやすく設計されています（モジュール内の _call_openai_api をパッチ可能）。
- DuckDB に存在するテーブルスキーマはデータ移入/初期化の別モジュール（本 README の範囲外）で準備する前提です。ETL 実行前に必要なテーブルスキーマを準備してください（save_* 関数は ON CONFLICT を使うため既存スキーマと互換性が必要）。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY           : OpenAI API キー（AI スコアリングで使用）
- KABU_API_PASSWORD        : kabu ステーション API パスワード
- KABU_API_BASE_URL        : kabu API のベース URL（オプション）
- DUCKDB_PATH              : DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH              : SQLite 監視 DB（default: data/monitoring.db）
- KABUSYS_ENV              : 'development' | 'paper_trading' | 'live'（default: development）
- LOG_LEVEL                : 'INFO' 等（default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると .env 自動読み込みを無効化

config.Settings クラスを通じてコード内から参照できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - audit initialization utilities
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research と data 間の統計ユーティリティ参照（zscore_normalize など）

（上記は主要モジュールのみ抜粋しています。実装ファイルを参照してください。）

---

## 開発時の注意点 / 設計上のポイント

- ルックアヘッドバイアス回避:
  - 多くの処理（news ウィンドウ計算、MA 計算、ETL target_date の扱いなど）は現時点の時刻を直接参照せず、target_date を明示的に与えることでバックテスト時の情報フローを制御します。
- 冪等性:
  - DuckDB への保存は ON CONFLICT 句で上書きする設計。ETL は差分取得を行い、部分失敗時でも既存データを不要に削除しないよう配慮しています。
- OpenAI / 外部 API:
  - レート制御・リトライ・5xx ハンドリングを実装。API 失敗時はフォールバック（ゼロスコア等）で続行する設計です（フェイルセーフ）。
- セキュリティ:
  - RSS 取得で SSRF 対策（リダイレクト検査・プライベートアドレス拒否）、defusedxml による安全な XML パースを実装。

---

## テストとモック

- OpenAI に対する呼び出しは各モジュール内の `_call_openai_api` を unittest.mock.patch 等で差し替えることで簡単にモック可能です。
- jquants_client の HTTP 層は urllib を用いているため、HTTP レスポンスをスタブ化する場合は urllib.request のオープナー等をモックしてください。

---

## 参考 / 今後の拡張

- 発注実行（kabu ステーションとの実際の注文送信）やポジション管理、リスク管理モジュールは別途実装して統合します。
- CI 用の requirements.txt / pyproject.toml、実行用 CLI スクリプト、Dockerfile などを追加すると運用が容易になります。

---

問題や改善点、追加してほしい利用例があれば教えてください。必要に応じて README を拡張してセットアップの具体的なコマンドやサンプル .env.example を追記します。