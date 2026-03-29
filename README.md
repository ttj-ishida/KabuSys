# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・ニュース収集／NLP（OpenAI）・市場レジーム判定・ファクター計算・データ品質チェック・監査ログ（オーダー/約定トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は日本株の定量投資／自動売買基盤向けに設計された Python パッケージです。主な目的は以下です。

- J-Quants API からの株価／財務／カレンダー等の ETL（差分更新・品質チェック付き）
- RSS ニュースの収集と前処理、OpenAI を用いた銘柄別ニュースセンチメント付与
- ETF（1321）を用いた市場レジーム判定（MA200 とマクロニュースの合成）
- ファクター計算（Momentum / Volatility / Value 等）と研究ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注フローの監査／トレーサビリティ用の監査 DB 初期化ユーティリティ

パッケージはモジュール化されており、ETL / data / ai / research / monitoring / execution 等の責務に分かれています。

---

## 主な機能一覧

- ETL
  - run_daily_etl: 日次の ETL（カレンダー・株価・財務 + 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL ジョブ
  - jquants_client: API 呼び出し、保存（DuckDB へ冪等保存）、トークン自動リフレッシュ、レート制御
- データ管理
  - news_collector: RSS フィード取得、前処理、raw_news への保存（SSRF 対策・gzip 上限管理 等）
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - audit: 監査ログスキーマの初期化・監査 DB 作成ユーティリティ
- AI（OpenAI）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出（gpt-4o-mini、JSON mode、バッチ処理、リトライ）
  - regime_detector.score_regime: ETF MA200 とマクロニュースを合成して市場レジームを判定（bull/neutral/bear）
- 研究用ユーティリティ
  - research.factor_research: momentum / volatility / value のファクター計算
  - research.feature_exploration: 将来リターン、IC（Information Coefficient）、統計サマリー
  - data.stats.zscore_normalize: クロスセクションの Z スコア正規化ユーティリティ
- 設定管理
  - config.Settings: 環境変数からの設定読み込み（.env 自動読み込み・保護・検証）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の構文で 3.10+ を想定）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン（またはパッケージを取得）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 必要な主な依存:
     - duckdb
     - openai
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトに requirements.txt があれば
   # pip install -r requirements.txt
   ```

4. パッケージをインストール（開発インストール）
   ```
   pip install -e .
   ```

5. 環境変数（.env）を用意
   プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。設定例（必須項目はプロジェクト利用機能による）:

   - 必須（利用機能により必要）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API 用パスワード（注文機能を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack 通知先チャンネルID
   - 任意
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を使う場合）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite パス（モニタリング用）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

注意:
- パッケージ起動時、config モジュールがプロジェクトルート（.git または pyproject.toml）を探索して自動で .env/.env.local を読み込みます。テストなどで自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings は未設定の必須変数を参照すると ValueError を投げます。

---

## 使い方（代表的な例）

以下は簡単な利用例です。実行前に `.env` を準備し、必要な依存をインストールしておいてください。

- DuckDB 接続を作って ETL を実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  # 指定日を省略すると today が使われます
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア付与（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n_written)
  ```

- 市場レジーム判定（ETF 1321 MA200 + マクロニュース）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（発注履歴用 DuckDB）
  ```python
  from pathlib import Path
  import duckdb
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db(Path("data/audit.duckdb"))
  ```

- ファクター計算・研究ユーティリティ（例: momentum）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

ログ出力・動作環境:
- settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- settings.env により本番・ペーパー等の振る舞いを切り替えできます（development, paper_trading, live）。

---

## ディレクトリ構成（主要ファイル）

簡略化したトップレベルと主要モジュール:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py             — ニュース NLP（score_news）
      - regime_detector.py      — 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py       — J-Quants API クライアント（fetch / save）
      - pipeline.py             — ETL パイプライン（run_daily_etl 等）
      - etl.py                  — ETL 型の再エクスポート（ETLResult）
      - news_collector.py       — RSS 収集と前処理
      - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
      - quality.py              — データ品質チェック
      - stats.py                — 統計ユーティリティ（zscore）
      - audit.py                — 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py      — ファクター計算
      - feature_exploration.py  — 将来リターン / IC / 統計サマリー
    - (その他: strategy / execution / monitoring 等の名前空間は __all__ で公開予定)

---

## 設定（環境変数の主な一覧）

- JQUANTS_REFRESH_TOKEN (必須: J-Quants 通信が必要な機能で)
- KABU_API_PASSWORD (kabu API を使う場合)
- OPENAI_API_KEY (news_nlp / regime_detector を使う場合)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (モニタリング DB のパス)
- KABUSYS_ENV ∈ {development, paper_trading, live}（デフォルト development）
- LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}

config.Settings は未設定の必須項目を参照した際に ValueError を投げます。自動読み込みはプロジェクトルートの `.env` / `.env.local` に対して行われます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 注意点 / トラブルシューティング

- OpenAI 呼び出しはレスポンス JSON の形式（JSON mode）を前提にパースします。不正な出力やパース失敗時はフェイルセーフで 0.0 / スキップ にフォールバックする実装になっていますが、誤った API キーや API 料金設定には注意してください。
- J-Quants API はレート制限が厳しいため、jquants_client は内部でスロットリングとリトライを行います。認証トークンが古い場合、自動リフレッシュを試みます。
- DuckDB のバージョン差による executemany の挙動やリストバインドの違いに注意（pipeline / news_nlp 内で考慮済み）。
- news_collector は SSRF 対策・受信サイズ制限・gzip 解凍後上限検査など安全性を考慮しています。外部 RSS の巨大レスポンスや圧縮異常に対してはスキップする場合があります。
- config._find_project_root により .env 自動読み込みはパッケージ配置（.git か pyproject.tomlがあるルート）を基準に行います。パッケージ配布後の環境では自動ロードが期待通りに動作しない場合があります。その場合は環境変数を直接設定してください。

---

## ライセンス・コントリビュート

（ここにはプロジェクトのライセンス情報や貢献方法を記載してください。リポジトリの LICENSE を参照するか、プロジェクトポリシーに合わせて追記してください）

---

README に書かれている使い方は主要な API を示したサンプルです。詳細な仕様・更に踏み込んだ設定（発注処理、リアルタイム監視、Slack 通知や kabu API 統合等）は対応するモジュールのドキュメントやコード内コメントを参照してください。必要であれば、使い方の追加例（ETL スケジューリング、監査ログの参照クエリ、OpenAI のレスポンス例と検証方法など）を追記します。