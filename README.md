# KabuSys — 日本株自動売買システム

簡潔な説明:
KabuSys は日本株のデータプラットフォーム、リサーチ、AI ベースのニュースセンチメント解析、監査ログを備えた自動売買基盤のライブラリ群です。J-Quants / kabuステーション / OpenAI 等と連携して、ETL、品質チェック、ファクター計算、ニュース NLP、マーケット・レジーム判定、監査ログ初期化などを提供します。

---

## 主な機能
- データ取得・ETL
  - J-Quants API から株価（日足）、財務、上場銘柄情報、マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分更新 / バックフィル / ページネーション対応 / レート制限・リトライ
- データ品質チェック
  - 欠損、重複、将来日付、スパイク（急騰・急落）検出
- ニュース収集・NLP
  - RSS 収集（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメントスコアリング（ai_scores へ保存）
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離 + マクロ記事の LLM センチメントを合成して日次で bull/neutral/bear を判定
- リサーチ/ファクター計算
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Spearman）やファクター統計要約
- 監査ログ（トレーサビリティ）
  - シグナル → 発注 → 約定まで追跡可能な監査テーブルの初期化ユーティリティ（DuckDB）
- 設定管理
  - .env / .env.local / 環境変数の読み込み（プロジェクトルート検出、自動ロードを無効化可能）

---

## 要件（想定）
- Python 3.10+
- ライブラリ（少なくとも以下が必要）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ多数）

（実際の requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール
   - 開発環境例:
     - git clone ...
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e .  （setup がある場合）または必要パッケージを pip install duckdb openai defusedxml

2. 環境変数 (.env) を作成
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として下記を設定します。
   - 自動読み込み:
     - パッケージ読み込み時に OS 環境変数 > .env.local > .env の順で読み込まれます。
     - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等）。

   必須の環境変数（少なくとも下記を設定してください）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN — Slack 通知を利用する場合
   - SLACK_CHANNEL_ID — Slack 通知先チャンネル
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - OPENAI_API_KEY — OpenAI を利用する場合（score_news / score_regime の呼出し時に引数で渡すことも可）

   任意 / デフォルトあり:
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

3. DB 初期化（監査ログ用の例）
   - 監査ログテーブルを用いる場合は DuckDB を作成して初期化します（親ディレクトリがなければ自動作成）。
   - Python 例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db("data/audit.duckdb")
     # conn は初期化済みの DuckDB 接続
     ```

---

## 使い方（代表的な例）

- DuckDB 接続の作成（ETL / AI / Research 共通）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を渡すことも可
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI API キーが必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算 / リサーチ機能例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # z-score 正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 監査ログスキーマの初期化（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

---

## 自動環境変数ロードの振る舞い
- パッケージ読み込み時にプロジェクトルート（.git か pyproject.toml の存在）を基準に `.env` と `.env.local` を自動読み込みします。
- 読み込み順: OS 環境変数（最優先） → .env.local（上書き） → .env（未設定キーのみ）
- 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すれば自動ロードを行いません（テスト向け）。

.env ファイルのパースは一般的な形式（KEY=val、export KEY=val、クォートやインラインコメントなど）に対応しています。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント解析（OpenAI）
    - regime_detector.py  — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント + DuckDB 保存
    - pipeline.py         — ETL パイプライン & run_daily_etl
    - etl.py              — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py   — RSS 収集・前処理
    - quality.py          — データ品質チェック
    - calendar_management.py — 市場カレンダー管理
    - audit.py            — 監査ログテーブル初期化
    - stats.py            — 共通統計ユーティリティ (zscore_normalize)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

---

## 運用上の注意・ベストプラクティス
- OpenAI 呼び出しや外部 API は料金・レート制限に注意して利用してください。
- look-ahead バイアスを防ぐため、本ライブラリの多くの関数は date を明示的に受け取り、内部で現在日時を参照しない設計です。バックテスト時は ETL で事前に必要なデータを確保してから利用してください。
- ETL は各ステップでエラーを独立にハンドリングするため、部分的な失敗があっても全体処理を継続します。結果は ETLResult で確認してください。
- DuckDB の executemany に空リストを渡せないバージョンの互換性考慮がコード内にあります。DuckDB のバージョンに留意してください。
- ニュース収集には SSRF / XML Bomb 等の対策を実装していますが、外部 URL の扱いには引き続き注意が必要です。

---

## テスト・開発向けフック
- 環境の自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ai モジュール内の OpenAI 呼び出しは内部でラッパー関数に切り出されており、単体テスト時はこれらをパッチしてモックできます（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。

---

## 問い合わせ / 貢献
- バグ報告や機能提案は issue にお願いします。
- コントリビュートの際は tests / linters を追加していただけると助かります。

---

README の内容は実装ファイルのコメント・関数仕様に基づいています。詳細な API 仕様や運用手順は各モジュールの docstring や実装コメントも参照してください。