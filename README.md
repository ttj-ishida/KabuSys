# KabuSys

日本株向けの自動売買・データプラットフォームコンポーネント群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）までを含むユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引のための共通ライブラリ群です。主な目的は以下です。

- J-Quants API からのデータ取得と DuckDB への保存（ETL）
- RSS ニュース収集と前処理（raw_news）
- OpenAI を用いたニュースセンチメント算出（ai.score_news）
- ETF とマクロニュースを統合した市場レジーム判定（ai.score_regime）
- 研究用ファクター計算（research）
- データ品質チェック（data.quality）
- 監査ログスキーマ（data.audit）によるシグナル→発注→約定の完全トレーサビリティ

設計上の特徴：
- ルックアヘッドバイアスに配慮（date.today() などを内部で直接参照する設計を避け、target_date を明示）
- API 呼び出しに対するリトライ・バックオフ（J-Quants / OpenAI）
- DuckDB を用いたローカルデータ管理と冪等保存（ON CONFLICT を利用）
- セキュリティ配慮（RSS の SSRF 対策、XML ディフェンス等）

---

## 主な機能一覧

- data（ETL / calendar / jquants_client / news_collector / quality / audit / stats）
  - run_daily_etl: 日次 ETL（市場カレンダー、株価、財務、品質チェック）
  - jquants_client: J-Quants API ラッパー（取得・保存・認証・ページネーション・レート制御）
  - news_collector: RSS 収集・前処理・保存
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - stats: z-score 正規化 等

- ai（news_nlp / regime_detector）
  - score_news: 指定日のニュースを銘柄ごとに集約して OpenAI でセンチメント評価し ai_scores に書き込む
  - score_regime: ETF (1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に書き込む

- research（factor_research / feature_exploration）
  - calc_momentum / calc_volatility / calc_value: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank: 研究用統計解析ユーティリティ

- config
  - 環境変数管理（.env 自動ロード、必須値チェック、環境フラグ）

---

## 前提（推奨環境）

- Python 3.10+
  - 型注釈（X | Y 形式）を使用しているため Python 3.10 以上が必要です
- 必要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - これ以外に標準ライブラリを使用

（プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - pyproject.toml / requirements.txt があればそれを使用してください。ない場合の例:
   ```
   pip install duckdb openai defusedxml
   ```

4. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```

5. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD：kabuステーション API のパスワード（発注機能等）
     - SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID：通知先 Slack チャネル ID
     - OPENAI_API_KEY：OpenAI API キー（ai モジュール使用時）
     - DUCKDB_PATH：デフォルト data/kabusys.duckdb（任意）
     - SQLITE_PATH：監視用 SQLite（任意）
     - KABUSYS_ENV：development / paper_trading / live（デフォルト development）
     - LOG_LEVEL：DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   例 .env（必要に応じて .env.local を使用して上書き可）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

6. （オプション）監査 DB 初期化
   ```py
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（代表例）

以下は Python スクリプトからの利用例です。全ての公開関数は DuckDB の接続オブジェクトと target_date を受け取る設計になっています（ルックアヘッドバイアス防止のため）。

- DuckDB に接続する（ファイルベース）
  ```py
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に保存する
  - OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込み銘柄数:", written)
  ```

- 市場レジーム判定を実行する
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用途）
  ```py
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

- 設定値にアクセスする（環境変数管理）
  ```py
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- OpenAI 呼び出しは失敗時にフェイルセーフ（スコア0など）で継続する設計ですが、API キーが未設定だと ValueError を送出します。テスト時は関数引数で api_key を注入するか、環境変数を設定してください。
- ETL の run_daily_etl は内部で複数ステップを実行し、失敗したステップは errors に記録され続行します（厳密な停止は呼び出し元で判断可能）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                    — 環境変数 / 設定管理（.env 自動ロード）
- ai/
  - __init__.py (score_news エクスポート)
  - news_nlp.py                 — ニュースの NLP スコアリング（OpenAI）
  - regime_detector.py          — 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py           — J-Quants API クライアント（取得・保存）
  - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
  - etl.py                      — ETLResult の再エクスポート
  - calendar_management.py      — 市場カレンダー管理（営業日判定・更新ジョブ）
  - news_collector.py           — RSS ニュース収集・前処理
  - quality.py                  — データ品質チェック
  - stats.py                    — 統計ユーティリティ（zscore 等）
  - audit.py                    — 監査ログスキーマ初期化（signal/order/execution）
- research/
  - __init__.py
  - factor_research.py          — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py      — 将来リターン・IC・統計サマリー等

テスト / ドキュメント（存在する場合）はリポジトリルートに配置されます。

---

## 実運用上の注意・設計上のポイント

- 環境切替:
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれか。is_live / is_paper / is_dev プロパティで判定可能。
- 自動 .env ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml）を基準に `.env` と `.env.local` を自動で読み込みます。テストなどで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- API リトライ / フェイルセーフ:
  - J-Quants / OpenAI の呼び出しはリトライと指数バックオフを備えています。LLM 応答のパースに失敗した場合は該当スコアを 0.0 に置き換えて継続する実装箇所があります（サービスの一部停止で ETL 全体が止まらないように設計）。
- DuckDB の互換性:
  - 一部の実装は DuckDB の特定バージョンの制約（executemany の空引数等）を考慮していますが、環境の DuckDB バージョンによっては微調整が必要な場合があります。
- セキュリティ:
  - RSS 収集は SSRF や XML Explosion（defusedxml）に対する保護を実装しています。外部 URL を扱う際は注意してください。

---

## さらに学ぶ / 拡張

- 取引（execution）層、リスク管理、ポートフォリオ構築、外部ブローカー連携（kabu API 呼び出し）などは別モジュール／サービスとして接続する想定です（kabu ステーション API 用設定は用意されています）。
- 研究用途のコード（research）を基にバックテスト / シグナル生成ロジックを追加可能です。
- OpenAI のモデルやレスポンス形式に変更があった場合は ai モジュールのレスポンスパース部分を調整してください。

---

必要があれば以下も作成します：
- .env.example（必須環境変数テンプレート）
- 簡易 CLI スクリプト（ETL/run_news/score_regime 等）
- デプロイ / CI 用の手順（Dockerfile, GitHub Actions 等）

ご希望があれば、用途に合わせた README の追加セクション（例: デプロイ手順、運用 runbook、開発ガイド）を作成します。