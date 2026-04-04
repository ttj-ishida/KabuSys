# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants -> DuckDB）、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注〜約定トレース）などを提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・前処理・研究（リサーチ）・戦略サポートに必要なユーティリティ群をまとめた Python パッケージです。主な用途は以下です。

- J-Quants API からのデータ取得 & DuckDB への差分保存（ETL）
- RSS ニュース収集と OpenAI を使ったニュースセンチメント評価（銘柄別 ai_score）
- マクロ + テクニカルを統合した市場レジーム判定
- ファクター計算・特徴量探索（リサーチ用）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 発注〜約定を追跡する監査ログスキーマの初期化・操作

設計方針としては「バックテストでのルックアヘッドバイアス防止」「ETL・DB操作の冪等性」「外部API呼び出しの堅牢なリトライ」「テストしやすさ」を重視しています。

---

## 機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証、ページング、レート制御、保存関数）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS -> raw_news）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: ニュースを LLM に投げ銘柄別スコアを ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200乖離 + マクロ記事センチメントで市場レジーム判定
- research/
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config
  - .env 自動読み込み（プロジェクトルート検出）と Settings（環境変数ラッパー）

---

## 前提 / 必要環境

- Python 3.10 以上（型アノテーションの union 表記などを使用）
- 必要パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらに従ってください）

インストール例（簡易）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発時にローカルパッケージとして扱う場合
pip install -e .
```

---

## 環境変数 / 設定

パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を自動検出し、優先順位に従って環境変数を読み込みます:

読み込み順（優先度高→低）
1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env

自動ロードを無効化するには環境変数を設定:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主要な環境変数（必須のものとデフォルト値）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- OPENAI_API_KEY (必須 for AI functions) — OpenAI API キー
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 監視関連
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

注意: Settings は属性アクセス（例: settings.jquants_refresh_token）で値を取得し、必須変数が未設定の場合は ValueError を送出します。

---

## セットアップ手順（簡易ガイド）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成 & 依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # 無ければ個別に duckdb openai defusedxml をインストール
   ```

3. 環境変数を設定（.env をプロジェクトルートに作成）
   例: .env
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

4. DuckDB 初期スキーマ（監査ログ等）が必要なら初期化
   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   init_audit_db(settings.duckdb_path)
   ```

5. ETL 実行や AI スコアリングを呼び出し可能

---

## 使い方（代表的な呼び出し例）

Python スクリプト／REPL から直接呼ぶ例を示します。

準備（共通）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL を実行（市場カレンダー取得・株価・財務・品質チェックを順に実行）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメント（ai_scores へ保存）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

市場レジーム判定（market_regime テーブルへ保存）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

監査DB の初期化（監査ログ専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

データ品質チェックの実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意:
- OpenAI を用いる関数（score_news, score_regime）は OPENAI_API_KEY が必要です。引数 api_key を渡すことも可能です。
- J-Quants API は JQUANTS_REFRESH_TOKEN が必要です。jquants_client.get_id_token により自動で ID トークンを取得します。

---

## ディレクトリ構成

以下は主要なファイル/モジュール構成（src/kabusys 以下）です。実際のリポジトリにあるファイルに合わせてください。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - calendar_management.py
      - news_collector.py
      - quality.py
      - audit.py
      - stats.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
      - ...
    - research/ (その他ユーティリティ)
    - monitoring/ (※コードベースに含まれている場合)
    - execution/ (※コードベースに含まれている場合)

（上記は抜粋です。詳細はプロジェクト内の src/kabusys ディレクトリを参照してください）

---

## 注意事項 / トラブルシューティング

- 環境変数が未設定の場合、多くの関数（特に外部APIを使うもの）は ValueError を送出します。エラーを見たら env を確認してください。
- .env 読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml）。テスト時などで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはリトライやフェイルセーフ（失敗時にスコアを 0 にフォールバック）を組み込んでいますが、API キー・料金・レート制限には注意してください。
- J-Quants クライアントはレート制限（120 req/min）を守る実装です。大量ページングを行う処理では時間がかかる点に注意してください。
- news_collector は RSS の URL 正規化や SSRF ガード、XML パースを堅牢に行うよう実装されています。外部ソース追加時は URL の妥当性に注意してください。
- DuckDB の executemany に関する制約（バージョン差）を考慮した実装箇所があります。もし挙動がおかしい場合は duckdb パッケージのバージョンを確認してください。

---

## 開発に関する補足

- 型注釈・ログ出力が充実しているため、IDE での補完や静的解析がしやすくなっています。
- 単体テストや、OpenAI/J-Quants 呼び出し部分はモック可能な設計になっています（関数を patch して差し替え）。

---

README の内容や利用方法で不明点があれば、どの機能を詳しく知りたいか（例: ETL の詳細な設定、news_nlp のプロンプト設計、監査ログスキーマの拡張方法など）を教えてください。必要に応じて具体的なコード例や運用手順を追記します。