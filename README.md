# KabuSys

日本株向けの自動売買・データ基盤ライブラリ KabuSys の README です。  
本リポジトリはデータ ETL、ニュース NLP（LLM を用いたセンチメント評価）、市場レジーム判定、リサーチ用ファクター計算、監査ログ等のユーティリティを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインとアルゴリズム取引のための基盤ライブラリです。主な目的は以下です。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS や記事の収集・前処理・ニュースセンチメントの LLM による評価（ニュース NLP）
- ETF 指標とマクロニュースを組み合わせた市場レジーム判定
- リサーチ用途のファクター計算・特徴量探索ユーティリティ
- 発注フローの監査ログ（監査テーブル初期化、監査用 DB 管理）
- データ品質チェック（欠損、重複、スパイク、日付不整合）

設計思想としては「バックテストでのルックアヘッドバイアス回避」「ETL の冪等性」「外部 API 呼び出しでの堅牢なリトライ・レート制御」「DB 操作のトランザクション安全性」を重視しています。

---

## 機能一覧

- data:
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得 + DuckDB 保存関数）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day など）
  - ニュース収集（RSS 取得、前処理、raw_news 保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ（監査テーブルの初期化・監査 DB 作成）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai:
  - ニュース NLP（gpt-4o-mini を用いた銘柄別センチメント → ai_scores への書込支援）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロセンチメントの合成）
- research:
  - ファクター生成（momentum / value / volatility 等）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリー等）
- config:
  - 環境変数の管理（.env 自動ロード、必須環境変数取得ユーティリティ）
- audit:
  - 監査テーブル定義・初期化（signal_events / order_requests / executions 等）

---

## 必要条件（依存）

- Python 3.10+
- 必要パッケージ（主なもの）
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
  - その他（標準ライブラリの urllib 等を使用）

（プロジェクトの setup.py / pyproject.toml に依存宣言がある場合はそちらを参照してください）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. パッケージのインストール
   - 開発環境やローカルでの編集を想定する場合:
     ```bash
     pip install -e .
     ```
   - 依存のみをインストールする場合:
     ```bash
     pip install duckdb openai defusedxml
     ```

3. 環境変数の準備
   - プロジェクトルートに `.env` および（必要に応じて）`.env.local` を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector 呼び出し時に使われます）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（実際に発注する場合）
     - SLACK_BOT_TOKEN       : Slack 通知用 BOT トークン（必要に応じて）
     - SLACK_CHANNEL_ID      : Slack チャネル ID
   - 任意 / デフォルト
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例: .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主な例）

ここでは Python API を直接呼ぶ基本的な例を示します。実行はプロジェクトルートで行ってください。

- DuckDB 接続を作成して ETL を実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（指定日分のスコア算出）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で用意
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査 DB 初期化（独立した監査用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # init_audit_db は監査テーブル群を作成して接続を返す
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(records[:5])
  ```

注意:
- OpenAI を呼ぶ関数は api_key 引数に明示的にキーを渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API は JQUANTS_REFRESH_TOKEN（環境変数）または引数経由でトークンを渡す必要があります。
- ETL / API 呼び出しはネットワーク／API レート制限や認証に依存します。実運用時は適切に設定してください。

---

## ディレクトリ構成

パッケージは `src/kabusys` 以下に配置されています。主要ファイルと役割は以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py                - パッケージ初期化（__version__ 等）
  - config.py                  - 環境変数 / 設定読み込みロジック（.env 自動読み込み、必須チェック等）
  - ai/
    - __init__.py
    - news_nlp.py              - ニュースセンチメント（LLM）処理、ai_scores 書き込みサポート
    - regime_detector.py       - ETF MA200 とマクロセンチメントを合成した市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py              - ETL パイプラインと run_daily_etl 等
    - jquants_client.py        - J-Quants API クライアント（取得 & DuckDB 保存）
    - news_collector.py        - RSS 取得・前処理・保存ロジック
    - calendar_management.py   - 市場カレンダー管理（営業日判定等）
    - quality.py               - データ品質チェック
    - stats.py                 - 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                 - 監査テーブル定義・初期化
    - etl.py                   - ETLResult の再公開インターフェース
  - research/
    - __init__.py
    - factor_research.py       - モメンタム/ボラティリティ/バリュー等のファクター計算
    - feature_exploration.py   - 将来リターン計算、IC、統計サマリー等

この README のサンプルは上のモジュール API に基づいています。詳細な関数ドキュメントは各モジュールの docstring を参照してください。

---

## 補足・運用上の注意

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）で行われます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テスト時に有用）。
- OpenAI の呼び出しは失敗時にフェイルセーフ（0.0 など）で継続する実装です。プロダクション運用ではログ監視やリトライ設定の確認をおすすめします。
- J-Quants クライアントはレート制限・リトライ・トークン自動リフレッシュを実装していますが、API 利用規約・レート制限の順守は利用者の責任です。
- DuckDB のバージョン互換性（executemany の仕様など）に注意してください。README に記載の動作は DuckDB 0.10 系程度を想定しています。

---

ご不明な点や README に追加したい内容（例: CLI、Docker、CI の使い方など）があれば教えてください。README を拡張して具体的な運用手順や例を追加できます。