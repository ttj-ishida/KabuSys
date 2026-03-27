# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
（ETL / データ品質 / ニュース収集 / AIセンチメント / ファクター研究 / 監査ログ 等の機能を提供）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方
- ディレクトリ構成
- 環境変数（.env）の例
- トラブルシューティング・設計上の注意

---

## プロジェクト概要

KabuSys は日本株を対象にした内部データ基盤とリサーチ／自動売買補助のためのモジュール群です。主な狙いは以下です。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- DuckDB を用いたローカルデータ保存と品質チェック
- RSS ベースのニュース収集と前処理（SSRF / Gzip / トラッキングパラメータ対策）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 / マクロ）
- マーケットレジーム判定（ETF の MA 乖離 + マクロセンチメントの合成）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 実行監査（signal → order_request → execution をトレースする監査スキーマ）

設計上のポイント:
- ルックアヘッドバイアス対策（target_date ベースで操作、datetime.today 参照を避ける）
- 冪等保存（ON CONFLICT / UPDATE を多用）
- API 呼び出し時のリトライ・レートリミット制御・フェイルセーフ

---

## 機能一覧

- config
  - 環境変数自動読み込み（プロジェクトルートの .env / .env.local）
  - 必須設定のラップ（settings オブジェクト）
- data
  - jquants_client: J-Quants API からの取得・DuckDB への保存（ページネーション・認証リフレッシュ・リトライ）
  - pipeline: 日次 ETL（calendar / prices / financials）+ 品質チェック（quality）
  - news_collector: RSS 取得・前処理（URL 正規化、SSRF 対策、gzip 対応）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: 欠損・重複・スパイク・日付不整合の検出
  - stats: Zスコア正規化ユーティリティ
  - audit: 監査ログ用テーブルの初期化 / インメモリ DB 初期化ユーティリティ
- ai
  - news_nlp: 銘柄別ニュースを LLM でスコアリングし ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA200 乖離とマクロセンチメントを合成して market_regime テーブルへ書き込み
- research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー

---

## セットアップ手順

前提
- Python 3.10+
- ネットワーク接続（J-Quants / OpenAI / RSS）

1. リポジトリをクローン / パッケージをインストール
   （プロジェクトに requirements.txt がある想定。未提供の場合は下記必須パッケージを直接インストール）

   pip 例:
   ```
   python -m pip install duckdb openai defusedxml
   # 開発用: pip install -e .
   ```

2. 環境変数または .env ファイルを用意
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. DuckDB ファイル・SQLite 等のパス設定は環境変数で
   - デフォルトの DuckDB パスは `data/kabusys.duckdb`
   - 設定は .env の `DUCKDB_PATH` / `SQLITE_PATH` に記載

4. 必須外部 API の認証情報（例）を .env に設定
   - J-Quants: JQUANTS_REFRESH_TOKEN
   - OpenAI: OPENAI_API_KEY （関数引数でも指定可能）
   - kabuステーション: KABU_API_PASSWORD（発注層利用時）
   - Slack 通知: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

5. （任意）監査 DB 初期化用に duckdb をインストール済みであること

---

## 使い方（代表的な例）

以下は Python スクリプトからの呼び出し例です。実行前に必要な環境変数を設定してください。

- ETL（日次パイプライン）実行例
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア（LLM）実行例
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定実行例
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査 DB 初期化（監査用 DuckDB を作成）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブル（signal_events, order_requests, executions 等）が作成されます
  ```

- リサーチ用ファクター計算例
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(f"計算済み銘柄数: {len(momentum)}")
  ```

- RSS 取得（ニュースコレクタ）例
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  print(len(articles))
  ```

注意:
- OpenAI の呼び出しは API キーを引数で明示的に渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- J-Quants の認証は `JQUANTS_REFRESH_TOKEN` を .env 等に設定しておくことで自動で ID トークンを取得します（モジュールキャッシュあり）。

---

## ディレクトリ構成

主要ファイルのみ抜粋（src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                        -- 環境変数・.env ロード / settings
  - ai/
    - __init__.py
    - news_nlp.py                     -- ニュースセンチメント（銘柄別）
    - regime_detector.py              -- マクロ + ETF MA 合成によるレジーム判定
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント（取得・保存）
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - etl.py                          -- ETLResult 再エクスポート
    - news_collector.py               -- RSS 取得・前処理
    - calendar_management.py          -- マーケットカレンダー管理 / 営業日ユーティリティ
    - quality.py                      -- データ品質チェック
    - stats.py                        -- 統計ユーティリティ（zscore_normalize）
    - audit.py                         -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py              -- momentum/value/volatility 等
    - feature_exploration.py          -- forward returns, IC, summary

この README で触れていない細かなモジュールや関数はコード内の docstring に設計方針や使用上の注意が詳述されています。

---

## 環境変数（.env）の例

以下は利用する主要な環境変数の例です（.env にコピーして編集してください）。

例 (.env):
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション（発注用）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# データベースパス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 動作モード / ログレベル
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

注意:
- config.Settings は必須の変数が未設定だと ValueError を送出します（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。

---

## トラブルシューティング・設計上の注意

- OpenAI / J-Quants API エラー
  - モジュールはリトライやフェイルセーフを組み込んでいます。例えば news_nlp / regime_detector は API が失敗した場合に該当スコアを 0.0 にフォールバックするなどの挙動があります（ログに警告が出ます）。
- Look-ahead バイアス
  - すべての AI / リサーチ・処理は target_date ベースでの参照を行い、datetime.today() を無条件に参照しないよう設計されています。バックテストでの使用には注意してください。
- DuckDB executemany の制約
  - 一部の保存処理は DuckDB のバージョン差異を考慮して空リストの executemany を避ける実装になっています。
- RSS のセキュリティ
  - news_collector は SSRF・XML Bomb・Gzip Bomb 等に対する防御を実装しています。独自 RSS を追加する際は URL スキームやホストの安全性に注意してください。
- 自動 .env ロードを無効化したい場合
  - テストなどで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

開発や運用で README の補足が必要であれば、実行したいユースケース（ETL スケジュール、発注ワークフロー、監査トレース要件 等）を教えてください。用途に合わせたサンプルスクリプトや運用手順を作成します。