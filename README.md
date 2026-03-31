# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取り込み）、ニュースの NLP によるスコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）など、量的運用に必要な基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ実装（日時の暗黙参照を避ける）
- DuckDB をデータ格納に利用（SQL ベースの効率的処理）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを実装
- 冪等性（ON CONFLICT / idempotent 保存）を重視

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env ファイルと OS 環境変数からの設定読み込み（自動ロード機能、無効化可）
- データ ETL（jquants クライアント）
  - 株価（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存
  - レート制御・リトライ・トークン自動リフレッシュ対応
- ニュース収集・前処理
  - RSS 取得、URL 正規化、SSRF 対策、gzip 制限、XML パース保護
  - raw_news / news_symbols への保存（冪等）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（ai_scores への保存）
  - マクロニュースのセンチメントを用いた市場レジーム判定（bull/neutral/bear）
  - OpenAI 呼び出しに対するエクスポネンシャルバックオフ、レスポンスバリデーション
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター算出
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などのチェック（QualityIssue を返す）
- 監査ログ（audit）
  - signal → order_request → execution までのトレーサビリティテーブルを初期化
  - 監査用 DuckDB DB の作成ユーティリティ

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```bash
   git clone <your-repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要パッケージのインストール（例）
   requirements.txt がない場合は下記をインストールしてください。
   - duckdb
   - openai
   - defusedxml

   例:
   ```bash
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに合わせてバージョン固定を推奨）

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くことで自動読み込みされます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（実行する機能により必要なものが異なります）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector 等で使用）
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（発注系で必要）
   - SLACK_BOT_TOKEN       : Slack 通知（任意だが一部機能で必須）
   - SLACK_CHANNEL_ID      : Slack 送信先チャンネル ID
   推奨（デフォルト値あり）:
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL             : DEBUG/INFO/...
   - DUCKDB_PATH           : DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（例: data/monitoring.db）

   .env の例（一部）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要ユースケース例）

重要：各サンプルは実行環境に合わせてパスや日付、API キーを設定してください。

- DuckDB 接続の作成例
  ```python
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')
  ```

- 日次 ETL 実行（pipeline.run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # conn は duckdb 接続
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコアを生成して ai_scores に保存（news_nlp.score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", count)
  ```

- 市場レジーム判定（regime_detector.score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit_duckdb.db")
  # conn_audit を使って監査テーブルにアクセスできます
  ```

- ファクター計算（研究用途）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

ログレベルは環境変数 LOG_LEVEL で制御できます。エラーは例外として上げられる場合と、フェイルセーフでログとともにデフォルト値（例: スコア 0.0）を使う場合があります。

---

## 主要モジュールの説明（概要）

- kabusys.config
  - 環境変数および .env ファイルの自動読み込み、設定オブジェクト提供
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます

- kabusys.data
  - jquants_client.py: J-Quants API クライアント（取得/保存関数）
  - pipeline.py: 日次 ETL パイプライン（run_daily_etl, run_prices_etl 等）
  - news_collector.py: RSS 取得・前処理・raw_news 保存ロジック
  - quality.py: データ品質チェック群
  - calendar_management.py: JPX カレンダー管理と営業日ロジック
  - audit.py: 監査ログテーブルの DDL / 初期化ユーティリティ
  - stats.py: 汎用統計ユーティリティ（zscore_normalize）

- kabusys.ai
  - news_nlp.py: ニュースをまとめて OpenAI に投げ、銘柄ごとのスコアを作成し ai_scores に保存
  - regime_detector.py: ETF（1321）200日移動平均乖離とマクロニュースを合成して市場レジーム判定

- kabusys.research
  - factor_research.py, feature_exploration.py: ファクター計算、将来リターン、IC、統計サマリー

- パッケージトップ: src/kabusys/__init__.py で主要サブパッケージをエクスポート

注: README 作成時点で strategy / execution / monitoring パッケージの実体はリポジトリに揃っているか確認してください（__all__ に含まれていますが、実装が別途必要な場合があります）。

---

## ディレクトリ構成

（リポジトリルート配下の主要ファイルを抜粋）

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
      - news_collector.py
      - quality.py
      - calendar_management.py
      - audit.py
      - stats.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（その他）
    - (strategy/, execution/, monitoring/ は将来機能または別モジュール)
- pyproject.toml (プロジェクト設定: 存在する場合)
- .git/
- .env, .env.local (プロジェクトルートに置く)

---

## 開発メモ / 注意点

- OpenAI 経由の機能（news_nlp / regime_detector）は API リクエストの失敗時にフォールバック（0.0 スコア）する設計ですが、API キーは必須です。ローカルでのテスト時はモックすることを推奨します（コード内で _call_openai_api を patch 可能）。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、空チェックが入っています（既知の互換性考慮）。
- .env のパースはシェルスタイル（export KEY=val、クォート、コメント）に対応しています。
- news_collector は SSRF や XML 関連の攻撃に配慮した実装（defusedxml, ホストのプライベート判定、レスポンスサイズ制限）を含みます。
- 監査ログは削除を想定せず、created_at/updated_at を UTC で管理します。init_audit_db により独立の DuckDB を作成できます。

---

お問い合わせ・貢献
- イシューやプルリクエストは GitHub のリポジトリ上でお願いします。
- 大きな設計変更や API 変更を行う場合は事前に Issue で議論してください。

以上。README に追加したい具体的な実行例や CI、requirements.txt の内容があれば教えてください。