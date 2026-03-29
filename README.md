# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データのETL（J-Quants）、ニュース収集とNLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ等のユーティリティを提供します。

## 主な特徴（機能一覧）
- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、JPXマーケットカレンダーを差分取得・保存（DuckDB）
  - 差分取得、バックフィル、自動トークンリフレッシュ、レートリミット管理、リトライ
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（quality モジュール）
- ニュース収集・前処理
  - RSS フィード収集（SSRF対策、トラッキングパラメータ除去、gzip対応）、raw_news / news_symbols への冪等保存
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュースを統合して LLM によるセンチメント（ai_scores）を取得（バッチ・リトライ・レスポンス検証）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM センチメントの合成）
- 研究用ユーティリティ
  - Momentum / Value / Volatility 等のファクター計算、将来リターン、IC 計算、Zスコア正規化
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 をトレースするテーブル群と初期化ヘルパー（DuckDB）

---

## 必要条件 / 依存
- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants, OpenAI, RSS フィード）

（プロジェクトの setup.cfg/pyproject.toml がある前提で pip install してください）

---

## セットアップ手順

1. リポジトリをクローン・移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. パッケージのインストール
   - プロジェクトのパッケージ管理（pyproject.toml / requirements.txt）がある場合はそれに従ってください。例:
     ```bash
     pip install -e .            # 開発インストール
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` を配置すると自動で読み込まれます（パッケージ import 時に自動ロード）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。
   - 必須環境変数（少なくとも実行する機能に応じて設定が必要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API（発注）用パスワード
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（score_news / regime などで使用）
   - データベースのパス（任意、デフォルトを使用可能）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（代表的な呼び出し例）

以下は Python から直接呼ぶ例です。すべて DuckDB の接続オブジェクトを受け取る設計のため、まず接続を作成してから各機能を利用します。

- DuckDB 接続
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア（OpenAI API キーを環境変数で用意）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジーム（MA200 と マクロニュースの LLM スコア合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログの初期化（監査用の DuckDB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算例
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  ```

備考:
- OpenAI 呼び出しはネットワークと API キーが必要です。API 呼び出しはリトライ・フェイルセーフ設計になっており、失敗時はスコアを 0 として継続する箇所があります。
- ETL や保存処理は冪等化（ON CONFLICT DO UPDATE 等）されています。

---

## よく使う設定 / 環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須: J-Quants 認証)
- KABU_API_PASSWORD (発注連携で使用)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
- OPENAI_API_KEY (OpenAI を利用する機能で必要)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 （自動 .env ロードを無効化）

---

## ディレクトリ構成（抜粋）
（リポジトリルートを想定。src 配下にパッケージが配置されています。）

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数・設定管理（自動 .env ロード）
    - ai/
      - __init__.py
      - news_nlp.py              — ニュースNLP（OpenAI）スコアリング
      - regime_detector.py       — 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py        — J-Quants API クライアント + DuckDB 保存
      - pipeline.py              — ETL パイプライン（run_daily_etl 等）
      - etl.py                   — ETLResult エクスポート
      - calendar_management.py   — マーケットカレンダー管理（営業日判定等）
      - news_collector.py        — RSS ニュース収集
      - quality.py               — データ品質チェック
      - stats.py                 — 統計ユーティリティ（zscore 等）
      - audit.py                 — 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py       — Momentum / Value / Volatility 等
      - feature_exploration.py   — 将来リターン・IC・統計サマリー
    - ai/、data/、research/ の各ユーティリティ群
- pyproject.toml / setup.cfg / requirements.txt（存在する場合は依存管理）

---

## 注意事項 / 設計上のポイント
- ルックアヘッドバイアス防止: 多くのモジュールは datetime.today() や date.today() を直接参照しない設計で、ETL や研究処理は明示的な target_date を受け取ります。
- 冪等性: DB への保存は基本的に ON CONFLICT DO UPDATE 等で冪等化されています。
- フェイルセーフ: API の一時失敗時は適切にリトライし、致命的でない場合は処理を継続します（例: LLM 呼び出し失敗時にスコアを 0 とする等）。
- セキュリティ: RSS 収集では SSRF 対策、XML の defusedxml 利用、レスポンスサイズ制限などを実装しています。
- DuckDB バージョン差異等に配慮した実装（executemany の空リスト回避等）があります。

---

## サポート / 開発に関する備考
- テスト・CI の仕組みがある場合はそのルールに従ってください（この README にはテスト手順は含めていません）。
- 新しい機能追加や API 仕様変更時は J-Quants / OpenAI のレートやレスポンス形式に注意してください。

---

この README はコードベースの主要部分に基づいて作成しています。実運用では .env.example を整備し、セキュリティ（シークレット管理）・監視・ロギング設定を適切に行ってください。