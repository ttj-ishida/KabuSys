# KabuSys

日本株向け自動売買 / データ基盤ライブラリ (KabuSys)

このリポジトリは、日本株のデータETL、ニュースNLP、ファクター研究、監査ログ、ならびに市場レジーム判定を行うユーティリティ群をまとめたパッケージです。バックテストや実運用（paper/live）向けに設計されており、Look‑ahead バイアス防止・冪等性・堅牢な外部API呼び出しを重視しています。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ収集 / ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得して DuckDB に保存（ページネーション対応・リトライ・レート制御）
  - ETL 実行結果を表す ETLResult の提供

- データ品質チェック
  - 欠損データ、スパイク（急騰/急落）、重複、日付整合性チェック

- ニュース収集 / 前処理
  - RSS フィード取得（SSRF対策・トラッキングパラメータ除去・受信サイズ制限）
  - raw_news テーブルへの冪等保存、news_symbols との紐付け

- ニュースNLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント解析（gpt-4o-mini を利用）
  - レスポンス検証・バッチ処理・リトライロジック搭載

- 市場レジーム判定（Regime）
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースセンチメントを組み合わせて日次でレジーム（bull/neutral/bear）判定

- リサーチ向けユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Z スコア正規化

- 監査ログ（トレーサビリティ）
  - シグナル → 発注 → 約定のフローを追跡する監査用テーブル定義・初期化ユーティリティ

- 設定管理
  - .env / .env.local / OS 環境変数からの設定読み込み（プロジェクトルート検出・自動ロード。無効化オプションあり）

---

## 動作環境 / 前提

- Python 3.10 以上（型ヒントに union 演算子 `|` を使用）
- 主要依存ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ

実行環境に応じて追加パッケージが必要になる場合があります（例: requests 等）。requirements.txt がない場合は下記のようにインストールしてください：

例:
pip install duckdb openai defusedxml

またパッケージを開発インストールする場合:
pip install -e .

---

## 環境変数 / .env

パッケージは .env / .env.local（プロジェクトルート）を自動的に読み込みます（OS 環境変数が優先）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化できます。

主な環境変数（settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：データETL を使う場合）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注等を行う場合）
- KABU_API_BASE_URL: kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視用
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視しきい値
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

プロジェクトルートに .env.example を置く想定です。.env を作成して必要な値を設定してください。

---

## セットアップ手順

1. レポジトリをクローン
   - git clone <repo-url>

2. Python 環境の準備（仮想環境推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要パッケージのインストール
   - pip install duckdb openai defusedxml
   - （開発インストール）pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成し、必須値を設定:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - 必要に応じて他の変数も設定

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ ディレクトリ配下に DuckDB ファイルが作成されます。存在しない場合は自動作成されますが、手動で作る場合:
     - mkdir -p data

---

## 使い方（主要 API / 例）

以下はパッケージ内の主要ユーティリティの簡単な使い方例です。日付は標準ライブラリの date を使用します。

- DuckDB 接続の取得（例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコアを生成（ai.news_nlp）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API key は環境変数 OPENAI_API_KEY
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（ai.regime_detector）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key は OPENAI_API_KEY
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 必要に応じて同一 conn に対して他処理を続ける
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

注意:
- OpenAI 系 API を呼ぶ関数は、環境変数 `OPENAI_API_KEY` を参照します。引数で明示的に api_key を渡すことも可能です（テスト等で便利）。
- LLM/API 呼び出しはリトライやフェイルセーフ（問題時は 0.0 にフォールバック）を備えていますが、APIキーやレート制限には注意してください。

---

## よく使うモジュールの説明

- kabusys.config
  - 環境変数／.env の自動読込、settings オブジェクト（各種設定）

- kabusys.data
  - jquants_client: J-Quants API とのやり取り、DuckDB への保存関数
  - pipeline: ETL のメインロジック（run_daily_etl 等）
  - news_collector: RSS 取得・前処理・raw_news への保存
  - calendar_management: 市場カレンダー操作（営業日判定等）
  - quality: データ品質チェック群
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログ用テーブルの初期化・管理

- kabusys.ai
  - news_nlp: ニュースセンチメント（銘柄毎 ai_score）生成ロジック
  - regime_detector: ETF＋マクロニュースで市場レジーム（bull/neutral/bear）判定

- kabusys.research
  - factor_research: モメンタム / バリュー / ボラティリティ等の計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等

---

## ディレクトリ構成

リポジトリの主要ファイル（抜粋）:

- src/kabusys/
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
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - audit...（監査関連ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
    - ...（研究用ユーティリティ）
  - ai, research, data 以下にそれぞれの機能実装がある

（上記はコードベースからの主要モジュール一覧です。詳細は各ファイル内の docstring を参照してください）

---

## 運用上の注意 / 設計上のポイント

- Look‑ahead バイアス対策
  - 多くの関数は内部で datetime.today() や date.today() を直接参照せず、外部から target_date を渡す設計です。バックテストや過去の時点での計算に適しています。

- 冪等性
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE / DO NOTHING を使い冪等性を担保しています。

- フェイルセーフ
  - 外部API（OpenAI, J-Quants）でのエラー時はリトライやゼロフォールバック等、上位プロセスが致命的エラーと扱わない実装が多くあります。必要に応じて呼び出し側でエラー検知やリトライを追加してください。

- セキュリティ
  - ニュース取得（RSS）では SSRF 対策、defusedxml を用いた XML パース、受信サイズ制限などを実装しています。

---

## 貢献・拡張

- 新しいニュースソースを追加する場合:
  - kabusys.data.news_collector.DEFAULT_RSS_SOURCES を拡張し、fetch_rss の結果を保存する処理（DB スキーマに合わせた保存）を作成してください。

- 新しいファクター・戦略を追加する場合:
  - kabusys.research に関数を追加し、zscore_normalize や feature_exploration のユーティリティを活用してください。

---

README は以上です。実際に触ってみて、必要な箇所（例: .env.example、requirements.txt、起動スクリプト）を追加すると運用がより楽になります。必要ならばサンプル .env や簡単な起動スクリプト、ユニットテストの雛形も作成しますのでお知らせください。