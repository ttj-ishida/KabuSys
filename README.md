# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース NLP（OpenAI を利用したセンチメント分析）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ等のユーティリティを提供します。

---

## 主要機能（ハイライト）

- データ取得・ETL
  - J-Quants API からの株価日足、財務情報、JPX カレンダー取得（ページネーション・リトライ・レート制御対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ品質管理
  - 欠損データ、主キー重複、スパイク（急変）、日付不整合のチェックと QualityIssue レポート

- ニュース収集・NLP
  - RSS 収集（SSRF 防御、URL 正規化、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント集約（銘柄単位）

- 市場レジーム判定
  - ETF（1321）200日移動平均乖離 + マクロニュースの LLM センチメントを組合せた日次レジーム判定（bull / neutral / bear）

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ（ATR等）、バリュー（PER/ROE）計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルの初期化ユーティリティ（DuckDB）

---

## 必要条件 / 推奨環境

- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （その他）requests を直接使っていないが環境に応じて urllib 標準ライブラリで十分
- J-Quants / OpenAI / Slack 等の API キー

（プロジェクトで requirements.txt が用意されている場合はそちらを利用してください）

---

## セットアップ手順

1. 仮想環境を作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. パッケージをインストール
   - 開発中の場合（ソースツリーのルートで実行）
     ```bash
     pip install -e ".[dev]"  # setup.cfg/pyproject toml がある場合
     ```
   - 最低限の依存を手動で入れる場合
     ```bash
     pip install duckdb openai defusedxml
     ```

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（と、任意で `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効にしたいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで使用）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード
     - SLACK_BOT_TOKEN: Slack ボットトークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に引数で渡すことも可）
   - 任意のシステム設定
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   KABUSYS_ENV=development
   ```

---

## 使い方（代表的なユースケース）

以下はライブラリ内の公開関数を使った例です。DuckDB 接続はプロジェクト設定のデフォルトパス（settings.duckdb_path）を参照しますが、任意のパスでも可。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # または settings.duckdb_path
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコアを付ける（OpenAI API キーを引数で渡すことも可）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（別ファイルに監査用 DB を分離したい場合）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions 等のテーブルが作成される
  ```

- リサーチ系：モメンタムや IC を計算する
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  factors = calc_momentum(conn, date0)
  forwards = calc_forward_returns(conn, date0, horizons=[1,5,21])
  ic = calc_ic(factors, forwards, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- カレンダー関連ユーティリティ（営業日判定など）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 21)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 設定取得（環境変数）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

---

## 注意点 / 設計上の方針（抜粋）

- ルックアヘッドバイアス対策
  - 多くの関数は内部で date.today() を直接参照せず、target_date を明示的に渡す設計です。
  - データ取得や分析の際は target_date 未満のデータのみ参照するよう注意しています。

- フェイルセーフ
  - 外部 API（OpenAI / J-Quants）呼び出しに対してはリトライ・フォールバックロジックを実装し、API障害時でも例外を一部吸収して継続可能に設計されています（必要に応じてログ出力）。

- 冪等性
  - ETL の保存処理は冪等（ON CONFLICT DO UPDATE / INSERT … DO NOTHING）で行い、再実行時の安全性を確保します。
  - 監査ログの order_request_id 等は冪等キーとして扱うことを前提としています。

- セキュリティ
  - ニュース収集では SSRF 対策、XML パースには defusedxml を使用する等の対策が入っています。

---

## ディレクトリ構成（抜粋）

プロジェクトは src 配下のパッケージ構成です。主要ファイルを示します。

- src/kabusys/
  - __init__.py
  - config.py                          （環境変数 / 設定管理）
  - ai/
    - __init__.py
    - news_nlp.py                       （ニュース NLP / score_news）
    - regime_detector.py                （市場レジーム判定 / score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 （J-Quants API クライアント & DuckDB 保存）
    - pipeline.py                       （ETL パイプライン：run_daily_etl 等）
    - etl.py                            （ETLResult の再エクスポート）
    - calendar_management.py            （マーケットカレンダー管理）
    - news_collector.py                 （RSS 収集・前処理）
    - quality.py                        （データ品質チェック）
    - stats.py                          （統計ユーティリティ）
    - audit.py                          （監査ログテーブルの初期化）
  - research/
    - __init__.py
    - factor_research.py                （モメンタム / ボラティリティ / バリュー）
    - feature_exploration.py            （将来リターン, IC, 統計サマリ）
  - research、ai、data 配下のモジュールはさらに細分化されています（README 参照）

---

## 開発 / テスト

- 自動 env ロードは .env / .env.local をプロジェクトルートから検索して行います。テスト時に自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI への呼び出し部分（kabusys.ai.*）は内部で _call_openai_api のようなラッパー関数を使っており、ユニットテストではモックしやすくなっています（unittest.mock.patch で差し替え）。

---

## 参考 / 連絡

問題や改善提案がある場合はリポジトリの Issue に記載してください。README に載せきれない運用上の注意（API レート管理、トークン管理、Slack 通知フロー等）は別途運用ドキュメントを用意することを推奨します。

---
（この README はソースコードのコメントおよびモジュール設計に基づいて作成しています。実運用前に各種設定値・スキーマ・API キーの配置を必ず確認してください。）