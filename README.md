# KabuSys

日本株向けのデータプラットフォーム／自動売買支援ライブラリです。  
DuckDBベースのデータレイクに対する ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー／約定）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB をデータ層に採用し SQL と Python の組合せで処理
- ETL / 保存処理は冪等（ON CONFLICT / DELETE→INSERT 等）を意識
- 外部 API 呼び出し（J-Quants / OpenAI 等）はリトライ・レート制御・フェイルセーフ処理あり

---

## 機能一覧

- データ取得・ETL
  - J-Quants API クライアント（株価日足 / 財務 / 上場銘柄 / カレンダー）
  - 差分ETL（run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl）
- データ品質チェック（quality）
  - 欠損、重複、スパイク、日付不整合の検出・レポート
- ニュース収集（news_collector）
  - RSS 取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF対策、受信サイズ制限、トラッキングパラメータ除去
- ニュース NLP（news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメントスコア生成（ai_scores テーブル）
  - バッチ処理、JSON Mode 利用、リトライ・バリデーション
- 市場レジーム判定（regime_detector）
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定
- 研究（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- カレンダー管理（calendar_management）
  - JPX カレンダーを使った営業日判定・前後営業日検索・更新ジョブ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義、初期化ユーティリティ
- 設定管理（config）
  - .env 自動読み込み（プロジェクトルート検出）と Settings API

---

## 動作要件

- Python 3.10+
- 必要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json, logging 等）

（実際のインストール要件はプロジェクトの requirements ファイル等に合わせてください）

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. 仮想環境作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   - 開発環境に合わせて requirements.txt があればそれを使用
   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクトに requirements があれば:
   # pip install -r requirements.txt
   ```
4. パッケージをインストール（ローカル開発）
   ```bash
   pip install -e .
   ```
5. 環境変数を設定（.env ファイルをプロジェクトルートに置くか、OS環境変数を利用）
   - 主要な環境変数（最低限必要なものを示す）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 用）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（注文実行連携がある場合）
     - KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack Bot トークン（通知用）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
   - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

---

## 使い方（クイックスタート）

以下は Python REPL やスクリプト内での利用例です。DuckDB の接続には duckdb.connect を使います。

- 日次 ETL の実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI が必要）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か引数で指定
  print(f"scored {count} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化（専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます
  ```

- 研究用ファクター計算例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- データ品質チェックをまとめて実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

---

## 注意点 / 設計に関するメモ

- 多くの処理は「ルックアヘッドバイアス防止」を明示しているため、内部で現在時刻を直接参照しない設計になっています。バックテストでの利用時は ETL で取得した時刻情報（fetched_at 等）と運用方針に注意してください。
- 外部 API 呼び出し（J-Quants / OpenAI）にはレート制御・リトライ・フェイルセーフが実装されていますが、実環境ではキーや制限に応じて追加の運用制御が必要です。
- news_collector では SSRF / XML Bomb / 過大レスポンス対策が組み込まれています。RSS ソース設定は DEFAULT_RSS_SOURCES を参照してください。
- DuckDB の互換性や executemany の挙動（空リスト不可など）に対処済みのコードになっていますが、DuckDB のバージョン依存の動作は運用時に確認してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールとファイルです（抜粋）:

- kabusys/
  - __init__.py
  - config.py                        # 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py                     # ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py              # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               # J-Quants API クライアント & DuckDB 保存
    - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
    - etl.py                          # ETL インターフェース再エクスポート
    - news_collector.py               # RSS ニュース収集
    - calendar_management.py          # カレンダー管理（営業日判定・更新ジョブ）
    - quality.py                      # データ品質チェック
    - stats.py                        # 統計ユーティリティ（zscore_normalize）
    - audit.py                         # 監査ログスキーマ・初期化
  - research/
    - __init__.py
    - factor_research.py               # Momentum / Value / Volatility 等
    - feature_exploration.py           # forward returns / IC / summary / rank

（テスト、スクリプト、ドキュメント等はプロジェクトルートに別途配置されている想定です）

---

## 開発とテスト

- 自動環境変数読み込みは config.py でプロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を読み込みます。テスト時に自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し等は内部で再試行ロジックがあるため、単体テストではモック（unittest.mock.patch）して外部通信を切り離して検証してください。news_nlp/regime_detector 内部で _call_openai_api を差し替えられる設計になっています。

---

不明点や README に追記して欲しい内容（例: 実運用時の監視、Slack通知の使い方、kabu API を利用した実際の発注フローのサンプル等）があれば教えてください。必要に応じて実行例（シェルスクリプトや docker-compose など）も追加します。