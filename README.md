# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを含みます。

---

## 主な特徴

- ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得して DuckDB に保存
  - 差分更新、バックフィル、品質チェックを備えた日次 ETL パイプライン
- ニュース収集 / NLP
  - RSS を安全に収集（SSRF 対策、gzip・サイズ制限）
  - OpenAI を用いた銘柄ごとのニュースセンチメントスコア（ai_scores）生成
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離 + マクロニュースの LLM センチメントを合成して日次レジーム判定
- リサーチ（ファクター解析）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン・IC 計算、統計サマリー
  - Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合の検出
- 監査ログ（audit）
  - signal → order_request → executions のトレーサビリティを保証する監査テーブルの初期化ユーティリティ

---

## 必要条件 / 依存パッケージ（代表）

- Python 3.9+
- duckdb
- openai
- defusedxml

（実行環境に応じてさらに標準ライブラリ外のパッケージを追加してください。pip でインストールします。）

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード例）:

   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   pip install duckdb openai defusedxml
   ```

2. 環境変数を設定する（.env をプロジェクトルートに置くと自動で読み込まれます）。
   - 自動ロードはデフォルトで有効です（.env → .env.local の順に読み込み）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. 必須の環境変数（代表）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
   - OPENAI_API_KEY — OpenAI 呼び出しに使用（ai.score 等）。各関数は引数で上書き可能。
   - KABU_API_PASSWORD — kabu ステーション API 用パスワード（注文実行などで必要）
   - SLACK_BOT_TOKEN — Slack 通知用（必要に応じて）
   - SLACK_CHANNEL_ID — Slack チャンネル ID
   - かつ任意:
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`
     - KABUSYS_ENV — `development` | `paper_trading` | `live`
     - LOG_LEVEL — `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`

   .env の書式は一般的な KEY=VALUE（export KEY=... 形式も一部サポート）。クォートやコメントも取り扱います。

---

## 使い方（代表的な例）

※ 以下はライブラリ API を直接利用する例です。適切なエラーハンドリングとログ設定を行ってください。

1. DuckDB 接続（デフォルトパスを使う例）:

   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL を実行（run_daily_etl）:

   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   # target_date を指定しなければ今日が対象
   res = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(res.to_dict())
   ```

3. ニュースセンチメント計算（score_news）:

   ```python
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   # OpenAI キーを環境変数に設定するか、api_key 引数で渡す
   n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
   print(f"scored {n} codes")
   ```

4. 市場レジーム判定（score_regime）:

   ```python
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
   ```

5. 監査DB を初期化（監査用 DuckDB を新規作成）:

   ```python
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db("data/audit.duckdb")
   # audit_conn をアプリで使用
   ```

6. 研究用ファクター計算（例: momentum）:

   ```python
   from datetime import date
   from kabusys.research.factor_research import calc_momentum

   records = calc_momentum(conn, target_date=date(2026, 3, 20))
   # records は {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"} の dict リスト
   ```

---

## 重要な設計方針（実運用・バックテスト向けの注意点）

- Look-ahead バイアス対策
  - モジュール内の多くの関数は内部で date.today() や datetime.today() を直接参照せず、明示的に target_date を受け取り、DB クエリでは target_date 未満（排他）などを意識しています。バックテスト時は必ず適切な target_date を渡してください。
- フェイルセーフ
  - LLM 呼び出しや外部 API エラーは多くの場合フォールバック（ゼロスコア）で継続します。致命的失敗は上位に伝播しますが、部分失敗で他データを消さないように設計しています（例: ai_scores の部分置換など）。
- 冪等性
  - ETL の保存処理は ON CONFLICT DO UPDATE 等を利用して冪等的に保存します。
- セキュリティ
  - ニュース収集モジュールは SSRF 対策、XML インジェクション対策（defusedxml）、レスポンスサイズ制限を実装しています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定の読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し、score_news）
    - regime_detector.py — 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - news_collector.py — RSS ニュース収集
    - calendar_management.py — 市場カレンダー管理
    - quality.py — データ品質チェック
    - audit.py — 監査ログテーブル定義と初期化
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - etl.py — ETLResult の公開（短縮再エクスポート）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - (その他) strategy/, execution/, monitoring/ パッケージ候補 — __all__ に含まれるが実装は別途

---

## 補足 / トラブルシューティング

- 自動 .env 読み込み
  - プロジェクトルートは __file__ を基点に探索して `.git` または `pyproject.toml` を見つけます。CWD に依存しないためパッケージ配布後でも安定して動作します。見つからない場合は自動ロードをスキップします。
- テスト時の便利オプション
  - 自動環境変数ロードを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - OpenAI 呼び出し等は内部で差し替え可能に実装されており、ユニットテストでは該当関数をモックできます（例: news_nlp._call_openai_api, regime_detector._call_openai_api）。
- ロギング
  - settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。

---

README は必要に応じてプロジェクト固有の情報（CI、ライセンス、貢献ガイド、詳細な API 仕様）を追加してください。必要であれば各モジュールのサンプルや CLI ラッパー用の例も追記します。