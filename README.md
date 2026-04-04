# KabuSys

KabuSys は日本株のデータ取得・ETL・特徴量計算・ニュース NLP・市場レジーム判定・監査ログ管理を行う自動売買／リサーチ基盤のライブラリです。  
本リポジトリは ETL パイプライン、データ品質チェック、AI を用いたニュースセンチメント評価、ファクター計算、監査テーブル初期化などを提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー等の差分取得および保存（冪等）
  - レートリミッティングとリトライ（トークンリフレッシュ対応）
- ETL パイプライン
  - 日次 ETL（calendar / prices / financials）と品質チェックの連携
  - ETL 実行結果を表す ETLResult クラス
- データ品質チェック
  - 欠損（OHLC）、スパイク（急変）、重複、日付整合性チェック
- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、カレンダー差分更新ジョブ
- ニュース収集
  - RSS 取得、前処理、SSRF 対策、raw_news への冪等保存（ID は正規化 URL の SHA-256）
- AI（OpenAI）を使った処理
  - ニュースごとの銘柄センチメント評価（ai.news_nlp.score_news）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの統合 → ai.regime_detector.score_regime）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions の DDL と初期化機能（監査・トレーサビリティ）
  - 監査専用 DB 初期化ユーティリティ

---

## セットアップ手順

前提: Python 3.10+（typing の一部機能を利用）、ネットワークアクセス（J-Quants / OpenAI）可能な環境

1. リポジトリをクローンして開発インストール（例）:
   ```
   git clone <repo-url>
   cd <repo>
   python -m pip install -e .
   ```

2. 必要な外部パッケージ（主に実行時依存）:
   - duckdb
   - openai
   - defusedxml
   - （用途に応じて）urllib 標準ライブラリ等は標準で同梱

   例（pip）:
   ```
   python -m pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（発注機能を使う場合）
   - OpenAI（AI 機能）:
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - その他の変数例（デフォルトあり）:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   - 例 `.env`（最低限）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABU_API_PASSWORD=your_password
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. （任意）監査 DB 初期化:
   - audit 用 DB を作る場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要な API と実行例）

以下は主要なユースケースの簡易例です。詳細は各モジュールのドキュメント（ソース内 docstring）を参照してください。

- DuckDB 接続の作成（デフォルトパスは settings.duckdb_path）:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today(), id_token=None)
  print(result.to_dict())
  ```

- ニュースセンチメントをスコア化して ai_scores に書き込む:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数で設定していることを想定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"スコア書込み件数: {written}")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用）:
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存接続にテーブルを追加）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for issue in issues:
      print(issue)
  ```

注意:
- AI 機能（score_news, score_regime）は OpenAI API に依存します。API キーが必要です。
- ETL / データ取得は J-Quants API に依存します。J-Quants の認証トークン（リフレッシュトークン）を設定してください。
- 各関数はルックアヘッドバイアスを避ける設計（関数引数に target_date を与え、内部で date.today() を直接参照しない）になっています。バッチ処理やバックテストで使いやすくなっています。

---

## 設計上の注意点 / ポイント

- 環境変数の自動ロード:
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動で読み込みます（テスト時等に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env のパースはシェル風の export やクォート、コメントに対応します。

- 冪等性:
  - J-Quants から取得したデータを保存する関数（save_*）は ON CONFLICT を利用して冪等に保存します。
  - ニュース収集は URL 正規化＋SHA-256 による記事 ID 生成で重複保存を防止します。

- フェイルセーフ:
  - AI の呼び出しや外部 API の失敗は原則フェイルセーフ（例: LLM 呼び出し失敗時はセンチメントを 0 にフォールバック）で、パイプライン全体を停止させない設計になっています（ログ出力は行います）。

- テスト容易性:
  - OpenAI 呼び出しや RSS ダウンロード等、外部依存箇所は内部呼び出しをモックしやすく分離されています（ユニットテスト時に patch 可能）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要モジュール構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースを銘柄ごとにスコア化して ai_scores に書き込む
    - regime_detector.py             — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py         — マーケットカレンダー管理（営業日判定等）
    - etl.py                         — ETL インターフェース再エクスポート
    - pipeline.py                    — ETL パイプラインと run_daily_etl
    - stats.py                       — 統計ユーティリティ（zscore_normalize 等）
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログ（DDL・初期化関数）
    - jquants_client.py              — J-Quants API クライアント（取得＋保存）
    - news_collector.py              — RSS 収集・前処理・保存（SSRF 対策等）
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum, value, volatility）
    - feature_exploration.py         — 将来リターン、IC、統計サマリー等
  - (その他) strategy / execution / monitoring などのパッケージが想定される（__all__ に記載）

---

## 開発・運用上の補足

- ログレベルは環境変数 LOG_LEVEL で制御できます（デフォルト INFO）。
- KABUSYS_ENV は development / paper_trading / live のいずれか。live では実際の発注等を行う想定なので慎重に設定してください。
- DuckDB ファイルや SQLite 監視 DB のパスは環境変数で変更可能（デフォルトは data/ 以下）。
- ネットワーク周り（RSS、J-Quants、OpenAI）でタイムアウトやレート制限が発生することを考慮してリトライやスロットリングが組み込まれています。

---

もし README に追加したい内容（例: API キーの取得手順、より詳しい .env.example、CI に関する情報、運用用コマンド群など）があれば教えてください。README をそれに合わせて拡張します。