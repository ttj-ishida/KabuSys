# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群。  
データ取り込み（J-Quants）、品質チェック、ニュースセンチメント（OpenAI）、市場レジーム判定、ファクター計算、監査ログなどの共通処理をまとめたモジュール群を提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境設定の自動読み込み（`.env`, `.env.local`、OS 環境変数優先）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存（ページネーション・リトライ・レート制限対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 市場カレンダー / 日次株価 / 財務データの差分取得・保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - ETL 実行結果を ETLResult として集約
- ニュース収集（RSS）＆前処理（SSRF 対策、トラッキングパラメータ除去、gzip 対応）
- ニュース NLP（OpenAI）による銘柄別センチメント算出（batch, JSON mode, 再試行ロジック）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用モジュール
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン / IC / 統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ初期化ユーティリティ
- 監視 / 設定（PID ファイルパス、リソース閾値などを環境変数で管理）

---

## 前提条件

- Python 3.10+（型注釈等に準拠）
- 必要な外部パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース 等）
- J-Quants / OpenAI の認証情報

（プロジェクトで用いる実際の requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存ライブラリをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実際のプロジェクトで requirements.txt があれば `pip install -r requirements.txt` を推奨します。

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数設定
   - プロジェクトルートに `.env`（および必要に応じ `.env.local`）を配置します。自動読み込み順序は:
     OS 環境変数 > .env.local > .env
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API パスワード
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack チャネル ID
     - OPENAI_API_KEY        : OpenAI API キー（AI モジュール利用時）
   - 任意の環境変数（デフォルトあり）
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視DB, デフォルト: data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/...)

---

## 使い方（主な API の例）

以下は最小限の利用例です。実運用ではログ設定・例外処理・リトライ・監視等を適切に組み込んでください。

- DuckDB 接続の作成（設定経由でパスを取得）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書込銘柄数: {written}")
  ```

- 市場レジーム判定（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 研究用関数の呼び出し例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.stats import zscore_normalize

  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  normalized = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

- 監査ログスキーマの初期化（監査用 DuckDB を別途作る場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn は初期化済みの DuckDB 接続
  ```

注意:
- AI モジュール（news_nlp, regime_detector）は OpenAI API を呼び出します。api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定してください。未設定の場合は ValueError が発生します。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みをオフにできます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                    — ニュースセンチメント（OpenAI）/ score_news
  - regime_detector.py             — 市場レジーム判定（MA200 + マクロセンチメント）
- data/
  - __init__.py
  - calendar_management.py         — マーケットカレンダー管理 / 営業日判定
  - etl.py                         — ETL の公開インターフェース（ETLResult）
  - pipeline.py                    — 日次 ETL パイプライン（run_daily_etl 等）
  - stats.py                       — z-score 等の統計ユーティリティ
  - quality.py                     — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py                       — 監査ログスキーマ初期化（signal/order/execution）
  - jquants_client.py              — J-Quants API クライアント（fetch/save）
  - news_collector.py              — RSS ニュース収集・前処理
- research/
  - __init__.py
  - factor_research.py             — モメンタム / バリュー / ボラティリティ等
  - feature_exploration.py         — 将来リターン / IC / 統計サマリー
- monitoring/ (※コードベースに監視関連があればここに配置)
- strategy/, execution/           — 戦略・約定周りのパッケージ（利用の想定）
- その他ユーティリティ群

（上記は主要モジュールの抜粋です。実際のツリーはリポジトリ内のファイルを参照してください）

---

## 開発・運用に関する注意点

- Look-ahead bias を避ける設計が多用されています（target_date を明示して過去データのみ参照する等）。バックテストや再現性保持のため、この動作に従ってください。
- DuckDB を用いた SQL 実行ではパラメータバインド（?）を使用しています。SQL インジェクション対策済みですが、直接文字列連結は避けてください。
- OpenAI 呼び出し部分はリトライやフェイルセーフ（失敗時 0.0 を返す等）を備えていますが、レートやコストに注意してください。
- J-Quants API の rate limit（120 req/min）に合わせた内部レート制限とリトライロジックを備えています。ID トークン自動リフレッシュも実装されています。

---

## トラブルシューティング（よくある問題）

- 環境変数未設定で起動すると ValueError が発生します（例: JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY）。`.env.example` を参考に `.env` を作成してください。
- OpenAI への API 呼び出しで 5xx やタイムアウトが発生した場合、内部でリトライしてフェイルセーフ値を返します。ログを確認してください。
- DuckDB の executemany に空リストを渡すとエラーになる環境（特定バージョン）があります。パイプライン内ではこの点に注意してガードしています。

---

必要に応じて README を拡張して、CI/CD、運用手順、Slack 通知の利用方法、サンプル .env.example、テストの実行方法などを追加できます。追加したい情報があれば指示してください。