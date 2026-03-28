# KabuSys

KabuSys は日本株のデータパイプライン、リサーチ、ニュースNLP、そして市場レジーム判定を含む自動売買／リサーチ基盤の Python パッケージです。J-Quants API や OpenAI（gpt-4o-mini）を活用し、DuckDB を内部データストアとして利用する設計になっています。

主な設計方針の抜粋:
- ルックアヘッドバイアス防止（日時関数の直接参照を避け、ETL/スコアは明示的な target_date を受け取る）
- ETL・保存は冪等に実装（ON CONFLICT / DELETE→INSERT 等）
- API 呼び出しにはリトライ・レート制御・フェイルセーフを実装
- テスト可能性（関数注入やモック対象の内部呼び出しを明示）

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価（日足）、財務データ、上場情報、JPX カレンダーを差分取得（pagination 対応）
  - ETL の差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付整合性）
  - news_collector による RSS ニュース収集（SSRF 対策、トラッキング除去、前処理）
- データ保存・スキーマ
  - DuckDB への冪等的保存関数（raw_prices, raw_financials, market_calendar, raw_news, ai_scores など）
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー、流動性）
  - 特徴量解析（将来リターン計算、IC / Spearman、統計サマリー、zscore 正規化）
- AI（ニュースNLP / レジーム判定）
  - news_nlp.score_news: ニュースを銘柄ごとに集約し OpenAI でセンチメント付与 → ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離 + マクロニュースセンチメントを合成して市場レジームを判定 → market_regime に保存
- ユーティリティ
  - カレンダー管理（営業日判定、next/prev_trading_day、get_trading_days）
  - J-Quants クライアント（レートリミット、トークン自動リフレッシュ、リトライ）
  - データ品質チェック（run_all_checks）

---

## 必要条件（概略）

- Python 3.10+
- ネットワークアクセス（J-Quants API / RSS / OpenAI）
- 推奨パッケージ（requirements 例）
  - duckdb
  - openai
  - defusedxml
  - (ロギング等は標準ライブラリで対応)

例（requirements.txt の例）:
```
duckdb>=0.10
openai>=1.0
defusedxml>=0.7
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成して依存関係をインストール:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   requirements.txt が無い場合は上の推奨パッケージをインストールしてください。

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（モジュール kabusys.config が読み込みます）。
   - 必須環境変数（少なくともこれらを設定してください）:
     - JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD - kabuステーション API パスワード（発注モジュール等で使用）
     - SLACK_BOT_TOKEN - Slack 通知用トークン（Slack を使う機能が有る場合）
     - SLACK_CHANNEL_ID - Slack チャンネル ID
     - OPENAI_API_KEY - OpenAI API キー（news_nlp / regime_detector で使用）
   - 任意 / デフォルト:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - LOG_LEVEL (DEBUG / INFO / …) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB 用ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（サンプル）

以下は代表的な使い方例です。各関数はモジュール単位で独立しているので、目的に応じて呼び出してください。

- DuckDB 接続を作る:
  ```python
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')
  ```

- ETL（日次パイプライン）を実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を明示的に指定（ルックアヘッド防止）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI が必要）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"wrote {written} ai scores")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用DB初期化（監査専用 DB を作る）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで監査テーブルが作成されます
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  t = date(2026, 3, 20)
  mom = calc_momentum(conn, t)
  val = calc_value(conn, t)
  vol = calc_volatility(conn, t)
  ```

- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意:
- AI 呼び出し（OpenAI）は API 利用料が発生します。テスト時は内部の _call_openai_api をモックすることを推奨します。
- 多くの関数は target_date を引数で受け取り、date.today() を直接参照しないよう設計されています。バックテストや再実行時の再現性に有益です。

---

## 環境変数の自動ロードについて（kabusys.config）

- モジュール kabusys.config は実行時にプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、`.env` → `.env.local` の順に読み込みます。
- OS 環境変数を優先し、`.env.local` は既存の環境変数を上書きします（ただし OS 変数保護）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

Settings の主要プロパティ:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path
- settings.sqlite_path
- settings.env / settings.log_level / settings.is_live / settings.is_paper / settings.is_dev

---

## 重要な設計・運用上の注意

- Look-ahead bias（未来情報参照）を避けるため、日付取り扱いは明示的に target_date を受け取る設計です。バックテストやリサーチでの利用時は必ず target_date を制御してください。
- API 呼び出し部（J-Quants, OpenAI）はレート制御・リトライを実装していますが、商用運用時は API の利用制限・コストを監視してください。
- DuckDB の executemany に関するバージョン依存（空リスト不可）など実稼働上の注意がソース内コメントに記載されています。使用する DuckDB バージョンに注意してください。
- news_collector は SSRF 対策、受信サイズ制限、XML ハードニング（defusedxml）などを行っていますが、外部フィードの信頼性やライセンス等は運用で管理してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント付与（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - etl.py                 — ETL 公開インターフェース
    - pipeline.py            — 日次 ETL パイプライン実装
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（テーブル定義・初期化）
    - jquants_client.py      — J-Quants API クライアント（fetch/save 実装）
    - news_collector.py      — RSS ニュース収集・前処理
    - pipeline.py            — （ETL の中核、ETLResult を含む）
    - etl.py                 — ETL インターフェース（ETLResult 再公開）
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 等の計算
    - feature_exploration.py — forward returns / IC / summary / rank
  - research/*（他の研究ユーティリティ）
  - その他（strategy, execution, monitoring は __all__ に含まれる想定）

（上記は提供されたコードベースの主要モジュールを抜粋したものです）

---

## テスト・開発時のヒント

- OpenAI 呼び出しやネットワーク I/O 部分はモック可能に設計されています（ソース内にモック対象の関数名がコメントで示されています）。ユニットテストではこれらを差し替えてください。
- DuckDB をインメモリで使うとテストが高速になります:
  ```python
  conn = duckdb.connect(":memory:")
  ```
- settings はプロパティアクセスで環境変数を検証します。テスト時は必要な環境変数を一時的に設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動で注入してください。

---

必要であれば、README に追加したい内容（例: API キー取得方法、より詳細な起動例、CI/CD 設定、Dockerfile 例、運用手順書など）を教えてください。必要に応じてサンプル .env.example も作成します。