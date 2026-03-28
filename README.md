# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ構築、ファクター計算など、アルゴリズム取引・リサーチに必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション・リトライ・レート制御対応）
  - 差分更新・バックフィル・品質チェック付きの日次 ETL パイプライン（run_daily_etl）
- ニュース収集 / NLP
  - RSS 取得・前処理・raw_news への冪等保存（SSRF 対策、トラッキング除去、サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄単位センチメントスコア生成（score_news）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（score_regime）
- リサーチ支援
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマの初期化（init_audit_schema / init_audit_db）
- 共通ユーティリティ
  - 環境設定管理（.env 自動読み込み・強制無効化対応）
  - 汎用統計ユーティリティ（zscore_normalize など）

設計上の注意点：
- ルックアヘッドバイアスを避けるため、日付計算で date.today() の直接参照を避ける設計が多く採られています（関数に target_date を渡す形）。
- 外部 API 呼び出しは冪等化・リトライ・フェイルセーフを意識した実装です。

---

## 必要条件（依存ライブラリ）

主な依存パッケージ（抜粋）:
- Python 3.9+
- duckdb
- openai（OpenAI の公式 SDK）
- defusedxml
- その他: 標準ライブラリ（urllib 等）を利用

プロジェクトで使う具体的な依存関係は環境に合わせて requirements.txt や pyproject.toml を用意してインストールしてください。

例（最低限インストールする場合）:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   - プロジェクトルートには `.git` または `pyproject.toml` があると .env の自動読み込みが有効になります。

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml と同じ階層）に `.env` / `.env.local` を置くと自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API パスワード（利用する場合）
     - SLACK_BOT_TOKEN : Slack 通知を使う場合
     - SLACK_CHANNEL_ID : Slack チャンネル ID（通知先）
     - OPENAI_API_KEY : OpenAI API を使う処理（news/regime）で必要（関数呼び出し時に直接渡すことも可能）

   - データベースパスのデフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db

   例 .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   ```

5. DuckDB 用ディレクトリを作成
   - デフォルトパス（data/kabusys.duckdb）を使う場合は data/ を作成しておくと良いです:
     mkdir -p data

6. （オプション）Kabuステーションや Slack と連携する場合はそれぞれの設定を行ってください。

---

## 使い方（代表的な API）

以下は簡単な利用例です。各関数は duckdb 接続（duckdb.connect(...)）や target_date を受け取ります。

- DuckDB 接続の作成例:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- ETL（日次パイプライン）を実行:
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - res = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(res.to_dict())

- ニュースのスコアリング（OpenAI を利用）:
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None の場合 OPENAI_API_KEY env を使用

- 市場レジームスコアの計算:
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - r = score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査データベースの初期化（監査用 DuckDB を新規作成）:
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- ファクター計算（例: モメンタム）
  - from kabusys.research.factor_research import calc_momentum
  - from datetime import date
  - factors = calc_momentum(conn, target_date=date(2026,3,20))

備考:
- OpenAI を使用する関数は api_key を引数で渡すこともできます。渡さない場合は環境変数 OPENAI_API_KEY を参照します。
- 多くの処理は「target_date」を受け取り、内部で look-ahead バイアスにならないよう設計されています（date.today() を勝手に参照しない）。

---

## 設定（環境変数一覧と説明）

重要な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants API 用リフレッシュトークン。get_id_token で使用。

- OPENAI_API_KEY  
  OpenAI API キー。news_nlp / regime_detector にて使用。

- KABU_API_PASSWORD  
  kabuステーション API を使う場合のパスワード。

- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID  
  Slack 通知を行う場合に必要。

- DUCKDB_PATH (省略可)  
  デフォルト: data/kabusys.duckdb

- SQLITE_PATH (省略可)  
  デフォルト: data/monitoring.db

- KABUSYS_ENV (省略可)  
  設定可能値: development / paper_trading / live（デフォルト development）

- LOG_LEVEL (省略可)  
  DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

- KABUSYS_DISABLE_AUTO_ENV_LOAD  
  真理値（1）で .env 自動ロードを無効化（テスト用途など）

.env の自動読み込み:
- プロジェクトルート（__file__ の親ディレクトリで .git または pyproject.toml が見つかった場所）に `.env` / `.env.local` がある場合、自動で読み込まれます。`.env.local` は `.env` より優先され上書きされます（ただし OS 環境変数は保護されます）。

---

## ディレクトリ構成（主要ファイル説明）

src/kabusys/
- __init__.py — パッケージ初期化
- config.py — 環境変数 / 設定管理（.env 自動読み込み含む）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（銘柄単位）: score_news, calc_news_window 等
  - regime_detector.py — 市場レジーム判定: score_regime
- data/
  - __init__.py
  - pipeline.py — ETL パイプライン / run_daily_etl / run_*_etl
  - jquants_client.py — J-Quants API クライアント（取得 / 保存関数群）
  - news_collector.py — RSS 取得と raw_news 保存
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - stats.py — zscore_normalize 等
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit.py — 監査スキーマ初期化（signal_events / order_requests / executions）
  - etl.py — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
- ai/、data/、research/ 以下にそれぞれの主要機能の実装が入っています。

---

## 開発 / テストに関するメモ

- 多くの外部 API 呼び出し（OpenAI / J-Quants / RSS）部分はモック化しやすい設計（内部呼び出しを差し替え可能）になっています。単体テストではネットワーク呼び出し部分を patch / mock して検証してください。
- DuckDB を使うため、ローカルで動作確認する際はデータベースファイル（:memory: も可）を活用できます。
- ログは標準の logging を使用しています。LOG_LEVEL を環境変数で調整してください。

---

## 注意事項 / ライセンス等

- 本コードベースは API キーや外部サービスに依存します。実運用時は API レートや約款、個別サービスの利用規約を遵守してください。
- 実注文（ライブ環境）を行う場合は、paper_trading → live の移行やリスク管理ロジックを慎重に検証してください（KABUSYS_ENV による動作モードの区別を設けています）。
- ライセンス情報はこのリポジトリに含まれる LICENSE を参照してください（ここには含まれていません）。

---

README に記載の使用例で不明点や、特定のモジュール（例: news_collector の RSS ソース追加、ETL のスケジューリング、kabuステーション発注モジュールの接続方法）の追加説明が必要であれば教えてください。必要に応じてサンプルスクリプトや .env.example を作成します。