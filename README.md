# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースNLP（OpenAI を使ったセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログスキーマなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・特徴量生成・AI ベースのニューススコアリング・市場レジーム判定・監査ログなど、アルゴリズム取引システムに必要な基盤機能を集約した Python パッケージです。主に以下用途を想定しています。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL
- RSS を用いたニュース収集と OpenAI による銘柄別センチメント付与
- ETF ベースの移動平均＋マクロニュースを用いた市場レジーム判定
- ファクター計算・将来リターン計算・IC 等のリサーチユーティリティ
- DuckDB を使った監査ログ（order/signals/executions）スキーマ初期化
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・リトライ・レート制御）
  - market_calendar 管理・営業日判定ユーティリティ
  - ニュース収集（RSS -> raw_news、SSRF 対策・トラッキングパラメータ削除）
  - データ品質チェック（missing / duplicates / spike / date_consistency）
  - 監査ログスキーマの作成・初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores テーブルへ）
  - 市場レジーム判定（score_regime: ETF MA とマクロニュースを合成）
  - OpenAI との呼び出しは再試行・フェイルセーフ実装。テスト時に差し替え可能な設計。
- research
  - ファクター計算（momentum, volatility, value）
  - feature_exploration（forward returns, IC, summary, rank）
- audit / monitoring / execution / strategy
  - パッケージ API としてエクスポートされる（プロジェクトの他コンポーネントと連携する想定）

---

## セットアップ手順

要求環境
- Python 3.10+（Union types、型ヒント表記を利用しているため）
- 推奨ライブラリ（最低限）:
  - duckdb
  - openai
  - defusedxml

例: 仮想環境作成とインストール
```bash
git clone <this-repo-url>
cd <this-repo-dir>

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install duckdb openai defusedxml
# または `pip install -e .`（パッケージ化されていれば）
```

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略可, デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack のチャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視関連
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

.env ロードについて
- パッケージは自動的にプロジェクトルート（.git または pyproject.toml を基準）を探し、`.env` と `.env.local` を読み込みます。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意: .env.example を参考に .env を作成してください（リポジトリに example がある想定）。

---

## 使い方（代表的な例）

以下は簡単な Python からの利用例です。すべて DuckDB 接続を受け取る設計になっています。

1) DuckDB に接続して日次 ETL を走らせる
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースをスコアリングして ai_scores テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数で設定しておくか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジームを判定して market_regime テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。テーブル群が作成されます。
```

5) 研究用ファクターを計算する
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

テスト用の差し替えポイント
- OpenAI 呼び出しはモジュール内の `_call_openai_api` を patch してモック可能（unittest.mock.patch など）。
- news_collector のネットワーク I/O は `_urlopen` を差し替えてテスト可能。

---

## ディレクトリ構成（抜粋）

（ソースは `src/kabusys/` に配置されています。主要ファイルを下に示します）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLU / OpenAI 呼び出し、ai_scores への書き込み
    - regime_detector.py      — ETF MA とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py       — J-Quants API クライアント（認証/取得/保存）
    - news_collector.py       — RSS 収集・前処理・raw_news 保存
    - calendar_management.py  — market_calendar 管理・営業日判定
    - quality.py              — データ品質チェック
    - stats.py                — 汎用統計（zscore_normalize 等）
    - audit.py                — 監査ログスキーマ作成 / init_audit_db
    - etl.py                  — パイプラインの型/再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — momentum / volatility / value の計算
    - feature_exploration.py  — forward returns / IC / summary / rank
  - ai/, research/ 以下にそれぞれのユーティリティ群
  - monitoring/, execution/, strategy/  — パッケージ公開対象として __all__ に含める（実際の実装は他ファイルで管理）

---

## 運用上の注意

- Look-ahead bias（未来情報の参照）を避ける設計が各モジュールに組み込まれています。target_date 引数を外部から与えることで、バックテスト時に過去日時での動作再現が可能です。
- OpenAI / J-Quants 呼び出しにはレート・リトライ制御やフェイルセーフがあるものの、API キー／料金に注意してください。
- news_collector は SSRF 対策、受信サイズ制限、XML の安全パーサ（defusedxml）を使用していますが、本番導入時はタイムアウトやソースの信頼性について追加検討を行ってください。
- DuckDB に対する executemany の空リスト渡しはバージョン依存で失敗するため、モジュール側でガードされています。DuckDB の互換性に注意してください。

---

## 開発・テスト

- ユニットテスト時はネットワーク呼び出しや OpenAI 呼び出しをモックしてください（各モジュールに差し替え点が用意されています）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。CI やユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して読み込みを制御してください。

---

必要であれば README に含めるサンプル .env.example、依存パッケージ一覧（requirements.txt）やより詳細な CLI/デーモン実行手順、docker / systemd での運用例も作成できます。どの形式の追加情報が必要か教えてください。