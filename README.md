# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント解析）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（約定トレーサビリティ）などの機能を提供します。

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分・バックフィル・ページネーション・リトライ・レート制御を備えた実装
- ニュース収集・NLP
  - RSS からニュースを収集し raw_news に保存（SSRF 対策、URL 正規化）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント解析（ai_scores へ保存）
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュースセンチメントを合成し、日次で `market_regime` に保存
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等の定量ファクター計算（DuckDB + SQL）
  - 将来リターン計算、IC（スピアマン）計算、Z スコア正規化等
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合（将来日付／非営業日データ）を検出
- 監査ログ（audit）
  - signal → order_request → execution のトレーサビリティ用テーブル定義および初期化ユーティリティ
- 設定管理
  - .env（.env.local 含む）および環境変数から設定を読み込み（自動ロード、プロジェクトルート検出）

---

## 動作要件

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging 等）

（実際は pyproject.toml / requirements.txt を参照してインストールしてください）

---

## インストール（開発環境）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

3. パッケージをプロジェクトにインストール（開発モード）
   - pip install -e .

---

## 設定（環境変数 / .env）

設定は環境変数またはプロジェクトルートに配置された `.env` / `.env.local` から自動読み込みされます。
プロジェクトルートは `.git` か `pyproject.toml` を含む親ディレクトリを基準に自動検出されます。

読み込み優先順位:
- OS 環境変数 > .env.local > .env

自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途）。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必要時) — OpenAI 呼び出しに使用
- KABU_API_PASSWORD (必須: kabu ステーション連携時)
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視用設定
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.git やパッケージ内に `.env.example` を用意し、それを元に `.env` を作成してください。

---

## セットアップ（データベース初期化等）

- 監査ログ用の DuckDB を初期化する例:

  from pathlib import Path
  import duckdb
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db(Path("data/audit.duckdb"))  # ":memory:" も可

- ETL 用の DuckDB（メイン DB）はデフォルト `data/kabusys.duckdb` を使用することを想定しています（設定で変更可能）。

---

## 使い方（サンプル）

以下は代表的な呼び出し例です。実行環境に必要な環境変数（JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY など）を設定した状態で実行してください。

- 日次 ETL の実行

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（特定日）のスコア取得（OpenAI が必要）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # 戻り値: 書き込んだ銘柄数

- 市場レジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査スキーマの初期化（既存接続に追加）

  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)

- 研究用ファクター計算の呼び出し例

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))

---

## 重要な挙動・注意点

- Look-ahead バイアス防止:
  - 多くの関数は内部で date.today() や datetime.now() を安易に参照せず、外部から明示的に target_date を受け取る設計です。バックテスト用途では必ず適切な target_date を渡してください。
- エラーのフェイルセーフ設計:
  - OpenAI / 外部 API の失敗時、多くの処理は例外ではなくフォールバック（ゼロスコア等）で継続するか、ETL 結果にエラー情報を収集して返します。
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在する階層）を基準に `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany に空リストを渡すと不具合があるバージョンへの対処が各所に含まれています。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py — パッケージエクスポート
- config.py — 環境変数 / 設定管理（自動 .env 読込、settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント解析）
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 & DuckDB への保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult 再エクスポート
  - calendar_management.py — 市場カレンダー管理、営業日判定
  - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
  - quality.py — データ品質チェック
  - news_collector.py — RSS 収集・前処理・保存
  - audit.py — 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py — モメンタム／ボラティリティ／バリュー等
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- monitoring, strategy, execution, など（パッケージ __all__ に含まれるが本 README に載っていないモジュールも存在）

---

## 開発・貢献

- コードベースはモジュール単位で分離されており、ユニットテストやモック差替えを想定した設計（API 呼び出しのラップ、_call_openai_api の差替えポイント等）になっています。
- Pull Request 前に静的解析・テストを実行してください（テストフレームワークは環境に応じて追加してください）。

---

README に記載の無い詳細（API の細かい挙動や追加の設定項目）はソースコード（各モジュールの docstring / 関数コメント）を参照してください。必要であれば README のサンプルやセットアップ手順を追加で整備します。