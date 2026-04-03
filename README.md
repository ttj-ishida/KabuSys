# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL・データ品質チェック・ニュースNLP（LLMベース）・市場レジーム判定・リサーチ用ファクター計算・監査ログ（発注トレーサビリティ）などの機能を提供します。

---

## 主な特徴（抜粋）

- ETL（J-Quants API）:
  - 株価日足（OHLCV）、財務データ、JPXカレンダーの差分取得・冪等保存
  - レート制限・リトライ・トークン自動更新に対応
- データ品質チェック:
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue データ構造で返却）
- ニュース収集 & NLP:
  - RSS からのニュース収集（SSRF対策、トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコアリング（ai_scores へ保存）
- 市場レジーム判定:
  - ETF (1321) の 200日移動平均乖離 と マクロニュース（LLM）を合成して日次レジーム判定
- リサーチ / ファクター:
  - Momentum / Value / Volatility 等の定量ファクター計算、将来リターン・IC・統計サマリ
- 監査ログ / トレーサビリティ:
  - signal_events, order_requests, executions の監査テーブルを DuckDB で初期化・管理
- 設定管理:
  - .env / 環境変数から設定を自動ロード（プロジェクトルート検出・上書きルールあり）
  - テスト用途に自動ロードを無効化するフラグあり

設計上の共通方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を直接参照しない関数設計）
- DuckDB をバックエンドに SQL と最小限の Python で処理
- 外部API失敗時は基本的にフォールバックして継続（フェイルセーフ）

---

## 機能一覧（モジュール別概略）

- kabusys.config
  - 環境変数 / .env 読み込み、Settings オブジェクトで設定取得
- kabusys.data
  - jquants_client: J-Quants API 呼び出し・保存ユーティリティ
  - pipeline: 日次 ETL 実行（run_daily_etl）と ETLResult
  - quality: データ品質チェック（check_missing_data/check_spike/check_duplicates/check_date_consistency/run_all_checks）
  - news_collector: RSS 取得・前処理・保存ロジック
  - calendar_management: 市場カレンダー判定・更新ジョブ
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の汎用統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores に書き込み
  - regime_detector.score_regime: ETF MA と マクロニュースを合成して market_regime に書き込み
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. リポジトリをクローンする（またはパッケージを取得）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 環境を準備（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール  
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用）
   代表的な依存例:
   - duckdb
   - openai
   - defusedxml
   - typing-extensions（古い Python の場合）
   ```
   pip install duckdb openai defusedxml
   # または開発用: pip install -e .
   ```

4. 環境変数設定（.env をプロジェクトルートに置くと自動読み込みされます）
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を読み込みます。
   - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   主な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須 for ETL）
   - OPENAI_API_KEY: OpenAI 呼び出し（news_nlp/regime_detector）
   - KABU_API_PASSWORD / KABU_API_BASE_URL: kabuステーション API（発注等）
   - DUCKDB_PATH / SQLITE_PATH: デフォルト DB パス
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG/INFO/...

---

## 使い方・例

以下は Python インタプリタ / スクリプトからの利用例です。各関数は例外を投げる場合があるため呼び出し側で try/except を推奨します。

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次ETL を実行（pipeline.run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（ai.news_nlp.score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数か、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成
  ```

- ファクター計算（research）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  d = date(2026, 3, 20)
  mom = calc_momentum(conn, d)
  val = calc_value(conn, d)
  vol = calc_volatility(conn, d)
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意点:
- OpenAI 呼び出しは gpt-4o-mini を使用する設計です。API使用量・コスト管理を行ってください。
- J-Quants API はレート制限（120 req/min）があります。jquants_client 内で制御されていますが、外部から直接大量呼び出しをしないでください。
- 多くの関数は「look-ahead bias」を避ける設計になっており、target_date を明示的に渡すことを想定しています。

---

## 簡易トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートの検出は __file__ の親ディレクトリから .git または pyproject.toml を探します。パッケージ配置・テスト環境では検出できない場合があります。その場合は手動で環境変数を設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- OpenAI 関連で JSON パースエラー
  - レスポンスのフォーマットが想定外の場合は該当処理は 0.0 にフォールバックする等の安全処理が入ります。ログ（LOG_LEVEL=DEBUG）で詳細を確認してください。
- DuckDB の executemany が空のリストでエラーになる
  - モジュール側は空チェックを行っているため通常は心配不要ですが、自分で executemany を使う場合注意してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要モジュールを抜粋しています（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                          - 環境変数 / .env 管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py                       - ニュース NLP（score_news）
    - regime_detector.py                - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 - J-Quants API クライアント・保存処理
    - pipeline.py                       - ETL パイプライン（run_daily_etl 等）
    - quality.py                        - データ品質チェック
    - news_collector.py                 - RSS 収集・前処理
    - calendar_management.py            - 市場カレンダー管理
    - audit.py                          - 監査ログスキーマ初期化
    - etl.py                            - ETLResult 再エクスポート
    - stats.py                          - 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py                - Momentum / Value / Volatility 等
    - feature_exploration.py            - 将来リターン / IC / summary / rank

---

## ライセンス・コントリビューション

（本READMEには記載がありません。実際のリポジトリに LICENSE や CONTRIBUTING を置いてください）

---

必要であれば、特定機能（ETL のスケジューリング例、kabu API を使った発注フロー、CI テスト方法など）について、さらに具体的な手順やサンプルコードを追記します。どの部分を詳しく知りたいか教えてください。