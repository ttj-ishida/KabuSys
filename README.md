# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants） → データ品質チェック → 特徴量計算 → ニュースNLP（OpenAI） → 戦略 / 監査ログまでをカバーするモジュール群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境変数設定管理
  - `.env` / `.env.local` 自動読み込み（プロジェクトルート検出、必要に応じて無効化可能）
  - 必須設定を Settings クラスで型安全に取得

- データ取得 / ETL（J-Quants API）
  - 日次株価（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーの差分取得
  - レートリミッティング、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）

- データ品質チェック
  - 欠損、主キー重複、スパイク、日付不整合（未来日・非営業日）検出
  - QualityIssue 型で問題を集約

- ニュース収集 / 前処理
  - RSS 取得（SSRF 対策・リダイレクト検査・受信サイズ制限）
  - URL 正規化、トラッキングパラメータ除去、記事ID生成（SHA256）

- ニュース NLP（OpenAI）
  - 銘柄単位に記事をまとめて LLM に投げ、スコア（-1.0 〜 1.0）を ai_scores に保存
  - チャンク処理、リトライ、レスポンスバリデーション

- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成し
    日次で market_regime に保存（'bull' / 'neutral' / 'bear'）

- 研究用ユーティリティ（Research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC 計算、統計サマリ関数、Z スコア正規化

- 監査ログ（Audit）スキーマ
  - signal_events / order_requests / executions の冪等テーブル、インデックス、初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 のユニオン型表記を使用）
- duckdb, openai, defusedxml 等のライブラリが必要

1. リポジトリをクローン / コピー
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境（任意）を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # 開発インストール:
   pip install -e .
   ```

   ※ requirements.txt / pyproject.toml がある場合はそちらを使用してください。

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` と `.env.local` を置くことで自動読み込みされます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   代表的な環境変数（最低限必要なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
   - KABU_API_PASSWORD: kabu ステーション API 用パスワード（必要に応じて）
   - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - LOG_LEVEL, KABUSYS_ENV 等

   例 `.env`（最小）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な操作サンプル）

以下は簡単な Python スニペットです。適宜ロギングやエラーハンドリングを追加してください。

- DuckDB 接続を得る（ファイル DB）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しない場合は今日が使われます
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # APIキーを引数で渡すことも可能（None の場合は OPENAI_API_KEY 環境変数を参照）
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("ai_scores 書き込み件数:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions が作成されます
  ```

- 研究用ファクター計算例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

---

## 設定管理の注意点

- Settings クラスはプロパティで値を取得します。必須設定が欠けていると ValueError を送出します。
  - 例: settings.jquants_refresh_token は JQUANTS_REFRESH_TOKEN が未設定だと例外

- 自動 .env 読み込み
  - プロジェクトルートを .git または pyproject.toml で検出して `.env` と `.env.local` を読み込みます。
  - テスト等で自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - OS 環境変数は保護され、.env の値で上書きされません（`.env.local` は override=True だが既存 OS キーは保護）。

---

## ディレクトリ構成

主なソース構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP スコアリング
    - regime_detector.py          — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント & 保存処理
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py      — 市場カレンダー管理（営業日判定等）
    - news_collector.py           — RSS 収集・前処理
    - quality.py                  — データ品質チェック
    - stats.py                    — 統計ユーティリティ（zscore_normalize）
    - audit.py                    — 監査ログスキーマ初期化
    - etl.py                      — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py          — モメンタム/バリュー/ボラティリティ
    - feature_exploration.py      — 将来リターン / IC / サマリ
  - ai、data、research の他に strategy / execution / monitoring 等のサブパッケージが想定されています（パッケージ __all__ に含まれています）

簡易ツリービュー（抜粋）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ quality.py
│  ├─ news_collector.py
│  ├─ calendar_management.py
│  ├─ stats.py
│  └─ audit.py
└─ research/
   ├─ __init__.py
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## 運用上のヒント / 注意事項

- Look-ahead バイアス防止:
  - 多くの関数は内部で datetime.today()/date.today() を直接参照せず、target_date 引数ベースで動作します。バックテストの際は target_date を適切に指定してください。

- OpenAI / J-Quants の API 呼び出し:
  - ネットワーク障害やレート制限が起こり得るため、ライブラリ側でリトライおよびフォールバック（スコア 0.0 など）を実装していますが、運用側でも適切な監視とエラーハンドリングを実装してください。

- DuckDB の executemany 空リスト注意:
  - 一部の DuckDB バージョンでは executemany に空リストを渡すとエラーとなるため、コード内で空チェックが行われています。運用での DB バージョン差に注意してください。

- セキュリティ:
  - news_collector は SSRF 対策、XML の defusedxml、受信サイズ制限などの保護を実装していますが、外部ソースの扱いは慎重に。RSS ソースは信頼できるものに限定してください。

---

## ライセンス / 貢献

（ここにライセンス情報や貢献方法を追記してください。）

---

README の内容やサンプルに追加して欲しい項目（例: CLI 実行方法、unit tests、CI 設定など）があれば教えてください。