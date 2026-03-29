# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ収集（J-Quants、RSS）、ETL、データ品質チェック、ファクター／リサーチ、AI（ニュースNLP／市場レジーム判定）、および監査ログ（発注・約定トレース）までを含むモジュール群を提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易例）
- 環境変数一覧（主なもの）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株を対象としたデータプラットフォーム兼リサーチ／自動売買の基盤ライブラリです。  
主な特徴は次のとおりです。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得と DuckDB への冪等保存
- RSS によるニュース収集と前処理（SSRF対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント解析（ニュースNLP）と市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注から約定までの監査ログスキーマ（監査用の DuckDB 初期化ユーティリティ）
- 環境変数 / .env 自動読み込み（プロジェクトルート検出）機構

設計方針として、ルックアヘッドバイアスの排除、冪等性、フェイルセーフ（API障害時の安全なフォールバック）を重視しています。

---

## 機能一覧

- データ収集 / ETL
  - J-Quants から株価（日足）、財務データ、マーケットカレンダーの差分取得（ページネーション対応）
  - 差分保存（ON CONFLICT DO UPDATE）による冪等処理
  - ETL パイプライン（run_daily_etl）の提供
- ニュース収集
  - RSS 取得・正規化・前処理（URL除去・文字列正規化）
  - raw_news / news_symbols への冪等保存
  - SSRF / Gzipbomb / トラッキングパラメータ対策
- AI（OpenAI）
  - ニュースごとのセンチメントスコア算出（score_news）
  - ETF 1321 の MA とマクロ記事センチメントを合成した市場レジーム判定（score_regime）
  - レート制限・リトライ・レスポンス検証を考慮した実装
- 研究・ファクター
  - calc_momentum / calc_value / calc_volatility：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank：特徴量探索支援
  - zscore_normalize：Zスコア正規化ユーティリティ
- データ品質
  - 欠損、スパイク、重複、日付不整合チェック（run_all_checks）
  - QualityIssue データ構造による詳細レポート
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化（init_audit_db / init_audit_schema）
  - トレーサビリティ（UUID連鎖）を前提としたスキーマ
- 設定管理
  - 環境変数・.env 自動ロード（プロジェクトルート検出）
  - Settings クラスによる型付き設定取得

---

## セットアップ手順

1. Python のインストール（推奨: 3.10+）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - 最低限の依存（本リポジトリの setup/requirements が無い場合の例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （実運用では pyproject.toml / requirements.txt に従ってください）
4. プロジェクトルートに .env を用意
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. DuckDB 用ディレクトリを作成（デフォルト: data/kabusys.duckdb）
   - mkdir -p data
6. 監査ログ DB の初期化（任意）
   - Python スクリプト例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

注:
- 自動ロードは .env と .env.local をプロジェクトルートから順にロードします（OS環境変数優先）。
- テスト時など自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主なもの）

以下はコード内で参照される主要な環境変数です。必須のものは Settings._require により未設定時に例外を発生させます。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、値: development / paper_trading / live, default: development)
- LOG_LEVEL (任意、例: DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY (AI モジュールで使用。score_news/score_regime の api_key 引数で上書き可能)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意、1 を設定すると .env の自動読み込みを無効化)

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易例）

以下は最も基本的な操作例です。詳細は各モジュールのドキュメントを参照してください。

- DuckDB 接続の取得（例）
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメントをスコアリングする
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"scored {n_written} codes")

- 市場レジームを判定する
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- ファクター計算（例: モメンタム）
  from kabusys.research.factor_research import calc_momentum
  factors = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(factors))

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

注意:
- AI モジュールは OpenAI の API 呼び出しを行います。API キーと利用制限に注意してください。
- run_daily_etl 等は J-Quants API を叩きます。J-Quants の認証情報やレート制限に留意してください。
- production（本番売買）に移行する場合は settings.is_live フラグや kabu 発注フローを十分に検証してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py : パッケージエントリ（version 等）
- config.py : 環境変数 / Settings の実装、.env 自動ロード機構
- ai/
  - __init__.py
  - news_nlp.py : ニュースを集約して OpenAI に投げるロジック、score_news を提供
  - regime_detector.py : ETF 1321 の MA とマクロ記事センチメントを合成する市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py : ETL 用の公開インターフェース（ETLResult の再エクスポート）
  - news_collector.py : RSS 取得・前処理・ID生成・保存
  - calendar_management.py : 市場カレンダー管理／営業日判定／calendar_update_job
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py : 汎用統計ユーティリティ（zscore_normalize）
  - audit.py : 監査ログスキーマ定義と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py : モメンタム／バリュー／ボラティリティ計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー 等

各モジュールはドメインごとに分割されており、DuckDB 接続を受け取って SQL + Python で処理を行う設計です。バックテスト用ループから直接 API を叩かない等、ルックアヘッドバイアス回避の配慮があります。

---

## 運用上の注意点（抜粋）

- OpenAI / J-Quants など外部 API の呼び出しはコスト・レート制限・エラー処理に注意してください。各モジュールでリトライ／フェイルセーフが実装されていますが、運用設計は必須です。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に動作します。CI・テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に環境をコントロールしてください。
- DuckDB の executemany に関する挙動（空リスト不可等）を考慮したコードになっています。DuckDB のバージョンアップがある場合は互換性に留意してください。
- 監査ログは削除しない前提です（完全なトレーサビリティのため）。

---

必要であれば、README に掲載する具体的な .env.example（テンプレート）、requirements.txt の推奨内容、より詳しい利用例（ETL スケジュール／Slack 通知／kabu 発注フロー）を別途作成します。どの項目を追加したいか教えてください。