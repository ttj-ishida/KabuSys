# KabuSys — 日本株自動売買プラットフォーム（README）

概要
---
KabuSys は日本株のデータプラットフォーム、研究（リサーチ）、AI ベースのニュースセンチメント解析、監査ログ、ETL、そして売買戦略実行に必要なユーティリティ群を提供する Python パッケージです。本リポジトリの実装は DuckDB を主要な分析 DB とし、J-Quants API / RSS / OpenAI 等と連携してデータ収集・品質チェック・特徴量作成・レジーム判定・監査（発注→約定トレース）を行います。

主な機能
---
- データ収集（J-Quants 経由）
  - 株価日足（OHLCV）、財務データ、上場銘柄一覧、JPX カレンダー
  - 保存は冪等（ON CONFLICT / UPDTE）で実行
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックの統合
  - ETL 実行結果を ETLResult として返却
- ニュース収集 / 前処理
  - RSS フィード安全取得（SSRF 防止、gzip 上限、XML 脆弱性対策）
  - URL 正規化 → SHA256 による記事 ID 生成 → raw_news 保存
- ニュース NLP（OpenAI）
  - 銘柄別ニュース集約 → LLM（gpt-4o-mini）に JSON 返却を要求 → ai_scores へ保存
  - バッチ、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定（AI + MA200）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily market_regime を算出
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター算出
  - 将来リターン計算、IC（Spearman）計算、ファクター統計
  - Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査スキーマの初期化・管理
  - 発注→約定までのトレーサビリティ確保

前提・要件
---
- Python 3.10+
- 依存ライブラリ（代表例）
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
  - （標準ライブラリ以外の依存は setup.py / pyproject.toml を参照してください）

セットアップ手順
---
1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. パッケージをインストール（開発モード推奨）

   ```bash
   pip install -e ".[dev]"   # pyproject/セットアップで extras を定義している場合
   ```

   主要依存を個別に入れるなら:
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (実行時に直接渡すことも可能)
   - オプション:
     - KABUSYS_ENV = development | paper_trading | live
     - LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL
     - KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 (自動 .env ロード無効化)
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

使い方（代表的な API / 実行例）
---

- DuckDB 接続を用意する

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（run_daily_etl）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースセンチメントスコア（score_news）

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"scored: {count} symbols")
  ```

- 市場レジーム判定（score_regime）

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査 DB 初期化（監査用専用 DB）

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され監査スキーマが使えるようになります
  ```

- 市場カレンダー操作例

  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026,3,20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点 / 実装上のポイント
---
- .env 自動ロード:
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を自動ロードします。
  - テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して無効化できます。
- OpenAI 呼び出し:
  - news_nlp と regime_detector は gpt-4o-mini を JSON mode で呼び出す設計です。API の失敗はフェイルセーフでスコア 0.0 を採用する等の処理を行いますが、API キー未設定時は ValueError を発生させます。
- DuckDB バージョン互換性:
  - 一部実装で executemany に空リストを渡すと例外となる制約に対処しています（空チェックあり）。
- Look-ahead バイアス防止:
  - 多くの処理（ニュースウィンドウ、MA 計算、ETL の target_date 取り扱い等）で現在時刻を参照せず、明示的な target_date を受け取りルックアヘッドを防いでいます。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py — パッケージ定義（version, submodules）
- config.py — 環境変数 / .env 自動ロード・Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント解析 & OpenAI 呼び出しロジック
  - regime_detector.py — MA200 + マクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — ETL 実行（run_daily_etl など）と ETLResult
  - etl.py — ETLResult 再エクスポート
  - calendar_management.py — 市場カレンダーの判定・更新ジョブ
  - news_collector.py — RSS フィード収集 & 前処理
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログスキーマ初期化・監査 DB ヘルパー
- research/
  - __init__.py
  - factor_research.py — momentum/value/volatility の計算
  - feature_exploration.py — forward return / IC / summary / rank 等
- ai, research, data の各モジュールは、バックテストや運用から直接呼べるユーティリティ群を提供します。

開発・運用時のヒント
---
- ローカルテスト時は OPENAI_API_KEY のモック化（unittest.mock.patch）や KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境を分離してください。
- J-Quants API はレート制限があるため、開発時の連続実行は注意してください。jquants_client は内部で固定間隔スロットリングを実装しています。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に配置されます。複数プロセスから同時に書き込むケースは注意してください（バックアップや排他設計を検討）。

ライセンス／貢献
---
- ソースのライセンスやコントリビューション方針はリポジトリルートの LICENSE / CONTRIBUTING を参照してください。

フィードバック・問題報告
---
バグ報告や機能要望は Issue に登録してください。利用時に API キーや実データを扱う部分はセキュリティに注意して下さい。

以上が KabuSys の概要・セットアップ・代表的な使い方・ディレクトリ構成の説明です。必要であれば、各モジュールの関数リファレンスやサンプルワークフロー（ETL → ニュース解析 → レジーム判定 → 監査ログの保存）を追加で作成します。