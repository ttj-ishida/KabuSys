KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

## [0.1.0] - 2026-03-29
初回公開リリース。

### 追加
- パッケージの初期構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）
  - バージョン: 0.1.0

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルの自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）
  - .env の文法パーサーを実装（export KEY=val、クォート内のバックスラッシュエスケープ、コメント処理等に対応）
  - 読み込み優先順位: OS 環境変数 > .env.local（上書き）> .env（未設定時にセット）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
  - 環境変数保護（OS 環境変数を protected set として上書きから保護）
  - Settings クラスを実装し、主要設定に対するプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト）,
      SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパスの既定値: DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db)
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の便宜プロパティ
  - 必須設定未定義時は _require() が ValueError を投げる挙動を定義

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news / news_symbols を集約して銘柄毎のテキストを作成
    - タイムウィンドウ計算（JST基準 → DBは UTC）: calc_news_window 実装
    - OpenAI（gpt-4o-mini、JSON Mode）呼び出しを行い銘柄ごとのセンチメントを取得
    - バッチ処理（最大 20 銘柄 / チャンク）、1銘柄あたり記事数・文字数のトリム実装
    - 429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフリトライ
    - レスポンスの厳密なバリデーションとスコア ±1.0 のクリップ
    - ai_scores テーブルへ冪等（DELETE → INSERT）での書き込み。部分失敗時に既存データ保護
    - テスト容易性: _call_openai_api をパッチ差し替え可能
    - 関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）と
      マクロ経済ニュースの LLM センチメント（重み 30%）を合成して
      日次で市場レジーム（bull/neutral/bear）を判定
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドを防止
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、リトライとフェイルセーフ（API 失敗時は macro_sentiment = 0）
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - テスト容易性: _call_openai_api を差し替え可能
    - 関数: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す

- データ管理モジュール (src/kabusys/data)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを参照して is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar 未取得時は曜日ベースのフォールバック（土日を休日扱い）
    - 異常検知（未来日付が極端に大きい等）や最大探索日数制限を実装
    - JPX カレンダーの差分取得バッチ job: calendar_update_job (jquants_client との fetch/save を利用、バックフィル含む)
  - ETL パイプライン補助 (pipeline.py / etl.py)
    - ETLResult データクラスを追加（ETL の取得数・保存数、品質問題、errors 等を格納）
    - 複数ユーティリティ: テーブル存在チェック、最大日付取得、トレード日調整等
    - パイプラインの設計方針やバックフィル挙動、品質チェックの扱いをコード化
    - etl.py で pipeline.ETLResult を再エクスポート

- Research（調査）モジュール (src/kabusys/research)
  - ファクター計算 (factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率（部分ウィンドウでも算出）
    - calc_value: raw_financials から直近財務を取得して PER / ROE を計算
    - DuckDB 上の SQL と最小限の Python で実装。prices_daily / raw_financials のみ参照
  - 特徴量探索 (feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括算出
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（有効レコード 3 未満は None）
    - rank: 同順位の平均ランク化（丸め処理で ties の安定化）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出
  - research パッケージで主要関数を再エクスポート（zscore_normalize は data.stats から）

- パッケージ初期化 / エクスポート
  - ai, research パッケージで主要関数を __all__ にて公開（例: score_news, score_regime 等）

### 既知の設計上の注意・制約
- OpenAI API 呼び出しは gpt-4o-mini を前提に JSON Mode を利用。API レスポンスや SDK の仕様変更を考慮した例外処理を実装しているが、モデル／SDK の大幅変更時は追加対応が必要になる可能性あり。
- DuckDB 0.10 の挙動（executemany に空リストを渡せない等）を考慮した実装が含まれる。
- jquants_client（J-Quants API との接続・保存処理）は参照しているが、本リリースでのクライアント実装の有無により外部連携が必要。
- 一部関数は外部リソース（DB, OpenAI）への依存が強いため、ユニットテスト時は _call_openai_api のパッチや DB のモックを推奨。
- 日時の取り扱いはルックアヘッドバイアス防止のため datetime.today()/date.today() の直接参照を避けるよう設計されている点に注意。

### 変更
- なし（初版）

### 修正
- なし（初版）