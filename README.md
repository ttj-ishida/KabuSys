# KabuSys

日本株向けのデータプラットフォーム・研究・自動売買補助ライブラリ群です。  
DuckDB をデータレポジトリとして使用し、J-Quants API / RSS / OpenAI を組み合わせてデータ収集・品質チェック・特徴量作成・ニュース NLP・市場レジーム判定・監査ログ構築などを行います。

主な設計方針：
- バックテストでの Look‑ahead bias を避ける（datetime.today() に依存しない等）
- DuckDB を中心に SQL + 軽量 Python で処理
- API呼び出しはレート制御・リトライ・フェイルセーフを備える
- データ品質チェックと監査ログを重視

---

## 機能一覧

- 環境設定管理
  - .env の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック
- データ ETL（J-Quants）
  - 日次株価（OHLCV）取得 / 保存（差分取得・ページネーション対応）
  - 財務データ取得 / 保存
  - JPX マーケットカレンダー取得 / 保存
  - ETL の統合エントリ（run_daily_etl）と ETL 結果の ETLResult
- データ品質チェック
  - 欠損（OHLC）・スパイク・重複・日付不整合チェック
- カレンダー管理
  - 営業日判定 / 前後営業日検索 / 期間内の営業日取得
  - 夜間バッチでのカレンダー更新（calendar_update_job）
- ニュース収集
  - RSS 取得（SSRF 対策、サイズ上限、トラッキングパラメータ削除）
  - raw_news / news_symbols への冪等保存（記事ID: 正規化URLのSHA256）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - マクロニュースを使った市場レジーム判定（score_regime）
  - OpenAI 呼び出しは JSON Mode、バッチ処理・リトライ制御を実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン・IC（Spearman）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化
  - 冪等性（order_request_id）と UTC タイムスタンプポリシー

---

## 必要条件（推奨）

- Python 3.10+
- DuckDB
- OpenAI SDK（OpenAI の Chat API を使う機能を利用する場合）
- defusedxml（RSS パースの安全化）
- （ネットワークアクセス可能で J-Quants の資格情報を所持していること）

推奨パッケージ例（pip）:
```bash
pip install duckdb openai defusedxml
```

プロジェクトの依存関係ファイル（requirements.txt）があればそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン / ソース配置
   - 例: git clone <repo_url>

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定（.env をプロジェクトルートに作成することを推奨）
   サンプル（.env.example のようなファイルを作成）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development            # development | paper_trading | live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```
   - 自動ロードはデフォルトで有効（config.py 内でプロジェクトルートの .env / .env.local を自動読み込み）
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. DuckDB データファイルのディレクトリを作成
   ```bash
   mkdir -p data
   ```

---

## 使い方（基本例）

以下は主要 API の利用例です。実行前に環境変数（J-Quants トークンや OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続の準備
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- ETL（デイリー ETL）の実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日（ただし内部で営業日に調整）
print(result.to_dict())
```

- ニュースセンチメント計測（OpenAI 使用）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"written {n_written} ai_scores")
```

- 市場レジーム判定（ETF 1321 とマクロ記事を合成）
```python
from kabusys.ai.regime_detector import score_regime

res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
print("score_regime returned", res)
```

- 監査データベース初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 監査テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究ユーティリティ（例: モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の mom_1m, mom_3m, mom_6m, ma200_dev を含む dict のリスト
```

注意点：
- AI（OpenAI）を利用する関数は OPENAI_API_KEY を渡すか、api_key 引数で明示してください。未設定だと ValueError が発生します。
- J-Quants API はレート制限があるため、jquants_client モジュールは内部でレート制御とリトライを行います。ID token は refresh token から自動取得されます（settings.jquants_refresh_token が必要）。

---

## 設定（環境変数）

主な必須・推奨環境変数：
- JQUANTS_REFRESH_TOKEN (必須: J‑Quants からのリフレッシュトークン)
- KABU_API_PASSWORD (必須: kabuステーション API 用パスワード)
- SLACK_BOT_TOKEN (必須: Slack 通知用)
- SLACK_CHANNEL_ID (必須: Slack 送信先チャンネル)
- OPENAI_API_KEY (OpenAI を使う処理を行う場合は必須)
- DUCKDB_PATH (省略可: data/kabusys.duckdb がデフォルト)
- SQLITE_PATH (省略可: data/monitoring.db がデフォルト)
- KABUSYS_ENV: development | paper_trading | live （デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 をセットすると .env 自動ロードを停止)

config.py はプロジェクトルート（.git または pyproject.toml が存在する場所）を基準に .env/.env.local を読み込みます。

---

## ディレクトリ構成

主要ファイル / モジュールと簡単な説明:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読込・Settings クラス（アプリ設定）を提供
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事を銘柄ごとに集計し OpenAI でセンチメントを算出、ai_scores に保存
    - regime_detector.py
      - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書込
  - data/
    - __init__.py
    - calendar_management.py
      - market_calendar を使った営業日判定・next/prev/get_trading_days 等
    - etl.py
      - ETLResult の再エクスポート
    - pipeline.py
      - run_daily_etl, 個別 ETL (prices/financials/calendar) 実装
    - stats.py
      - zscore_normalize
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ用スキーマ定義・初期化（signal_events, order_requests, executions）
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レート制御）
    - news_collector.py
      - RSS 取得・記事前処理・記事ID生成・SSRF対策
  - research/
    - __init__.py
    - factor_research.py
      - momentum/volatility/value 等のファクター計算
    - feature_exploration.py
      - calc_forward_returns, calc_ic, rank, factor_summary 等

（上記は主要モジュール抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 運用上の注意 / ベストプラクティス

- Look‑ahead bias に注意：各 AI / 研究用関数は target_date を明示的に受け取り、システム時刻に依存しないよう設計されています。バックテストでは target_date を厳密に制御してください。
- API キーの管理：J-Quants リフレッシュトークンや OpenAI キーは秘匿して管理してください。.env をバージョン管理に入れないこと。
- レート制限：J-Quants は 120 req/min の制限があります（jquants_client で制御）。多数の並列ジョブは避けてください。
- フェイルセーフ：OpenAI や外部 API の一部エラーはフェイルセーフ（スコア=0 にフォールバック）になっていますが、ログを必ず監視してください。
- 監査ログ：order_requests の order_request_id を冪等キーとして再送時の二重発注を防ぎます。実運用では order_request_id 管理を厳密に行ってください。

---

## 開発・テスト

- 自動 .env 読み込みはテスト時に邪魔な場合があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- OpenAI 呼び出しなどはモック差し替え（unittest.mock.patch）を想定した設計になっています（_call_openai_api をモックする等）。

---

README は以上です。より詳細な使い方や API 仕様、スキーマ定義、運用手順等を追加したい場合は、目的（例: ETL 運用 runbook、バックテストガイド、API 参照）を教えてください。必要に応じて .env.example のテンプレートや運用チェックリストも作成します。