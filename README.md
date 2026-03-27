# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants 経由の株価・財務・カレンダー収集）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注 → 約定トレース）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートを検出）
  - 必須環境変数チェック（Settings API）
- データ収集（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー取得（ページネーション・リトライ・レート制御付き）
  - DuckDB へ冪等保存（ON CONFLICT）
- ETL パイプライン
  - run_daily_etl による市場カレンダー、株価、財務データの差分取得・保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - ETL 結果を ETLResult で返却
- ニュース収集
  - RSS 取得・前処理・SSRF 対策・トラッキングパラメータ除去
  - raw_news / news_symbols への冪等保存（ID生成は正規化 URL のハッシュ）
- ニュース NLP（OpenAI）
  - gpt-4o-mini を用いた銘柄ごとのセンチメント集計（score_news）
  - レート制限や 429/タイムアウト/5xx に対するリトライ実装、結果バリデーション、±1.0 でクリップ
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成（score_regime）
  - LLM 呼び出しのフォールバック・再試行ロジックを搭載
- 研究（Research）
  - モメンタム／ボラティリティ／バリューなどのファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化など
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定の階層的トレーサビリティ用テーブルを DuckDB に初期化（init_audit_schema / init_audit_db）
  - 冪等キー・ステータス管理・UTC タイムスタンプ対応

---

## 必要条件

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

（正確な requirements はプロジェクトの packaging / requirements ファイルに従ってください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージに含める
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - またはプロジェクトに requirements.txt / pyproject.toml があれば pip install -e .（開発インストール）
4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成（自動読み込みされます）
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
   - 省略時のデフォルトやパス:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|...)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

簡易的な .env.example:
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- KABU_API_PASSWORD=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

---

## 使い方（主な API と実行例）

※ 以下は簡易例です。実際はログ設定・例外処理などを行ってください。

1) DuckDB 接続と日次 ETL 実行
- 例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

2) ニュースセンチメントスコアを作成（score_news）
- 例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} codes")
  ```

3) 市場レジーム判定（score_regime）
- 例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

4) 監査ログ DB 初期化
- 例（専用 DB を作る場合）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

5) ファクター・リサーチ機能の利用（例: モメンタム計算）
- 例:
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

6) 設定値参照
- 例:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## 自動 .env ロードの挙動

- 実行時、パッケージ内でプロジェクトルート（.git または pyproject.toml を探索）を検出すると、優先度:
  OS 環境変数 > .env.local > .env
  で自動ロードされます。
- テスト等で自動ロードを無効にする場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

---

## ディレクトリ構成（抜粋）

（主要なモジュールを示します）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py        ← ニュースセンチメント（score_news）
    - regime_detector.py ← 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py        ← run_daily_etl / run_*_etl / ETLResult
    - stats.py
    - quality.py
    - audit.py           ← 監査ログ初期化
    - jquants_client.py  ← J-Quants API クライアント（fetch/save）
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/ 以下はファクター計算や統計ユーティリティへアクセスするための API を再公開

（この README はコードベースに合わせた抜粋構成です。完全なファイル一覧はリポジトリを参照してください）

---

## 実運用上の注意

- OpenAI / J-Quants API キー管理は慎重に行ってください（特に課金リスク）。
- run_daily_etl や score_news は外部 API を呼ぶためネットワーク/レート制限・コストに注意。
- DuckDB ファイルは適切にバックアップしてください。
- audit テーブルは削除しない前提で設計されています（監査ログ）。
- LLM 呼び出しについてはレスポンス検証とフォールバック（0.0）ロジックが組み込まれていますが、想定外の出力に備えて監視を行ってください。

---

## 開発 / テストのヒント

- 自動 .env ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 各モジュールの OpenAI 呼び出しは内部でラップされているため、ユニットテストでは該当関数（例: kabusys.ai.news_nlp._call_openai_api）を patch / モックして挙動を検証できます。
- DuckDB を ":memory:" にして単体テストを高速化できます。

---

もし README に追加したい使用例（CLI、cron の設定例、さらに詳しい .env.example、CI 設定など）があれば教えてください。必要に応じて追記します。