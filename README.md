# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリセットです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP による銘柄センチメント、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）など、運用・研究に必要な機能群を含みます。

バージョン: 0.1.0

---

## 主な機能一覧

- データ収集 / ETL
  - J-Quants API クライアント（株価日足 / 財務 / 上場銘柄 / マーケットカレンダー）
  - 差分取得、ページネーション対応、トークン自動リフレッシュ、レート制御、冪等保存（DuckDB へ ON CONFLICT）
  - 日次 ETL パイプライン（run_daily_etl）

- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出（quality モジュール）

- ニュース収集・処理
  - RSS 取得（SSRF 対策、gzip 上限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存

- ニュース NLP / AI
  - gpt-4o-mini を用いた銘柄毎ニュースセンチメント付与（news_nlp.score_news）
  - マクロニュースと ETF（1321）200日移動平均乖離で市場レジーム判定（ai.regime_detector.score_regime）
  - API 呼び出しでのリトライ・バックオフ・フェイルセーフ設計

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化

- 監査・トレーサビリティ
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ（データベース：DuckDB）
  - order_request_id による冪等制御、UTC タイムスタンプ保存

- マーケットカレンダー管理
  - market_calendar の夜間更新ジョブ
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - カレンダー未取得時の曜日ベースフォールバック

設計上の留意点: ルックアヘッドバイアス回避、API の堅牢なリトライ、冪等性、DuckDB との互換性を重視。

---

## 動作要件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / RSS / OpenAI）および適切な API トークン

具体的な依存はプロジェクト側で requirements.txt を用意している場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone <repo>

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用にローカルインストール:
     ```
     pip install -e .
     ```

4. 環境変数を設定
   - プロジェクトルートの .env / .env.local を自動読み込みします（config モジュール）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須の環境変数（一例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注モジュールを使用する場合）
     - SLACK_BOT_TOKEN — Slack 通知用（該当機能を利用する場合）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）
   - 任意の設定:
     - KABUSYS_ENV (development | paper_trading | live)、LOG_LEVEL、DUCKDB_PATH、SQLITE_PATH

   - .env の簡易例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（最小限の例）

- DuckDB 接続を作る（デフォルトパスは設定から取得できます）:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（run_daily_etl）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアを生成する:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n_written)
  ```

- マーケットレジームを判定する:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- リサーチ用ファクター計算:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

注意:
- OpenAI 呼び出しには OPENAI_API_KEY を環境変数か関数引数で渡す必要があります（引数で上書き可能）。
- ETL / API 呼び出しは外部ネットワークや認証が必要なので、事前にトークン等を設定してください。

---

## 設定（config モジュールの挙動）

- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を検出して `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- Settings API:
  - kabusys.config.settings から各種値へプロパティでアクセスできます（例: settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.log_level）。

- バリデーション:
  - 必須環境変数が未設定だと _require() により ValueError が発生します（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys/ 以下）

- __init__.py
- config.py

- ai/
  - __init__.py
  - news_nlp.py        — ニュースのセンチメント付与（OpenAI）
  - regime_detector.py — マクロ + ETF による市場レジーム判定

- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント + DuckDB 保存
  - pipeline.py           — ETL パイプラインと run_daily_etl
  - etl.py                — ETL の公開型再エクスポート（ETLResult）
  - stats.py              — zscore_normalize 等の統計ユーティリティ
  - quality.py            — データ品質チェック
  - news_collector.py     — RSS 取得 / 前処理 / raw_news 保存
  - calendar_management.py— マーケットカレンダー管理と更新ジョブ
  - audit.py              — 監査ログ（テーブル作成・初期化）
  - その他 jquants_client の補助関数

- research/
  - __init__.py
  - factor_research.py     — Momentum / Volatility / Value
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

- research と data の間で共有されるユーティリティ（data.stats など）

---

## 設計上のポイント・注意事項

- ルックアヘッドバイアス防止:
  - 関数は基本的に内部で datetime.today() / date.today() を盲目的に参照しない設計。テスト・バックテストで target_date を明示して使用してください。

- 冪等性:
  - DuckDB への保存処理は ON CONFLICT で更新することで同一データの再保存を安全に扱います。

- API 耐障害性:
  - J-Quants や OpenAI への呼び出しはリトライと指数バックオフを実装。致命的な失敗時にはフェイルセーフ（例: マクロスコアを 0.0 にフォールバック）を行う箇所があります。

- セキュリティ:
  - news_collector は SSRF 対策、トラッキングパラメータ削除、XML の防御的パース（defusedxml）などを行います。

---

## 開発・貢献

- コードの拡張やバグ修正は PR を welcome です。  
- テストを追加する場合は、外部 API 呼び出しをモック（patch）してネットワークに依存しないテストを書くことを推奨します（config の自動 .env ロードはテスト時に無効化可能）。

---

必要であれば README に:
- より詳細な .env.example（ファイル）や SQL スキーマ（初期化手順）、
- 典型的な運用スケジュール（夜間 ETL ジョブ、ニュースバッチ、戦略→発注フロー）、
- サンプル Dockerfile / systemd ユニット例、
を追加します。どの情報を詳細化したいか指示してください。