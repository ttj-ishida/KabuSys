# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。初回公開バージョンとして以下を記録します。

## [0.1.0] - 2026-04-09

### 追加 (Added)
- 全体
  - パッケージ初期リリース。パッケージ名: kabusys。バージョンは src/kabusys/__init__.py の __version__ にて "0.1.0" を提供。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を検出して行う（CWD 非依存）。
  - .env パーサ実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理などに対応。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - J-Quants / kabuステーション / LINE / DB パス / PaperTrading 設定 / 監視閾値 / ログ・環境判定など多数のプロパティを公開。
    - 必須値取得用の _require を実装（未設定時は ValueError）。
    - PAPER_FILL_MODE（instant/partial/never/reject）などのバリデーションを実装。
    - KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL のバリデーションを実装。

- データ関連 (kabusys.data)
  - calendar_management モジュール:
    - market_calendar テーブルを用いた営業日判定機能を提供。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB 未登録日のフォールバック（曜日ベース）を備え、一貫性のある挙動を保証。
    - 夜間バッチ calendar_update_job を実装。J-Quants クライアントから差分取得し冪等保存（バックフィル・健全性チェック付き）。
    - 最大探索日数やバックフィル日数などの安全パラメータを導入。
  - ETL パイプライン関連:
    - ETLResult データクラスを実装（pipeline モジュール）。ETL 実行の取得数/保存数/品質問題/エラーを集約。
    - data.etl で ETLResult を再エクスポート。

- AI / NLP (kabusys.ai)
  - news_nlp モジュール:
    - raw_news + news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメント（ai_score）を算出。
    - calc_news_window、score_news、内部の API 呼び出し・レスポンス検証・スコアクリップ・リトライ（429/ネットワーク/5xx）・DuckDB 互換性対策（executemany の空リスト回避）等を実装。
    - スコアが取得できた銘柄のみを DELETE → INSERT で置換することで部分失敗時のデータ保全を実現。
  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成し、市場レジーム（bull/neutral/bear）を日次で判定して market_regime テーブルへ冪等書き込み。
    - _calc_ma200_ratio、_fetch_macro_news、_score_macro、score_regime を実装。
    - OpenAI 呼び出しの堅牢化（リトライ、エラー種別の分岐、フェイルセーフで macro_sentiment=0.0 等）を実装。
    - 設計上、ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない実装方針を採用。

- リサーチ / ファクター (kabusys.research)
  - factor_research モジュール:
    - calc_momentum（1M/3M/6M リターン、ma200 乖離）、calc_volatility（20日 ATR、相対ATR、出来高関連）、calc_value（PER/ROE）を実装。
    - DuckDB 内 SQL とウィンドウ関数を利用した高効率な実装。
    - データ不足・条件不成立時は None を返す等の安全設計。
  - feature_exploration モジュール:
    - calc_forward_returns（複数ホライズンに対応）、calc_ic（スピアマンランク相関）、rank（同順位は平均ランク）、factor_summary（基本統計量）を実装。
    - 外部依存を持たない純粋な標準ライブラリ実装。Research 利用に合わせた出力フォーマット。

- パッケージのエクスポート整理
  - 各サブパッケージから主要関数/ユーティリティを __all__ で公開（例: kabusys.ai.score_news, kabusys.research の関数群, kabusys.data.ETLResult など）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 環境変数（API キー等）は OS 環境もしくは .env/.env.local により注入する想定。自動 .env ロードはプロジェクトルートの検出を行い、必要に応じて無効化する環境変数を提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

## 備考 / マイグレーションノート
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション API）
  - OPENAI_API_KEY（news_nlp / regime_detector を利用する場合）
- 設定可能な主要環境変数:
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH / PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等。
- PAPER_FILL_MODE の有効値: "instant", "partial", "never", "reject"（大文字小文字を無視して判定）。
- KABUSYS_ENV の有効値: "development", "paper_trading", "live"。
- DuckDB に対する互換性対策:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）への対処を行っているため、部分的に空チェックがある。
- 設計上の注意:
  - ルックアヘッドバイアス防止のため、日付計算は全て呼び出し元で与える target_date ベースで行う設計です。内部での現在時刻参照は避けています。
  - OpenAI 呼び出しはリトライとフェイルセーフ（失敗時にスコアを 0.0 とする等）を備えていますが、API レートやコストに注意してください。
- 未実装 / TODO:
  - 一部機能（例: PBR・配当利回り等のバリューファクター、monitoring パッケージの実体）はこのリリースで未提供の可能性があるため、今後追加予定です。

もし CHANGELOG に加えたい日付の修正や、より詳細なカテゴリ分け（例: テーブルスキーマ変更、API 互換性注意事項など）が必要であれば教えてください。