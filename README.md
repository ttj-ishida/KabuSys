# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP によるセンチメント評価、ファクター計算、監査ログ、マーケットカレンダー管理、レジーム判定など、アルゴリズム取引やリサーチに必要な機能群を提供します。

バージョン: 0.1.0

---

## 主要な機能（概要）

- データ ETL / 管理
  - J-Quants API 経由での株価日足（OHLCV）・財務データ・上場銘柄情報・マーケットカレンダー取得
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）

- ニュース処理
  - RSS 取得と前処理（URL 正規化、トラッキングパラメータ除去、SSRF 防御）
  - raw_news / news_symbols への保存（冪等性考慮）
  - OpenAI を使ったニュースセンチメント解析（gpt-4o-mini、JSON Mode）

- AI / レジーム判定
  - ニュースセンチメントと ETF（1321）200日移動平均乖離を合成して市場レジーム（bull / neutral / bear）を日次判定
  - ニュースごとの銘柄センチメントを取得して ai_scores に書き込み

- リサーチ / ファクター分析
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（スピアマン）計算、ファクターの統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions など、シグナルから約定にいたる監査テーブルの DDL と初期化
  - order_request_id による冪等化、UTC タイムスタンプ運用

- 運用補助
  - 環境設定管理（.env 自動読み込み）
  - Slack 通知用設定（トークン / チャンネル ID）
  - 実行監視用しきい値（CPU / メモリ / ディスク）

---

## 必要条件 / 依存パッケージ

- Python 3.10 以上（型アノテーションの表記から想定）
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging など）
- （オプション）SQLite（標準ライブラリ sqlite3）や Slack クライアント等は運用ツールに合わせて追加

依存関係はプロジェクトの setup / pyproject.toml に合わせてインストールしてください。開発時は仮想環境を推奨します。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# その他プロジェクトの requirements をインストール
```

---

## 環境変数（設定）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注系）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（通知）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）

任意 / デフォルト値あり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

必須設定が不足すると Settings オブジェクトから参照した際に ValueError が送出されます。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   # もしくは必要なパッケージを個別インストール
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxx
     OPENAI_API_KEY=sk-xxx
     SLACK_BOT_TOKEN=xoxb-xxx
     SLACK_CHANNEL_ID=C0123456
     KABUSYS_ENV=development
     ```

5. DuckDB の初期スキーマや監査 DB を準備（任意）
   - 監査ログ専用 DB を作成する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - または既存の DuckDB 接続にスキーマ追加:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn)
     ```

---

## 使い方（代表的な例）

以下では簡単な Python スニペットで主要機能の呼び出し例を示します。詳細な引数や返り値は各モジュールの docstring を参照してください。

- ETL（日次パイプライン）を実行する:
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # target_date を指定することも可
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリング（OpenAI が必要）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))  # api_keyは環境変数 OPENAI_API_KEY が使われる
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- RSS フィードを取得してアプリケーションで保存:
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  # articles は NewsArticle 型の dict リスト。アプリ側で raw_news テーブルへ保存する処理を行う。
  ```

- 監査ログテーブル初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions 等のテーブルが作成されます
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

---

## 設計上の重要なポイント（抜粋）

- Look-ahead bias の排除
  - 各処理は内部で `datetime.today()` や `date.today()` を盲目的に参照せず、`target_date` を明示して処理する設計になっています（バックテストでのデータ漏洩を防止）。

- 冪等性
  - DuckDB への保存処理は可能な限り ON CONFLICT / DO UPDATE を用い冪等に動作します。

- フェイルセーフ / ロバストネス
  - 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・バックオフ・タイムアウトを備え、致命的な例外は可能な限り局所化して他の処理を継続します。

- セキュリティ対策
  - RSS 収集では SSRF 対策（プライベート IP の検出、リダイレクト時の検証）、defusedxml による XML パース保護などを実装しています。

- 運用配慮
  - J-Quants はレート制限が厳しいため固定間隔スロットリングを導入しています。
  - OpenAI 呼び出しは JSON Mode を使い厳密な構造で結果を期待しています（バリデーションあり）。

---

## ディレクトリ構成

（src 配下を基準）

- src/kabusys/
  - __init__.py                    — パッケージ初期化（version 等）
  - config.py                      — 環境変数 / Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py                  — ai サブパッケージ公開 API（score_news 等）
    - news_nlp.py                  — ニュース NLP / OpenAI 呼び出し、score_news 実装
    - regime_detector.py           — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得＋DuckDB への保存）
    - pipeline.py                  — ETL パイプライン / run_daily_etl 等
    - etl.py                       — ETL の公開インターフェース / 型再エクスポート
    - news_collector.py            — RSS 取得・前処理・保存ユーティリティ
    - calendar_management.py       — マーケットカレンダー管理 / 営業日ロジック
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py       — 将来リターン・IC・統計サマリー等
  - research/（その他ファイル）
  - （その他戦略・実行・監視関連モジュールは将来的に追加）

---

## 参考・補足

- OpenAI を使う機能（news_nlp / regime_detector）は API キーを必要とします。API 呼び出しに失敗した場合はフォールバック（多くは中立スコア 0.0）して処理を継続する設計です。
- J-Quants へのアクセスは API レート制限・認証トークンのリフレッシュを考慮しています。JQUANTS_REFRESH_TOKEN を .env に設定してください。
- この README はコードベースの docstring を元にした要約です。詳細な挙動やパラメータは各モジュールの docstring を確認してください。

---

もし README に含めたい追加の情報（例: コマンドラインツール、CI 設定、テスト実行方法、デプロイ手順など）があれば教えてください。必要に応じて追記します。