# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys の README。  
このリポジトリは、データ取得（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュースの NLP スコアリング（OpenAI を利用）、市場レジーム判定、監査ログ管理などを統合した内部ライブラリ群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究用プラットフォームの基盤モジュール群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等の差分取得と DuckDB への冪等保存（ETL）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース記事の収集と LLM による銘柄センチメント算出（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの融合）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ生成

設計上の特徴:
- Look-ahead bias を回避するため、内部ロジックは明示的な target_date を受け取る設計。
- DuckDB を中核 DB とし、ETL は差分取得＋バックフィルで堅牢に更新。
- 外部 API 呼び出しはレート制御・リトライ・フェイルセーフを実装。
- OpenAI 呼び出しは JSON モードで厳密な出力を期待し、例外時はフェイルセーフ（スコア 0 等）で継続。

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / 認証・トークン管理）
  - pipeline: 日次 ETL（株価 / 財務 / カレンダー）と ETL 結果管理（ETLResult）
  - quality: 品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - news_collector: RSS を用いたニュース収集（SSRF 対策、正規化）
  - calendar_management: 市場カレンダー管理 / 営業日判定 / バッチ更新
  - audit: 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
  - stats: Zスコア正規化など汎用統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースを LLM で銘柄別センチメントに変換し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを組合せて市場レジーム判定
- research
  - factor_research: calc_momentum, calc_value, calc_volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等
- config
  - 環境変数読み込み（.env / .env.local を自動読込。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由で設定値を提供

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントの union 表記 (X | Y) を使用）
- DuckDB を利用（duckdb パッケージ）
- OpenAI を利用する機能は OpenAI SDK（openai）が必要
- RSS パースに defusedxml を利用

例: 仮想環境作成と依存関係インストール（requirements.txt が無い場合の例示）

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 必要に応じて他ライブラリを追加
```

パッケージを開発モードでインストールする（setuptools が用意されている場合）:

```bash
pip install -e .
```

環境変数／.env
- プロジェクトルートに `.env` / `.env.local` を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 主な環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabu API のパスワード（必須）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
  - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
  - DUCKDB_PATH: データベースファイル path（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 sqlite path（デフォルト data/monitoring.db）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意: config モジュールは .git または pyproject.toml を基準にプロジェクトルートを探索します。

---

## 使い方（主な API と実行例）

基本的に各機能はモジュールの関数を直接呼び出す方式です。DuckDB 接続は呼び出し側で用意して渡します。

共通の準備:

```python
from kabusys.config import settings
import duckdb
from datetime import date

# DuckDB ファイルを settings から取得
conn = duckdb.connect(str(settings.duckdb_path))
today = date.today()
```

日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）:

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=today)
print(result.to_dict())
```

ニュースのセンチメントスコア算出（OpenAI 必須）:

```python
from kabusys.ai.news_nlp import score_news

# target_date に対して前日15:00 JST ～ 当日08:30 JST のニュースを対象に分散集計し ai_scores に書き込む
n_written = score_news(conn, target_date=today)
print(f"書き込み件数: {n_written}")
```

市場レジーム判定（1321 の MA とマクロニュースで判定、OpenAI 必須）:

```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=today)
```

監査ログスキーマ初期化（監査用 DB を独立させたい場合）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# もしくは既存 conn に対して init_audit_schema(conn)
```

研究用ファクター計算例:

```python
from kabusys.research.factor_research import calc_momentum

mom = calc_momentum(conn, target_date=today)
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- OpenAI 呼び出しを含む関数は api_key 引数を受け取れる（None の場合は環境変数 OPENAI_API_KEY を参照）。テスト時は内部の API 呼び出しをモック可能に設計されています。
- run_daily_etl 等は内部で例外を捕捉して継続する箇所があり、ETLResult にエラー情報を収集します。致命的な失敗は ETLResult.errors や has_errors で確認してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 配下に配置されています。主要ファイルと役割は以下の通り。

- src/kabusys/__init__.py
  - パッケージのエントリ。バージョン情報を含む。
- src/kabusys/config.py
  - 環境変数管理・settings オブジェクト（.env 自動読み込み・検証）
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py: ニュースの LLM ベースセンチメント解析・ai_scores 書き込み
  - regime_detector.py: ETF MA とマクロニュースで市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得／保存／認証）
  - pipeline.py: ETL 実行（run_daily_etl 等）と ETLResult
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector.py: RSS 収集（SSRF・XML 防御・ID 生成）
  - calendar_management.py: 市場カレンダー管理／営業日判定／calendar_update_job
  - audit.py: 監査ログ用スキーマ定義・初期化（signal_events / order_requests / executions）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - etl.py: ETLResult の再エクスポートインターフェース
- src/kabusys/research/
  - __init__.py
  - factor_research.py: momentum/value/volatility の計算
  - feature_exploration.py: 将来リターン / IC / 統計サマリ / ランク関数

（注）news_collector.py の RSS 読み取り部にはレスポンスサイズ制限・SSRF 防御・XML トラスト対策が実装されています。

---

## テスト・開発上のヒント

- config の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして無効化できます。単体テストでは環境依存を切るために便利です。
- OpenAI を使う箇所は内部で _call_openai_api を呼び出すため、ユニットテストでは patch によりモック可能です（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- J-Quants API 呼び出しも jquants_client._request をモックすることで API 依存を排除できます。get_id_token は settings.jquants_refresh_token を参照します。
- DuckDB の executemany に空のパラメータを渡すと問題になるバージョンがあるため、コード内で空チェックが行われています。テストでの DuckDB バージョンに注意してください。

---

## ライセンス・貢献

（この README はサンプルです。実際のライセンスや貢献ルールがある場合はプロジェクトの LICENSE / CONTRIBUTING を参照してください。）

---

以上が KabuSys の概要と基本的な使い方です。必要であれば、各モジュールの詳細な API 仕様やサンプルワークフロー（ETL スケジューリング、戦略→発注→監査ログの例）を追記します。どの部分を詳しく知りたいか教えてください。