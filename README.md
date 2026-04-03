# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants / DuckDB を利用したデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注・約定のトレース）などを備えたモジュール群を提供します。

主な設計方針は「バックテストでのルックアヘッドバイアス防止」「DuckDB を用いた冪等な永続化」「外部 API 呼び出しに対する堅牢なリトライ/フォールバック」です。

---

## 機能一覧

- データ ETL（J-Quants からの株価・財務・マーケットカレンダー取得）
  - 差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策、URL 正規化）
- ニュースの NLP スコアリング（OpenAI gpt-4o-mini を用いた銘柄別センチメント）
  - batch 処理、リトライ、レスポンス検証、スコアのクリップ
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）
- 研究用モジュール（ファクター計算、将来リターン計算、IC 計算、Z スコア正規化）
- マーケットカレンダー管理（営業日判定、next/prev trading day、夜間バッチ更新）
- 監査ログ（signal_events / order_requests / executions）テーブルの初期化ユーティリティ
- 設定管理（.env 自動読み込み、環境変数経由の設定取得）

---

## 前提 / 動作環境

- Python 3.10+（型注釈に `X | None` 形式を使用しているため）
- 推奨パッケージ（主にコード中で使用されているもの）
  - duckdb
  - openai
  - defusedxml

（任意で）仮想環境の作成を推奨します。

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール
   - requirements ファイルが無ければ最低限以下を入れてください：
   ```
   pip install duckdb openai defusedxml
   ```
   - 開発用にパッケージとしてインストールする場合：
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（動作中のカレントワークディレクトリに依存せず、ソース位置からプロジェクトルートを検出します）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。
   - 例: `.env` に最低限設定するべきキー（用途に応じて設定してください）
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # OpenAI
     OPENAI_API_KEY=your_openai_api_key

     # kabuステーション API（発注用）
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # LINE 通知（任意）
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=

     # DB パス等（任意）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 環境 / ログ
     KABUSYS_ENV=development       # development | paper_trading | live
     LOG_LEVEL=INFO
     ```
   - 必須の設定値はモジュールの property で `_require` されます（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` は未設定時に ValueError）。

---

## 使い方（主要なユースケース例）

以下はライブラリをインポートして主要処理を実行する最小例です。実行前に必要な環境変数が設定され、DuckDB の接続先（settings.duckdb_path）が適切であることを確認してください。

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL パイプライン実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアリング（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20), api_key="your_openai_api_key")
  print("written:", written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key="your_openai_api_key")
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査用テーブルへアクセス可能
  ```

- マーケットカレンダー更新ジョブ（差分フェッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from datetime import date

  saved = calendar_update_job(conn, lookahead_days=90)
  print("saved:", saved)
  ```

注意点:
- OpenAI 呼び出しや J-Quants API 呼び出しは外部ネットワークを使用します。API キーやトークンの管理に注意してください。
- score_news / score_regime の API キーは引数で注入できます（テストやキー切替に便利）。
- 各関数はルックアヘッドバイアスを避ける設計（target_date を明示）になっています。バッチ実行時は target_date を適切に指定してください。

---

## 設定と環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（発注処理用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視等）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

設定はモジュール `kabusys.config.settings` から参照できます。

---

## ディレクトリ構成（コードベースの抜粋）

主要なモジュール／パッケージ構成の概観です（src/ 以下）。

src/kabusys/
- __init__.py
- config.py                           # 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                        # ニュース NLP スコアリング
  - regime_detector.py                 # 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                  # J-Quants API クライアント + 保存関数
  - pipeline.py                        # ETL パイプライン（run_daily_etl 等）
  - etl.py                             # ETL 結果型再エクスポート
  - news_collector.py                  # RSS ニュース収集
  - calendar_management.py             # マーケットカレンダー管理
  - quality.py                          # データ品質チェック
  - stats.py                            # 共通統計ユーティリティ (zscore_normalize)
  - audit.py                            # 監査ログテーブル初期化
- research/
  - __init__.py
  - factor_research.py                 # ファクター計算（momentum/value/volatility）
  - feature_exploration.py             # 将来リターン, IC, 統計サマリー
- research/*（その他モジュール）

上記は主要ファイルの一覧です。詳細は各モジュールの docstring を参照してください。

---

## テスト・開発時のヒント

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在する階層）から行われます。テストで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部はモックしやすいように内部呼び出しをラップしています（ユニットテストでは patch による差し替えが可能）。
- DuckDB の executemany に関するバージョン差異（空リストを渡せない等）を考慮した実装になっています。テスト時はインメモリ `":memory:"` を使うことが可能です。
- ニュース収集では defusedxml を使用しています。RSS の XML を直接扱うため、安全性に配慮してありますが、外部リソースを扱う点に注意してください。

---

## 追加情報 / 貢献

バグ報告や機能改善の提案は Issue にお願いします。プルリクは歓迎します。コード内の docstring に設計方針や注意点が詳しく記載されていますので、実装や挙動を追う際は各モジュールの冒頭コメントを参照してください。

---

以上が KabuSys の概要と基本的な使い方です。必要であれば README に含めるコマンド例や .env.example の完全サンプル、よくあるトラブルシュート等の追記も対応します。どの項目を拡張しますか？