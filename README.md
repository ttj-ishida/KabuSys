# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
データ収集（J-Quants, RSS）、ETL、データ品質チェック、AI（ニュースセンチメント / 市場レジーム判定）、リサーチ用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

本リポジトリはライブラリ（Python package）として設計されており、DuckDB を中心としたオンプレ／ローカルなデータ基盤と連携して動作します。

---

## 主な機能

- ETL（J-Quants）  
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得・保存（ページネーション・冪等保存・レート制御・リトライ）
- ニュース収集（RSS）  
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、raw_news/ news_symbols への保存
- ニュース NLP（OpenAI）  
  - ニュースを銘柄ごとにバッチで LLM（gpt-4o-mini）に送り、センチメント ai_score を ai_scores テーブルへ保存（JSON Mode／リトライ・バリデーション）
- 市場レジーム判定（Regime Detector）  
  - ETF(1321) の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成し日次で 'bull'/'neutral'/'bear' を判定
- データ品質チェック（quality）  
  - 欠損、スパイク（前日比）、重複、日付不整合の検出と QualityIssue レポート化
- リサーチ（research）  
  - モメンタム、ボラティリティ、バリュー等のファクター計算、将来リターン計算、IC（Spearman）や統計サマリー、Z スコア正規化
- 監査ログ（audit）  
  - signal_events / order_requests / executions 等の監査テーブルを初期化・管理（UUID ベースのトレーサビリティ）
- 環境設定管理（config）  
  - .env / .env.local の自動読み込み、主要な設定を `settings` 経由で提供
- 安全設計・運用配慮  
  - Look-ahead バイアス防止（日付参照やクエリ制約の明確化）、API リトライ・バックオフ、LLM リトライ、フェイルセーフ（API 失敗時はゼロフォールバック等）

---

## 要件

- Python 3.10+
- 主な依存パッケージ（一部）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリのみで動くユニットも多数ありますが、ETL / AI 機能を利用する場合は上記が必要です。

（プロジェクトに pyproject.toml / requirements.txt があればそちらからインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. パッケージと依存関係をインストール
   - 開発中であれば editable install:
     ```
     pip install -e .
     ```
   - 最小依存を個別に入れる場合:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数（.env）を用意  
   プロジェクトルートに `.env` や `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます）。  
   必要な主な環境変数（説明付き）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite パス（監視用途、省略時: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO）

   .env のフォーマットは shell 互換（`KEY=VAL`、引用符あり可）です。config モジュールはプロジェクトルートの `.env` / `.env.local` を自動読み込みします。

---

## 使い方（代表的な API と実行例）

以下は最小限の利用例です。詳細は各モジュールの関数ドキュメントを参照してください。

- DuckDB 接続を準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（全体パイプライン）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定しないと今日を使います
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（AI）スコアを生成して ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI キーは環境変数 OPENAI_API_KEY でも渡せます
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（Regime Scoring）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB を別に作る場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_schema は内部で実行済み
  ```

- カレンダー / 営業日ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 設定値取得
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点（運用上の配慮）:
- OpenAI 呼び出しは JSON Mode を使い、レスポンスの厳密なバリデーションを行います。API 失敗時にはフェイルセーフとして 0.0 を返す箇所があります（ログ記録あり）。
- J-Quants API 呼び出しはレート制御、リトライ、401 トークンリフレッシュに対応しています。
- 日付処理は Look-ahead バイアスを避けるため、内部で date.today() や datetime.today() を不用意に参照しない設計がなされています。ETL / スコアリングは明示的な target_date を渡すことを推奨します。

---

## ディレクトリ構成（主要ファイル／モジュール）

（パッケージルート: src/kabusys）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（LLM）処理
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL インターフェース公開
    - news_collector.py      — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py — 市場カレンダー / 営業日ユーティリティ
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ（監査テーブル作成・init）
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - ai, data, research の他に strategy / execution / monitoring といったサブパッケージを予定（__all__ に含む）

---

## 運用メモ / トラブルシュート

- .env の自動読み込みをテスト等で無効化するには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- DuckDB による executemany で空リストを渡すとエラーになるバージョンがあるため、実装側で空チェックが行われています。自作コードで executemany を呼ぶ場合は注意してください。
- OpenAI / J-Quants の API 呼び出しはリトライとバックオフ、429 / 5xx のハンドリングが実装されていますが、運用環境では API キーの利用上限・コスト管理に注意してください。
- ニュース収集では RSS のサイズ上限や gzip 解凍後サイズチェック、SSRF 回避のためのホスト/IP 検証を行っています。外部ソースを追加する場合は事前に URL の安全性を確認してください。

---

## 参考・拡張

- research モジュールは外部解析・モデル検証のためのツール群です。バックテストや戦略実行ロジックは別モジュール（strategy / execution / monitoring）で実装することを想定しています。
- 将来的な拡張例:
  - 発注 API（kabuステーション）連携の execution 層の実装
  - リアルタイム監視・アラート機能（Slack 通知等）
  - モデル学習パイプライン（特徴量ストア / モデル管理）

---

この README はコード内の docstring に基づき作成しています。各関数・モジュールの詳細な仕様は該当ソースファイルの docstring を参照してください。必要であれば利用例・運用手順を追加で作成します—どの部分を詳しく追加したいか教えてください。