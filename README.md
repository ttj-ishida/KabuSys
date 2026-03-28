# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
J-Quants / RSS / OpenAI を利用したデータ取得・品質チェック・ニュースNLP・市場レジーム判定・ETL 等の共通処理を提供します。

## 主な特徴
- J-Quants API からの差分取得（株価／財務／上場情報／カレンダー）と DuckDB への冪等保存
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）とニュースベースの銘柄別センチメント解析（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価の組合せ）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- 監査ログ（signal/order/execution）のスキーマ定義と初期化ユーティリティ
- ETL の高階 API（run_daily_etl）で日次パイプラインを一気通貫で実行

---

## 機能一覧（モジュール別）
- kabusys.config
  - .env 自動読み込み（`.env` → `.env.local`）、設定取得（settings）
- kabusys.data
  - jquants_client: J-Quants からの取得 / DuckDB 保存（差分・ページング・リトライ・レート制御）
  - pipeline: ETL パイプライン（run_daily_etl、run_prices_etl、...）
  - calendar_management: JPX カレンダー管理・営業日の判定ユーティリティ
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策・gzip 上限等）
  - quality: データ品質チェック（missing / spike / duplicates / date consistency）
  - stats: zscore 正規化ユーティリティ
  - audit: 監査ログテーブル定義・初期化ユーティリティ（init_audit_schema / init_audit_db）
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) MA とマクロニュース LLM を組合せて市場レジームを判定し market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 動作要件
- Python 3.10+
- 主なライブラリ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード / Slack 等）

pip の requirements.txt を用意している場合はそれを利用してください。なければ最低限以下をインストールしてください:
pip install duckdb openai defusedxml

---

## 環境変数（主なもの）
必須の環境変数（Settings で _require として参照されるもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API のパスワード（発注関連）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot Token
- SLACK_CHANNEL_ID       : Slack チャンネル ID

任意／デフォルトあり
- KABUSYS_ENV            : development / paper_trading / live（デフォルト development）
- LOG_LEVEL              : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env ロードを無効化
- OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime で参照）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : 監視などに使う SQLite パス（デフォルト data/monitoring.db）

自動で .env / .env.local をプロジェクトルート（.git または pyproject.toml の祖先）から読み込みます。`.env.local` が `.env` を上書きします。テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（例）
1. リポジトリをクローン
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリのインストール
   - pip install -r requirements.txt
   - または: pip install duckdb openai defusedxml
4. 環境変数の設定
   - プロジェクトルートに .env ファイルを作成（.env.example を参照する想定）
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data
6. 監査 DB 初期化（オプション）
   - Python で init:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な利用例）
以下は Python REPL やスクリプトから利用する例です。

- DuckDB 接続と日次 ETL 実行
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントスコア生成（OpenAI API キーが環境に必要）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {n} codes")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))

- 監査DBの初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- ファクター計算（研究用途）
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))

注意:
- OpenAI 呼び出しはレスポンスを JSON Mode（response_format）で要求しています。API キーとモデル使用のコストに注意してください。
- J-Quants API 呼び出しにはレート制限とトークンの管理（自動リフレッシュ）があります。jquants_client にて制御済みです。

---

## ディレクトリ構成（主要ファイル）
（リポジトリ内 src/kabusys を基準）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数と .env 自動読み込み / Settings 提供
- src/kabusys/ai/
  - news_nlp.py       : ニュースセンチメント解析（score_news）
  - regime_detector.py: 市場レジーム判定（score_regime）
- src/kabusys/data/
  - jquants_client.py : J-Quants API クライアント（fetch / save 実装）
  - pipeline.py       : ETL パイプライン（run_daily_etl 等）
  - calendar_management.py : 市場カレンダーの管理と営業日ユーティリティ
  - news_collector.py : RSS 収集・前処理
  - quality.py        : データ品質チェック（QualityIssue）
  - stats.py          : zscore 正規化等
  - audit.py          : 監査ログスキーマと初期化ユーティリティ
  - etl.py            : ETLResult の再エクスポート
- src/kabusys/research/
  - factor_research.py      : Momentum / Value / Volatility 等
  - feature_exploration.py  : 将来リターン / IC / 統計サマリー 等
- src/kabusys/research/__init__.py
- （その他）strategy, execution, monitoring パッケージ参照用（__all__ に含まれるが詳細はコードベース参照）

---

## 運用上の注意
- Look-ahead バイアス防止: 多くの関数は内部で date.today() を直接参照せず、target_date を明示的に渡す設計です。バックテストや再現性確保のため target_date を明示することを推奨します。
- 自動 .env ロードは便利ですが CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して明示的に設定を注入してください。
- OpenAI / J-Quants の API 使用には料金・レート制限があるため、テスト時はモック（unittest.mock.patch）を使用することを推奨します。score_news / regime_detector の内部では _call_openai_api をモック可能です。
- RSS収集（news_collector）は SSRF 対策や受信サイズ制限など安全対策が実装されていますが、実運用では接続先や許可ホストの運用ポリシーを確認してください。

---

## 追加情報 / 開発
- コードは型注釈・ロギングを多用しているため、開発時は LOG_LEVEL=DEBUG を設定すると挙動観察に便利です。
- 新しい API やモデルを追加する場合、既存のフェイルセーフ設計（API 失敗時のフォールバック）に合わせて実装してください。

---

この README はコードベースの主要点をまとめたものです。より詳細な設計仕様（DataPlatform.md / StrategyModel.md 等）がある場合はそちらも参照してください。必要に応じて README の補足（例: CLI、Docker、CI 設定）を追加できます。