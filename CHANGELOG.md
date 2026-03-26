# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-26

### Added
- パッケージ初版リリース (kabusys v0.1.0)
  - パッケージのエントリポイントを定義（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境変数・設定管理モジュール（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml ベース）から自動ロードする機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト向け）。
  - .env パース実装：
    - コメント行、export プレフィクス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 上書きポリシー：
    - .env は既存 OS 環境変数を上書きしない（.env.local は上書き可能）。
    - OS 環境変数は保護（protected set）される。
  - Settings クラスで主要設定値をプロパティで取得：
    - J-Quants / kabu API / Slack トークン・チャンネル、DB パス（DuckDB / SQLite）、環境（development/paper_trading/live）、ログレベル判定、is_live/is_paper/is_dev 等のユーティリティ。
  - 必須設定未設定時は ValueError を送出する仕様。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）で銘柄毎のセンチメントを算出。
    - バッチ処理（最大 20 銘柄／リクエスト）、1銘柄あたり記事数制限・文字数トリム、JSON Mode を期待。
    - 429・接続断・タイムアウト・5xx に対して指数バックオフでリトライし堅牢化。
    - レスポンスの厳密なバリデーション実装（JSON 抽出、results 配列、code/score の検証、数値クリップ ±1.0）。
    - 成果は ai_scores テーブルへ冪等的に置換（対象 code のみ DELETE → INSERT）。
    - calc_news_window(target_date) ユーティリティを提供（JST 時間ウィンドウを UTC の naive datetime で返す）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を判定・保存。
    - prices_daily からのルックアヘッド防止（date < target_date）、ニュースウィンドウは news_nlp.calc_news_window を利用。
    - OpenAI 呼び出しは専用実装、API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア合成、閾値で bull / neutral / bear を判定し market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しはリトライ/エラー区別処理を行う（RateLimit/Connection/Timeout/5xx を再試行）。

- Research モジュール（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン）、ma200_dev、ボラティリティ（20日 ATR）、流動性（20日平均出来高・出来高比率）、バリューファクター（PER/ROE）等のファクター計算関数を提供。
    - DuckDB を使った SQL ベースの実装で、prices_daily / raw_financials の参照に限定（本番注文 API にはアクセスしない）。
    - データ不足時の扱い（必要行数未満で None を返す）やスキャン範囲バッファ設計を実装。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意の horizon 指定に対応、horizons の検証あり）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関、有効レコードが3件未満では None を返す）。
    - rank（同順位は平均ランクで処理）と factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- Data モジュール（src/kabusys/data）
  - calendar_management.py
    - JPX マーケットカレンダー管理：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（土日を非営業日）でフォールバックする一貫した動作設計。
    - calendar_update_job により J-Quants API から差分取得 → 保存（バッファ／バックフィル・健全性チェックを含む）。
    - DB 登録値優先・未登録日は曜日フォールバック等、部分的なカレンダーデータでも一貫して動作する設計。
  - pipeline.py / ETL（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を実装（取得数・保存数・品質問題・エラー集約・変換ユーティリティ to_dict）。
    - 差分更新やバックフィル方針、品質チェックの扱い（致命的な品質問題があっても ETL は継続し呼び出し元が判断する設計）を実装方針として反映。
    - DuckDB を利用したテーブル存在チェック / 最大日付取得ユーティリティなどの内部ヘルパを実装。
  - etl.py
    - pipeline.ETLResult を public に再エクスポート。

- パッケージ初期化・エクスポート整理
  - ai/__init__.py, research/__init__.py で主要関数を __all__ により公開。
  - モジュール分割によりテスト差し替え（例えば OpenAI 呼び出し）や結合低減を考慮した設計。

### Security
- 環境変数読み込みで OS 側の環境変数を保護（.env の上書きを抑制するデフォルト挙動）。
- 必須トークン（OpenAI / Slack / Kabu / J-Quants）の未設定は明示的な例外で通知。

### Design decisions / Notes
- ルックアヘッドバイアス回避のため、多くのモジュールで datetime.today() / date.today() を直接参照せず、target_date を呼び出し側で渡す設計。
- DuckDB を中心としたローカル分析データベース設計。ETL・カレンダー・リサーチ処理はいずれも DuckDB 接続を受け取る形で実装。
- OpenAI 呼び出し部分はテストで差し替えやすいように内部関数を分離してある（unittest.mock.patch によりモック可能）。

### Fixed
- 初版のため該当なし。

### Changed
- 初版のため該当なし。

### Deprecated
- 初版のため該当なし。

### Removed
- 初版のため該当なし。