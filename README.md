# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP、マーケットレジーム判定、監査ログ（トレーサビリティ）など、量的投資・リサーチ・運用に必要な共通機能を提供します。

> 現状の実装はライブラリレイヤ中心で、実行用の CLI/サービスはプロジェクト固有に組み合わせて利用する想定です。

## 主な特徴（機能一覧）

- データ収集 / ETL
  - J-Quants API 経由で株価日足（OHLCV）、財務データ、JPXカレンダーを差分で取得・保存
  - DuckDB へ冪等的に保存（ON CONFLICT による上書き）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損 / 重複 / 将来日付 / 株価スパイク検出（quality モジュール）
  - QualityIssue オブジェクトで問題を集約
- ニュース収集・NLP
  - RSS フィードから記事を収集（SSRF対策・サイズ制限・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離 + マクロニュースセンチメントを合成して日次レジーム判定（score_regime）
- 研究ツール
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算、IC（Spearmanランク相関）、統計サマリ
  - Zスコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル等を初期化する機能（init_audit_schema / init_audit_db）
- 設定管理
  - .env ファイルまたはOS環境変数から設定値読み込み（自動ロード機能、無効化可能）

---

## 必要条件

- Python 3.10 以上（型注釈に `X | None` を使用しているため）
- 主要 Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ：urllib 等は不要な追加インストール不要）
- ネットワーク接続（J-Quants / OpenAI / RSS 等の外部 API にアクセスする場合）

※ requirements.txt / pyproject.toml はプロジェクト側で用意してください。上記は実装から推測した主要依存です。

---

## 環境変数（主なもの）

config.Settings クラスで参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション等のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネルID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL (任意) — "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を使う機能（score_news, score_regime 等）で参照

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）にある `.env` および `.env.local` を自動的に読み込みます。
- OS 環境変数が優先され、.env.local は .env 上書きが可能です。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <your-repo-url>
   cd <your-repo>
   ```

2. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - pyproject.toml / requirements.txt がある場合はそちらを使ってください。
   例:
   ```
   pip install -r requirements.txt
   ```
   必要なパッケージの例:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成して必要な変数を設定します。
   - 例 `.env`（実運用ではトークン等は安全に管理してください）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. データベース用ディレクトリを作成（必要な場合）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な呼び出し例）

以下は Python スクリプト／REPL からライブラリを使う最小例です。DuckDB を使う想定です。

共通準備（例）:
```python
import duckdb
from datetime import date

# duckdb ファイルに接続（なければ作成）
conn = duckdb.connect("data/kabusys.duckdb")
```

1) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

# 対象日を指定（省略時は today）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコアを計算して ai_scores に保存する
```python
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数で設定するか、api_key 引数で渡せます
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定を実行する
```python
from kabusys.ai.regime_detector import score_regime

res = score_regime(conn, target_date=date(2026, 3, 20))
print("完了" if res == 1 else "失敗")
```

4) 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# audit_conn に対して発注・監査テーブルが作成される
```

5) 研究用のファクター計算・評価
```python
from kabusys.research.factor_research import calc_momentum
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

factors = calc_momentum(conn, date(2026, 3, 20))
forward = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
ic = calc_ic(factors, forward, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

注意点：
- AI 関連の関数（score_news / score_regime）は OpenAI API キー（OPENAI_API_KEY）を参照します。api_key を直接渡すことも可能です。
- ETL / データ取得はネットワーク依存・外部API呼び出しを行います。適切な認証情報とレート制御に注意してください。
- 関数は Look-ahead バイアス防止設計（target_date より前のデータのみ参照）を意識して実装されています。

---

## 主要モジュール説明（抜粋）

- kabusys.config
  - 環境変数の読み込み・バリデーション（自動 .env ロード）
- kabusys.data
  - pipeline: ETL のエントリポイント（run_daily_etl など）
  - jquants_client: J-Quants API 呼び出し・保存処理
  - news_collector: RSS 取得と前処理
  - quality: データ品質チェック
  - calendar_management: マーケットカレンダー管理、営業日判定
  - audit: 監査ログスキーマ初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
- kabusys.ai
  - news_nlp: ニュースから銘柄ごとのセンチメント計算（score_news）
  - regime_detector: マーケットレジーム判定（score_regime）
- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン・IC・統計サマリ等

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル/ディレクトリ（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - researchパッケージは data.stats を利用します

（この README は全ソースを網羅する目的ではなく、主なエントリポイントと構成を示しています）

---

## 運用上の注意 / ベストプラクティス

- 秘匿情報（J-Quants トークン、OpenAI キー、Slack トークン等）は `.env` ではなくシークレットマネージャーや CI の Secret 機能で管理することを推奨します。
- OpenAI/API 呼び出しはレート制限と失敗処理（リトライ・バックオフ）が組み込まれていますが、コスト抑制のためバッチ化やキャッシュを検討してください。
- DuckDB ファイルのバックアップ・世代管理を行ってください（誤削除や破損時のリカバリに必要）。
- 実運用（ライブ口座）では KABUSYS_ENV を `live` に設定し、発注部分（ここでは提供されていない execution 層）を慎重に運用してください。
- テスト実行時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い、環境を明示的に制御すると安全です。

---

## 参考（実装上の補足）

- 自動 `.env` ロードはプロジェクトルート（.git または pyproject.toml が見つかる親ディレクトリ）を起点に行います。
- OpenAI 呼び出しは gpt-4o-mini / JSON mode を利用する設計になっており、API レスポンスのパース・検証ロジックが組み込まれています。
- J-Quants クライアントは ID トークンを自動リフレッシュし、ページネーション対応・レート制御（120 req/min）・エラーハンドリング（再試行）を実装しています。

---

必要であれば、README に含める具体的な .env.example や requirements.txt のテンプレート、より詳細な API 使用例（エラー例・ログ設定例）を追加できます。どの情報がさらに欲しいか教えてください。