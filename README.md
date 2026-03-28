# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ（KabuSys）。  
ETL、ニュース収集・NLP、リサーチ用ファクター計算、監査ログ定義、J-Quants / kabuステーション / OpenAI 連携などを含むモジュール群です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要なAPIの例）
- 環境変数 / 設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・品質検査・特徴量計算・ニュースセンチメント評価・市場レジーム判定・監査ログ管理など、アルゴリズム取引や研究向けに必要な基盤機能を提供する Python ライブラリです。  
設計上の特徴として、ルックアヘッドバイアスを避ける取り扱い（日時参照の扱いの配慮）、DuckDB を用いたローカルデータ管理、外部API呼び出しのリトライ・フェイルセーフポリシー、ID トークンの自動更新などを備えています。

---

## 主な機能一覧

- 環境設定読み込み（.env / .env.local をプロジェクトルートから自動ロード、無効化可能）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得・保存（ページネーション対応、レート制御、リトライ）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 上場銘柄情報取得
- ETL パイプライン
  - 日次 ETL（calendar / prices / financials） + 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、gzip制御）
  - raw_news / news_symbols への冪等保存
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュースセンチメント評価（gpt-4o-mini / JSON Mode）
  - レート制御・チャンク処理・リトライ・レスポンス検証
- 市場レジーム判定（AI + テクニカル）
  - ETF (1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算・IC・統計サマリー
- 汎用統計ユーティリティ（Zスコア正規化等）

---

## セットアップ手順

前提: Python 3.10+ を想定（ソースは型ヒントで Python >=3.10 のユニオン演算子等を使用）。

1. リポジトリをチェックアウト / コピー

2. 仮想環境を作成・有効化（推奨）
   - Unix/macOS
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存ライブラリをインストール  
   （プロジェクトに pyproject.toml / requirements がある想定。基本的に以下が必要です）
   ```
   pip install duckdb openai defusedxml
   ```
   実際のパッケージリストはプロジェクトの packaging 設定に従ってください。

4. パッケージを開発モードでインストール（任意）
   プロジェクトルートに pyproject.toml がある場合:
   ```
   pip install -e .
   ```

5. 環境変数の設定  
   必要な環境変数は次節「環境変数 / 設定」を参照。プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

## 環境変数 / 設定

KabuSys は環境変数または .env ファイルから設定を読み込みます（優先順位: OS環境変数 > .env.local > .env）。自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使用可能）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視等）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）デフォルトは development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

注意:
- Settings で未設定の必須値を参照すると ValueError が発生します。
- .env のパースは一般的な shell 風記述に対応（export プレフィックスや引用符・コメント処理あり）。

---

## 使い方（主要な例）

以下は最小限の利用例です。詳細な業務ロジック・DB スキーマ準備はプロジェクトの別ドキュメントに従ってください。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント評価（AI: OpenAI）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にあれば api_key を省略可能
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n_written} codes")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
# market_regime テーブルに書き込まれます
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブル(signal_events, order_requests, executions) が作成されます
```

- カレンダー更新ジョブ（J-Quants から差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} calendar rows")
```

ログの出力や詳細な例、DB スキーマ（tables）についてはプロジェクト内部の data/schema 定義や追加ドキュメントを参照してください。

---

## 注意点 / 実装上の設計ポリシー（抜粋）

- ルックアヘッドバイアス対策:
  - AI スコアリング / レジーム判定 / ETL などの関数は内部で datetime.today()/date.today() を直接参照しないか、呼び出し側で日付を明示的に渡す設計になっています（テスト・バックテスト時の安全性）。
- 外部 API 呼び出し:
  - レート制御、再試行、429/5xx への対応、401 のトークンリフレッシュなどを備えています。API エラー時はフェイルセーフ（デフォルトスコア 0.0 や処理のスキップ）で継続することが多いです。
- DuckDB を中心にデータを永続化し、ETL は冪等（ON CONFLICT / DO UPDATE 等）を重視しています。
- ニュース収集: SSRF 対策、トラッキングパラメータ除去、受信バイト数制限、defusedxml による安全な XML パース等を実装しています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         # ニュースセンチメント評価（score_news）
  - regime_detector.py  # 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py   # J-Quants API クライアント（fetch / save）
  - pipeline.py         # ETL パイプライン（run_daily_etl 等）
  - etl.py              # ETLResult の再エクスポート
  - calendar_management.py
  - stats.py
  - quality.py
  - news_collector.py
  - audit.py            # 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/... (その他のリサーチユーティリティ)
- その他: strategy, execution, monitoring パッケージエントリ（package __all__ に含むが今回は省略）

（上記は主要モジュールの抜粋です。実際のリポジトリには追加の補助モジュールやテストが含まれる可能性があります。）

---

もし README に追加したい内容（CI 手順、データベーススキーマ定義の詳細、例 .env.example、運用手順、開発者向けドキュメント等）があれば教えてください。それに合わせて README を拡張します。