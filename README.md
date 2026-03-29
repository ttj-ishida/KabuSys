# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。ETL（J-Quants からのデータ取得）、ニュース収集・NLP（LLM によるセンチメント）、市場レジーム判定、ファクター計算、監査ログ（発注 → 約定のトレーサビリティ）など、売買システム／リサーチ基盤に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ ETL
  - J-Quants API からの株価（日足）、財務データ、JPX カレンダー取得（差分更新・ページネーション・再取得/バックフィル対応）
  - DuckDB への冪等保存（ON CONFLICT を利用）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL エントリポイント `run_daily_etl`

- ニュース収集・NLP
  - RSS からのニュース収集（SSRF 対策・トラッキング除去・サイズ制限）
  - OpenAI（gpt-4o-mini, JSON mode）を使った銘柄別センチメント付与（`score_news`）
  - 1 銘柄あたりの文字数・記事数制限、バッチ処理、リトライ・バックオフ実装

- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離（70%）とマクロニュースの LLM センチメント（30%）を合成し daily レジーム（bull/neutral/bear）を判定（`score_regime`）
  - LLM 呼び出しのリトライ・フェイルセーフ実装

- リサーチユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（`research`）
  - 将来リターン計算、IC（Spearman）、Z スコア正規化等

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までトレース可能な監査テーブル定義・初期化機能（`data.audit.init_audit_schema` / `init_audit_db`）
  - UUID ベースの冪等キー・ステータス管理

- 設定管理
  - `.env` / `.env.local` と環境変数の統合ロード、必要環境変数の明示（`kabusys.config.settings`）

---

## 要件

- Python 3.10+
- 主要依存（代表）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- その他標準ライブラリ（urllib, logging, json 等）を利用

実際のプロダクションでは requirements.txt / pyproject.toml を用意してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

   （パッケージはプロジェクトに合わせて適宜追加してください）

4. （開発）パッケージを editable インストール
   ```
   pip install -e .
   ```

5. 環境変数の準備
   - プロジェクトルート（`src/kabusys` から上がったルート）に `.env` または `.env.local` を配置すると自動読み込みされます（デフォルト）。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   - 最低限必要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=... (score_news / regime_detector の呼び出しで未指定の場合に参照)
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development  # 有効値: development / paper_trading / live
     - LOG_LEVEL=INFO

   - `.env` のパース挙動:
     - `export KEY=val` にも対応
     - シングル/ダブルクォート内のバックスラッシュエスケープ対応
     - コメント（#）は一定条件で無視
     - OS 環境変数はデフォルトで保護されます（.env の上書きに制限あり）

---

## 使い方（簡単な例）

以下はモジュールの主要な利用方法の例です。DuckDB を利用したローカル実行を想定します。

- 日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出する（OpenAI API キーは環境変数 OPENAI_API_KEY でも可）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n} codes")
  ```

- 市場レジーム判定を行う
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ DB の初期化（専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # ":memory:" でインメモリ可能
  # これで監査テーブルとインデックスが初期化されます
  ```

- 設定値の取得
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)  # 未設定なら ValueError
  print(settings.kabu_api_base_url)      # デフォルト http://localhost:18080/kabusapi
  print(settings.env)                    # development/paper_trading/live のいずれか
  ```

注意点:
- AI（OpenAI）呼び出しは外部 API への通信を行うため、テストでは該当関数をモックしてください（コード内でもモックしやすい設計になっています）。
- LLM へのプロンプトは JSON モード（response_format={"type":"json_object"}）で期待する構造を要求しています。レスポンスパース失敗時はフェイルセーフとしてデフォルト値にフォールバックします。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                    — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                — ニュースの LLM スコアリング（score_news）
  - regime_detector.py         — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py          — J-Quants API クライアント（fetch / save）
  - pipeline.py                — ETL パイプライン（run_daily_etl 等）
  - etl.py                     — ETL 公開インターフェース（ETLResult 再エクスポート）
  - calendar_management.py     — マーケットカレンダー管理・判定関数
  - news_collector.py          — RSS ベースのニュース収集
  - quality.py                 — データ品質チェック
  - stats.py                   — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                   — 監査ログスキーマ初期化・ヘルパー
- research/
  - __init__.py
  - factor_research.py         — ファクター計算（momentum/volatility/value）
  - feature_exploration.py     — 将来リターン・IC・統計サマリー等
- research/__init__.py
- その他: strategy / execution / monitoring 等の名前空間（パッケージ公開用）

（上記はリポジトリ内の主要ファイルを抜粋した構成です）

---

## 環境変数・.env の例（.env.example）

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション（発注等）
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（相対パス/ホーム展開可）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 運用モード
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## テスト・開発上の注意

- LLM / 外部 API 呼び出しはモック可能な設計になっています。ユニットテスト時は `_call_openai_api` や `kabusys.data.news_collector._urlopen` などを patch して外部通信を差し替えてください。
- `.env` 自動読み込みはプロジェクトルート（.git または pyproject.toml がある階層）を基準に行われます。テストで自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のバージョンによっては executemany の挙動が制約されるため、実装側で空集合に対する呼び出しを回避する対策が入っています。

---

## 補足

- 本リポジトリは「データ取得・処理」「リサーチ」「監査ログ」「LLM を使った NLP」などを分離して実装しており、本番の発注処理（ブローカーとの直接通信）部分は別モジュール/実装で繋ぐことを想定しています。
- セキュリティ: RSS の取得や外部 API 呼び出しには SSRF 対策、レスポンスサイズの制限、XML の防御的パースなどの安全策が盛り込まれています。

ご不明点や README に追加したい利用例があれば教えてください。README を用途（開発者向け / 運用手順書向け）に合わせて拡張できます。