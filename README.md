# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
データ収集（J-Quants, RSS）、ETL、データ品質チェック、ファクター計算、LLM を使ったニュースセンチメント、監査ログなどのコンポーネントを提供します。

主な設計思想：
- ルックアヘッドバイアスに注意した時系列処理（内部で date.today() を直接参照しない等）
- DuckDB を中心としたローカルデータ管理（冪等保存、トランザクション）
- 外部 API 呼び出しに対するリトライ／レートリミット／フォールバック処理
- テスト容易性（環境変数自動読込を無効化するフラグ等）

---

## 機能一覧

- 環境変数／設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須値チェック・環境別フラグ（development / paper_trading / live）
- データ収集・ETL（kabusys.data）
  - J-Quants API クライアント（価格、財務、上場情報、カレンダー）
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去）
  - 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ（signal / order_request / executions テーブル、初期化ユーティリティ）
- 研究用ユーティリティ（kabusys.research）
  - モメンタム / バリュー / ボラティリティなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、feature summary
  - z-score 正規化ユーティリティ（kabusys.data.stats）
- AI（kabusys.ai）
  - news_nlp: ニュース記事群をまとめて LLM に投げ、銘柄ごとの ai_score を生成
  - regime_detector: ETF（1321）200日 MA とマクロニュース LLM 評価を合成して市場レジーム判定
  - OpenAI API 呼び出しに対するリトライ・フォールバックやレスポンス検証を内包
- その他ユーティリティ
  - DuckDB への冪等保存関数、ID トークン管理、HTTP リトライ・レート制御 等

---

## 動作要件（推奨）

- Python 3.10+
- 必須パッケージ（主なもの）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

※ 実際のプロジェクトでは requirements.txt または pyproject.toml を参照してください。

---

## 環境変数

主に以下を使用します（README 内で触れた関数から必要に応じ読み込みます）。

必須（実行コンポーネントに応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（注文連係を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先
- OPENAI_API_KEY — OpenAI（LLM）呼び出しに使用

オプション／挙動制御:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化（テスト用）

自動読み込み:
- パッケージ import 時にプロジェクトルート（.git or pyproject.toml）を探索して `.env` → `.env.local` の順で読み込みます。
- `.env.local` は `.env` を上書きできますが OS 環境変数は保護されます。

例：.env に含める主なキー（参考）
- JQUANTS_REFRESH_TOKEN=
- OPENAI_API_KEY=
- KABU_API_PASSWORD=
- SLACK_BOT_TOKEN=
- SLACK_CHANNEL_ID=
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意（3.10+）
2. リポジトリをクローン / コピー
3. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
4. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （その他ユーティリティがあれば追加）
   - または開発用に pip install -e .（pyproject がある場合）
5. .env を作成して必要な環境変数を設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます
6. DuckDB 用ディレクトリの作成（任意）
   - デフォルトでは data/kabusys.duckdb を使用します。必要に応じてディレクトリ作成。

---

## 使い方（主要ユースケース例）

以下は簡単な Python スニペット例です。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続と日次 ETL 実行（データ収集）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP による銘柄スコア付け（AI）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # 例: api_key は OPENAI_API_KEY を渡す
print("written:", n_written)
```
注意: score_news の api_key 引数は OpenAI API キーを受け取ります。None の場合は環境変数 OPENAI_API_KEY が使われます。

- 市場レジーム判定（regime_detector）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY 環境変数を利用
```

- 監査ログデータベース初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 必要に応じてパス指定
```

- 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 注意点 / トラブルシューティング

- OpenAI API 呼び出しでキーが必要です。関数は api_key 引数または環境変数 OPENAI_API_KEY を要求します。未設定時には ValueError を送出します。
- J-Quants 用のトークンも必須（JQUANTS_REFRESH_TOKEN）。get_id_token や fetch_* 系を使う前に設定してください。
- .env の自動ロードを止めたい単体テスト等では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、モジュール内で空チェックが入っています。直接 SQL を実行する場合は注意してください。
- news_collector は RSS 取得時に SSRF・gzip・サイズ上限・XML の危険な入力に対する防御を実装しています。RSS 取得で失敗する場合はログを確認してください。

---

## ディレクトリ構成（概要）

以下はソース内の主要ファイル／モジュールのツリー（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースを LLM でスコアリング
    - regime_detector.py            -- 市場レジーム判定（ETF MA + マクロ LLM）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl など）
    - etl.py                        -- ETLResult の再エクスポート
    - news_collector.py             -- RSS 収集（前処理・保存）
    - calendar_management.py        -- 市場カレンダー管理（営業日判定等）
    - stats.py                      -- z-score 等の統計ユーティリティ
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログテーブル初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py            -- Momentum/Value/Volatility 等
    - feature_exploration.py        -- forward returns / IC / summary / rank
  - monitoring/ (存在する場合、監視用モジュール群)
  - strategy/ (将来的に戦略・シグナル生成を置く想定)
  - execution/ (発注連携モジュール想定)

---

## ログ／監視

- ログレベルは環境変数 LOG_LEVEL で設定（デフォルト INFO）。
- data.quality.run_all_checks は品質問題を一覧で返します。ETL の結果（ETLResult）に品質問題や errors が格納されます。

---

## 開発・貢献

本リポジトリの設計はモジュール分割を重視しているため、各コンポーネントは単体でテストしやすくなっています。  
- 外部 API 呼び出しは内部で差し替え可能（モック用フックや小さなラッパー関数を用意）。
- .env 自動読み込みをテストで無効化可能。

バグ報告や機能追加の提案は Issue を立ててください。

---

この README はコードベース（src/kabusys 配下）を基に作成しています。実際の運用・デプロイ時はセキュリティや注文の実行に関する運用手順・権限管理を十分に設計してください。