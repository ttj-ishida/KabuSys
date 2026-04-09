# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（データ取得・保存・品質チェック）、ニュース NLP（LLM を使った銘柄センチメント付与）、市場レジーム判定、監査ログ（トレーサビリティ）、ファクター研究ユーティリティなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、J-Quants / RSS / 各種 API からデータを集約し、DuckDB を中心に保存・品質チェックを行い、その上で下流の自動売買やリサーチ処理を実行するための共通ライブラリ群です。設計上の特徴:

- Look-ahead bias を避ける設計（内部で `datetime.today()` / `date.today()` を直接参照しない等）
- DuckDB をデータ基盤として使用
- J-Quants API 用の堅牢なクライアント（レート制御・リトライ・トークン自動リフレッシュ）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON モード）
- ETL や品質チェックが独立し、部分失敗時も他処理を継続する堅牢性
- 監査ログ（signal → order_request → executions）テーブルで発注フローをトレーサビリティ可能

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）、設定ラッパ
  - 主要環境変数: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, 等
- kabusys.data
  - jquants_client: J-Quants API からの取得 / DuckDB への冪等保存（raw_prices/raw_financials/market_calendar 等）
  - pipeline: 日次 ETL（prices / financials / calendar）と品質チェックの統合エントリポイント（run_daily_etl）
  - quality: 欠損・重複・スパイク・日付不整合などの品質チェック
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策・XML 脆弱性対策あり）
  - audit: 監査ログテーブル定義と初期化ユーティリティ（init_audit_db / init_audit_schema）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュース記事を銘柄単位に集約し LLM に投げて ai_scores を作成
  - regime_detector.score_regime: ETF（1321）200 日移動平均乖離とマクロニュースセンチメントを合成して market_regime を作成
- kabusys.research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: forward returns, IC（Information Coefficient）計算、統計サマリー等

---

## 前提 / 要件

- Python 3.9+（型アノテーションや一部機能に合わせて調整してください）
- 主な依存パッケージ（プロジェクトに requirements.txt があればそちらを使用）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）
- 環境変数: JQUANTS_REFRESH_TOKEN（必須）、OPENAI_API_KEY（AI 機能利用時）

---

## セットアップ手順

1. リポジトリをクローン / コピー
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```bash
     pip install -r requirements.txt
     ```
   - 主要パッケージだけ手動で:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. パッケージを編集モードでインストール（開発）
   ```bash
   pip install -e .
   ```

5. 環境変数を用意
   - プロジェクトルートに `.env` を配置すると自動読み込みされます（自動ロードはデフォルトで有効）。
   - 例: `.env`
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方

以下は代表的な利用例です。実行は Python スクリプトや CLI ラッパーから行ってください。

- DuckDB 接続の作成（デフォルト DB パスは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を走らせる
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI API キーが必要）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/monitoring.duckdb")
  # conn_audit は初期化済みの DuckDB 接続
  ```

- ファクター計算 / 研究ユーティリティ
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

注意点:
- OpenAI を用いる関数は `OPENAI_API_KEY` を環境変数に設定するか、関数の `api_key` 引数で明示的に渡してください。
- ETL やニュース収集は大規模な DB 書き込みを行うため、実行前にバックアップや接続先を確認してください。
- DuckDB の `:memory:` もサポートしている関数があります（テスト用途）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。
- OPENAI_API_KEY: OpenAI の API キー（news_nlp, regime_detector で使用）。
- KABU_API_PASSWORD: kabu ステーション API のパスワード（実行時の注文機能で使用）。
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（data/monitoring.db）
- PAPER_FILL_MODE: paper trading 時のフィルモード（instant|partial|never|reject）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

---

## ディレクトリ構成

主要なファイル・モジュール（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - quality.py                     — データ品質チェック（check_missing_data 等）
    - news_collector.py              — RSS 収集・保存
    - calendar_management.py         — 市場カレンダー / 営業日判定
    - audit.py                       — 監査テーブル定義・初期化
    - etl.py                         — ETL インターフェース再エクスポート
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py             — momentum/value/volatility 等
    - feature_exploration.py         — forward returns / IC / factor_summary
  - research/...                      — 研究用ユーティリティ群
  - ...（他モジュール）

（上記は主要ファイルの一覧です。実際のリポジトリにはさらに補助モジュールやテスト等が含まれる可能性があります）

---

## 開発上の注意・設計方針（抜粋）

- Look-ahead bias を持ち込まないため、関数は基本的に target_date を明示して処理します。
- 外部 API の呼び出しはリトライ / バックオフ / フォールバックを備え、失敗時に全体が停止しないように設計されています。
- DuckDB へ保存する際は冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を考慮している箇所が多くあります。
- RSS 周りは SSRF / XML 脆弱性対策（defusedxml、リダイレクトチェック、プライベートアドレスチェック）を実装しています。
- OpenAI 呼び出しは JSON Mode を使い、レスポンスのパース・バリデーションを厳格に行います。API 失敗時は安全側のデフォルト（0.0 等）にフォールバックします。

---

## よくある運用例 / ヒント

- ローカルで試す場合は DuckDB をローカルファイルに設定し、まずは ETL を一日分だけ走らせてテーブルの状態を確認することを推奨します。
- OpenAI の利用はコストがかかるため、開発時はモック化（ユニットテスト内で _call_openai_api をパッチ）してください。コード中でも差し替え可能な設計になっています。
- .env に機密情報を置く際は .gitignore を確認し、リポジトリに含めないようにしてください。

---

## 連絡先 / 貢献

バグ修正や機能提案は Issue を立ててください。Pull Request は歓迎します。コーディング規約やテスト基準に従って PR を作成してください。

---

README は以上です。必要であれば、セットアップスクリプト（requirements.txt / example .env）や実行用の CLI ラッパーのテンプレートを追加で作成できます。どの部分を優先して詳細化したいか教えてください。