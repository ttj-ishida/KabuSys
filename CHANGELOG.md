# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
リリース日はコードベースから推測した日付を使用しています。

全般的な注意
- このリポジトリは日本株の自動売買/データ基盤/研究用途を対象としたライブラリです。内部で DuckDB をデータストア、OpenAI（gpt-4o-mini）を NLP 用 LLM、J-Quants / kabu ステーション等の外部 API を利用する前提になっています。
- 環境変数管理や .env 自動ロード、DB への冪等（idempotent）書き込み、LLM 呼び出し時のリトライ＆フォールバックなど、運用を重視したフェイルセーフ設計が取り入れられています。

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-03-31
初回リリース（推定）。主要機能と実装上の設計方針をまとめます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期公開。パッケージエクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）。
  - バージョン: 0.1.0

- 設定・環境変数管理 (src/kabusys/config.py)
  - Settings クラスを導入し、アプリケーション設定を環境変数から取得する API を提供。
  - 必須設定を _require() で検査（未設定時は ValueError を送出）。
  - 有効な環境: development / paper_trading / live。LOG_LEVEL のバリデーション。
  - デフォルト DB パス: DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）。
  - .env 自動ロード機能：
    - プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動で読み込む。
    - export KEY=val 形式、クォート、エスケープ、コメント（#）処理に対応したパーサ実装。
    - OS 環境変数は protected として .env による上書きを抑止。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可。

- Data / ETL / カレンダー (src/kabusys/data/)
  - calendar_management:
    - market_calendar を用いた営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする設計。
    - calendar_update_job により J-Quants から差分取得して冪等的に保存（バックフィル・健全性チェックあり）。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得／保存件数、品質チェック結果、エラー一覧を保持）。
    - 差分取得・バックフィル・品質チェックを想定した ETL 基盤（jquants_client を経由した保存処理想定）。
    - _get_max_date 等ユーティリティ実装。

- AI（ニュース NLP / レジーム判定） (src/kabusys/ai/)
  - news_nlp.score_news:
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出。
    - 一度に最大 20 銘柄のバッチ送信、1 銘柄あたり記事数・文字数上限（トリム）を実装。
    - JSON Mode を用いた厳格な JSON 応答検証（results リスト、code/score のバリデーション）。
    - リトライ（429, ネットワークエラー, タイムアウト, 5xx）を指数バックオフで実装。非リトライ対象エラーはスキップして継続（フェイルセーフ）。
    - DuckDB に対する書き込みは対象コードのみを DELETE → INSERT することで部分失敗時の保護を実現。
    - calc_news_window による JST/UTC のウィンドウ計算（前日15:00 JST 〜 当日08:30 JST を対象）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロニュースセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
    - ma200_ratio の計算、マクロニュース絞込み（マクロキーワード群）→ OpenAI による JSON レスポンス取得 → スコア合成。
    - LLM 呼び出しでのリトライ＆フォールバック（API 失敗時は macro_sentiment = 0.0）。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI API キーは引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。

- Research（因子計算 / 特徴量探索） (src/kabusys/research/)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離率）を DuckDB SQL による高速計算で提供。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から最新財務データを引き、PER / ROE を計算（EPS が 0/欠損時は None）。
    - 設計方針: DuckDB の SQL ウィンドウ関数を活用し、外部 API にはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一括算出。
    - calc_ic: スピアマンのランク相関（IC）を実装。十分な有効レコードがない場合は None を返す。
    - rank: 平均ランク（同順位は平均ランク）を算出（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。

### 変更 (Changed)
- 初回公開に伴い、コードは運用を想定した堅牢なデフォルト挙動（リトライ・フェイルセーフ・冪等書き込み・タイムゾーン扱い・ルックアヘッドバイアスの回避）を採用。

### 修正 (Fixed)
- 初期実装段階の挙動（例: DuckDB の executemany に空リストを渡さない等の互換性対応）を含めて実装済み。

### セキュリティ (Security)
- 環境変数の必須チェック（API キー系）を追加。OpenAI や各 API のキーが未設定時は ValueError を投げ、誤操作で空キーが渡らないように設計。
- .env ファイルの読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用）。

### 既知の設計上の注意点
- DuckDB へは SQL（主にウィンドウ関数）でデータ参照/書き込みを行うため、DuckDB のバージョン互換性に注意（コード内に互換性対策あり）。
- OpenAI 呼び出し部は JSON Mode を前提とするため、将来の API 仕様変更時はパース処理の確認が必要。
- news_nlp / regime_detector ともに外部 API 장애時はスコアを 0.0 にフォールバックするなど保守的に設計しているため、LLM に依存する機能はモデル運用状況に応じた挙動変化が発生します。
- time / date の扱いはルックアヘッドバイアス防止のため、内部で datetime.today() や date.today() を参照しない設計（関数呼び出し側で target_date を明示する）。

---

開発者向けメモ（省略可能）
- 主要な公開 API:
  - settings (kabusys.config.Settings インスタンス)
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
  - kabusys.data.ETLResult（pipeline から再エクスポート）
- 必要な主な環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (任意), SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL

（以上）