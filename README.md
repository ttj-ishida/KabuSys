# KabuSys

KabuSysは日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants連携）・データ品質チェック・ニュース収集とNLPスコアリング・AIによる市場レジーム判定・ファクター計算・監査ログ（トレーサビリティ）など、量的運用のための主要機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

このライブラリは以下の目的で設計されています。

- J-Quants APIからの株価・財務・カレンダー情報の差分取得とDuckDBへの冪等保存（ETLパイプライン）
- raw_newsの収集・前処理・銘柄紐付け（RSSベース）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）とマクロセンチメント評価
- ETFベースの200日移動平均乖離とマクロセンチメントを組み合わせた市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）をDuckDBに初期化・管理
- JPXカレンダー管理（営業日計算、夜間バッチ更新）

設計方針として、ルックアヘッドバイアス防止や冪等性、エラー時のフォールバックを重視しています。

---

## 機能一覧

主な機能（モジュール）

- kabusys.config
  - .env / 環境変数の自動読み込み、設定アクセス（settings）
- kabusys.data
  - jquants_client: J-Quants APIクライアント（レートリミット・リトライ・トークンリフレッシュ含む）
  - pipeline: 日次ETL（市場カレンダー・株価・財務・品質チェック）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS取得と記事前処理・raw_news保存
  - calendar_management: 営業日判定・next/prev_trading_dayやcalendar更新ジョブ
  - audit: 監査テーブルのDDL定義と初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント算出と ai_scores への保存
  - regime_detector.score_regime: ETF(1321)のMA乖離 + マクロセンチメントで日次市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

その他：
- DuckDB を主要なストレージエンジンとして利用
- OpenAI（Chat Completions / JSON mode）連携（APIキーは引数または環境変数）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに union types 等を使用）
- ネットワークアクセス（J-Quants、OpenAI、RSS取得）

インストール（開発環境）
1. リポジトリをクローン
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - あるいは pyproject.toml / requirements.txt がある場合はそれを利用してください。
4. パッケージをeditableでインストール（任意）
   - pip install -e .

環境変数 / .env
- プロジェクトルート（pyproject.toml または .git を基準）に `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定）。
- 代表的な環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI APIキー（news_nlp / regime_detector のデフォルト）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE通知用（任意）
  - DUCKDB_PATH: メイン DuckDB ファイルパス（例: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（任意）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG | INFO | WARN | ERROR（デフォルト INFO）
  - その他監視関連変数（PID_FILE_PATH 等）

注意:
- `.env.example` を参照して `.env` を作成してください（プロジェクトに例ファイルがある想定）。
- セキュリティ上の理由でトークンや秘密情報はリポジトリに含めないでください。

---

## 使い方（代表例）

以下はライブラリAPIを直接呼ぶ簡単な例です。実運用ではスクリプトやデーモンから呼び出してください。

共通準備:
```python
import duckdb
from kabusys.config import settings

# DuckDB ファイルへの接続（settings.duckdb_path は Path を返す）
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次ETLを実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())  # ETLResult の概要を表示
```

2) ニュースセンチメント（銘柄別）を取得して ai_scores に保存
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーを引数で渡すこともできます。None の場合は環境変数 OPENAI_API_KEY を参照。
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written {written} codes")
```

3) 市場レジーム判定を実行（ETF 1321 の MA200乖離 + マクロセンチメント）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
# market_regime テーブルに書き込まれます
```

4) 監査用DB初期化（監査ログ専用のDuckDB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 必要に応じて audit_conn をアプリの監査ログ用に使用
```

5) JPXカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date

saved = calendar_update_job(conn, lookahead_days=90)
print("saved", saved)
```

注意点:
- OpenAI呼び出しはAPI呼び出しに失敗した場合フェイルセーフでスコア0やスキップにフォールバックしますが、APIキーは必須（明示的に渡すか OPENAI_API_KEY を設定してください）。
- DuckDBのテーブルスキーマや初期化処理はアプリ側で整備する必要があります（data/schema 初期化等のユーティリティを用意してください）。

---

## 設定（主要な環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI APIキー（news_nlp / regime_detector用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視データ用）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます。

kabusys.config.Settings からプロパティでアクセスできます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## ディレクトリ構成

下記は主要なモジュールとファイルの構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュースNLP（銘柄別スコア）
    - regime_detector.py           # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants APIクライアント + DuckDB保存
    - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       # JPXカレンダー管理
    - news_collector.py            # RSS 収集・前処理
    - quality.py                   # データ品質チェック
    - stats.py                     # 統計ユーティリティ（zscore_normalize 等）
    - audit.py                     # 監査ログスキーマ初期化
    - etl.py                       # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py           # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py       # calc_forward_returns / calc_ic / factor_summary / rank

その他:
- pyproject.toml / setup.cfg 等（プロジェクトルートに存在する想定）
- .env, .env.local（環境変数をここで管理）
- data/（デフォルトのDBや一時ファイル格納先）

---

## 運用上の注意

- ルックアヘッドバイアス対策:
  - 各モジュールは内部で date や window を外部引数として受け取り、datetime.today()/date.today() に直接依存しない設計になっています。バックテストや再現性のため、この設計方針を守ってください。
- 冪等性:
  - J-Quantsから取得したデータは ON CONFLICT DO UPDATE 等により冪等に保存されます。
- エラーハンドリング:
  - OpenAIやHTTP API呼び出しはリトライ・フェイルセーフ設計です。重大な失敗はログに残り、部分成功をできるだけ保持する設計です。
- セキュリティ:
  - .envにシークレットを保存する場合は適切なアクセス制御をしてください。
  - news_collector は SSRF対策（ホスト検証・リダイレクト検査）を実装していますが、RSSソースは信頼できるものに限定してください。

---

## 開発・貢献

- バグ報告や機能提案は Issue で受け付けてください。
- コード変更時はユニットテストを追加し、静的型チェック（mypy等）の実行を推奨します。

---

このREADMEはコードベースの要点をまとめたものです。詳細なAPI仕様やDDL、運用手順は各モジュールのdocstringやプロジェクト内ドキュメント（DataPlatform.md, StrategyModel.md 等）を参照してください。