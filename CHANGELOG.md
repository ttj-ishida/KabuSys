# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-01

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能を実装しました。主な追加点・設計方針・注意点を以下にまとめます。

### Added（追加）
- パッケージ基盤
  - src/kabusys/__init__.py によりパッケージ初期化およびバージョン（0.1.0）を定義。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装（OS環境変数 > .env.local > .env の優先順）。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサで export KEY=val 形式、クォート（シングル／ダブル）とバックスラッシュエスケープ、インラインコメントの取扱い（スペース直前での # をコメントとして認識）に対応。
    - 既存 OS 環境変数を保護するため protected set を使用し、.env.local は override=True で上書き可能に。
    - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス /監視しきい値 / 環境（development/paper_trading/live）/ログレベル等の取得・バリデーションを提供。
    - 必須環境変数が未設定の場合は ValueError を送出するヘルパーを提供。

- AI（ニュース / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を用いて、銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメント（ai_score）を算出。
    - チャンク処理（最大20銘柄/チャンク）、1銘柄あたり最大記事数・文字数でトリム（トークン肥大対策）。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。レスポンス検証（JSON 抽出、results/コード/数値検査）を強化。
    - スコアは ±1.0 にクリップ。取得したスコアのみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時に他銘柄の既存データを保護。
    - lookahead バイアス防止のため datetime.today() を利用せず、target_date ベースで時間ウィンドウを算出。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（225連動）について過去200日移動平均乖離（重み70%）とニュース由来の LLM マクロセンチメント（重み30%）を合成し日次で市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは独立実装で、API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - DB へは冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。ルックアヘッドバイアス防止のためクエリに date < target_date の排他条件を使用。
    - リトライ、エラー分類（RateLimitError / APIError / 5xx 等）を考慮。

- データプラットフォーム（ETL・カレンダー）
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラスを公開。ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返す。
    - 差分更新方針、backfill による再取得、品質チェック（quality モジュール連携）を反映する設計方針を実装。
    - DuckDB を前提としたテーブル存在チェック・最大日付取得等のユーティリティを実装。
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダーの管理機能（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）と夜間バッチ更新 job（calendar_update_job）を実装。
    - market_calendar が存在しない場合は曜日ベース（土日非営業日）でフォールバックする一貫した挙動。
    - calendar_update_job は J-Quants クライアント（jquants_client.fetch_market_calendar / save_market_calendar）を呼び出して差分・バックフィル（直近 _BACKFILL_DAYS）を行う。健全性チェック（将来日付の異常検出）を実装。

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対 ATR、出来高指標）、Value（PER, ROE）を DuckDB の SQL ウィンドウ関数等で計算する関数群（calc_momentum, calc_volatility, calc_value）を実装。
    - データ不足時の None 設定やログ出力を整備。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic / Spearman 相関に相当するランク相関）、ランク関数、統計サマリ（factor_summary）を実装。
    - pandas 等外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。

### Changed（設計・挙動）
- 全体的な設計方針を明確化
  - ルックアヘッドバイアス防止: 全てのバッチ/スコアリング関数は内部で datetime.today()/date.today() を直接参照せず、caller が渡す target_date のみを使用。
  - DB 書き込みは冪等化（DELETE→INSERT または ON CONFLICT を前提）し、トランザクション境界でエラー発生時は ROLLBACK を試行。
  - OpenAI との連携は JSON Mode を利用し、レスポンス検証を厳格に行うことで LLM の不安定出力に耐性を持たせる。
  - API 呼び出しはリトライと指数バックオフを導入し、致命的失敗時もシステム全体が停止しない（フェイルセーフ）設計。

### Fixed（バグ修正 / 安全対策）
- 環境変数ロード処理でのエンコーディング・ファイル読み込み失敗時に警告発行し処理継続する挙動を追加。
- .env パーサのクォート内エスケープ処理を強化し、複雑な値（引用符・バックスラッシュ含む）を正しく扱えるように改善。
- DuckDB executemany に空リストを渡すと失敗する問題に対し、実行前に空チェックを行う保護を追加（ai_scores / pipeline の INSERT/DELETE に適用）。
- OpenAI API 呼び出し時の APIError について、status_code の有無に柔軟に対応するロジックを導入（将来の SDK 変化に耐える）。

### Security（セキュリティ関連）
- 環境変数の自動上書きを防ぐ protected set の導入により、OS 環境変数が .env によって意図せず上書きされることを防止。
- 必須のシークレット類（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）は Settings で明示的に require し、未設定時は早期に例外を発生させることで不正な公開や誤設定を検出しやすくしています。

### Known issues / Limitations（既知の制約）
- jquants_client（J-Quants API 連携）および quality モジュールは本コード内で参照されるが、この変更セットに実装ファイルが含まれていないため、実際の API 連携には別途クライアント実装が必要です。
- OpenAI SDK 依存: 本実装は OpenAI の Python SDK（chat.completions.create を利用するインターフェース）を前提としているため、SDK バージョンにより微調整が必要となる可能性があります。
- DuckDB の SQL バインドや型戻りに関しては、環境（DuckDB バージョン）差異に依存する箇所があるため、運用環境での互換性確認を推奨します。

---

メジャーな追加機能や設計方針（ルックアヘッド防止・冪等性・厳格なレスポンス検証・フェイルセーフ）を中心に初期実装を行いました。運用開始後に実データでの挙動確認（品質チェックルール調整、AI プロンプト改善、API レート制御調整等）を推奨します。