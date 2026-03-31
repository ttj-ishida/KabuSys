# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション などからのデータ取得、ETL、ニュース NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

## 概要
このリポジトリは日本株の自動売買やリサーチ基盤のためのユーティリティ群をまとめたパッケージです。主に以下を扱います。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と銘柄紐付け
- OpenAI を用いたニュースセンチメント評価（銘柄単位・マクロ）
- ETF とマクロセンチメントを組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック、監査ログ（トレーサビリティ）管理

プロジェクトは Look-ahead bias 回避や API レート制御、冪等性（INSERT ... ON CONFLICT）等を設計方針として組み込んでいます。

## 機能一覧
- data/jquants_client:
  - J-Quants からのデータ取得（株価日足、財務、上場情報、マーケットカレンダー）
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）
  - レートリミット／リトライ／トークン自動更新対応
- data/pipeline:
  - 日次 ETL パイプライン（run_daily_etl） - カレンダー→株価→財務→品質チェックを実行
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- data/news_collector:
  - RSS 取得、記事正規化、SSRF 防止、raw_news への冪等保存
- ai/news_nlp, ai/regime_detector:
  - gpt-4o-mini を用いたニュースセンチメント（銘柄単位の ai_score）
  - ETF(1321)のMA乖離とマクロセンチメントの合成による市場レジーム判定
- research:
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・IC 計算・統計サマリー
- data/quality:
  - 欠損・スパイク・重複・日付不整合のチェック
- data/audit:
  - 注文・約定等の監査テーブル定義・初期化ユーティリティ（DuckDB）

## 必要条件（主な依存）
- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai (OpenAI の最新版 SDK を利用する想定)
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード 等）

（実際の requirements.txt / pyproject.toml をプロジェクトに合わせて用意してください）

## 環境変数 / 設定
パッケージは環境変数またはプロジェクトルートの `.env` / `.env.local` から設定を自動読み込みします（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知の Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の引数に渡すことも可能）

その他:
- KABUSYS_ENV: environment（development / paper_trading / live）。既定は `development`
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）

注意: 必須環境変数が不足すると Settings プロパティからアクセスした際に ValueError が送出されます。

## セットアップ手順（開発環境向け）
1. リポジトリをチェックアウト
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - あるいはプロジェクトの pyproject.toml / requirements.txt があればそれを使用
4. パッケージを編集可能モードでインストール（オプション）
   - pip install -e .
5. 環境変数を準備
   - プロジェクトルートに `.env` と `.env.local` を作成（`.env.example` を参照）
   - 必須キーを設定（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

## 使い方（サンプル）
以下は Python REPL やスクリプトから利用する一例です。

- Settings の利用
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB に接続して ETL を実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントをスコアリング（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n = score_news(conn, target_date=date(2026, 3, 19), api_key=settings.jquants_refresh_token)  # 例: api_key を直接渡す
```

- 市場レジーム判定（ETF 1321 + マクロ）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19), api_key="YOUR_OPENAI_API_KEY")
```

- 監査用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル(signal_events, order_requests, executions) が作成されます
```

- ニュース収集（RSS 取得の例）
news_collector モジュールは fetch_rss 等の関数を提供しています。RSS の URL は `DEFAULT_RSS_SOURCES` を参照して追加可能です（SSRF 対策やサイズ上限等を実装済み）。

## 注意事項 / 運用上のポイント
- OpenAI 呼び出しは API コスト・レート制限に注意してください。score_news / score_regime はリトライ・フェイルセーフ設計です（失敗時はスコア 0.0 等で継続）。
- ETL は差分取得およびバックフィル（デフォルト 3 日）を行い、J-Quants の API レート制限を厳守するための RateLimiter を組み込んでいます。
- 本システムは本番口座（live）での発注機能を含む設計要素があります。実際の発注・自動売買を行う場合は十分なテストとリスク管理を行ってください。settings.is_live / is_paper / is_dev を利用して環境ごとに挙動を分離できます。
- パッケージは Look-ahead bias を避けるため、内部で date.today()/datetime.today() を直接参照しない設計を心がけています。呼び出し側で対象日 (target_date) を明示的に与えて処理してください。

## ディレクトリ構成（主要ファイル）
以下は主要モジュールの構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（銘柄別スコア）
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント / 保存関数
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL の公開インターフェース (ETLResult)
    - news_collector.py              — RSS 収集と前処理
    - calendar_management.py         — マーケットカレンダー管理
    - stats.py                       — 統計ユーティリティ（z-score 等）
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログ初期化・DDL
  - research/
    - __init__.py
    - factor_research.py             — モメンタム・バリュー・ボラティリティ等
    - feature_exploration.py         — 将来リターン・IC・統計サマリー
  - monitoring/                       — （監視・メトリクス等、未掲載の想定モジュール）
  - execution/, strategy/ 等         — （発注・戦略関連モジュール想定）

（実際のファイルツリーはリポジトリルートの構成に合わせて参照してください）

## 開発・テスト
- ユニットテストや API 呼び出し箇所はモック可能な設計（_call_openai_api の差し替え、news_collector._urlopen のモックなど）になっています。
- テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env 自動読み込みを無効にするとテスト制御が容易です。

---

この README は主要機能と利用開始に必要な情報をまとめた概要です。詳細な API 使用法やスキーマ、運用手順は各モジュールの docstring（ソース内コメント）やプロジェクトの設計ドキュメント（StrategyModel.md / DataPlatform.md など）を参照してください。必要であれば README に追記・具体例（SQL スキーマ、実行スクリプト例等）を追加します。