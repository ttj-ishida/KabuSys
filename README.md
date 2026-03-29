# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
DuckDB をデータストアに用い、J-Quants からのデータ取得、ニュース収集、LLM を使ったニュースセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）などを提供します。

主な目的は「データ取得（ETL）」「データ品質チェック」「AI によるニューススコアリング」「市場レジーム判定」「研究用ファクター計算」「監査ログ（発注／約定の追跡）」です。

---

## 主な機能（抜粋）

- データ取得（J-Quants API 経由）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXマーケットカレンダー
  - レート制御・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - run_daily_etl による一括処理
- ニュース収集（RSS）と前処理
  - URL 正規化、SSRF 対策、gzip 上限チェック、XML の安全パース
- ニュース NLP（OpenAI）
  - 複数銘柄バッチでのセンチメント評価（gpt-4o-mini）
  - score_news による ai_scores 書き込み
- 市場レジーム判定（AI + 指標）
  - ETF(1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成
  - score_regime による market_regime 書き込み
- 研究用モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化
- 監査ログ（Audit）
  - signal_events, order_requests, executions テーブルの初期化・管理（冪等）
  - init_audit_schema / init_audit_db を提供

---

## 必要条件

- Python 3.10+
  - 型ヒントに `X | None` などの構文を使用しているため 3.10 以上を想定しています
- 主な依存パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / 各 RSS / OpenAI）

詳細な requirements はプロジェクトの requirements.txt（ある場合）を参照してください。

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. インストール
   - パッケージ化されている場合:
     ```
     pip install -e .
     ```
   - あるいは最低限の依存を直接:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数 / .env を準備
   - 自動で .env/.env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（コード内で _require によって必須扱い）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると自動ロードを無効化)
     - KABUSYS における DB パス:
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（監視用 DB のパス、デフォルト: data/monitoring.db）

   - シンプルな .env 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=yyyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（代表的な例）

以下はライブラリの主要機能を呼び出す基本的な例です。実行はプロジェクトルートで行ってください（.env 自動ロードの前提）。

- DuckDB 接続の作成
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー→株価→財務→品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア算出（OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で指定）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))  # 戻り値: 書き込んだ銘柄数
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作成）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  momentum_records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- Zスコア正規化ユーティリティ
  ```python
  from kabusys.data.stats import zscore_normalize

  normalized = zscore_normalize(momentum_records, columns=["mom_1m", "mom_3m", "ma200_dev"])
  ```

注意:
- AI 呼び出し (OpenAI) には API キー（OPENAI_API_KEY）を設定してください。関数は api_key を直接引数で渡すこともできます。
- 主要 API 呼び出しは失敗時にフェイルセーフ（例: スコアが取れない場合は 0.0 でフォールバック）を採っていますが、ログを必ず確認してください。

---

## CLI / スケジューリング（運用ヒント）

本リポジトリはジョブを直接提供する CLI が明記されていませんが、上記の関数群は cron / Airflow / systemd タイマーなどから呼べます。運用例:

- 夜間 ETL（毎朝）:
  - Python スクリプト内で run_daily_etl を呼ぶ（target_date を明示するか date.today() を使う）
- 毎朝のニューススコアリング:
  - score_news を定期実行し ai_scores を更新
- 毎営業日の市場レジーム判定:
  - score_regime を実行して market_regime を更新

ログとモニタリング（Slack 連携など）を組み合わせると運用が安定します（SLACK_* 環境変数は設定必須）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 配下に実装されています。主な構成は以下の通り（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                   # 環境変数・設定読み込みロジック（.env 自動ロードなど）
  - ai/
    - __init__.py
    - news_nlp.py               # ニュースセンチメント（score_news）
    - regime_detector.py        # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（fetch / save 関数）
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    # 市場カレンダー管理（営業日判定等）
    - news_collector.py         # RSS ニュース収集
    - quality.py                # データ品質チェック
    - stats.py                  # 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                  # 監査ログスキーマ初期化
    - etl.py                    # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py        # モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py    # 将来リターン, IC, summary, rank
  - monitoring/ (存在する場合: 監視用コード)
  - execution/  (存在する場合: 発注関連コード)
  - strategy/   (存在する場合: 戦略定義)

（実際のツリーはプロジェクト全体を参照してください）

---

## 注意事項 / 設計上のポイント

- Look-ahead バイアス回避:
  - 多くのモジュールは target_date を明示的に受け取り、datetime.today() を無闘に参照しない設計です。
  - ETL／スコアリング／レジーム判定におけるデータ取得は「target_date より前のデータのみ」を使うよう配慮されています。
- 冪等性:
  - DuckDB への保存処理は ON CONFLICT DO UPDATE や適切なキー管理で冪等に設計されています。
- フェイルセーフ:
  - AI 呼び出しや外部 API はリトライ・タイムアウト・フォールバック（多くはスコア 0.0）で安全策を取っています。ただしログは必ず確認してください。
- セキュリティ:
  - news_collector は SSRF 防止、受信サイズ上限、defusedxml を利用した XML パースなど安全性に配慮しています。

---

## サポート / 貢献

- バグ報告や機能要望は Issue を立ててください。
- 新機能追加や修正は PR を歓迎します。テストと簡潔な説明を添えてください。

---

以上。必要であれば README に実行可能なスクリプト例（systemd / cron 用のサンプル）、より詳細な .env.example、あるいは依存関係ファイル（requirements.txt）や CI 設定のテンプレートを追記します。どの情報を追加しますか？