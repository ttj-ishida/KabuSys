# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants / kabu API 等からのデータ取得、ETL、ニュースNLP（OpenAI 経由）、研究用ファクター計算、監査ログ/発注追跡などを含むモジュール群を提供します。

バージョン: 0.1.0

## 概要

KabuSys は以下の用途を想定した Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータ保存（冪等保存、品質チェック付き）
- ニュース収集・NLP スコアリング（OpenAI を用いたセンチメント評価、銘柄別スコア化）
- 市場レジーム判定（ETF MA とマクロニュースセンチメントの合成）
- 研究用途のファクター計算（モメンタム / ボラティリティ / バリュー等）と解析ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ生成と初期化
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上のポイント:
- ルックアヘッドバイアスを防ぐ実装（内部で date.today()/datetime.today() を直接参照しない等）
- API 呼び出しはリトライ・バックオフ・フェイルセーフを考慮
- DuckDB への書き込みはなるべく冪等（ON CONFLICT）で実行
- テスト容易性を考えた抽象化（API 呼び出し箇所を差し替え可能）

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants 連携: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - 保存ユーティリティ: save_daily_quotes, save_financial_statements, save_market_calendar

- データ品質
  - 欠損・重複・スパイク・日付不整合検出（quality モジュール）
  - ETL 結果を表す ETLResult（監査ログ用辞書変換対応）

- ニュース & NLP（OpenAI）
  - RSS 収集（news_collector）
  - 銘柄別ニュース統合 → OpenAI（gpt-4o-mini）でセンチメント算出（news_nlp.score_news）
  - マクロニュースと ETF MA を使った市場レジーム判定（ai.regime_detector.score_regime）

- 研究（research）
  - モメンタム / ボラティリティ / バリューファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化

- 監査・トレーサビリティ
  - 監査用スキーマ定義と初期化（data.audit.init_audit_schema / init_audit_db）
  - signal_events / order_requests / executions テーブルとインデックス

- 設定管理
  - 環境変数を .env / .env.local から自動読み込み（config.Settings）
  - 必須環境変数の検証とデフォルト設定

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型ヒントに | を使用）
- システムに DuckDB と必要な依存パッケージをインストールできること

1. リポジトリをクローンしてパッケージをインストール（開発モード例）
   - pipenv/poetry 等を使う運用も想定できますが、最低限 pip で依存を入れてください。

   ```
   git clone <repo>
   cd <repo>
   pip install -e .
   ```

2. 必要な Python パッケージ（一例）
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに .env（および必要に応じて .env.local）を配置すると自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - SLACK_BOT_TOKEN: Slack 通知用トークン（未使用コンポーネントがあれば不要）
   - SLACK_CHANNEL_ID: Slack チャネル ID
   - KABU_API_PASSWORD: kabu API のパスワード
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

   任意 / デフォルトあり
   - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
   - KABU_API_BASE_URL デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH デフォルト: data/kabusys.duckdb
   - SQLITE_PATH デフォルト: data/monitoring.db
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, LOG_LEVEL 等

   .env の例（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ準備
   - 監査ログ用 DB を初期化する例:

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # 以降 conn を利用して監査テーブルが存在する状態になります
   ```

---

## 使い方（簡単な例）

※ 実行は各自の環境設定（.env / 環境変数）を整えてから行ってください。

- DuckDB 接続を作って日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を None にすると今日を対象（内部で取引日調整あり）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの銘柄別センチメントを算出する（OpenAI API キー必須）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"scored {n_written} codes")
```

- 市場レジームを算出して保存する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB を初期化して接続を取得する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

- config.Settings の利用例

```python
from kabusys.config import settings
print(settings.duckdb_path)      # Path('data/kabusys.duckdb')
print(settings.is_live)          # 環境が 'live' の場合 True
```

---

## 実装上の注意・運用ヒント

- OpenAI呼び出しは gpt-4o-mini（JSON mode）を想定しています。API レート・コストに注意してください。
- news_nlp と regime_detector は API 失敗時にフェイルセーフ（スコア=0 等）で継続する設計です。重大な失敗はログで監視してください。
- J-Quants API はレート制限（120 req/min）を守るためモジュール内でスロットリングを行います。大量データ取得時は時間がかかります。
- DuckDB に対する executemany の呼び出しは空リストを渡すと不正になるバージョンがあるため、実装側でチェック済みです。
- news_collector は SSRF 対策・レスポンスサイズ制限等の安全対策を備えています。外部 RSS を追加する際もホワイトリスト運用を推奨します。
- 自動 .env 読み込みはプロジェクトルート (.git または pyproject.toml を探索) を基準に行います。CI やテストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要モジュールのツリー（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py            # 銘柄別ニュースセンチメント算出（OpenAI）
    - regime_detector.py     # 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得 + 保存）
    - pipeline.py            # ETL パイプライン（run_daily_etl など）
    - etl.py                 # ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py      # RSS 収集・前処理
    - calendar_management.py # マーケットカレンダー管理・営業日判定
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - quality.py             # データ品質チェック
    - audit.py               # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     # 各種ファクター計算（momentum/value/volatility）
    - feature_exploration.py # 将来リターン、IC、統計サマリー等
  - execution/                # （発注・実行ロジック用のパッケージ想定）
  - monitoring/               # （監視・アラート用のパッケージ想定）

（実際のリポジトリでは上記に加えてテスト・ドキュメント・スクリプト等が存在する可能性があります）

---

## 参考情報

- 環境変数読み込み順:
  - OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 設計注記: 各モジュールの docstring に設計方針や想定動作、フェイルセーフの挙動が詳細に記載されています。実運用時はログ（INFO/WARNING/ERROR）を必ず監視してください。

---

必要ならば README にサンプル .env.example ファイルや、Cron/airflow 用の簡易ジョブ定義、より詳細な利用例（ETL スケジュール、監査ログの参照方法など）も追加できます。どの追加ドキュメントが必要か教えてください。