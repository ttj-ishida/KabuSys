# KabuSys

日本株向けの自動売買/データ基盤ライブラリ。J-Quants / DuckDB を中心としたデータ取得・ETL、ニュース/NLP による銘柄センチメント評価、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）などを提供します。

---

## 概要

KabuSys は以下の用途を想定した Python モジュール群です。

- J-Quants API からの株価/財務/カレンダー等の差分 ETL
- DuckDB を用いたローカルデータベース保存（冪等保存）
- ニュース収集および OpenAI を利用したニュースセンチメント（銘柄別）解析
- 相場レジーム判定（ETF + マクロニュースの合成）
- ファクター計算・リサーチユーティリティ（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（signal → order_request → executions のトレーサビリティ）

設計方針としては「ルックアヘッドバイアスを防ぐ」「DuckDB への冪等保存」「外部 API に対する堅牢なリトライ/レート制御」「フェイルセーフで継続できる実装」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得 + 保存関数、トークン自動リフレッシュ、レート制限）
  - market_calendar 管理（営業日判定 / next/prev_trading_day / calendar_update_job）
  - news_collector（RSS 取得・前処理・SSRF 対策）
  - quality（欠損・スパイク・重複・日付不整合のチェック）
  - audit（監査ログスキーマの初期化 / init_audit_db）
  - stats（zscore_normalize など）
- ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約して OpenAI でスコア化し ai_scores に書き込む
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュースの LLM スコアを合成して market_regime に書き込む
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理
  - kabusys.config.settings を通じた環境変数ベースの設定取得（.env 自動ロード機能あり）

---

## セットアップ

前提
- Python 3.10 以上（モジュール内で | 型やパターンを使用）
- 推奨ライブラリ（最低限）:
  - duckdb
  - openai
  - defusedxml

例: pip でインストールする最小依存
```bash
pip install duckdb openai defusedxml
```

推奨: 仮想環境を作成してからインストールしてください。

.env 設定
- プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（ルート判定は `.git` または `pyproject.toml` を探索）。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

重要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行に必須）
- KABU_API_PASSWORD: kabu API パスワード（発注関連で使用）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / ai.score_regime 実行に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment (development / paper_trading / live)（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

サンプル .env（例）
```
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易例）

基本的に DuckDB 接続を取得して各関数に渡して使用します。

1) ETL（日次 ETL 実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```
- J-Quants トークンは settings.jquants_refresh_token（.env 経由）または引数で注入可能。
- run_daily_etl は calendar → prices → financials → 品質チェック の順に実行し ETLResult を返します。

2) ニューススコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None で環境変数 OPENAI_API_KEY を使用
print("書き込んだ銘柄数:", written)
```

3) 市場レジーム判定（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path
from kabusys.config import settings

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# または settings.duckdb_path を使う（用途に応じて別 DB を推奨）
```

5) 設定取得
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.is_live, settings.jquants_refresh_token)
```

ログ・環境
- KABUSYS_ENV（development / paper_trading / live）により動作モードを判定する関数が settings にあります（is_dev, is_paper, is_live）。
- LOG_LEVEL でログレベルを制御してください。

注意点
- AI 機能（score_news, score_regime）は OpenAI API の呼び出しを行います。API 制限やコストに注意してください。
- J-Quants API はレート制限/認証トークンが必要です。get_id_token により自動取得・更新が行われます。
- 各種関数は「ルックアヘッドバイアスを防ぐ」設計になっており、内部で date.today() 等を勝手に参照しないものが多いです（target_date を明示してください）。

---

## ディレクトリ構成（主要ファイル）

以下はコードベース内の主要モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動読込、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等、ETLResult）
    - etl.py                — ETLResult の再エクスポート
    - news_collector.py     — RSS 収集・前処理（SSRF 対策、記事正規化）
    - calendar_management.py — 市場カレンダー（is_trading_day / next_trading_day 等）
    - quality.py            — データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py    — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

（各モジュール内でさらに細かな関数や定数が定義されています。README は全体像の案内として参照してください。）

---

## 開発・貢献

- コードはモジュール単位でテストしやすい設計（外部呼び出しを注入可能、API 呼び出し関数を差し替え可能）となっています。
- .env.example を用意して環境変数の雛形を共有してください（本リポジトリ内にない場合は上のサンプルを参照）。
- 自動ロードの挙動を無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 参考・補足

- DuckDB への INSERT は可能な限り ON CONFLICT / executemany を用いた冪等保存を行っていますが、DuckDB のバージョン差（executemany の空リスト禁止など）に注意が必要です。
- OpenAI 呼び出しは JSON Mode を利用する想定で、レスポンスのパース・バリデーションを厳密に行っています。API の変更により挙動が変わる場合は該当モジュールの調整が必要です。
- セキュリティ: news_collector は SSRF 対策・XML 脆弱性対策（defusedxml）を取り入れていますが、運用時は RSS ソース管理や HTTP タイムアウトなど適切に設定してください。

---

必要であれば、README をさらに詳細なインストール手順（依存バージョン固定用 requirements.txt の例）、サンプル .env.example、具体的なスキーマ（DuckDB の CREATE TABLE 文例）や運用手順（cron ジョブ例、監視の仕組み）を追加できます。どの情報を補完しましょうか？