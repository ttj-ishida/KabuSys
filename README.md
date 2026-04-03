# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）の README。  
このリポジトリはデータ収集（ETL）、品質チェック、特徴量計算、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログなど、自動売買システムの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とする Python パッケージです。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- ニュース収集（RSS）とニュースに対する LLM（OpenAI）によるセンチメントスコア算出
- ファクター（モメンタム／バリュー／ボラティリティ等）計算および研究用ユーティリティ
- 市場レジーム（bull/neutral/bear）判定（ETF とマクロニュースの組合せ）
- 監査ログ（signal → order_request → execution）用スキーマ初期化とユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴：
- DuckDB を主要なデータ格納に使用（軽量・分析向け）
- Look-ahead バイアス対策（日時の明示・ETL/スコアリングでの未来参照禁止）
- 冪等性を考慮した保存（ON CONFLICT / DELETE→INSERT など）
- OpenAI（gpt-4o-mini）を使った JSON 出力モードでのバッチスコアリング
- RSS 収集では SSRF 対策・受信サイズ制限・XML パース安全化を実装

---

## 主な機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート判定）
  - 必須キー未設定時の明確なエラー
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants から差分取得（ページネーション・レートリミット・トークン自動更新）
  - raw_prices / raw_financials / market_calendar などへの保存（冪等）
  - run_daily_etl による日次パイプライン
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・記事ID生成・raw_news 保存
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごと記事をまとめて LLM へ投げ、ai_scores にスコアを書き込む
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の MA200 乖離 + マクロニュースセンチメントを合成して market_regime に記録
- リサーチ用ユーティリティ（kabusys.research）
  - モメンタム・ボラティリティ・バリュー計算
  - 将来リターン・IC（スピアマン）・統計サマリーなど
- 監査ログスキーマ初期化（kabusys.data.audit）
  - signal_events / order_requests / executions 等の DDL とインデックス定義
  - init_audit_db / init_audit_schema を提供

---

## 必要条件（想定）

- Python 3.10+
- 推奨ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクト環境に応じて追加パッケージが必要になることがあります。requirements.txt を用意する場合は上記を含めてください）

---

## 環境変数（主なもの）

以下はコード内で参照される主要な環境変数です。`.env`（または`.env.local`）に設定してください。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知等に利用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視用、デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

注意：
- パース時はクォート・コメント処理に対応しています。
- `.env.local` の方が優先され、OS 環境変数は常に保護されます。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   例: pip install
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数を設定（`.env` をプロジェクトルートに置く）
   - 先述の必須キーを `.env` に記述

5. DuckDB データベース初期化（監査ログなど）
   Python REPL またはスクリプト:
   ```python
   import duckdb
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   # ファイルパスは settings.duckdb_path（デフォルト data/kabusys.duckdb）
   conn = init_audit_db(settings.duckdb_path)
   # または既存の conn を使って init_audit_schema(conn)
   ```

---

## 使い方（代表的な例）

以下はライブラリの主要機能を呼び出すサンプルです。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY）を設定してください。

- DuckDB 接続取得
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（ai_scores へ書き込み）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数で設定しておくか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を専用に初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  momentum = calc_momentum(conn, date(2026, 3, 20))
  print(len(momentum), momentum[:3])
  ```

テスト時の補助：
- OpenAI API 呼び出しは内部で分離されており、ユニットテストでは `_call_openai_api` をモックしてレスポンスを制御できます（kabusys.ai.news_nlp._call_openai_api 等）。

---

## 主要モジュールとディレクトリ構成

（src 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP スコアリング（LLM 呼び出し・バッチ処理）
    - regime_detector.py         — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETL 型等の再エクスポート（ETLResult）
    - audit.py                   — 監査ログスキーマ初期化（DDL / init_audit_db）
    - news_collector.py          — RSS 収集（SSRF 対策・XML 安全化）
    - calendar_management.py     — マーケットカレンダー管理・営業日判定
    - quality.py                 — データ品質チェック（欠損／スパイク／重複／日付不整合）
    - stats.py                   — 統計ユーティリティ（Z-score など）
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/value/volatility）
    - feature_exploration.py     — 将来リターン・IC・統計サマリー
  - monitoring/                   — （実装例: プロセス監視や PID 管理等が想定される）
  - execution/                    — （約定・発注関連のユーティリティが入る想定）
  - strategy/                     — （戦略生成・シグナル生成の層）

（ファイル一覧は主要ファイルを抜粋しています。詳細はソースツリーを参照してください）

---

## 注意事項 / 運用上のヒント

- OpenAI を利用する機能（news_nlp / regime_detector）は API 呼び出し回数・コストが発生します。バッチサイズ・再試行設定はモジュール定数で調整可能です（例: _BATCH_SIZE, _MAX_RETRIES）。
- J-Quants API はレート制限があるため jquants_client の RateLimiter を尊重してください。長時間の連続取得は制限に注意。
- ETL とスコアリング関数はいずれも「内部で現在日時を参照しない」設計ポリシーが徹底されています。バックテストなどで Look-ahead バイアスを避けるため、target_date を明示して呼び出してください。
- テストでは外部 API 呼び出しをモックすることが容易になるよう、内部の HTTP / OpenAI 呼び出しを差し替える設計になっています（モジュール内の helper を patch する）。

---

## 開発・貢献

- コードの追加や修正は機能単位で分割し、ユニットテストを付けてください。外部 API 呼び出しはモックしてテストを書くこと。
- ドキュメントや型注釈が豊富に入っているので、実装に沿って追加の説明を README や docstring に追記してください。

---

必要であれば、README に以下を追加で記載できます：
- requirements.txt の具体例
- CI / テスト実行手順（pytest の実行例）
- 運用 playbook（ETL 定期実行、監視、ログの取り方）
どれを追加するか教えてください。