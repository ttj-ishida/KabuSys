# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
市場データの ETL、ニュースの収集・NLP スコアリング、ファクター計算、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

主な用途例:
- J-Quants からの株価・財務・カレンダーの差分 ETL
- RSS ニュース収集と OpenAI による銘柄／マクロのセンチメント評価
- ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログテーブルの初期化（発注／約定トレース）
- データ品質チェックとマーケットカレンダー管理

---

## 機能一覧

- config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）と型チェック（settings）
  - 必須環境変数の取得ラッパー

- data
  - jquants_client: J-Quants API クライアント（認証、ページネーション、レート制限、保存関数）
  - pipeline: 日次 ETL パイプライン（prices / financials / calendar の差分取得・保存・品質チェック）
  - news_collector: RSS フィード収集（SSRF 対策、正規化、冪等保存）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats: 汎用統計ユーティリティ（Zスコア正規化など）
  - audit: 監査ログスキーマ定義と初期化ユーティリティ（signal_events, order_requests, executions）

- ai
  - news_nlp.score_news: ニュースを銘柄毎に集約して OpenAI でスコアリングし ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースセンチメントを合成して市場レジームを判定・保存

- research
  - factor_research: モメンタム、バリュー、ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC（情報係数）、統計サマリーなど

---

## 動作環境（推奨）

- Python 3.10 以上（typing の表記に依存）
- 必要なライブラリ（最低限の例）
  - duckdb
  - openai
  - defusedxml

※ パッケージの実際の依存関係はプロジェクト要件に合わせて requirements.txt / pyproject.toml を確認してください。

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .    # または pip install -r requirements.txt
   ```

2. Python パッケージ依存のインストール（必要に応じて）
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置すると自動的に読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（実行に必要な代表的なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必要な機能がある場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector 実行時に必要）

   オプション:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

4. データベース初期化（監査テーブルなど）
   - 監査ログ専用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     from kabusys.config import settings

     conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
     ```
   - 既存接続へ監査スキーマのみ適用する:
     ```python
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（代表的な例）

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(settings.duckdb_path.as_posix())
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアを計算して ai_scores テーブルへ書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(settings.duckdb_path.as_posix())
  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")
  ```

- 市場レジーム（bull/neutral/bear）スコアリング
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(settings.duckdb_path.as_posix())
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  from kabusys.config import settings

  conn = duckdb.connect(settings.duckdb_path.as_posix())
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), records[:3])
  ```

- データ品質チェックだけを実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.quality import run_all_checks

  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

---

## 主要ディレクトリ構成

（パッケージルート: src/kabusys/ 以下）

- __init__.py
  - パッケージメタ情報（__version__）と公開モジュール一覧

- config.py
  - 環境変数読み込み・Settings クラス（必須変数チェック、.env 自動ロード）

- ai/
  - news_nlp.py: ニュース集約と OpenAI による銘柄センチメント算出（score_news）
  - regime_detector.py: ETF MA とマクロニュースを合成して市場レジーム判定（score_regime）

- data/
  - pipeline.py: 日次 ETL パイプライン（run_daily_etl 等）
  - jquants_client.py: J-Quants API クライアント（fetch_* / save_*）
  - news_collector.py: RSS 収集・前処理・冪等保存
  - calendar_management.py: 市場カレンダー取得・営業日判定
  - quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py: 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py: 監査ログテーブル定義・初期化（signal_events, order_requests, executions）
  - etl.py: ETLResult の再エクスポート（API 互換性）

- research/
  - factor_research.py: モメンタム・バリュー・ボラティリティ等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー等
  - __init__.py: 研究系ユーティリティの公開

---

## 設計上の注意点・運用上のポイント

- Look-ahead bias に注意
  - 多くの処理は内部で datetime.today()/date.today() を直接参照しないよう設計されています（呼び出し側で target_date を指定すること）。
- OpenAI 呼び出し
  - ai モジュールは OpenAI の JSON mode（厳密な JSON 出力）を前提にしています。API の安定性のためリトライやフェイルセーフ（失敗時はスコア 0 を用いる等）が入っています。
- J-Quants API
  - rate limit（120 req/min）に従うレートリミッタと、401 時の自動トークンリフレッシュ、リトライロジックが実装されています。
- DuckDB との互換性
  - 一部の executemany/リストバインドに関して DuckDB のバージョン差分を考慮した実装（空リストの扱いなど）があります。
- セキュリティ
  - news_collector は SSRF 対策、XML パース保護（defusedxml）、受信サイズ制限などを実装しています。
- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みします。テスト時等に無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## トラブルシューティング（よくある質問）

- .env が読み込まれない
  - プロジェクトルートの検出に失敗している可能性があります（.git または pyproject.toml が存在するディレクトリを起点に探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認してください。手動で export するか、環境変数を直接設定してください。

- OpenAI API のエラーで処理が止まる
  - ai モジュールは多くのエラーケースでフォールバック（スコア 0）して継続する設計ですが、API キー未設定の場合は ValueError が投げられます。OPENAI_API_KEY の設定を確認してください。

- DuckDB に書き込みが失敗する
  - スキーマが存在しない場合や型不整合の可能性があります。まずは audit.init_audit_db や必要なスキーマ初期化手順を実行してください。

---

この README はコードベースの主要機能と利用開始手順の要点をまとめています。実運用時は各モジュールの docstring（関数やメソッドの説明）を参照し、環境変数・DB スキーマの準備や API キー管理を適切に行ってください。必要であれば、各モジュールの追加説明や運用ガイド（デプロイ・監視・バックテスト用の使い方）を作成します。