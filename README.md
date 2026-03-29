# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL・ニュース収集・AIによるニュースセンチメント／市場レジーム判定・リサーチ用ファクター計算・監査ログ管理など、取引基盤に必要な主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とする Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存（ETL）
- RSS ニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄単位）およびマクロセンチメント→市場レジーム判定
- ファクター計算・特徴量解析（モメンタム / バリュー / ボラティリティ 等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 取引フローの監査ログ（signal / order_request / execution）の初期化・管理

設計上の共通方針として、「ルックアヘッドバイアスの排除」「API 呼び出しの堅牢化（リトライ・バックオフ）」「DuckDB への冪等保存」「テスト容易性」を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存関数）
  - カレンダー管理（営業日判定・next/prev_trading_day）
  - ニュース収集（RSS 取得・正規化・raw_news 保存）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化（audit schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースをまとめて OpenAI に送り、ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースの LLM スコアを合成して market_regime に書き込む
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

※ 以下は開発環境の一例です。プロジェクトで必要な依存関係は setup.py/pyproject.toml にも記載されている想定です。

1. Python 仮想環境を作成して有効化:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. パッケージをインストール（編集可能インストール）:

   ```bash
   pip install -e .[dev]   # extras があれば適宜
   ```

3. 必要な OS 環境変数または .env ファイルを作成します（下記参照）。

4. DuckDB などランタイム依存がある場合はインストール済みであることを確認します（pip install duckdb 等）。

### 必須環境変数（主なキー）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

その他（デフォルト値あり／任意）:

- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作モード: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

.env ファイルの自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml の親）を探索し、`.env` と `.env.local` を自動読み込みします（OS 環境変数より低優先）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):

```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な利用例）

以下はライブラリを直接インポートして使う最小例です。実際にはエラーハンドリングやログ設定を追加してください。

- ETL を日次で実行する（DuckDB 接続を渡す）:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコア付与（score_news）:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB（audit）を初期化する:

```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# audit 用に別 DB を作る場合はパスを分けても良い
conn = init_audit_db(settings.duckdb_path)
# 以後 conn を使って監査ログテーブルを利用する
```

- リサーチ関数の利用例（ファクター計算 → 正規化 → 前方リターン → IC）:

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)

mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
ic = calc_ic(mom_z, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

---

## 実装上の注意点 / 設計ポリシー

- ルックアヘッドバイアス防止:
  - モジュール内では date.today() / datetime.today() を直接参照しない設計になっている箇所が多く、関数呼び出し側で target_date を与える想定です（バックテストに向く実装）。
- API 呼び出しの堅牢化:
  - J-Quants クライアント・OpenAI 呼び出しにはリトライ（指数バックオフ）やレート制限対策が組み込まれています。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE / INSERT ... ON CONFLICT を用いることで冪等保存を実現しています。
- セキュリティ対策:
  - ニュース収集で SSRF 対策（リダイレクト検査・プライベートホスト拒否）や XML パースの安全化（defusedxml）を行っています。

---

## ディレクトリ構成

主要なファイルと役割を示します（抜粋）。

```
src/kabusys/
├── __init__.py                     # パッケージ初期化（version, __all__）
├── config.py                        # 環境変数 / 設定管理（自動 .env ロード）
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py                  # ニュースの LLM スコアリング（ai_scores へ書込）
│   └── regime_detector.py           # ETF MA とマクロ LLMS を合成して market_regime を判定
├── data/
│   ├── __init__.py
│   ├── pipeline.py                  # ETL パイプライン（run_daily_etl 等）
│   ├── jquants_client.py            # J-Quants API クライアント / 保存関数
│   ├── news_collector.py            # RSS 収集、前処理、raw_news への保存
│   ├── calendar_management.py       # 市場カレンダー管理（営業日判定等）
│   ├── quality.py                   # データ品質チェック
│   ├── audit.py                     # 監査ログスキーマ初期化 / init_audit_db
│   ├── etl.py                       # ETL の公開インターフェース（ETLResult 再エクスポート）
│   └── stats.py                     # 汎用統計（zscore_normalize）
├── research/
│   ├── __init__.py
│   ├── factor_research.py           # モメンタム / バリュー / ボラティリティ
│   └── feature_exploration.py       # forward returns, IC, summary, rank
└── ... (その他ユーティリティ)
```

各モジュールは README の該当セクション・ソース内ドキュメントに詳細な設計注記が含まれています。

---

## トラブルシューティング / よくある質問

- .env が読み込まれない:
  - パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env/.env.local を読み込みます。テストなどで自動ロードを抑制したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI/API キー未設定時の挙動:
  - news_nlp.score_news / regime_detector.score_regime は引数で api_key を受け取れます。引数未指定時は環境変数 `OPENAI_API_KEY` を参照します。未設定の場合は ValueError が発生します。
- DuckDB のテーブルがない:
  - ETL 実行前にスキーマ初期化を行うか、ETL 実装側の初期化手順に従ってください。audit.init_audit_db は監査テーブルを初期化するユーティリティを提供します。

---

## 貢献 / 開発

- コードベースはモジュール単位でテスト可能な設計です。OpenAI やネットワーク呼び出し部分は内部関数をモックしてユニットテストを実施してください（ソース内に patch 用の参照箇所あり）。
- PR・Issue の送付時には再現手順・環境（.env を含む）を添えてください。

---

README に掲載されていない詳細な使用例や API の仕様は各モジュール（src/kabusys/...）の docstring を参照してください。必要であれば、特定機能の利用方法（例: ETL のスケジュール化、OpenAI のレスポンスバリデーションの挙動など）をさらに詳しくまとめます。