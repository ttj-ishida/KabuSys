# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトではセマンティックバージョニングを採用しています。

全般的な注意:
- 本リリースはライブラリの初期公開（0.1.0）相当の機能群を含みます。
- 多くの機能は DuckDB のスキーマ（prices_daily / raw_news / ai_scores / market_calendar / raw_financials 等）を前提としています。運用前に必要なテーブルが存在することを確認してください。
- OpenAI（gpt-4o-mini）および J-Quants など外部 API の利用が前提の機能があります。動作には各種環境変数の設定が必要です（詳細は「重要な環境変数」を参照）。

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージメタ:
    - src/kabusys/__init__.py に __version__ とパッケージ公開モジュール一覧を追加。
  - 環境変数 / 設定管理:
    - src/kabusys/config.py
      - .env および .env.local ファイルをプロジェクトルート (.git または pyproject.toml を基準) から自動読み込みする仕組みを実装。
      - エクスポート形式（export KEY=val）やクォート・エスケープ、行末コメントの取り扱いに対応するパーサー実装。
      - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - 環境変数を取得する Settings クラスを提供（プロパティ: jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev）。
      - env と log_level に対する入力値検証（許容値セットの定義）。
  - AI（自然言語処理）:
    - src/kabusys/ai/news_nlp.py
      - ニュース記事の銘柄単位センチメント評価を行い ai_scores テーブルへ書き込む処理を実装。
      - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）を calc_news_window で提供。
      - 記事の集約（news_symbols 結合）、1銘柄あたりの記事数・文字数トリム、バッチ（最大 20 銘柄）での OpenAI 呼び出し、JSON Mode を用いたレスポンス検証を実装。
      - API 呼出しのリトライ（429/接続断/タイムアウト/5xx）と指数バックオフを実装。失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
      - レスポンスバリデーションにより不正な出力は無視（安全側）、正常スコアは ±1.0 にクリップ。
      - テスト容易性のため _call_openai_api をパッチで差し替え可能に設計。
    - src/kabusys/ai/regime_detector.py
      - 日次の「市場レジーム判定（bull/neutral/bear）」ロジックを実装。
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成してスコア化。
      - マクロニュース抽出（キーワードフィルタ）、OpenAI 呼び出し（gpt-4o-mini、JSON Mode）、リトライ／フォールバック（API 失敗時 macro_sentiment=0.0）を実装。
      - 計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
  - データプラットフォーム・ETL:
    - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
      - ETL の公開インターフェース（ETLResult データクラス）を実装。ETLResult はフェッチ数・保存数・品質チェック結果・エラー概要などを保持。
      - DuckDB に対する差分取得 / backfill 方針を想定したユーティリティを提供。
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー（market_calendar）に関するユーティリティ群を提供:
        - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
      - calendar_update_job: J-Quants からカレンダーを差分取得して保存する夜間バッチ処理を実装（バックフィル、健全性チェック、ON CONFLICT 相当による冪等保存を想定）。
      - DB にデータがない場合の曜日ベースのフォールバック（主に土日判定）を実装。
  - 研究・ファクター分析:
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）等の計算関数を実装。全て DuckDB (prices_daily / raw_financials) を参照。
      - データ不足時の None ハンドリング、結果を (date, code) ごとの dict リストで返す設計。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、ランク化ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
      - pandas 等外部依存なしでの実装を意識。
    - src/kabusys/research/__init__.py に主要関数を再エクスポート。
  - テスト / 開発支援:
    - OpenAI 呼び出しをラップする内部関数（各 ai モジュールの _call_openai_api）はテスト時に patch して差し替え可能。
  - 互換性考慮:
    - DuckDB のバージョン差異への対応（executemany に空リスト不可など）を考慮した実装。

### Fixed
- （初回リリースのため該当なし）

### Changed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 外部 API キーやトークン（OpenAI、J-Quants、KabuStation、Slack 等）を環境変数で取得する設計。運用時は秘密情報の管理に注意してください（.env ファイルのアクセス制御等）。

## 重要な環境変数（本バージョンで使用されるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
- OPENAI_API_KEY: OpenAI 呼び出し（news_nlp / regime_detector 用、必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化するフラグ（任意）

## 既知の注意点 / 制約
- 多くの機能は DuckDB 内の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）が存在することを前提としています。スキーマ整備は利用者の責任です。
- OpenAI への問い合わせは gpt-4o-mini を前提にプロンプト（JSON Mode）で行いますが、API の挙動変化やモデル差異によりパース失敗が発生する可能性があります。失敗時は該当部分をスキップしてフェイルセーフ（0.0 など）で継続します。
- news_nlp のバッチサイズ・トリム設定は現状固定（最大 20 銘柄／チャンク、1銘柄あたり最大 10 記事・3000 文字）。必要に応じて調整してください。
- calendar_update_job は jquants_client モジュール（kabusys.data.jquants_client）に依存します。外部 API クライアントの実装／設定が必要です。
- テスト容易性のため OpenAI 呼び出しを抽象化していますが、実運用時はネットワークとコスト（API 使用量）に注意してください。

## マイグレーション / 利用開始メモ
- .env からの自動ロードはデフォルトで有効です。テスト環境や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑制してください。
- ETL / calendar 更新 / AI スコアリング等、順序はデータ依存があります（まず prices_daily, raw_news 等のデータを ETL によって整備した後に AI スコアリングや regime 判定を実行してください）。
- DuckDB の互換性（executemany の空リスト不可など）を考慮しているため、既存の DuckDB バージョンで問題が発生する場合はログとスタックトレースを確認してください。

---

今後の予定（例）
- AI モジュールの評価・プロンプト改良、モデル切り替えのための設定追加
- ETL のジョブ管理・スケジューリング周りのラッパー提供
- ユニットテストと CI の整備、モッククライアントを用いた回帰テスト

もし CHANGELOG に追加してほしい点や、特定モジュールについての詳細（例: API の戻り値のスキーマ、期待する DuckDB テーブル定義など）があれば教えてください。