# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ用スキーマ、マーケットカレンダーなど、量化運用に必要な共通機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、マーケットカレンダーを差分取得して DuckDB に保存
  - 差分取得・バックフィル・ページネーション・リトライ・レートリミット対応
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出する品質チェック群
- ニュース収集 & 前処理
  - RSS フィードの取得、URL 正規化、SSRF 対策、記事の前処理、raw_news への冪等保存設計
- ニュースNLP（OpenAI）
  - ニュースを銘柄単位に集約して LLM（gpt-4o-mini）でセンチメント評価し ai_scores に書き込み
  - バッチ・リトライ・レスポンスバリデーションを実装
- 市場レジーム判定（AI + テクニカル）
  - ETF 1321 の 200 日移動平均乖離とマクロニュース LLM センチメントを合成して日次レジームを判定し market_regime に保存
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクター計算、将来リターン・IC（情報係数）計算、Zスコア正規化
- 監査ログ（Audit）
  - signal → order_request → execution をトレースする監査テーブルの DDL / 初期化ユーティリティ
- 設定管理
  - .env / 環境変数から設定を自動で読み込み（パッケージ配布後も動作するようにプロジェクトルート探索）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリのみで機能する部分もありますが、上記は主に ETL / AI / XML で必要です。

例（pip）:
pip install duckdb openai defusedxml

プロジェクトを配布形式で使う場合は requirements.txt / pyproject.toml を参照してください。

---

## 環境変数 / 設定

config.Settings から環境変数を参照します。自動でプロジェクトルートの `.env` → `.env.local` を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須（少なくとも設定しておくべきもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携等で使用）
- SLACK_BOT_TOKEN: Slack 通知用トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルト値あり
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL: ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動読み込みを無効化
- KABUS_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで参照）

.env.example を参考に .env を用意してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   git clone <repo_url>
   cd <repo_dir>

2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使ってください）
   pip install -e .

4. 環境変数設定
   プロジェクトルートに `.env` を作成するか、環境変数を設定してください。
   例（.env）:
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUS_API_PASSWORD=...

   自動読み込みは config.py がプロジェクトルート（.git または pyproject.toml を基準）を探して行います。

---

## 使い方（主要な例）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り）を受け取ることが多いです。

- DuckDB 接続を作る
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントスコアを作る（OpenAI API キーを環境変数または api_key 引数で）
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数にセットするか、api_key="sk-..." を渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み件数: {written}")

- 市場レジーム判定を実行する
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルに書き込まれる

- 監査ログ用 DB を初期化する
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # 必要なら同じ接続を本 DB として使うか別 DB に保管する

- Zスコア正規化ユーティリティ（研究用）
  from kabusys.research import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])

---

## 実装上のポイント / 注意点

- ルックアヘッドバイアス対策
  - 多くの処理（ETL・研究関数・AIスコアリング）は date 引数を明示的に受け取り、datetime.today()/date.today() を内部で参照しない設計です。バックテストや再現性のため、必ず target_date を明示的に与えることが推奨されます。
- 冪等性
  - DuckDB への保存は可能な限り ON CONFLICT / UPSERT を使い冪等に設計されています（ETL の再実行が安全）。
- OpenAI 呼び出し
  - AI モジュールは gpt-4o-mini を使用する想定で JSON mode を利用しています。API 制限やエラー時のフォールバック（0.0）やリトライを実装しています。
- セキュリティ
  - RSS フィード取得では SSRF 対策（リダイレクト先検証、プライベート IP 拒否）、XML の defusedxml 使用、受信サイズ制限などを施しています。
- テスト容易性
  - OpenAI / ネットワーク呼び出し部分は内部関数を分離しており、unittest.mock.patch による差し替えが可能です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                    - 環境変数・設定の読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                 - ニュースセンチメント解析（OpenAI）
    - regime_detector.py          - マクロ＋テクニカルで市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py                 - ETL パイプライン（run_daily_etl 等）
    - jquants_client.py           - J-Quants API クライアント + DuckDB 保存
    - news_collector.py           - RSS 収集・前処理
    - calendar_management.py      - マーケットカレンダー管理・営業日判定
    - quality.py                  - データ品質チェック群
    - stats.py                    - 共通統計ユーティリティ（zscore 等）
    - audit.py                    - 監査ログ DDL と初期化ユーティリティ
    - pipeline.py (ETLResult クラス再エクスポート)
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py          - モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py      - 将来リターン、IC、統計サマリー等

（上記以外に strategy / execution / monitoring 等のパッケージ公開を意図した __all__ が定義されていますが、本コードベースの代表モジュールは上記です。）

---

## 追加情報 / トラブルシューティング

- .env の自動読み込み
  - config._find_project_root() は __file__ を起点に親ディレクトリを探索し .git または pyproject.toml を見つけたルートにある `.env` / `.env.local` を読み込みます。テストなどで自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のバージョン差異
  - 一部の executemany / バインド動作は DuckDB のバージョンに依存する可能性があるため、動作しない場合は DuckDB のバージョンを揃えてください（コード内に互換性対策の注記あり）。
- OpenAI SDK 互換性
  - 現在コードは openai パッケージの Chat Completions JSON mode を前提とした呼び出しを行います。OpenAI SDK のバージョン差分で呼び出し API が異なる場合は適宜ラッパーを差し替えてください。

---

開発・運用にあたっての詳細は各モジュールの docstring（ソース内コメント）に設計方針や処理フローが詳細に書かれています。まずは ETL → ニュース収集 → スコア算出の順で実行して動作確認することを推奨します。必要であれば README をプロジェクト固有のセットアップ（CI / secrets 管理 / scheduler 連携）に合わせて追記してください。