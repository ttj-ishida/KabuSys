# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
リリースバージョンはパッケージ内の __version__（0.1.0）に合わせています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - 日本株自動売買 / リサーチ / データ基盤向けのコア機能群を実装。
  - パッケージエントリポイント: src/kabusys/__init__.py により data, strategy, execution, monitoring を公開。

- 環境設定管理
  - kabusys.config.Settings を実装。環境変数から各種設定値（J-Quants トークン、kabu API パスワード、Slack トークン/チャネル、DBパス 等）を取得。
  - 自動 .env ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml に基づく）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは以下の要件に対応:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無し値のインラインコメント処理（直前がスペース/タブ時のみ）
  - 重要な検証: KABUSYS_ENV と LOG_LEVEL の許容値チェック、必須環境変数未設定時は ValueError を送出。

- データモジュール（DuckDB ベース）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分取得・バックフィル・品質チェックの設計に沿った ETLResult データクラスを実装。
    - DuckDB を用いた最終日付取得ユーティリティ等を提供。
  - calendar 管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新 job（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のマーケットカレンダー用ユーティリティを提供。
    - market_calendar 未登録時の曜日ベースフォールバックを実装し、DB 登録値優先の一貫した挙動を確保。
    - 最大探索範囲制限 (_MAX_SEARCH_DAYS) やバックフィル、健全性チェックを実装。

- AI モジュール（OpenAI 経由の NLP）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で実装。
    - バッチサイズ、記事数・文字数上限、JSON レスポンスの厳密バリデーション、スコアの ±1.0 クリップを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。非リトライ系エラーはスキップして継続（フェイルセーフ）。
    - DuckDB の executemany に関する空リストの互換性考慮を実装（空時は呼ばない）。
  - マクロレジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出ロジック（キーワードによるフィルタ）、LLM 呼び出し（gpt-4o-mini）、レスポンス JSON パース、再試行戦略、API 失敗時の macro_sentiment=0.0 フェイルセーフを実装。
    - ルックアヘッドバイアス対策（target_date 未満のデータのみ参照、datetime.today() を参照しない設計）。

- リサーチ / ファクター群（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）等を計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials からの EPS/ROE を使った PER/ROE 計算（target_date 以前の最新財務データ使用）。
    - いずれも DuckDB 上の SQL とウィンドウ関数で実装し、データ不足時の None ハンドリングを明示。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装（3 銘柄未満は None）。
    - rank: 同順位は平均ランクを返すランク実装（丸めにより ties の検出安定化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算する要約機能。

- リサーチ用ユーティリティの公開
  - kabusys.research.__init__ で主要関数を再公開（zscore_normalize は kabusys.data.stats から）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- なし（初回リリース）

### Notes / 実装上の注記
- OpenAI クライアントの呼び出しは各モジュールで独立実装（テストのために _call_openai_api を patch しやすい設計）。
- DB 書き込みは冪等性を意識（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK の扱い）。
- ログ出力と警告を多用し、外部 API 失敗時は安全にデフォルト値で継続する設計方針（フェイルセーフ）。
- DuckDB との互換性（executemany の空リスト回避等）に対する注意喚起を実装。
- ルックアヘッドバイアス対策として、日次スコア算出処理は内部で現在時刻を直接参照しない設計になっている（target_date を明示的に渡す方式）。

## マイグレーション / 破壊的変更
- なし（初回リリース）。