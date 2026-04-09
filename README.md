# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群

---

## プロジェクト概要

KabuSys は日本株を対象としたデータ収集・品質管理・ファクター開発・AI ベースのニュースセンチメント・監査ログ・ETL パイプラインを提供する Python パッケージです。  
主に以下の目的を想定しています：

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への保存（ETL）
- ニュース記事収集と LLM による銘柄別センチメント付与
- ETF / マクロニュースを組み合わせた市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 発注〜約定までを追跡する監査ログスキーマ（DuckDB）

パッケージはモジュール単位で設計され、バックテスト環境・運用環境のいずれにも組み込みやすいようフェイルセーフやルックアヘッドバイアス対策が施されています。

---

## 主な機能一覧

- data:
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・レートリミット・保存関数）
  - market_calendar 管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - ニュース収集モジュール（RSS -> raw_news、SSRF対策、前処理）
  - 監査ログスキーマ初期化（audit テーブル群・index）
  - 統計ユーティリティ（z-score 正規化）
- ai:
  - news_nlp.score_news: ニュースを銘柄ごとに LLM で評価して ai_scores に書込
  - regime_detector.score_regime: ETF（1321）MA200 乖離とマクロニュースの LLM 評価を合成して market_regime に書込
  - LLM 呼び出しは OpenAI SDK（gpt-4o-mini 想定）を使用し、リトライ・フォールバックを実装
- research:
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC 計算、ファクター統計サマリ
- config:
  - .env ファイル・環境変数の自動読み込み（.env, .env.local、OS 環境変数保護）
  - Settings クラスでアプリ設定を集中管理

---

## 要求事項 / 依存

主に以下を想定しています（本コードベースに依存記述ファイルは含まれていないため、必要に応じて追加してください）：

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （ネットワークアクセス：J-Quants API, 各 RSS ソース, OpenAI）

推奨インストール例（pip）：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを開発モードでインストールしている場合:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンしてワークツリーへ移動
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
4. DuckDB ファイルや SQLite（監視用）のディレクトリを作成（必要なら）

重要な環境変数（主要なものを抜粋）:

- J-Quants / データ関連
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- kabu ステーション（発注用）
  - KABU_API_PASSWORD: kabu API のパスワード（必須）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の引数に渡すことも可能）
- その他
  - DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
  - PAPER_FILL_MODE: paper trading の fill モード（instant | partial | never | reject、デフォルト: instant）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START（監視系）

例 `.env`（最小）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（よく使う API と例）

以下はライブラリを直接インポートして利用する簡単な例です。いずれも duckdb の接続オブジェクトを渡して使います。

1) 日次 ETL 実行（株価・財務・カレンダー取得／品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を None にすると今日（システム日）を対象に処理を行います
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（前日 15:00 JST ～ 当日 08:30 JST の記事を対象に銘柄別スコアを ai_scores テーブルへ書く）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
print(f"書き込み銘柄数: {n_written}")
```
※ api_key を None にすると環境変数 OPENAI_API_KEY を参照します。

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成して market_regime に保存）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数を使用
```

4) 監査ログ DB の初期化（監査専用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンも設定されます
```

5) 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# レコードは list[dict] 形式（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

注意点:
- LLM に関わる関数は API エラー時にフェイルセーフで 0 や空結果にフォールバックします。テストでは内部の _call_openai_api をモックしてください。
- time / date の扱いはルックアヘッドバイアスを防ぐため target_date ベースで設計されています。datetime.today() などを直接参照しないことに留意してください。

---

## よくある運用フラグ

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - パッケージインポート時の .env 自動読み込みを無効化（テストやコンテナ化環境で便利）
- PAPER_FILL_MODE
  - paper_trading 環境でのモック約定挙動を制御（instant/partial/never/reject）
- KABUSYS_ENV
  - 環境（development / paper_trading / live）を指定

---

## ディレクトリ構成

パッケージ内部の主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py
    - jquants_client.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult 再エクスポート)
    - etl.py (ETL API)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py exports: calc_momentum, calc_value, calc_volatility, zscore_normalize 等
  - その他（strategy, execution, monitoring 等の名前空間が __all__ に含まれますが、ここに示した以外のモジュールは別ファイルで定義されます）

（上記は主要モジュールの抜粋です。実際のリポジトリではさらに補助モジュールやテストが存在する可能性があります）

---

## 開発・テスト

- LLM / ネットワーク呼び出しはテストでモックしやすいように設計されています（内部の _call_openai_api や jquants_client._request, news_collector._urlopen などを patch して差し替え）。
- DuckDB を ":memory:" 指定してインメモリ DB を作成し、単体テストを行うことが可能です。

---

## 注意事項 / セキュリティ

- RSS フィード取得は SSRF 対策（ホスト検査、リダイレクト検査）を実装していますが、運用時は取り込むソースを制限してください。
- API キー・シークレットは常に安全に管理し、公開リポジトリに含めないでください。
- ETL / 発注部分は実運用でのテストと検証が必要です。paper_trading モードを活用して十分に検証してください。

---

以上が KabuSys の簡易 README です。必要であれば以下を追加で作成します：

- .env.example のテンプレート
- 具体的な SQL スキーマ（テーブル定義抜粋）の節
- CI / デプロイ手順（systemd / cron / Docker など）
- API リファレンス（関数・戻り値の詳細）

どれを優先して追加しますか？