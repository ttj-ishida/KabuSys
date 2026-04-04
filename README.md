# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）によるデータ収集、ニュース収集・NLP スコアリング（OpenAI）、ファクター計算・リサーチユーティリティ、監査ログ（発注／約定トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインと研究・自動売買基盤向けの内部ユーティリティ群です。主な目的は以下の通りです。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- RSS ニュース収集と記事の前処理 / 銘柄紐付け
- OpenAI を使ったニュース NLP（銘柄ごとのセンチメント）とマクロセンチメントを用いた市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ初期化と運用ユーティリティ
- データ品質チェックモジュール

設計上の特徴として、ルックアヘッドバイアス回避のため内部で `datetime.today()` 等を不用意に参照せず、DuckDB を DB 層として用いる点が挙げられます。

---

## 機能一覧

- data/
  - ETL パイプライン（差分取得、保存、品質チェック）
  - J-Quants クライアント（認証・ページネーション・リトライ・レート制御）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS、SSRF 対策、前処理、冪等保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（Z スコア正規化 など）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM 評価を合成して market_regime に書き込む
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）
  - 必須環境変数の検証
  - 各種パス / モード /しきい値の取得
- その他
  - OpenAI / J-Quants / kabu API 連携用のクライアントコード（認証・リトライ・レート制御・フェイルセーフ）

---

## 要件

- Python 3.10+
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml
- その他: ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

実際のインストール環境では pyproject.toml / requirements.txt を参照してください（本コードベースに合わせ適宜追加）。

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーへ配置
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - またはパッケージ化されている場合: pip install -e .
4. 環境変数 / .env を準備

必須・推奨される環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector に必要）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注機能を使用する場合）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL, KABUSYS_ENV, PID_FILE_PATH, KILL_FLAG_PATH 等

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development

---

## 使い方（サンプル）

以下は主要機能を Python スクリプトから呼び出すサンプルです。DuckDB 接続を作成して各関数を利用します。

- ETL（日次実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用する場合 api_key=None
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# 以降 conn を使って order_requests / signal_events / executions テーブルが使用可能
```

- ファクター計算（研究用途）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(mom), "件のモメンタム計算結果")
```

注意:
- AI を使う関数は OpenAI API の呼び出しに失敗してもフェイルセーフとして継続する設計です（例: LLM が使えない場合は 0.0 を使う等）。
- 多くの関数は内部で日付パラメータを明示的に受け取り、ルックアヘッドバイアスを防止する設計になっています。バックテストや再現性を重視する場合は target_date を必ず指定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                        — 環境変数 / 設定管理（.env 読み込み、settings）
- ai/
  - __init__.py
  - news_nlp.py                     — ニュース NLP と ai_scores 書き込み
  - regime_detector.py              — マクロ + ETF MA による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py               — J-Quants API クライアント（取得 / 保存）
  - pipeline.py                     — ETL パイプライン（run_daily_etl 他）
  - calendar_management.py          — 市場カレンダー管理（営業日判定等）
  - news_collector.py               — RSS 取得と raw_news 保存
  - quality.py                      — データ品質チェック
  - stats.py                        — 統計ユーティリティ（zscore_normalize）
  - audit.py                        — 監査ログスキーマ初期化 / init_audit_db
  - etl.py                          — ETLResult 再公開
- research/
  - __init__.py
  - factor_research.py              — ファクター計算
  - feature_exploration.py          — 将来リターン・IC・stat summary
- research/*（その他ユーティリティ）
- （strategy/ execution/ monitoring 等の高レベルモジュールは別途実装）

---

## 注意事項 / 実運用上のヒント

- .env の管理: .env.example を参照して必須キーを設定してください。環境に応じて .env.local を使って上書きできます。
- トークン管理: J-Quants トークンは `JQUANTS_REFRESH_TOKEN`、OpenAI は `OPENAI_API_KEY` を使用します。
- レート制御: J-Quants クライアントは120 req/min のレート制限を守る設計です。大量リクエストの際は注意してください。
- DuckDB: スキーマやテーブルが存在しないときは各モジュールの保存関数が失敗する場合があります。初期スキーマのセットアップ手順（別途スキーマ初期化関数がある場合）を確認してください（audit 用の init_audit_db は本リポジトリに含まれています）。
- セキュリティ: news_collector は SSRF 対策（ホストプライベート判定、リダイレクト検査）、XML パース安全化（defusedxml）などを行っています。RSS ソースは信頼できるものを使用してください。
- テスト / CI: 自動 env ロードを無効化したいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## サポート / 貢献

バグ報告や機能改善の提案は Issue を作成してください。Pull Request の際はユニットテストと軽量の統合テスト（外部 API 呼び出しはモック）を付けることを推奨します。

---

README は以上です。必要であればセットアップコマンドの具体化（pyproject.toml や requirements.txt の内容に合わせたインストール手順）、あるいは各モジュール（ETL スキーマ初期化やテーブル定義）のサンプルスクリプトを追記できます。どの部分の詳細が欲しいか教えてください。