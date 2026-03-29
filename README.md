# KabuSys

日本株向けの自動売買 / データプラットフォーム補助ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を使用したセンチメント評価）、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（.env）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株向けの自動売買システム開発を支援するためのモジュール群です。データの ETL、ニュース収集と AI による記事スコアリング、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（order / execution トレース）など、実運用で必要となる共通機能を集めています。

設計方針の例:
- ルックアヘッドバイアスを避ける（datetime.today() を直接参照しない設計）
- DuckDB を主な分析 DB として利用
- 冪等性（ETL の ON CONFLICT / DO UPDATE 等）を重視
- 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・バックオフ・レート制御を実装
- テスト容易性のため依存注入（api_key 等）をサポート

---

## 主な機能（抜粋）
- data/
  - ETL パイプライン（J-Quants からの daily quotes / financials / market calendar 取得）
  - market calendar 管理と営業日判定
  - news_collector: RSS 収集、前処理、raw_news への保存（SSRF 対策・サイズ制限等）
  - jquants_client: API クライアント（認証・ページネーション・保存関数）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査テーブルの初期化 / 監査 DB ユーティリティ
- ai/
  - news_nlp.score_news: OpenAI を用いたニュース記事の銘柄別センチメント集約・ai_scores 書き込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- config.py
  - 環境変数の自動ロード（プロジェクトルートの .env / .env.local）と Settings インターフェース

---

## セットアップ手順

前提:
- Python 3.9 以上（typing の型表現に依存）
- 必要な拡張パッケージ（下記参照）

推奨手順（ローカル開発）:

1. リポジトリをクローン / 取得
2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```
3. 依存パッケージをインストール  
   このコードベースで利用している代表的な外部依存（例）:
   - duckdb
   - openai
   - defusedxml
   - requests（必要に応じて）
   - (必要に応じて) slack_sdk 等

   例:
   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクトに requirements.txt がある場合:
   # pip install -r requirements.txt
   ```
4. パッケージを editable インストール（開発用）
   ```bash
   pip install -e .
   ```
5. 環境変数の準備  
   プロジェクトルートに `.env`（と必要であれば `.env.local`）を置くと自動でロードされます（config.py の自動ロード機能）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主要）
config.Settings で参照される主な環境変数（必須は _require により未設定時に例外）:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD : kabuステーション API を使う場合のパスワード
- SLACK_BOT_TOKEN : Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID : Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUS_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : duckdb ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 sqlite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY : OpenAI の API キー（ai.score_news / score_regime に使用可能）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易サンプル）

以下は Python から直接呼ぶ例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

- DuckDB に接続して日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {written}")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究用途のファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は list[dict] 形式
```

注意:
- OpenAI 呼び出しは外部ネットワークを使用します。API キーと利用料に注意してください。
- ETL / 取得処理はネットワーク・API レート制限に従い時間を要します。

---

## ディレクトリ構成（要約）
（コードベースの主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定と .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース記事の LLM によるスコアリング
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得＋DuckDB 保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL 結果型の再エクスポート
    - news_collector.py      — RSS 取得・前処理
    - calendar_management.py — マーケットカレンダー関連ユーティリティ（営業日判定等）
    - quality.py             — データ品質チェック
    - stats.py               — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログテーブル初期化 / audit DB ヘルパー
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン・IC・集計関数
  - (その他: strategy / execution / monitoring などが __all__ に名前として挙がっています。実装が続くかもしれません)

---

## 注意事項・運用上のポイント
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト等で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは失敗時にフォールバック（score を 0.0）する等のフェイルセーフが組み込まれていますが、API 使用量とエラーハンドリングに注意してください。
- ETL と品質チェックは分離され、品質問題があっても ETL 全体が停止しない設計です。result.has_quality_errors や result.has_errors をチェックした上で運用判断を行ってください。
- DuckDB のバージョンに依存する挙動（executemany の空リスト制約 など）があります。テスト環境・本番環境でバージョン整合を取ってください。

---

もし README に追記したい点（例: サンプル .env.example ファイルの完全版、CI / デプロイ手順、依存関係ファイルの追加）があれば教えてください。README をそれに合わせて拡張します。