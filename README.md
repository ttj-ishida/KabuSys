# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants / kabuステーション / OpenAI 等と連携して、データ収集（ETL）、データ品質チェック、ニュースNLP（LLM）による銘柄スコアリング、マーケットレジーム判定、因子計算、監査ログ（監査テーブル）などを提供します。

主な設計方針は「バックテストでのルックアヘッドバイアス防止」「ETL の冪等性」「外部 API 呼び出しの堅牢化（リトライ・レート制御）」「DuckDB を中心としたローカルデータ管理」です。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション・リトライ・レートリミット対応）
  - 差分更新・バックフィル機能
  - ETL 結果の品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集 / NLP
  - RSS フィードからのニュース収集（SSRF 対策・トラッキング除去・前処理）
  - OpenAI（gpt-4o-mini）による銘柄別ニュースセンチメント算出（ai_scores への保存）
  - ニュースウィンドウ計算（JST 基準で前日15:00〜当日08:30 相当）

- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュース LLM センチメントを重み合成して日次レジーム判定（bull/neutral/bear）

- 研究（Research）機能
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
  - Z-score 正規化ユーティリティ

- 監査（Audit）
  - シグナル → 発注 → 約定までの監査テーブル群（冪等キー・ステータス管理）を初期化するユーティリティ

- 設定管理
  - .env / .env.local /OS環境変数からの設定読み込み（自動ロード、優先順位管理）
  - 実行環境（development / paper_trading / live）やしきい値等のアクセス用プロパティ

---

## セットアップ手順

前提: Python 3.9+（型アノテーションで | を利用しているため）を推奨します。

1. リポジトリをクローン / パッケージディレクトリへ移動

2. 必要ライブラリをインストール（例）
   - 最低限必要な外部依存:
     - duckdb
     - openai
     - defusedxml
   - インストール例:
     ```bash
     python -m pip install duckdb openai defusedxml
     # または 開発モードでパッケージ化している場合
     pip install -e .
     ```

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` を作成すると自動で読み込まれます。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等）。
   - 主要な環境変数例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token  # 必須
     KABU_API_PASSWORD=your_kabu_api_password          # 必須
     OPENAI_API_KEY=sk-xxxx                             # LLM を使う機能で必要
     LINE_CHANNEL_ACCESS_TOKEN=                         # （任意）
     LINE_USER_ID=                                       # （任意）
     DUCKDB_PATH=data/kabusys.duckdb                    # デフォルト値
     SQLITE_PATH=data/monitoring.db                     # 監視用 sqlitePath（デフォルト）
     KABUSYS_ENV=development                            # development | paper_trading | live
     LOG_LEVEL=INFO
     ```

4. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単なコード例）

以下はライブラリの代表的な使い方例です。実行は Python スクリプト / REPL で行えます。

- DuckDB 接続を作って日次 ETL を回す例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path でのデフォルト
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別スコア）を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を .env 或いは引数で指定
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数等で設定
  ```

- 研究用ファクターを計算する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  val = calc_value(conn, date0)
  vol = calc_volatility(conn, date0)
  ```

- 監査テーブル（別 DB）を初期化する例:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可能
  ```

---

## 設定（主な環境変数）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（settings.jquants_refresh_token で参照）
  - KABU_API_PASSWORD — kabuステーション API のパスワード（settings.kabu_api_password）

- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector 等で使用（score_news / score_regime は引数で api_key を渡すことも可能）

- ログ / 環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

- DB パス等（settings.* が参照）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値など（監視機能向け）

- 自動 .env ロード制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数 / .env 読み込みと Settings API（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM ベーススコアリング（score_news）
    - regime_detector.py — ETF MA とマクロニュース LLM を使った市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存・レートリミット・リトライ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - calendar_management.py — JPX カレンダーの管理・営業日判定
    - news_collector.py — RSS ニュース収集（SSRF 対策・正規化・保存）
    - audit.py — 監査ログテーブル初期化 / DB 作成ユーティリティ
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - etl.py — ETLResult の再エクスポートインターフェース
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等の因子計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank 等
  - ai/regime_detector.py, ai/news_nlp.py の中で OpenAI の呼び出しは専用内部関数経由で行われ、テスト時に差し替えやすい設計

その他:
- .env/.env.local — 実行時の設定（プロジェクトルートに配置）
- data/ — デフォルトのデータベース・PID・フラグなどを置く場所（手動で作成）

---

## 注意事項 / 実装上のポイント

- DuckDB をローカル DB として想定しており、ETL の保存処理は ON CONFLICT DO UPDATE 等で冪等化されています。
- ニュース/LMM 呼び出しは rate limit とリトライの考慮が入っています。APIキー未設定時は関連機能は例外を投げます（score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY のいずれかが必要）。
- calendar / ETL 周りは市場営業日を考慮した設計で、calendar がない場合は曜日ベースでフォールバックします。
- テスト容易性のため、内部の API 呼び出し関数（例えば OpenAI 呼び出しや URL open）をモックしやすい構造になっています。
- セキュリティ面: news_collector は SSRF 対策（リダイレクト検査・プライベート IP 拒否）、defusedxml による XML パース防御等を組み込んでいます。

---

## 貢献 / 開発時のヒント

- 設定の自動ロードは config.py で行われます。テスト中や CI で .env 読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- OpenAI 呼び出し部分はテスト時に patch してレスポンスを差し替える想定（例: unittest.mock.patch）。
- DuckDB のバージョンによって executemany の挙動に注意（空リスト不可など）— pipeline 等では互換性を考慮した実装になっています。

---

README は以上です。必要であれば、具体的な .env.example、requirements.txt、起動スクリプト（CLI）例、あるいは各モジュールの詳細な API リファレンス（関数引数・戻り値の表）も追加で作成できます。どの箇所を詳しく書きたいか教えてください。