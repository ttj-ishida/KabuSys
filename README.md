# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ（プロトタイプ）

このリポジトリは、J-Quants API を用いたデータ ETL、ニュース収集・NLP、LLM を用いたニュース/マクロ評価、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを含む日本株向けの内部ライブラリ群です。DuckDB をデータストアに用いる設計になっています。

主な用途は以下のとおりです。
- 日次 ETL（株価・財務・市場カレンダー）の自動取得および保存
- ニュースの収集・前処理と OpenAI による銘柄センチメント評価（ai_scores 生成）
- マクロセンチメントと ETF MA 乖離から市場レジーム判定（bull/neutral/bear）
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 取引フローの監査テーブル（signal → order_request → execution）の初期化ユーティリティ

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存関数、トークン自動リフレッシュ、レート制御、リトライ）
  - pipeline: ETL（run_daily_etl）と個別 ETL（prices, financials, calendar）
  - news_collector: RSS 収集・前処理（SSRF 対策、トラッキング除去、gzip 対応）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログ用テーブル作成 / 初期化ユーティリティ（init_audit_db / init_audit_schema）
  - stats: z-score 正規化などの統計ユーティリティ
- ai/
  - news_nlp: ニュース記事を銘柄ごとにまとめて OpenAI に問い合わせ、ai_scores に書き込む（score_news）
  - regime_detector: ETF（1321）200日 MA 乖離とマクロニュース LLM センチメントを合成して市場レジームを算出（score_regime）
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）、統計サマリー、ランク変換 等
- config: 環境変数読み込み（.env 自動読み込み）と Settings オブジェクト
- その他ユーティリティ群

---

## 必要条件

- Python >= 3.10
- 推奨パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml
  - requests（必要に応じて）
  - slack-sdk（Slack 通知を行う場合）
  - その他テストやユーティリティに応じたパッケージ

（プロジェクトに requirements.txt がある想定で、適宜バージョンを合わせてください）

例:
```bash
python -m pip install "duckdb>=0.7" "openai>=1.0" "defusedxml" "requests" "slack-sdk"
```

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install -r requirements.txt
   # または個別インストール:
   pip install duckdb openai defusedxml
   ```
4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと、kabusys.config が自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低限必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_station_api_password
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb  # デフォルト
     - SQLITE_PATH=data/monitoring.db    # デフォルト
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - サンプル .env（プロジェクトルートに配置）
     ```
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB ファイルや監査 DB の初期化（必要に応じて）
   - 監査ログ専用 DB を作る場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn は duckdb 接続オブジェクト
     ```

---

## 使い方（主要な例）

以下はライブラリの代表的な呼び出し例です。実行前に環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を必ず設定してください。

- DuckDB に接続して日次 ETL を実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # デフォルトパスと一致させる
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} ai scores")
```
- マーケットレジーム判定（regime score）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査スキーマ初期化（既存 DB へ追加）:
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- 研究用にファクターを計算する例:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意点:
- score_news / score_regime などは OpenAI API を呼び出します。テスト時は内部の _call_openai_api をモックしてください（README にある関数の docstring にも指示があります）。
- config.Settings は .env を自動でロードしますが、自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要ファイル／ディレクトリ（抜粋）:

- src/
  - kabusys/
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
      - pipeline.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/*.py (factor / feature ユーティリティ)
    - other modules...
- requirements.txt (想定)

重要モジュールの役割まとめ:
- kabusys.config: .env 自動読み込み、Settings（環境変数管理）
- kabusys.data.jquants_client: J-Quants API 通信・保存ロジック（rate limiting / retry / token refresh）
- kabusys.data.pipeline: ETL のエントリポイント（run_daily_etl 等）
- kabusys.data.news_collector: RSS ニュース収集・前処理（SSRF 対策あり）
- kabusys.ai.news_nlp: ニュースを銘柄別に集計して OpenAI で評価（score_news）
- kabusys.ai.regime_detector: マクロニュース + ETF MA を用いた市場レジーム判定（score_regime）
- kabusys.research.*: ファクター計算・解析ユーティリティ
- kabusys.data.audit: 取引監査テーブルの DDL と初期化ユーティリティ

---

## 実装上の注意点 / 設計原則

- ルックアヘッドバイアスの回避: 多くの処理は date / target_date を明示的に受け取り、datetime.today() / date.today() を無差別に参照しないように設計されています。バックテストや再現可能性に配慮しています。
- 冪等性: J-Quants データ保存、監査テーブル初期化等は冪等に設計されています（ON CONFLICT 等）。
- フェイルセーフ: OpenAI API の呼び出しや外部 API 呼び出しでの失敗は、可能な範囲でフォールバック（スコア 0.0 等）して処理継続する設計です。
- セキュリティ: news_collector は SSRF 対策・XML インジェクション対策（defusedxml）・受信サイズ制限などを実装しています。
- テスト容易性: OpenAI 呼び出し部分は内部の _call_openai_api を patch して置き換えられる設計です。

---

## よくある質問 / トラブルシュート

- .env が読み込まれない
  - config.py がプロジェクトルート（.git または pyproject.toml を基準）を探索して .env を読み込みます。テスト時や明示的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI のレスポンスでエラーやパース失敗が出る
  - ラベル化や JSON 解析に失敗した場合は警告ログを出してフォールバックする実装です。実運用ではリトライ設定やログ監視を行ってください。
- DuckDB の接続やパスについて
  - settings.duckdb_path でデフォルトパスを読みます。必要であれば環境変数 DUCKDB_PATH を設定してください。

---

この README はコードベースの主要点をまとめたものです。さらに詳しい仕様（DataPlatform.md, StrategyModel.md 等）は設計文書をご参照ください。必要であれば README をより実運用向けに拡張（デプロイ手順、cron / Airflow でのスケジュール例、Slack 通知設定など）します。