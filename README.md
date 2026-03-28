# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
ETL（J-Quants からのデータ取得）・ニュース収集・NLP（LLM）による記事スコアリング・マーケットレジーム判定・調査用ファクター計算・監査ログ（注文 → 約定トレーサビリティ）などを提供します。

主な想定用途：
- データプラットフォームの夜間バッチ（株価・財務・カレンダーの差分ETL）
- ニュースの収集と銘柄ごとの NLP スコアリング（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- 研究用ファクター計算・特徴量探索
- 発注・約定フローの監査ログ用スキーマ初期化

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数の自動読み込み（プロジェクトルートの `.env` / `.env.local` を採用）
  - 必須設定のラッパー（settings オブジェクト）
- kabusys.data
  - jquants_client：J-Quants API クライアント（ページネーション・リトライ・トークン管理・DuckDB への保存）
  - pipeline：日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - calendar_management：JPX カレンダー管理・営業日判定ユーティリティ
  - news_collector：RSS 収集・前処理・raw_news 保存（SSRF 対策や GZIP 保護など）
  - quality：データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit：監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats：汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news：銘柄ごとのニュースセンチメントを LLM（gpt-4o-mini）で評価して ai_scores に保存
  - regime_detector.score_regime：ETF（1321）200日MA乖離とマクロニュースセンチメントを合成し市場レジームを market_regime に保存
- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value：ファクター計算
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank：特徴量探索・IC 計算など

---

## 必須環境・依存関係

- Python 3.10 以上（type union 演算子 `|` を使用）
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで多くを実装。必要に応じてその他パッケージを追加）

requirements.txt（例）
```
duckdb
openai
defusedxml
```

---

## セットアップ手順

1. リポジトリを取得
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   # または最低限:
   pip install duckdb openai defusedxml
   ```

4. パッケージをインストール（開発モード推奨）
   ```
   pip install -e .
   ```

5. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（起動時）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで使用）。

   主に必要な環境変数（コード内で参照されるもの）：
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用 Slack（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に利用）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 環境 ('development' | 'paper_trading' | 'live')（デフォルト: development）
   - LOG_LEVEL: ログレベル（'DEBUG','INFO','WARNING','ERROR','CRITICAL'）（デフォルト: INFO）

6. データベース周りの初期化（例）
   - 監査ログ用 DB を初期化する：
     ```py
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # :memory: も可
     ```

---

## 使い方（例）

以下は基本的な操作例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続を作る（settings を使う例）
  ```py
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（pipeline.run_daily_etl）
  ```py
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（LLM）を実行して ai_scores に保存
  ```py
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key は None にすると環境変数 OPENAI_API_KEY を使用
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定を実行
  ```py
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- ファクター計算（研究用）
  ```py
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  m = calc_momentum(conn, date(2026,3,20))
  v = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

- 品質チェック（quality）
  ```py
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

- 監査スキーマを既存 DB に追加（init_audit_schema）
  ```py
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意点：
- LLM 呼び出し（score_news / score_regime）は OpenAI API を利用します。API キーと API 利用料に注意してください。
- ETL の J-Quants 呼び出しはレート制限・認証トークンを扱います。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- モジュールはルックアヘッドバイアス防止のため、target_date を明示的に渡す設計になっています。内部で date.today() を無条件に参照しない実装方針です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save）
    - pipeline.py           — ETL パイプライン / run_daily_etl 等
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - news_collector.py     — RSS 収集・前処理
    - quality.py            — データ品質チェック
    - stats.py              — 汎用統計（zscore_normalize）
    - audit.py              — 監査ログスキーマ初期化
    - etl.py                — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py    — momentum/value/volatility
    - feature_exploration.py— forward returns / IC / summarization
  - research/（上記のサブモジュール）
  - その他（strategy / execution / monitoring は __all__ に含まれるが実装は省略／別ファイルにある想定）

---

## 設計上の注意点 / ポリシー

- Look-ahead bias 回避
  - バックテストやモデル評価でのルックアヘッドを防ぐため、多くの関数で target_date を必須にしたり、DB へのクエリで排他的条件（date < target_date など）を使用しています。
- 冪等性
  - J-Quants からの保存処理は ON CONFLICT DO UPDATE を使って冪等に設計されています。
- フェイルセーフ
  - LLM/API 失敗時はゼロスコアやスキップで継続する設計が多く、処理停止を最小化します（ログは出力）。
- セキュリティ
  - NewsCollector では SSRF 対策・XML インジェクション対策（defusedxml）・応答サイズ上限などを導入しています。
- ロギングと環境
  - settings.log_level や settings.env（development / paper_trading / live）で動作モードを管理できます。

---

## よくある操作フロー（例）

1. 環境変数を設定（.env）
2. DuckDB を接続・schema を整備（監査スキーマ等）
3. run_daily_etl を夜間バッチで実行してデータを蓄積
4. news_collector で raw_news を収集 → score_news で ai_scores を生成
5. regime_detector で market_regime を更新
6. 研究チームは research.* の関数でファクター分析・シグナル開発
7. 戦略から監査ログ（signal_events / order_requests / executions）を用いて発注トレーサビリティを確保

---

## サポート / 貢献

- バグ報告や機能提案はリポジトリの Issue を利用してください。
- テスト、ドキュメント、型アノテーションの改善などの貢献を歓迎します。

---

README の内容や使用例で不明点があれば、実行シナリオ（ETL/LLM/監査スキーマなど）を教えてください。具体的なセットアップ手順やコード例をそのシナリオに合わせて追加で提供します。