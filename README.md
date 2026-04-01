# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
主に以下の機能をモジュール化して提供します。

- データ収集・ETL（J-Quants API 経由の株価・財務・カレンダー）
- データ品質チェック・カレンダー管理
- ニュース収集（RSS）・NLP（OpenAI を用いたセンチメント評価）
- 市場レジーム判定（MA とマクロニュースの組合せ）
- 研究用ファクター計算・特徴量解析
- 監査ログ（発注・約定トレース）用スキーマ初期化ユーティリティ
- 設定管理（.envの自動読み込み、環境検証）

このリポジトリはライブラリとしてインポートして使うことを想定しています（例: ETL ジョブ、研究ワークフロー、戦略開発など）。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、ID トークン自動更新、DuckDB への冪等保存）
  - pipeline / etl: 日次差分 ETL（calendar / prices / financials）、ETL 結果の集約（ETLResult）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - news_collector: RSS 収集（SSRF 対策・トラッキング除去・前処理）と raw_news 保存
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログ（signal / order_request / executions）用スキーマ初期化・DB初期化
  - stats: zscore 正規化など共通統計関数
- ai/
  - news_nlp: ニュースを銘柄ごとに集約して OpenAI に投げ、ai_scores に書込む（batch、リトライ、レスポンス検証）
  - regime_detector: ETF（1321）200日移動平均乖離とマクロセンチメントを合成して market_regime に書き込む
- research/
  - factor_research: Momentum / Value / Volatility / Liquidity 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー等
- config.py: .env の自動読み込み（プロジェクトルート検出）、重要な環境変数のラッパー（settings）

---

## 要求ランタイム / 依存ライブラリ

- Python 3.10+
- 明示的に使われている外部パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトに合わせて追加で logging やテスト用ライブラリを導入してください。パッケージ化時は requirements.txt を用意することを推奨します。）

---

## セットアップ手順

1. リポジトリを取得
   - git clone / ダウンロード

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) / .venv\Scripts\activate (Windows)

3. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（.git または pyproject.toml を起点にプロジェクトルートを検出）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用）。

   主要な環境変数（必須 / デフォルト）:
   - JQUANTS_REFRESH_TOKEN ・・・（必須）J-Quants リフレッシュトークン
   - KABU_API_PASSWORD       ・・・（必須）kabuステーション API パスワード
   - KABU_API_BASE_URL       ・・・デフォルト "http://localhost:18080/kabusapi"
   - SLACK_BOT_TOKEN         ・・・（必須）Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID        ・・・（必須）Slack 通知先チャンネルID
   - OPENAI_API_KEY          ・・・（OpenAI を使う処理で必要。関数呼び出しで api_key を渡すことも可能）
   - DUCKDB_PATH             ・・・デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH             ・・・デフォルト "data/monitoring.db"
   - PID_FILE_PATH           ・・・デフォルト "data/execution.pid"
   - KABUSYS_ENV             ・・・"development" | "paper_trading" | "live"（デフォルト "development"）
   - LOG_LEVEL               ・・・"DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C01234567
   ```

5. データディレクトリを作成（必要なら）
   - mkdir -p data

---

## 使い方（簡単なコード例）

※ すべての関数は extern の DB 接続（duckdb.connect）を受け取ります。Look-ahead bias を避けるため target_date を明示して呼び出してください。

1) DuckDB に接続する
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行する（市場カレンダー・株価・財務の差分 ETL + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（ai_scores）を生成する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

4) 市場レジーム判定を実行する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ（audit）スキーマを初期化する
```python
from kabusys.data.audit import init_audit_db

# :memory: でメモリ DB、またはパスを指定してファイル DB を作成
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 注意事項 / 運用メモ

- AI 呼び出し（OpenAI）は課金を伴います。API キーの管理と呼び出し頻度に注意してください。
- news_nlp / regime_detector は OpenAI の JSON Mode を利用する設計になっており、レスポンスのバリデーションとリトライを備えていますが、API 失敗時はフォールバック（スコア=0.0 など）で処理を継続する設計です。
- ETL と品質チェックは個別に例外処理されます。1 ステップが失敗しても他ステップは継続され、ETLResult にエラー情報が蓄積されます。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。テストや CI で環境制御が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## ディレクトリ構成（主要ファイル）

（省略可能な補助ファイルは除く、src/kabusys を起点）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / settings 管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースの集約・OpenAI でスコアリング -> ai_scores
    - regime_detector.py         — 市場レジーム判定（1321 MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + DuckDB 保存ユーティリティ
    - pipeline.py                — ETL パイプライン / run_daily_etl / ETLResult
    - etl.py                     — ETL の公開型再エクスポート（ETLResult）
    - calendar_management.py     — マーケットカレンダー管理・営業日判定
    - news_collector.py          — RSS 取得・前処理・raw_news 保存（SSRF/サイズ対策あり）
    - quality.py                 — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                   — zscore_normalize 等の共通統計
    - audit.py                   — 監査ログ用スキーマ作成・DB 初期化
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Value / Volatility 等の計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー
  - research/ 他のモジュール...
  - （その他 実行/運用用モジュールはここに追加）

---

## 開発 / テスト時のヒント

- テスト時に環境変数自動読み込みを抑止する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出し部分は内部で _call_openai_api を別関数化しており、ユニットテストでは patch / mock で差し替えてテスト可能です（例: unittest.mock.patch）。
- news_collector のネットワーク呼び出しも _urlopen を差し替えてテストできます。
- DuckDB に対する executemany の空パラメータの扱い（バージョン依存）に注意して実装されています。実運用環境の duckdb バージョンと互換性を確認してください。

---

問題や追加してほしい内容（例: CLI、Docker サポート、requirements.txt 作成、CI 設定など）があれば教えてください。README の拡張版（実際の .env.example、サンプルワークフロー、運用チェックリスト）も作成できます。