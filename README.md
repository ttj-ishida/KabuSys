# KabuSys

日本株向け自動売買 / データ基盤ライブラリ群

概要
- KabuSys は日本株のデータ収集・品質管理・特徴量生成・AI ベースのニュースセンチメント評価・市場レジーム判定・監査ログ管理などを提供する Python モジュール群です。
- 主にバックエンドのデータプラットフォーム（DuckDB）と外部 API（J-Quants, OpenAI, RSS 等）をつなぎ、ETL・品質チェック・リサーチ・戦略開発のための再利用可能な関数を提供します。
- パッケージは src/kabusys 以下にモジュール単位で整理されています（data, ai, research, config, など）。

主な機能
- データ取得・ETL
  - J-Quants から株価日足 / 財務データ / 上場銘柄情報 / 市場カレンダーを差分取得・保存（jquants_client）
  - 日次 ETL パイプライン（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - ETL 結果を表現する ETLResult（data.pipeline）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合の検出（data.quality）
- ニュース収集・前処理
  - RSS フィード取得・SSRF 対策・トラッキングパラメータ除去・記事ID生成（data.news_collector）
- AI ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM に送りセンチメントを算出して ai_scores テーブルへ保存（ai.news_nlp）
  - マクロニュースと ETF の MA200 乖離を組み合わせて市場レジーム（bull/neutral/bear）を判定（ai.regime_detector）
- リサーチ用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility / Liquidity）（research.factor_research）
  - 将来リターン計算、IC、ファクター統計サマリ、正規化ユーティリティ（research.feature_exploration, data.stats）
- カレンダー管理
  - JPX カレンダーの更新・営業日判定・次/前営業日取得（data.calendar_management）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ（data.audit）
  - 監査 DB 初期化関数（init_audit_db / init_audit_schema）
- 設定管理
  - .env または環境変数から設定を自動読み込み（config.settings）
  - 自動読み込みの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

前提・依存
- Python 3.10+
- 必要パッケージ例（pip でインストール）:
  - duckdb
  - openai
  - defusedxml
  - その他（標準ライブラリのみで動く部分も多いですが、実行環境に応じて追加で logger/HTTP クライアント等が必要になる場合があります）

セットアップ手順

1. リポジトリをクローンしてインストール（開発モード推奨）
   ```
   git clone <repo_url>
   cd <repo>
   pip install -e ".[dev]"   # extras が用意されている場合。最低限 pip install -e . でも可
   ```

2. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。
   - 主要な環境変数（README用サンプル）:

     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

     # OpenAI
     OPENAI_API_KEY=sk-...

     # kabuステーション API
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # Slack (通知用)
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789

     # データベース / ファイル
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PID_FILE_PATH=data/execution.pid

     # システム設定
     KABUSYS_ENV=development   # development | paper_trading | live
     LOG_LEVEL=INFO
     ```

   - .env のパースはシェル風（export を許容、引用符・コメント処理あり）で行われます。

3. DuckDB / 監査 DB 初期化（例）
   - 監査ログ用 DB を初期化するには:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用のメイン DuckDB ファイルパスは settings.duckdb_path で指定できます。

使い方（代表的な利用例）

- DuckDB 接続を作成して日次 ETL を実行
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # デフォルトで今日を対象に ETL を実行
  print(result.to_dict())
  ```

- ニュースセンチメント評価（ai.news_nlp.score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # 対象日を指定
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（詳細）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # transactional=True で一括DDLを原子的に実行する内部関数も利用可能（関数引数参照）
  ```

- リサーチ系のファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  t = date(2026, 3, 20)
  momentum = calc_momentum(conn, t)
  volatility = calc_volatility(conn, t)
  value = calc_value(conn, t)
  ```

設定読み込みの挙動・注意点
- configモジュールは起動時に自動でプロジェクトルート（.git または pyproject.toml）を探し、.env → .env.local の順で読み込みます。OS環境変数は上書きされません（.env.local は上書き可能）。
- 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利です）。
- Settings クラス経由で各種設定値を取得できます（例: settings.jquants_refresh_token）。

主なモジュールとディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — 銘柄ニュースの LLM センチメント評価
    - regime_detector.py      — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 + 保存）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - news_collector.py       — RSS 収集・前処理
    - calendar_management.py  — 市場カレンダー管理
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 等
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー / rank
  - monitoring/ (存在を示すエントリは __all__ にあるが実装が分かれる可能性)
  - execution/, strategy/ 等（将来の戦略・約定実装想定）

設計方針（ポイント）
- Look-ahead bias の回避: 日付やデータ取得において将来データを参照しない設計（target_date を明示する、クエリは date < target_date のように排他にする等）。
- 冪等性: ETL 保存関数は ON CONFLICT DO UPDATE（重複防止）や INSERT...DO NOTHING を使い、再実行可能。
- フェイルセーフ: AI/API 呼び出し失敗時は安全側のデフォルト値を採る（例: macro_sentiment=0.0）し、例外で全面停止しない箇所が多い。
- セキュリティ: RSS 取得時の SSRF 対策、defusedxml を使った XML パース等の安全対策を実装。

トラブルシューティング / 注意事項
- OpenAI / J-Quants の API キー・トークンは必須です。未設定の場合、関連関数は ValueError を投げます。
- DuckDB の executemany はバージョン差異で空パラメータの扱いが異なるため、空リストの executemany を避ける実装になっています。
- news_collector では外部接続制御やファイルサイズ制限を行っているため、極端に大きい RSS フィードはスキップされます。
- audit.init_audit_schema は transactional フラグに注意（呼び出し元トランザクション状態に依存する）。

ライセンス・コントリビューション
- 本リポジトリの実際のライセンス情報やコントリビュート手順はリポジトリのトップレベル（LICENSE / CONTRIBUTING）を参照してください。

最小限の開発フロー例
1. .env を作成して必要なキーを設定
2. duckdb を作成して監査スキーマを初期化（必要に応じて）
3. run_daily_etl を定期実行（cron / CI / Airflow 等）してデータ基盤を整備
4. research モジュールでファクターを計算し戦略検証を行う
5. strategy → execution 層を実装して監査ログを保存しつつ実運用へ展開

問い合わせ
- 実装の詳細や使い方、追加モジュールの要望があればプロジェクトの issue に投稿してください。

以上。必要があれば README に含めるサンプル .env.example ファイルやより詳細な API 使用例（関数ごとのパラメータ説明）を追加で作成します。どの部分を詳しく載せたいか教えてください。