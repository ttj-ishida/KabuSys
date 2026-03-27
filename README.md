# KabuSys

日本株のデータプラットフォームと自動売買支援を目的としたライブラリ群です。  
ETL（J-Quants からのデータ取得）／ニュース収集と AI によるセンチメント評価／市場レジーム判定／リサーチ用ファクター計算／監査（オーディット）ログなどを提供します。

---

## 主な特徴

- データ収集（J-Quants API 経由）
  - 株価日足（OHLCV）、財務データ、上場情報、JPX カレンダーを差分取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ対応

- ニュース収集・NLP
  - RSS からニュースを安全に収集（SSRF対策、XML 脆弱性対策、トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄単位のセンチメント（ai_scores）評価（バッチ処理・リトライ）

- 市場レジーム判定
  - ETF（1321）の200日MA乖離（70%）とマクロニュースセンチメント（30%）を合成して日次レジーム判定（bull/neutral/bear）

- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付整合性チェックを実施

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等ファクター計算、将来リターン・IC 計算、ファクター統計サマリー
  - Z-score 正規化ユーティリティ

- 監査（Audit）ログ
  - signal → order_request → execution までのトレーサビリティを保持する監査テーブルを DuckDB に初期化・管理

- 設計上の配慮
  - ルックアヘッドバイアスの排除（datetime.today() を直接参照しない等）
  - 冪等性（DB 書き込みは ON CONFLICT / upsert）
  - テスト容易性（API 呼び出しの差し替えが可能 / 明確な境界）

---

## 必要要件 / 依存パッケージ

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml

簡易インストール例:

```
python -m pip install duckdb openai defusedxml
# またはプロジェクト配布パッケージがある場合:
# pip install -e .
```

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. 仮想環境を作成して依存をインストール

3. 環境変数 / .env を用意
   - `src/kabusys/config.py` はプロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を自動読み込みします（ただし環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化可能）。
   - 必須環境変数（実行する機能により異なる。最低限の例）:
     - JQUANTS_REFRESH_TOKEN（J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD（kabuステーション API パスワード）
     - SLACK_BOT_TOKEN（Slack 通知を使う場合）
     - SLACK_CHANNEL_ID（Slack 通知先）
   - オプション / 推奨:
     - OPENAI_API_KEY（AI モジュールを利用する際。関数引数で渡すことも可能）
     - KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL = DEBUG | INFO | ...
     - DUCKDB_PATH（デフォルト `data/kabusys.duckdb`）
     - SQLITE_PATH（デフォルト `data/monitoring.db`）

例 `.env`:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本的なコード例）

※ ここでは duckdb を直接使う例を示します。各関数は duckdb の接続オブジェクト（DuckDBPyConnection）を受け取ります。

- ETL（日次パイプライン）実行例:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント（個別実行）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# APIキーを引数で渡すことも可能: score_news(conn, date(2026,3,20), api_key="sk-...")
n_written = score_news(conn, target_date=date.today())
print("written", n_written)
```

- 市場レジーム判定:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date.today())
```

- 監査 DB 初期化（監査専用 DB を作る例）:

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を使うか、別パスを指定
conn = init_audit_db(settings.duckdb_path)
# conn を用いて監査テーブルにアクセス可能
```

- 研究モジュール（ファクター計算）の利用例:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date": ..., "code": ..., "mom_1m": ..., ...}, ...] のリスト
```

---

## よく使うモジュール（抜粋）

- kabusys.config
  - settings: 環境変数ベースの設定アクセサ（例: settings.duckdb_path, settings.env）

- kabusys.data
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / ETLResult
  - jquants_client: J-Quants API 呼び出しと DuckDB 保存ユーティリティ
  - news_collector: RSS 取得・正規化・raw_news 保存
  - calendar_management: 営業日ロジック（is_trading_day, next_trading_day 等）
  - quality: データ品質チェック（check_missing_data, check_spike, ...）
  - audit: 監査テーブル初期化（init_audit_schema / init_audit_db）

- kabusys.ai
  - news_nlp.score_news: ニュースを用いた銘柄スコアリング
  - regime_detector.score_regime: 市場レジーム判定

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## ディレクトリ構成（主要ファイル）

（リポジトリの `src/kabusys` 以下を抜粋）

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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - audit.py
    - audit.py (監査関連のDDL・初期化関数)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
    - ...（リサーチ関連）

（上記は主要モジュールの抜粋です。細かいユーティリティは各サブパッケージの中にあります）

---

## 運用上の注意 / 設計上のポイント

- ルックアヘッドバイアス回避
  - 多くの処理（news window, ma 計算, ETL など）は内部で target_date を明示的に受け取り、datetime.today() を直接参照しない設計です。バックテスト等での再現性に配慮しています。

- 冪等性
  - J-Quants から取得したデータは DuckDB へ ON CONFLICT で upsert します。ETL は差分取得・バックフィルをサポート。

- レート制限・リトライ
  - J-Quants クライアントは固定間隔レート制御と指数バックオフリトライを備えています。
  - OpenAI 呼び出しもリトライロジックやフェイルセーフ（失敗時は中立スコア等）を実装。

- セキュリティ
  - RSS 収集での SSRF 対策、defusedxml による XML パース保護、受信サイズ制限などを実装。

- テスト容易性
  - 外部 API 呼び出し部分は差し替え可能（モジュール内の呼び出しをモックする想定）。

---

## トラブルシューティング

- 環境変数が読み込まれない場合:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されていないか確認
  - `.env` / `.env.local` がプロジェクトルート（.git や pyproject.toml のあるディレクトリ）に存在するか確認

- OpenAI / J-Quants API エラー:
  - ネットワークやクレデンシャル誤りが多いです。ログ（LOG_LEVEL を DEBUG に設定）を確認してください。
  - J-Quants API は 401 時にトークン自動更新を試みますが、refresh token が正しくないと失敗します。

---

## 参考

- 設定アクセス: `from kabusys.config import settings`
- ETL 結果型: `from kabusys.data.etl import ETLResult`（pipeline から再エクスポート）
- AI モジュールは OpenAI の API キーを環境変数 `OPENAI_API_KEY` で受け取ります（関数引数で渡すことも可）。

---

この README はコードベース内のドキュメントと設計コメントを基に作成しています。より詳細な運用手順やデプロイ方法、CI/CD、モニタリング連携（Slack 通知など）は運用方針に合わせて追加してください。