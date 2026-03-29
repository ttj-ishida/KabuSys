# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-29

### Added
- 初回リリース。KabuSys 日本株自動売買システムのコアライブラリを追加。
- パッケージエントリーポイント
  - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。パッケージの主要サブパッケージ（data, research, ai, ...）を __all__ で提示。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動で読み込む仕組みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント（#）の取り扱いに対応する堅牢な実装。
  - OS 環境変数の保護（protected set）をサポートした上書きロジック。
  - Settings クラスを提供し、必須環境変数取得（_require）や各種設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト有）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development|paper_trading|live の検証）、LOG_LEVEL の検証
    - is_live / is_paper / is_dev のヘルパー
- AI モジュール（src/kabusys/ai）
  - news_nlp: ニュースセンチメントスコアリング（score_news）
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）calc_news_window を提供。
    - raw_news と news_symbols を集約して銘柄ごとに最大記事数・文字数でトリムし、OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄/チャンク）。
    - API 呼び出しのリトライ（429・接続断・タイムアウト・5xx）、レスポンスバリデーション、スコアの ±1.0 クリップ。
    - DuckDB への冪等書き込み（DELETE → INSERT）で部分失敗時に他銘柄データを保護。
    - テスト補助: _call_openai_api を patch できる設計。
  - regime_detector: 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily レジーム（bull / neutral / bear）判定。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - マクロニュース抽出、OpenAI 呼び出し、リトライ、フォールバック（API失敗時 macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト補助: _call_openai_api を patch できる設計。
- Data モジュール（src/kabusys/data）
  - calendar_management:
    - JPX カレンダー管理：market_calendar に基づく営業日判定ロジックを提供（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants から差分取得し冪等保存、バックフィルや健全性チェック実装。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得数・保存数・品質チェック結果・エラー等を集約）。
    - ETL 設計方針に準拠した差分取得、バックフィル、品質チェックのインフラを用意。
  - etl モジュールで ETLResult を再エクスポート。
- Research モジュール（src/kabusys/research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 偏差を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が0や欠損時は None）。
    - DuckDB 上で SQL + Python により実行（外部 API へアクセスしない設計）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関による IC（Information Coefficient）を算出（有効レコード < 3 の場合 None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と統計サマリ（count/mean/std/min/max/median）を提供。
- ロギング・定数・設計上の注記
  - 各モジュールでログ出力を適切に実装（info/warning/debug）。
  - API リトライ回数やバックオフ、バッチサイズ、ウィンドウ定義、しきい値等はモジュール内定数として明示。
  - DuckDB をデータ層の前提として設計（互換性考慮の記述あり）。
- テスト容易性
  - OpenAI 呼び出しを切り替え可能（モジュール内の _call_openai_api を patch することでユニットテスト可能）。
  - 環境変数自動ロードを環境変数で無効化でき、テスト時に副作用を抑制可能。

### Changed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env 自動読み込み時に OS 環境変数を保護する実装（既存の OS 環境変数は上書きされない、.env.local の override 時にも保護キーは尊重）。

### 注意事項 / 既知の制約
- OpenAI API（gpt-4o-mini）利用部分は外部サービス依存。API キー未設定時は ValueError を送出する仕様（score_news / score_regime）。
- DuckDB のバージョン互換性注意（executemany の空リスト制約などについてコード内に互換処理あり）。
- 時刻扱いは UTC naive な datetime を用いており、JST <---> UTC の変換ロジックはモジュール内で明示的に扱っている。利用時は target_date が date オブジェクトであることを前提とする。
- レスポンスのフォールバック設計により、外部 API が不安定でもシステムは継続するが、その際は macro_sentiment=0.0 や該当銘柄のスコア未取得（スキップ）となる点に注意。

### マイグレーション / 利用開始メモ
- .env.example を参照して必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）を設定してください。
- 自動的に .env/.env.local をロードする挙動をテストで抑えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のパス（DUCKDB_PATH）がデフォルト data/kabusys.duckdb に設定されているため、初回利用時はディレクトリ作成等を行ってください。
- OpenAI 呼び出しをユニットテストでモックするには、kabusys.ai.news_nlp._call_openai_api もしくは kabusys.ai.regime_detector._call_openai_api を patch してください。

---

今後のリリースでは以下を想定しています（例）:
- モデルや API クライアント抽象化の強化（複数モデル対応など）
- ai_score / market_regime の可視化・モニタリング機能追加
- ETL のスケジューラ連携・差分取得ロジック強化

（問題や要望があれば issue を作成してください。）