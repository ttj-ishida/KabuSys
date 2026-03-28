# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys のリポジトリ用 README。

目的：J-Quants や RSS / OpenAI を組み合わせてデータ収集（ETL）・品質チェック・ニュースセンチメント分析・市場レジーム判定・リサーチ用ファクター計算・監査（監査ログ）を行うための共通ライブラリ群を提供します。

---

## 主な機能（概要）

- データ取得・ETL
  - J-Quants API から株価（日足）・財務・上場銘柄・市場カレンダーを差分取得して DuckDB に冪等保存
  - 差分更新 / バックフィル / ページネーション対応 / レート制限・リトライ実装
- データ品質チェック
  - 欠損（OHLC）, スパイク検出（前日比閾値）, 重複チェック, 日付整合性チェック等
- ニュース収集
  - RSS からニュースを収集して前処理し raw_news に保存（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメントを LLM（gpt-4o-mini）で評価して ai_scores に書き込み
  - タイムウィンドウやバッチ処理、リトライ、レスポンス検証を実装
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次で 'bull'/'neutral'/'bear' 判定
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクターサマリ
- 監査（監査ログ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（DuckDB）
- 設定管理
  - .env 自動読込（プロジェクトルート検出）と Settings オブジェクトを通じた環境変数取得

---

## 必要な環境変数

主に以下を設定してください（.env をプロジェクトルートに置くことで自動ロードされます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須（Settings._require を使っているもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注系が使う場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID

OpenAI（ニュース NLP / レジーム判定用）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime は引数で上書き可能）

その他（省略時にデフォルトあり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視/モニタリング用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env 読み込みを無効化

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意し virtualenv を作成
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール（プロジェクトに requirements.txt がある想定、なければ最低以下を入れる）
   ```
   pip install duckdb openai defusedxml
   ```

   - 実際のプロジェクトでは additional deps（urllib 等標準ライブラリ以外）もある可能性があります。パッケージ配布時の setup/pyproject を参照してください。

3. ソースを editable インストール（開発時）
   ```
   pip install -e .
   ```

4. .env を作成し必要な環境変数を設定

5. DuckDB の初期スキーマや監査DBを準備
   - 監査用 DB を初期化する例（monitoring 用）
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/monitoring.db")
     ```

---

## 使い方（代表的な例）

※ すべての API は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取る仕様が多く、バッチ処理やテストで容易に差し替え可能です。

1. DuckDB 接続を作成する
   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL を実行する（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn, target_date=date(2026,3,20))
   print(result.to_dict())
   ```

3. ニュースセンチメント（ai_scores）を作成する
   ```python
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   # OPENAI_API_KEY が環境変数にあれば api_key を省略可
   written = score_news(conn, target_date=date(2026,3,20))
   print(f"書き込んだ銘柄数: {written}")
   ```

4. 市場レジーム判定を実行する
   ```python
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   score_regime(conn, target_date=date(2026,3,20))
   ```

5. 監査テーブルを初期化する
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

6. J-Quants から全上場銘柄情報を取得する（内部でトークン管理）
   ```python
   from kabusys.data.jquants_client import fetch_listed_info
   infos = fetch_listed_info()
   ```

7. データ品質チェックを個別に実行する
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=date(2026,3,20))
   for i in issues:
       print(i)
   ```

注意点：
- LLM 呼び出し（score_news/score_regime）は OPENAI_API_KEY を必要とします。テスト時は各内部 _call_openai_api をモックする設計になっています。
- ETL / API 呼び出しはリトライ・レート制限実装があるため長時間実行されることがあります（ログで進捗確認してください）。
- Date 操作ではルックアヘッドバイアス回避のため date.today() を内部的に参照しない設計の関数が多く、target_date を明示して使用することを推奨します。

---

## ディレクトリ構成（主要ファイルと役割）

（リポジトリ内 src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
    - パッケージ定義、バージョン情報
  - config.py
    - 環境変数・設定読み込みロジック（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
      - score_news をエクスポート
    - news_nlp.py
      - ニュースの LLM センチメント評価、バッチ処理、ai_scores への書き込み
    - regime_detector.py
      - ETF(1321) MA 乖離 + マクロニュース LLM を合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、ページネーション、保存関数）
    - pipeline.py
      - ETL パイプラインの実装（run_daily_etl など）、ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - 市場カレンダー取得・営業日判定ユーティリティ
    - news_collector.py
      - RSS フィード取得 & 前処理 & raw_news へ保存（SSRF 対策等）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py
      - zscore_normalize 等の共通統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）のスキーマ初期化ユーティリティ
  - research/
    - __init__.py
      - 研究用関数の公開
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、rank、factor_summary 等

---

## 運用メモ / ベストプラクティス

- 環境分離: KABUSYS_ENV を使い development / paper_trading / live を分離してください。is_live/is_paper/is_dev プロパティが Settings にあります。
- シークレット管理: .env は Git 管理しないこと。.env.example をリポジトリに置き、実運用では Vault 等の利用を推奨します。
- LLM 呼び出しでのモック: テストでは kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch して外部依存を切り離せます。
- DB バックアップ: DuckDB ファイルを定期的にバックアップしてください。監査用 DB（init_audit_db）や monitoring DB（SQLite）も同様です。
- ETL の冪等性: jquants_client の save_* 関数は ON CONFLICT DO UPDATE により冪等動作を提供します。部分失敗時は ETLResult で検出できます。

---

## 参考・補足

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- news_collector は RSS のサイズ上限（10 MB）や gzip 解凍後サイズチェック、SSRF 対策など堅牢化を施しています。
- jquants_client は固定間隔レート制限（120 req/min）を厳守する RateLimiter、401 時のトークン自動リフレッシュ、リトライ・バックオフを備えています。

---

README に書かれている説明で不明な点や、特定機能の詳細（例: ETL のフローを cron 化する方法、OpenAI プロンプトの調整方法、DuckDB スキーマの完全な定義など）が必要であれば、目的に合わせてサンプルコード・運用手順を追加します。どの箇所を詳しく補足しますか？