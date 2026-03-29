# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
価格・財務・ニュースを収集・品質チェック・特徴量算出・AIによるニュース評価・市場レジーム判定・監査ログなどを含む、バックテスト／運用向けのデータ／研究／監視ユーティリティ群です。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない）
- DuckDB を主なローカルデータストアとして利用
- J-Quants / OpenAI / RSS 等外部 API との堅牢なやり取り（レート制御、リトライ、フェイルセーフ）
- ETL/品質チェック/監査ログを冪等（idempotent）に実装

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート基準）
  - 必須設定の検証、環境（development/paper_trading/live）判定、ログレベル等

- データ収集 / ETL（kabusys.data）
  - J-Quants API クライアント（株価/財務/カレンダー取得）
  - 差分ETL / 日次ETL パイプライン（run_daily_etl）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS 取得・前処理・SSRF対策・正規化）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal/order/execution）テーブル定義・初期化ユーティリティ

- 研究（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - z-score 正規化ユーティリティ

- AI（kabusys.ai）
  - ニュースのセンチメントスコアリング（OpenAI を用いた gpt-4o-mini）
    - 複数銘柄をバッチ送信して ai_scores テーブルへ書込
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM センチメントを合成）

- ユーティリティ
  - DuckDB 用の監査DB初期化（init_audit_db / init_audit_schema）
  - 各種堅牢な HTTP / API 呼び出しの実装（レートリミッタ／リトライ等）

---

## 動作環境 / 依存パッケージ（代表例）

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリを多用（urllib, json, logging, datetime 等）

インストールはプロジェクトルートで仮想環境を作成し、必要パッケージをインストールしてください（pyproject / requirements がある場合はそちらを利用）。

例:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージのインストール（例）:
  - pip install duckdb openai defusedxml

プロジェクトをローカル開発モードで使う場合（pyproject.toml / setup がある想定）:
- pip install -e .

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動

2. 仮想環境を作成し依存をインストール（上記参照）

3. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を用意してください。自動読み込みは .git または pyproject.toml からプロジェクトルートを検出して行います。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット。

4. 必要な環境変数（主要なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注関連で使用）
   - KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   例 `.env`（簡易）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な例）

以下は Python インタプリタやスクリプト内での利用例です。

- DuckDB 接続を取得して日次 ETL を実行する
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントを評価して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数に設定されているか、api_key 引数を渡す
  written = score_news(conn, target_date=date(2026,3,20))
  print("wrote", written, "scores")
  ```

- 市場レジームを判定する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ用の DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit_duckdb.duckdb")
  # 返却された conn は監査テーブル初期化済み
  ```

- ニュース RSS を取得（単体利用）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

- 研究用ファクター呼び出し例
  ```python
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026,3,20))
  # res は各銘柄の辞書リスト
  ```

注意点:
- AI (OpenAI) を呼ぶ関数は api_key 引数でキーを直接渡すか、環境変数 OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・フェイルセーフを持ちますが、キーが無いと ValueError が発生します。
- J-Quants の API 呼び出しは JQUANTS_REFRESH_TOKEN（Settings.jquants_refresh_token）を必要とします。

---

## 設計上の注意 / 実運用ポイント

- 全モジュールは基本的にルックアヘッドバイアスに配慮（target_date 未満のデータのみ参照など）しています。バックテスト目的のときは ETL の取り扱う時点・日付に注意してください。
- ETL は部分的に失敗しても他のステップを継続する設計です（エラーは ETLResult.errors に収集されます）。
- NewsCollector は SSRF 保護・受信サイズ制限・XML パースの安全化（defusedxml）を行っていますが、外部ソースの扱いには常に注意してください。
- DuckDB の executemany に関する挙動（空リスト不可など）に配慮した実装になっています。

---

## ディレクトリ構成

（ソースは src/kabusys 配下に配置）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースNLPスコアリング（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py        — 市場カレンダー管理（営業日判定 等）
    - etl.py                        — ETL 公開インターフェース（ETLResult）
    - pipeline.py                   — ETL パイプライン実装（run_daily_etl 等）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマ初期化
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - news_collector.py             — RSS 収集・正規化・保存ロジック
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Volatility/Value 等
    - feature_exploration.py        — forward returns / IC / summary / rank

---

## 開発・貢献

- コードは docstring / logger を重視して書かれており、ユニットテストとモックを利用した検証が想定されています。
- 外部 API 呼び出し部分（OpenAI / J-Quants / HTTP）はモック差替えでテスト可能な設計です（内部の _call_openai_api や _urlopen 等を patch 可能）。
- PR の際は既存の設計方針（ルックアヘッド回避、冪等性、フェイルセーフ）に沿うことを推奨します。

---

README は以上です。必要であれば、具体的な .env.example、pip install のための pyproject.toml / requirements.txt のテンプレート、または各機能のより詳しい使用例（ETL の cron 化 / ロギング設定 / Slack 通知サンプル）を追加で作成します。どの部分を詳しくしますか？