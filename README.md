# KabuSys

日本株自動売買およびデータ基盤ライブラリ（KabuSys）の README。  
このリポジトリはデータ収集（J-Quants / RSS）、品質チェック、特徴量算出、AI によるニュースセンチメント評価、監査ログ設計などを含む日本株向けの研究・運用ユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームと戦略研究／実行に必要な以下の機能群を提供する Python パッケージです。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）と DuckDB への永続化（冪等保存）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメントおよび市場レジーム判定
- ファクター（モメンタム／バリュー／ボラティリティ）計算および特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマ初期化ユーティリティ
- 環境変数・設定の自動ロード（.env, .env.local）

設計上の注記:
- ルックアヘッドバイアスを避けるため、内部実装は基本的に `date` / `target_date` を引数に取り、`date.today()` に依存しない実装になっています。
- API 呼び出しはリトライ・バックオフやレート制御を備え、フェイルセーフ（失敗時はスキップやゼロフォールバック）を優先します。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存関数、認証、自動リフレッシュ、レートリミット）
  - pipeline: 日次 ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 取得・前処理・保存支援
  - quality: データ品質チェック（QualityIssue を返す）
  - calendar_management: JPX カレンダー管理・営業日判定
  - audit: 監査ログテーブル初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計（zscore_normalize 等）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント評価（OpenAI 経由）
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM 評価を組み合わせた市場レジーム判定
- research/
  - factor_research: モメンタム、バリュー、ボラティリティの計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー 等
- config.py: .env 自動読み込み、Settings（環境変数ラッパー）
- audit/schema 初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに unions | を使用。3.10 以上を推奨）
- DuckDB、openai、defusedxml 等の依存パッケージ

1. 仮想環境を作成・有効化（例: venv）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール（例）:
   ```
   pip install duckdb openai defusedxml
   ```
   - 実運用では logger/requests など追加が必要な場合があります。requirements.txt / pyproject.toml を用意している場合はそちらを使用してください。

3. ソースを editable インストール（任意）:
   ```
   pip install -e .
   ```
   （プロジェクトが pyproject.toml / setup.py を含む場合）

4. 環境変数（.env）の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動的にロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 例（.env.example）:

     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # kabuステーション（注文実行に必要な場合）
     KABU_API_PASSWORD=your_kabu_api_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # OpenAI
     OPENAI_API_KEY=sk-...

     # Slack 通知
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789

     # DB パス
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 実行環境
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. 環境の確認:
   - Python REPL で以下を実行して設定が読めることを確認:
     ```python
     from kabusys.config import settings
     print(settings.duckdb_path, settings.is_dev)
     ```

---

## 使い方（主要ユースケース）

ここでは代表的な利用例を示します。実運用やスクリプトでは例外ハンドリングやログ設定を適切に行ってください。

1. DuckDB 接続の生成（例: ファイル DB）
   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL 実行（データ取得・保存・品質チェック）
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニュースセンチメントのスコアリング（AI）
   - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定します。
   ```python
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数を使用
   print("書込銘柄数:", written)
   ```

4. 市場レジーム判定（ETF 1321 MA + マクロニュース）
   ```python
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   score_regime(conn, target_date=date(2026,3,20), api_key=None)
   ```

5. ファクター計算・研究ユーティリティ
   ```python
   from datetime import date
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   from kabusys.data.stats import zscore_normalize

   t = date(2026, 3, 20)
   mom = calc_momentum(conn, t)
   val = calc_value(conn, t)
   vol = calc_volatility(conn, t)

   # 例: 正規化
   mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
   ```

6. 監査ログスキーマ初期化
   ```python
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db("data/audit.duckdb")  # ':memory:' も可
   ```

7. RSS 取得（ニュース収集）
   - news_collector.fetch_rss を呼んで記事を取得し、自前の保存ロジックで raw_news に入れてください。
   - 既存の実装は前処理（URL 除去・トラッキング除去）や SSRF 対策を備えています。

---

## 重要な設計上の注意点・運用注意

- Look-ahead bias の防止:
  - AI スコア／レジーム判定／ETL などは target_date 引数を取り、内部で現在時刻を直接参照しないように実装されています。バックテストや再現性のある研究では必ず target_date を明示してください。
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env / .env.local を自動読み込みします。テスト時などに自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API キーと課金:
  - OpenAI や J-Quants の API キーは機密情報です。運用時は適切に管理してください。AI 呼び出しはコストが発生します。
- エラー時挙動:
  - 多くの API 呼び出しはリトライとフェイルセーフを持ちますが、部分失敗（例: AI レスポンス解析失敗）によりスコア取得が不足することがあります。ETLResult や quality モジュールの出力を監視してください。
- DuckDB の executemany:
  - 一部の DuckDB バージョンでは executemany に空リストを渡せない制約があります（コード内でチェック済み）。運用スクリプトでも入力が空か確認することを推奨します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

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
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - (その他モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (監視関連モジュールは __all__ に含まれる想定)
  - strategy/ (戦略実装用スペース)
  - execution/ (発注 / ブローカー連携用スペース)

---

## よくある質問（FAQ）

- Q: 環境変数が読み込まれない
  - A: プロジェクトルート判定は __file__ からの親ディレクトリ探索に基づきます。テスト環境や別作業ディレクトリから実行する場合、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして手動で環境変数を読み込むか、明示的に os.environ を設定してください。
- Q: OpenAI のレスポンスがパースできないときは？
  - A: news_nlp / regime_detector は JSON パース失敗時にログを出し、該当銘柄はスキップまたは macro_sentiment=0.0 にフォールバックします。原因解析のためログを確認してください。
- Q: DuckDB のスキーマが無い／テーブルがない
  - A: ETL や audit 初期化関数を呼んでスキーマを作成してください。audit.init_audit_db は監査スキーマを初期化します。data.schema によるスキーマ初期化用のユーティリティをプロジェクトで提供している場合はそちらを利用してください。

---

## 貢献・開発

- 開発する際は仮想環境を使用し、静的解析・ユニットテストを追加してください。
- 外部 API を叩くコードはモック化（unittest.mock.patch）可能な実装になっています。テストでは外部呼び出しをモックして安定したテストを実行してください。

---

この README はコードベースの主要な使い方と設計・運用上のポイントをまとめたものです。より詳細な動作仕様や API ドキュメントは各モジュールの docstring を参照してください。質問や追加ドキュメントが必要であれば知らせてください。