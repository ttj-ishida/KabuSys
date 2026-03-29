# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants / kabuステーション 等の外部連携を含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインとリサーチ / 戦略支援のためのユーティリティ群を提供する Python パッケージです。主な目的は以下です。

- J-Quants API からのデータフェッチ（株価/財務/カレンダー）
- DuckDB ベースの ETL パイプライン（差分取得・冪等保存・品質チェック）
- RSS ベースのニュース収集と機械学習（LLM）によるニュースセンチメント分析
- 市場レジーム判定（MA200 と マクロセンチメントの合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 監査（signal → order → execution）のためのテーブル初期化・管理
- 運用向け設定管理（.env 自動読み込み、環境フラグ、ログレベル）

設計上の共通方針として「ルックアヘッドバイアスの防止」「外部API失敗時のフェイルセーフ」「DuckDB による効率的な集計」が重視されています。

---

## 主な機能一覧

- data/
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: fetch/save（差分取得、ページネーション、トークン自動リフレッシュ、レート制御）
  - ニュース収集: RSS 取得、前処理、raw_news への冪等保存（SSRF/サイズ制限対策あり）
  - データ品質チェック: 欠損、重複、スパイク、日付不整合検出
  - マーケットカレンダー管理: 営業日判定 / next/prev / 範囲取得 / カレンダー更新ジョブ
  - 監査ログ初期化: signal_events / order_requests / executions テーブル定義・初期化
  - 汎用統計ユーティリティ: zscore 正規化
- ai/
  - news_nlp.score_news: ニュース記事を LLM（gpt-4o-mini）で銘柄ごとにセンチメントを算出し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime に保存
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config.py
  - .env 自動読み込み（プロジェクトルート検出）と環境変数ラップ（settings オブジェクト）

---

## セットアップ手順

前提
- Python 3.10+ を想定（PEP 604 の型記法や from __future__ を利用）
- DuckDB、OpenAI SDK、defusedxml 等が必要

推奨手順（ローカル開発）

1. 仮想環境を作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール
   （プロジェクトに requirements.txt がない場合は下記を手動で）
   ```
   pip install duckdb openai defusedxml
   ```
   追加で必要になる場合:
   - requests（利用していないが外部ツールと併用する場合）
   - その他開発用ツール（pytest 等）

3. リポジトリルートに `.env` を配置（自動読み込み機構あり）
   - 自動読み込みの挙動:
     - プロジェクトルートの判定は src/kabusys/config._find_project_root() が .git または pyproject.toml を上位に探す
     - 読み込み順: OS 環境変数 > .env.local > .env
     - テスト等で自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - サンプルに必要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション 接続パスワード
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID: 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を外部から呼ぶ場合）
   - 任意・設定可能
     - KABUSYS_ENV: development | paper_trading | live （デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト data/monitoring.db）

4. DB用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主な呼び出し例）

以下はパッケージの主要機能を直接 Python で呼ぶ最小例です。実運用ではジョブ化・ログ管理・例外処理を追加してください。

- DuckDB 接続の作成（ファイル DB）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（AI）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジームの判定（AI）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（audit）スキーマ初期化
  ```python
  from kabusys.data.audit import init_audit_db
  # 新規 DuckDB ファイルを作り、監査スキーマを作成して接続を返す
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

注:
- score_news / score_regime は OpenAI API を呼びます。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl は内部で calendar ETL → prices ETL → financials ETL → 品質チェック を実行します。途中での個別失敗は記録され戻り値（ETLResult）に反映されます。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- OPENAI_API_KEY (LLM 呼び出し時に使用)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL (デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動読み込みを抑止

.env 例（抜粋）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
SLACK_BOT_TOKEN=xoxb-xxxx...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## ディレクトリ構成（要約）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（settings オブジェクト）
  - ai/
    - __init__.py (score_news エクスポート)
    - news_nlp.py — ニュースセンチメント（LLM）処理、score_news
    - regime_detector.py — 市場レジーム判定、score_regime
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save 実装、レート制御）
    - pipeline.py — ETL パイプライン / run_daily_etl 等
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 取得 / 前処理 / raw_news 保存
    - calendar_management.py — market_calendar 管理 / 営業日判定 / calendar_update_job
    - quality.py — データ品質チェック
    - stats.py — zscore_normalize など汎用統計
    - audit.py — 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
  - research パッケージはファクター研究・特徴量解析向けユーティリティを提供
  - その他: strategy/ execution/ monitoring 用のサブパッケージ名が __all__ に定義されています（実装は別）

---

## 運用上の注意・補足

- Look-ahead バイアス対策: 多くの関数は内部で date を引数に取り、datetime.today()/date.today() を直接参照しない設計になっています。バックテスト用途に適していますが、呼び出し側で適切に target_date を渡してください。
- LLM 呼び出し: OpenAI のレスポンスは常に期待どおりとは限らないため、応答パース失敗時はフェイルセーフとして 0.0 スコア等にフォールバックします。API トークン・料金に注意してください。
- J-Quants API: rate limit（120 req/min）を守るためモジュール内でレートリミッタが実装されています。ID トークンのリフレッシュ処理や 401 リトライをサポートします。
- DuckDB の executemany に関する互換性考慮: パッケージ内では空パラメータの executemany 呼び出し回避などの互換性対策が入っています。
- セキュリティ: news_collector は SSRF 等の脆弱性を考慮（スキーム検査、プライベート IP の拒否、gzip/bomb 対策）しています。

---

## 貢献・拡張

- 新しい ETL ソースや戦略モジュールを追加する場合は、DuckDB による冪等保存（ON CONFLICT）・品質チェックの実装方針に従ってください。
- LLM のモデル変更やプロンプト改良は ai/news_nlp.py / ai/regime_detector.py を編集してください。テストのために API 呼び出し関数をモックできる設計になっています（内部で _call_openai_api を分離）。

---

必要な情報や README に追記してほしい点（例: インストール用 requirements.txt、具体的な .env.example、運用の cron / Supervisor のサンプル等）があれば教えてください。README をその内容に合わせて拡張します。