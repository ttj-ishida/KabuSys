# KabuSys

KabuSys は日本株のデータ基盤・リサーチ・自動売買に必要なユーティリティ群を提供するライブラリです。J-Quants / kabuステーション / OpenAI 等と連携してデータ取得、ETL、ニュース NLP、ファクター計算、監査ログ、マーケットカレンダー管理などの機能を備えます。

主な設計方針：
- ルックアヘッドバイアス（未来データ参照）を厳格に防止
- DuckDB を中心としたオンプレ・軽量データベース設計
- API 呼び出しに対する堅牢なリトライ・フェイルセーフ実装
- ETL/保存処理は冪等（idempotent）を意識した実装

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得・保存、ページネーション、トークン自動リフレッシュ、レート制御）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 取得・前処理・SSRF 対策・記事 ID 正規化）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ DB 初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP による銘柄別センチメントスコア生成（score_news）
  - マクロニュースと ETF の MA を組み合わせた市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini 等）呼び出しのラップ（JSON mode）とリトライ制御
- research
  - ファクター計算（momentum / volatility / value 等）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリー、ランク化など）
- config
  - .env / 環境変数の自動読み込みと設定ラッパー（Settings）

注：strategy / execution / monitoring パッケージ用の名前空間は公開されていますが、本リポジトリに含まれる機能は上記が中心です（発注実行周りは実装方針に準拠）。

---

## 必要要件

- Python 3.10+
- 依存主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

実装によりさらに標準ライブラリ以外の依存がある場合があります。セットアップ時に pip または poetry でインストールしてください。

---

## インストール

ローカル開発用（pip editable）例:

```bash
# プロジェクトルートで
pip install -e ".[dev]"   # setup があれば extras で dev 依存を入れてください
# または必要な依存のみ
pip install duckdb openai defusedxml
```

パッケージが pyproject.toml / setup.py を含む場合はそれに従ってください。

---

## 環境変数 / 設定 (.env)

パッケージ起動時にルート（.git / pyproject.toml の親）から自動で `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に利用する環境変数（必須は読み出し時に ValueError が発生します）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- kabuステーション
  - KABU_API_PASSWORD : kabu API のパスワード（必須）
  - KABU_API_BASE_URL : kabu API の base URL（省略時 default http://localhost:18080/kabusapi）
- OpenAI / AI
  - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime 等で必須）
- Slack
  - SLACK_BOT_TOKEN : Slack ボットトークン（必須）
  - SLACK_CHANNEL_ID : 通知先チャンネル ID（必須）
- DB パス等
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH : SQLite path（監視用、デフォルト data/monitoring.db）
- 動作モード / ログ
  - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
  - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

.env の書式はコメント行、export プレフィックス、クォート（シングル/ダブル）などに対応しています。詳しくは kabusys.config の _parse_env_line 実装を参照してください。

---

## クイックスタート・使い方

以下は基本的な利用例（Python スクリプトや REPL）です。DuckDB 接続は duckdb.connect(path) を使います。

1) ETL の実行（デイリー ETL）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントスコアを生成（OpenAI API 必須）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
print(f"scored {n} symbols")
```

3) 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
```

4) 監査ログ DB 初期化（約定/発注トレース用）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_duckdb.db")
# conn は初期化済みの DuckDB 接続
```

5) 市場カレンダーの判定・取得

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

注意点:
- score_news / score_regime は OpenAI API を利用します。API キー未設定時は ValueError が発生します。
- ETL/API 呼び出しはネットワーク・レート制限を考慮して設計されていますが、実行環境でのレート制御やキー管理には注意してください。
- データ保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行われます。部分失敗時のデータ保護ロジックも組み込まれています。

---

## 開発者向けノート / 安全対策

- lookahead-bias 回避: 各種処理で datetime.today() / date.today() の直接参照を避け、関数引数で基準日を与える実装になっています。
- API 呼び出し: J-Quants / OpenAI 周りは指数バックオフ・リトライ、429/5xx の取り扱い、401 のトークン自動更新（J-Quants）などが実装されています。
- ニュース収集: RSS の SSRF 対策（リダイレクト検査・プライベートホスト拒否）、受信サイズ上限、XML パースの安全ライブラリ（defusedxml）を採用。
- データ品質: ETL 後に品質チェックを実行し、欠損・スパイク・重複・日付不整合を検出する仕組みがあります。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと目的の一覧です（コードベースから抜粋）。

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py  — 市場カレンダー管理
    - etl.py                  — ETL インターフェース再エクスポート
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログテーブル初期化 / init_audit_db
    - jquants_client.py       — J-Quants API クライアント（fetch/save 系）
    - news_collector.py       — RSS ニュース収集・前処理
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（mom, volatility, value）
    - feature_exploration.py  — 将来リターン計算・IC・統計サマリー

各モジュールにはドキュメント文字列（docstring）で設計方針・処理フロー・注意点が詳述されています。実装の詳細や追加ユーティリティはソースをご参照ください。

---

## 貢献 / 開発

- バグ報告・機能追加は issue を立ててください（プロジェクト管理ポリシーに従ってください）。
- ローカルで開発する際は .env を作成後、必要な依存をインストールしてから実行してください。
- 自動環境変数読み込みをテストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

README に記載のない詳細（API の戻り値形式やテーブルスキーマ等）は、モジュールの docstring／関数定義コメントを参照してください。追加の説明やサンプルが必要であればどの部分を詳述するか教えてください。