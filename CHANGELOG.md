# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニング (SemVer) を採用します。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回リリース

### Added
- パッケージの初期構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数からの設定読み込み機能を実装
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env 読み込みの上書きルール（.env → .env.local）と OS 環境変数保護機能
  - .env 行パーサーの実装:
    - export KEY=... 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - インラインコメント処理（クォートあり/なしの違いを考慮）
  - Settings クラスによりアプリ設定をプロパティで提供:
    - J-Quants / kabuステーション API、Slack トークン / チャンネル
    - データベースパス (DuckDB, SQLite)
    - 監視設定（PID ファイル、CPU/メモリ/ディスク閾値）
    - 実行環境判定（development / paper_trading / live）とログレベル検証

- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング (kabusys.ai.news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini の JSON モード）へバッチ送信してセンチメントを取得
    - タイムウィンドウ: JST 前日 15:00 〜 当日 08:30（DB 比較は UTC に変換）
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたり記事数・文字数制限でトークン肥大化を抑制
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ
    - レスポンス検証・数値変換・±1.0 でクリップ
    - 成功した銘柄のみ ai_scores テーブルへ置換的に書き込み（DELETE → INSERT、部分失敗に強い）
    - テスト容易性: OpenAI 呼び出しはモジュール内 _call_openai_api を patch 可能
    - ルックアヘッドバイアス回避の設計（datetime.today() を直接参照しない）

  - 市場レジーム判定 (kabusys.ai.regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成してレジーム（bull/neutral/bear）を判定
    - prices_daily と raw_news を参照して日次判定
    - マクロキーワードによるニュースフィルタリング、OpenAI（gpt-4o-mini）に JSON 出力を要求
    - API エラー時は macro_sentiment=0.0 として継続（フェイルセーフ）
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、ROLLBACK 対応）
    - 設計上の注意点や安全策（ルックアヘッド回避、リトライ、5xx 判定、ログ出力）

- データ基盤関連（kabusys.data）
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを利用した営業日判定ユーティリティ:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB 登録値優先、未登録日のフォールバックは曜日ベース（土日を非営業日とする）
    - calendar_update_job により J-Quants から差分取得して冪等で保存。バックフィル（直近再取得）と健全性チェックを実装
  - ETL パイプラインのインターフェース（etl モジュール → ETLResult を再エクスポート）
  - ETL 実装のコア（pipeline）
    - ETLResult データクラス（実行結果、品質問題、エラー情報を保持）
    - 差分取得、バックフィル、品質チェック（quality モジュール利用）、jquants_client 経由の保存処理の設計
    - DB テーブル存在チェック等のユーティリティ

- リサーチ（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時の扱いを明記）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（最新レポートを target_date 以前で取得）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来終値リターンを一括取得するクエリ実装
    - calc_ic: Spearman ランク相関（IC）算出。十分なサンプルがない場合は None を返す
    - rank: 平均ランク付け（同順位は平均ランク）、丸め処理により ties の誤差を抑制
    - factor_summary: count/mean/std/min/max/median の統計サマリー
  - data.stats の zscore_normalize を再エクスポートする形で研究用 API を提供

### Changed
- （初回リリースのため、過去バージョンからの変更はなし）
- 各モジュールは外部副作用（実売買 API 等）を行わない設計で実装。DuckDB と OpenAI（読み取り）への依存に限定。

### Fixed
- （初回リリースのため、バグ修正履歴はなし）

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY にて供給。未設定時は ValueError を発生させ明示的に扱う。
- .env 読み込みでは既存の OS 環境変数を保護する仕組み（protected set）を導入。

### Notes / Limitations
- LLM 呼び出しは外部サービスに依存するため、ネットワーク障害やレート制限発生時はフェイルセーフ（スコア 0.0 またはスキップ）で継続する設計です。完全な可用性は外部 API の状態に依存します。
- 一部の関数はデータ不足時に中立値（None または 1.0 等）を返す仕様です（ログに警告を出力）。
- DuckDB バインドの互換性に配慮し、executemany に空リストを渡さないガードを実装しています。
- news_nlp と regime_detector はそれぞれ独立した OpenAI 呼び出しラッパーを持ち、モジュール結合を避ける設計です（テストで patch 可能）。

---

過去のリリースや未反映の変更がある場合は本 CHANGELOG を更新してください。