# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）〜 データ品質チェック、ニュース収集・LLMによるセンチメント評価、リサーチ用ファクター計算、監査ログの管理までを含むモジュール群を提供します。

主な目的は「バックテストや自動売買のための堅牢なデータ基盤と分析ツール群」を提供することです。

---

## 主な機能

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダー取得（ページネーション・トークン自動更新・レート制限対応）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック、カレンダー先読みなどを統合した日次 ETL（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付不整合の検出（QualityIssue を返す）
- ニュース収集（RSS）
  - URL 正規化・トラッキング除去・SSRF 対策・XML セキュリティ対策を行い raw_news に保存
- ニュース NLP（OpenAI を利用）
  - 銘柄ごとのセンチメントスコア算出（score_news）
  - 時間ウィンドウやバッチ処理、リトライ・エラーハンドリング実装
- 市場レジーム判定
  - ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（score_regime）
- 研究用モジュール
  - モメンタム / ボラティリティ / バリュー 等のファクター計算、将来リターン計算、IC（情報係数）など
- 監査ログ（Audit）
  - シグナル→発注→約定までをトレース可能にする監査テーブルの初期化・管理（init_audit_schema / init_audit_db）
- 安全・堅牢性
  - DuckDB を使ったローカル DB、JSON レスポンスの堅牢なパース、API リトライ・レート制御、SSRF・XML爆弾対策 等

---

## 必要条件 / 依存

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- そのほか標準ライブラリ（urllib 等）を多用

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン／展開する

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動的にロードされます。
     - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必要な場合）
     - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知等に使用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

   - `.env.example` を参考に作成してください（リポジトリに含めている場合）。

5. DuckDB データベースファイルのディレクトリ作成（必要な場合）
   - mkdir -p data

---

## 使い方（主要 API / 実行例）

以下は Python REPL / スクリプトからの基本的な使い方例です。

- 設定の利用
  - from kabusys.config import settings
  - settings.duckdb_path などでパス取得、settings.jquants_refresh_token で必須トークン取得（未設定なら例外）

- DuckDB 接続を開く
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(result.to_dict())

- ニュースセンチメントのスコアリング（LLM 使用）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要

- 市場レジーム判定（LLM 使用）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要

- 監査DBの初期化（監査専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # :memory: でも可

- 監査スキーマ単体初期化（既存接続へ）
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

注意:
- score_news / score_regime は OpenAI にアクセスするため API キー（引数で api_key を与えるか環境変数 OPENAI_API_KEY）を必ず設定してください。未設定時は ValueError を送出します。
- ETL / News / J-Quants の呼び出しはネットワークや API エラーに備えて例外処理を行ってください。多くの箇所でフェイルセーフ（失敗時はスキップして継続）やリトライが実装されていますが、呼び出し元でのログ・アラートは推奨されます。

---

## 環境変数・設定の自動読み込み挙動

- パッケージ読み込み時に次の順で .env を自動読み込みします（OS 環境変数が優先）
  1. OS 環境変数
  2. <project_root>/.env
  3. <project_root>/.env.local（存在すれば上書き）

- プロジェクトルートの判定はパッケージファイル位置から親ディレクトリ中に `.git` または `pyproject.toml` を探すことで行います。見つからない場合は自動ロードをスキップします。

- 自動ロードを無効化する環境変数:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル / モジュール）

以下は src/kabusys 以下の主要モジュール群（コードベースからの抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL インターフェース再エクスポート
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック
    - news_collector.py       — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py  — マーケットカレンダー管理（営業日判定・更新ジョブ）
    - audit.py                — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー等
  - ai/ (再掲)
  - その他: monitoring / execution / strategy 等（パッケージ初期に __all__ で公開）

（実際のリポジトリではさらに細かなファイル・テスト等が存在する想定です）

---

## 開発時のヒント / 注意点

- DuckDB の executemany に空リストを渡すと問題になるバージョンがあります（pipeline / ai で回避実装あり）。
- LLM 呼び出しは API レート・レスポンス形式の乱れ（余計なテキスト）に強い実装になっていますが、ユニットテストでは該当呼び出しをモックしてください（各モジュールにモック差し替え用にコメントあり）。
- タイムゾーン扱いに注意: DB 内の日付/時刻は基本的に UTC で処理・保存する方針です（audit.init で SET TimeZone='UTC' 等）。
- KABUSYS_ENV は "development" | "paper_trading" | "live" のいずれかを指定してください。live 時は is_live が True になります。

---

## サポート・コントリビューション

- バグ報告や機能提案は Issue を立ててください。
- コントリビュートする場合はコードスタイルやユニットテストを含めて PR を作成してください。

---

以上がこのコードベースの概要・セットアップ・基本的な使い方です。README の追加要望（例: CI 連携手順、より詳しい API リファレンス、サンプル .env.example）等があれば教えてください。