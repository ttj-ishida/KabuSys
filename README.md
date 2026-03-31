# KabuSys

日本株向けのデータ基盤・AI支援・リサーチ・監査を備えた自動売買支援ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI 使用）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログスキーマなどを提供します。

主な設計方針：
- ルックアヘッドバイアス防止（関数内で datetime.today()/date.today() を安易に参照しない）
- 冪等性（DB 保存は ON CONFLICT 等で上書き）
- 外部 API 呼び出しに対するリトライ・レート制御・フェイルセーフ
- セキュリティ考慮（SSRF 対策等）

バージョン: 0.1.0

---

## 主要機能一覧

- データ ETL（J-Quants API）
  - 日次株価（raw_prices）/ 財務（raw_financials）/ 市場カレンダー（market_calendar）の差分取得・保存
  - ページネーション・トークンリフレッシュ・レート制御・リトライ実装
- ニュース収集・NLP
  - RSS 収集（SSRF 対策・URL 正規化・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いたセンチメントスコア算出（ai_scores テーブル）
- 市場レジーム判定
  - ETF 1321 の MA200 乖離（70%）とマクロニュース LLM 評価（30%）を合成して日次レジーム判定（bull/neutral/bear）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損検出、スパイク検出、重複チェック、日付整合性チェック
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ
- コンフィグ管理
  - .env / .env.local / OS 環境変数の優先順位で設定をロード（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

---

## 必要条件

- Python 3.10 以上（型注釈に | を使用）
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール例（最低限）:
```bash
python -m pip install duckdb openai defusedxml
# またはプロジェクトに requirements.txt があれば
# python -m pip install -r requirements.txt
```

（プロジェクト配布時は setup/pyproject に依存関係を記載してください）

---

## セットアップ手順

1. リポジトリをクローン／展開
2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb openai defusedxml
   ```
4. 環境変数を設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化）。
   - 必須例（.env に記載する例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_station_password
     SLACK_BOT_TOKEN=your_slack_bot_token
     SLACK_CHANNEL_ID=your_slack_channel_id
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - .env の自動読み込みはプロジェクトルート（.git または pyproject.toml 視認）を基準に行われます。
5. データベースディレクトリの作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要モジュール・API）

以下はライブラリ関数を直接呼び出す簡単な例です。DuckDB 接続を渡して処理を行います。

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを計算して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込銘柄数:", n_written)
```

- 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB の接続オブジェクト
```

- ETL 結果クラスの参照（型）
```python
from kabusys.data import ETLResult  # pipeline.ETLResult を再エクスポート
```

注意点：
- OpenAI API を使う関数（score_news、score_regime 等）は api_key 引数を受け取ります。指定しない場合は環境変数 OPENAI_API_KEY を参照します。
- DuckDB のスキーマ（テーブル）や初期化は別途スキーマ初期化処理が必要です（ETL が必要なテーブルを期待します）。audit.init_audit_schema 等で監査テーブルは初期化できます。
- 自動 .env 読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（gpt-4o-mini を使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用 Slack 設定
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: sqlite（監視用 DB）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視関連設定
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

---

## セキュリティ・信頼性に関する設計メモ

- Look-ahead バイアス防止のため、スコア計算や ETL は「target_date」を明示的に受け取り、内部で現在日を直接参照しないようにしています。
- J-Quants クライアントはレート制御（120 req/min）とリトライ、401 リフレッシュを実装しています。
- ニュース収集は URL 正規化・トラッキング除去・SSRF 対策・受信サイズ制限を行います。
- OpenAI 呼び出しはリトライや非致命的フォールバック（失敗時は 0.0 を返す等）を採用しています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                         -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      -- ニュース NLP スコアリング（score_news）
    - regime_detector.py               -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                -- J-Quants API クライアント（fetch / save）
    - pipeline.py                      -- ETL パイプライン（run_daily_etl 等）
    - etl.py                           -- ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py                -- RSS ニュース収集
    - quality.py                       -- データ品質チェック
    - stats.py                         -- 統計ユーティリティ（zscore_normalize）
    - calendar_management.py           -- マーケットカレンダー管理
    - audit.py                         -- 監査ログスキーマ初期化（init_audit_db 等）
  - research/
    - __init__.py
    - factor_research.py               -- Momentum/Value/Volatility ファクター計算
    - feature_exploration.py           -- 将来リターン / IC / 統計サマリー 等
  - ai/、research/、data/ 配下にテスト対象のロジックがまとまっています

---

## 開発・テスト時の注意点

- 自動 .env 読み込みはパッケージ import 時に行われます。ユニットテスト等で環境読み込みを制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 API 呼び出し部分はモジュール内で個別にラップされているため unit test では該当関数をモックしてテストできます（実装箇所に注釈あり）。
- DuckDB の executemany はバージョン依存で空リストが渡せないケースがあるため、該当コードでは空チェックを行っています。テストで DuckDB を使う場合は実データで検証してください。

---

以上が README.md の骨子です。必要であれば以下の追加情報を作成します：
- requirements.txt の推奨内容
- .env.example の具体ファイル
- スキーマ初期化のサンプル SQL / スクリプト
- 実行可能な CLI エントリ（run_etl.py 等）の例

どれを追加しますか？