# KabuSys

日本株向け自動売買／データ基盤ライブラリ「KabuSys」のリポジトリ用 README（日本語）。

このドキュメントはコードベース（src/kabusys 以下）をもとに作成しています。実装済みの主要機能、セットアップ手順、使い方例、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムとそのデータ基盤・研究ツール群を提供する Python パッケージです。主に以下を目的としています。

- J-Quants API などから市場データ（株価・財務・市場カレンダー・銘柄一覧等）を取得・ETL する機能
- ニュースの収集・NLP による銘柄別センチメントスコア算出（OpenAI を利用）
- 市場レジーム判定（ETF の移動平均乖離 + マクロニュース）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- データ品質チェック、監査ログ（signal → order → execution のトレーサビリティ）
- kabuステーション 等の実売買モジュール（骨格）

設計上の特徴：
- DuckDB をデータレイクとして利用（ローカルファイルやインメモリ）
- Look-ahead バイアス防止を考慮した日次境界処理
- API 呼び出しに対する堅牢なリトライとレート制御
- .env / 環境変数に基づく設定管理（自動読み込み機能あり）

---

## 主な機能一覧

- data パッケージ
  - ETL パイプライン（差分取得 / 保存 / 品質チェック）：kabusys.data.pipeline.run_daily_etl 等
  - J-Quants クライアント（取得 + DuckDB へ冪等保存）：kabusys.data.jquants_client
  - ニュース収集（RSS → raw_news）：kabusys.data.news_collector
  - マーケットカレンダー管理（営業日判定 / カレンダー更新ジョブ）：kabusys.data.calendar_management
  - データ品質チェック：kabusys.data.quality
  - 監査ログスキーマ初期化：kabusys.data.audit.init_audit_db / init_audit_schema
  - 汎用統計ユーティリティ：kabusys.data.stats.zscore_normalize

- ai パッケージ
  - ニュース NLP（銘柄別センチメントを OpenAI により算出）：kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM 評価）：kabusys.ai.regime_detector.score_regime

- research パッケージ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）：kabusys.research.factor_research
  - 特徴量探索（将来リターン計算 / IC / 統計サマリー）：kabusys.research.feature_exploration
  - zscore 正規化ユーティリティを再エクスポート

- 設定管理
  - 環境変数・.env の自動読み込みと Settings オブジェクト：kabusys.config.settings

---

## 動作環境 / 依存

必須：
- Python 3.10 以上（型アノテーションで X | Y 構文を使用）
- duckdb
- openai
- defusedxml

推奨（用途に応じて）：
- その他ネットワーク関連や標準ライブラリのみで動作する部分が多いですが、実運用では systemd / supervisor などでプロセス管理、監視を行ってください。

例（仮想環境作成・インストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発インストール（setup があれば）
# pip install -e .
```

（パッケージの正式要件は requirements.txt / pyproject.toml を参照してください）

---

## 設定（環境変数 / .env）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動読み込みは、パッケージ内でプロジェクトルート（.git または pyproject.toml）を探索して行われます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

主要な環境変数一覧（config.Settings が参照）：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 監視制御用
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）

例：`.env.example`
```env
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# DB paths
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（最小）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   ```bash
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   # 追加パッケージがある場合は requirements.txt を使用
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env` を作成するか、環境変数を設定する。
   - 認証トークン（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定。

5. DuckDB 初期化（任意：監査ログ用 DB を作る場合）
   - Python から：
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - またはメイン ETL が接続時に必要テーブルを作成するような初期化処理を用意してください。

---

## 使い方（例）

以下は主要なモジュールの簡単な利用例です。適宜 logging を設定し、環境変数を与えて実行してください。

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアの取得（ai.news_nlp）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数で設定するか、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ai.regime_detector）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用途：ファクター計算 / forward returns / IC
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- 監査ログスキーマ初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル（signal_events, order_requests, executions）が作成されます
```

注意点：
- ai モジュールは外部 OpenAI API を呼びます。API キーとレート制限に注意してください。
- J-Quants API 関連は認証トークン（JQUANTS_REFRESH_TOKEN）を必須とします。
- ETL / API 呼び出しはネットワーク・レート制限・例外処理を含むため、運用時はログと再試行戦略を用意してください。

---

## ディレクトリ構成（主要ファイルと説明）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
    - パッケージ初期化。公開サブパッケージを定義。
  - config.py
    - 環境変数・.env の自動読み込みと Settings オブジェクト定義。
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に書き込むロジック。
    - regime_detector.py
      - ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成し market_regime テーブルへ書き込む。
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API との通信・ページネーション・リトライ・DuckDB への保存ロジック（raw_prices/raw_financials/market_calendar 等）。
    - pipeline.py
      - 日次 ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl など）。
    - news_collector.py
      - RSS フィード取得・前処理・raw_news への保存（SSRF 対策、XML 防護など）。
    - calendar_management.py
      - market_calendar の管理、営業日判定や更新ジョブ。
    - quality.py
      - データ品質チェック（欠損、重複、スパイク、日付不整合）。
    - stats.py
      - z-score 正規化等の統計ユーティリティ。
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）の DDL と初期化機能。
    - etl.py
      - ETLResult の公開再エクスポート。
  - research/
    - __init__.py
    - factor_research.py
      - Momentum, Value, Volatility 等のファクター計算関数。
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク化ユーティリティ。
  - ai/（上で記載）
  - research/（上で記載）

---

## 運用上の注意 / ヒント

- 環境（KABUSYS_ENV）が `live` の場合は実発注等に接続する可能性があるため、設定やパスワードの管理に充分注意してください。
- OpenAI 呼び出しはコストが発生します。API キー管理とレート制御（モジュール内部にも対応あり）を行ってください。
- DuckDB ファイルのバックアップ、監査ログの保全を運用ルールで定めてください。
- 自動 .env ロードはプロジェクトルート検出に依存します。テスト等で無効化する際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。
- テストを書く際はネットワーク呼び出し（OpenAI / J-Quants / RSS）をモックすることを推奨します。ライブラリ内でモックしやすいように呼び出し箇所の関数を分離してあります。

---

以上がコードベースに基づく README の内容です。必要であれば実例スクリプト、CI 設定、requirements ファイルの提案や README の英語版作成も対応します。