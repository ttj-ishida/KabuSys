# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
J-Quants からのデータ取得・ETL、ニュースの収集と LLM によるニュース NLP、研究用ファクター計算、監査ログ（オーディット）等を提供します。

主要な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API失敗時の継続）」「DuckDB を用いたローカルなデータ基盤」です。

---

## 機能一覧（概要）

- 環境設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数のチェック（settings オブジェクト）
- データ ETL（J-Quants）
  - 株価日足（raw_prices）・財務データ（raw_financials）・市場カレンダーの差分取得と保存
  - レートリミット・再試行・トークン自動リフレッシュ対応
  - ETL パイプライン（run_daily_etl）と個別ジョブ（run_prices_etl 等）
- データ品質チェック
  - 欠損、重複、スパイク（急騰/急落）、将来日付や非営業日のチェック
  - QualityIssue を返す（エラー/警告で分類）
- ニュース収集
  - RSS 取得（SSRF対策、gzip 対応、トラッキングパラメータ除去、記事IDは正規化URLのハッシュで冪等性）
  - raw_news への保存と銘柄紐付け処理の想定
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを集約して LLM に投げ、銘柄別センチメント（ai_scores）を生成（score_news）
  - マクロニュースを集めて市場レジーム（bull/neutral/bear）を判定（score_regime）
  - リトライ・レスポンスバリデーション・スコアクリッピングなど堅牢化
- 研究用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman rank）計算、統計サマリ、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ヘルパー
  - 監査用 DuckDB DB 初期化（init_audit_db / init_audit_schema）
- J-Quants クライアント
  - API 呼び出しユーティリティ（ページネーション、レート制御、401 自動リフレッシュ、保存関数）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `X | Y` を使用しているため）
- Git, pip

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて）pip install slack_sdk などの外部連携ライブラリを追加
   - 開発用に package としてインストールする場合:
     - pip install -e .

   ※プロジェクトに requirements.txt / pyproject.toml があればそちらからインストールしてください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml が存在するルート）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (任意、デフォルト有)
     - SLACK_BOT_TOKEN=your_slack_token
     - SLACK_CHANNEL_ID=your_slack_channel
     - DUCKDB_PATH=data/kabusys.duckdb  (任意)
     - SQLITE_PATH=data/monitoring.db     (任意)
     - PID_FILE_PATH=data/execution.pid   (任意)
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|...  (デフォルト: INFO)

   - `.env.example` をプロジェクトに含めている場合はそれを参照して作成してください（config._require が未設定時に ValueError を投げます）。

---

## 使い方（主な例）

以下はライブラリ関数を直接呼び出す簡単なコード例です。実運用ではログ設定や例外ハンドリング、監視を追加してください。

1. DuckDB へ接続して日次 ETL を実行（J-Quants から差分取得）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュース NLP（OpenAI を使って銘柄別スコア生成）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で OPENAI_API_KEY を参照
print(f"written scores: {n_written}")
```

3. 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数で解決
```

4. 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査用の DuckDB 接続
```

5. 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str("data/kabusys.duckdb"))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"} の dict リスト
```

---

## 重要な挙動・注意点

- 自動 .env ロード: パッケージインポート時にプロジェクトルートを探索して .env/.env.local を読み込みます。テスト時に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 利用:
  - news_nlp / regime_detector は OpenAI の JSON mode を利用する設計です。API レスポンスのバリデーションやリトライ実装がありますが、応答形式の変化に注意してください。
  - API キーは引数で明示するか環境変数 OPENAI_API_KEY を設定してください。
- DuckDB: ETL や監査ログは DuckDB を想定しています。ファイルパスは settings.duckdb_path で管理します。
- J-Quants:
  - get_id_token() は JQUANTS_REFRESH_TOKEN を使用して id_token を取得します。
  - API レート制限（120 req/min）に合わせて内部でスロットリングします。
- データ品質チェックは Fail-Fast ではなく、問題をすべて列挙して返す設計です。呼び出し側で結果を評価して対処してください。
- ルックアヘッドバイアス防止:
  - 各モジュールは date 引数を明示的に受け取り、内部で date.today() を直接参照しない（または必要箇所で設計上注意）方針です。バックテストなどでの使用に配慮されています。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージのエクスポート（data, strategy, execution, monitoring 等）
- config.py
  - 環境変数管理・settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py        -- ニュースの LLM スコアリング（score_news）
  - regime_detector.py -- マクロ + ETF ma200 で市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      -- J-Quants API クライアント + 保存ロジック
  - pipeline.py           -- ETL パイプライン（run_daily_etl 他）
  - etl.py                -- ETLResult 再エクスポート
  - news_collector.py     -- RSS 取得・前処理 & 保存ロジック
  - calendar_management.py-- 市場カレンダー管理（is_trading_day 等）
  - quality.py            -- データ品質チェック（QualityIssue）
  - audit.py              -- 監査ログテーブル DDL / 初期化
  - stats.py              -- 汎用統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py    -- Momentum / Value / Volatility 等の計算
  - feature_exploration.py-- 将来リターン・IC・統計サマリ等
- research/*、ai/* などはテスト・研究用に設計。実トレードの注文ロジック（execution）や戦略層（strategy）は別モジュールとして統合可能。

---

## さらに詳しい情報・開発者向け

- ログレベルは環境変数 LOG_LEVEL で制御します（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 実運用時は settings.is_live / is_paper / is_dev で挙動を分岐できます。
- テスト時のモック対象（例）
  - OpenAI 呼び出し関数は内部で分離されているため unittest.mock.patch で置き換えやすく設計されています（news_nlp._call_openai_api 等）。
- 新しい機能追加や API 変更を行う場合、ETL の冪等性・品質チェック・監査ログの整合性を壊さないよう注意してください。

---

必要であれば、README にサンプル .env.example、docker-compose の例、CI 用のテスト実行方法、具体的なスキーマ（DuckDB テーブル定義）や運用手順（cron / systemd unit / プロセスマネージャ）などを追記できます。どの情報を優先して追加しましょうか？