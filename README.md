# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータパイプライン、リサーチ、AI ベースのニュース評価、監査/発注トレーサビリティを備えた自動売買基盤のコードベースです。本リポジトリは DuckDB を中心としたローカルデータプラットフォームと、J-Quants / OpenAI / kabu ステーション 等の外部 API を組み合わせて、ETL → 研究（ファクター計算）→ シグナル生成 → 発注監査までを支援します。

主な設計方針：
- ルックアヘッドバイアスを避けること（日時の参照や DB クエリにおける排他条件に配慮）
- 冪等性（ETL / DB 保存は ON CONFLICT 等で安全に上書き）
- フェイルセーフ（外部 API エラー時は一部処理をスキップして継続）
- テスト容易性（外部呼び出しや内部関数をモックしやすい設計）

---

## 機能一覧

- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルートを探索）
  - 必須環境変数チェック（Settings クラス）
- データ収集・ETL（kabusys.data）
  - J-Quants API クライアント（fetch/保存関数、レートリミット・リトライ・トークン自動リフレッシュ）
  - 日次 ETL パイプライン（run_daily_etl: calendar, prices, financials の差分取得 + 品質チェック）
  - ニュース収集（RSS → raw_news）
  - マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化・監査 DB（signal_events / order_requests / executions）
- AI（kabusys.ai）
  - ニュース NLP（ニュース記事を OpenAI でセンチメント解析して ai_scores に保存）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを合成）
  - OpenAI 呼び出しはリトライや JSON モードを用いて堅牢に実装
- 研究（kabusys.research）
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索・IC 計算・将来リターン計算・Z スコア正規化ユーティリティ
- ユーティリティ
  - 統計関数（zscore_normalize 等）
  - DuckDB ベースの DB 初期化ヘルパー（監査 DB 初期化関数等）

---

## セットアップ手順

前提
- Python 3.10+（コードは型ヒントに union | を使用）
- DuckDB, OpenAI SDK, defusedxml 等の依存パッケージ

1. リポジトリをクローン / チェックアウト
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がない場合、最低限必要なパッケージは以下です：
     - duckdb
     - openai
     - defusedxml
   例：
   ```
   pip install duckdb openai defusedxml
   ```
   （実運用では pyproject.toml / requirements.txt を参照してインストールしてください）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置して設定を行います。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 用、関数呼び出しでも上書き可）
   - 任意/デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - .env の自動読み込み:
     - パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索し、
       `.env` → `.env.local` の順で環境を読み込みます。
     - テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データベースの初期化（監査 DB など）
   - 監査ログ用 DB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   - 既存の DuckDB 接続に監査スキーマを追加したい場合:
   ```python
   from kabusys.data.audit import init_audit_schema
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（基本例）

ここでは主なユースケースの簡単な利用例を示します。すべて Python API 経由で操作できます。

1. 設定オブジェクトにアクセス
```python
from kabusys.config import settings
print(settings.duckdb_path)        # Path オブジェクト
print(settings.jquants_refresh_token)  # 必須トークン（存在チェックあり）
```

2. DuckDB 接続を開いて日次 ETL を実行
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl は calendar、prices、financials の差分 ETL と品質チェックを順に実行し ETLResult を返します。

3. ニュースセンチメント解析（AI）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {n_written}")
```
- score_news は raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して ai_scores に書き込みます。
- API 呼び出しはリトライやレスポンスバリデーションを行い、失敗した銘柄はスキップします。

4. 市場レジームスコアの算出
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```
- ETF 1321 の MA200 乖離とマクロニュースセンチメントを 70:30 の重みで合成して market_regime テーブルへ保存します。
- API キー未設定時は ValueError を投げます（api_key 引数または環境変数 OPENAI_API_KEY を設定してください）。

5. 研究系ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

---

## よく使うユーティリティ / API の注意点

- 環境変数の自動ロード：
  - import kabusys.config 時にプロジェクトルート（.git / pyproject.toml）を探索して .env を読み込みます。
  - テストで自動読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- J-Quants クライアント（kabusys.data.jquants_client）：
  - レート制限（120 req/min）をモジュール内で制御します。
  - 401 を受けた場合はリフレッシュトークンで id_token を再取得して 1 回リトライします。
  - fetch_* 系はページネーション対応。save_* 系は ON CONFLICT による冪等保存。

- OpenAI（news_nlp / regime_detector）：
  - gpt-4o-mini と JSON Mode を利用します（response_format={"type": "json_object"}）。
  - レスポンスの JSON パースや API エラーに対して堅牢な処理を持ち、失敗時はスコアを 0 にフォールバックする等のフェイルセーフがあります。
  - テストしやすさのため、内部の API 呼び出し関数はモック可能な形で実装されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。

- データ品質チェック（kabusys.data.quality）：
  - 各チェックは QualityIssue のリストを返します。Fail-Fast ではなく問題の全件収集を行います。
  - ETL 実行時に run_quality_checks=True の場合は pipeline.run_daily_etl が品質チェックを実行して結果を ETLResult に格納します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成（抜粋）です。実際のファイル数は増える可能性があります。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの OpenAI スコアリング
    - regime_detector.py    — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch/save）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult の再エクスポート
    - news_collector.py     — RSS ニュース収集
    - calendar_management.py— マーケットカレンダー管理（is_trading_day 等）
    - quality.py            — データ品質チェック
    - audit.py              — 監査ログ（テーブル定義・初期化）
    - stats.py              — 汎用統計関数（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン / IC / サマリー 等

---

## 開発・運用上の注意点

- ルックアヘッド防止:
  - モジュールは内部で明示的な "today()" の参照を避け、target_date を引数として受け取る設計が多いです。バックテスト・再現性の観点で重要です。
- 環境依存:
  - .env の読み込みは import 時に行われるため、テスト環境では環境変数を明示的に操作するか KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- DB 操作:
  - DuckDB の executemany は空リストを受け付けないバージョンのため、空パラメータのチェックがコード中にあります（注意）。
- API キー管理:
  - OpenAI / J-Quants の API キーは秘密情報です。`.env` に保存する際は適切に管理してください。
- テスト容易性:
  - 外部ネットワーク呼び出しや内部 API 呼び出しはモックできるように実装されています（例えば _call_openai_api, _urlopen 等を patch）。

---

## トラブルシュート（簡易）

- .env が読み込まれない
  - プロジェクトルートが .git または pyproject.toml によって探索されます。ルート位置を確認してください。
  - 自動読み込みを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD がセットされていないか確認してください。

- OpenAI 呼び出しで失敗（429 等）
  - モジュールはリトライ実装がありますが、使用量が多い場合はレート制限に引っかかります。API キーのレートやバッチサイズを調整してください。

- DuckDB にスキーマがない / テーブルがない
  - ETL 実行前に必要テーブルを作成するスクリプト（schema init）や audit.init_audit_schema を実行してください。多くの save_* 関数はテーブル存在を前提としています。

---

この README はコードベースの主要設計・利用方法の概要を示しています。より詳細な仕様（DataPlatform.md, StrategyModel.md 等）が存在する想定であり、実運用前にそれらドキュメントを参照してください。質問や追加の利用例が必要であればお知らせください。