# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤用ライブラリ。  
DuckDB をデータストアに用い、J-Quants / RSS / OpenAI などの外部サービスを組み合わせてデータ収集（ETL）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ管理を行うためのモジュール群を提供します。

主にライブラリとして利用し、バッチジョブや研究・バックテスト基盤に組み込んで使います。

対応想定 Python バージョン: 3.10+

---

## 主要機能

- データ取得／ETL
  - J-Quants API から株価（日足）、財務データ、マーケットカレンダーを差分取得して DuckDB に保存（冪等処理、ページネーション対応、レートリミット／リトライ実装）
  - ETL のエントリーポイント run_daily_etl による一括実行。品質チェック機能統合
- ニュース収集・処理
  - RSS フィードからニュースを収集して raw_news に保存（SSRF対策、サイズ制限、URL 正規化、トラッキングパラメータ除去）
  - ニュース前処理ユーティリティ（URL 除去・空白正規化等）
- ニュース NLP（OpenAI）
  - 銘柄毎に複数記事を統合して LLM にバッチ入力し ai_scores にスコアを保存（gpt-4o-mini + JSON mode を想定）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離 + LLM センチメントを合成）
  - フェイルセーフなリトライ・バリデーション実装
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリー
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェックを集約してレポート
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の DDL を冪等的に作成する初期化機能（init_audit_schema / init_audit_db）
  - 発注トレースのための UUID 階層とインデックス設計
- 設定管理
  - 環境変数／.env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）
  - Settings クラス経由で設定値にアクセス可能（settings をインポートして使用）

---

## 必要依存パッケージ（主要）

- duckdb
- openai
- defusedxml

（その他標準ライブラリで実装されている部分が多いです。実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。）

---

## セットアップ手順（開発環境向け・クイックスタート）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成と有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - プロジェクトに requirements / pyproject があればそれに従ってください。最低限:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発時は editable install:
     ```
     pip install -e .
     ```

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   例: `.env` の最小例
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - .env.local は .env を上書きする（優先される）。OS 環境変数は常に優先されます。

---

## 簡単な使い方（コード例）

※ すべて DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）と datetime.date を引数に取ります。

- ETL を日次で実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュース NLP スコアリング（ai_scores へ書き込む）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算（例：モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(momentum), "銘柄分の結果")
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn に対し order_requests 等の insert/検索が可能
  ```

注意点:
- AI 関連（score_news, score_regime）は OpenAI API キー（OPENAI_API_KEY）が環境変数または api_key 引数で必要です。
- ほとんどの関数は外部 API を呼ぶか DuckDB のテーブル構造に依存するため、事前に適切なスキーマ／テーブルが存在することを確認してください（ETL によるテーブル作成は別途スキーマ初期化が必要な場合があります）。

---

## 設定（環境変数一覧）

主な環境変数（Settings で参照されるもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで利用）
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン（通知用途）
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用途の DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
- LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL

自動 .env 読み込み:
- プロジェクトルートはこのパッケージのファイル位置から上方へ .git または pyproject.toml を探索して特定します。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

（リポジトリ直下の src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py        — ニュース NLP（LLM）スコアリング
    - regime_detector.py — マーケットレジーム判定（MA200 + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント / DB 保存処理
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETL 公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py  — RSS ニュース収集
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - quality.py         — データ品質チェック
    - stats.py           — 統計ユーティリティ（zscore_normalize 等）
    - audit.py           — 監査ログスキーマ初期化（signal / order / execution）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー

---

## 実運用上の注意

- Look-ahead バイアス対策:
  - モジュール設計上、多くの処理で date の扱いに細心の注意を払い、内部で datetime.today() を直接参照しない・DB クエリに排他条件を入れる等の実装ポリシーがあります。バッチやバックテストで使用する際は target_date を明示してください。
- セキュリティ:
  - news_collector は SSRF 対策・XML 脆弱性対策（defusedxml）・レスポンスサイズ制限を実装していますが、本番外部入力にはさらに注意してください。
- エラーとフォールバック:
  - AI/API 呼び出しはリトライ／フェイルセーフを実装しており、失敗時はスコアを 0 にフォールバックする等の挙動になります。挙動を変更する場合は関数の設計方針に沿って実装を更新してください。
- DuckDB スキーマ:
  - ETL・監査ログ等は所定のテーブル構造を前提とします。初期スキーマの生成やマイグレーションはプロジェクト固有の手順に従ってください（audit.init_audit_schema 等を利用できます）。

---

問題やドキュメントの補足が必要でしたら、どの部分を詳しく知りたいか教えてください。README の例 .env.example や運用チェックリストなど、追加で作成できます。