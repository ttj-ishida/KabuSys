# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP、ファクター計算、監査ログ、カレンダー管理、外部APIクライアントなどを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス（バックテストで未来情報を参照すること）の回避を重視
- DuckDB をデータプラットフォームとして利用（冪等保存、トランザクション）
- API 呼び出しに対するレート制御・リトライ・フェイルセーフ処理
- 監査痕跡（signal → order → execution のトレーサビリティ）を保持

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務、上場銘柄、JPXカレンダー）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集 / NLP
  - RSS からのニュース収集（安全対策: SSRF/圧縮/サイズ制限など）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_scores 書込）
  - マクロニュースとETF MA乖離を合成した市場レジーム判定（bull/neutral/bear）
- リサーチ / ファクター
  - モメンタム / バリュー / ボラティリティ 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Zスコア正規化ユーティリティ
- 市場カレンダー管理
  - market_calendar テーブルの更新・営業日判定（next_trading_day 等）
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義・初期化関数
  - すべて UTC タイムスタンプ、冪等性を考慮した設計

---

## 必要条件（推奨）

- Python 3.10+
- 推奨パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- (標準ライブラリで実装されている箇所も多く、依存は最小限)

インストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージがパッケージ化されている場合:
# pip install -e .
```

依存関係はプロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

---

## 環境変数 / 設定

kabusys は .env ファイル（プロジェクトルートの .git または pyproject.toml を基準に自動読み込み）または環境変数を参照します。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に利用される環境変数（必須は README 内で明示）:

- J-Quants 関連
  - JQUANTS_REFRESH_TOKEN (必須) - J-Quants リフレッシュトークン
- kabu ステーション API
  - KABU_API_PASSWORD (必須) - kabu API パスワード
  - KABU_API_BASE_URL (任意) - デフォルト: http://localhost:18080/kabusapi
- Slack（通知等）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース
  - DUCKDB_PATH (任意) - デフォルト: data/kabusys.duckdb
  - SQLITE_PATH (任意) - デフォルト: data/monitoring.db
- システム
  - KABUSYS_ENV (任意) - 値: development | paper_trading | live （デフォルト development）
  - LOG_LEVEL (任意) - DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- OpenAI
  - OPENAI_API_KEY - OpenAI 呼び出しに使用（各関数に api_key を渡すことも可能）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースはシェル風の記法（export KEY=val、コメント、クォート）に対応しています。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成 & 有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクトの requirements.txt / pyproject.toml に従う
   ```

4. .env を作成（プロジェクトルートに .env を置く）
   - .env.example を参考に必須値を設定してください。

5. データベース・監査スキーマ初期化（任意）
   - 監査用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # :memory: でも可
     ```
   - DuckDB の接続を用意したら、ETL / その他操作に渡して使用します。

---

## 使い方（基本例）

- 日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 株価（prices）差分 ETL のみ
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
  ```

- ニュースセンチメント解析（銘柄別スコア）を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定するか、api_key を引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存 DB に追加）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

各関数はドキュメンテーションストリング（docstring）に使用法・引数や返り値、例外動作が記載されていますので参照してください。

---

## 設計上の注意点 / 取り決め

- ルックアヘッドバイアス回避:
  - 各処理は内部で date.today() を直接参照しないか、引数として基準日を受け取ります。
  - prices_daily 等の取得・クエリでは target_date 未満（排他）などの条件が組み込まれています。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE を使っているため再実行に耐えます。
- 外部 API:
  - J-Quants クライアントはレート制限・リトライ・401 リフレッシュに対応。
  - OpenAI 呼び出しはリトライやフェイルセーフ（失敗時は 0.0 を返す等）を実装。
- セキュリティ:
  - RSS 収集は SSRF 防止、XML 安全パーサ（defusedxml）、応答サイズ制限などを実施。

---

## ディレクトリ構成（抜粋）

リポジトリは src/kabusys に配置されることを想定しています。主なファイル:

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    # ニュースセンチメント（銘柄別）
    - regime_detector.py             # マクロ + MA でレジーム判定
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント & DuckDB 保存
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - etl.py                         # ETLResult 再エクスポート
    - calendar_management.py         # 市場カレンダー管理
    - news_collector.py              # RSS 取得・前処理
    - quality.py                     # 品質チェック
    - stats.py                       # 統計ユーティリティ（zscore_normalize）
    - audit.py                       # 監査スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             # モメンタム/ボラティリティ/バリュー
    - feature_exploration.py         # 将来リターン/IC/summary/rank

---

## 開発 / テスト

- 自動環境読み込みはデフォルトで有効です。テスト時に自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API 呼び出し等外部通信は関数内の `_call_openai_api` をモックしてユニットテストを書く想定です。
- DuckDB をインメモリ（":memory:"）で使えばテストが簡単になります。

---

## 参考・補足

- 各モジュールには詳細な docstring があり、設計方針・処理フロー・フェイルセーフ挙動が記載されています。実装の詳細は該当ファイルを参照してください。
- ライセンス情報や貢献ガイドが必要であればプロジェクトルートに追加してください。

---

ご要望があれば、README に以下を追加できます：
- requirements.txt / pyproject.toml の推奨内容
- CI / CD（GitHub Actions）サンプル
- より詳細な実行例（cron ジョブ、Airflow 連携等）
- データベーススキーマの完全一覧（DDL）