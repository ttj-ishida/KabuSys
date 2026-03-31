# Changelog

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」仕様に準拠します。  
リリースはセマンティックバージョニングに従います。

最新更新日: 2026-03-31

## [Unreleased]
（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-03-31
初回公開リリース。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本セットアップを追加。バージョンは 0.1.0。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート判定は __file__ から親ディレクトリを探索し、.git または pyproject.toml を基準に特定。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val フォーマット対応。
    - シングル／ダブルクォート内のエスケープ処理やインラインコメント考慮。
    - クォートなし値のコメント判定（直前がスペースまたはタブの場合）。
  - Settings クラスを提供（プロパティ経由で型変換や必須チェックを実施）。
    - J-Quants / kabu ステーション / Slack / DB パス / ログレベル / 環境フラグ等の設定を用意。
    - 値検証（KABUSYS_ENV の許容値・LOG_LEVEL の許容値等）を行う。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を元に、銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価して ai_scores テーブルへ保存。
    - バッチ処理（最大 20 銘柄/API コール）、トークン肥大対策（記事数・文字数制限）、リトライ（429・ネットワーク・5xx に対する指数バックオフ）を実装。
    - レスポンスバリデーションと数値クリップ（±1.0）を実施。部分成功時の DB 保護（対象コードのみ DELETE→INSERT）。
    - 時間ウィンドウ（JST 前日15:00 ～ 当日08:30）計算ユーティリティ calc_news_window を提供。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して daily レジーム（bull/neutral/bear）を判定・market_regime テーブルへ保存。
    - OpenAI 呼び出しは専用実装、API エラー時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）。
    - DuckDB クエリはルックアヘッドを防ぐ条件（date < target_date 等）で実装。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実現。

- データ基盤 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - 夜間バッチ更新 calendar_update_job により J-Quants API から差分取得→冪等保存（fetch & save の呼び出しを想定）。
    - 健全性チェック、バックフィル（直近 N 日の再取得）等を実装。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー一覧等の構造を保持）。
    - 差分取得、バックフィル、品質チェックの設計方針とユーティリティ関数を実装。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。
    - kabusys.data.etl は pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金 / 出来高比率）を計算する関数を提供（calc_momentum, calc_value, calc_volatility）。
    - DuckDB 上で SQL と窓関数を用いて効率的に取得。
    - データ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応・入力検証）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を持たない純粋 Python 実装（pandas 等未使用）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制約 / 注意点 (Known issues / Notes)
- OpenAI 利用
  - API キーは引数または環境変数 OPENAI_API_KEY が必須。未設定時は ValueError を送出する関数がある。
  - 使用モデルは gpt-4o-mini。JSON Mode を利用して厳密な JSON レスポンスを期待するが、パース失敗時の復元ロジック（最外側の {} を抽出）を実装している。
- データベース依存
  - DuckDB を前提。DuckDB のバージョン差異（例: executemany に空リスト不可等）に合わせた互換性処理を含む。
  - 一部モジュールは jquants_client（kabusys.data.jquants_client）への依存を持つが、今回の提供コードには jquants_client の実装は含まれない。
- 時刻処理
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を参照しない設計（target_date を明示的に渡すことを想定）。
- フェイルセーフ設計
  - OpenAI や外部 API の失敗時には例外を投げずにフォールバック（0.0）やスキップを行う箇所がある。運用時はログで事象を確認すること。

### アップグレード / 移行手順 (Upgrade notes)
- 環境変数を適切に設定すること（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）。
- パッケージ配布後に自動 .env 読み込みが必要ない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）を事前に用意するか、ETL で作成・初期ロードを行う必要あり。

---

開発・利用に関する詳細な設計方針や API の使い方は各モジュールの docstring／コメントを参照してください。変更履歴は今後のコミットごとに更新します。