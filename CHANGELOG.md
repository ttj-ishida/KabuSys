# CHANGELOG

すべての重要な変更履歴をここに記録します。本ファイルは Keep a Changelog 準拠の形式を採用しています。

最新リリース: 0.1.0 (初期公開)

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04
初期公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの公開インターフェースを追加（data / strategy / execution / monitoring）。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
  - 自動ロードの順序: OS 環境変数 → .env.local (上書き) → .env（未設定のみ）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - `.env` のパース機能を強化:
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォートとバックスラッシュエスケープを考慮した値の抽出。
    - 行内コメントの取り扱い（クォートの有無に応じた判定）。
  - 必須設定取得ヘルパ `_require` と Settings クラスを提供:
    - J-Quants / kabuステーション / LINE / データベースパス / 監視設定 / システム設定（env, log_level）等のプロパティを実装。
    - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（許容値チェック）。

- データプラットフォーム関連
  - ETL パイプラインの公開インターフェース（ETLResult の再エクスポート）。
  - ETL 結果を表す `ETLResult` dataclass (`kabusys.data.pipeline`) を実装:
    - 取得・保存件数、品質チェックの結果、エラー一覧などを保持。
    - to_dict() によるシリアライズ対応。
  - JPX カレンダー管理モジュール (`kabusys.data.calendar_management`) を実装:
    - market_calendar テーブルを元に営業日判定（is_trading_day, is_sq_day）。
    - 翌営業日 / 前営業日 / 期間内営業日列挙（next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック含む）。

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`):
    - モメンタム: calc_momentum（1M/3M/6M リターン、200日MA乖離）。
    - ボラティリティ/流動性: calc_volatility（20日ATR、相対ATR、平均売買代金、出来高比率）。
    - バリュー: calc_value（PER、ROE。raw_financials からの最新財務データを参照）。
    - 計算は DuckDB の prices_daily / raw_financials のみを参照。
  - 特徴量探索 (`kabusys.research.feature_exploration`):
    - 将来リターン計算: calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンのランク相関）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク）。
    - 統計サマリー: factor_summary（count, mean, std, min, max, median）。
  - research パッケージの公開 API を整理（関数群の再エクスポート）。

- AI 機能 (`kabusys.ai`)
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`):
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - JST 時間ウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）とそれに基づく calc_news_window を実装。
    - バッチ処理（最大 20 銘柄／回）、1銘柄あたりの記事数・文字数制限、レスポンスバリデーションを実装。
    - OpenAI API 呼び出しのリトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ。
    - JSON Mode のレスポンスに対する堅牢なパース（前後余計テキストの復元ロジックを含む）。
    - DuckDB の executemany に対する互換性対応（空リスト回避）と冪等的な DELETE→INSERT ロジック。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`):
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を生成。
    - マクロニュース抽出はキーワードマッチ（複数キーワード）で行い、最大記事数を制限。
    - OpenAI 呼び出しは専用ラッパーを用いてリトライ制御・例外ハンドリングを実装。
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT と失敗時の ROLLBACK ハンドリング）。
  - AI モジュールはテスト容易性のため `_call_openai_api` をモック差し替え可能。

### Changed
- （初回リリースのため該当なし）

### Fixed / Hardening
- .env 読み込みや OpenAI レスポンス処理など、実運用で起きうる不整合に対する堅牢化を多数実装:
  - .env の読み込み失敗時に警告を出して継続する（例外を投げない）。
  - OpenAI レスポンスの JSON パース失敗や API エラー時はフェイルセーフでスコアを 0.0 にフォールバックする（例外を上位へ投げない設計の箇所あり）。
  - DuckDB の互換性問題（executemany の空リスト等）への対応。
  - 各処理でルックアヘッドバイアスを防ぐ設計（datetime.today()/date.today() を直接参照しない箇所の説明を明示）。

### Security
- 必須機密情報は環境変数経由で取得する設計（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
- `.env` 自動ロードでは既存 OS 環境変数を保護するための protected キーセットを用いる。

### Known limitations / Notes
- OpenAI を利用する機能（score_news, score_regime）は動作に `OPENAI_API_KEY` が必要。キー未設定時は ValueError を送出する。
- AI スコアは実装上 ±1.0 にクリップされる（安全領域の確保）。
- ETL / calendar_update_job / 各種 DB 操作は DuckDB 接続を前提としており、テーブル（prices_daily, raw_news, market_calendar, ai_scores, news_symbols, raw_financials 等）のスキーマ整備が前提。
- 本リリースでは発注・実行（kabu の発注等）に直接影響するモジュールは含まれているが、Strategy / Execution の実際の発注ロジックは別モジュールとして想定（本 changelog のコード群は主にデータ・研究・AI 側の基盤実装）。

---

開発者向けの補足:
- テスト時の利便性として、OpenAI 呼び出しラッパー（各モジュールの `_call_openai_api`）は unittest.mock.patch で差し替えて単体テスト可能に設計されています。
- 自動環境変数読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

（以上）