# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
データ収集（J-Quants、RSS）、品質チェック、ファクター計算、ニュース / マクロの自然言語処理（OpenAI）を組み合わせ、研究（Research） → シグナル → 発注（Audit / Execution）までを支援するモジュール群を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ収集（J-Quants API）と DuckDB への冪等保存
  - 日足株価（OHLCV）、財務データ、マーケットカレンダー取得
  - レート制限・リトライ・トークン自動リフレッシュ機構を実装
- ニュース収集（RSS）とニュース前処理（SSRF対策・トラッキング除去）
- ニュースセンチメント解析（OpenAI / gpt-4o-mini）による銘柄ごとのAIスコアリング
- マクロセンチメント + ETF MA乖離を使った市場レジーム判定
- ETLパイプライン（差分更新・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 監査ログ（signal_events / order_requests / executions）のスキーマ定義と初期化
- 研究用モジュール（ファクター計算、将来リターン、IC計算、統計要約）
- 環境設定を .env / 環境変数で管理（自動ロード機能あり）

---

## 主要機能一覧（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）、必須設定チェック、settings オブジェクト
- kabusys.data
  - jquants_client: J-Quants API ラッパー（取得・保存・認証）
  - pipeline / etl: 日次 ETL パイプライン、個別 ETL ジョブ
  - news_collector: RSS 取得・前処理・raw_news への保存ヘルパ
  - quality: データ品質チェック（QualityIssue を返す）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - stats: z-score 正規化等の統計ユーティリティ
  - audit: 監査ログ用テーブル定義 & 初期化ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースをまとめて LLM に投げ、ai_scores に保存
  - regime_detector.score_regime: ETF MA・マクロニュースから市場レジーム判定
- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリ等

（strategy / execution / monitoring パッケージはパブリックAPIとして __all__ に含まれていますが、ここでは主要な data/research/ai 機能を中心に説明しています。）

---

## 必要条件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （その他標準ライブラリ）

実行環境に応じて適切なパッケージをインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得

2. Python の仮想環境を作成・有効化（推奨）

   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 依存パッケージをインストール（例）

   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用）

4. パッケージを編集可能モードでインストール（任意）

   - pip install -e .

5. 環境変数の設定

   プロジェクトルートに `.env` を置くと自動的に読み込まれます（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（少なくともこれらは設定が期待されます）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（使用箇所に依存）
   - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
   - SLACK_CHANNEL_ID: Slack 送信先チャネル ID

   任意 / デフォルトあり:

   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / ...（デフォルト INFO）
   - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime に未指定時に参照）

   サンプル .env（例）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（よく使う API と例）

以下は Python REPL やスクリプトから呼ぶ例です。DuckDB 接続に対して各関数を呼び出します。

- DuckDB 接続の作成例：

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（run_daily_etl）：

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しない場合は今日（os.date.today()）が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI を使う）：

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、OPENAI_API_KEY を環境変数で設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written: {n_written} codes")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを組合せ）：

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究用）：

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
```

- 監査ログスキーマ初期化（audit DB）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使って監査関連の INSERT/SELECT を行う
```

注意点:
- score_news / score_regime は OpenAI API を使用します。API キーは引数 api_key で渡すか、環境変数 OPENAI_API_KEY を設定してください。API 呼び出しにはリトライ・フォールバック処理がありますが、API 利用料が発生します。
- ETL / データ保存は DuckDB のテーブルスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_calendar など）を前提としています。事前にスキーマを用意するか、別途スキーマ初期化ロジックを用意してください。
- モジュールはルックアヘッドバイアス（look-ahead bias）に注意して設計されています。target_date 未満や対象ウィンドウの排他条件を守る実装です。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py             # ニュースセンチメント解析 / ai_scores 書き込み
      - regime_detector.py      # マクロ + ETF MA による市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント（取得・保存）
      - pipeline.py             # ETL パイプライン（run_daily_etl 等）
      - etl.py                  # ETLResult の公開（再エクスポート）
      - news_collector.py       # RSS 収集 / 前処理 / raw_news 保存
      - quality.py              # データ品質チェック（missing/spike/duplicates 等）
      - calendar_management.py  # 市場カレンダー管理 / 営業日判定
      - stats.py                # zscore_normalize 等
      - audit.py                # 監査ログ（DDL / 初期化）
    - research/
      - __init__.py
      - factor_research.py      # Momentum / Value / Volatility ファクター計算
      - feature_exploration.py  # 将来リターン / IC / summary / rank
    - ai/, data/, research/ などは上記の役割に対応

上記以外に strategy / execution / monitoring パッケージがエクスポート対象として __all__ に含まれています（本 README のコードベースに存在する機能のうち主要なものを記載）。

---

## 環境設定 / 動作設定の補足

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` / `.env.local` を自動ロードします。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

- ログレベル / 環境切替
  - KABUSYS_ENV: development / paper_trading / live のいずれか
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

---

## テスト・開発時のヒント

- OpenAI・J-Quants API 呼び出しは外部依存のためユニットテストではモック（patch）してください。各モジュール内の _call_openai_api や jquants_client._request などは差し替えが想定されています。
- DuckDB をインメモリでテストする場合: duckdb.connect(":memory:")
- .env 自動ロードはテストで邪魔になることがあるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。

---

## おわりに

この README はソースコードの主要な使い方や構成をまとめたものです。詳細な API の使用方法（テーブルスキーマや各関数の引数／戻り値の詳細）は該当モジュールの docstring を参照してください。必要であれば、README に追記する内容（例: テーブル定義、実運用手順、cron ジョブ例、Slack 通知設定など）を教えてください。