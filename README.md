# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリセットです。  
データ取得（J-Quants）、ETL、データ品質チェック、研究用ファクター計算、ニュースの NLP スコアリング、そして監査（オーダー/約定）テーブル管理などを含みます。

## 主要な特徴
- J-Quants API 経由での差分取得（株価日足・財務・カレンダー）と DuckDB への冪等保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別スコア）および市場レジーム判定
- 研究用モジュール（モメンタム・バリュー・ボラティリティ等のファクター計算、将来リターン、IC計算、Zスコア正規化）
- 監査ログ（signal / order_request / execution）用のスキーマ初期化ユーティリティ
- 環境変数ベースの設定管理（.env/.env.local をプロジェクトルートから自動読み込み）

---

## 要件（例）
- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装された部分も多い）

※ 実際の依存は pyproject.toml / requirements.txt を参照してください（本リポジトリに含まれる想定）。

---

## セットアップ

1. 仮想環境を作る（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ ローカルの pyproject.toml / requirements.txt がある場合はそちらを使用してください:
   ```
   pip install -e .
   ```

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として必要な環境変数を置くと、自動的に読み込まれます。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 必須・推奨の環境変数

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注機能利用時）

- 任意 / デフォルトあり
  - OPENAI_API_KEY          : OpenAI API キー（news_nlp / regime_detector で使用）
  - KABUSYS_ENV            : 環境名（development / paper_trading / live）デフォルト: development
  - LOG_LEVEL              : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）, デフォルト: INFO
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知の設定
  - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - PAPER_FILL_MODE        : paper trading の fill 動作（instant|partial|never|reject）, デフォルト: instant
  - PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH 等（実行監視用）

設定値は以下のようにコードから参照できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## 使い方（基本例）

以下はライブラリの代表的な呼び出し例です。DuckDB 接続を作って各ユーティリティを呼び出します。

- DuckDB 接続準備（デフォルトパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を明示することが Look-ahead バイアス防止に役立ちます
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュース NLP（銘柄別スコア）を実行
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数に設定しておくか、api_key に渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written rows:", n_written)
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ初期化（監査用 DB を別途用意することも可能）
```python
from kabusys.data.audit import init_audit_db

# 監査ログ専用の DuckDB を初期化して接続を取得
audit_conn = init_audit_db("data/audit.duckdb")
```

- 研究用関数例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

momentum = calc_momentum(conn, date(2026,3,20))
forward = calc_forward_returns(conn, date(2026,3,20), horizons=[1,5,21])
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
```

- カレンダー関係ユーティリティ例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date

d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

---

## 自動環境変数読み込みの挙動
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動読み込みします。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主要ファイル）
プロジェクトのルートに `src/kabusys` があり、主要モジュールは次のとおりです。

- kabusys/
  - __init__.py
  - config.py                             — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                          — ニュースの集約・OpenAI を使った銘柄別スコアリング
    - regime_detector.py                   — マーケットレジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py                    — J-Quants API クライアント & DuckDB 保存処理
    - pipeline.py                          — ETL 実装（run_daily_etl 等）
    - etl.py                               — ETL インターフェース（ETLResult 再エクスポート）
    - quality.py                           — データ品質チェック
    - stats.py                             — 共通統計ユーティリティ（zscore_normalize）
    - calendar_management.py               — 市場カレンダー管理 / 営業日ロジック
    - news_collector.py                     — RSS 収集、前処理、SSRF 対策等
    - audit.py                              — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py                   — Momentum / Value / Volatility 等
    - feature_exploration.py               — 将来リターン / IC / 統計サマリー
  - researchパッケージは data.stats と組み合わせて使います

（上記は本 README に含まれるサンプル実装群に基づく主要ファイル一覧です）

---

## 開発メモ / 注意事項
- Look-ahead バイアス防止: 多くの関数は内部で date.today() 等を参照せず、caller が target_date を与える設計です。バックテスト用途では target_date 指定を徹底してください。
- OpenAI API 呼び出しにはリトライやフォールバックロジックを組んでいますが、API キーの管理・コストに注意してください。
- J-Quants API の呼び出しはレートリミットを考慮した実装が組み込まれています（120 req/min）。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、実装側で空チェックを行っています。
- news_collector は SSRF 対策（ホスト/リダイレクト検査）や XML パースの安全化（defusedxml）を行っています。

---

## さらに
- 実運用では監視（プロセス監視、kill フラグ、PID ファイル等）やログ設定（LOG_LEVEL）を適切に設定してください。
- 発注周り・実際のブローカー連携は別モジュール（execution 等）で実装される想定です。本リポジトリの一部はデータ基盤・研究基盤側の実装を中心にしています。

---

ご不明な点や README に追加したい具体的な使用例（スクリプト、CI、ローカル開発フロー等）があれば教えてください。README に追記して反映します。