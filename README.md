# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ（オーディット）、市場カレンダー管理、J-Quants / kabu ステーション連携など、取引・リサーチ・運用に必要なユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダーの差分 ETL（DuckDB 保存・品質チェック付き）
- RSS ニュース収集と LLM を使ったニュースセンチメント評価（銘柄別 ai_scores 書き込み）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- 監査ログ（signal → order_request → executions）を DuckDB へ冪等的に初期化・管理
- kabu ステーションや外部 API へ接続するための設定管理

設計上の方針として、バックテスト等でのルックアヘッドバイアス防止、API 呼び出しの堅牢化（リトライ・バックオフ）、DuckDB を利用した冪等保存・トランザクション管理に重きを置いています。

---

## 主な機能一覧

- 環境変数 / .env 管理（自動ロード機能）
- J-Quants クライアント（取得・保存・認証・レート制御）
- ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS → raw_news、SSRF 対策・サイズ制限・トラッキング除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメント score_news）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコア合成 score_regime）
- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- 研究ユーティリティ（ファクタ算出・正規化・IC・統計サマリ）

---

## 要求環境 / 依存

- Python 3.10+
- 必須（例）パッケージ:
  - duckdb
  - openai
  - defusedxml

（実際の `pyproject.toml` / requirements はプロジェクト側で管理してください）

---

## 環境変数（主なもの）

パッケージは .env/.env.local または OS 環境変数を参照します。自動ロードはパッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）から行います。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主なキー（大文字）:

- JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン（必須 for API）
- KABU_API_PASSWORD … kabu ステーション API パスワード
- KABU_API_BASE_URL … kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY … OpenAI 呼び出しに使用（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID … 通知用（任意）
- DUCKDB_PATH … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH … 監視・モニタリング用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START … 実行監視関連
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT … 監視閾値
- KABUSYS_ENV … 開発環境: development / paper_trading / live
- LOG_LEVEL … ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env.example を参考に .env ファイルを作成してください。`Settings` クラスは未設定の必須値で ValueError を送出します。

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし、プロジェクトルートへ移動

2. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数を準備
   - プロジェクトルートに `.env` を作成し、必要なキーを設定します（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）
   - 自動ロードはパッケージ import 時に行われます（.env → .env.local の順で上書き）

5. DuckDB の初期化（監査 DB を使う場合）
   - 監査用スキーマを初期化する例（ファイルベース DB 使用）:
     ```python
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db(settings.duckdb_path)
     ```
   - 上記では settings.duckdb_path のディレクトリが自動で作成されます。

---

## 使い方（主な例）

以下はライブラリの代表的な利用例（Python スクリプト内で呼び出す想定）です。

- DuckDB 接続準備:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（LLM 使用）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key を明示的に渡すことも可能（None の場合は環境変数 OPENAI_API_KEY を参照）
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"scored {written} codes")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査スキーマ初期化（個別）:
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn, transactional=True)
  ```

- 監査 DB の専用初期化（ファイル作成含む）:
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  audit_conn = init_audit_db(settings.duckdb_path)
  ```

注意点:
- news_nlp / regime_detector は OpenAI API を呼び出します。API キー（OPENAI_API_KEY）を環境変数で設定するか、関数に api_key を渡してください。
- J-Quants API 呼び出しにはレート制限（120 req/min）やトークンリフレッシュロジックがあります。JQUANTS_REFRESH_TOKEN を設定してください。
- DuckDB への書き込みは冪等性（ON CONFLICT DO UPDATE）を考慮して実装されています。

---

## ディレクトリ構成（主要ファイルと説明）

(パッケージルート: src/kabusys)

- __init__.py
  - パッケージ初期化。公開サブパッケージ: data, strategy, execution, monitoring
- config.py
  - 環境変数の自動ロード、Settings クラス（各種設定取得）
- ai/
  - news_nlp.py : ニュースの LLM ベーススコアリング（score_news）
  - regime_detector.py : 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得 / 保存 / 認証 / レート制御）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）
  - etl.py : ETL インターフェース（ETLResult 再エクスポート）
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector.py : RSS 収集・前処理・保存ロジック（SSRF 対策含む）
  - calendar_management.py : JPX カレンダー管理、営業日判定・バッチ更新
  - stats.py : 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py : 監査ログ（signal / order_request / executions）スキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py : モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py : 将来リターン、IC、統計サマリー、ランキング等
- ai/__init__.py, research/__init__.py 等で主要関数を公開

（上記はコードベース抜粋に基づく主要ファイル一覧です）

---

## 運用上の注意 / ベストプラクティス

- ルックアヘッドバイアス回避:
  - 多くのモジュールは内部で date.today() を直接参照せず、呼び出し側から target_date を与える設計です。バックテストや re-run の際は target_date を明示してください。
- OpenAI 呼び出し:
  - レスポンスのパースや API エラー時のフォールバック（0.0）などが組み込まれていますが、コストとレートを考慮して運用してください。
- J-Quants:
  - API レート上限（120 req/min）を厳守するための RateLimiter が実装されています。大量取得は分割して実行してください。
- .env 自動ロード:
  - パッケージインポート時に自動で .env をプロジェクトルートから読み込みます。テスト等でこれを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB executemany の空リスト問題:
  - 一部実装では DuckDB 0.10 系で executemany に空リストを渡すと失敗することを考慮して、空チェックを行っています。DuckDB バージョンの互換性には注意してください。

---

## 例: .env の最小例

```
JQUANTS_REFRESH_TOKEN=xxxxxxx
OPENAI_API_KEY=sk-xxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## サポート / コントリビュート

- バグレポートや機能提案は issue を立ててください。
- コントリビュートする場合は、機能ごとにユニットテストを追加し、既存の設計方針（ルックアヘッド回避・冪等性・ログ）に従ってください。

---

以上がこのコードベースの README.md です。必要であれば、README に含めるコマンド例（Unit test, lint, packaging）や .env.example の詳細テンプレート、API 利用料金や注意点なども追記できます。どの追加情報が欲しいか教えてください。