# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、ファクター算出、監査ログ、発注監視等の機能を備えた内部ライブラリ群です。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を提供します：

- J-Quants API からの差分取得（株価・財務・上場情報・マーケットカレンダー）と DuckDB への冪等保存
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）およびマクロセンチメント合成による市場レジーム判定
- ファクター（モメンタム / バリュー / ボラティリティ等）計算と特徴量探索ツール
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（シグナル → 発注 → 約定のトレーサビリティ）と初期化ヘルパ
- kabuステーション等への発注/監視用設定（設定は環境変数で管理）

設計上の特徴：
- ルックアヘッドバイアス防止（datetime.today()/date.today() を内部で不用意に参照しない設計）
- DuckDB を中心とした SQL 操作（外部ライブラリ依存を最小化）
- 冪等性を重視した保存ロジック（ON CONFLICT など）
- API 呼び出しはレート制御・リトライ・トークン自動リフレッシュ等の堅牢化を実装

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_db / init_audit_schema）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント生成・ai_scores 書き込み（OpenAI 利用）
  - regime_detector.score_regime: ETF MA200 とマクロニュースを合成した市場レジーム判定
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config.py
  - 環境変数管理（.env 自動読み込み、必須変数チェック、各種パス・フラグ）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | None` 構文を使用）
- DuckDB を利用可能な環境

インストール手順（例）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（最低限）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を推奨）

3. 開発インストール（編集可能な状態）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（代表例）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector が参照）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_FILL_MODE: paper trading の fill モード（instant/partial/never/reject）
- その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値等

簡易 .env 例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な呼び出し例）

以下はライブラリ関数を直接呼ぶ簡単な例です。実運用ではジョブスケジューラや CLI/サービスから呼び出します。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数に設定されていることを確認
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジームを判定して market_regime テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring_audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

注意点:
- AI モジュールを実行するには OPENAI_API_KEY が必要です（引数での注入も可能）。
- ETL 実行時は J-Quants のアクセストークン（settings.jquants_refresh_token）を用いて id_token を自動取得します。
- 自動 .env 読み込みはプロジェクトルートを基準に行われます（.git または pyproject.toml を探索）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ初期化、バージョン定義
- config.py — 環境変数 / 設定の読み込みと検証
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETL 型の再エクスポート（ETLResult）
  - news_collector.py — RSS 収集・前処理
  - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログスキーマ定義と初期化
- research/
  - __init__.py
  - factor_research.py — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank

（上記以外に strategy / execution / monitoring 等のパッケージ参照が __all__ に含まれていますが、今回のコード抜粋に含まれない場合があります）

---

## 開発・運用上の注意

- Python バージョンは 3.10 以上を推奨します（型ヒントに新しい構文を使用）。
- OpenAI / J-Quants など外部 API を利用する機能はネットワーク・課金が発生するため、本番環境でのキー管理に注意してください。
- ETL や AI モジュールは外部 API の失敗に対してフェイルセーフ設計（多くはスキップして継続）になっていますが、ログと品質チェックの結果を必ず確認してください。
- DuckDB に対する executemany の空リストバインド等、バージョン依存の挙動に注意（パッケージ内で対策済みの箇所あり）。
- テスト実行時に自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

この README はコードベースの要点をまとめたものです。詳細な API 仕様や運用手順は各モジュールの docstring（ソース内コメント）を参照してください。質問や追加のドキュメント化が必要であれば教えてください。