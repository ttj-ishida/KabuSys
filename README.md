# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。  
市場データの ETL、ニュースの収集・NLP スコアリング、ファクター計算、監査ログ定義、そして戦略評価に必要なユーティリティ群を提供します。

現在のバージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を想定したモジュール群を持つ Python パッケージです。

- J-Quants API を利用した株価・財務・カレンダーの差分 ETL
- DuckDB を用いたデータ保存・集計
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント・マクロセンチメント評価
- 市場レジーム判定（ETF MA と LLM スコアを合成）
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算＆探索用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → executions）のテーブル定義・初期化ユーティリティ

設計上の特徴:
- ルックアヘッドバイアス防止（内部処理が現在時刻を不用意に参照しない設計）
- 冪等性を重視した DB 保存（ON CONFLICT での上書き）
- API リトライ・バックオフ・レートリミット対応
- テスト容易性：依存関数の差し替えを想定した分離設計

---

## 主な機能一覧

- Data
  - ETL パイプライン: daily ETL（prices, financials, calendar）
  - J-Quants クライアント: 認証（refresh → id token）、ページネーション対応取得、DuckDB 保存
  - カレンダー管理: 営業日判定、next/prev_trading_day、calendar_update_job
  - ニュース収集: RSS 取得、前処理、raw_news への保存、SSRF 対策
  - データ品質チェック: missing, duplicates, spike, date consistency
  - 監査ログスキーマ初期化（audit DB）
  - 統計ユーティリティ: zscore 正規化 等
- AI
  - ニュース NLP スコアリング（銘柄ごとの ai_score を ai_scores テーブルへ保存）
  - マクロセンチメント + ETF MA を合成した市場レジーム判定（market_regime テーブルへ保存）
- Research
  - ファクター計算: momentum, value, volatility
  - 特徴量探索: forward returns, IC 計算, 統計サマリー、rank 等
- 設定管理
  - 環境変数/.env の自動読み込み（プロジェクトルート検出）と Settings クラス

---

## セットアップ手順

前提:
- Python 3.10+（型ヒント Union | を使用）
- DuckDB、openai、defusedxml 等が必要

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール（例）
   pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して `pip install -e .` や `pip install -r requirements.txt` を使用してください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）に `.env` / `.env.local` を配置できます。
   - 自動ロードはデフォルトで有効。無効化する場合は環境変数:
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（ETL に必須）
- KABU_API_PASSWORD : kabuステーション API 用パスワード（発注・接続で使用）
- OPENAI_API_KEY : OpenAI を使う場合に必要（news_nlp / regime_detector）
その他（省略可能・デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_FILL_MODE (instant | partial | never | reject) default "instant"
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live) default "development"
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) default "INFO"

環境変数は .env/.env.local の形式で自動読み込みされます（OS 環境変数 > .env.local > .env の優先順位）。.env 読み込みはプロジェクトルートを .git または pyproject.toml から検出します。

---

## 使い方（主な例）

以下はライブラリをインポートして使う際の簡単な例です。詳細は各モジュールの docstring を参照してください。

1) DuckDB 接続を作成して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path のデフォルトと一致
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアリング（OpenAI API キー必要）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（OpenAI API キー必要）

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ DB 初期化（監査専用 DuckDB を作る）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブル群が作成され、UTC タイムゾーンに設定されます
```

5) ファクター・リサーチ系の利用例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

ログ・エラー処理:
- 各モジュールは logging を使って情報・警告・エラーを出力します。実行環境でロガー設定（ハンドラ・フォーマット）を行ってください。

注意:
- AI 関連関数は OPENAI_API_KEY または api_key 引数を必須とします。未設定時は ValueError が発生します。
- ETL / データ保存関数は冪等性を持つよう設計されていますが、本番運用前にバックアップを取る等の運用ルールを推奨します。

---

## ディレクトリ構成（抜粋）

パッケージルート: src/kabusys/

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースの LLM スコアリング、ai_scores への書き込み
    - regime_detector.py            — MA と LLM を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL の公開インターフェース（ETLResult エクスポート）
    - news_collector.py             — RSS 取得・前処理・SSRF 対策
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility 等の計算
    - feature_exploration.py        — forward returns / IC / summary / rank 等
  - research/（公開APIでまとめられている各関数）
- その他: .env / .env.local / pyproject.toml 等（プロジェクトルート）

---

## 開発・運用に関する注意事項

- .env 自動読み込み: settings モジュールは実行時にプロジェクトルートを探索して .env/.env.local を読み込みます。テストで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しの扱い: news_nlp と regime_detector は JSON mode を利用し、レスポンスのバリデーションやリトライを実装しています。API エラー時はフェイルセーフでスコアを 0.0 にフォールバックする実装が多く含まれますが、実運用ではレート制限・コスト管理を必ず行ってください。
- DuckDB の互換性: 一部実装は DuckDB のバージョン差分（executemany の空リスト扱い等）への配慮があります。DuckDB バージョン依存の挙動に注意してください。
- セキュリティ: news_collector は SSRF 対策、defusedxml による XML 脆弱性対策、トラッキングパラメータの除去等を行っていますが、実装や外部フィードの信頼性を踏まえた追加の監視を推奨します。
- バックテスト運用: Look-ahead bias を避ける設計が随所に施されています。バックテストを行う際はデータの取り込みタイミング（fetched_at）やスキーマに注意して下さい。

---

必要に応じて README にサンプル .env.example、運用手順（cron ジョブ例、監視・再起動方法）、CI/test の設定例を追加できます。追加したい項目があれば教えてください。