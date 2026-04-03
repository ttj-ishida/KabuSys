# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、研究用ファクター計算、監査ログ（発注 → 約定トレース）、市場カレンダー管理などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびデータプラットフォームのコア機能群を提供する Python パッケージです。主な目的は以下です。

- J-Quants API を用いた株価／財務／カレンダーの差分 ETL（DuckDB に保存）
- RSS に基づくニュース収集と記事前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュース／マクロセンチメント評価
- 研究用途のファクター計算（モメンタム / ボラティリティ / バリュー 等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal → order_request → execution のトレース）
- 市場カレンダー管理（JPX）

設計上の共通方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today() を直接参照する箇所を制限）
- DuckDB をデータレイヤーに利用
- API 呼び出しはリトライ・バックオフ・レート制御を導入
- 冪等性を重視（DB 保存は ON CONFLICT / DELETE→INSERT のパターン）

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` 自動読み込み（プロジェクトルート検出）
  - 設定アクセス: `kabusys.config.settings`（JQUANTS_REFRESH_TOKEN や DB パス等）
- データ ETL（kabusys.data.pipeline）
  - 日次 ETL のエントリポイント: `run_daily_etl`
  - J-Quants クライアント（取得・保存関数）
  - カレンダー更新ジョブ
  - ETL 結果を表す `ETLResult`
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策・XML 安全化）
  - 文章前処理・記事ID 正規化（SHA-256）
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を用いた銘柄毎のセンチメントスコア生成（JSON Mode）
  - バッチ処理・リトライ・レスポンス検証
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成
  - market_regime テーブルへの冪等書き込み
- 研究モジュール（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン計算・IC・要約統計）
  - Z スコア正規化ユーティリティ
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付整合性チェック
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を作成・初期化する DDL とヘルパ
  - 監査 DB 初期化 helper（UTC タイムゾーン固定）

---

## セットアップ手順（開発環境向け）

前提
- Python 3.10+ 推奨（型アノテーションで | を使用するため）
- DuckDB、OpenAI SDK、defusedxml などの依存

推奨手順（ローカル開発）：

1. リポジトリをクローンしワークディレクトリへ移動
   - git clone ...
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存をインストール
   - 必要な主なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - プロジェクトに pyproject.toml / setup.py がある場合:
     - pip install -e .
4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成してください。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に必要）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注関連）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 sqlite（デフォルト: data/monitoring.db）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - KABUSYS_ENV — development / paper_trading / live
   - 自動ロードを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 注意: パッケージは `.env` をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みします。

5. データフォルダ作成（例）
   - mkdir -p data

---

## 使い方（主要 API の例）

以下は簡単な実行例です。すべて例であり、実行前に必要な環境変数や DB スキーマが整っていることを確認してください。

- 基本的な接続例（DuckDB）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())  # ETLResult の内容を確認
```

- ニュースセンチメントスコア生成（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを明示的に渡すか、OPENAI_API_KEY 環境変数を設定してください
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} symbols")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB の初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.sqlite_path など任意のファイルパスを指定
audit_conn = init_audit_db(settings.duckdb_path)  # 例: same DB file or separate
```

- 設定アクセス例
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)
```

注意点:
- OpenAI 関連関数（news_nlp, regime_detector）は API 呼び出しに失敗した場合フェイルセーフでスコアを 0 相当にフォールバックする設計です（例外を投げないケースが多い）。
- ETL / save_* 関数は DuckDB 側で ON CONFLICT を使用し冪等に保存します。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants refresh token（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD — kabu API パスワード
- KABU_API_BASE_URL — kabu API base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 監視関連
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

---

## 開発者向けメモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準とします。パッケージ配布後も CWD に依存せず動作するように設計されています。
- OpenAI 呼び出しの内部関数はテスト時にモック可能（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- J-Quants API クライアントは固定間隔の RateLimiter を用いてレート制限（120 req/min）を守ります。401 を受けた場合は自動でトークンをリフレッシュして再試行します。
- DuckDB を想定した SQL 実装のため、バージョン特有の挙動（executemany の空リスト不可など）に留意しています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトのソースは `src/kabusys/` 以下にあります。主要ファイル・モジュールを抜粋します。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py                  — ニュース NLP（OpenAI）
      - regime_detector.py           — 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント / 保存関数
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - etl.py                       — ETL インターフェース再エクスポート
      - news_collector.py            — RSS 収集 / 前処理
      - calendar_management.py       — 市場カレンダー管理
      - quality.py                   — データ品質チェック
      - stats.py                     — 統計ユーティリティ（zscore_normalize）
      - audit.py                     — 監査ログ（DDL / 初期化）
    - research/
      - __init__.py
      - factor_research.py           — モメンタム / ボラティリティ / バリュー計算
      - feature_exploration.py       — 将来リターン / IC / 統計要約
    - monitoring/ (省略されているが監視系が存在する想定)
    - strategy/, execution/ (発注／戦略関連は名前空間で公開)

---

## ライセンス・貢献

（この README ではライセンスファイル・コントリビュート手順は省略しています。実運用する場合は LICENSE、CONTRIBUTING を適宜追加してください。）

---

README の内容はコードベース（src/kabusys）に基づいて作成しています。実行や本番運用の際は、環境変数・API キー・DB スキーマ（必要なテーブルの作成）・ネットワークアクセス権等を十分に確認してください。必要であれば各モジュールのドキュメントや docstring を参照してください。