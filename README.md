# KabuSys

日本株向けの自動売買 / データプラットフォームの骨組みを提供する Python パッケージです。  
データ ETL、ニュースの NLP スコアリング、ファクター計算、監査ログなどをモジュール単位で実装しています。

---

## プロジェクト概要

KabuSys は次の目的を想定したライブラリ群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得と DuckDB への冪等保存（ETL）
- RSS ニュース収集と前処理（raw_news 保存）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_score）および市場レジーム判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ定義と初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・将来日付等）

意図：
- バックテストや本番運用で Look-ahead バイアスを起こさないよう設計（日付参照の扱いに注意）
- DuckDB を中心としたローカル DB ベースのデータプラットフォーム
- 冪等性（ON CONFLICT）やフォールバック・フェイルセーフを重視

---

## 主な機能一覧

- 環境設定管理
  - .env の自動読み込み（プロジェクトルート検出） / 必須環境変数チェック
- Data (kabusys.data)
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証, ページネーション, レート制御, 保存関数）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS -> raw_news, SSRF 対策・トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- AI (kabusys.ai)
  - news_nlp.score_news: RSS からのニュースをまとめて LLM に投げ、ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースを組み合わせて市場レジーム判定
- Research (kabusys.research)
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン・IC・統計サマリー（calc_forward_returns, calc_ic, factor_summary, rank）

---

## 必要環境 / 前提

- Python 3.10+
- 推奨パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- J-Quants API、OpenAI API の利用に必要なトークン

（プロジェクトで使用する依存はプロジェクト側で requirements.txt / pyproject.toml にまとめてください）

---

## 環境変数

主要な環境変数（必須／デフォルト値）：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先 channel id
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 設定環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール呼び出し時に使用）

自動で .env / .env.local をプロジェクトルートから読み込みます（CWD ではなくモジュール位置からルートを探索）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン
   - (例) git clone ...

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実際のプロジェクトでは requirements.txt または pyproject.toml を用意して pip / poetry で管理してください。

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（.env.example を参考に）。
   - 必須項目（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD など）を設定。

5. データベース初期化（監査ログ等）
   - 監査用 DB を初期化する例:
     ```python
     import kabusys.data.audit as audit
     conn = audit.init_audit_db("data/audit.duckdb")
     # conn は duckdb.DuckDBPyConnection
     ```

---

## 使い方（代表的な例）

以下は最小限の呼び出し例です。各関数は DuckDB の接続 (duckdb.connect(...)) を引数に取ります。

- DuckDB 接続作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー、株価、財務、品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアを生成して ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数に設定されていることが前提
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} scores")
  ```

- 市場レジーム判定（ETF 1321 + マクロニュース）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究モジュール例（モメンタム計算）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は各銘柄の mom_1m, mom_3m, mom_6m, ma200_dev を含む dict のリスト
  ```

- データ品質チェックを実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意点:
- AI 呼び出し（news_nlp / regime_detector）は OpenAI の API キーが必要です。api_key 引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL・J-Quants 呼び出しは API レート制限に注意してください（モジュール内で制御しています）。
- API 呼び出し失敗時は多くの箇所でフェイルセーフ（スキップ・デフォルト値）を取る設計です。

---

## ディレクトリ構成

リポジトリ内の主要ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数管理、.env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py       — ニュースの LLM スコアリング（score_news）
    - regime_detector.py— 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント / 保存関数
    - pipeline.py       — ETL パイプライン（run_daily_etl など）
    - etl.py            — ETL 結果クラス再エクスポート
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py — RSS 取得 / 前処理 / raw_news 保存ユーティリティ
    - stats.py          — 統計ユーティリティ（zscore_normalize）
    - quality.py        — データ品質チェック
    - audit.py          — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py  — 将来リターン計算・IC・summary
  - research/... その他ファイル

各モジュール内に詳細な docstring と設計意図が記載されています。まずは該当モジュールの docstring を参照してください。

---

## 運用上の注意 / ベストプラクティス

- 環境設定は .env（.env.local）で管理し、機密情報は共有しないこと。
- 本番環境（KABUSYS_ENV=live）で動かす前に paper_trading などで十分検証してください。
- DuckDB ファイルは定期バックアップを推奨します。
- OpenAI など外部 API のコスト・レート制限を運用ルールに組み込んでください。
- ニュース収集時は RSS ソースの信頼性と著作権にご注意ください。

---

必要であれば README に以下を追加できます：
- .env.example のテンプレート
- 依存パッケージの exact list（requirements.txt）
- CI / 開発用コマンド（pytest, lint など）
- よくあるトラブルシュート（認証エラー、DuckDB バージョン互換性など）

追加してほしい項目があれば教えてください。