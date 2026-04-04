# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング（OpenAI）、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注→約定トレース）などの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価（日足）・財務（四半期）・マーケットカレンダーを差分で取得・保存
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL 実行結果を ETLResult で集約（品質チェック含む）
- ニュース収集 / 前処理
  - RSS フィード取得（SSRF 対策・レスポンスサイズ制限）
  - URL 正規化・記事 ID（SHA-256 切り出し）による冪等保存
- ニュース NLP（OpenAI）
  - 銘柄単位のニュースセンチメントを LLM（gpt-4o-mini）でスコア化し ai_scores へ書き込み
  - レート制限・リトライ・レスポンス検証・チャンク処理対応
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成し
    日次で 'bull' / 'neutral' / 'bear' を判定して market_regime に保存
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェックの実装（QualityIssue）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化等
- 監査ログ（Audit）
  - signal → order_request → executions までのトレーサビリティ用テーブルの初期化・管理
- 設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で設定にアクセス

---

## 必要条件

- Python 3.10 以上（PEP 604 の型構文などを使用）
- 推奨ライブラリ（主な依存）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt があればそれを利用してください。なければ上記をインストールしてください:
pip install duckdb openai defusedxml）

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン
  - KABU_API_PASSWORD : kabu ステーション API パスワード（発注系を使う場合）
- OpenAI
  - OPENAI_API_KEY : OpenAI 呼び出しに必要（news_nlp / regime_detector）
- 任意 / デフォルトあり
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV (development | paper_trading | live; default: development)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- 自動 .env ロードの制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

.env の読み込み順序:
OS 環境 > .env.local > .env（プロジェクトルートは .git または pyproject.toml を基準に検出）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワークツリーを移動
   - （プロジェクトルートは .git または pyproject.toml がある場所）
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて他のライブラリもインストール）
4. 環境変数設定
   - プロジェクトルートに .env（および .env.local）を作成
   - 例（.env）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=your_kabu_password
   - 自動読み込みが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. DuckDB データディレクトリを用意（デフォルト data/）
   - mkdir -p data

---

## 使い方（代表的な API と実行例）

以下は簡単な利用例です。実行前に環境変数を正しく設定してください。

- settings の参照
  - from kabusys.config import settings
  - settings.jquants_refresh_token などでアクセス（未設定時は ValueError が発生）

- DuckDB 接続例
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（prices / financials / calendar / 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=None)  # target_date=None → 今日（ただし ETL 内で営業日に調整）
  - print(result.to_dict())

- ニュース NLP スコアリング
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → 環境変数 OPENAI_API_KEY を使う
  - print(f"scored {count} symbols")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査スキーマの初期化（監査 DB を別ファイルで作る例）
  - from pathlib import Path
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db(Path("data/audit.duckdb"))
  - # これで監査用テーブルが作成される

- RSS フィードを取得する（ニュース収集ヘルパー）
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  - for a in articles: print(a["title"], a["datetime"], a["url"])

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数でキー注入可能（テスト容易性）
- ETL / AI 関数はルックアヘッドバイアスに配慮して設計されています（内部で date.today() を直接参照しない等）
- エラーハンドリング: 多くの処理は API エラー発生時にフェイルセーフ（スキップ・0 戻し）します。ログ（logger）を確認してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                   — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py               — ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py        — 市場レジーム判定（MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（取得＋保存）
  - pipeline.py               — ETL パイプライン（run_daily_etl 等）
  - etl.py                    — ETLResult の再エクスポート
  - news_collector.py         — RSS ニュース収集
  - calendar_management.py    — マーケットカレンダー管理（営業日判定等）
  - quality.py                — データ品質チェック
  - stats.py                  — 統計ユーティリティ（zscore_normalize）
  - audit.py                  — 監査テーブルの初期化/管理
- research/
  - __init__.py
  - factor_research.py        — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py    — 将来リターン / IC / 統計サマリー 等
- research/*（上記モジュールをエクスポート）
- その他: strategy / execution / monitoring（パッケージ初期化で __all__ に含まれる想定）

> README 上では要点を抜粋しています。実装ファイル内に詳細な docstring（処理フロー・設計方針）があるため、個別機能の動作は該当モジュールの docstring を参照してください。

---

## トラブルシューティング / よくある注意点

- 環境変数が足りないと settings のプロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN 未設定）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは料金・レート制限に注意してください。news_nlp/regime_detector は各種リトライ・フォールバック実装済みですが、API キーや課金状況に依存します。
- DuckDB の executemany はバージョンによって空リストバインドに制約があるため、実装は空リストをチェックしてから executemany を呼び出すようになっています。

---

## 貢献 / 拡張

- 新しいニュースソースの追加（DEFAULT_RSS_SOURCES に登録し、news_collector を利用）
- 研究向け指標の追加は kabusys.research 以下に新関数を追加し __init__.py で公開
- 発注・ブローカー連携部分は分離設計のため、execution / monitoring モジュールを拡張して実装してください

---

この README はコード内の docstring を要約して作成しています。個々の関数の使用例や詳細は該当モジュールのドキュメント（ソース内の docstring）を参照してください。質問や追加の README 展開（例: デプロイ手順、CI 設定、より詳細な使用例）が必要であれば教えてください。