# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL、ニュース収集・NLP（OpenAI）、マーケットカレンダー管理、ファクター計算、監査ログ（トレーサビリティ）など、取引戦略や研究ワークフローに必要なコンポーネントを提供します。

---

## 主要な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェックと型変換ユーティリティ
- データプラットフォーム（DuckDB ベース）
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動更新、レートリミット・リトライ）
  - ETL パイプライン（prices / financials / calendar の差分取得・保存）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF 対策、トラッキングパラメータ除去）
  - 監査ログスキーマ初期化（signal / order_request / executions）
- AI（OpenAI）機能
  - ニュースの銘柄別センチメントスコアリング（news_nlp.score_news）
  - マクロニュース + ETF MA に基づく市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しの堅牢なリトライ・パース戦略
- 研究ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - 汎用統計ユーティリティ（zscore 正規化）

---

## 動作環境 / 依存関係

- Python 3.10 以上（型注釈に `X | Y` を使用）
- 主な依存パッケージ（例）
  - duckdb
  - openai （OpenAI Python SDK）
  - defusedxml
- 標準ライブラリの urllib を主に利用しているため requests は必須ではありませんが、運用環境に合わせて追加してください。

（プロジェクトの配布側で requirements.txt / pyproject.toml を用意する想定です）

---

## セットアップ手順

1. リポジトリをクローン／取得
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - Linux/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要なパッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを使用してください）

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_station_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

   主な環境変数（Settings 経由で参照）
   - JQUANTS_REFRESH_TOKEN（必須）
   - OPENAI_API_KEY（AI 機能を使う場合は必須）
   - KABU_API_PASSWORD（kabuステーション API を使う場合）
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視用データベース、デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / CPU/MEM/DISK 閾値など（監視設定）
   - KABUSYS_ENV（development / paper_trading / live）
   - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## 使い方（簡単な例）

以下は基本的なライブラリの使い方例です。実運用時はログや例外処理を適宜追加してください。

- DuckDB 接続の作成（デフォルトのパスを使用）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（差分取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジームを判定して market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

- 研究用ユーティリティの利用例（モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# 返り値は dict のリスト: [{"date": ..., "code": ..., "mom_1m": ..., ...}, ...]
```

注意点:
- AI 機能（news_nlp / regime_detector）は OpenAI API キーを必要とします（引数で渡すか環境変数 OPENAI_API_KEY を設定してください）。
- ETL / save_* 関数は対象の DuckDB 上に適切なスキーマ（テーブル）を作成済みであることを前提とします。スキーマ作成用の初期化処理（data.schema 等）が別途ある想定です（本コードベースでは監査用スキーマ初期化関数が含まれています）。
- auto .env 読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml が目印）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイルの説明）

（リポジトリ内 `src/kabusys/` を抜粋）

- __init__.py
  - パッケージのエントリ。バージョンやサブパッケージの公開設定。

- config.py
  - 環境変数・設定管理。.env 自動ロード、必須項目チェック、Settings クラスを提供。

- ai/
  - news_nlp.py : ニュースの銘柄別センチメントスコアリング（OpenAI を用いる）
  - regime_detector.py : ETF（1321）200日MA とマクロニュースセンチメントで市場レジーム判定

- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得・保存ロジック、リトライ・レート制御）
  - pipeline.py : ETL パイプライン（run_daily_etl / 個別 ETL ジョブ）
  - etl.py : ETLResult の再エクスポート
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - quality.py : データ品質チェック群（欠損・重複・スパイク・日付不整合）
  - calendar_management.py : マーケットカレンダー管理（is_trading_day 等）
  - news_collector.py : RSS フィード収集・前処理・保存ロジック（SSRF 対策、トラッキング除去）
  - audit.py : 監査ログ用スキーマ定義と初期化（signal/order_requests/executions）
  - その他（schema 初期化等は別ファイルで提供される想定）

- research/
  - __init__.py
  - factor_research.py : モメンタム・ボラティリティ・バリュー計算
  - feature_exploration.py : 将来リターン／IC／統計サマリー等

---

## 運用上の注意と設計方針（抜粋）

- Look-ahead bias 回避のため、日付計算は target_date を引数に取る形で実装され、内部で datetime.today() を参照しない方針です（バックテストに適した設計）。
- AI 呼び出しは冪等ではなく、レスポンスのパース失敗や API エラーに対してはフェイルセーフで 0.0 を返す／スキップするなど堅牢化されています。
- J-Quants クライアントは ID トークンをキャッシュし、401 時に自動リフレッシュします。API レート（120 req/min）を尊重する制御を内蔵しています。
- ニュース収集は SSRF 対策と受信サイズ制限、ID の SHA-256 ハッシュ生成による冪等化を行っています。
- ETL と品質チェックは独立して動作する設計で、ひとつのステップが失敗しても他が続行され結果が集計されるようになっています。

---

## 貢献 / テスト

- 開発用にローカルで DuckDB ファイルを用意し、.env に適切なトークン（ダミーでも可）を設定して単体関数を試すことができます。
- テスト時は自動 .env 読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しや外部ネットワーク依存部分はモックしやすいように設計されています（内部の _call_openai_api や _urlopen 等を patch 可能）。

---

必要であれば、README に含める具体的な CLI コマンド例やスキーマ初期化 SQL、典型的な .env.example を追記できます。どの内容を優先して追加しますか？